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
    def test_first_start_http_guards_and_progress(self):
        from fleet.common import save
        from services.app_activity import AppActivity
        status,data,_=self.request('/api/onboarding')
        self.assertEqual(status,200);self.assertFalse(json.loads(data)['required'])
        for activity in (AppActivity(recording=True),AppActivity(live='active'),AppActivity(pending=True),AppActivity(maintenance=True)):
            with patch.object(self.app,'activity',return_value=activity), patch.object(self.app.first_start,'run_network') as network:
                self.assertEqual(self.request('/api/onboarding/network',{'action':'connect'})[0],400)
                network.assert_not_called()
        self.assertEqual(self.request('/api/onboarding/step',{'step':'pair'},headers={'X-CSRF-Token':'wrong'})[0],403)
        self.assertEqual(self.request('/api/onboarding/step',{'step':'done'})[0],400)
        self.assertEqual(self.request('/api/onboarding/step',{'step':'done','offline':True})[0],200)
        self.app.first_start.busy=True
        for path in ('/api/record/start','/api/live/reserve','/api/management/enroll'):
            self.assertEqual(self.request(path,{})[0],400)
        self.app.first_start.busy=False

    def test_index_version_is_rendered_from_running_backend(self):
        with patch('web_server.VERSION', 'release-under-test'):
            for path in ('/', '/index.html'):
                status, data, headers = self.request(path)
                self.assertEqual(status, 200)
                self.assertIn(b'name="studio-ui-version" content="release-under-test"', data)
                self.assertNotIn(b'__STUDIO_VERSION__', data)
                self.assertEqual(int(headers['Content-Length']), len(data))

    def test_wake_phrase_selection_respects_activity_and_persists(self):
        from services.app_activity import AppActivity
        for activity in (AppActivity(recording=True),AppActivity(paused=True,recording=True),AppActivity(live='active'),AppActivity(maintenance=True)):
            with patch.object(self.app,'activity',return_value=activity):
                self.assertEqual(self.request('/api/wake',{'action':'phrase','phrase':'hey-kai'})[0],400)
        self.assertEqual(self.app.wake.phrase,'hey-brain')
        self.assertEqual(self.request('/api/wake',{'action':'phrase','phrase':'okay-kai'})[0],200)
        self.assertEqual(self.app.wake.public()['word'],'Okay KAI')
        self.assertEqual(self.request('/api/wake',{'action':'phrase','phrase':'unknown'})[0],400)
        self.assertEqual(self.app.wake.phrase,'okay-kai')

    def test_management_token_maintenance_and_timer_guards(self):
        from fleet.common import read
        headers={'Authorization':'Bearer '+read(self.app.management.auth)['token']}
        command='11111111-1111-1111-1111-111111111111'
        self.assertEqual(self.request('/api/management/health')[0],403)
        self.assertEqual(self.request('/api/management/prepare',{'command':command})[0],403)
        from services.app_activity import AppActivity
        for activity in (AppActivity(recording=True),AppActivity(live='active'),AppActivity(pending=True),AppActivity(download=True),AppActivity(bluetooth=True)):
            with patch.object(self.app,'activity',return_value=activity):
                self.assertEqual(self.request('/api/management/prepare',{'command':command},headers)[0],409)
                self.assertFalse(self.app.management.busy())
        self.assertEqual(self.request('/api/management/prepare',{'command':command},headers)[0],200)
        self.assertTrue(self.app.management.busy())
        for path,body in [('/api/wake',{'action':'on'}),('/api/record/start',{}),('/api/timers',{'action':'create'}),('/api/live/reserve',{})]:
            self.assertEqual(self.request(path,body)[0],400)
        self.assertEqual(self.request('/api/management/release',{'command':command},headers)[0],200)
        self.assertFalse(self.app.management.busy())
        self.app.schedules.create({'kind':'timer','seconds':30,'label':'Keep','request_id':'management-lock'})
        self.assertEqual(self.request('/api/management/prepare',{'command':command},headers)[0],409)
        self.assertFalse(self.app.management.busy())

    def test_local_restart_requires_csrf_confirmation_and_activity_clearance(self):
        from services.app_activity import AppActivity
        from unittest.mock import Mock
        with patch('services.device_management.subprocess.run',return_value=Mock(returncode=0)):
            self.assertEqual(self.request('/api/device/restart',{'confirm':True},{'X-CSRF-Token':'wrong'})[0],403)
            self.assertEqual(self.request('/api/device/restart',{})[0],400)
        for activity in (AppActivity(recording=True),AppActivity(paused=True,recording=True),AppActivity(live='listening'),AppActivity(pending=True)):
            with patch.object(self.app.management,'boot_id',return_value='boot'),patch.object(self.app,'activity',return_value=activity),patch('services.device_management.subprocess.run',return_value=Mock(returncode=0)) as run:
                self.assertEqual(self.request('/api/device/restart',{'confirm':True})[0],400)
                self.assertFalse(any('systemd-run' in c.args[0] for c in run.call_args_list))

    def test_recognition_feedback_does_not_wait_for_controller_lock(self):
        self.app.wake.recognized_until=time.monotonic()+8
        locked=threading.Event();release=threading.Event()
        def hold():
            with self.app.controller.lock:locked.set();release.wait(4)
        worker=threading.Thread(target=hold);worker.start();self.assertTrue(locked.wait(1))
        try:
            start=time.monotonic();status,data,_=self.request('/api/wake/status')
            self.assertEqual(status,200);self.assertGreater(json.loads(data)['recognized_for'],0)
            self.assertLess(time.monotonic()-start,1)
        finally:release.set();worker.join(2)

    def test_due_alarm_mixes_during_live_and_ack_does_not_close_conversation(self):
        from services.app_activity import AppActivity
        # Stop background ticks to drive real persistent timers deterministically.
        self.app.ambient_stop.set(); self.app.ambient_thread.join(3)
        ident=self.app.schedules.create({'kind':'timer','seconds':1,'label':'Test',
                                        'request_id':'mix-live','tone':'bell'})['id']
        time.sleep(1.1); self.app.schedules.tick(True)
        # Playing media and the Live audio sink no longer defer the timer.
        self.app.output_busy_until=time.monotonic()+60
        self.app.playback_leases['live-test']=time.monotonic()+60
        with patch.object(self.app,'activity',return_value=AppActivity(live='speaking')), \
             patch.object(self.app.speakers,'start_alarm') as start, \
             patch.object(self.app.speakers,'test_status',return_value={'state':'running'}), \
             patch.object(self.app.speakers,'stop_test') as stop, \
             patch.object(self.app.live,'end') as end:
            self.app.tick_alarm();self.assertEqual(self.app.alarm_id,ident)
            start.assert_called_once_with('bell')
            self.app.tick_alarm();self.assertEqual(start.call_count,1)
            item=self.app.schedules.items()[0]
            self.app.schedules.change({'action':'ack','id':ident,'revision':item['revision']})
            self.app.tick_alarm();stop.assert_called_once();end.assert_not_called()
            self.assertIsNone(self.app.alarm_id)

    def test_due_alarm_remains_pending_until_recording_finishes(self):
        from services.app_activity import AppActivity
        self.app.ambient_stop.set();self.app.ambient_thread.join(3)
        self.app.schedules.create({'kind':'timer','seconds':1,'label':'Test',
                                  'request_id':'record-hold','tone':'bell'})
        time.sleep(1.1);self.app.schedules.tick(True)
        with patch.object(self.app,'activity',return_value=AppActivity(recording=True)), \
             patch.object(self.app.speakers,'start_alarm') as start:
            self.app.tick_alarm();start.assert_not_called()
            self.assertEqual(self.app.schedules.items()[0]['sound'],'pending')
        with patch.object(self.app,'activity',return_value=AppActivity()), \
             patch.object(self.app.speakers,'start_alarm') as start:
            self.app.tick_alarm();start.assert_called_once_with('bell')

    def test_wake_test_can_be_stopped_without_enabling(self):
        self.app.wake.test_until=time.monotonic()+30
        self.assertEqual(self.request('/api/wake',{'action':'test-stop'})[0],200)
        self.assertFalse(self.app.wake.public()['testing'])
        self.assertFalse(self.app.wake.enabled)

    def test_timers_survive_audio_locks_and_require_csrf(self):
        body={'action':'create','kind':'timer','label':'Test','seconds':30,'request_id':'studio-timer'}
        self.assertEqual(self.request('/api/timers',body,{'X-CSRF-Token':'bad'})[0],403)
        self.app.engine.recorder.active={'id':'lock','paused':True}
        try:
            self.assertEqual(self.request('/api/timers',body)[0],200)
            self.assertEqual(self.request('/api/wake',{'action':'test'})[0],400)
            self.assertEqual(self.request('/api/wake',{'action':'on'})[0],400)
        finally:self.app.engine.recorder.active=None
        with patch.object(self.app.live,'busy',return_value=True):
            item=self.app.schedules.items()[0]
            self.assertEqual(self.request('/api/timers',{'action':'cancel','id':item['id'],'revision':item['revision']})[0],200)
        self.assertEqual(self.app.schedules.items()[0]['state'],'cancelled')

    def test_wake_is_preempted_before_record_and_live(self):
        with patch.object(self.app.wake,'suspend') as suspend,patch.object(self.app.engine,'start',return_value='synthetic') as start:
            self.app.engine.configure({'setup_complete':True})
            self.assertEqual(self.request('/api/record/start',{})[0],200)
            self.assertTrue(suspend.called);start.assert_called_once()
        with patch.object(self.app.live,'busy',return_value=True),patch.object(self.app.live,'public',return_value={'state':'connecting','busy':True}):
            self.assertEqual(self.request('/api/wake',{'action':'test'})[0],400)
            self.assertEqual(self.request('/api/wake',{'action':'off'})[0],200)

    def test_browser_playback_holds_detector_and_expires(self):
        self.assertEqual(self.request('/api/playback',{'client':'browser-test','playing':True})[0],200)
        self.assertEqual(self.app.wake_reason(),'Audiowiedergabe läuft.')
        self.assertEqual(self.request('/api/playback',{'client':'browser-test','playing':False})[0],200)
        self.assertNotEqual(self.app.wake_reason(),'Audiowiedergabe läuft.')

    def test_display_control_is_loopback_csrf_protected_and_recording_locked(self):
        self.app.display.address=('127.0.0.1',0)
        self.assertEqual(self.request('/api/display/control',{'action':'enable'},{'X-CSRF-Token':'bad'})[0],403)
        self.app.engine.recorder.active={'id':'lock'}
        try:self.assertEqual(self.request('/api/display/control',{'action':'enable'})[0],400)
        finally:self.app.engine.recorder.active=None
        self.assertEqual(self.request('/api/display/control',{'action':'enable'})[0],200)
        self.assertTrue(json.loads(self.app.display_preferences.read_text())['enabled'])
        session={'server':'https://staging.cdbos.de','identity':{'user_id':'test','client_id':'11111111-1111-1111-1111-111111111111'}}
        account={'binding':{'server':session['server'],**session['identity']},'generation':0}
        with patch.object(self.app.display,'account',return_value=account), patch.object(self.app.cdb,'session',return_value=session):
            token,pending=self.app.display.begin('Test')
            self.assertEqual(self.request('/api/display/control',{'action':'pair','code':pending['code']})[0],200)
            self.assertTrue(self.app.display.pulse(token)['paired'])
        with patch.object(self.app.live,'public',return_value={'state':'speaking','busy':True}):
            self.assertEqual(self.request('/api/display/control',{'action':'pair','code':'123456'})[0],400)
            self.assertEqual(self.request('/api/display/revoke',{})[0],200)
        self.assertEqual(self.request('/api/display/control',{'action':'disable'})[0],200)
        self.assertFalse(self.app.display.status()['enabled'])

    def test_bluetooth_interlocks_and_csrf(self):
        with patch.object(self.app.bluetooth,'action',return_value={'ok':True}) as action:
            self.assertEqual(self.request('/api/bluetooth',{'action':'scan'},{'X-CSRF-Token':'bad'})[0],403)
            self.app.engine.recorder.active={'id':'lock'}
            try:self.assertEqual(self.request('/api/bluetooth',{'action':'scan'})[0],400)
            finally:self.app.engine.recorder.active=None
            with patch.object(self.app.live,'public',return_value={'state':'speaking','busy':True}):
                self.assertEqual(self.request('/api/bluetooth',{'action':'scan'})[0],400)
            action.assert_not_called()
            self.app.bluetooth.update(busy=True,operation='scan')
            for path in ('/api/record/start','/api/live/reserve','/api/settings','/api/microphone/test'):
                self.assertEqual(self.request(path,{})[0],400)
            self.assertEqual(self.request('/api/bluetooth',{'action':'cancel'})[0],200)
            self.app.bluetooth.update(busy=False)

    def test_capture_controls_reject_idle_invalid_and_cross_origin_requests(self):
        self.assertEqual(self.request('/api/record/control',{'paused':True})[0],400)
        self.assertEqual(self.request('/api/record/control',{'muted':True},{'Origin':'http://evil.example'})[0],403)
        self.assertEqual(self.request('/api/record/control',{'unknown':True})[0],400)
        self.assertEqual(self.request('/api/record/control',{'paused':None})[0],400)
        with patch.object(self.app.engine.recorder,'control',return_value={'id':'test','paused':True}) as control:
            self.assertEqual(self.request('/api/record/control',{'paused':True})[0],200)
            control.assert_called_once_with(paused=True)

    def test_live_and_recorder_share_server_side_interlock(self):
        area='11111111-1111-1111-1111-111111111111'
        with patch.object(self.app.cdb,'read',return_value={'identity':{'user_id':'test'}}), patch.object(self.app.live,'_binding',return_value={'server':'https://staging.cdbos.de','user_id':'test','client_id':area}):
            self.app.engine.recorder.active={'id':'lock'}
            try:self.assertEqual(self.request('/api/live/reserve',{'area_ids':[area]})[0],400)
            finally:self.app.engine.recorder.active=None
            self.assertEqual(self.request('/api/live/reserve',{'area_ids':[area]},{'X-CSRF-Token':'bad'})[0],403)
            status,body,_=self.request('/api/live/reserve',{'area_ids':[area]})
            self.assertEqual(status,200);lease=json.loads(body)['lease']
            for mode in ('connecting','listening','thinking','speaking','reconnecting','closing'):
                self.app.live.state=mode
                for path in ('/api/record/start','/api/settings','/api/speakers/test','/api/cdb/logout','/api/live/reserve'):
                    with self.subTest(mode=mode,path=path):self.assertEqual(self.request(path,{})[0],400)
            self.app.live.state='connecting'
            self.assertEqual(self.request('/api/live/pulse',{'lease':'other-browser'})[0],400)
            self.assertEqual(self.request('/api/live/end',{'lease':lease})[0],200)
            self.assertTrue(self.app.live.finished.wait(2))
            self.assertTrue(self.app.capabilities()['configure']['allowed'])
            self.assertTrue(self.app.capabilities()['live']['allowed'])
            self.assertEqual(self.request('/api/settings',{'threads':2})[0],200)

    def test_live_audio_uses_exact_configured_pi_devices(self):
        self.app.engine.configure({'device':'plughw:CARD=Array,DEV=0'})
        speaker={'available':True,'muted':False,'volume':40,'selected':'chosen-speaker','devices':[{'id':'chosen-speaker','label':'USB Speaker'}]}
        with patch.object(self.app,'audio_devices',return_value={'devices':[{'id':'plughw:CARD=Array,DEV=0','label':'ReSpeaker'}]}), patch.object(self.app.speakers,'public',return_value=speaker):
            c=self.app.live_audio_config();self.assertEqual(c['device'],'plughw:CARD=Array,DEV=0');self.assertEqual(c['speaker'],'chosen-speaker')
            speaker['muted']=True
            with self.assertRaisesRegex(ValueError,'stumm'):self.app.live_audio_config()
        with patch.object(self.app,'audio_devices',return_value={'devices':[]}):
            with self.assertRaisesRegex(ValueError,'Mikrofon fehlt'):self.app.live_audio_config()

    def test_native_live_route_and_browser_audio_policy(self):
        self.assertEqual(self.request('/api/live/start',{'sdp':'v=0','lease':'old'})[0],400)
        with patch.object(self.app.live,'start_native',return_value={'starting':True,'transport':'pi'}) as native:
            self.assertEqual(self.request('/api/live/start-native',{'lease':'test'},{'X-CSRF-Token':'invalid'})[0],403)
            self.assertEqual(self.request('/api/live/start-native',{'lease':'test'})[0],200)
            native.assert_called_once_with('test')
        self.assertEqual(self.request('/')[2]['Permissions-Policy'],'microphone=(), camera=()')

    def test_speaker_routes_are_protected_and_recording_interlocked(self):
        with patch.object(self.app.speakers,'public',return_value={'devices':[]}), patch.object(self.app.speakers,'configure',return_value={'ok':True}) as configure:
            self.assertEqual(self.request('/api/speakers')[0],200)
            self.assertEqual(self.request('/api/speakers',{'volume':50},{'X-CSRF-Token':'bad'})[0],403)
            self.assertEqual(self.request('/api/speakers',{'volume':50})[0],200)
            self.app.engine.recorder.active={'id':'synthetic-lock'}
            try:
                self.assertEqual(self.request('/api/speakers',{'volume':20})[0],400)
                self.assertEqual(self.request('/api/speakers/test',{})[0],400)
            finally:self.app.engine.recorder.active=None
            configure.assert_called_once()
        with patch.object(self.app.speakers,'test_status',return_value={'state':'running'}):
            self.assertFalse(self.app.capabilities()['record']['allowed'])
            self.assertFalse(self.app.capabilities()['probe']['allowed'])
            self.assertEqual(self.request('/api/record/start',{})[0],400)
        with patch.object(self.app.speakers,'stop_test',return_value={'state':'cancelled'}):
            self.assertEqual(self.request('/api/speakers/stop',{})[0],200)

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
        current_save=f"/api/sessions/{captured['id']}/save"
        self.assertEqual(self.request(current_save,{'changes':{'notes':'Während Aufnahme gespeichert'},'base':{'notes':''}})[0],200)
        for path,body in [('/api/settings',{'threads':2}),('/api/cdb/area',{'area':'blocked'}),
                          ('/api/cdb/logout',{}),('/api/prompts',{'action':'add','name':'blocked','text':'blocked'}),
                          (current_save,{'changes':{'title':'blocked'},'base':{'title':captured['title']}}),
                          (f'/api/sessions/{self.sid}/save',{'changes':{'notes':'blocked'},'base':{'notes':'Alte Notizen'}}),
                          (f'/api/sessions/{self.sid}/retry',{}),
                          (f'/api/sessions/{self.sid}/delete',{})]:
            self.assertEqual(self.request(path,body)[0],400,path)

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

    def test_independent_whisper_check_needs_no_summary_runtime_and_does_not_activate(self):
        old=self.app.store.config()
        m={'id':'medium','label':'Whisper medium','installed':True,'path':'/new-medium.bin','fingerprint':'weights','tested':False}
        catalog={'asr':[m],'llm':[],'whisper_runtime':True,'ollama':False}
        with patch.object(self.app.models,'catalog',return_value=catalog),patch.object(self.app,'model_test_preflight'),patch.object(self.app.model_checks,'execute',return_value='Anna erstellt die Aufgabenliste.'),patch.object(self.app.models,'validate_pair') as validate:
            status,body,_=self.request('/api/models/check',{'stage':'transcription','provider':'local','model':'medium'})
            self.assertEqual(status,200);self.app.model_checks.thread.join(3)
            self.assertEqual(self.app.model_checks.public()['state'],'completed')
            validate.assert_called_once_with({'whisper':m})
            self.assertEqual(self.app.store.config(),old)
            self.assertEqual(self.request('/api/models/use',{'stage':'transcription','provider':'local','model':'medium'})[0],400)
            m['tested']=True
            self.assertEqual(self.request('/api/models/use',{'stage':'transcription','provider':'local','model':'medium'})[0],200)
            self.assertEqual(self.app.store.config()['whisper_model'],'/new-medium.bin')

    def test_failed_independent_check_cannot_validate_model(self):
        m={'id':'test','label':'Test','installed':True,'fingerprint':'a','tested':False}
        with patch.object(self.app.models,'catalog',return_value={'asr':[],'llm':[m],'whisper_runtime':False,'ollama':True}),patch.object(self.app,'model_test_preflight'),patch.object(self.app.model_checks,'execute',return_value=''),patch.object(self.app.models,'validate_pair') as validate:
            self.assertEqual(self.request('/api/models/check',{'stage':'summary','provider':'local','model':'test'})[0],200)
            self.app.model_checks.thread.join(3);validate.assert_not_called()
            self.assertEqual(self.app.model_checks.public()['state'],'failed')

    def test_check_blocks_recording_configuration_and_duplicate_start_until_complete(self):
        gate=threading.Event()
        m={'id':'test','label':'Test','installed':True,'fingerprint':'a','tested':False}
        with patch.object(self.app.models,'catalog',return_value={'asr':[],'llm':[m],'whisper_runtime':False,'ollama':True}),patch.object(self.app,'model_test_preflight'),patch.object(self.app.model_checks,'execute',side_effect=lambda *_:(gate.wait(3) or True) and 'Result'),patch.object(self.app.models,'validate_pair'):
            body={'stage':'summary','provider':'local','model':'test'}
            try:
                self.assertEqual(self.request('/api/models/check',body)[0],200)
                caps=self.app.capabilities()
                for key in ('record','configure','install','model_test'):self.assertFalse(caps[key]['allowed'])
                self.assertEqual(self.request('/api/models/check',body)[0],400)
                self.assertEqual(self.request('/api/models/use',body)[0],400)
            finally:gate.set();self.app.model_checks.thread.join(3)
            self.assertTrue(self.app.capabilities()['configure']['allowed'])

    def test_cloud_activation_requires_successful_same_account_and_stage_check(self):
        session={'server':'https://staging.cdbos.de','identity':{'user_id':'one','client_id':'tenant'}}
        with patch.object(self.app.cdb,'session',return_value=session),patch.object(self.app.cdb,'configure') as configure,patch.object(self.app.model_checks,'execute',return_value='Synthetisches Ergebnis'):
            body={'stage':'summary','provider':'cdb'}
            self.assertEqual(self.request('/api/models/use',body)[0],400)
            self.assertEqual(self.request('/api/models/check',body)[0],200);self.app.model_checks.thread.join(3)
            self.assertEqual(self.request('/api/models/use',body)[0],200)
            configure.assert_called_once_with({'summary':'cdb'})
            self.assertEqual(self.request('/api/models/use',body|{'stage':'transcription'})[0],400)
            session['identity']['user_id']='other'
            self.assertEqual(self.request('/api/models/use',body)[0],400)

    def test_successes_survive_other_model_tests_and_restart(self):
        from services.model_checks import ModelChecks
        checks=self.app.model_checks
        binding={'server':'https://staging.cdbos.de','user_id':'one','client_id':'tenant'}
        checks.latest={'stage':'summary','provider':'cdb','model':'company-standard','binding':binding}
        checks.save(state='completed',result='Anna erstellt die Liste.')
        checks.latest={'stage':'transcription','provider':'local','model':'medium','fingerprint':'exact-model-and-runtime'}
        checks.save(state='completed',result='Anna erstellt die Liste.')
        checks.latest={'stage':'summary','provider':'local','model':'other'}
        checks.save(state='failed',message='Test fehlgeschlagen')
        restored=ModelChecks(self.app)
        self.assertEqual(len(restored.results()),2)
        self.assertEqual(next(r for r in restored.results() if r['provider']=='local')['fingerprint'],'exact-model-and-runtime')
        with patch.object(self.app.cdb,'session',return_value={'server':binding['server'],'identity':binding}),patch.object(self.app.cdb,'configure') as configure:
            restored.use({'stage':'summary','provider':'cdb'})
            configure.assert_called_once_with({'summary':'cdb'})

    def test_running_check_is_not_reported_as_success_after_restart(self):
        from services.model_checks import ModelChecks
        self.app.model_checks.save(state='running',stage='summary',provider='local',model='example')
        restored=ModelChecks(self.app)
        self.assertEqual(restored.public()['state'],'failed')
        self.assertIn('unterbrochen',restored.public()['message'])

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
