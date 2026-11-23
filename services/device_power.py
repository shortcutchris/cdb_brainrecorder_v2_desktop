"""Fixed shutdown command, isolated from the HTTP request and bound to its lease."""
import argparse
from pathlib import Path
import subprocess
import time
from fleet.common import read,save

LOGIN_MANAGER=['/usr/bin/busctl','call','org.freedesktop.login1','/org/freedesktop/login1','org.freedesktop.login1.Manager']

def shutdown_method(runner=subprocess.run):
    # Check in the same user-manager context as the delayed worker. Never prompt.
    try:
        result=runner(LOGIN_MANAGER+['CanPowerOff'],capture_output=True,text=True,timeout=5)
        if result.returncode==0 and result.stdout.strip()=='s "yes"':return 'logind'
    except (OSError,subprocess.SubprocessError):pass
    try:
        result=runner(['sudo','-n','-l','/usr/bin/systemctl','poweroff'],capture_output=True,timeout=5)
        if result.returncode==0:return 'sudo'
    except (OSError,subprocess.SubprocessError):pass
    raise ValueError('Herunterfahren ist auf diesem Pi noch nicht freigegeben. Bitte die Geräteeinrichtung prüfen.')

def power_status(root,boot):
    state=read(Path(root)/'power.json',{})
    if not boot or state.get('boot')!=boot:return {}
    status=state.get('state')
    if status in ('scheduled','requested') and state.get('expires',0)<=time.time():status='failed'
    return {'command':state.get('command'),'state':status} if status in ('scheduled','requested','failed') else {}

def execute_shutdown(root,command,method,runner=subprocess.run,boot=None):
    root=Path(root);marker=root/'maintenance.json';power=root/'power.json'
    boot=boot or Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    lease=read(marker,{})
    if lease.get('command')!=command or lease.get('boot')!=boot or lease.get('expires',0)<=time.time():return False
    commands={'logind':LOGIN_MANAGER+['PowerOff','b','false'],
              'sudo':['/usr/bin/sudo','-n','/usr/bin/systemctl','poweroff']}
    try:
        if method not in commands:raise ValueError('Unknown shutdown method')
        save(power,{'command':command,'boot':boot,'state':'requested','expires':lease['expires']})
        result=runner(commands[method],capture_output=True,timeout=15)
        if result.returncode:raise ValueError('System rejected shutdown')
        return True
    except (OSError,ValueError,subprocess.SubprocessError):
        save(power,{'command':command,'boot':boot,'state':'failed'})
        if read(marker,{}).get('command')==command:marker.unlink(missing_ok=True)
        return False

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--command',required=True)
    parser.add_argument('--method',choices=['logind','sudo'],required=True)
    args=parser.parse_args()
    raise SystemExit(0 if execute_shutdown(args.root,args.command,args.method) else 1)
