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
        self.app=StudioApp(self.root/'queue',self.root/'sessions.db',backend=Backend(),settings_file=self.root/'settings.ini')
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
            with urllib.request.urlopen(req,timeout=8) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:
            with e:return e.code,e.read(),e.headers
    def test_cdb_endpoints_require_login_and_keep_local_default(self):
        self.assertEqual(self.request('/api/cdb/config',{'summary':'cdb'})[0],400)
        self.assertEqual(self.request('/api/cdb/areas')[0],400)
        self.assertEqual(self.request('/api/cdb/send',{'session':self.sid,'area':'invalid'})[0],400)
        self.assertEqual(json.loads(self.request('/api/state')[1])['cdb']['config']['summary'],'local')
    def test_cloud_setup_does_not_require_unused_local_models(self):
        with patch.object(self.app.cdb,'config',return_value={'transcription':'cdb','summary':'cdb'}), patch.object(self.app.cdb,'read',return_value={'identity':{'user_id':'synthetic'}}), patch.object(self.app.models,'catalog',return_value={'whisper_runtime':False,'ollama':False,'asr':[],'llm':[]}), patch.object(self.app.probe,'status',return_value={'state':'completed','device':'default'}), patch.object(self.app,'model_test_preflight'):
            setup=self.app.setup_state()
            self.assertTrue(setup['ready']);self.assertEqual(len(setup['checks']),2)
    def test_selected_cloud_without_login_blocks_new_recording(self):
        self.app.engine.configure({'setup_complete':True})
        with patch.object(self.app.cdb,'config',return_value={'transcription':'cdb','summary':'local'}):
            rule=self.app.capabilities()['record'];self.assertFalse(rule['allowed']);self.assertIn('Microsoft',rule['reason'])

    def test_cdb_actions_share_origin_and_csrf_protection(self):
        self.assertEqual(self.request('/api/cdb/login',{}, {'Origin':'http://evil.example'})[0],403)
        self.assertEqual(self.request('/api/cdb/logout',{}, {'X-CSRF-Token':'bad'})[0],403)

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
    def test_meeting_tasks_are_available_without_translation_and_custom_prompts_survive(self):
        self.app.mutate_prompt({'action':'add','name':'Eigener Ablauf','text':'Eigener Arbeitsauftrag'})
        prompts=self.app.prompts()
        self.assertEqual([p['id'] for p in prompts if p['is_default']],['zusammenfassen','aufgaben'])
        self.assertTrue(any(p['name']=='Eigener Ablauf' for p in prompts))
        self.assertIn('Verantwortliche und Fristen nur übernehmen',prompts[1]['prompt_text'])
        self.assertIn('Vorschläge sind keine vereinbarten Aufgaben',prompts[1]['prompt_text'])
        self.assertIn("keine Aufgabe 'Bestellung freigeben'",prompts[1]['prompt_text'])

    def test_prompts_preserved_mutation_and_default_protection(self):
        initial=self.app.prompts()
        self.assertEqual(self.request('/api/prompts',{'action':'add','name':'Eigener','text':'Arbeitsauftrag'})[0],200)
        custom=self.app.prompts()[-1];self.assertEqual(custom['name'],'Eigener')
        self.assertEqual(self.request('/api/prompts',{'action':'update','id':custom['id'],'name':'Neu','text':'Neuer Auftrag'})[0],200)
        self.assertEqual(self.app.prompts()[-1]['prompt_text'],'Neuer Auftrag')
        self.assertEqual(self.request('/api/prompts',{'action':'delete','id':initial[0]['id']})[0],400)
        self.assertEqual(self.app.prompts()[:len(initial)],initial)

    def test_explicit_settings_file_does_not_construct_native_preferences(self):
        with patch('settings.QSettings',side_effect=AssertionError('Native preferences must stay untouched')):
            self.assertEqual(Path(self.app.settings_manager().settings.fileName()).resolve(),(self.root/'settings.ini').resolve())
            self.app.mutate_prompt({'action':'add','name':'Isoliert','text':'Nur Testdaten'})
            self.assertEqual(self.app.prompts()[-1]['name'],'Isoliert')
        persisted=QSettings(str(self.root/'settings.ini'),QSettings.IniFormat)
        self.assertIn('Nur Testdaten',persisted.value('custom_prompts'))
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

    def test_download_guards_server_actions_but_keeps_notes_available(self):
        self.app.engine.configure({'setup_complete':True})
        original=self.app.models.status
        self.app.models.status=lambda:{'state':'running'}
        try:
            capabilities=json.loads(self.request('/api/state')[1])['capabilities']
            for key in ('record','configure','probe','install','model_test','finish_setup','process'):
                self.assertFalse(capabilities[key]['allowed'],key)
            for path,body in [('/api/record/start',{}),('/api/settings',{'threads':2}),
                              ('/api/microphone/test',{}),('/api/models/test',{}),
                              ('/api/setup/complete',{}),('/api/models/install',{'backend':'whisper','model':'medium'}),
                              (f'/api/sessions/{self.sid}/retry',{})]:
                self.assertEqual(self.request(path,body)[0],400,path)
            self.assertEqual(self.request(f'/api/sessions/{self.sid}/save',{'changes':{'notes':'Parallel'},'base':{'notes':'Alte Notizen'}})[0],200)
        finally:self.app.models.status=original

    def test_pending_jobs_block_model_operations_not_capture_or_notes(self):
        self.app.engine.configure({'setup_complete':True})
        self.app.store.claim=lambda:None
        ident=self.app.store.create('Wartet');self.app.store.update(ident,state='queued')
        capabilities=self.app.capabilities()
        self.assertTrue(capabilities['record']['allowed'])
        self.assertTrue(capabilities['configure']['allowed'])
        self.assertFalse(capabilities['install']['allowed'])
        self.assertFalse(capabilities['model_test']['allowed'])
        self.app.repo.update(self.sid,local_job_id=ident,transcription_status='queued')
        self.assertEqual(self.request(f'/api/sessions/{self.sid}/delete',{})[0],400)
        self.assertIsNotNone(self.app.repo.get_by_id(self.sid))

    def test_concurrent_state_poll_and_capture_stop_complete_without_lock_inversion(self):
        import concurrent.futures
        script="import sys,time;\nwhile True:\n sys.stdout.buffer.write(b'\\x01\\x00'*1600);sys.stdout.buffer.flush();time.sleep(.1)"
        self.app.engine.recorder.command_factory=lambda _:[sys.executable,'-u','-c',script]
        self.app.engine.configure({'setup_complete':True})
        self.app.store.claim=lambda:None
        self.assertEqual(self.request('/api/record/start',{})[0],200)
        pcm=self.app.store.folder(self.app.engine.recorder.active)/'audio.pcm'
        end=time.monotonic()+3
        while pcm.stat().st_size<3200 and time.monotonic()<end:time.sleep(.02)
        self.assertGreaterEqual(pcm.stat().st_size,3200)
        barrier=threading.Barrier(3)
        def polling():
            barrier.wait()
            for _ in range(15):self.assertEqual(self.request('/api/state')[0],200)
        def stopping():
            barrier.wait()
            return self.request('/api/record/stop',{})[0]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(polling),pool.submit(polling),pool.submit(stopping)]
            for future in futures:future.result(timeout=10)
            self.assertEqual(futures[2].result(),200)
        self.assertFalse(self.app.engine.recorder.active)

    def test_model_test_identity_and_exclusive_rules_survive_restart(self):
        self.app.store.claim=lambda:None
        ident=self.app.store.create('Model test')
        self.app.store.update(ident,state='queued')
        folder=self.app.store.root/'model-test';folder.mkdir(exist_ok=True)
        (folder/'job.txt').write_text(ident)
        with self.app.store.db() as db:db.execute('INSERT OR IGNORE INTO hidden_jobs VALUES(?)',(ident,))
        self.app.close()
        with patch('meeting_recorder.processing.Worker.run',return_value=None):
            self.app=StudioApp(self.root/'queue',self.root/'sessions.db',backend=Backend(),settings_file=self.root/'settings.ini')
        self.server.app=self.app
        self.app.engine.configure({'setup_complete':True})
        self.assertEqual(self.app.model_test,ident)
        self.assertFalse(self.app.capabilities()['record']['allowed'])
        self.assertFalse(self.app.capabilities()['configure']['allowed'])
        self.assertEqual(len(self.app.state()['sessions']),1)

    def test_low_disk_blocks_capture_without_writing_large_files(self):
        self.app.engine.configure({'setup_complete':True})
        with patch.object(self.app.store,'free_mb',return_value=256):
            self.assertFalse(self.app.capabilities()['record']['allowed'])
            self.assertEqual(self.request('/api/record/start',{})[0],400)

    def test_shared_audio_is_preserved_when_one_reference_is_deleted(self):
        original=self.app.repo.get_by_id(self.sid)
        other=self.app.repo.create('Andere Referenz','2025-01-02',original['path'])
        result=self.app.repo.delete(self.sid)
        self.assertFalse(result['file_deleted'])
        self.assertTrue(Path(self.app.repo.get_by_id(other)['path']).is_file())

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
        self.app=StudioApp(self.root/'queue',self.root/'sessions.db',backend=Backend(),settings_file=self.root/'settings.ini')
        self.server.app=self.app
        row=self.app.session(captured['id'])
        self.assertEqual(row['local_job_id'],ident)
        self.assertEqual(row['notes'],'Während Aufnahme gespeichert')
        self.assertEqual(len([r for r in self.app.repo.get_all() if r.get('local_job_id')==ident]),1)

    def test_model_candidates_do_not_activate_without_passed_device_test(self):
        old=self.app.store.config()['summary_model']
        model={'id':'candidate','installed':True,'tested':False,'fingerprint':'digest|runtime'}
        catalog={'asr':[],'llm':[model]}
        with patch.object(self.app.models,'catalog',return_value=catalog):
            self.assertEqual(self.request('/api/models/activate',{'backend':'ollama','model':'candidate'})[0],400)
            self.assertEqual(self.request('/api/settings',{'summary_model':'candidate'})[0],400)
            self.assertEqual(self.app.store.config()['summary_model'],old)
            model['tested']=True
            self.assertEqual(self.request('/api/models/activate',{'backend':'ollama','model':'candidate'})[0],200)
            self.assertEqual(self.app.store.config()['summary_model'],'candidate')

    def test_candidate_test_uses_selected_pair_without_changing_configuration(self):
        old=self.app.store.config()
        asr={'id':'large-v3','path':'/candidate.bin','installed':True,'fingerprint':'asr'}
        llm={'id':'candidate','installed':True,'candidate':True,'runtime_compatible':True,'fingerprint':'llm'}
        catalog={'asr':[asr],'llm':[llm],'whisper_runtime':True,'ollama':True}
        with patch.object(self.app.models,'catalog',return_value=catalog),patch.object(self.app,'model_test_preflight'),patch.object(self.app,'start_model_test',return_value={'id':'test'}) as start:
            self.assertEqual(self.request('/api/models/test',{'asr':'large-v3','llm':'candidate'})[0],200)
            self.assertEqual(start.call_args.args[0],{'whisper':asr,'ollama':llm})
            llm['runtime_compatible']=False
            self.assertEqual(self.request('/api/models/test',{'asr':'large-v3','llm':'candidate'})[0],400)
        self.assertEqual(self.app.store.config(),old)

    def test_cooling_preflight_prevents_test_before_any_work(self):
        with patch.object(self.app,'model_test_preflight',side_effect=ValueError('Lüfter meldet 0 U/min')),patch.object(self.app,'start_model_test') as start:
            status,body,_=self.request('/api/models/test',{})
            self.assertEqual(status,400);self.assertIn('0 U/min',body.decode());start.assert_not_called()

    def test_only_completed_unchanged_pair_gains_persistent_validation(self):
        ident=self.app.store.create('Isolated model test');self.app.model_test=ident
        folder=self.app.store.folder(ident)
        entries={'whisper':{'id':'medium','fingerprint':'weights'},'ollama':{'id':'candidate','fingerprint':'digest'}}
        pending=self.app.store.root/'model-test'/'pair.json';pending.parent.mkdir(exist_ok=True)
        pending.write_text(json.dumps({'id':ident,'entries':entries}))
        (folder/'transcript.txt').write_text('Erkannter Text');(folder/'summary.md').write_text('Sachliches Protokoll')
        catalog={'asr':[entries['whisper']],'llm':[entries['ollama']]}
        with patch.object(self.app.models,'catalog',return_value=catalog),patch.object(self.app.models,'validate_pair') as validate:
            self.app.store.update(ident,state='failed');self.app.finish_model_validation();validate.assert_not_called()
            pending.write_text(json.dumps({'id':ident,'entries':entries}))
            self.app.store.update(ident,state='completed');self.app.finish_model_validation();validate.assert_called_once_with(entries)
            self.app.finish_model_validation();validate.assert_called_once()
            pending.write_text(json.dumps({'id':ident,'entries':entries}));validate.reset_mock()
            catalog['llm']=[{'id':'candidate','fingerprint':'replaced'}]
            self.app.finish_model_validation();validate.assert_not_called()

class ModelPreflightTests(unittest.TestCase):
    def test_cold_idle_fan_is_allowed_but_requested_cooling_without_rpm_is_blocked(self):
        with tempfile.TemporaryDirectory() as root:
            def path(value):return Path(root)/str(value).lstrip('/')
            for name,value in [('/proc/device-tree/model','Raspberry Pi 5'),('/proc/meminfo','MemAvailable: 7000000 kB\n'),('/sys/class/thermal/thermal_zone0/temp','45000'),('/sys/class/hwmon/hwmon3/fan1_input','0'),('/sys/class/hwmon/hwmon3/pwm1','0')]:
                p=path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
            with patch('web_server.Path',side_effect=path):StudioApp.model_test_preflight()
            path('/sys/class/thermal/thermal_zone0/temp').write_text('55000');path('/sys/class/hwmon/hwmon3/pwm1').write_text('75')
            with patch('web_server.Path',side_effect=path),self.assertRaisesRegex(ValueError,'0 U/min'):StudioApp.model_test_preflight()
            path('/sys/class/hwmon/hwmon3/pwm1').write_text('0');path('/sys/class/thermal/thermal_zone0/temp').write_text('66000')
            with patch('web_server.Path',side_effect=path),self.assertRaisesRegex(ValueError,'65'):StudioApp.model_test_preflight()
