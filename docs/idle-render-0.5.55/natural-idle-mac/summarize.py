"""Summarize one bounded local browser observation; never declares Pi acceptance."""
import hashlib
import json
from pathlib import Path
import statistics
import sys

root = Path(sys.argv[1])
init = json.loads((root / 'init.json').read_text())
rows = [json.loads(line) for line in (root / 'samples.jsonl').read_text().splitlines() if line]
processes = [json.loads(line) for line in (root / 'process-memory.jsonl').read_text().splitlines() if line]
assert rows and all(b['at'] > a['at'] for a, b in zip(rows, rows[1:])), 'Missing or unordered samples'
start = init['startedAt'] / 1000
first, last = rows[0]['at'] / 1000, rows[-1]['at'] / 1000
processes = [row for row in processes if start <= row['at_epoch'] <= last]

def metric(values, factor=1):
    values = [value / factor for value in values]
    return {key: round(value, 4) for key, value in {
        'first': values[0], 'last': values[-1], 'minimum': min(values), 'maximum': max(values),
        'first_five_median': statistics.median(values[:5]),
        'last_five_median': statistics.median(values[-5:]),
    }.items()}

gaps = [(b['at'] - a['at']) / 1000 for a, b in zip(rows, rows[1:])]
report = {
    'scope': 'Local synthetic Mac preview, natural GC; no Pi, cloud or acoustic acceptance',
    'planned_seconds': 1800, 'elapsed_from_ready_seconds': round(last - start, 3),
    'first_sample_delay_seconds': round(first - start, 3), 'sample_count': len(rows),
    'largest_sample_gap_seconds': round(max(gaps, default=0), 3),
    'observation_window_complete': last - start >= 1800 and first - start <= 90 and max(gaps, default=0) <= 90,
    'overall_goal_complete': False,
    'preview_backend_version': init['backendVersion'],
    'frontend_hashes': json.loads((root / 'source-hashes.json').read_text()),
    'browser_versions': sorted({row['browser']['product'] for row in rows}),
    'all_samples_visible_and_listening': all(row['page']['hidden'] is False and row['page']['wakeState'] == 'listening' for row in rows),
    'heap_mib': {key: metric([row['heap'][key] for row in rows], 1024 ** 2)
                 for key in ('usedSize', 'totalSize', 'embedderHeapUsedSize', 'backingStorageSize')},
    'dom': {key: metric([row['dom'][key] for row in rows]) for key in ('documents', 'nodes', 'jsEventListeners')},
    'attached_elements': metric([row['page']['attachedNodes'] for row in rows]),
    'limitations': [
        'Chrome on Mac differs from Chromium on Pi; synthetic fixture has three recordings.',
        'One-minute samples cannot prove absence of shorter spikes or memory leaks.',
        'Natural GC cycles are not equivalent to retained-heap snapshots after explicit GC.',
        'RSS includes allocator and browser caches; it is not a count of retained JavaScript objects.',
        'Playwright driver RSS is separate and excluded from browser RSS.',
        'OS samples cover their stated interval only; PID reuse is not independently excluded.',
        'Process RSS sums may count shared pages more than once.',
    ],
    'source_sha256': {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                      for name in ('init.json', 'source-hashes.json', 'samples.jsonl', 'process-memory.jsonl')},
}
if processes:
    a, b = processes[0], processes[-1]
    report['os_samples'] = {
        'count': len(processes), 'first_elapsed_seconds': round(a['at_epoch'] - start, 3),
        'last_elapsed_seconds': round(b['at_epoch'] - start, 3),
        'browser_rss_mib': metric([row['browser_rss_kib'] for row in processes], 1024),
        'same_pid_sets': all({p['pid'] for p in row['processes']} == {p['pid'] for p in a['processes']} for row in processes),
        'process_changes': [
            {'pid': p['pid'], 'name': p['name'], 'driver_excluded_from_browser_rss': p['pid'] == b['driver_pid'],
             'first_rss_mib': round(old['rss_kib']/1024, 3), 'last_rss_mib': round(p['rss_kib']/1024, 3)}
            for p in b['processes'] for old in a['processes'] if p['pid'] == old['pid']
        ],
    }
print(json.dumps(report, indent=2))
