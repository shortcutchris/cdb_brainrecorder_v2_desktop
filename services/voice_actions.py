"""Account-bound presentation requests, never voice-authorized power commands.

The live executor already holds the live lock. Do not acquire control_lock here.
Touch confirmations run under control_lock then live.lock, in the normal order.
"""
import copy
import json
import threading
import time
from pathlib import Path

ACTION_NAMES = ('show_device_timer', 'show_device_clock', 'check_meeting_readiness',
                'open_device_help', 'prepare_speaker_test', 'prepare_device_move')
HELP_TOPICS = ('start', 'kabel', 'audio', 'talk', 'meeting', 'timer', 'timerdisplay', 'probleme')


def valid_action(name, args):
    if name == 'show_device_timer':
        return set(args) == {'id'} and isinstance(args['id'], str) and 1 <= len(args['id']) <= 64
    if name == 'open_device_help':
        return set(args) == {'topic'} and args['topic'] in HELP_TOPICS
    return name in ACTION_NAMES and not args


class VoiceActions:
    def __init__(self, app, *, clock=time.monotonic):
        self.app, self.clock = app, clock
        self.lock = threading.RLock()
        self.row = None
        self.lcd = None
        self.observation = None

    def observe(self, state):
        # Called by state() after its normal activity checks. The live tool must
        # never acquire the recorder/control locks in the opposite order.
        with self.lock:
            self.observation = {'at': self.clock(), 'account': self.app.room.account(),
                                'record': dict(state['capabilities']['record'])}

    def _current(self):
        row = self.row
        if row and (row['account'] != self.app.room.account() or row['epoch'] != self.app.room.epoch or self.clock() >= row['expires']):
            self.row = None
        return self.row

    def readiness(self):
        from services.voice_device import device_status
        components = device_status(self.app)['components']
        with self.lock:
            observed = self.observation
            fresh = observed and observed['account'] == self.app.room.account() and self.clock() - observed['at'] < 10
            activity = observed['record'] if fresh else {'allowed': False, 'reason': 'Aktueller Bedienstatus unbekannt. Display prüfen.'}
        cfg = self.app.store.config()
        checks = [
            ('Anmeldung', components['account'].get('signed_in')),
            ('Mikrofon erkannt', components['microphone'].get('detected')),
            ('Freier Speicher', None if 'low_space' not in components['storage'] else not components['storage']['low_space']),
            ('Einrichtung abgeschlossen', bool(cfg.get('setup_complete'))),
            ('Lautsprecher hörbar eingestellt', components['speakers'].get('audible_expected')),
            ('Mikrofon-Hardwareschalter', None if not components['respeaker_leds'].get('connected') else not components['respeaker_leds'].get('hardware_muted', True)),
        ]
        rows = [{'label': label, 'state': 'unknown' if value is None else 'ok' if value else 'attention'} for label, value in checks]
        return {'checks': rows, 'can_start_now': bool(activity['allowed'] and all(r['state'] == 'ok' for r in rows)),
                'activity_reason': activity['reason'], 'processing': components['processing'],
                'instruction': 'Nur technische Momentaufnahme. Kein Hör-, Aufnahme-, Modell- oder Netztest; keine Aufnahme gestartet. Das laufende Gespräch muss vor einer Aufnahme enden.'}

    def request(self, scope, request):
        name, args = request['name'], request['arguments']
        if not valid_action(name, args): raise ValueError('Ungültige Geräteansicht.')
        account = self.app.room.account()
        if not account: raise ValueError('Anmeldung erforderlich.')
        data = {}
        if name == 'show_device_timer':
            visible = self.app.schedules.visible_ids()
            rows = [i for i in self.app.schedules.items() if i['id'] in visible]
            if args['id'] == 'current':
                rows = [i for i in rows if i['state'] in ('scheduled', 'due', 'missed')]
                if len(rows) != 1:
                    return {'ok': False, 'code': 'choose_timer' if rows else 'no_timer',
                            'instruction': 'Timerliste abfragen und bei mehreren Timern nach dem gewünschten Timer fragen.'}
            else:
                rows = [i for i in rows if i['id'] == args['id']]
            if len(rows) != 1: raise ValueError('Timer nicht sichtbar oder nicht mehr vorhanden.')
            data = {'timer_id': rows[0]['id']}
        elif name == 'check_meeting_readiness':
            data = self.readiness()
        elif name == 'open_device_help':
            articles = json.loads((Path(__file__).resolve().parents[1] / 'studio/help/articles.json').read_text())
            data = {'article': next(a for a in articles if a['id'] == args['topic'])}
        with self.lock:
            if self._current() and self.row['name'] in ('prepare_speaker_test', 'prepare_device_move'):
                return {'ok': False, 'code': 'confirmation_pending', 'instruction': 'Zuerst den offenen Geräteablauf am Display abschließen oder abbrechen.'}
            self.row = {'id': request['id'], 'name': name, 'data': data, 'stage': 'offered',
                        'account': account, 'epoch': self.app.room.epoch, 'generation': self.app.live.generation,
                        'expires': self.clock() + 120, 'shown': False}
            if name in ('show_device_timer', 'show_device_clock'):
                self.lcd = {'account': account, 'epoch': self.app.room.epoch, 'mode': name,
                            'timer_id': data.get('timer_id'), 'expires': self.clock() + 3600}
        return {'ok': True, 'presentation': 'requested',
                'confirmation_required': name in ('prepare_speaker_test', 'prepare_device_move'),
                **(data if name == 'check_meeting_readiness' else {}),
                'instruction': 'Ansicht am Pi angefordert, noch keine sichtbare Anzeige bestätigt. Keine Aufnahme, kein Testton, kein Gesprächsende und kein Herunterfahren ausgeführt. Offene Dialoge haben Vorrang; Aufforderung verfällt nach zwei Minuten.'}

    def public(self):
        with self.lock:
            row = self._current()
            return None if not row else {k: copy.deepcopy(row[k]) for k in ('id', 'name', 'data', 'stage', 'shown')}

    def touch(self, body):
        if set(body) != {'id', 'action'}: raise ValueError('Ungültige Bestätigung.')
        # All callers hold control_lock. Same lock order as the live executor.
        with self.app.live.lock, self.lock:
            row = self._current()
            if not row or body['id'] != row['id']: raise ValueError('Geräteablauf abgelaufen. Bitte erneut anfordern.')
            action = body['action']
            if action == 'dismiss':
                test = self.app.speakers.test_status()
                if row.get('test_id') and test.get('id') == row['test_id'] and test['state'] == 'running':
                    self.app.speakers.stop_test()
                self.row = None
                return {'ok': True}
            if action == 'shown':
                if not row['shown']:
                    row.update(shown=True, expires=self.clock() + 600)
                return {'ok': True}
            if row['name'] not in ('prepare_speaker_test', 'prepare_device_move'):
                raise ValueError('Diese Ansicht enthält keine Geräteaktion.')
            if action == 'end_talk':
                if self.app.live.generation != row['generation']: raise ValueError('Inzwischen wurde ein anderes Gespräch gestartet.')
                self.app.live.end(generation=row['generation'])
                return {'ok': True, 'stage': 'ending_talk'}
            if row['name'] == 'prepare_speaker_test':
                if action == 'start_test':
                    if row['stage'] != 'offered': raise ValueError('Test wurde bereits gestartet.')
                    self.app.room.require_operator()
                    self.app.require('configure')
                    if any(t > time.monotonic() for t in self.app.playback_leases.values()): raise ValueError('Wiedergabe zuerst beenden.')
                    if self.app.countdown is not None: raise ValueError('Aufnahmevorbereitung zuerst beenden.')
                    row['test_id'] = self.app.speakers.start_test()['id']
                    row['stage'] = 'testing'
                elif action in ('heard', 'not_heard'):
                    test = self.app.speakers.test_status()
                    if row['stage'] != 'testing' or test['state'] != 'completed' or test.get('id') != row.get('test_id'):
                        raise ValueError('Testton wurde noch nicht vollständig ausgegeben.')
                    row['stage'] = action
                else: raise ValueError('Unbekannter Testschritt.')
                return {'ok': True, 'stage': row['stage']}
            # A voice tool may only open a preparation. The existing shutdown
            # route requires its own explicit screen confirmation and all guards.
            raise ValueError('Herunterfahren separat am Display bestätigen.')

    def project_lcd(self, snapshot):
        with self.lock:
            selection = self.lcd
            if selection and (selection['account'] != self.app.room.account() or selection['epoch'] != self.app.room.epoch or self.clock() >= selection['expires']):
                self.lcd = selection = None
            # Never hide a due/missed alarm, including other timers.
            if not selection or any(t['state'] in ('due', 'missed') for t in snapshot['timers']): return snapshot
            if selection['mode'] == 'show_device_clock': return snapshot | {'timers': [], 'total': 0}
            chosen = [t for t in snapshot['timers'] if t['id'] == selection['timer_id']]
            return snapshot | {'timers': chosen, 'total': 1} if chosen else snapshot

    def lcd_focus(self):
        # Reuse scope/expiry cleanup before the snapshot applies its page limit.
        self.project_lcd({'timers': [], 'total': 0})
        with self.lock:
            return self.lcd.get('timer_id') if self.lcd else None
