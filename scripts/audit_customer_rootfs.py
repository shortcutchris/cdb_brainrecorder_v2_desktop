#!/usr/bin/env python3
"""Read-only release gate for an OFFLINE factory rootfs, not a running device."""
import argparse
import json
from pathlib import Path


def audit(root):
    root = Path(root).resolve()
    if root == Path('/') or not (root / 'etc/cdb-factory-image.json').is_file():
        raise ValueError('An offline Brain factory rootfs is required')
    problems = []
    forbidden = ('etc/NetworkManager/system-connections/*', 'etc/ssh/ssh_host_*',
                 'home/*/.ssh/*', 'home/*/.local/share/cdb-recorder-*/*',
                 'home/*/.config/AudioSessions/*', 'home/*/.config/chromium/*',
                 'var/lib/tailscale/*', 'var/lib/cdb-network/*', 'var/lib/cdb-factory/*')
    for pattern in forbidden:
        for path in root.glob(pattern):
            if path.is_file() and path.stat().st_size:
                problems.append(str(path.relative_to(root)))
    machine = root / 'etc/machine-id'
    if machine.exists() and machine.read_text().strip() not in ('', 'uninitialized'):
        problems.append('shared machine-id')
    for line in (root / 'etc/shadow').read_text().splitlines():
        parts = line.split(':')
        if parts[0] in ('root', 'cdb') and not parts[1].startswith(('!', '*')):
            problems.append('unlocked factory account: ' + parts[0])
    for path in (root / 'opt/cdb').rglob('*'):
        if path.is_file() and (path.suffix in ('.db','.sqlite','.sqlite3') or path.name in ('credential.json','admin','release-private.pem','id_ed25519')):
            problems.append(str(path.relative_to(root)))
    if problems: raise ValueError('Factory image must not ship: ' + ', '.join(problems))
    return {'clean': True, 'boot_test_required': True}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rootfs');a=p.parse_args();print(json.dumps(audit(a.rootfs)))
