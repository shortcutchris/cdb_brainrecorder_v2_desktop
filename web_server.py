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
import shutil
import signal
import subprocess
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from data.repo import SessionRepository
from services.local_controller import LocalController
from settings import SettingsManager
from services.cdb_integration import CdbService, CdbBackend
from meeting_recorder.audio import devices
from meeting_recorder.core import atomic_write
from meeting_recorder.server import Handler, Server, App as SharedWebApp
from meeting_recorder.child_process import owned_command

VERSION = '0.5.14'
STATIC = Path(__file__).parent/'studio'
FIELDS = ('title', 'notes', 'transcript_text', 'summary_text')
BUSY = ('recording', 'importing', 'queued', 'transcribing', 'summarizing')


class Conflict(ValueError): pass


class StudioApp:
    def __init__(self, root, database, backend=None, command_factory=None, preview=False, settings_file=None):
        self.cdb = CdbService(root)
        self.cdb_backend = CdbBackend(self.cdb) if backend is None else None
        self.repo = SessionRepository(str(database))
        self.controller = LocalController(self.repo, root, backend=backend or self.cdb_backend, command_factory=command_factory)
        self.engine = self.controller.engine
        self.store, self.models, self.probe = self.engine.store, self.engine.models, self.engine.probe
        if self.cdb_backend:self.cdb_backend.store = self.store
        create = self.store.create
        def create_bound(title):
            snapshot = self.cdb.snapshot()
            ident = create(title)
            atomic_write(self.store.folder(ident)/'cdb-request.json',json.dumps(snapshot))
            return ident
        self.store.create = create_bound
        self.cdb.thread(self.cdb.run)
        self.token = ''
        self.csrf = secrets.token_urlsafe(32)
        self.preview = preview
        self.settings_file = Path(settings_file).resolve() if settings_file else None
        if self.settings_file:self.settings_file.parent.mkdir(parents=True,exist_ok=True)
        self.settings_lock = threading.RLock()
        self.control_lock = threading.RLock()
        self.closing = False
        from services.model_checks import ModelChecks
        self.model_checks = ModelChecks(self)
        self.model_test = None
        test_id = self.store.root/'model-test'/'job.txt'
        if test_id.is_file():
            try:
                candidate=test_id.read_text().strip();self.store.get(candidate)
                self.model_test=candidate
            except (OSError,KeyError,ValueError):pass

    def capabilities(self, state=None):
        state = state or self.engine.state()
        recording = bool(state['recording']['id'])
        probe = state['microphone_test']['state'] == 'running'
        download = state['installation']['state'] == 'running'
        test = self.model_checks.public()['state']=='running' or bool(self.model_test and self.store.get(self.model_test)['state'] in BUSY)
        pending = any(j['state'] in BUSY for j in state['jobs'])
        occupied = recording or probe or download or test
        reason = ('Aufnahme läuft.' if recording else 'Mikrofontest läuft.' if probe else
                  'Modelldownload läuft.' if download else 'Modelltest läuft.' if test else '')
        cdb_config=self.cdb.config()
        needs_login='cdb' in (cdb_config['transcription'],cdb_config['summary']) and not self.cdb.read('session.json',{}).get('identity')
        low_disk = self.store.free_mb() < state['config'].get('min_free_mb', 1024)
        def rule(allowed, why=''): return {'allowed': bool(allowed), 'reason': '' if allowed else why}
        return {
            'record': rule(not occupied and not low_disk and not needs_login and state['config']['setup_complete'],
                           reason or ('Microsoft anmelden oder Verarbeitung auf lokal stellen.' if needs_login else 'Zu wenig freier Speicher.' if low_disk else 'Mikrofon zuerst einrichten.')),
            'configure': rule(not occupied, reason),
            'probe': rule(not occupied and not low_disk, reason or 'Zu wenig freier Speicher.'),
            'install': rule(not occupied and not pending, reason or 'Offene Verarbeitung zuerst abschließen.'),
            'model_test': rule(not occupied and not pending and not low_disk,
                               reason or ('Zu wenig freier Speicher.' if low_disk else 'Offene Verarbeitung zuerst abschließen.')),
            'finish_setup': rule(not occupied, reason),
            'process': rule(not recording and not download and not test, reason),
        }

    def require(self, capability):
        rule = self.capabilities()[capability]
        if not rule['allowed']: raise ValueError(rule['reason'])

    def audio_devices(self): return devices()
    def setup_state(self):
        self.finish_model_validation()
        result=SharedWebApp.setup_state(self)
        providers=self.cdb.config();checks=result['checks']
        result['checks']=[check for i,check in enumerate(checks) if i==0 or i in (1,2) and providers['transcription']=='local' or i in (3,4) and providers['summary']=='local']
        if 'cdb' in (providers['transcription'],providers['summary']):result['checks'].append({'label':'CDB-Firmenanmeldung','ok':bool(self.cdb.read('session.json',{}).get('identity'))})
        result['ready']=all(check['ok'] for check in result['checks'])
        try:self.model_test_preflight();reason=""
        except ValueError as e:reason=str(e)
        except OSError:reason="Modelltest wartet: Kühlung, Temperatur oder Arbeitsspeicher prüfen."
        result["catalog"]["test_block_reason"]=reason
        return result

    def finish_model_validation(self):
        path=self.store.root/'model-test'/'pair.json'
        if not self.model_test or not path.exists():return
        pending=json.loads(path.read_text())
        if pending.get('id')!=self.model_test or pending.get('processed'):return
        job=self.store.get(self.model_test)
        if job['state'] not in ('completed','failed'):return
        result=self.engine.result(self.model_test)
        if job['state']=='completed' and result.get('transcript','').strip() and result.get('summary','').strip():
            catalog=self.models.catalog()
            entries=pending['entries']
            unchanged=all(any(m['id']==old['id'] and m['fingerprint']==old['fingerprint'] for m in catalog['asr' if backend=='whisper' else 'llm']) for backend,old in entries.items())
            if unchanged:self.models.validate_pair(entries)
        atomic_write(path,json.dumps(pending|{'processed':True}))

    @staticmethod
    def model_test_preflight():
        model=Path('/proc/device-tree/model')
        if not model.exists() or b'Raspberry Pi' not in model.read_bytes():return
        temperature=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        fans=list(Path('/sys/class/hwmon').glob('hwmon*/fan1_input'))
        if any(int(p.read_text())==0 and (int((p.parent/'pwm1').read_text())>0 if (p.parent/'pwm1').exists() else temperature>=50) for p in fans):
            raise ValueError('Modelltest wartet: Kühlung angefordert, Lüfter meldet 0 U/min. Anschluss und Lüfter prüfen.')
        if temperature>=65:raise ValueError('Modelltest wartet: Gerät zuerst unter 65 °C abkühlen lassen.')
        available=next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
        if available<4*1024**2:raise ValueError('Modelltest wartet: mindestens 4 GiB verfügbarer Arbeitsspeicher erforderlich.')


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
        state['capabilities'] = self.capabilities(state)
        state['cdb'] = self.cdb.public()
        state['model_check'] = self.model_checks.public()
        state['model_results'] = self.model_checks.results()
        state.update(csrf=self.csrf, version=VERSION, preview=self.preview,
            namespace=hashlib.sha256(str(self.store.root).encode()).hexdigest()[:16])
        if self.model_test:
            job = self.store.get(self.model_test)
            state['model_test'] = job | self.engine.result(self.model_test)
            self.finish_model_validation()
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

    def settings_manager(self):
        if self.settings_file:
            from PySide6.QtCore import QSettings
            return SettingsManager(QSettings(str(self.settings_file),QSettings.IniFormat))
        return SettingsManager()

    def prompts(self):
        with self.settings_lock:
            settings=self.settings_manager();settings.settings.sync()
            return settings.get_all_prompts()

    def mutate_prompt(self, body):
        with self.settings_lock:
            settings=self.settings_manager();settings.settings.sync()
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

    def start_model_test(self, entries=None):
        if self.model_test and self.store.get(self.model_test)['state'] not in ('completed','failed'):
            raise ValueError('Modelltest läuft bereits.')
        if not shutil.which('espeak-ng'):raise ValueError('Programm für künstliche Testsprache fehlt. Bitte Installation prüfen.')
        folder=self.store.root/'model-test';folder.mkdir(exist_ok=True)
        text='Dies ist ein technischer Modelltest. Anna erstellt bis Donnerstag eine Aufgabenliste. Fortsetzung am Freitag um zehn Uhr. Die Kosten sind ungeklärt.'
        subprocess.run(owned_command(['espeak-ng','-v','de','-s','145','-w',str(folder/'spoken.wav'),text]),
                       check=True,timeout=30,capture_output=True)
        with self.controller.lock:
            ident=self.engine.enqueue(folder/'spoken.wav','Technischer Modelltest · künstliche Sprache',test_config=None if entries is None else {'whisper_model':entries['whisper']['path'],'summary_model':entries['ollama']['id'],'model_test':True})
            if entries:atomic_write(folder/'pair.json',json.dumps({'id':ident,'entries':entries}))
            with self.store.db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS hidden_jobs (id TEXT PRIMARY KEY)')
                db.execute('INSERT OR IGNORE INTO hidden_jobs VALUES(?)',(ident,))
            self.model_test=ident
            atomic_write(folder/'job.txt',ident)
            atomic_write(folder/'expected.txt',text)
        return {'id':ident}

    def action(self, path, body):
        # Lock order matches state(): controller before recorder.
        with self.control_lock, self.controller.lock, self.engine.recorder.lock:
            if self.closing:raise ValueError('Dienst wird beendet. Änderungen bitte kurz aufbewahren.')
            if self.engine.recorder.active and path!='/api/record/stop':
                parts=path.strip('/').split('/')
                note_save=(len(parts)==4 and parts[:2]==['api','sessions'] and parts[3]=='save'
                           and isinstance(body.get('changes'),dict) and set(body['changes'])=={'notes'})
                active_id=self.engine.state()['recording']['id']
                if not note_save or self.session(int(parts[2])).get('local_job_id')!=active_id:
                    raise ValueError('Aufnahme läuft. Nur aktuelle Notizen und Stoppen sind verfügbar.')
            if path=='/api/record/start':
                self.require('record')
                if not self.store.config()['setup_complete']:raise ValueError('Kein getestetes Mikrofon. Bitte Einstellungen öffnen und Audio-Einrichtung abschließen.')
                if self.engine.recorder.active:raise ValueError('Aufnahme läuft bereits.')
                return {'id':self.engine.start('')}
            if path=='/api/record/stop':
                ident=self.engine.stop();self.controller.sync();return {'id':ident}
            if path.startswith('/api/cdb/'):
                if path=='/api/cdb/config':
                    self.require('configure');return self.cdb.configure(body)
                if path=='/api/cdb/login':
                    self.require('configure');return self.cdb.start_login()
                if path=='/api/cdb/logout':
                    self.require('configure');self.cdb.logout();return self.cdb.public()
                if path=='/api/cdb/area':return self.cdb.select_area(body.get('area'))
                if path=='/api/cdb/send':return self.cdb.enqueue(self.session(int(body.get('session',0))),body.get('area'))
                raise KeyError('Unbekannte CDB-Aktion.')
            if path=='/api/settings':
                self.require('configure')
                if set(body)-{'device','whisper_binary','whisper_model','summary_model','threads'}:raise ValueError('Unbekannte Einstellung.')
                if 'summary_model' in body or 'whisper_model' in body:
                    catalog=self.models.catalog()
                    for backend,key,entries,valuekey in [('whisper','whisper_model',catalog['asr'],'path'),('ollama','summary_model',catalog['llm'],'id')]:
                        if key in body and body[key]!=self.store.config()[key]:
                            m=next((m for m in entries if m[valuekey]==body[key]),None)
                            if not m or not m.get('tested'):raise ValueError('Neues Modell zuerst installieren und erfolgreich auf diesem Gerät testen; danach ausdrücklich aktivieren.')
                return self.engine.configure(body|{'setup_complete':False})
            if path=='/api/models/check':
                self.require('model_test');return self.model_checks.start(body)
            if path=='/api/models/use':
                self.require('configure');return self.model_checks.use(body)
            if path=='/api/models/install':
                self.require('install')
                return self.models.install(body.get('backend'),body.get('model'))
            if path=='/api/models/activate':
                self.require('configure');self.finish_model_validation()
                catalog=self.models.catalog();backend=body.get('backend')
                if backend not in ('whisper','ollama'):raise ValueError('Unbekannter Modelltyp.')
                entries=catalog['asr' if backend=='whisper' else 'llm']
                m=next((m for m in entries if m['id']==body.get('model')),None)
                if not m or not m.get('tested'):raise ValueError('Aktivierung erst nach bestandenem Gerätetest möglich.')
                key,value=('whisper_model',m['path']) if backend=='whisper' else ('summary_model',m['id'])
                return self.engine.configure({key:value})
            if path=='/api/models/test':
                self.require('model_test');self.model_test_preflight()
                catalog=self.models.catalog();config=self.store.config()
                asr=next((m for m in catalog['asr'] if (m['id']==body.get('asr') if body.get('asr') else m['path']==config['whisper_model'])),None)
                llm=next((m for m in catalog['llm'] if m['id']==body.get('llm',config['summary_model'])),None)
                if not (catalog['whisper_runtime'] and catalog['ollama'] and asr and asr['installed'] and llm and llm['installed']):
                    raise ValueError('Ausgewählte Modelle und Programme zuerst installieren.')
                if llm.get('candidate') and not llm.get('runtime_compatible'):raise ValueError('Laufzeit und Thinking-Vorlage dieses Kandidaten nicht bestätigt.')
                return self.start_model_test({'whisper':asr,'ollama':llm})
            if path=='/api/microphone/test':
                self.require('probe')
                return self.probe.start()
            if path=='/api/setup/complete':
                self.require('finish_setup')
                if not self.setup_state()['ready']:raise ValueError('Einrichtung noch nicht bereit. Offene Punkte prüfen.')
                return self.engine.configure({'setup_complete':True})
            if path=='/api/prompts':return self.mutate_prompt(body)
            parts=path.strip('/').split('/')
            if len(parts)==4 and parts[:2]==['api','sessions']:
                sid=int(parts[2]);session=self.session(sid)
                if parts[3]=='save':return self.save(sid,body.get('changes'),body.get('base'))
                if parts[3]=='process':
                    self.require('process')
                    prompt=next((p for p in self.prompts() if p['id']==body.get('prompt')),None)
                    if not prompt:raise ValueError('Prompt fehlt.')
                    return {'id':self.controller.process(sid,prompt['prompt_text'],reuse_transcript=not body.get('transcribe_again',False))}
                if parts[3]=='retry':
                    self.require('process')
                    if session.get('local_job_id'):self.engine.retry(session['local_job_id']);return {'ok':True}
                    return {'id':self.controller.process(sid)}
                if parts[3]=='delete':
                    if session['transcription_status'] in BUSY:raise ValueError('Aufnahme oder Verarbeitung zuerst abschließen.')
                    return self.controller.delete(sid)
            raise KeyError('Unbekannte Aktion.')

    def close(self):
        with self.control_lock:
            self.closing=True
            if self.engine.recorder.active:self.engine.stop()
            self.controller.sync()
            self.model_checks.stopping.set()
            self.cdb.close()
            if self.model_checks.thread:self.model_checks.thread.join(timeout=5)
            self.engine.close()


class StudioHandler(Handler):
    def get(self):
        if not self.authorized():return
        path=urlsplit(self.path).path
        if path=='/favicon.ico':
            self.send_response(204);self.headers_base('image/x-icon',0);self.end_headers();return
        if path=='/api/state':self.respond(self.server.app.state());return
        if path=='/api/cdb/areas':
            try:self.respond(self.server.app.cdb.areas())
            except ValueError as e:self.respond({'error':str(e)},400)
            return
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
