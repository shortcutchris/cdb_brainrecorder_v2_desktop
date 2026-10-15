"""Private local control boundary between Studio and the independent agent."""
import hmac
import os
from pathlib import Path
import secrets
import subprocess
import uuid
import time
from fleet.common import read, save


class DeviceManagement:
    def __init__(self,root):
        self.root=Path(root)/'management';self.root.mkdir(parents=True,exist_ok=True)
        self.auth=self.root/'local-auth.json'
        if not self.auth.exists():save(self.auth,{'token':secrets.token_urlsafe(32)})
        self.marker=self.root/'maintenance.json'

    def authorized(self,value):
        token=read(self.auth)['token']
        return bool(value) and hmac.compare_digest(value.removeprefix('Bearer '),token)

    def busy(self):
        marker=read(self.marker,{})
        updates=read(self.root/'config.json',{}).get('updates_root')
        transaction=bool(updates and (Path(updates)/'transaction.json').exists())
        boot=marker.get('boot')
        same_boot=not boot or boot==self.boot_id()
        return transaction or (same_boot and marker.get('expires',0)>time.time())

    def prepare(self,app,command,version):
        # Caller holds control/controller/recorder locks. All mutating paths and
        # wake starts consult this same marker, including after an app restart.
        if not isinstance(command,str) or len(command)!=36:raise ValueError('Auftragskennung fehlt.')
        activity=app.activity()
        if self.busy() or activity.occupied or activity.pending:raise ValueError('Aufnahme, Gespräch oder Verarbeitung läuft.')
        if any(i['state'] in ('scheduled','due') for i in app.schedules.items()):raise ValueError('Aktiver Timer oder Erinnerung zuerst abschließen.')
        if any(t>time.monotonic() for t in app.playback_leases.values()):raise ValueError('Wiedergabe läuft.')
        with app.cdb.db() as db:
            if db.execute("SELECT 1 FROM publications WHERE state IN ('queued','accepted','sending') LIMIT 1").fetchone():raise ValueError('Übertragung läuft.')
        save(self.marker,{'command':command,'expires':time.time()+600})
        app.wake.suspend('Gerät wird gewartet.')
        return {'ready':True,'version':version}

    def release(self,command):
        marker=read(self.marker,{})
        if marker.get('command')==command:self.marker.unlink(missing_ok=True)
        return {'ok':True}

    def public(self):
        state=read(self.root/'public.json',{'state':'unconfigured','message':'Geräteverwaltung noch nicht eingerichtet.'})
        if state.get('state')=='connected' and time.time()-state.get('last_seen',0)>100:
            state=state|{'state':'offline','message':'Verbindung zur Geräteverwaltung unterbrochen.'}
        return state|{'maintenance':self.busy()}

    def enroll(self,code):
        if self.busy():raise ValueError('Gerät wird gewartet.')
        if not read(self.root/'config.json',{}).get('server'):raise ValueError('Verwaltungsserver zuerst einrichten lassen.')
        if read(self.root/'credential.json'):raise ValueError('Gerät bereits gekoppelt.')
        code=str(code).replace('-','').replace(' ','').upper()
        if len(code)!=12 or any(c not in '0123456789ABCDEF' for c in code):raise ValueError('Zwölfstelligen Kopplungscode eingeben.')
        if (self.root/'enroll.json').exists():raise ValueError('Kopplung wird bereits geprüft.')
        save(self.root/'enroll.json',{'code':code})
        save(self.root/'public.json',{'state':'pairing','message':'Kopplung wird geprüft. Bitte kurz warten.'})
        return {'ok':True}

    @staticmethod
    def boot_id():
        try:return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        except OSError:return ''

    def restart_device(self,app,version,runner=None):
        runner=runner or subprocess.run
        if getattr(app,'preview',False) or not self.boot_id():
            raise ValueError('Neustart nur direkt am eingerichteten Pi verfügbar.')
        # Check the existing narrow privilege; never add or expand sudo rights.
        check=runner(['sudo','-n','-l','/usr/bin/systemctl','reboot'],capture_output=True,timeout=5)
        if check.returncode:raise ValueError('Geräteneustart ist auf diesem Pi noch nicht eingerichtet.')
        command=str(uuid.uuid4())
        self.prepare(app,command,version)
        save(self.marker,{'command':command,'expires':time.time()+60,'boot':self.boot_id()})
        try:
            result=runner(['systemd-run','--user','--collect','--on-active=2',
                '--unit=cdb-recorder-reboot','/usr/bin/sudo','-n','/usr/bin/systemctl','reboot'],
                capture_output=True,timeout=5)
            if result.returncode:raise ValueError('Neustart konnte nicht vorbereitet werden.')
        except Exception:
            self.release(command)
            raise
        return {'scheduled':True}
