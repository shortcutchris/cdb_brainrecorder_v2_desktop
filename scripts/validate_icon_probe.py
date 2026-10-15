"""Validate the bounded native Pi icon comparison, not overall app stability.

Requires the caller's hash of the actual committed candidate. A successfully
finished systemd service alone never constitutes a valid measurement.
"""
import math
import re

EXPECTED_RESPONSES = {'/api/cdb/areas': 200, '/api/microphone/audio': 200,
                      '/assets/InterVariable.woff2': 404, '/favicon.ico': 204}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(report, cleanup, candidate_sha256, mode):
    require(mode in ('original', 'guarded'), 'Unknown comparison mode')
    require(isinstance(candidate_sha256, str) and re.fullmatch('[0-9a-f]{64}', candidate_sha256),
            'Committed candidate digest required')
    require(report.get('revision') == 4 and report.get('mode') == mode, 'Wrong diagnostic revision or mode')
    require(report.get('browser', {}).get('product') == 'Chrome/142.0.7444.59', 'Unexpected browser version')
    require(report.get('planned_seconds') == 300, 'Unexpected planned window')
    require(cleanup.get('closed') is True and cleanup.get('remaining') == []
            and cleanup.get('server_stopped') is True and cleanup.get('guard_stopped') is True
            and cleanup.get('profile_written') is True, 'Incomplete measurement or cleanup')
    require(report.get('errors') == [], 'Unexpected response errors')
    guards = report.get('guard_samples', [])
    require(guards and all(g.get('idle') is True for g in guards), 'Missing or interrupted activity guard')
    require(report.get('auxiliary_statuses') == EXPECTED_RESPONSES, 'Responses differ from inspected production baseline')
    require(report.get('known_production_missing_assets') == ['/assets/InterVariable.woff2'],
            'Known missing production font must remain explicit')
    hashes = report.get('source_hashes', {})
    require(hashes.get('candidate_microphone.js') == candidate_sha256, 'Candidate differs from committed source')
    served = hashes.get('served_microphone.js')
    require(served == (candidate_sha256 if mode == 'guarded' else hashes.get('microphone.js'))
            and isinstance(served, str) and re.fullmatch('[0-9a-f]{64}', served), 'Wrong served source')
    rows = report.get('runs', [])
    require(len(rows) == 11, 'Incomplete sample count')
    times = [r.get('at_epoch') for r in rows]
    require(all(isinstance(t, (int, float)) and math.isfinite(t) for t in times), 'Invalid sample timestamps')
    require(299 <= times[-1] - times[0] <= 305, 'Incomplete measurement window')
    require(all(29 <= b - a <= 31 for a, b in zip(times, times[1:])), 'Interrupted sampling')
    root = str(report.get('browser_pid'))
    identity = rows[0].get('processes', {}).get(root, {}).get('start')
    require(isinstance(identity, int) and identity > 0, 'Missing browser identity')
    for row in rows:
        require(row.get('processes', {}).get(root, {}).get('start') == identity, 'Browser replaced during measurement')
        ui = row.get('ui', {})
        require(ui.get('workspace') == 'start-view' and ui.get('hidden') is False
                and ui.get('online') is True and ui.get('version') == '0.5.55', 'Unexpected app state')
        require(ui.get('probeSource') == '/assets/play.svg' and ui.get('probeReady') is True,
                'Missing or incorrect rendered icon')
        require(ui.get('errorCounts') == {'script': 0, 'rejection': 0}, 'Browser script errors')
        require(row.get('response_errors') == [], 'Unexpected response error at sample')
    for before, after in zip(rows, rows[1:]):
        for path in ('/api/state', '/api/wake/status'):
            require(after.get('requests', {}).get(path, 0) > before.get('requests', {}).get(path, 0),
                    'App polling stalled')
    return {'probe_valid': True, 'all_production_assets_healthy': False,
            'known_missing_asset': '/assets/InterVariable.woff2', 'overall_goal_complete': False}
