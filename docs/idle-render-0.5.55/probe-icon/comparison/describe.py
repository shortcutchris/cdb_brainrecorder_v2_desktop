"""Describe the completed diagnostic without accepting its failed process-group gate."""
import hashlib
import json
from pathlib import Path
import sys

assert len(sys.argv) == 2 and sys.argv[1] in ('original', 'guarded')
root = Path(__file__).resolve().parent / sys.argv[1]
repo = root.parents[4]
sys.path.insert(0, str(repo))
from scripts.summarize_unattached_browser import summarize

try:
    summarize(root)
except ValueError as error:
    rejection = str(error)
    assert rejection == 'Active browser process set changed after warmup', rejection
else:
    raise AssertionError('Expected process-group rejection is no longer reproduced')

rows = [json.loads(line) for line in (root/'process-memory.jsonl').read_text().splitlines()]
plan = json.loads((root/'plan.json').read_text())
measured = [r for r in rows if r['elapsed_seconds'] >= 120]
active = lambda r: {p['pid']: p for p in r['processes'] if p['name'] != '<defunct>'}
common = set.intersection(*(set(active(r)) for r in measured))
a, b = measured[0], measured[-1]
first, last = active(a), active(b)
transient = [{'elapsed_seconds': r['elapsed_seconds'], 'process': p}
             for r in measured for p in r['processes']
             if p['name'] != '<defunct>' and p['pid'] not in common]
report = {
    'completed_window_seconds': rows[-1]['elapsed_seconds'],
    'sample_count': len(rows),
    'strict_comparison_passed': False,
    'strict_comparison_rejection': rejection,
    'overall_goal_complete': False,
    'scope': 'Descriptive local diagnostic; unchanged Pi acceptance remains open',
    'max_sample_gap_seconds': max(y['elapsed_seconds']-x['elapsed_seconds'] for x,y in zip(rows,rows[1:])),
    'descriptive_endpoint_seconds': [a['elapsed_seconds'], b['elapsed_seconds']],
    'all_process_endpoint_rss_mib': [a['browser_rss_kib']/1024,b['browser_rss_kib']/1024],
    'all_process_peak_rss_mib': max(r['browser_rss_kib'] for r in measured)/1024,
    'transient_processes_after_warmup': transient,
    'continuous_pids': sorted(common),
    'continuous_processes': [
        {'pid': pid, 'role': first[pid]['name'],
         'first_rss_mib': first[pid]['rss_kib']/1024,
         'last_rss_mib': last[pid]['rss_kib']/1024,
         'delta_mib': (last[pid]['rss_kib']-first[pid]['rss_kib'])/1024}
        for pid in sorted(common)],
    'last_ten_minutes_rss_range_mib': [
        min(r['browser_rss_kib'] for r in rows if r['elapsed_seconds'] >= 1200)/1024,
        max(r['browser_rss_kib'] for r in rows if r['elapsed_seconds'] >= 1200)/1024],
    'limits': plan['limitations'] + [
        'PID and second-resolution OS process start times were checked by the strict validator.',
        'The short-lived helper identity and purpose are not established.',
        'Both modes share this Mac; offline symbol extraction and analysis also ran on it during the observation.',
        'The two modes differ only in the pinned microphone.js asset, but one parallel trial with process churn is not a causal effect-size or Pi acceptance proof.',
        'The failed strict comparison is retained, not bypassed or replaced with a later warmup cutoff.'],
    'source_sha256': {n:hashlib.sha256((root/n).read_bytes()).hexdigest()
                      for n in ['plan.json','process-memory.jsonl','sampler-complete.json',
                                'cleanup.json','proxy-counters.json','sampler.py']},
}
assert all(active(r)[pid]['name']==first[pid]['name'] for r in measured for pid in common)
print(json.dumps(report, indent=2))
