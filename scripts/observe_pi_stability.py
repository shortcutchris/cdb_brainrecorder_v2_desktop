#!/usr/bin/env python3
"""Bounded, read-only Pi observation. Never starts/stops audio or any service."""
import argparse
from collections import deque
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shlex
import time
import urllib.request


def utc(stamp=None):
    return datetime.fromtimestamp(time.time() if stamp is None else stamp, timezone.utc).isoformat()


def save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)


def get(path, token=None):
    # Fixed loopback destination; no credentials or response bodies in error logs.
    request = urllib.request.Request('http://127.0.0.1:8088' + path)
    if token:
        request.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.load(response)


def browser_processes(proc=Path('/proc'), profile=None, uid=None):
    profile = profile or str(Path.home() / '.local/share/cdb-recorder-kiosk/browser')
    uid = os.getuid() if uid is None else uid
    all_rows, roots = {}, set()
    for folder in proc.glob('[0-9]*'):
        try:
            if folder.stat().st_uid != uid:
                continue
            fields = (folder / 'stat').read_text().rsplit(')', 1)[1].split()
            argv = [arg for arg in (folder / 'cmdline').read_bytes().split(b'\0') if arg]
            # Debian Chromium rewrites its process title into one space-separated arg.
            if len(argv) == 1:
                argv = [arg.encode() for arg in shlex.split(argv[0].decode(errors='replace'))]
            pid = int(folder.name)
            all_rows[pid] = {'pid': pid, 'ppid': int(fields[1]), 'start': int(fields[19]),
                             'ticks': int(fields[11]) + int(fields[12]),
                             'rss_mb': int(fields[21]) * os.sysconf('SC_PAGE_SIZE') / 1048576,
                             'renderer': b'--type=renderer' in argv}
            if (folder / 'comm').read_text().strip() in ('chromium', 'chromium-brows') and (
                    ('--user-data-dir=' + profile).encode() in argv and not any(arg.startswith(b'--type=') for arg in argv)):
                roots.add(pid)
        except (OSError, ValueError, IndexError):
            continue
    selected = set(roots)
    while True:
        children = {pid for pid, row in all_rows.items() if row['ppid'] in selected}
        if children <= selected:
            break
        selected |= children
    return {pid: all_rows[pid] for pid in selected}, roots


def process_metrics(current, previous, seconds):
    # PID reuse/new browser generations must not produce enormous fake CPU spikes.
    ticks = sum(max(0, row['ticks'] - previous[pid]['ticks']) for pid, row in current.items()
                if pid in previous and row['start'] == previous[pid]['start'])
    return {'processes': len(current), 'renderers': sum(row['renderer'] for row in current.values()),
            'rss_mb': round(sum(row['rss_mb'] for row in current.values()), 2),
            'renderer_rss_mb': round(sum(row['rss_mb'] for row in current.values() if row['renderer']), 2),
            'cpu_percent': round(ticks / os.sysconf('SC_CLK_TCK') / seconds * 100, 2) if previous and seconds > 0 else None}


def resources():
    values = {}
    try:
        mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
        values['available_mb'] = round(mem['MemAvailable'] / 1024, 1)
    except (OSError, ValueError, KeyError):
        pass
    try:
        values['temperature_c'] = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
    except (OSError, ValueError):
        pass
    return values


class Observer:
    def __init__(self, emit):
        self.emit = emit
        self.samples = deque()
        self.alerts = set()
        self.wake_key = None
        self.pending = None
        self.idle_since = None
        self.last_state = None
        self.counts = {'wake_observed': 0, 'wake_connected': 0, 'wake_failed': 0}
        self.last_wake = None
        self.failures = 0
        self.wake_state = None
        self.wake_enabled = None
        self.wake_errors = deque()

    def alert(self, name, active, now, details=None):
        if active and name not in self.alerts:
            self.alerts.add(name)
            self.emit({'type': 'alert', 'code': name, 'at': utc(now), **(details or {})})
        elif not active and name in self.alerts:
            self.alerts.remove(name)
            self.emit({'type': 'recovered', 'code': name, 'at': utc(now)})

    def sample(self, row, now):
        self.samples.append((now, row))
        while self.samples and self.samples[0][0] < now - 3600:
            self.samples.popleft()
        window = [(t, r) for t, r in self.samples if t >= now - 300]
        sustained = len(window) >= 19 and window[-1][0] - window[0][0] >= 270
        idle = sustained and all(r.get('activity') == 'idle' for _, r in window)
        self.alert('browser_cpu_idle_high', idle and all((r['browser'].get('cpu_percent') or 0) >= 80 for _, r in window), now)
        self.alert('browser_memory_high', sustained and all(r['browser']['rss_mb'] >= 1536 for _, r in window), now)
        self.alert('browser_missing', sustained and all(not r['browser']['processes'] for _, r in window), now)
        self.alert('system_memory_low', sustained and all(r.get('available_mb', 99999) < 512 for _, r in window), now)
        self.alert('device_hot', sustained and all(r.get('temperature_c', 0) >= 80 for _, r in window), now)
        short = [(t, r) for t, r in self.samples if t >= now - 120]
        wake_stuck = len(short) >= 8 and short[-1][0] - short[0][0] >= 105 and all(
            r.get('activity') == 'idle' and r.get('wake_enabled') is True and
            r.get('wake_state') in ('loading', 'error') for _, r in short)
        self.alert('wake_not_ready', wake_stuck, now)
        # A rising half-hour trend is useful even before the absolute RAM limit.
        old = next(((t, r) for t, r in reversed(self.samples) if t <= now - 1800), None)
        growing = bool(old and old[1].get('browser_generation') == row.get('browser_generation') and
                       row['browser']['rss_mb'] - old[1]['browser']['rss_mb'] >= 256)
        self.alert('browser_memory_growth', growing, now)

    def poll(self, wake, live, now):
        self.failures = 0
        self.alert('status_unreachable', False, now)
        key = (wake.get('instance'), wake.get('detections'))
        state = live.get('state', 'unknown')
        self.wake_enabled = wake.get('enabled')
        if self.wake_state != wake.get('state'):
            self.wake_state = wake.get('state')
            self.emit({'type': 'wake_state', 'state': self.wake_state, 'at': utc(now)})
            if self.wake_state == 'error': self.wake_errors.append(now)
        while self.wake_errors and self.wake_errors[0] < now - 300:
            self.wake_errors.popleft()
        self.alert('wake_repeated_errors', len(self.wake_errors) >= 3, now)
        if self.last_state != state:
            self.emit({'type': 'live_state', 'at': utc(now), 'state': state})
            self.last_state = state
        if self.wake_key is not None and key[0] != self.wake_key[0]:
            self.emit({'type': 'backend_instance_changed', 'at': utc(now)})
            self.pending = None
        elif self.wake_key is not None and key != self.wake_key:
            self.counts['wake_observed'] += 1
            self.pending = {'detected_at': utc(now), 'detected_epoch': now,
                            'idle_seconds': round(now - self.idle_since, 1) if self.idle_since else None,
                            'count': key[1], 'connected_seconds': None, 'first_output_seconds': None}
            self.emit({'type': 'wake_observed', 'at': utc(now), **self.pending})
            self.alert('wake_connect_slow', False, now)
        self.wake_key = key
        if self.pending:
            elapsed = now - self.pending['detected_epoch']
            if state in ('listening', 'thinking', 'speaking') and self.pending['connected_seconds'] is None:
                self.pending['connected_seconds'] = round(elapsed, 2)
                self.counts['wake_connected'] += 1
                self.emit({'type': 'wake_connected', 'at': utc(now), **self.pending})
            if live.get('output', {}).get('active') and self.pending['first_output_seconds'] is None:
                self.pending['first_output_seconds'] = round(elapsed, 2)
                self.emit({'type': 'wake_first_output', 'at': utc(now), **self.pending})
            self.alert('wake_connect_slow', elapsed >= 15 and self.pending['connected_seconds'] is None, now)
            if state in ('ended', 'error', 'idle') and elapsed >= 3:
                if self.pending['connected_seconds'] is None:
                    self.counts['wake_failed'] += 1
                    self.emit({'type': 'wake_failed', 'at': utc(now), **self.pending})
                self.last_wake = self.pending
                self.pending = None
                self.alert('wake_connect_slow', False, now)
        if wake.get('state') == 'listening' and not live.get('active'):
            if self.idle_since is None:
                self.idle_since = now
        else:
            self.idle_since = None

    def failed(self, now):
        self.failures += 1
        self.alert('status_unreachable', self.failures >= 3, now)


def run(folder, hours):
    os.umask(0o077)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (folder / 'observer.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    plan_path = folder / 'plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    else:
        start = time.time()
        plan = {'start_epoch': start, 'end_epoch': start + hours * 3600,
                'started_at': utc(start), 'ends_at': utc(start + hours * 3600), 'mode': 'observe_only'}
        save(plan_path, plan)
    def emit(event):
        with (folder / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
    observer = Observer(emit)
    token_path = Path.home() / '.local/share/cdb-recorder-local/management/local-auth.json'
    previous, previous_at, next_sample = {}, time.monotonic(), 0
    latest = {}
    emit({'type': 'observer_started', 'at': utc(), 'mode': 'observe_only'})
    while time.time() < plan['end_epoch']:
        tick = time.monotonic()
        now = time.time()
        try:
            wake = get('/api/wake/status')
            live = get('/api/live/activity')
            observer.poll(wake, live, now)
        except (OSError, ValueError):
            observer.failed(now)
        if tick >= next_sample:
            current, roots = browser_processes()
            row = {'at': utc(now), 'browser': process_metrics(current, previous, tick - previous_at),
                   'browser_generation': sorted((pid, current[pid]['start']) for pid in roots),
                   'wake_enabled': observer.wake_enabled, **resources()}
            previous, previous_at, next_sample = current, tick, tick + 15
            try:
                token = json.loads(token_path.read_text())['token']
                start = time.monotonic()
                health = get('/api/management/health', token)
                row.update(activity=health['activity'], version=health['version'],
                           wake_state=health['wake_state'], health_ms=round((time.monotonic() - start) * 1000, 2))
            except (OSError, ValueError, KeyError):
                row.update(activity='unknown', health_ms=None)
            observer.sample(row, now)
            with (folder / 'metrics.jsonl').open('a') as stream:
                stream.write(json.dumps(row) + '\n')
            latest = row
            save(folder / 'status.json', {**plan, 'status': 'running', 'updated_at': utc(),
                 'latest': latest, 'alerts': sorted(observer.alerts), 'counts_since_process_start': observer.counts,
                 'last_wake': observer.pending or observer.last_wake})
        time.sleep(max(0.1, 1 - (time.monotonic() - tick)))
    status = json.loads((folder / 'status.json').read_text()) if (folder / 'status.json').exists() else plan
    save(folder / 'status.json', {**status, 'status': 'complete', 'updated_at': utc()})
    emit({'type': 'observation_complete', 'at': utc()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--hours', type=float, default=24)
    args = parser.parse_args()
    if not 0 < args.hours <= 24:
        parser.error('Duration must be greater than zero and at most 24 hours.')
    run(args.output, args.hours)
