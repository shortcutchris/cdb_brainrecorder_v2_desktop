#!/usr/bin/env python3
"""Install only the optional per-user LCD companion, never restart the recorder."""
import argparse
import grp
import os
from pathlib import Path
import subprocess
import sys


def quote(value):
    value = str(value)
    if any(ord(c) < 32 for c in value):
        raise ValueError('Control character in service argument')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def unit(root, runtime, api_port=8088, token_file=None):
    if not 1 <= api_port <= 65535:
        raise ValueError('Invalid API port')
    args = [runtime/'bin/python', '-m', 'services.lcd_bridge', '--api-port', str(api_port)]
    if token_file:
        args += ['--token-file', token_file]
    return '\n'.join([
        '[Unit]', 'Description=CDB automatic USB timer display', 'After=network.target', '',
        '[Service]', 'Type=simple', 'WorkingDirectory='+quote(root),
        'ExecStart='+' '.join(quote(arg).replace('$', '$$') for arg in args), 'Restart=always', 'RestartSec=5',
        'TimeoutStopSec=5', 'KillMode=control-group', 'UMask=0077', 'Nice=10',
        'CPUQuota=10%', 'MemoryMax=128M', 'NoNewPrivileges=yes',
        'RestrictAddressFamilies=AF_UNIX AF_INET', '', '[Install]', 'WantedBy=default.target', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-port', type=int, default=8088)
    parser.add_argument('--token-file', type=Path)
    parser.add_argument('--no-start', action='store_true', help='Enable for next login without starting now')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.getuid() == 0:
        parser.error('Run as the recorder desktop user on Linux, not root')
    # Do not silently grant access to serial or audio devices.
    try:
        permitted = grp.getgrnam('dialout').gr_gid in os.getgroups()
    except KeyError:
        permitted = False
    if not permitted:
        parser.error('The desktop user needs dialout membership (and a new login) before installation')
    root = Path(__file__).resolve().parents[2]
    runtime = Path.home()/'.local/share/cdb-lcd/runtime'
    token = args.token_file.resolve() if args.token_file else None
    if token and (not token.is_file() or token.stat().st_mode & 0o077):
        parser.error('Token file must exist and be private to the user')
    content = unit(root, runtime, args.api_port, token)
    os.umask(0o077)
    # Separate environment, no change to recorder requirements or configuration.
    subprocess.run([sys.executable, '-m', 'venv', str(runtime)], check=True)
    subprocess.run([str(runtime/'bin/python'), '-m', 'pip', 'install', 'pyserial==3.5'], check=True)
    destination = Path.home()/'.config/systemd/user/cdb-lcd-display.service'
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = destination.with_suffix('.tmp')
    staged.write_text(content)
    staged.replace(destination)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', 'cdb-lcd-display.service'], check=True)
    if not args.no_start:
        subprocess.run(['systemctl', '--user', 'restart', 'cdb-lcd-display.service'], check=True)
    print('LCD companion installed; recorder and audio services unchanged.')

if __name__ == '__main__':
    main()
