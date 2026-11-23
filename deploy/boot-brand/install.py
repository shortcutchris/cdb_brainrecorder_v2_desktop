#!/usr/bin/env python3
"""Explicit, reversible OS installation. Never invoked by the app updater."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

THEME = 'usr/share/plymouth/themes/cdb-pios'
CONFIGS = ('boot/firmware/config.txt', 'boot/firmware/cmdline.txt', 'etc/plymouth/plymouthd.conf')
STATE = 'var/lib/cdb-boot/installed.json'
SOURCE = Path(__file__).resolve().parent


def configuration(config, cmdline, plymouth):
    if len(cmdline.strip().splitlines()) != 1 or 'root=' not in cmdline:
        raise ValueError('Expected one existing boot command line with root=')
    words = cmdline.strip().split()
    for word in ('quiet', 'splash', 'logo.nologo'):
        if word not in words: words.append(word)
    marker = '# cdbPiOS boot branding'
    config = re.sub(r'\n# cdbPiOS boot branding\n\[all\]\ndisable_splash=1\n?', '\n', config)
    config = config.rstrip() + '\n\n' + marker + '\n[all]\ndisable_splash=1\n'
    lines = plymouth.splitlines(); result = []; daemon = False; found = False; section = False
    for line in lines:
        if line.strip().startswith('['):
            if daemon and not found: result.append('Theme=cdb-pios'); found = True
            daemon = line.strip() == '[Daemon]'; section |= daemon
        if daemon and re.match(r'\s*Theme\s*=', line):
            if not found: result.append('Theme=cdb-pios'); found = True
        else: result.append(line)
    if not found:
        if not section: result.extend(['', '[Daemon]'])
        result.append('Theme=cdb-pios')
    return (config, ' '.join(words) + '\n', '\n'.join(result) + '\n')


def payload(source, rotation):
    if rotation not in (90, 270): raise ValueError('Portrait rotation must be 90 or 270')
    files = {}
    for name in ('cdb-pios.plymouth', 'cdb-pios.script'):
        path = source / name
        if path.is_symlink(): raise ValueError('Theme symlinks are not allowed')
        files[name] = path.read_bytes()
    files['cdb-pios.script'] = files['cdb-pios.script'].replace(b'@ROTATION@', str(rotation).encode())
    for mode in ('startup', 'shutdown'):
        for view, original in [('landscape', 'landscape'), ('portrait', f'portrait{rotation}')]:
            path = source / 'assets' / f'{mode}-{original}.png'
            if path.is_symlink(): raise ValueError('Asset symlinks are not allowed')
            files[f'{mode}-{view}.png'] = path.read_bytes()
    files['dot.png'] = (source / 'assets/dot.png').read_bytes()
    return files


def write(path, value):
    if path.is_symlink(): raise ValueError(f'Refusing symlink: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Direct writes also work on the FAT firmware partition. Originals are backed up.
    with path.open('wb') as stream:
        stream.write(value); stream.flush(); os.fsync(stream.fileno())
    path.chmod(0o644)


def restore(root, backup, runner=subprocess.run):
    state = json.loads((backup / 'snapshot.json').read_text())
    if set(state['configs']) != set(CONFIGS): raise ValueError('Invalid boot backup')
    for name, existed in state['configs'].items():
        target = root / name
        if existed: write(target, (backup / name).read_bytes())
        else: target.unlink(missing_ok=True)
    target = root / THEME
    if target.is_symlink(): raise ValueError('Unexpected linked theme')
    if target.exists(): shutil.rmtree(target)
    if state['theme_existed']: shutil.copytree(backup / 'theme', target)
    marker = root / STATE
    if (backup / 'previous-state.json').exists(): write(marker, (backup / 'previous-state.json').read_bytes())
    else: marker.unlink(missing_ok=True)
    runner(['/usr/sbin/update-initramfs', '-u', '-k', 'all'], check=True, timeout=300)


def install(root=Path('/'), source=SOURCE, rotation=90, runner=subprocess.run, check=False):
    files = payload(source, rotation)
    config_paths = [root / name for name in CONFIGS]
    if not config_paths[0].is_file() or not config_paths[1].is_file():
        raise ValueError('Raspberry Pi OS firmware files are missing')
    if any(p.is_symlink() for p in config_paths) or (root / THEME).is_symlink():
        raise ValueError('Linked configuration requires manual review')
    old = [p.read_text() if p.exists() else '' for p in config_paths]
    values = configuration(*old)
    digest = hashlib.sha256(b''.join(k.encode() + files[k] for k in sorted(files))).hexdigest()
    result = {'brand': 'cdbPiOS', 'portrait_rotation': rotation, 'theme_sha256': digest,
              'desktop_rotation_changed': False, 'reboot_performed': False}
    if check: return result | {'status': 'checked-no-changes'}
    marker = root / STATE
    if marker.exists() and json.loads(marker.read_text()).get('theme_sha256') == digest:
        if all((root / THEME / k).is_file() and (root / THEME / k).read_bytes() == v for k, v in files.items()) and old == list(values):
            return result | {'status': 'already-installed'}
    backup = root / 'var/backups/cdb-boot' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup.mkdir(parents=True, mode=0o700)
    snapshot = {'configs': {name: (root / name).exists() for name in CONFIGS}, 'theme_existed': (root / THEME).exists()}
    for name, existed in snapshot['configs'].items():
        if existed: write(backup / name, (root / name).read_bytes())
    if snapshot['theme_existed']: shutil.copytree(root / THEME, backup / 'theme')
    if marker.exists(): write(backup / 'previous-state.json', marker.read_bytes())
    write(backup / 'snapshot.json', json.dumps(snapshot).encode())
    try:
        for name, value in files.items(): write(root / THEME / name, value)
        for path, value in zip(config_paths, values): write(path, value.encode())
        runner(['/usr/sbin/update-initramfs', '-u', '-k', 'all'], check=True, timeout=300)
        result |= {'status': 'installed-reboot-test-pending', 'backup': str(backup)}
        write(marker, json.dumps(result, indent=2).encode() + b'\n')
    except Exception:
        restore(root, backup, runner)
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--portrait-rotation', type=int, choices=(90, 270), default=90)
    parser.add_argument('--restore', type=Path, metavar='BACKUP')
    parser.add_argument('--image-build', action='store_true')
    args = parser.parse_args()
    if args.image_build:
        if not Path('/.cdb-image-build').exists(): parser.error('Not inside the customer image builder')
    else:
        model = Path('/proc/device-tree/model')
        if not model.exists() or 'Raspberry Pi' not in model.read_text(): parser.error('Run on Raspberry Pi OS')
    if not args.check and os.geteuid() != 0: parser.error('Administrator rights required; run with sudo on the Pi')
    for path in ('/usr/sbin/update-initramfs', '/usr/lib/aarch64-linux-gnu/plymouth/script.so'):
        if not Path(path).exists(): parser.error(f'Missing Plymouth/initramfs dependency: {path}')
    if shutil.disk_usage('/boot/firmware').free < 100 * 1024 * 1024:
        parser.error('At least 100 MB free space required on the firmware partition')
    if args.restore:
        if args.check: parser.error('--check cannot restore')
        backup = args.restore.resolve()
        if backup.parent != Path('/var/backups/cdb-boot'): parser.error('Select an original /var/backups/cdb-boot backup')
        restore(Path('/'), backup)
        print('Previous boot appearance restored; restart test pending.')
    else:
        print(json.dumps(install(rotation=args.portrait_rotation, check=args.check), indent=2))


if __name__ == '__main__':
    main()
