"""One-use account continuity for a guarded app update, never a machine reboot.

No credentials are copied here. Existing CDB tokens retain their normal validity
and refresh checks. A consumed or invalid handoff cannot resurrect a login.
"""
import json
import math
import re
import time
from pathlib import Path
from meeting_recorder.core import atomic_write


def boot_id():
    try: return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError: return ''


def _path(root):
    return Path(root) / 'management' / 'update-session.json'


def discard(root):
    _path(root).unlink(missing_ok=True)


def _marker(root, command):
    try:
        data = json.loads((Path(root) / 'management' / 'maintenance.json').read_text())
        return data.get('command') == command and data.get('expires', 0) > time.time()
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def issue(root, command, account, epoch, idle_remaining, *, clock=time.monotonic):
    """Called under the maintenance lock, after busy/login checks; no new login."""
    discard(root)
    boot = boot_id()
    if (not boot or not account or not re.fullmatch(r'[0-9a-f]{32}', epoch or '')
            or not isinstance(idle_remaining, (int, float)) or not 0 < idle_remaining <= 3600
            or not _marker(root, command)):
        return False
    now = clock()
    data = {'boot': boot, 'command': command, 'account': account, 'epoch': epoch,
            'issued': now, 'expires': now + 120, 'idle_until': now + idle_remaining}
    path = _path(root)
    atomic_write(path, json.dumps(data)); path.chmod(0o600)
    return True


def consume(root, account, idle_minutes, *, clock=time.monotonic):
    path = _path(root)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = None
    finally:
        discard(root)
    try:
        now = clock()
        if (not account or not isinstance(data, dict) or not boot_id()
                or data.get('boot') != boot_id() or data.get('account') != account
                or not _marker(root, data.get('command'))
                or not re.fullmatch(r'[0-9a-f]{32}', data.get('epoch', ''))):
            return None
        issued, expires, deadline = (data[k] for k in ('issued', 'expires', 'idle_until'))
        if (not all(type(v) in (int, float) and math.isfinite(v) for v in (issued, expires, deadline))
                or not issued <= now < expires <= issued + 120
                or not now < deadline <= issued + 3600):
            return None
        return {'epoch': data['epoch'], 'remaining': min(deadline - now, idle_minutes * 60)}
    except (ValueError, TypeError, KeyError):
        return None
