"""Read-only telemetry summary. Never declares the overall product goal complete."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
import time


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def stamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.timestamp() if parsed.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def distribution(values):
    values = sorted(v for v in values if number(v))
    if not values:
        return {'samples': 0}
    return {'samples': len(values), 'min': min(values), 'median': statistics.median(values),
            'p95': values[math.ceil(len(values) * .95) - 1], 'max': max(values)}


def coverage(times, start, end):
    """Union of 15-second observation slots; duplicate rows cannot fill gaps."""
    cursor, covered, gaps = start, 0., []
    for at in sorted(set(times)):
        left, right = max(start, at), min(end, at + 15)
        if right <= cursor or left >= end:
            continue
        if left > cursor:
            gaps.append(left - cursor)
        covered += right - max(cursor, left)
        cursor = right
    if cursor < end:
        gaps.append(end - cursor)
    return {'covered_seconds': round(covered, 3),
            'coverage_percent': round(100 * covered / (end - start), 4) if end > start else 0,
            'largest_gap_seconds': round(max(gaps, default=0), 3)}


def analyze(plan, status, metrics, events, now, parse_errors=0):
    start, end = plan['start_epoch'], plan['end_epoch']
    if not all(number(x) for x in (start, end, now)) or end <= start:
        raise ValueError('Invalid observation window')
    until = max(start, min(now, end))
    rows, timestamps, invalid = [], [], parse_errors
    for row in metrics:
        if not isinstance(row, dict) or (at := stamp(row.get('at'))) is None:
            invalid += 1
            continue
        timestamps.append(at)
        if not start <= at < until:
            continue
        browser = row.get('browser')
        if (not isinstance(browser, dict) or not number(browser.get('rss_mb')) or
                not number(browser.get('processes')) or browser['processes'] <= 0 or
                not number(row.get('health_ms')) or row['health_ms'] < 0 or
                row.get('activity') in (None, '', 'unknown') or not row.get('version') or
                not row.get('browser_generation')):
            invalid += 1
            continue
        rows.append((at, row))
    clock_order_ok = all(a <= b for a, b in zip(timestamps, timestamps[1:]))
    rows.sort(key=lambda pair: pair[0])
    selected_events, completion = [], False
    for event in events:
        if not isinstance(event, dict) or (at := stamp(event.get('at'))) is None:
            invalid += 1
            continue
        if event.get('type') == 'observation_complete' and end <= at <= now:
            completion = True
        if start <= at <= until:
            selected_events.append(event)
    generations = [json.dumps(r['browser_generation'], sort_keys=True) for _, r in rows]
    browser_changes = sum(a != b for a, b in zip(generations, generations[1:]))
    backend_changes = sum(e.get('type') == 'backend_instance_changed' for e in selected_events)
    observer_starts = sum(e.get('type') == 'observer_started' for e in selected_events)
    alerts = sorted({str(e.get('code')) for e in selected_events if e.get('type') == 'alert'})
    versions = sorted({str(r['version']) for _, r in rows})
    phrases = sorted({str(r.get('wake_phrase', 'hey-brain')) for _, r in rows} |
                     {str(e.get('phrase', 'unknown')) for e in selected_events if e.get('type') == 'wake_phrase'})
    wakes = {}
    for e in selected_events:
        if e.get('type') not in ('wake_observed', 'wake_connected', 'wake_first_output', 'wake_failed'):
            continue
        key = e.get('detected_epoch')
        if not number(key) or not start <= key <= until:
            invalid += 1
            continue
        wake = wakes.setdefault(key, {'detected_epoch': key, 'observed': False})
        if e['type'] == 'wake_observed':
            wake.update(observed=True, idle_seconds=e.get('idle_seconds'), phrase=e.get('phrase', 'hey-brain'))
        if e['type'] == 'wake_connected': wake['connected_seconds'] = e.get('connected_seconds')
        if e['type'] == 'wake_first_output': wake['first_output_seconds'] = e.get('first_output_seconds')
        if e['type'] == 'wake_failed': wake['failed'] = True
    long_wakes = [w for w in wakes.values() if w['observed'] and
                  number(w.get('idle_seconds')) and 28800 <= w['idle_seconds'] <= w['detected_epoch'] - start + 2 and
                  number(w.get('connected_seconds')) and 0 <= w['connected_seconds'] < 15 and
                  number(w.get('first_output_seconds')) and w['first_output_seconds'] >= 0 and not w.get('failed')]
    hourly = []
    for hour in range(math.ceil((until - start) / 3600)):
        values = [r['browser']['rss_mb'] for at, r in rows if start + hour * 3600 <= at < start + (hour + 1) * 3600]
        if values: hourly.append({'hour': hour, 'samples': len(values), 'median_rss_mb': statistics.median(values)})
    finished = (now >= end and end - start >= 86400 and status.get('status') == 'complete' and
                status.get('start_epoch') == start and status.get('end_epoch') == end and completion)
    measured = coverage([at for at, _ in rows], start, until)
    problems = []
    if invalid: problems.append('invalid_or_unavailable_samples')
    if not clock_order_ok: problems.append('clock_moved_backwards')
    if browser_changes or backend_changes: problems.append('runtime_restart_requires_review')
    if observer_starts == 0: problems.append('observer_start_evidence_missing')
    if observer_starts > 1: problems.append('observer_restart_requires_review')
    if len(versions) != 1: problems.append('missing_or_mixed_versions')
    if len(phrases) != 1 or 'unknown' in phrases: problems.append('mixed_or_unknown_wake_phrases')
    if alerts: problems.append('recorded_alerts_require_review')
    if measured['coverage_percent'] < 99: problems.append('coverage_below_99_percent')
    if not long_wakes: problems.append('real_wake_after_eight_hours_missing')
    return {
        'status': 'pending' if not finished else 'needs_review' if problems else 'ready_for_review',
        'overall_goal_complete': False,
        'note': 'Telemetry only. Review hourly RSS trend, actual UI/audio and the full acceptance matrix separately.',
        'start_epoch': start, 'end_epoch': end, 'analyzed_until_epoch': until,
        'elapsed_hours': round((until - start) / 3600, 4), 'completed_observation': finished,
        'valid_metric_samples': len(rows), 'invalid_samples': invalid, **measured,
        'planned_window_coverage_percent': round(measured['covered_seconds'] / (end - start) * 100, 4),
        'last_sample_age_seconds': round(now - rows[-1][0], 3) if rows else None,
        'versions': versions, 'browser_generation_changes': browser_changes,
        'wake_phrases': phrases,
        'backend_instance_changes': backend_changes, 'observer_starts': observer_starts,
        'alerts': alerts, 'review_items': problems,
        'idle_browser_cpu_percent_of_one_core': distribution(r['browser'].get('cpu_percent') for _, r in rows if r['activity'] == 'idle'),
        'idle_health_ms': distribution(r['health_ms'] for _, r in rows if r['activity'] == 'idle'),
        'browser_rss_mb': distribution(r['browser']['rss_mb'] for _, r in rows),
        'hourly_browser_rss': hourly,
        'observed_wakes': sorted(wakes.values(), key=lambda w: w['detected_epoch']),
        'qualified_long_idle_wakes': len(long_wakes),
    }


def read_lines(path):
    rows, errors = [], 0
    with path.open() as stream:
        for line in stream:
            try: rows.append(json.loads(line))
            except ValueError: errors += 1
    return rows, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    plan = json.loads((args.folder / 'plan.json').read_text())
    status = json.loads((args.folder / 'status.json').read_text())
    metrics, errors = read_lines(args.folder / 'metrics.jsonl')
    events, event_errors = read_lines(args.folder / 'events.jsonl')
    print(json.dumps(analyze(plan, status, metrics, events, time.time(), errors + event_errors), indent=2))


if __name__ == '__main__':
    main()
