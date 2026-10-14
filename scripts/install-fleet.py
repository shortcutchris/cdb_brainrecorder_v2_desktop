#!/usr/bin/env python3
"""One-time migration to version directories; run on an idle Pi as Studio user.

Requires tested Studio source, public signing key and HTTPS server. Keeps the old
service and complete original checkout as rollback; never copies data into releases.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fleet.common import request,save,read
from fleet.releases import allowed

p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--runtime-python',required=True);p.add_argument('--server',required=True);p.add_argument('--public-key',required=True);p.add_argument('--version',required=True);p.add_argument('--database',required=True);a=p.parse_args()
os.umask(0o077)
if not a.server.startswith('https://'):raise SystemExit('HTTPS server required')
root=Path.home()/'.local/share/cdb-recorder-app';data=Path.home()/'.local/share/cdb-recorder-local';agent=Path.home()/'.local/share/cdb-recorder-agent';source=Path(a.source).resolve();management=data/'management'
if root.exists() or agent.exists():raise SystemExit('Already installed: use signed release workflow.')
s=request('http://127.0.0.1:8088','/api/state')
if s['activity']['busy'] or any(j['state'] in ('queued','importing','transcribing','summarizing','recording') for j in s['jobs']) or any(i['state'] in ('scheduled','due') for i in s['timers']['items']) or any(j['state'] in ('queued','sending','accepted') for j in s['cdb']['publications']):raise SystemExit('Device busy; do not install.')
unit=Path.home()/'.config/systemd/user/cdb-recorder-studio.service'
backup=Path.home()/('backups/fleet-bootstrap-'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
shutil.copy2(unit,backup/unit.name)
# Deployment owns the unit only after the existing app is stopped and rechecked.
subprocess.run(['systemctl','--user','stop','cdb-recorder-kiosk-033.service'],check=True)
latest=request('http://127.0.0.1:8088','/api/state')
if latest['activity']['busy']:raise SystemExit('Activity changed: aborted before stopping app.')
subprocess.run(['systemctl','--user','stop','cdb-recorder-studio.service'],check=True)
try:
    baseline=root/'releases'/'bootstrap';baseline.mkdir(parents=True)
    for file in source.rglob('*'):
        name=file.relative_to(source).as_posix()
        if file.is_file() and allowed(name):
            target=baseline/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
    original=Path(a.runtime_python).parent.parent.parent
    (baseline/'models').symlink_to(original/'models',target_is_directory=True)
    (root/'current').symlink_to(baseline,target_is_directory=True)
    save(root/'accepted.json',{'version':a.version,'sequence':0,'release':'bootstrap'})
    save(root/'shared.json',{'models':str(original/'models')})
    agent.mkdir();shutil.copytree(source/'fleet',agent/'fleet',ignore=shutil.ignore_patterns('__pycache__'))
    management.mkdir(parents=True,exist_ok=True);shutil.copy2(a.public_key,management/'release-public.pem')
    freeze=subprocess.check_output([a.runtime_python,'-m','pip','freeze']).decode()
    runtime=hashlib.sha256((str(sys.version_info[:2])+freeze).encode()).hexdigest()
    save(management/'config.json',{'server':a.server,'updates_root':str(root),'runtime':runtime})
    text=unit.read_text();lines=text.splitlines()
    lines=[('ExecStart='+a.runtime_python+' '+str(root/'current/web_server.py')+' --port 8088 --database '+a.database) if line.startswith('ExecStart=') else line for line in lines]
    unit.write_text('\n'.join(lines)+'\n')
    agent_unit=unit.with_name('cdb-recorder-agent.service')
    agent_unit.write_text('[Unit]\nDescription=Brain device management agent\nAfter=network-online.target\n\n[Service]\nWorkingDirectory='+str(agent)+'\nExecStart='+a.runtime_python+' -m fleet.agent --root '+str(management)+'\nEnvironment=LANG=C.UTF-8\nEnvironment=PYTHONIOENCODING=utf-8\nUMask=0077\nRestart=on-failure\nRestartSec=10\n\n[Install]\nWantedBy=default.target\n')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','start','cdb-recorder-studio.service'],check=True)
    ok=False
    for _ in range(30):
        try:
            current=request('http://127.0.0.1:8088','/api/state');ok=current['version']==a.version and bool(current.get('management'))
        except Exception:pass
        if ok:break
        time.sleep(1)
    if not ok:raise RuntimeError('Bootstrap health check failed')
    subprocess.run(['systemctl','--user','enable','--now','cdb-recorder-agent.service'],check=True)
    print(json.dumps({'version':a.version,'runtime':runtime,'backup':str(backup),'root':str(root)}))
except Exception:
    shutil.copy2(backup/unit.name,unit);subprocess.run(['systemctl','--user','daemon-reload']);subprocess.run(['systemctl','--user','restart','cdb-recorder-studio.service']);raise
finally:subprocess.run(['systemd-run','--user','--collect','--unit=cdb-recorder-kiosk-fleet','--setenv=WAYLAND_DISPLAY=wayland-0','--setenv=DISPLAY=:0','--setenv=XDG_RUNTIME_DIR=/run/user/'+str(os.getuid()),str(Path(a.runtime_python).parent.parent.parent/'kiosk.sh')])
