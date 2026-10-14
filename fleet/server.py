"""Single-tenant portal. No shell, credentials, transcripts or audio in inventory.

Administrator secret is supplied via a private file, never a Brain user token.
Devices exchange single-use invitations for separately revocable credentials.
"""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import uuid
from .common import digest

ACTIONS = ('diagnose', 'restart-app', 'reboot', 'update')
FIELDS = {'version','activity','app_reachable','free_mb','temperature_c','memory_mb','wake_state','hardware','architecture','agent_version','update','last_result'}


class Registry:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS invitations(code TEXT PRIMARY KEY,name TEXT,expires REAL);
            CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,name TEXT,hardware TEXT,token TEXT UNIQUE,seen REAL,status TEXT,revoked INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,device TEXT,action TEXT,payload TEXT,created REAL,expires REAL,state TEXT,result TEXT);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,created REAL,event TEXT,device TEXT);
            ''')
        os.chmod(path,0o600)

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db: yield db
        finally: db.close()

    def invitation(self,name):
        if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('Gerätename fehlt (max. 80 Zeichen).')
        code=secrets.token_hex(6).upper()
        with self.db() as db:
            db.execute('DELETE FROM invitations WHERE expires<?',(self.clock(),))
            if db.execute('SELECT count(*) FROM invitations').fetchone()[0]>=50:raise ValueError('Zu viele offene Kopplungen.')
            db.execute('INSERT INTO invitations VALUES(?,?,?)',(digest(code),name.strip(),self.clock()+600))
        return {'code':code,'expires_in':600}

    def enroll(self,code,hardware):
        if not isinstance(hardware,str) or len(hardware)!=64:raise ValueError('Gerätekennung fehlt.')
        token=secrets.token_urlsafe(32);ident=str(uuid.uuid4())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            invitation=db.execute('SELECT * FROM invitations WHERE code=? AND expires>?',(digest(str(code).upper().replace('-','').replace(' ','')),self.clock())).fetchone()
            if not invitation:raise ValueError('Kopplungscode ungültig oder abgelaufen.')
            if db.execute('SELECT 1 FROM devices WHERE hardware=? AND revoked=0',(hardware,)).fetchone():raise ValueError('Gerät ist bereits gekoppelt. Alte Kopplung zuerst entfernen.')
            db.execute('DELETE FROM invitations WHERE code=?',(invitation['code'],))
            db.execute('INSERT INTO devices VALUES(?,?,?,?,?,?,0)',(ident,invitation['name'],hardware,digest(token),0,'{}'))
            db.execute('INSERT INTO audit(created,event,device) VALUES(?,?,?)',(self.clock(),'paired',ident))
        return {'id':ident,'name':invitation['name'],'token':token}

    def pulse(self,token,body):
        status=body.get('status',{})
        if not isinstance(status,dict) or len(json.dumps(status))>8192:raise ValueError('Status zu groß.')
        # Scalar allowlist: never accept log/message/history blobs from the app.
        status={k:v for k,v in status.items() if k in FIELDS and isinstance(v,(str,int,float,bool,type(None))) and len(str(v))<512}
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            device=db.execute('SELECT * FROM devices WHERE token=? AND revoked=0',(digest(token),)).fetchone()
            if not device or body.get('hardware')!=device['hardware']:raise PermissionError('Gerätekopplung ungültig.')
            ident=device['id']
            db.execute('UPDATE devices SET seen=?,status=? WHERE id=?',(self.clock(),json.dumps(status),ident))
            result=body.get('result')
            if result:
                if result.get('state') not in ('succeeded','failed','deferred','interrupted'):raise ValueError('Ungültiges Auftragsergebnis.')
                # No raw exception text/tokens allowed in remote diagnostics.
                detail=str(result.get('detail',''))[:160]
                db.execute("UPDATE commands SET state=?,result=? WHERE id=? AND device=? AND state='delivered'",(result['state'],detail,result.get('id'),ident))
            db.execute("UPDATE commands SET state='expired' WHERE device=? AND state='queued' AND expires<?",(ident,self.clock()))
            command=db.execute("SELECT * FROM commands WHERE device=? AND state IN ('queued','delivered') ORDER BY created LIMIT 1",(ident,)).fetchone()
            if command:
                db.execute("UPDATE commands SET state='delivered' WHERE id=?",(command['id'],))
                return {'command':{k:command[k] for k in ('id','action','expires')}|{'payload':json.loads(command['payload'])}}
        return {'command':None}

    def overview(self):
        with self.db() as db:
            devices=[{'id':r['id'],'name':r['name'],'online':self.clock()-r['seen']<100,'last_seen':r['seen'],'revoked':bool(r['revoked']),'status':json.loads(r['status'])} for r in db.execute('SELECT * FROM devices ORDER BY name')]
            commands=[dict(r) for r in db.execute('SELECT id,device,action,created,state,result FROM commands ORDER BY created DESC LIMIT 100')]
        return {'devices':devices,'commands':commands}

    def command(self,ident,action,payload):
        if action not in ACTIONS:raise ValueError('Unbekannter Auftrag.')
        if action=='update':
            if set(payload)!={'release'} or not isinstance(payload['release'],str) or not payload['release'].isalnum() or len(payload['release'])!=64:raise ValueError('Signierte Release-Kennung erforderlich.')
        elif payload:raise ValueError('Dieser Auftrag hat keine Parameter.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM devices WHERE id=? AND revoked=0',(ident,)).fetchone():raise ValueError('Gerät nicht verfügbar.')
            if db.execute("SELECT 1 FROM commands WHERE device=? AND state IN ('queued','delivered')",(ident,)).fetchone():raise ValueError('Ein Auftrag ist noch offen.')
            key=str(uuid.uuid4())
            db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?,?,?)',(key,ident,action,json.dumps(payload),self.clock(),self.clock()+600,'queued',''))
            db.execute('INSERT INTO audit(created,event,device) VALUES(?,?,?)',(self.clock(),action,ident))
        return {'id':key}

    def revoke(self,ident):
        with self.db() as db:
            db.execute('UPDATE devices SET revoked=1 WHERE id=?',(ident,))
            db.execute("UPDATE commands SET state='revoked' WHERE device=? AND state IN ('queued','delivered')",(ident,))
            db.execute('INSERT INTO audit(created,event,device) VALUES(?,?,?)',(self.clock(),'revoked',ident))
        return {'ok':True}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,value,mime='application/json'):
        data=json.dumps(value).encode() if mime=='application/json' else value
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(data)
    def do_GET(self):self.handle_request(False)
    def do_POST(self):self.handle_request(True)
    def handle_request(self,post):
        try:
            origin=self.headers.get('Origin')
            if origin and origin!=self.server.origin:raise PermissionError('Fremde Webseite abgewiesen.')
            path=self.path.split('?')[0]
            if not post and path=='/health':return self.send(200,{'ok':True,'service':'brain-fleet','version':'1'})
            if not post and path in ('/','/app.js','/style.css'):
                name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                return self.send(200,(Path(__file__).parent/'web'/name).read_bytes(),{'/':'text/html; charset=utf-8','/app.js':'text/javascript','/style.css':'text/css'}[path])
            token=self.headers.get('Authorization','').removeprefix('Bearer ')
            body={}
            if post:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384:raise ValueError('Ungültige Anfragegröße.')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise ValueError('Ungültige Anfrage.')
            if post and path=='/api/enroll':
                # Bounded global rate limit also covers deployments behind a proxy.
                with self.server.rate_lock:
                    now=time.monotonic();self.server.attempts=[t for t in self.server.attempts if now-t<60]
                    if len(self.server.attempts)>=20:return self.send(429,{'error':'Bitte in einer Minute erneut versuchen.'})
                    self.server.attempts.append(now)
                return self.send(200,self.server.registry.enroll(body.get('code'),body.get('hardware')))
            if post and path=='/api/pulse':return self.send(200,self.server.registry.pulse(token,body))
            if not post and path.startswith('/api/release/'):
                release=path.removeprefix('/api/release/')
                with self.server.registry.db() as db:
                    if not db.execute('SELECT 1 FROM devices WHERE token=? AND revoked=0',(digest(token),)).fetchone():raise PermissionError('Gerät nicht berechtigt.')
                if len(release)!=64 or any(c not in '0123456789abcdef' for c in release):raise ValueError('Release fehlt.')
                file=self.server.releases/(release+'.json')
                if not file.is_file():return self.send(404,{'error':'Release fehlt.'})
                return self.send(200,file.read_bytes(),'application/octet-stream')
            if not token or not hmac.compare_digest(digest(token),self.server.admin_hash):raise PermissionError('Bitte Verwaltungsschlüssel eingeben.')
            registry=self.server.registry
            if not post and path=='/api/overview':
                releases=[]
                for file in sorted(self.server.releases.glob('*.json'))[:100]:
                    try:
                        bundle=json.loads(file.read_bytes());m=bundle['manifest']
                        from .releases import canonical
                        import hashlib
                        if hashlib.sha256(canonical(m)).hexdigest()==file.stem and m['expires']>time.time():
                            releases.append({'id':file.stem,'version':m['version'],'sequence':m['sequence']})
                    except (OSError,ValueError,KeyError):pass
                return self.send(200,registry.overview()|{'releases':sorted(releases,key=lambda r:r['sequence'],reverse=True)})
            if post and path=='/api/invite':return self.send(200,registry.invitation(body.get('name')))
            if post and path=='/api/command':return self.send(200,registry.command(body.get('device'),body.get('action'),body.get('payload',{})))
            if post and path=='/api/revoke':return self.send(200,registry.revoke(body.get('device')))
            self.send(404,{'error':'Nicht gefunden.'})
        except PermissionError as e:self.send(403,{'error':str(e)})
        except (ValueError,TypeError,KeyError):self.send(400,{'error':'Anfrage nicht möglich. Code, Gerät und offene Aufträge prüfen.'})
        except Exception:self.send(500,{'error':'Dienst vorübergehend nicht verfügbar.'})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',required=True);parser.add_argument('--admin-file',required=True);parser.add_argument('--origin',required=True);parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8460)
    args=parser.parse_args();os.umask(0o077)
    admin=Path(args.admin_file).read_text().strip()
    if len(admin)<32:raise ValueError('Verwaltungsschlüssel muss mindestens 32 Zeichen haben.')
    server=ThreadingHTTPServer((args.host,args.port),Handler);server.registry=Registry(Path(args.data)/'fleet.sqlite3');server.admin_hash=digest(admin);server.origin=args.origin;server.attempts=[];server.rate_lock=threading.Lock()
    server.releases=Path(args.data)/'releases';server.releases.mkdir(exist_ok=True)
    server.serve_forever()

if __name__=='__main__':main()
