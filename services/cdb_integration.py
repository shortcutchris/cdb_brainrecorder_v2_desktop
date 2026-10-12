"""CDB public-client authentication, inference adapters and durable text publication.

No credentials leave the Python backend. Public model downloads remain independent.
"""
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from meeting_recorder.core import atomic_write
from meeting_recorder.processing import LocalModels, Interrupted

SCOPE = 'api://bfc31465-9282-4d18-8a6a-f3007b42832f/access_as_user offline_access'
AUTH = 'https://login.microsoftonline.com/organizations/oauth2/v2.0/'
DEFAULT = {'server':'https://staging.cdbos.de','client_id':'465abd84-272e-4606-b21c-b7e27e09b6d2',
           'transcription':'local','summary':'local'}
USER_AGENT = 'CDB-Recorder/0.5.0'
UUID = re.compile(r'^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$')

class CdbFailure(ValueError):
    pass

class Transport:
    def request(self, url, body=None, token=None, form=False):
        headers={'Accept':'application/json','User-Agent':USER_AGENT}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:
            data=urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
            headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
        else:data=None
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args):return None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        try:
            with opener.open(urllib.request.Request(url,data=data,headers=headers),timeout=90) as r:
                return json.loads(r.read(4_000_001))
        except urllib.error.HTTPError as e:
            if form:
                try:code=json.loads(e.read(65536)).get('error','')
                except (ValueError,OSError):code=''
                raise CdbFailure(code if code in ('authorization_pending','slow_down','expired_token','authorization_declined') else 'Microsoft-Anmeldung abgelehnt. Firmenfreigabe und App-Konfiguration prüfen.') from None
            raise CdbFailure({401:'Bitte erneut bei Microsoft anmelden.',403:'Keine Berechtigung für diese CDB-Aktion.',409:'Übertragung unklar oder bereits vorhanden. Nicht blind erneut senden.',429:'CDB ausgelastet. Später erneut versuchen.'}.get(e.code,f'CDB-Anfrage fehlgeschlagen (HTTP {e.code}).')) from None
        except (OSError,ValueError):raise CdbFailure('CDB nicht erreichbar oder Antwort ungültig.') from None

    def upload(self, server, token, path, client_id, filename, stopping):
        boundary='cdb'+secrets.token_hex(16)
        head=(f'--{boundary}\r\nContent-Disposition: form-data; name="client_id"\r\n\r\n{client_id}\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: audio/ogg\r\n\r\n').encode()
        tail=f'\r\n--{boundary}--\r\n'.encode()
        connection=http.client.HTTPSConnection(urllib.parse.urlsplit(server).hostname,timeout=90)
        try:
            connection.putrequest('POST','/api/v1/tqs/audio/upload')
            for key,value in {'Authorization':'Bearer '+token,'User-Agent':USER_AGENT,'Content-Type':'multipart/form-data; boundary='+boundary,'Content-Length':str(len(head)+path.stat().st_size+len(tail))}.items():connection.putheader(key,value)
            connection.endheaders();connection.send(head)
            with path.open('rb') as f:
                while block:=f.read(65536):
                    if stopping.is_set():raise Interrupted()
                    connection.send(block)
            connection.send(tail);r=connection.getresponse()
            if r.status not in (200,201,202):raise CdbFailure(f'Audioübertragung fehlgeschlagen (HTTP {r.status}).')
            return json.loads(r.read(1_000_000))
        except (OSError,ValueError) as e:
            if isinstance(e,CdbFailure):raise
            raise CdbFailure('Audioübertragung unklar. Erneut versuchen gleicht zuerst die Aufnahmen ab.') from None
        finally:connection.close()

class CdbService:
    def __init__(self, root, transport=None):
        self.root=Path(root)/'cdb';self.root.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(self.root,0o700)
        self.transport=transport or Transport();self.lock=threading.RLock();self.stopping=threading.Event()
        self.login={'state':'idle'};self.generation=0;self.progress='';self.threads=[]
        self.path=self.root/'publications.sqlite3'
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, payload TEXT, state TEXT, receipt TEXT, error TEXT)')
            db.execute("UPDATE publications SET state='uncertain',error='Neustart während Übertragung. Empfang zuerst prüfen.' WHERE state='sending'")
        os.chmod(self.path,0o600)
    @contextlib.contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=30)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:yield db
        finally:db.close()
    def read(self,name,default):
        path=self.root/name
        return json.loads(path.read_text()) if path.exists() else default
    def write(self,name,value):
        with self.lock:
            atomic_write(self.root/name,json.dumps(value,ensure_ascii=False));os.chmod(self.root/name,0o600)
    def config(self):return DEFAULT|self.read('config.json',{})
    def configure(self,changes):
        if set(changes)-set(DEFAULT):raise CdbFailure('Unbekannte CDB-Einstellung.')
        c=self.config()|changes
        if c['server'] not in ('https://staging.cdbos.de','https://cdbos.de'):raise CdbFailure('Bekannte CDB-Umgebung wählen.')
        if not isinstance(c['client_id'],str) or not UUID.fullmatch(c['client_id']):raise CdbFailure('Ungültige Firmen-App-ID.')
        if any(c[k] not in ('local','cdb') for k in ('transcription','summary')):raise CdbFailure('Verarbeitung wählen: lokal oder CDB.')
        with self.lock:
            if (c['server'],c['client_id'])!=(self.config()['server'],self.config()['client_id']):self.logout()
            if 'cdb' in (c['transcription'],c['summary']):self.session()
            self.write('config.json',c)
        return self.public()
    def logout(self):
        with self.lock:
            self.generation+=1;self.write('session.json',{});self.login={'state':'idle'}
    def identity(self,server,token):
        r=self.transport.request(server+'/api/v1/auth/me',token=token)
        if r.get('is_active') is not True or not isinstance(r.get('user_id'),str) or not UUID.fullmatch(r.get('client_id') or ''):raise CdbFailure('CDB-Benutzer oder Mandant nicht bestätigt.')
        return {'user_id':r['user_id'],'client_id':r['client_id'],'name':r.get('display_name') or r.get('email') or 'Firmenkonto'}
    def save_token(self,r,c,previous=None):
        if not isinstance(r.get('access_token'),str) or r.get('token_type','').lower()!='bearer' or not isinstance(r.get('expires_in'),(int,float)) or r['expires_in']<=60:raise CdbFailure('Microsoft-Antwort ungültig.')
        identity=self.identity(c['server'],r['access_token'])
        if previous and identity|{'name':''} != previous['identity']|{'name':''}:raise CdbFailure('Firmenkonto hat sich geändert. Neu anmelden.')
        session={'server':c['server'],'client_id':c['client_id'],'token':r['access_token'],'refresh':r.get('refresh_token') or (previous or {}).get('refresh'), 'expires':time.time()+r['expires_in'],'identity':identity}
        self.write('session.json',session);return session
    def session(self,binding=None):
        with self.lock:
            s=self.read('session.json',{});c=self.config()
            if not s or s['server']!=c['server'] or s['client_id']!=c['client_id']:raise CdbFailure('Bitte zuerst mit Microsoft anmelden.')
            if binding and binding!={'server':s['server'],**{k:s['identity'][k] for k in ('user_id','client_id')}}:raise CdbFailure('Auftrag gehört zu einem anderen Firmenkonto. Passendes Konto anmelden.')
            if s['expires']<time.time()+60:
                if not s.get('refresh'):raise CdbFailure('Bitte erneut mit Microsoft anmelden.')
                r=self.transport.request(AUTH+'token',{'client_id':s['client_id'],'scope':SCOPE,'grant_type':'refresh_token','refresh_token':s['refresh']},form=True)
                s=self.save_token(r,c,s)
            return s
    def snapshot(self):
        c=self.config();binding=None
        if 'cdb' in (c['transcription'],c['summary']):
            s=self.session();binding={'server':s['server'],**{k:s['identity'][k] for k in ('user_id','client_id')}}
        return {k:c[k] for k in ('transcription','summary')}|{'binding':binding}
    def start_login(self):
        with self.lock:
            if self.login['state']=='pending':return self.public()
            c=self.config();r=self.transport.request(AUTH+'devicecode',{'client_id':c['client_id'],'scope':SCOPE},form=True)
            if not all(isinstance(r.get(k),str) and r[k] for k in ('device_code','user_code','verification_uri')) or r['verification_uri'] not in ('https://microsoft.com/devicelogin','https://login.microsoft.com/device'):raise CdbFailure('Microsoft-Geräteanmeldung nicht verfügbar.')
            self.generation+=1;generation=self.generation
            self.login={'state':'pending','code':r['user_code'],'url':r['verification_uri'],'expires':time.time()+min(float(r.get('expires_in',900)),1800)}
            self.thread(self.poll_login,r,c,generation)
            return self.public()
    def thread(self,target,*args):
        t=threading.Thread(target=target,args=args,daemon=True);self.threads.append(t);t.start()
    def poll_login(self,r,c,generation):
        interval=max(5,float(r.get('interval',5)))
        while not self.stopping.wait(interval):
            with self.lock:
                if generation!=self.generation:return
                if time.time()>=self.login['expires']:self.login={'state':'error','message':'Anmeldecode abgelaufen. Erneut anmelden.'};return
            try:
                token=self.transport.request(AUTH+'token',{'client_id':c['client_id'],'grant_type':'urn:ietf:params:oauth:grant-type:device_code','device_code':r['device_code']},form=True)
                with self.lock:
                    if generation!=self.generation:return
                    self.save_token(token,c);self.login={'state':'completed'}
                return
            except CdbFailure as e:
                if str(e)=='authorization_pending':continue
                if str(e)=='slow_down':interval+=5;continue
                with self.lock:
                    if generation==self.generation:self.login={'state':'error','message':str(e)}
                return
    def public(self):
        with self.lock:
            s=self.read('session.json',{});identity=s.get('identity');login=dict(self.login)
        with self.db() as db:
            jobs=[{'id':r[0],'title':json.loads(r[1])['title'],'state':r[2],'error':r[3]} for r in db.execute('SELECT id,payload,state,error FROM publications ORDER BY rowid DESC LIMIT 30')]
        destination=self.read('destination.json',{})
        binding={'server':s.get('server'),**{k:(identity or {}).get(k) for k in ('user_id','client_id')}}
        if destination.get('binding')!=binding:destination={}
        return {'destination':destination.get('area'),'config':self.config(),'identity':identity,'login':login,'publications':jobs,'progress':self.progress}
    def call(self,path,body=None,binding=None):
        s=self.session(binding);return self.transport.request(s['server']+path,body,token=s['token'])
    def areas(self,binding=None):
        r=self.call('/api/v1/tqs/knowledge-areas?active_only=true',binding=binding)
        rows=r if isinstance(r,list) else r.get('knowledge_areas',r.get('items',[]))
        if not isinstance(rows,list):raise CdbFailure('Bereichsliste ungültig.')
        out=[];names=set();ids=set()
        for a in rows:
            if not isinstance(a,dict) or not UUID.fullmatch(a.get('id','')) or not isinstance(a.get('name'),str):raise CdbFailure('Bereichsantwort ungültig.')
            if a['id'] in ids or a['name'] in names or a.get('is_active') is not True:raise CdbFailure('Bereiche nicht eindeutig oder nicht aktiv.')
            ids.add(a['id']);names.add(a['name'])
            out.append({'id':a['id'],'name':a['name'],'label':a.get('display_name') or a['name'],'client_id':a.get('client_id'),'global':a.get('is_global',False)})
        return out
    def select_area(self,area_id):
        s=self.session();binding={'server':s['server'],**{k:s['identity'][k] for k in ('user_id','client_id')}}
        area=next((a for a in self.areas(binding) if a['id']==area_id),None)
        if not area:raise CdbFailure('Zielbereich nicht verfügbar.')
        self.write('destination.json',{'binding':binding,'area':area})
        return self.public()
    def enqueue(self,row,area_id):
        if row['transcription_status'] in ('recording','importing','queued','transcribing','summarizing'):raise CdbFailure('Verarbeitung zuerst abschließen.')
        s=self.session();binding={'server':s['server'],**{k:s['identity'][k] for k in ('user_id','client_id')}}
        areas=self.areas(binding);matches=[a for a in areas if a['id']==area_id]
        if len(matches)!=1:raise CdbFailure('Zielbereich nicht mehr verfügbar.')
        a=matches[0];client=a['client_id'] or (s['identity']['client_id'] if a['global'] else None)
        if not client or not UUID.fullmatch(client):raise CdbFailure('Zielmandant nicht bestätigt.')
        text='\n\n'.join('## '+label+'\n\n'+row[key].strip() for label,key in [('Zusammenfassung','summary_text'),('Transkript','transcript_text'),('Notizen','notes')] if row.get(key,'').strip())
        if not text or len(text)>1_000_000:raise CdbFailure('Kein Text oder Inhalt zu groß.')
        payload={'binding':binding,'area':a,'client':client,'title':row['title'],'content':text}
        fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        with self.db() as db:
            existing=db.execute('SELECT id FROM publications WHERE fingerprint=?',(fingerprint,)).fetchone()
            if existing:return {'id':existing[0]}
            ident=uuid.uuid4().hex;db.execute('INSERT INTO publications VALUES(?,?,?,?,?,?)',(ident,fingerprint,json.dumps(payload),'queued','', ''))
        return {'id':ident}
    def publication_once(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');r=db.execute("SELECT id,payload FROM publications WHERE state IN ('queued','accepted') ORDER BY rowid LIMIT 1").fetchone()
            if not r:return
            ident,payload=r[0],json.loads(r[1]);old=db.execute('SELECT state,receipt FROM publications WHERE id=?',(ident,)).fetchone()
        try:
            binding=payload['binding'];self.session(binding)
            if old[0]=='queued':
                areas=self.areas(binding)
                if payload['area'] not in areas:raise CdbFailure('Zielbereich wurde geändert. Übertragung prüfen.')
                with self.db() as db:db.execute("UPDATE publications SET state='sending' WHERE id=?",(ident,))
                result=self.call('/api/v1/tqs/documents/ingest',{'knowledge_area':payload['area']['name'],'client_id':payload['client'],'title':payload['title'],'content':payload['content'],'source':'raspberry_pi_recorder','origin':'ai_generated','auto_verify_tl1':False},binding)
                document=result.get('document_id');job=result.get('job_id')
                if not isinstance(document,str) or not UUID.fullmatch(document) or not isinstance(job,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',job):raise CdbFailure('Empfang nicht eindeutig bestätigt. Im CDB prüfen.')
                receipt={'document_id':document,'job_id':job}
                with self.db() as db:db.execute("UPDATE publications SET state='accepted',receipt=? WHERE id=?",(json.dumps(receipt),ident))
            else:receipt=json.loads(old[1])
            status=self.call('/api/v1/tqs/jobs/'+urllib.parse.quote(receipt['job_id'],safe=''),binding=binding)
            if status.get('job_id')!=receipt['job_id'] or status.get('document_id')!=receipt['document_id']:raise CdbFailure('Verarbeitungsstatus gehört zu einem anderen Dokument.')
            state=status.get('status')
            if state in ('completed','completed_without_graph','failed'):
                with self.db() as db:db.execute('UPDATE publications SET state=?,error=? WHERE id=?',(state,'CDB-Verarbeitung fehlgeschlagen.' if state=='failed' else '',ident))
        except (CdbFailure,OSError,ValueError):
            # Never repeat a dispatched write after an ambiguous answer.
            with self.db() as db:
                current=db.execute('SELECT state FROM publications WHERE id=?',(ident,)).fetchone()[0]
                if current=='sending':db.execute("UPDATE publications SET state='uncertain',error='Empfang unklar. Im CDB prüfen; kein automatischer Neuversand.' WHERE id=?",(ident,))
                else:db.execute('UPDATE publications SET error=? WHERE id=?',('Verbindung, Anmeldung oder Ziel prüfen. Auftrag bleibt erhalten.',ident))
    def run(self):
        while not self.stopping.wait(5):self.publication_once()
    def close(self):
        self.stopping.set();self.generation+=1

class CdbBackend:
    def __init__(self,service):
        self.service=service;self.stopping=service.stopping;self.local=LocalModels(self.stopping);self.store=None
    def route(self,folder,c):
        p=folder/'cdb-request.json'
        return json.loads(p.read_text()) if p.exists() and not c.get('model_test') else {'transcription':'local','summary':'local'}
    def transcribe(self,folder,c):
        self.service.progress=''
        route=self.route(folder,c)
        if route['transcription']=='local':
            result=self.local.transcribe(folder,c);self.last_asr_peak_mib=self.local.last_asr_peak_mib;return result
        self.last_asr_peak_mib=None
        try:
            result=self.remote_transcribe(folder,route,c.get('process_timeout',21600));c['whisper_model']='cdb/transcription-jobs';return result
        finally:self.service.progress=''
    def remote_transcribe(self,folder,route,timeout=21600):
        deadline=time.monotonic()+timeout
        service=self.service;binding=route['binding'];service.session(binding)
        checkpoint=folder/'cdb-asr.json';saved=json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
        def remember():atomic_write(checkpoint,json.dumps(saved))
        if not saved.get('recording_id'):
            opus=folder/'cdb-upload.ogg';name='pi-'+folder.name+'.ogg'
            if saved.get('sent'):
                rows=service.call('/api/v1/tqs/audio/recordings',binding=binding)
                rows=rows if isinstance(rows,list) else rows.get('recordings',[])
                matches=[r for r in rows if r.get('filename')==name]
                if len(matches)==1:saved['recording_id']=matches[0]['id'];remember()
                else:raise CdbFailure('Vorherige Audioübertragung unklar. Aufnahme im CDB prüfen; kein erneuter Upload.')
            else:
                self.service.progress='Audio für CDB vorbereiten'
                from meeting_recorder.child_process import owned_command
                proc=subprocess.Popen(owned_command(['ffmpeg','-nostdin','-v','error','-y','-i',str(folder/'audio.wav'),'-c:a','libopus','-b:a','32k',str(opus)]),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                while proc.poll() is None:
                    if self.stopping.wait(.2):proc.terminate();proc.wait();raise Interrupted()
                if proc.returncode or not opus.exists() or opus.stat().st_size>95*1024**2:raise CdbFailure('Audio konnte nicht für CDB vorbereitet werden.')
                s=service.session(binding);saved['sent']=True;remember();service.progress='Audio wird ins CDB übertragen'
                result=service.transport.upload(s['server'],s['token'],opus,binding['client_id'],name,self.stopping)
                ident=result.get('id') or result.get('recording_id')
                if not isinstance(ident,str) or not UUID.fullmatch(ident):raise CdbFailure('Audioempfang nicht bestätigt.')
                saved['recording_id']=ident;remember()
        if not saved.get('job_id'):
            result=service.call('/api/v1/tqs/audio/recordings/'+saved['recording_id']+'/transcription-jobs',{'language':'de-DE'},binding)
            ident=result.get('job_id')
            if result.get('recording_id')!=saved['recording_id'] or not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',ident):raise CdbFailure('Transkriptionsauftrag nicht bestätigt.')
            saved['job_id']=ident;remember()
        while not self.stopping.is_set():
            r=service.call('/api/v1/tqs/audio/transcription-jobs/'+saved['job_id'],binding=binding)
            if r.get('job_id')!=saved['job_id'] or r.get('recording_id')!=saved['recording_id']:raise CdbFailure('Falscher Transkriptionsauftrag.')
            if time.monotonic()>deadline:raise CdbFailure('CDB-Transkriptions-Zeitlimit erreicht. Serverauftrag bleibt für einen Wiederanlauf gespeichert.')
            p=r.get('progress') or {};percent=p.get('percent');service.progress='CDB: '+str(p.get('stage') or r.get('status'))+(f' · {round(percent)} %' if isinstance(percent,(int,float)) else '')
            if r.get('status')=='completed':
                text=(r.get('result') or {}).get('text')
                if not isinstance(text,str) or not text.strip():raise CdbFailure('CDB hat keinen Text erkannt.')
                service.progress='';return text.strip()
            if r.get('status')=='failed':
                saved.pop('job_id',None);remember()
                raise CdbFailure('CDB-Transkription fehlgeschlagen. Erneut versuchen startet einen neuen Serverauftrag.')
            if self.stopping.wait(5):raise Interrupted()
        raise Interrupted()
    def generate(self,text,c,merge=False):
        if self.store is None:
            from meeting_recorder.core import Store
            self.store=Store(self.service.root.parent)
        jobs=[j for j in self.store.list() if j['state']=='summarizing']
        route=self.route(self.store.folder(jobs[0]['id']),c) if len(jobs)==1 else {'summary':'local'}
        if route['summary']=='local':return self.local.generate(text,c,merge)
        r=self.service.call('/api/v1/tqs/agent/structure-text',{'text':text,'instructions':('Führe Teilprotokolle zusammen. ' if merge else '')+'Erstelle ein knappes deutsches Meetingprotokoll. Erfinde keine Fakten oder Aufgaben. Markiere Unklarheiten. '+c.get('prompt','')[:4000],'max_tokens':1500,'temperature':0.1},route['binding'])
        if r.get('stop_reason') in ('length','max_tokens') or not isinstance(r.get('content'),str) or not r['content'].strip():raise CdbFailure('CDB-Zusammenfassung leer oder abgeschnitten.')
        c['summary_model']='cdb/agent-structure-text'
        return r['content'].strip()
