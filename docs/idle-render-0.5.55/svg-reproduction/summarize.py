"""Describe bounded SVG diagnostics. Never declares overall stability passed."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

def summarize(mode):
    report = json.loads((ROOT / mode / 'profile.json').read_text())
    cleanup = json.loads((ROOT / mode / 'cleanup.json').read_text())
    assert cleanup['closed'] and not cleanup['remaining']
    assert cleanup['server_stopped'] and cleanup['guard_stopped']
    assert report['mode'] == mode and report['revision'] == 2
    assert report['browser']['product'] == 'Chrome/142.0.7444.59'
    assert report['expected_iterations'] == 500
    stress = report['after_stress_immediate']['probe']
    assert stress['done'] and stress['iterations'] == 500
    assert not report['errors'] and all(g['idle'] for g in report['guard_samples'])
    phases = []
    for row in report['runs']:
        before, after = row['before'], row['after']
        duration = after['at_epoch'] - before['at_epoch']
        assert 4.9 <= duration <= 6
        bm = {m['name']: m['value'] for m in before['metrics']['metrics']}
        am = {m['name']: m['value'] for m in after['metrics']['metrics']}
        processes = []
        for pid, a in after['processes'].items():
            b = before['processes'].get(pid)
            if b is None or b['start'] != a['start']:
                continue
            cpu = (a['user_ticks'] + a['system_ticks'] - b['user_ticks'] - b['system_ticks'])
            assert cpu >= 0
            processes.append({'pid': int(pid), 'start': a['start'],
                              'cpu_percent_one_core': round(cpu / report['clock_ticks'] / duration * 100, 3),
                              'rss_mib': round(a['rss_kib'] / 1024, 3)})
        phases.append({'phase': row['phase'], 'seconds': round(duration, 3),
                       'dom_before': before['dom'], 'dom_after': after['dom'],
                       'heap_after': after['heap'],
                       'task_seconds': round(am['TaskDuration'] - bm['TaskDuration'], 6),
                       'script_seconds': round(am['ScriptDuration'] - bm['ScriptDuration'], 6),
                       'same_identity_processes': processes,
                       'process_set_unchanged': before['processes'].keys() == after['processes'].keys()})
    assert [p['phase'] for p in phases] == ['baseline', 'after_stress', 'after_forced_gc']
    return {'mode': mode, 'start_epoch': report['started_at_epoch'],
            'end_epoch': cleanup['at_epoch'], 'source_hashes': report['source_hashes'],
            'stress': stress, 'requests': report['requests'], 'phases': phases,
            'closed': True, 'overall_goal_complete': False}

if __name__ == '__main__':
    rows = [summarize(mode) for mode in ('original', 'guarded')]
    assert rows[0]['source_hashes']['play.svg'] == rows[1]['source_hashes']['play.svg']
    print(json.dumps(rows, indent=2) + '\n', end='')
