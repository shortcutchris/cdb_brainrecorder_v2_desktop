"""Offline safety/flow tests. These fixtures never connect to a Pi or play audio."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from scripts.diagnose_usb_audio import (
    Abort, Api, Diagnostic, NoRedirect, OPEN_STATES, Reply, hardware_snapshot, write_report,
)


SINK = 'alsa_output.usb-0020_188A_20210924-00.analog-stereo'


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        if seconds < 0:
            raise ValueError('sleep length must be non-negative')
        self.now += seconds


class FakeApi:
    def __init__(self, clock):
        self.clock = clock
        self.lock = threading.RLock()
        self.calls = []
        self.starts = []
        self.completions = []
        self.epoch = 'private-account-epoch'
        self.csrf = 'never-export-this-token'
        self.selected = SINK
        self.volume = 40
        self.available = True
        self.signed_in = True
        self.flags = {}
        self.test = {'state': 'idle'}
        self.until = 0
        self.cooldown_until = 0
        self.ringing = None
        self.countdown = False
        self.items = [{'id': 'old-timer', 'kind': 'timer', 'label': 'Private client meeting',
                       'state': 'done', 'tone': 'bell', 'revision': 3, 'sound': 'completed'}]
        self.announcements = {'ready': True, 'timers': True, 'countdown': True, 'countdown_ready': True}
        self.foreign_count = 0
        self.force_activity = None
        self.hook = None
        self.reject_stop = False
        self.bad_concurrency = False
        self.count = 0

    def refresh(self):
        if self.test['state'] == 'running':
            self.cooldown_until = self.clock()+2
        if self.test['state'] == 'running' and self.clock() >= self.until:
            self.completions.append(self.clock())
            self.test['state'] = 'completed'
            self.countdown = False
        for item in self.items:
            if item['state'] != 'scheduled':
                continue
            remaining = item['due']-self.clock()
            if (5 <= remaining <= 7 and self.announcements['countdown'] and
                    not self.countdown and self.test['state'] != 'running'):
                self.countdown = True
                self.test = {'state': 'running', 'kind': 'announcement', 'device': self.selected}
                self.until = item['due']
            if remaining <= 0:
                item.update(state='due', sound='attempted', revision=item['revision']+1)
                self.ringing = item['id']
                self.countdown = False
                self.test = {'state': 'running', 'kind': 'alarm', 'device': self.selected}
                self.until = self.clock()+60

    def global_status(self):
        mode = 'alarm' if self.ringing else 'speaker-test' if self.test['state'] == 'running' else 'idle'
        result = {
            'preview': False, 'signed_in': self.signed_in, 'account_epoch': self.epoch, 'csrf': self.csrf,
            'activity': self.force_activity or {'mode': mode, 'busy': mode != 'idle', 'recording': False, 'live_busy': False},
            'pending_processing': False, 'playback_active': False, 'output_busy': self.test['state'] == 'running',
            'output_cooldown_active': self.clock() < self.cooldown_until,
            'pending_login': False, 'pending_intent': False,
            'open_timer_count': self.foreign_count + sum(i['state'] in OPEN_STATES for i in self.items),
            'ringing_id': self.ringing, 'countdown_active': self.countdown,
            'speakers': {'selected': self.selected, 'available': self.available, 'volume': self.volume,
                         'muted': False, 'test': self.test,
                         'devices': [{'id': self.selected}] if self.available else []},
        }
        result.update(self.flags)
        return copy.deepcopy(result)

    def get(self, path):
        with self.lock:
            self.calls.append(('GET', path))
            self.refresh()
            if self.hook:
                self.hook(self, path)
            if path == '/api/state':
                return copy.deepcopy({'room': {'epoch': self.epoch}, 'timers': {'items': self.items},
                    'announcements': self.announcements, 'csrf': self.csrf,
                    'cdb': {'identity': {'name': 'PRIVATE_ACCOUNT_NAME'}}})
            if path == '/api/speakers/diagnostic-status':
                return self.global_status()
            raise AssertionError('Unexpected GET: ' + path)

    def request(self, path, body=None, csrf=None):
        with self.lock:
            self.calls.append(('POST', path, copy.deepcopy(body), csrf))
            if csrf != self.csrf:
                return Reply(403, {'error': 'bad token'})
            self.refresh()
            if path in ('/api/speakers/test', '/api/timers/tone'):
                if self.test['state'] == 'running' and not self.bad_concurrency:
                    return Reply(400, {'error': 'Lautsprechertest läuft.'})
                self.test = {'state': 'running', 'kind': 'test', 'device': self.selected}
                self.starts.append(self.clock())
                self.until = self.clock()+3
                return Reply(200, copy.deepcopy(self.test))
            if path == '/api/speakers/stop':
                if self.reject_stop:
                    return Reply(400, {'error': 'not stopped'})
                self.test['state'] = 'cancelled'
                return Reply(200, copy.deepcopy(self.test))
            if path == '/api/timers' and body['action'] == 'create':
                self.count += 1
                ident = 'test-timer-' + str(self.count)
                self.items.append({'id': ident, 'label': body['label'], 'kind': 'timer',
                    'state': 'scheduled', 'revision': 1, 'sound': 'pending',
                    'tone': body['tone'], 'due': self.clock()+body['seconds']})
                return Reply(200, {'id': ident})
            if path == '/api/timers':
                row = next(i for i in self.items if i['id'] == body['id'])
                if row['revision'] != body['revision']:
                    return Reply(400, {'error': 'revision changed'})
                row.update(state='done' if body['action'] == 'ack' else 'cancelled', revision=row['revision']+1)
                if self.ringing == row['id']:
                    self.test['state'] = 'cancelled'; self.ringing = None
                return Reply(200, {'ok': True})
            raise AssertionError('Unexpected POST: ' + path)

    @property
    def mutations(self):
        return [call for call in self.calls if call[0] == 'POST']


class UsbAudioDiagnosticTests(unittest.TestCase):
    def make(self):
        clock = Clock()
        api = FakeApi(clock)
        diagnostic = Diagnostic(api, clock=clock, sleep=clock.sleep,
                                collect=lambda since: {'usb': [], 'kernel_events': []},
                                collect_usb=lambda: [{'port': '1-1.4', 'idVendor': '0020', 'idProduct': '0b21'}])
        return diagnostic, api, clock

    def test_default_is_read_only_and_report_contains_no_raw_app_data(self):
        diagnostic, api, _ = self.make()
        report = diagnostic.execute()
        self.assertEqual(report['result'], 'preflight_ready')
        self.assertEqual(api.mutations, [])
        text = json.dumps(report)
        for secret in (api.csrf, api.epoch, 'PRIVATE_ACCOUNT_NAME', 'Private client meeting', SINK):
            self.assertNotIn(secret, text)

    def test_observation_check_can_finish_after_its_deadline(self):
        diagnostic, api, clock = self.make()
        api.hook = lambda *_: clock.sleep(.6)
        with patch.object(diagnostic, 'sleep', wraps=clock.sleep) as sleep:
            diagnostic.observe(1)
        self.assertGreaterEqual(clock.now, 101)
        sleep.assert_not_called()
        self.assertEqual(api.mutations, [])

    def test_unexpected_failure_reports_class_without_sensitive_message(self):
        diagnostic, api, _ = self.make()
        api.hook = Mock(side_effect=ValueError(api.csrf))
        report = diagnostic.execute(True)
        self.assertEqual(report['error_type'], 'ValueError')
        self.assertEqual(report['result'], 'aborted')
        self.assertNotIn(api.csrf, json.dumps(report))
        self.assertEqual(api.mutations, [])

    def test_every_global_blocker_and_missing_safety_field_fails_closed(self):
        cases = {'signed_in': False, 'preview': True, 'pending_processing': True, 'output_cooldown_active': True,
                 'playback_active': True, 'output_busy': True, 'pending_login': True,
                 'pending_intent': True, 'open_timer_count': 1, 'countdown_active': True}
        for field, value in cases.items():
            with self.subTest(field=field):
                diagnostic, api, _ = self.make(); api.flags[field] = value
                self.assertEqual(diagnostic.execute(True)['result'], 'aborted')
                self.assertEqual(api.mutations, [])
        for field in ('pending_processing', 'playback_active', 'output_busy', 'output_cooldown_active', 'pending_login', 'pending_intent',
                      'open_timer_count', 'countdown_active', 'account_epoch', 'csrf'):
            with self.subTest(missing=field):
                diagnostic, api, _ = self.make(); api.flags[field] = None
                self.assertEqual(diagnostic.execute(True)['result'], 'aborted')
                self.assertEqual(api.mutations, [])

    def test_other_account_timers_and_active_capture_are_blockers(self):
        diagnostic, api, _ = self.make(); api.foreign_count = 1
        self.assertEqual(diagnostic.execute(True)['reason'], 'unowned_open_timers')
        self.assertEqual(api.mutations, [])
        for mode in ('recording', 'paused', 'live-active', 'microphone-test', 'maintenance', 'download'):
            with self.subTest(mode=mode):
                diagnostic, api, _ = self.make()
                api.force_activity = {'mode': mode, 'busy': True, 'recording': mode in ('recording', 'paused'), 'live_busy': mode == 'live-active'}
                self.assertEqual(diagnostic.execute(True)['result'], 'aborted')
                self.assertEqual(api.mutations, [])

    def test_never_selects_or_unmutes_an_output(self):
        diagnostic, api, _ = self.make(); api.selected = 'alsa_output.usb-reSpeaker'
        self.assertEqual(diagnostic.execute(True)['reason'], 'select_188a_first')
        self.assertEqual(api.mutations, [])
        diagnostic, api, _ = self.make(); api.volume = 0
        self.assertEqual(diagnostic.execute(True)['reason'], 'audible_volume_required')
        self.assertEqual(api.mutations, [])

    def test_complete_flow_bounds_alarms_and_cleans_only_its_three_timers(self):
        diagnostic, api, clock = self.make()
        before = copy.deepcopy(api.items[0])
        report = diagnostic.execute(True)
        self.assertEqual(report['result'], 'passed_software_checks', report)
        self.assertLess(report['elapsed_seconds'], 120)
        self.assertEqual(api.items[0], before)
        self.assertEqual(len(api.items), 4)
        self.assertTrue(all(row['state'] == 'done' for row in api.items))
        self.assertFalse(api.ringing)
        self.assertTrue(all(row['label'].startswith(diagnostic.run_id) for row in api.items[1:]))
        self.assertTrue(all(call[3] == api.csrf for call in api.mutations))
        self.assertEqual([call[2]['tone'] for call in api.mutations if call[1] == '/api/timers/tone'], ['bell', 'chime', 'pulse'])
        durations = [call[2]['seconds'] for call in api.mutations if call[1] == '/api/timers' and call[2]['action'] == 'create']
        self.assertEqual(durations, [8, 4, 4])
        concurrency = next(e for e in report['events'] if e['event'] == 'competing_result')
        self.assertEqual((concurrency['accepted'], concurrency['blocked']), (1, 1))
        self.assertTrue(all(call[1] in ('/api/speakers/test', '/api/speakers/stop', '/api/timers', '/api/timers/tone') for call in api.mutations))

    def test_missing_countdown_configuration_is_explicitly_skipped(self):
        diagnostic, api, _ = self.make(); api.announcements['countdown'] = False
        report = diagnostic.execute(True)
        self.assertEqual(report['result'], 'passed_software_checks')
        self.assertTrue(any(e['event'] == 'countdown_skipped' for e in report['events']))
        creates = [call[2] for call in api.mutations if call[1] == '/api/timers' and call[2]['action'] == 'create']
        self.assertEqual([body['seconds'] for body in creates], [4, 4, 4])

    def test_warm_and_idle_resume_are_real_complete_starts_with_usb_evidence(self):
        diagnostic, api, _ = self.make()
        report = diagnostic.execute(True)
        self.assertEqual(report['result'], 'passed_software_checks')
        self.assertLess(api.starts[1]-api.completions[0], 5)
        self.assertGreaterEqual(api.starts[2]-api.completions[1], 7)
        phases = [(e['event'], e.get('phase')) for e in report['events']]
        self.assertIn(('warm_repeat', 'after'), phases)
        self.assertIn(('idle_resume', 'after'), phases)
        warm = next(e for e in report['events'] if e['event'] == 'warm_repeat' and e['phase'] == 'started')
        self.assertLess(warm['idle_upper_bound_seconds'], 5)
        idle = next(e for e in report['events'] if e['event'] == 'idle_resume' and e['phase'] == 'before')
        self.assertGreaterEqual(idle['quiet_seconds'], 7)
        for event in report['events']:
            if event['event'] in ('warm_repeat', 'idle_resume') and event['phase'] != 'started':
                self.assertEqual(event['usb'][0]['idProduct'], '0b21')
        # All three initial stereo tests finish normally; no stop is interleaved.
        self.assertEqual([c[1] for c in api.mutations[:3]], ['/api/speakers/test']*3)

    def test_slow_warm_preflight_cannot_masquerade_as_a_warm_repeat(self):
        diagnostic, api, clock = self.make()
        def stall(api, path):
            if len(api.starts) == 1 and api.completions and not api.flags.get('stalled'):
                api.flags['stalled'] = True
                clock.sleep(5)
        api.hook = stall
        report = diagnostic.execute(True)
        self.assertEqual(report['reason'], 'warm_repeat_window_missed')
        self.assertEqual(len(api.starts), 1)

    def test_loss_in_each_repeat_phase_prevents_further_audio_starts(self):
        for phase in ('warm_repeat', 'idle_resume'):
            with self.subTest(phase=phase):
                diagnostic, api, _ = self.make()
                def lose(api, path):
                    if any(e['event'] == phase for e in diagnostic.report['events']):
                        api.available = False
                api.hook = lose
                report = diagnostic.execute(True)
                self.assertEqual(report['reason'], 'soundbar_lost')
                self.assertEqual(len(api.starts), 1 if phase == 'warm_repeat' else 2)
                self.assertIn('hardware_after', report)
                self.assertFalse(any(c[1] == '/api/timers/tone' for c in api.mutations))

    def test_188a_loss_immediately_stops_scenarios_but_attempts_owned_cleanup(self):
        diagnostic, api, _ = self.make()
        def lose(api, path):
            if api.mutations:
                api.available = False
        api.hook = lose
        report = diagnostic.execute(True)
        self.assertEqual(report['reason'], 'soundbar_lost')
        self.assertEqual([call[1] for call in api.mutations], ['/api/speakers/test', '/api/speakers/stop'])
        self.assertIn('hardware_after', report)

    def test_account_change_prevents_cleanup_mutations_in_new_account(self):
        diagnostic, api, _ = self.make()
        def switch(api, path):
            if api.mutations:
                api.epoch = 'different-account'
        api.hook = switch
        report = diagnostic.execute(True)
        self.assertEqual(report['reason'], 'session_changed')
        self.assertTrue(report['cleanup_required'])
        self.assertEqual(len(api.mutations), 1)

    def test_volume_change_during_run_aborts_without_reconfiguring(self):
        diagnostic, api, _ = self.make()
        api.hook = lambda a, p: setattr(a, 'volume', 41) if a.mutations else None
        report = diagnostic.execute(True)
        self.assertEqual(report['reason'], 'audio_configuration_changed')
        self.assertEqual(len(api.mutations), 1)

    def test_competing_starts_must_be_rejected_by_actual_app_guard(self):
        diagnostic, api, _ = self.make()
        diagnostic.check(); api.bad_concurrency = True
        with self.assertRaisesRegex(Abort, 'concurrent_start_guard_failed'):
            diagnostic.competing_starts()
        self.assertEqual(len(api.mutations), 2)
        self.assertTrue(diagnostic.cleanup())

    def test_timer_response_loss_can_only_recover_this_runs_unique_creation(self):
        diagnostic, api, _ = self.make(); diagnostic.check()
        request = api.request
        def lost(path, body=None, csrf=None):
            result = request(path, body, csrf)
            if path == '/api/timers' and body['action'] == 'create':
                raise Abort('api_unavailable')
            return result
        api.request = lost
        with self.assertRaisesRegex(Abort, 'api_unavailable'):
            diagnostic.timer('bell', 4)
        self.assertTrue(diagnostic.cleanup())
        self.assertEqual(api.items[0]['state'], 'done')
        self.assertEqual(api.items[1]['state'], 'cancelled')
        self.assertEqual([c[2]['id'] for c in api.mutations if c[1] == '/api/timers' and c[2]['action'] == 'cancel'], ['test-timer-1'])

    def test_fresh_global_check_blocks_start_when_playback_begins_between_checks(self):
        diagnostic, api, _ = self.make(); diagnostic.check()
        api.flags['playback_active'] = True
        with self.assertRaisesRegex(Abort, 'unsafe_playback_active'):
            diagnostic.post('/api/speakers/test', {})
        self.assertEqual(api.mutations, [])

    def test_rejected_start_does_not_claim_or_stop_another_operators_tone(self):
        diagnostic, api, _ = self.make()
        original = api.request
        def other_operator_starts(path, body=None, csrf=None):
            api.test = {'state': 'running', 'kind': 'test', 'device': SINK}
            api.until = api.clock()+3
            return original(path, body, csrf)
        api.request = other_operator_starts
        report = diagnostic.execute(True)
        self.assertEqual(report['reason'], 'mutation_rejected')
        self.assertFalse(diagnostic.own_audio)
        self.assertEqual([c[1] for c in api.mutations], ['/api/speakers/test'])

    def test_rejected_stop_is_not_reported_as_success(self):
        diagnostic, api, _ = self.make(); api.reject_stop = True
        report = diagnostic.execute(True)
        self.assertEqual(report['result'], 'aborted')
        self.assertTrue(report['cleanup_required'])
        self.assertTrue(any(e['event'] == 'cleanup_incomplete' for e in report['events']))

    def test_report_is_private_and_does_not_leave_temp_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'result.json'
            write_report(path, {'result': 'aborted', 'reason': 'soundbar_lost'})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())['reason'], 'soundbar_lost')
            self.assertEqual(list(Path(folder).iterdir()), [path])


class ApiBoundaryTests(unittest.TestCase):
    def test_only_numeric_loopback_no_credentials_no_redirects(self):
        for url in ('https://127.0.0.1:8088', 'http://127.0.0.1:8088/x', 'http://example.com:8088',
                    'http://user:pass@127.0.0.1:8088', 'http://127.0.0.1:8088?token=secret',
                    'http://127.0.0.1', 'http://localhost:8088'):
            with self.subTest(url=url), self.assertRaises(Abort):
                Api(url)
        self.assertEqual(Api('http://[::1]:8088').base, 'http://[::1]:8088')
        self.assertIsNone(NoRedirect().redirect_request(None, None, None, None, None, None))

    def test_normal_csrf_and_origin_are_used_without_authorization_bypass(self):
        response = Mock(code=200)
        response.read.return_value = b'{"state":"running"}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(); opener.open.return_value = response
        with patch('urllib.request.build_opener', return_value=opener):
            Api().request('/api/speakers/test', {}, 'csrf-example')
        req = opener.open.call_args.args[0]
        self.assertEqual(req.get_header('X-csrf-token'), 'csrf-example')
        self.assertEqual(req.get_header('Origin'), 'http://127.0.0.1:8088')
        self.assertIsNone(req.get_header('Authorization'))
        with self.assertRaisesRegex(Abort, 'csrf_missing'):
            Api().request('/api/speakers/test', {})
        with self.assertRaisesRegex(Abort, 'route_not_permitted'):
            Api().request('/api/speakers/recover', {'confirm': True}, 'csrf-example')

    def test_kernel_evidence_keeps_error_timing_but_not_arbitrary_names(self):
        rows = [
            {'MESSAGE': 'xhci_hcd 0001:01:00.0: xHCI host controller not responding, assume dead', '__REALTIME_TIMESTAMP': '123456'},
            {'MESSAGE': 'usb 1-1.4: USB disconnect, device number 3', '__REALTIME_TIMESTAMP': '123457'},
            {'MESSAGE': 'usb 1-1.4: Product: PRIVATE_PERSON_SECRET_TOKEN', '__REALTIME_TIMESTAMP': '123458'},
        ]
        def command(args, **kwargs):
            return Mock(returncode=0, stdout=json.dumps([{'name': SINK, 'state': 'RUNNING', 'mute': False,
                'description': 'PRIVATE_ACCOUNT', 'volume': {'left': {'value': 20000}}}]) if args[0] == 'pactl'
                else '\n'.join(json.dumps(row) for row in rows))
        with patch('subprocess.run', side_effect=command), patch.object(Path, 'glob', return_value=[]), \
             patch.object(Path, 'read_text', return_value=' 1 [AUDIO ]: USB-Audio - 188A\n'):
            result = hardware_snapshot('2026-11-24T12:00:00+00:00')
        self.assertEqual([e['event'] for e in result['kernel_events']], ['controller_dead', 'disconnect'])
        self.assertEqual(result['kernel_events'][0]['timestamp_us'], '123456')
        self.assertTrue(result['alsa'][0]['soundbar_188a'])
        self.assertNotIn('PRIVATE', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
