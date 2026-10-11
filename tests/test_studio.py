import json, sys, threading, time, tempfile, unittest, urllib.request, urllib.error, wave
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QSettings
from web_server import StudioApp, StudioServer


class Backend:
    def transcribe(self,folder,c):return 'Testtranskript'
    def generate(self,text,c,merge=False):return 'Testzusammenfassung'


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        QSettings.setDefaultFormat(QSettings.IniFormat);QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(self.root/'settings'))
        self.app=StudioApp(self.root/'queue',self.root/'sessions.db',backend=Backend())
        audio=self.root/'test.wav'
        with wave.open(str(audio),'wb') as w:w.setparams((1,2,16000,0,'NONE','none'));w.writeframes(b'\0\0'*16000)
        self.sid=self.app.repo.create('Bestand','2025-01-01',str(audio),notes='Alte Notizen')
        self.app.repo.update(self.sid,transcript_text='Altes Transkript',summary_text='Alte Zusammenfassung',transcription_status='completed')
        self.server=StudioServer(('127.0.0.1',0),self.app);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):self.server.shutdown();self.server.server_close();self.app.close();self.tmp.cleanup()
    def request(self,path,body=None,headers=None):
        req=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),
            headers=({'Content-Type':'application/json','X-CSRF-Token':self.app.csrf} if body is not None else {})|(headers or {}))
        try:
            with urllib.request.urlopen(req) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:
            with e:return e.code,e.read(),e.headers
    def test_existing_library_content_save_reload_and_optimistic_conflict(self):
        row=json.loads(self.request('/api/sessions/'+str(self.sid))[1]);self.assertEqual(row['notes'],'Alte Notizen')
        status,body,_=self.request('/api/sessions/'+str(self.sid)+'/save',{'changes':{'notes':'Neue Notizen'},'base':{'notes':'Alte Notizen'}})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['transcript_text'],'Altes Transkript')
        self.assertEqual(self.app.repo.get_by_id(self.sid)['notes'],'Neue Notizen')
        status,_,_=self.request('/api/sessions/'+str(self.sid)+'/save',{'changes':{'notes':'Überholt'},'base':{'notes':'Alte Notizen'}})
        self.assertEqual(status,409);self.assertEqual(self.app.repo.get_by_id(self.sid)['notes'],'Neue Notizen')
        self.assertEqual(len(json.loads(self.request('/api/state')[1])['sessions']),1)
    def test_local_host_origin_csrf_static_paths_and_no_lan_bind(self):
        self.assertEqual(self.request('/api/state',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/api/settings',{}, {'Origin':'http://evil.example'})[0],403)
        self.assertEqual(self.request('/api/settings',{}, {'X-CSRF-Token':'wrong'})[0],403)
        self.assertEqual(self.request('/../../settings.py')[0],404)
        self.assertEqual(self.request('/api/record/start',{})[0],400)
        with self.assertRaises(ValueError):StudioServer(('0.0.0.0',0),self.app)
        self.assertIn("script-src 'self'",self.request('/')[2]['Content-Security-Policy'])
        self.assertEqual(self.request('/')[2]['Permissions-Policy'],'microphone=(), camera=()')
    def test_audio_stream_range_and_export_use_session_mapping(self):
        status,data,headers=self.request(f'/api/sessions/{self.sid}/audio',headers={'Range':'bytes=4-19'})
        self.assertEqual(status,206);self.assertEqual(len(data),16);self.assertEqual(headers['Content-Range'],'bytes 4-19/32044')
        self.assertEqual(self.request(f'/api/sessions/{self.sid}/audio',headers={'Range':'bytes=999999-'})[0],416)
        data=self.request(f'/api/sessions/{self.sid}/export')[1].decode();self.assertIn('Alte Notizen',data);self.assertIn('Alte Zusammenfassung',data)
    def test_prompts_preserved_mutation_and_default_protection(self):
        initial=self.app.prompts()
        self.assertEqual(self.request('/api/prompts',{'action':'add','name':'Eigener','text':'Arbeitsauftrag'})[0],200)
        custom=self.app.prompts()[-1];self.assertEqual(custom['name'],'Eigener')
        self.assertEqual(self.request('/api/prompts',{'action':'update','id':custom['id'],'name':'Neu','text':'Neuer Auftrag'})[0],200)
        self.assertEqual(self.app.prompts()[-1]['prompt_text'],'Neuer Auftrag')
        self.assertEqual(self.request('/api/prompts',{'action':'delete','id':initial[0]['id']})[0],400)
        self.assertEqual(self.app.prompts()[:len(initial)],initial)
    def test_busy_text_protection_notes_allowed_and_engine_single_owner(self):
        self.app.repo.update(self.sid,transcription_status='summarizing')
        self.assertEqual(self.request(f'/api/sessions/{self.sid}/save',{'changes':{'transcript_text':'Neu'},'base':{'transcript_text':'Altes Transkript'}})[0],409)
        self.assertEqual(self.request(f'/api/sessions/{self.sid}/save',{'changes':{'notes':'Parallel'},'base':{'notes':'Alte Notizen'}})[0],200)
        with self.assertRaises(RuntimeError):StudioApp(self.root/'queue',self.root/'other.db')
    def test_process_settings_and_results_remain_on_original_session(self):
        prompt=self.app.prompts()[0]['id'];status,body,_=self.request(f'/api/sessions/{self.sid}/process',{'prompt':prompt})
        self.assertEqual(status,200);ident=json.loads(body)['id'];end=time.monotonic()+8
        while self.app.store.get(ident)['state'] not in ('completed','failed') and time.monotonic()<end:time.sleep(.03)
        row=self.app.session(self.sid);self.assertEqual(row['notes'],'Alte Notizen');self.assertEqual(row['summary_text'],'Testzusammenfassung')
        self.assertEqual(row['id'],self.sid);self.assertEqual(len(self.app.repo.get_all()),1)
        self.assertEqual(self.request('/api/settings',{'summary_model':'qwen3:4b-instruct'})[0],200)
        self.assertFalse(self.app.store.config()['setup_complete'])
        self.assertEqual(self.request('/api/settings',{'openai_api_key':'never'})[0],400)
        self.app.save(self.sid,{'summary_text':''},{'summary_text':'Testzusammenfassung'});self.app.controller.sync()
        self.assertEqual(self.app.session(self.sid)['summary_text'],'')

    def test_capture_double_start_guard_and_shutdown_preserve_audio_and_mapping(self):
        script="import sys,time;\nwhile True:\n sys.stdout.buffer.write(b'\\x01\\x00'*1600);sys.stdout.buffer.flush();time.sleep(.1)"
        self.app.engine.recorder.command_factory=lambda _:[sys.executable,'-u','-c',script]
        self.app.engine.configure({'setup_complete':True})
        status,data,_=self.request('/api/record/start',{})
        self.assertEqual(status,200);ident=json.loads(data)['id']
        self.assertEqual(self.request('/api/record/start',{})[0],400)
        end=time.monotonic()+3
        pcm=self.app.store.folder(ident)/'audio.pcm'
        while (not pcm.exists() or pcm.stat().st_size<3200) and time.monotonic()<end:time.sleep(.03)
        self.assertGreaterEqual(pcm.stat().st_size,3200)
        self.app.controller.sync()
        captured=next(r for r in self.app.repo.get_all() if r.get('local_job_id')==ident)
        self.app.save(captured['id'],{'notes':'Während Aufnahme gespeichert'},{'notes':''})
        self.app.close()
        with wave.open(str(pcm.with_name('audio.wav')),'rb') as audio:self.assertGreater(audio.getnframes(),0)
        self.app=StudioApp(self.root/'queue',self.root/'sessions.db',backend=Backend())
        self.server.app=self.app
        row=self.app.session(captured['id'])
        self.assertEqual(row['local_job_id'],ident)
        self.assertEqual(row['notes'],'Während Aufnahme gespeichert')
        self.assertEqual(len([r for r in self.app.repo.get_all() if r.get('local_job_id')==ident]),1)
