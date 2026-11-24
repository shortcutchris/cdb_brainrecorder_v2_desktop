#!/usr/bin/env python3
"""Explicit, bounded USB soundbar exercise through the running Studio API.

Run as the normal Pi application user, with the device signed in and operator
settings unlocked. Select the 188A output and a comfortable volume beforehand.
Keep the device exclusively for this test until the report is written.

    python3 scripts/diagnose_usb_audio.py --output /tmp/usb-audio-check.json
    python3 scripts/diagnose_usb_audio.py --run --output /tmp/usb-audio-run.json

Without --run only read-only preflight/diagnostics occur. A run normally takes
about 2 minutes: stereo warm/idle repeats, all three alarm sounds, repeated start/stop,
short real timers, concurrent-start rejection, and an idle observation period.
Existing local timer announcements remain enabled if configured. No microphone
test/recording, cloud request, audio configuration, recovery or reboot is issued.
The API needs /api/speakers/diagnostic-status; missing safety data fails closed.

The report proves software/device observations, not that a person heard sound.
There is no API playback ownership token: do not start another manual sound test
during this explicitly supervised run. Other detected activity aborts the run.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


OPEN_STATES = {'scheduled', 'due', 'missed'}
TONES = ('bell', 'chime', 'pulse')
BUSY_ERRORS = {'Lautsprechertest läuft.', 'Audioausgabe läuft bereits.'}
SINK_PATTERN = re.compile(r'alsa_output\.usb-0020_188A_[A-Za-z0-9_.-]+')
MAX_SECONDS = 150


class Abort(RuntimeError):
    """A fixed, non-sensitive reason code safe to put in the report."""


@dataclass
class Reply:
    status: int
    data: dict


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Api:
    def __init__(self, base='http://127.0.0.1:8088'):
        url = urllib.parse.urlsplit(base)
        if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', '::1') or
                url.username or url.password or url.path not in ('', '/') or
                url.query or url.fragment or not url.port):
            raise Abort('loopback_url_required')
        self.base = base.rstrip('/')

    def request(self, path, body=None, csrf=None):
        if path not in ('/api/state', '/api/speakers/diagnostic-status',
                        '/api/speakers/test', '/api/speakers/stop',
                        '/api/timers/tone', '/api/timers'):
            raise Abort('route_not_permitted')
        headers = {'Accept': 'application/json'}
        if body is not None:
            if not csrf:
                raise Abort('csrf_missing')
            headers.update({'Content-Type': 'application/json',
                            'X-CSRF-Token': csrf, 'Origin': self.base})
        request = urllib.request.Request(self.base + path, headers=headers,
            data=None if body is None else json.dumps(body).encode())
        # Ignore proxy environment variables: tokens never leave loopback. Each
        # concurrent caller has its own opener; redirects are never followed.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            try:
                response = opener.open(request, timeout=4)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise Abort('api_response_too_large')
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise Abort('api_response_invalid')
                return Reply(response.code, data)
        except Abort:
            raise
        except (OSError, ValueError, urllib.error.URLError):
            # Never include URL, headers, body, token or account data in errors.
            raise Abort('api_unavailable') from None

    def get(self, path):
        reply = self.request(path)
        if reply.status != 200:
            raise Abort('diagnostic_access_denied' if reply.status in (400, 403) else 'diagnostic_endpoint_unavailable')
        return reply.data


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def usb_inventory():
    """Fast sysfs-only evidence, so collecting it does not cause a suspend gap."""
    devices = []
    for entry in sorted(Path('/sys/bus/usb/devices').glob('*')):
        if not re.fullmatch(r'(?:usb\d+|\d+-[\d.]+)', entry.name):
            continue
        item = {'port': entry.name}
        for key in ('idVendor', 'idProduct', 'busnum', 'devnum', 'speed', 'authorized'):
            try:
                value = (entry/key).read_text().strip()
                if re.fullmatch(r'[0-9a-fA-F.]{1,12}', value):
                    item[key] = value
            except OSError:
                pass
        if 'idVendor' in item:
            devices.append(item)
    return devices


def hardware_snapshot(since):
    """Read-only, bounded, whitelist-only Linux evidence; no sudo or raw dumps."""
    result = {'captured_at': utc_now(), 'usb': usb_inventory(), 'alsa': [], 'sinks': [], 'kernel_events': []}
    try:
        for line in Path('/proc/asound/cards').read_text().splitlines():
            match = re.match(r'\s*(\d+) \[', line)
            if match:
                result['alsa'].append({'card': int(match[1]), 'soundbar_188a': '188A' in line,
                                       'usb_audio': 'USB-Audio' in line})
    except OSError:
        result['alsa_unavailable'] = True

    def command(args):
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
            return proc.stdout if proc.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None

    raw = command(['pactl', '-f', 'json', 'list', 'sinks'])
    try:
        sinks = json.loads(raw) if raw else []
        for sink in sinks:
            volume = sink.get('volume', {})
            result['sinks'].append({
                'soundbar_188a': bool(SINK_PATTERN.fullmatch(sink.get('name', ''))),
                'state': sink.get('state') if sink.get('state') in ('RUNNING', 'IDLE', 'SUSPENDED') else 'unknown',
                'muted': sink.get('mute') is True,
                'volumes': [v.get('value') for v in volume.values() if type(v.get('value')) is int],
            })
    except (ValueError, TypeError, AttributeError):
        result['sink_read_failed'] = True
    if raw is None:
        result['sink_read_failed'] = True

    raw = command(['journalctl', '-k', '-b', '--since', since, '--no-pager', '-n', '3000', '-o', 'json'])
    if raw is None:
        result['kernel_read_failed'] = True
    else:
        # Keep technical bus/error events, never product strings, serials or
        # arbitrary device-provided names. Preserve journal time for correlation.
        patterns = (
            ('controller_dead', r'(?:xHCI host controller not responding|HC died)'),
            ('endpoint_timeout', r'Timeout while waiting for configure endpoint command'),
            ('bandwidth_error', r'Not enough bandwidth for altsetting\s*\d*'),
            ('interface_error', r'usb_set_interface failed\s*\(-?\d+\)'),
            ('disconnect', r'USB disconnect, device number \d+'),
            ('connect', r'new (?:low|full|high|super|SuperSpeed)[- a-zA-Z]*speed USB device number \d+'),
            ('usb_error', r'(?:device descriptor read/\d+, error -?\d+|unable to enumerate USB device|Cannot enable\. Maybe the USB cable is bad\?|reset (?:high|full|low|SuperSpeed)[- a-zA-Z]*speed USB device number \d+)'),
        )
        for line in raw.splitlines():
            try:
                row = json.loads(line)
                message = row.get('MESSAGE', '')
                if not isinstance(message, str) or not re.match(r'(?:usb\s|xhci_hcd\s)', message):
                    continue
                for name, pattern in patterns:
                    match = re.search(pattern, message)
                    if match:
                        prefix = re.match(r'(?:usb\s[0-9.:-]+|xhci_hcd\s[0-9a-f:.]+)', message)
                        stamp = row.get('__REALTIME_TIMESTAMP', '')
                        result['kernel_events'].append({'event': name, 'bus': prefix[0] if prefix else '',
                            'detail': match[0], 'timestamp_us': stamp if str(stamp).isdigit() else None})
                        break
            except (ValueError, TypeError, AttributeError):
                continue
        result['kernel_events'] = result['kernel_events'][-300:]
    return result


class Diagnostic:
    def __init__(self, api, *, clock=time.monotonic, sleep=time.sleep, collect=hardware_snapshot,
                 collect_usb=usb_inventory):
        self.api, self.clock, self.sleep, self.collect = api, clock, sleep, collect
        self.collect_usb = collect_usb
        self.started = clock()
        self.started_at = utc_now()
        self.run_id = 'USB-AUDIO-DIAG-' + uuid.uuid4().hex[:12]
        self.epoch = self.sink = self.volume = self.csrf = None
        self.own_audio = False
        self.own_cooldown = False
        self.audio_started_at = None
        self.timer_labels = {}
        self.own_timers = set()
        self.lock = threading.Lock()
        self.report = {'schema': 1, 'run_id': self.run_id, 'started_at': self.started_at,
                       'heard_by_person': None, 'events': [], 'snapshots': []}

    def event(self, name, **fields):
        with self.lock:
            self.report['events'].append({'event': name, 'at': utc_now(),
                'elapsed_seconds': round(self.clock()-self.started, 3), **fields})

    def snapshot(self):
        # The final read is the global, locked safety snapshot including route.
        state = self.api.get('/api/state')
        status = self.api.get('/api/speakers/diagnostic-status')
        speakers = status.get('speakers', {})
        items = state.get('timers', {}).get('items')
        if not isinstance(items, list) or not isinstance(speakers, dict):
            raise Abort('safety_status_missing')
        # Recover only our unique creation labels if the create reply was lost.
        for item in items:
            if (isinstance(item, dict) and item.get('label') in self.timer_labels and
                    item.get('kind') == 'timer' and item.get('tone') == self.timer_labels[item['label']] and
                    isinstance(item.get('id'), str)):
                self.own_timers.add(item['id'])
        with self.lock:
            self.report['snapshots'].append({
                'at': utc_now(), 'elapsed_seconds': round(self.clock()-self.started, 3),
                'available': speakers.get('available') is True,
                'selected_188a': bool(SINK_PATTERN.fullmatch(str(speakers.get('selected', '')))),
                'selected_unchanged': self.sink is None or speakers.get('selected') == self.sink,
                'volume': speakers.get('volume') if type(speakers.get('volume')) is int else None,
                'muted': speakers.get('muted') is True,
                'speaker_state': self.safe_state(speakers.get('test', {}).get('state')),
                'open_timer_count': status.get('open_timer_count') if type(status.get('open_timer_count')) is int else None,
            })
        return state, status, speakers

    @staticmethod
    def safe_state(value):
        return value if value in ('idle', 'running', 'completed', 'failed', 'cancelled') else 'unknown'

    def check(self, *, own_allowed=False, cleanup=False):
        state, status, speakers = self.snapshot()
        if not cleanup and self.clock()-self.started > MAX_SECONDS:
            raise Abort('run_deadline')
        if status.get('preview') is not False:
            raise Abort('hardware_app_required')
        if status.get('signed_in') is not True:
            raise Abort('sign_in_required')
        epoch, csrf = status.get('account_epoch'), status.get('csrf')
        if not isinstance(epoch, str) or not epoch or not isinstance(csrf, str) or not csrf:
            raise Abort('safety_status_missing')
        if self.epoch is None:
            self.epoch, self.csrf = epoch, csrf
        if self.epoch != epoch or self.csrf != csrf or state.get('room', {}).get('epoch') != epoch:
            raise Abort('session_changed')
        for flag in ('pending_processing', 'playback_active', 'pending_login', 'pending_intent'):
            if status.get(flag) is not False:
                raise Abort('unsafe_' + flag)
        activity = status.get('activity', {})
        if activity.get('recording') is not False or activity.get('live_busy') is not False:
            raise Abort('other_audio_activity')
        own_items = [i for i in state['timers']['items'] if i.get('id') in self.own_timers and i.get('state') in OPEN_STATES]
        cooldown = status.get('output_cooldown_active')
        if type(cooldown) is not bool or (cooldown and not (own_allowed and
                (self.own_audio or self.own_cooldown or own_items))):
            raise Abort('unsafe_output_cooldown')
        count = status.get('open_timer_count')
        if type(count) is not int or count != len(own_items):
            raise Abort('unowned_open_timers')
        ringing = status.get('ringing_id')
        if ringing is not None and ringing not in self.own_timers:
            raise Abort('unowned_alarm')
        countdown = status.get('countdown_active')
        if type(countdown) is not bool or (countdown and not (own_allowed and len(own_items) == 1)):
            raise Abort('unowned_countdown')
        test = speakers.get('test', {})
        own_running = own_allowed and test.get('state') == 'running' and (
            (self.own_audio and test.get('kind') == 'test') or
            (ringing in self.own_timers and test.get('kind') == 'alarm') or
            (countdown and len(own_items) == 1 and test.get('kind') == 'announcement'))
        if type(status.get('output_busy')) is not bool or (status['output_busy'] and not own_running):
            raise Abort('unsafe_output_busy')
        if not ((activity.get('mode') == 'idle' and activity.get('busy') is False and test.get('state') != 'running') or
                (own_running and activity.get('mode') in ('speaker-test', 'alarm') and activity.get('busy') is True)):
            raise Abort('device_not_idle')
        selected = speakers.get('selected')
        if not isinstance(selected, str) or not SINK_PATTERN.fullmatch(selected):
            raise Abort('select_188a_first')
        if self.sink is None:
            self.sink, self.volume = selected, speakers.get('volume')
        if selected != self.sink or speakers.get('volume') != self.volume or speakers.get('muted') is not False:
            raise Abort('audio_configuration_changed')
        if not cleanup and (speakers.get('available') is not True or not any(d.get('id') == self.sink for d in speakers.get('devices', []))):
            raise Abort('soundbar_lost')
        if not cleanup and (type(self.volume) is not int or self.volume <= 0):
            raise Abort('audible_volume_required')
        if not cleanup and own_running and test.get('device') != self.sink:
            raise Abort('playback_route_changed')
        return state, status, speakers

    def post(self, path, body, *, own_allowed=False, cleanup=False, before=None):
        _, status, _ = self.check(own_allowed=own_allowed, cleanup=cleanup)
        if before is not None and self.clock() >= before:
            raise Abort('warm_repeat_window_missed')
        reply = self.api.request(path, body, status['csrf'])
        self.event('request', route=path, http_status=reply.status)
        if reply.status != 200:
            raise Abort('mutation_rejected')
        return reply.data

    def observe(self, seconds, *, own_allowed=False):
        until = self.clock() + seconds
        while self.clock() < until:
            self.check(own_allowed=own_allowed)
            self.sleep(min(.4, until-self.clock()))

    def finish_audio(self, *, require_completed=False):
        until = self.clock() + 10
        last_running = self.audio_started_at
        ended_observed = None
        while self.clock() < until:
            checked_at = self.clock()
            _, status, speakers = self.check(own_allowed=True)
            state = speakers['test'].get('state')
            if state == 'running':
                # A conservative lower bound: the server's running snapshot
                # was taken no earlier than the beginning of this read.
                last_running = checked_at
            else:
                if state not in ('completed', 'cancelled'):
                    raise Abort('playback_failed')
                if require_completed and state != 'completed':
                    raise Abort('playback_did_not_complete')
                if ended_observed is None:
                    ended_observed = self.clock()
                if not status['output_cooldown_active']:
                    self.own_audio = self.own_cooldown = False
                    return {'last_running_at': last_running, 'ended_observed_at': ended_observed}
            self.sleep(.4)
        raise Abort('playback_timeout')

    def start(self, tone=None, *, before=None):
        path = '/api/speakers/test' if tone is None else '/api/timers/tone'
        # Only a confirmed start is ours. An ambiguous network failure never
        # authorizes stopping someone else's test; these tones expire in 3 s.
        started_at = self.clock()
        data = self.post(path, {} if tone is None else {'tone': tone}, before=before)
        if data.get('state') != 'running' or data.get('device') != self.sink:
            raise Abort('start_not_confirmed')
        self.own_audio = True
        self.audio_started_at = started_at

    def stereo_repeats(self, first_completion):
        last_running = first_completion['last_running_at']
        if last_running is None:
            raise Abort('warm_repeat_window_unknown')
        self.event('warm_repeat', phase='before', usb=self.collect_usb(),
                   max_idle_seconds=5)
        # The deadline is measured from the last confirmed running read, not
        # from completion-plus-cooldown; this deliberately errs on the safe side.
        self.start(before=last_running+5)
        if self.clock() >= last_running+5:
            raise Abort('warm_repeat_window_missed')
        self.event('warm_repeat', phase='started',
                   idle_upper_bound_seconds=round(self.clock()-last_running, 3))
        self.finish_audio(require_completed=True)
        self.event('warm_repeat', phase='after', usb=self.collect_usb())
        self.check()
        self.event('idle_resume', phase='idle', seconds=7, usb=self.collect_usb())
        idle_at = self.clock()
        self.observe(7)
        self.event('idle_resume', phase='before', usb=self.collect_usb(),
                   quiet_seconds=round(self.clock()-idle_at, 3))
        self.start()
        self.finish_audio(require_completed=True)
        self.event('idle_resume', phase='after', usb=self.collect_usb())
        self.check()

    def timer(self, tone, seconds):
        label = self.run_id + '-' + tone
        self.timer_labels[label] = tone
        self.event('timer_start', tone=tone, duration_seconds=seconds)
        data = self.post('/api/timers', {'action': 'create', 'kind': 'timer', 'label': label,
                         'request_id': str(uuid.uuid4()), 'seconds': seconds, 'tone': tone})
        if not isinstance(data.get('id'), str):
            raise Abort('timer_create_unconfirmed')
        ident = data['id']
        self.own_timers.add(ident)
        until = self.clock() + seconds + 12
        alarm_at = None
        while self.clock() < until:
            state, status, _ = self.check(own_allowed=True)
            row = next((i for i in state['timers']['items'] if i.get('id') == ident), None)
            if not row or row.get('state') not in OPEN_STATES:
                raise Abort('test_timer_changed')
            if row.get('sound') in ('failed', 'interrupted', 'silent'):
                raise Abort('timer_audio_failed')
            if status.get('ringing_id') == ident:
                alarm_at = alarm_at or self.clock()
                if self.clock()-alarm_at >= 1.2:
                    self.change_timer(ident)
                    self.own_cooldown = True
                    self.finish_audio()
                    self.event('timer_acknowledged', tone=tone)
                    return
            self.sleep(.4)
        raise Abort('timer_alarm_timeout')

    def change_timer(self, ident, *, cleanup=False):
        state, status, _ = self.check(own_allowed=True, cleanup=cleanup)
        row = next((i for i in state['timers']['items'] if i.get('id') == ident), None)
        if not row or row.get('state') not in OPEN_STATES:
            return
        if ident not in self.own_timers or row.get('label') not in self.timer_labels:
            raise Abort('timer_ownership_changed')
        # Use the just-read revision; a concurrent user change fails normally.
        body = {'action': 'cancel' if row['state'] == 'scheduled' else 'ack',
                'id': ident, 'revision': row['revision']}
        reply = self.api.request('/api/timers', body, status['csrf'])
        self.event('timer_cleanup' if cleanup else 'timer_finish', http_status=reply.status,
                   action=body['action'])
        if reply.status != 200:
            raise Abort('timer_cleanup_rejected')

    def competing_starts(self):
        self.event('competing_starts')
        gate = threading.Barrier(2, timeout=8)

        def contender():
            try:
                _, status, _ = self.check()
                gate.wait()
                return self.api.request('/api/speakers/test', {}, status['csrf'])
            except Exception:
                gate.abort()
                raise

        # A fresh global check in each worker precedes the synchronized POST.
        # Only the app's own atomic guard decides which request may start audio.
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(contender) for _ in range(2)]
            replies, failed = [], False
            for future in futures:
                try:
                    replies.append(future.result())
                except Exception:
                    failed = True
        accepted = [r for r in replies if r.status == 200 and r.data.get('state') == 'running' and r.data.get('device') == self.sink]
        self.own_audio = bool(accepted)
        blocked = [r for r in replies if r.status in (400, 409) and r.data.get('error') in BUSY_ERRORS]
        self.event('competing_result', accepted=len(accepted), blocked=len(blocked),
                   http_statuses=sorted(r.status for r in replies))
        if failed or len(accepted) != 1 or len(blocked) != 1:
            raise Abort('concurrent_start_guard_failed')
        self.finish_audio()

    def cleanup(self):
        try:
            # Includes timers whose response was lost; only this run's unique
            # labels are adopted. A different account/activity is never changed.
            _, _, speakers = self.check(own_allowed=True, cleanup=True)
            for ident in sorted(self.own_timers):
                self.change_timer(ident, cleanup=True)
            if self.own_audio and speakers.get('test', {}).get('state') == 'running':
                self.post('/api/speakers/stop', {}, own_allowed=True, cleanup=True)
                self.own_audio = False
            self.event('cleanup_complete')
            return True
        except Abort as error:
            self.event('cleanup_incomplete', reason=str(error), test_timer_ids=sorted(self.own_timers))
            return False

    def execute(self, run=False):
        self.report['run_requested'] = run
        try:
            state, _, _ = self.check()
            announcements = state.get('announcements', {})
            self.report['timer_announcements'] = {k: announcements.get(k) is True
                for k in ('ready', 'timers', 'countdown', 'countdown_ready')}
            self.report['hardware_before'] = self.collect(self.started_at)
            if not run:
                self.report['result'] = 'preflight_ready'
            else:
                self.event('stereo_test'); self.start()
                first_completion = self.finish_audio(require_completed=True)
                self.stereo_repeats(first_completion)
                for tone in TONES:
                    self.event('tone_test', tone=tone); self.start(tone); self.finish_audio()
                for index in range(6):
                    self.event('start_stop', cycle=index+1)
                    self.start(); self.observe(1, own_allowed=True)
                    self.post('/api/speakers/stop', {}, own_allowed=True)
                    self.finish_audio(); self.observe(.4)
                countdown = announcements.get('countdown_ready') is True and announcements.get('countdown') is True
                if not countdown:
                    self.event('countdown_skipped', reason='not_configured')
                for index, tone in enumerate(TONES):
                    self.timer(tone, 8 if countdown and index == 0 else 4)
                self.competing_starts()
                self.event('idle_observation', seconds=30); self.observe(30)
                self.report['result'] = 'passed_software_checks'
        except Abort as error:
            self.report.update(result='aborted', reason=str(error))
            self.event('abort', reason=str(error))
        except KeyboardInterrupt:
            self.report.update(result='interrupted', reason='operator_interrupt')
        except Exception:
            self.report.update(result='aborted', reason='unexpected_error')
        finally:
            if run and (self.own_audio or self.timer_labels):
                if not self.cleanup():
                    self.report['cleanup_required'] = True
                    if self.report.get('result') == 'passed_software_checks':
                        self.report.update(result='aborted', reason='cleanup_incomplete')
            try:
                self.report['hardware_after'] = self.collect(self.started_at)
            except Exception:
                self.report['hardware_after'] = {'collection_failed': True}
            self.report['finished_at'] = utc_now()
            self.report['elapsed_seconds'] = round(self.clock()-self.started, 3)
        return self.report


def write_report(path, report):
    path = Path(path).expanduser().absolute()
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run', action='store_true', help='Play synthetic/local test sounds and create only marked test timers.')
    parser.add_argument('--output', type=Path, required=True, help='JSON report path (written with private file permissions).')
    parser.add_argument('--base-url', default='http://127.0.0.1:8088', help='Numeric loopback address of the real Studio app.')
    args = parser.parse_args(argv)
    try:
        api = Api(args.base_url)
    except (Abort, ValueError):
        parser.error('Use an HTTP numeric loopback URL with an explicit port.')
    def interrupted(*_):
        raise KeyboardInterrupt()
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        report = Diagnostic(api).execute(args.run)
        write_report(args.output, report)
    finally:
        signal.signal(signal.SIGTERM, previous)
    print('USB audio diagnostic: ' + report['result'] + '. Report: ' + str(args.output))
    return 0 if report['result'] in ('preflight_ready', 'passed_software_checks') else 1


if __name__ == '__main__':
    raise SystemExit(main())
