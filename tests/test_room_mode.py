import json
import time
import unittest
from unittest.mock import patch, Mock
import test_studio
from services.room_mode import RoomMode


class RoomTests(unittest.TestCase):
    setUp = test_studio.StudioTests.setUp
    tearDown = test_studio.StudioTests.tearDown
    request = test_studio.StudioTests.request

    def login(self, user='alice', tenant='12345678-1234-1234-1234-123456789012'):
        c = self.app.cdb.config()
        self.app.cdb.write('session.json', {'server': c['server'], 'client_id': c['client_id'],
            'identity': {'user_id': user, 'client_id': tenant, 'name': user},
            'token': 'synthetic-test', 'expires': time.time()+3600})
        self.app.cdb.login = {'state': 'completed'}

    def enable(self):
        self.app.ambient_stop.set(); self.app.ambient_thread.join(3)
        status, data, _ = self.request('/api/room/configure', {'enabled':True, 'pin':'123456', 'idle_minutes':5})
        self.assertEqual(status, 200, data)

    def job(self, title='Private meeting'):
        ident = self.app.store.create(title)
        folder = self.app.store.folder(ident)
        (folder/'audio.wav').write_bytes((self.root/'test.wav').read_bytes())
        (folder/'transcript.txt').write_text('private transcript')
        self.app.store.update(ident, state='failed', error='synthetic failure')
        self.app.controller.sync()
        row = next(row for row in self.app.repo.get_all() if row.get('local_job_id') == ident)
        return ident, row['id']

    def test_opt_in_preserves_legacy_and_requires_pin(self):
        self.assertFalse(self.app.room.enabled)
        self.assertEqual(len(self.app.state()['sessions']),1)
        self.assertEqual(self.request('/api/room/configure',{'enabled':True})[0],400)
        self.enable()
        self.assertEqual(self.app.state()['sessions'],[])
        self.assertIsNotNone(self.app.repo.get_by_id(self.sid))
        for path in ('/api/record/start','/api/live/reserve','/api/nfc','/api/settings'):
            self.assertEqual(self.request(path,{})[0],400,path)
        self.assertEqual(self.request('/api/room/configure',{'enabled':False})[0],400)
        self.assertEqual(self.request('/api/room/unlock',{'pin':'123456'})[0],200)
        self.assertEqual(self.request('/api/sessions/'+str(self.sid))[0],404)

    def test_owner_filters_every_content_route_and_mutation(self):
        self.enable(); self.login()
        ident, sid = self.job()
        self.assertEqual(len(self.app.state()['sessions']),1)
        self.assertEqual(self.request('/api/sessions/'+str(sid))[0],200)
        self.app.room_logout(); self.login('bob')
        state = self.app.state()
        self.assertEqual(state['sessions'],[]); self.assertEqual(state['jobs'],[])
        self.assertEqual(json.loads(self.request('/api/search?q=Private')[1]),[])
        for base in ('/api/sessions/'+str(sid), '/api/meetings/'+ident):
            for suffix in ('','/audio','/export','/peaks','/transcript','/summary','/metrics'):
                self.assertNotEqual(self.request(base+suffix)[0],200,base+suffix)
        for action in ('save','process','retry','delete'):
            self.assertNotEqual(self.request('/api/sessions/'+str(sid)+'/'+action,{})[0],200,action)
        self.app.room.operator_until = time.monotonic()+100
        self.assertNotEqual(self.request('/api/sessions/'+str(sid))[0],200)
        self.app.room.configure({'enabled':False})
        self.assertNotEqual(self.request('/api/sessions/'+str(sid))[0],200)
        self.login(); self.assertEqual(self.request('/api/sessions/'+str(sid))[0],200)

    def test_same_user_other_tenant_is_not_same_owner(self):
        self.enable();self.login();_,sid=self.job()
        self.login(tenant='87654321-1234-1234-1234-123456789012')
        self.assertNotEqual(self.request('/api/sessions/'+str(sid))[0],200)

    def test_nfc_login_never_starts_capture_and_removal_cancels(self):
        self.enable()
        nfc=self.app.nfc;nfc.enabled=True;nfc.tag='a'*64
        nfc.reader=Mock();nfc.reader.snapshot.return_value={'state':'present','tag':nfc.tag}
        with patch.object(self.app.engine,'start') as start:
            with self.assertRaises(ValueError):self.app.nfc_start('meeting')
            intent=self.app.room.intent['id'];self.login();self.app.room.reconcile(nfc)
            start.assert_not_called()
            nfc.reader.snapshot.return_value={'state':'absent'}
            self.app.room.reconcile(nfc)
            self.assertIsNone(self.app.room.intent)
            self.assertEqual(self.request('/api/room/start',{'id':intent})[0],400)
            start.assert_not_called()

    def test_intent_rejects_expiry_error_and_account_change(self):
        self.enable();self.login()
        now=[100.0];self.app.room.clock=lambda:now[0]
        self.app.room.begin('meeting');ident=self.app.room.intent['id']
        now[0]+=301
        self.assertEqual(self.request('/api/room/start',{'id':ident})[0],400)
        self.app.room.begin('meeting');ident=self.app.room.intent['id'];self.login('bob')
        self.assertEqual(self.request('/api/room/start',{'id':ident})[0],400)
        nfc=self.app.nfc;nfc.enabled=True;nfc.reader=Mock();nfc.reader.snapshot.return_value={'state':'error'}
        self.app.room.begin('talk','a'*64);self.app.room.reconcile(nfc)
        self.assertIsNone(self.app.room.intent)

    def test_explicit_start_then_nfc_owns_only_that_capture(self):
        self.enable();self.login();self.app.engine.configure({'setup_complete':True})
        nfc=self.app.nfc;nfc.enabled=True;nfc.reader=Mock();nfc.reader.snapshot.return_value={'state':'present','tag':'a'*64}
        self.app.room.begin('meeting','a'*64)
        with patch.object(self.app.engine,'start',return_value='capture-id') as start:
            status,data,_=self.request('/api/room/start',{'id':self.app.room.intent['id']})
            self.assertEqual(status,200,data);start.assert_called_once()
        self.assertEqual(nfc.owner,('meeting','capture-id'));self.assertIsNone(self.app.room.intent)

    def test_failed_stop_keeps_account_and_recording(self):
        self.enable();self.login()
        with patch.object(self.app.engine.recorder,'active','synthetic-id'), patch.object(self.app.engine,'stop',side_effect=ValueError('stop failed')):
            self.assertEqual(self.request('/api/room/finish',{'confirm':True})[0],400)
            self.assertIsNotNone(self.app.room.account())

    def test_restart_does_not_reuse_room_login_or_intent(self):
        self.enable();self.login();ident,sid=self.job();self.app.room.begin('meeting')
        restarted=RoomMode(self.app.store.root,self.app.cdb)
        self.assertTrue(restarted.enabled);self.assertIsNone(restarted.account());self.assertIsNone(restarted.intent)
        self.assertIsNotNone(restarted.owner(self.app.store.folder(ident)))
        self.assertIsNotNone(self.app.repo.get_by_id(sid))

    def test_pin_rate_limit_and_no_plain_pin_storage(self):
        self.enable()
        self.assertNotIn('123456',self.app.room.path.read_text())
        for _ in range(5):self.assertEqual(self.request('/api/room/unlock',{'pin':'999999'})[0],400)
        self.assertEqual(self.request('/api/room/unlock',{'pin':'123456'})[0],400)

    def test_publications_do_not_leak_across_users(self):
        self.enable();self.login()
        binding=self.app.room.account()
        with self.app.cdb.db() as db:
            db.execute('INSERT INTO publications VALUES(?,?,?,?,?,?)',('job','fingerprint',json.dumps({'title':'secret title','binding':binding}),'failed','',''))
        self.assertEqual(len(self.app.cdb.public()['publications']),1)
        self.login('bob');self.assertEqual(self.app.cdb.public()['publications'],[])

    def test_idle_signout_pauses_during_capture_and_live(self):
        from services.app_activity import AppActivity
        self.enable();self.login()
        now=[100.0];self.app.room.clock=lambda:now[0]
        self.app.tick_room()
        for activity in (AppActivity(recording=True),AppActivity(recording=True,paused=True),AppActivity(live='active')):
            now[0]+=400
            with patch.object(self.app,'activity',return_value=activity):self.app.tick_room()
            self.assertIsNotNone(self.app.room.account())
        now[0]+=301
        with patch.object(self.app,'activity',return_value=AppActivity()):self.app.tick_room()
        self.assertIsNone(self.app.room.account())

    def test_independent_pending_login_not_cancelled_by_nfc_intent(self):
        self.enable();self.app.cdb.login={'state':'pending'}
        self.app.room.begin('meeting')
        with patch.object(self.app.cdb,'start_login',return_value={}) as login:
            self.app.action('/api/cdb/login',{})
        self.app.room.cancel()
        self.assertEqual(self.app.cdb.login['state'],'pending')

    def test_timer_labels_and_operations_are_account_bound(self):
        self.enable();self.login()
        row=self.app.action('/api/timers',{'action':'create','kind':'timer','seconds':120,'label':'Private reminder','request_id':'private-timer-test'})
        self.assertEqual(len(self.app.state()['timers']['items']),1)
        self.login('bob')
        self.assertEqual(self.app.state()['timers']['items'],[])
        self.assertEqual(self.request('/api/timers',{'action':'cancel','id':row['id'],'revision':1})[0],400)
        self.assertEqual(json.loads(self.request('/api/lcd/timers')[1])['timers'],[])

    def test_offline_processing_waits_without_changing_owner_or_route(self):
        from services.cdb_integration import CdbBackend, CdbWaiting
        self.enable();self.login();ident,sid=self.job()
        folder=self.app.store.folder(ident)
        route={'transcription':'cdb','summary':'local','binding':self.app.room.account()}
        (folder/'cdb-request.json').write_text(json.dumps(route))
        backend=CdbBackend(self.app.cdb)
        with patch.object(backend,'remote_transcribe',side_effect=CdbWaiting('Netzwerk fehlt.')):
            with self.assertRaises(CdbWaiting):backend.transcribe(folder,{})
        self.assertTrue((folder/'brain-wait.json').exists())
        self.assertTrue(next(j for j in self.app.state()['jobs'] if j['id']==ident)['waiting_for_brain'])
        self.assertEqual(json.loads((folder/'cdb-request.json').read_text()),route)
        self.app.room_logout();self.login('bob')
        self.assertEqual(self.request('/api/sessions/'+str(sid)+'/retry',{})[0],400)

    def test_clean_install_files_allowlisted_and_no_private_schema_change(self):
        from fleet.releases import allowed
        for path in ('services/room_mode.py','studio/room.js','studio/room.css'):
            self.assertTrue(allowed(path))
        self.assertFalse(allowed('room-mode.json'))
        self.assertFalse(allowed('meetings/abc/room-owner.json'))
        self.enable()
        with self.app.repo.connection() as db:
            self.assertNotIn('owner',{r[1] for r in db.execute('PRAGMA table_info(sessions)')})


if __name__ == '__main__':unittest.main()
