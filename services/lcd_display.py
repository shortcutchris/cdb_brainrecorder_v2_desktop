"""Small read-only LCD projection. No audio, accounts or recorder state."""
import math
import unicodedata

PROTOCOL = 'cdb.lcd/1'
MAX_TIMERS = 16
MAX_FRAME = 8192


def label(value, limit=80):
    return ''.join(c for c in str(value) if not unicodedata.category(c).startswith('C'))[:limit]


def snapshot(schedules, clock_ready):
    # Use the scheduler's monotonic clock, not rounded browser seconds or SQL writes.
    with schedules.lock, schedules.db() as db:
        rows = db.execute("SELECT * FROM schedules WHERE state IN ('scheduled','due','missed') ORDER BY CASE state WHEN 'due' THEN 0 WHEN 'missed' THEN 1 ELSE 2 END,due").fetchall()
    timers = []
    for row in rows[:MAX_TIMERS]:
        valid = bool(clock_ready or (row['kind'] == 'timer' and row['boot'] == schedules.boot))
        remaining = schedules.remaining(row) if valid else 0
        timers.append({'id': row['id'], 'revision': row['revision'], 'label': label(row['label']),
                       'state': row['state'], 'remaining_ms': max(0, min(31622400000, math.ceil(remaining * 1000))),
                       'time_valid': valid})
    return {'protocol': PROTOCOL, 'type': 'timers', 'clock_ready': bool(clock_ready),
            'total': len(rows), 'timers': timers}
