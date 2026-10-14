"""Private local control boundary between Studio and the independent agent."""
import hmac
import os
from pathlib import Path
import secrets
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
        return transaction or marker.get('expires',0)>time.time()

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
        save(self.root/'enroll.json',{'code':code})
        return {'ok':True}
