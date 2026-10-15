"""Validate a completed debugger-free local browser diagnostic, not Pi acceptance."""
import argparse
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(root):
    root = Path(root)
    names = ('plan.json', 'process-memory.jsonl', 'sampler-complete.json',
             'cleanup.json', 'proxy-counters.json')
    raw = {name: (root / name).read_bytes() for name in names}
    plan = json.loads(raw['plan.json'])
    rows = [json.loads(line) for line in raw['process-memory.jsonl'].splitlines()]
    complete = json.loads(raw['sampler-complete.json'])
    cleanup = json.loads(raw['cleanup.json'])
    proxy = json.loads(raw['proxy-counters.json'])
    duration = plan['planned_seconds']
    require(duration >= 1800, 'At least 30 real minutes are required for this comparison')
    require(complete.get('completed') is True, 'Sampler has not completed')
    require(cleanup.get('closed') is True and cleanup.get('completed_observation') is True
            and cleanup.get('proxy_thread_stopped') is True
            and not cleanup.get('remaining_processes'), 'Cleanup is incomplete')
    require(not proxy['errors'], 'Proxy errors require investigation')
    require(len(rows) >= 2, 'Not enough samples')
    require(0 <= rows[0]['elapsed_seconds'] <= 5, 'Initial sample missing')
    require(duration <= rows[-1]['elapsed_seconds'] <= duration + 90,
            'Observation did not cover the planned interval')
    require(abs(complete['elapsed_seconds'] - rows[-1]['elapsed_seconds']) < 1,
            'Completion does not match the last sample')
    require(complete['at_epoch'] >= rows[-1]['at_epoch']
            and cleanup['at_epoch'] >= complete['at_epoch'], 'Invalid completion order')
    root_pid = plan['browser_pid']
    active_sets = []
    identity_present = ['started_at' in p for row in rows for p in row['processes']]
    require(all(identity_present) or not any(identity_present),
            'Process start identities are only partially recorded')
    with_start_identity = all(identity_present)
    observed_starts = {}
    for row in rows:
        require(row['root_pid'] == root_pid, 'Browser root changed')
        processes = row['processes']
        ids = [p['pid'] for p in processes]
        if with_start_identity:
            for process in processes:
                start = process['started_at']
                require(isinstance(start, str) and bool(start.strip()),
                        'Invalid process start identity')
                previous = observed_starts.setdefault(process['pid'], start)
                require(start == previous, 'Process start identity changed for a reused PID')
        require(len(ids) == len(set(ids)) and root_pid in ids, 'Invalid process census')
        require(all(p['rss_kib'] >= 0 for p in processes), 'Negative RSS')
        require(sum(p['rss_kib'] for p in processes) == row['browser_rss_kib'],
                'RSS total does not match its processes')
        require(all(p['pid'] == root_pid or p['parent'] in ids for p in processes),
                'Unrelated process in browser census')
        require(row['proxy_errors'] == 0, 'A sample contains proxy errors')
        require(abs(row['at_epoch'] - plan['started_at_epoch'] - row['elapsed_seconds']) < 5,
                'Wall clock and monotonic time disagree')
        # A zero-RSS zombie is not an active renderer. Keep it in raw evidence.
        active_sets.append({p['pid'] for p in processes if p['name'] != '<defunct>'})
        require(all(p['rss_kib'] == 0 for p in processes if p['name'] == '<defunct>'),
                'Unexpected resident defunct process')
    for a, b in zip(rows, rows[1:]):
        require(0 < b['elapsed_seconds'] - a['elapsed_seconds'] <= 90,
                'Missing or unordered measurement interval')
        for endpoint in ('/api/state', '/api/wake/status'):
            require(b['request_counts'].get(endpoint, 0) > a['request_counts'].get(endpoint, 0),
                    'Expected application polling stopped')
    measured = [(row, ids) for row, ids in zip(rows, active_sets) if row['elapsed_seconds'] >= 120]
    require(len(measured) >= 2, 'No interval after warmup')
    require(all(ids == measured[0][1] for _, ids in measured),
            'Active browser process set changed after warmup')
    a, b = measured[0][0], measured[-1][0]
    old = {p['pid']: p for p in a['processes']}
    return {
        'scope': plan['scope'], 'overall_goal_complete': False,
        'completed_local_observation': True, 'chrome_version': plan['chrome_version'],
        'process_identity_check': 'pid_and_os_start_time' if with_start_identity else 'pid_only',
        'preview_backend_version': plan['preview_backend_version'],
        'frontend_hashes': plan['frontend_hashes'], 'sample_count': len(rows),
        'elapsed_seconds': rows[-1]['elapsed_seconds'],
        'os_warmup_excluded_before_seconds': 120,
        'os_interval_seconds_from_ready': [a['elapsed_seconds'], b['elapsed_seconds']],
        'browser_rss_mib': [a['browser_rss_kib'] / 1024, b['browser_rss_kib'] / 1024],
        'browser_rss_delta_mib': (b['browser_rss_kib'] - a['browser_rss_kib']) / 1024,
        'process_deltas_mib': [
            {'pid': p['pid'], 'role': p['name'],
             'delta_mib': (p['rss_kib'] - old[p['pid']]['rss_kib']) / 1024}
            for p in b['processes'] if p['name'] != '<defunct>'],
        'limits': plan['limitations'] + [
            'Different flags and HTTP proxy from instrumented runs: not an exact causal A/B comparison.',
            ('PID and reported OS start time are checked; timestamp resolution limits identity precision.'
             if with_start_identity else 'PID membership is checked, but process start times were not collected.'),
            'Successful API polling does not verify visible UI, wake recognition or cloud connection.'],
        'source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(summarize(parser.parse_args().directory), indent=2))
