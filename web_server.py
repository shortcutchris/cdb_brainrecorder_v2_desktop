"""Studio HTTP adapter for the existing native data and shared DesktopEngine.

Loopback only. No second recorder, worker, model pipeline or session database.
"""
import argparse
import hashlib
import hmac
import json
import logging
import mimetypes
import os
from pathlib import Path
import secrets
import signal
import subprocess
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from data.repo import SessionRepository
from services.local_controller import LocalController
from settings import SettingsManager
from meeting_recorder.audio import devices
from meeting_recorder.core import atomic_write
from meeting_recorder.server import Handler, Server, App as SharedWebApp
from meeting_recorder.child_process import owned_command

VERSION = '0.4.0'
STATIC = Path(__file__).parent/'studio'
FIELDS = ('title', 'notes', 'transcript_text', 'summary_text')
BUSY = ('recording', 'importing', 'queued', 'transcribing', 'summarizing')


class Conflict(ValueError): pass


class StudioApp:
    def __init__(self, root, database, backend=None, command_factory=None, preview=False):
        self.repo = SessionRepository(str(database))
        self.controller = LocalController(self.repo, root, backend=backend, command_factory=command_factory)
        self.engine = self.controller.engine
        self.store, self.models, self.probe = self.engine.store, self.engine.models, self.engine.probe
        self.token = ''
        self.csrf = secrets.token_urlsafe(32)
        self.preview = preview
        self.settings_lock = threading.RLock()
        self.control_lock = threading.RLock()
        self.closing = False
        self.model_test = None

    def audio_devices(self): return devices()
    def setup_state(self): return SharedWebApp.setup_state(self)

    def state(self):
        with self.controller.lock:
            self.controller.sync()
            state = self.engine.state()
            rows = self.repo.get_all()
            state['sessions'] = [{k:r.get(k) for k in ('id','title','recorded_at','duration_sec',
                'samplerate','channels','transcription_status','local_job_id','local_error')}
                | {'has_audio': bool(r.get('path') and Path(r['path']).is_file())} for r in rows]
        raw = b''
        ident = state['recording']['id']
        if ident:
            path = self.store.folder(ident)/'audio.pcm'
            try:
                with path.open('rb') as f:
                    f.seek(max(0,path.stat().st_size-32000));raw=f.read(32000)
            except OSError: pass
        # Actual bounded PCM measurements, never decorative fake microphone levels.
        if raw:
            import numpy as np
            samples = np.frombuffer(raw[:len(raw)//2*2],dtype='<i2').astype('float32')/32768
            state['waveform'] = [float(abs(chunk).max()) if len(chunk) else 0 for chunk in np.array_split(samples,64)]
        else: state['waveform'] = [0]*64
        state['level'] = self.probe.level(raw) if raw else 0
        state.update(csrf=self.csrf, version=VERSION, preview=self.preview,
            namespace=hashlib.sha256(str(self.store.root).encode()).hexdigest()[:16])
        if self.model_test:
            job = self.store.get(self.model_test)
            state['model_test'] = job | self.engine.result(self.model_test)
        return state

    def session(self, sid):
        with self.controller.lock:
            self.controller.sync()
            row = self.repo.get_by_id(sid)
        if not row: raise KeyError('Meeting fehlt.')
        return row

    def save(self, sid, changes, base):
        if not isinstance(changes,dict) or not changes or set(changes)-set(FIELDS):
            raise ValueError('Ungültige Textfelder.')
        if not isinstance(base,dict) or set(changes)-set(base): raise ValueError('Textbasis fehlt.')
        if any(not isinstance(v,str) or len(v)>1_000_000 for v in changes.values()):
            raise ValueError('Text ist ungültig oder zu groß.')
        with self.controller.lock:
            self.controller.sync()
            with self.repo.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                db.row_factory = __import__('sqlite3').Row
                row = db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
                if not row: raise KeyError('Meeting fehlt.')
                if row['transcription_status'] in BUSY and set(changes)-{'title','notes'}:
                    raise Conflict('KI-Texte erst nach Abschluss bearbeiten. Entwurf bleibt erhalten.')
                if any((row[k] or '') != base[k] for k in changes):
                    raise Conflict('Text wurde zwischenzeitlich geändert. Entwurf bleibt erhalten; zuerst exportieren und vergleichen.')
                db.execute('UPDATE sessions SET '+','.join(k+'=?' for k in changes)+' WHERE id=?',
                           [*changes.values(),sid])
        return self.session(sid)

    def prompts(self):
        with self.settings_lock:
            settings=SettingsManager();settings.settings.sync()
            return settings.get_all_prompts()

    def mutate_prompt(self, body):
        with self.settings_lock:
            settings=SettingsManager();settings.settings.sync()
            action=body.get('action');ident=body.get('id')
            if action in ('update','delete'):
                current=settings.get_prompt_by_id(ident)
                if not current or current.get('is_default'):raise ValueError('Standardprompt bleibt unverändert. Eigenen Prompt anlegen.')
            if action != 'delete':
                if not isinstance(body.get('name'),str) or not 1<=len(body['name'].strip())<=120:raise ValueError('Promptname fehlt.')
                if not isinstance(body.get('text'),str) or not 1<=len(body['text'])<=16000:raise ValueError('Prompttext fehlt oder ist zu lang.')
            if action=='add':settings.add_prompt(body['name'].strip(),body['text'])
            elif action=='update':settings.update_prompt(ident,body['name'].strip(),body['text'])
            elif action=='delete':settings.delete_prompt(ident)
            else:raise ValueError('Unbekannte Promptaktion.')
            settings.settings.sync()
            if settings.settings.status()!=settings.settings.Status.NoError:raise OSError('Prompts konnten nicht gespeichert werden.')
            return settings.get_all_prompts()

    def start_model_test(self):
        if self.model_test and self.store.get(self.model_test)['state'] not in ('completed','failed'):
            raise ValueError('Modelltest läuft bereits.')
        folder=self.store.root/'model-test';folder.mkdir(exist_ok=True)
        text='Dies ist ein technischer Modelltest. Anna erstellt bis Donnerstag eine Aufgabenliste. Fortsetzung am Freitag um zehn Uhr. Die Kosten sind ungeklärt.'
        subprocess.run(owned_command(['espeak-ng','-v','de','-s','145','-w',str(folder/'spoken.wav'),text]),
                       check=True,timeout=30,capture_output=True)
        with self.controller.lock:
            ident=self.engine.enqueue(folder/'spoken.wav','Technischer Modelltest · künstliche Sprache')
            with self.store.db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS hidden_jobs (id TEXT PRIMARY KEY)')
                db.execute('INSERT OR IGNORE INTO hidden_jobs VALUES(?)',(ident,))
            self.model_test=ident
            atomic_write(folder/'expected.txt',text)
        return {'id':ident}

    def action(self, path, body):
        with self.control_lock:
            if self.closing:raise ValueError('Dienst wird beendet. Änderungen bitte kurz aufbewahren.')
            if path=='/api/record/start':
                if not self.store.config()['setup_complete']:raise ValueError('Kein getestetes Mikrofon. Bitte Einstellungen öffnen und Audio-Einrichtung abschließen.')
                if self.engine.recorder.active:raise ValueError('Aufnahme läuft bereits.')
                return {'id':self.engine.start('')}
            if path=='/api/record/stop':
                ident=self.engine.stop();self.controller.sync();return {'id':ident}
            if path=='/api/settings':
                if set(body)-{'device','whisper_binary','whisper_model','summary_model','threads'}:raise ValueError('Unbekannte Einstellung.')
                return self.engine.configure(body|{'setup_complete':False})
            if path=='/api/models/install':return self.models.install(body.get('backend'),body.get('model'))
            if path=='/api/models/test':return self.start_model_test()
            if path=='/api/microphone/test':return self.probe.start()
            if path=='/api/setup/complete':
                if not self.setup_state()['ready']:raise ValueError('Einrichtung noch nicht bereit. Offene Punkte prüfen.')
                return self.engine.configure({'setup_complete':True})
            if path=='/api/prompts':return self.mutate_prompt(body)
            parts=path.strip('/').split('/')
            if len(parts)==4 and parts[:2]==['api','sessions']:
                sid=int(parts[2]);session=self.session(sid)
                if parts[3]=='save':return self.save(sid,body.get('changes'),body.get('base'))
                if parts[3]=='process':
                    prompt=next((p for p in self.prompts() if p['id']==body.get('prompt')),None)
                    if not prompt:raise ValueError('Prompt fehlt.')
                    return {'id':self.controller.process(sid,prompt['prompt_text'],reuse_transcript=not body.get('transcribe_again',False))}
                if parts[3]=='retry':
                    if session.get('local_job_id'):self.engine.retry(session['local_job_id']);return {'ok':True}
                    return {'id':self.controller.process(sid)}
                if parts[3]=='delete':return self.controller.delete(sid)
            raise KeyError('Unbekannte Aktion.')

    def close(self):
        with self.control_lock:
            self.closing=True
            if self.engine.recorder.active:self.engine.stop()
            self.controller.sync()
            self.engine.close()


class StudioHandler(Handler):
    def get(self):
        if not self.authorized():return
        path=urlsplit(self.path).path
        if path=='/favicon.ico':
            self.send_response(204);self.headers_base('image/x-icon',0);self.end_headers();return
        if path=='/api/state':self.respond(self.server.app.state());return
        if path=='/api/prompts':self.respond(self.server.app.prompts());return
        if path=='/api/search':
            from urllib.parse import parse_qs
            query=parse_qs(urlsplit(self.path).query).get('q',[''])[0][:1000]
            self.respond([{k:r[k] for k in ('id','title','recorded_at')} for r in self.server.app.repo.get_all(query)]);return
        if path.startswith('/api/sessions/'):
            parts=path.strip('/').split('/')
            if len(parts) not in (3,4):raise KeyError('Unbekannte Datei.')
            row=self.server.app.session(int(parts[2]))
            if len(parts)==3:self.respond(row);return
            if parts[3]=='peaks':
                import wave, array
                peaks=[]
                try:
                    with wave.open(row['path'],'rb') as f:
                        if f.getsampwidth()!=2:raise ValueError('Unsupported audio width')
                        total=f.getnframes()
                        for i in range(64):
                            f.setpos(min(max(0,total-128),total*i//64))
                            data=array.array('h',f.readframes(128))
                            peaks.append(max((abs(n)/32768 for n in data),default=0))
                except (OSError,ValueError,wave.Error):peaks=[0]*64
                self.respond(peaks);return
            if parts[3]=='audio':self.serve_file(Path(row['path']),'audio/wav',ranges=True);return
            if parts[3]=='export':
                text='# '+row['title']+'\n\n'+'\n\n'.join('## '+title+'\n\n'+(row.get(key) or '')
                    for title,key in [('Notizen','notes'),('Transkript','transcript_text'),('Zusammenfassung','summary_text')])
                self.send_response(200);self.headers_base('text/markdown; charset=utf-8',len(text.encode()))
                self.send_header('Content-Disposition',f'attachment; filename="meeting-{row["id"]}.md"')
                self.end_headers();self.wfile.write(text.encode());return
            raise KeyError('Unbekannte Datei.')
        if path=='/api/microphone/audio':self.serve_file(self.server.app.probe.folder/'audio.wav','audio/wav',ranges=True);return
        if path.startswith('/api/'):
            super().get();return
        relative='index.html' if path=='/' else path.lstrip('/')
        file=(STATIC/relative).resolve()
        if not file.is_relative_to(STATIC.resolve()) or not file.is_file():raise KeyError('Datei fehlt.')
        self.serve_file(file,mimetypes.guess_type(file.name)[0] or 'application/octet-stream')

    def headers_base(self,mime,length):
        super().headers_base(mime,length)
        self.send_header('Permissions-Policy','microphone=(), camera=()')

    def serve_file(self,path,mime,ranges=False):
        if not path.is_file():raise KeyError('Audiodatei fehlt.' if ranges else 'Datei fehlt.')
        size=path.stat().st_size;start=0;end=size-1;status=200
        value=self.headers.get('Range') if ranges else None
        if value:
            import re
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
            if not match or not any(match.groups()):raise ValueError('Ungültiger Audiobereich.')
            first,last=match.groups()
            if first:start=int(first);end=min(int(last),end) if last else end
            else:start=max(0,size-int(last))
            if start>=size or start>end:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
            status=206
        length=max(0,end-start+1)
        self.send_response(status);self.headers_base(mime,length)
        if ranges:self.send_header('Accept-Ranges','bytes')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with path.open('rb') as source:
            source.seek(start)
            while length:
                block=source.read(min(length,65536))
                if not block:break
                self.wfile.write(block);length-=len(block)

    def do_POST(self):
        try:
            if not self.authorized():return
            origin=self.headers.get('Origin')
            if origin and origin!='http://'+self.headers.get('Host',''):
                self.respond({'error':'Fremder Ursprung nicht erlaubt.'},403);return
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),self.server.app.csrf):
                self.respond({'error':'Sitzung ungültig. Seite neu laden; Entwürfe bleiben lokal erhalten.'},403);return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=4_000_000:self.respond({'error':'Anfrage zu groß.'},413);return
            body=json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(body,dict):raise ValueError('JSON-Objekt erwartet.')
            self.respond(self.server.app.action(urlsplit(self.path).path,body))
        except (BrokenPipeError,ConnectionResetError):pass
        except Conflict as e:self.respond({'error':str(e)},409)
        except (ValueError,KeyError) as e:self.respond({'error':str(e)},400)
        except Exception:
            logging.exception('Aktion fehlgeschlagen')
            self.respond({'error':'Aktion fehlgeschlagen. Dienstprotokoll prüfen; Entwurf bleibt erhalten.'},500)


class StudioServer(Server):
    def __init__(self,address,app):
        if address[0]!='127.0.0.1':raise ValueError('Studio ist ausschließlich lokal erreichbar. Für Fernzugriff SSH-Tunnel verwenden.')
        self.app=app
        ThreadingHTTPServer.__init__(self,address,StudioHandler)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8088)
    parser.add_argument('--root',default=str(Path.home()/'.local/share/cdb-recorder-local'))
    parser.add_argument('--database',default='data/sessions.db')
    args=parser.parse_args()
    os.umask(0o077)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    app=StudioApp(args.root,args.database)
    server=StudioServer(('127.0.0.1',args.port),app);server.timeout=.5
    stopping=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stopping.set())
    signal.signal(signal.SIGINT,lambda *_:stopping.set())
    try:
        while not stopping.is_set():server.handle_request()
    finally:
        server.server_close();app.close()

if __name__=='__main__':main()
