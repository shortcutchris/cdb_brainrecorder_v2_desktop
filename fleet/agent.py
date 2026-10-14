"""Outbound-only companion. Commands are persisted before execution, never replayed.

Run separately from Studio; device credentials never enter Studio state/browser.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
from .common import read, request, save
from .releases import Updater, canonical


def hardware():
    path=Path('/sys/firmware/devicetree/base/serial-number')
    if not path.exists():raise ValueError('Keine Raspberry-Pi-Hardwarekennung.')
    return hashlib.sha256(path.read_bytes().rstrip(b'\0')).hexdigest()


def diagnostics(app):
    result={'app_reachable':bool(app),'architecture':platform.machine(),'agent_version':'1','free_mb':shutil.disk_usage(Path.home()).free//1048576}
    for k in ('version','activity','wake_state'):result[k]=app.get(k,'unknown')
    for filename,key,scale in [('/sys/class/thermal/thermal_zone0/temp','temperature_c',1000)]:
        try:result[key]=round(float(Path(filename).read_text())/scale,1)
        except (OSError,ValueError):result[key]=None
    try:result['memory_mb']=int(Path('/proc/meminfo').read_text().splitlines()[0].split()[1])//1024
    except (OSError,ValueError,IndexError):result['memory_mb']=None
    return result


class Agent:
    def __init__(self,root,identity=hardware,execute=None):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.identity=identity;self.execute=execute or self.execute_command
        self.hardware=identity();self.result=read(self.root/'result.json');self.status={}
        self.config=read(self.root/'config.json',{})
        self.updater=None
        if self.config.get('updates_root'):
            self.updater=Updater(self.config['updates_root'],self.root/'release-public.pem',self.config['runtime'],self.restart,self.health)
            self.updater.recover()
        inflight=read(self.root/'inflight.json')
        if inflight:
            # A reboot is only confirmed when the kernel boot ID actually changes.
            rebooted=inflight['action']=='reboot' and inflight.get('boot')!=self.boot()
            self.result={'id':inflight['id'],'state':'succeeded' if rebooted else 'interrupted','detail':'Neustart bestätigt.' if rebooted else 'Unterbrochener Auftrag; nicht automatisch wiederholt.'}
            save(self.root/'result.json',self.result);(self.root/'inflight.json').unlink()
            try:self.local('/api/management/release',{'command':inflight['id']})
            except Exception:pass

    @staticmethod
    def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    def local(self,path,body=None):
        key=read(self.root/'local-auth.json',{}).get('token','')
        return request(self.config.get('app_url','http://127.0.0.1:8088'),path,body,key)

    def restart(self):
        subprocess.run(['systemctl','--user','restart','cdb-recorder-studio.service'],check=True,timeout=60)

    def health(self,version):
        for _ in range(30):
            try:
                s=self.local('/api/management/health')
                if s['version']==version and s['ready']:return True
            except Exception:pass
            time.sleep(1)
        return False

    def execute_command(self,command):
        action=command['action']
        if action=='diagnose':return 'Diagnose aktualisiert.'
        if action not in ('restart-app','reboot','update'):raise ValueError('Unbekannter Auftrag.')
        bundle=None
        if action=='update':
            if not self.updater:raise ValueError('Signierte Updates noch nicht eingerichtet.')
            freeze=subprocess.check_output([sys.executable,'-m','pip','freeze'],timeout=30).decode()
            runtime=hashlib.sha256((str(sys.version_info[:2])+freeze).encode()).hexdigest()
            if runtime!=self.config['runtime']:raise ValueError('Python-Laufzeit geändert. Update-Basis neu prüfen.')
            credential=read(self.root/'credential.json')
            release=command['payload']['release']
            bundle=request(self.config['server'],'/api/release/'+release,token=credential['token'],limit=48*1024*1024)
            if hashlib.sha256(canonical(bundle['manifest'])).hexdigest()!=release:raise ValueError('Falsches Release.')
            # Verify before maintenance, then again inside the transaction.
            from .releases import verify
            ledger=read(self.updater.ledger)
            verify(bundle,self.updater.key,self.updater.architecture,self.updater.runtime,ledger['version'],ledger['sequence'])
        # Studio owns the atomic activity lock and persistent maintenance marker.
        lease=self.local('/api/management/prepare',{'command':command['id']})
        try:
            if action=='update':self.updater.install(bundle)
            elif action=='restart-app':
                version=lease['version'];self.restart()
                if not self.health(version):raise ValueError('App-Neustart konnte nicht bestätigt werden.')
            else:
                # Narrow sudoers entry is installed separately; no arbitrary command.
                try:subprocess.run(['sudo','-n','/usr/bin/systemctl','reboot'],check=True,timeout=15)
                except Exception:
                    self.local('/api/management/release',{'command':command['id']});raise
                return None  # completion confirmed after boot, not when reboot was queued
            return 'Update geprüft.' if action=='update' else 'App-Neustart geprüft.'
        finally:
            if action!='reboot':
                try:self.local('/api/management/release',{'command':command['id']})
                except Exception:pass

    def tick(self):
        self.config=read(self.root/'config.json',{})
        try:app=self.local('/api/management/health')
        except Exception:app={}
        if app.get('activity')=='maintenance' and self.result and not (self.updater and self.updater.journal.exists()):
            try:self.local('/api/management/release',{'command':self.result['id']})
            except Exception:pass
        self.status=diagnostics(app)
        if self.updater:self.status['release_sequence']=read(self.updater.ledger,{}).get('sequence',0)
        credential=read(self.root/'credential.json')
        enrollment=read(self.root/'enroll.json')
        if enrollment:
            try:
                if credential:raise ValueError('Bereits gekoppelt.')
                credential=request(self.config['server'],'/api/enroll',{'code':enrollment['code'],'hardware':self.hardware})
                credential['hardware']=self.hardware;save(self.root/'credential.json',credential)
                (self.root/'enroll.json').unlink()
            except Exception:
                (self.root/'enroll.json').unlink(missing_ok=True)
                save(self.root/'public.json',{'state':'error','message':'Kopplung nicht möglich. Neuen Code anfordern.'});return
        if not credential:
            save(self.root/'public.json',{'state':'unpaired','message':'Noch nicht mit der Geräteverwaltung verbunden.'});return
        if credential['hardware']!=self.identity():
            save(self.root/'public.json',{'state':'hardware-changed','message':'Hardware gewechselt. Kopplung durch Administrator erneuern.'});return
        response=request(self.config['server'],'/api/pulse',{'hardware':self.hardware,'status':self.status,'result':self.result},credential['token'])
        save(self.root/'public.json',{'state':'connected','message':'Geräteverwaltung verbunden.','name':credential['name'],'server':self.config['server'],'last_seen':time.time(),'update_ready':bool(self.updater)})
        command=response.get('command')
        if not command:return
        if self.result and self.result['id']==command['id']:return
        if (self.root/'inflight.json').exists():return
        state='failed';detail='Auftrag fehlgeschlagen. Lokal prüfen.'
        if command['expires']<time.time():detail='Auftrag abgelaufen.'
        else:
            save(self.root/'inflight.json',command|{'boot':self.boot()})
            try:
                detail=self.execute(command)
                if detail is None:return
                state='succeeded'
            except urllib.error.HTTPError as e:
                state='deferred' if e.code==409 else 'failed';detail='Gerät beschäftigt; später erneut beauftragen.' if e.code==409 else 'Geräteaktion abgewiesen.'
            except Exception:detail='Aktion fehlgeschlagen; Versions- und Verbindungsstatus prüfen.'
        self.result={'id':command['id'],'state':state,'detail':detail}
        save(self.root/'result.json',self.result);(self.root/'inflight.json').unlink(missing_ok=True)
        return True  # acknowledge completion promptly instead of another 30-second wait


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args();os.umask(0o077)
    import fcntl
    Path(args.root).mkdir(parents=True,exist_ok=True)
    lock=open(Path(args.root)/'agent.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    agent=Agent(args.root)
    while True:
        delay=30
        try:
            if agent.tick():delay=1
        except Exception:
            save(agent.root/'public.json',{'state':'offline','message':'Geräteverwaltung nicht erreichbar. Lokale Funktionen bleiben verfügbar.'})
        time.sleep(delay)

if __name__=='__main__':main()
