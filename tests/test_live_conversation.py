import tempfile
import threading
import time
import unittest
from pathlib import Path
from services.live_conversation import LiveConversation, BASE

AREA='11111111-1111-1111-1111-111111111111'

class Brain:
    generation=0
    def __init__(self):
        self.calls=[];self.block=None;self.reached=threading.Event();self.fail=False
    def session(self,binding=None):
        return {'server':'https://staging.cdbos.de','identity':{'user_id':'test-user','client_id':AREA},'token':'do-not-expose'}
    def public(self):return {'destination':{'id':AREA}}
    def areas(self,binding=None):return [{'id':AREA,'name':'staging_playground','label':'Staging'}]
    def call(self,path,body=None,binding=None):
        self.calls.append((path,body,binding))
        if path.endswith('/capabilities'):return {'enabled':True,'max_areas':8,'heartbeat_seconds':15}
        if path==BASE+'/sessions':
            self.reached.set()
            if self.block:self.block.wait(3)
            if self.fail:raise ValueError('secret provider error')
            return {'session_handle':'safe-handle','sdp_answer':'v=0\r\nanswer'}
        return {}

class LiveTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory();self.brain=Brain();self.events_release=threading.Event()
        def events(handle,binding,callback):self.events_release.wait(3)
        self.live=LiveConversation(self.brain,self.root.name,events=events)
    def tearDown(self):
        self.events_release.set();self.live.close();self.root.cleanup()
    def wait(self,predicate):
        until=time.monotonic()+3
        while not predicate() and time.monotonic()<until:time.sleep(.01)
        self.assertTrue(predicate())
    def reserve(self):return self.live.reserve([AREA])['lease']
    def test_reservation_excludes_second_owner_and_requires_valid_areas(self):
        for value in ([],[{}],[AREA,AREA],['invalid'],[AREA]*9,None):
            with self.assertRaises(ValueError):self.live.reserve(value)
        lease=self.reserve();self.assertTrue(self.live.busy())
        with self.assertRaises(ValueError):self.reserve()
        with self.assertRaises(ValueError):self.live.pulse('another-tab')
        self.live.pulse(lease)
        self.assertNotIn(lease,str(self.live.public()))
        self.assertNotIn('do-not-expose',str(self.live.public()))
    def test_start_uses_scoped_cdb_contract_and_owner_only_sdp(self):
        lease=self.reserve();self.live.start(lease,'v=0\r\noffer')
        self.wait(lambda:self.live.public()['state']=='listening')
        self.assertEqual(self.live.status(lease)['sdp_answer'],'v=0\r\nanswer')
        self.assertNotIn('answer',str(self.live.public()))
        request=next(body for path,body,_ in self.brain.calls if path==BASE+'/sessions')
        self.assertEqual(request['area_ids'],[AREA]);self.assertEqual(request['language'],'de')
        self.assertNotIn('token',request)
        self.live.mute(lease,True);self.assertTrue(self.live.public()['muted'])
        with self.assertRaises(ValueError):self.live.mute(lease,'true')
    def test_failed_start_releases_reservation_without_exposing_provider_error(self):
        self.brain.fail=True;lease=self.reserve();self.live.start(lease,'v=0\r\n')
        self.wait(lambda:not self.live.busy())
        self.assertEqual(self.live.public()['state'],'error')
        self.assertNotIn('secret',str(self.live.public()))
        self.reserve()
    def test_cancel_during_remote_start_keeps_lock_until_late_session_closed(self):
        self.brain.block=threading.Event();lease=self.reserve();self.live.start(lease,'v=0\r\n')
        self.assertTrue(self.brain.reached.wait(1));self.live.end(lease)
        self.assertTrue(self.live.busy());self.assertEqual(self.live.public()['state'],'closing')
        with self.assertRaises(ValueError):self.reserve()
        self.brain.block.set();self.wait(lambda:not self.live.busy())
        self.assertTrue(any(path.endswith('/safe-handle/close') for path,_,_ in self.brain.calls))
    def test_transcripts_persist_and_stale_events_do_not_contaminate_new_session(self):
        lease=self.reserve();generation=self.live.generation
        self.live._frame(generation,'transcript',{'role':'user','delta':'Hallo '})
        self.live._frame(generation,'transcript',{'role':'user','delta':'Brain'})
        self.live._frame(generation,'transcript',{'role':'assistant','delta':'Guten Tag'})
        self.live.end(lease);self.wait(lambda:not self.live.busy())
        self.assertEqual(self.live.public()['history'][0]['text'],'Hallo Brain')
        files=list((Path(self.root.name)/'live').glob('conversation-*.json'))
        self.assertEqual(len(files),1);self.assertEqual(files[0].stat().st_mode&0o777,0o600)
        self.live.clear();self.reserve();self.live._frame(generation,'transcript',{'role':'user','delta':'stale'})
        self.assertEqual(self.live.public()['history'],[])
    def test_history_is_restored_only_for_matching_account_and_hidden_on_logout(self):
        lease=self.reserve();generation=self.live.generation
        self.live._frame(generation,'transcript',{'role':'user','delta':'Account scoped text'})
        self.live.end(lease);self.wait(lambda:not self.live.busy())
        self.brain.generation+=1
        self.assertEqual(self.live.public()['history'],[])
        self.live.restored_binding=None
        self.live.setup()
        self.assertEqual(self.live.public()['history'][0]['text'],'Account scoped text')
        self.live.clear();self.live.setup()
        self.assertEqual(self.live.public()['history'],[])
        self.assertEqual(len(list((Path(self.root.name)/'live').glob('conversation-*.json'))),1)
        self.brain.session=lambda binding=None:{'server':'https://staging.cdbos.de','identity':{'user_id':'other-user','client_id':AREA}}
        self.brain.generation+=1
        self.live.setup()
        self.assertEqual(self.live.public()['history'],[])

    def test_interleaved_syllables_join_same_speaker_and_later_question_starts_new_turn(self):
        self.reserve();g=self.live.generation
        frames=[('user',' Dies ist ein technischer Test ohne Kundend',0,2500),
                ('assistant',' Alles klar',2600,3000),('user','aten',2500,2600),
                ('assistant','.',3000,3100),('user','Eine neue Frage.',8000,9000)]
        for role,delta,start,end in frames:
            self.live._frame(g,'transcript',{'role':role,'delta':delta,'start_ms':start,'end_ms':end})
        self.assertEqual([r['text'] for r in self.live.history],
                         ['Dies ist ein technischer Test ohne Kundendaten','Alles klar.','Eine neue Frage.'])
        self.live._frame(g,'transcript',{'role':'assistant','delta':'.','start_ms':3000,'end_ms':3100})
        self.assertEqual(self.live.history[1]['text'],'Alles klar.')

    def test_interleaved_fragments_without_timestamps_use_per_role_arrival_window(self):
        self.reserve();g=self.live.generation
        for role,delta in [('user','Daten'),('assistant','Verstanden'),('user','schutz'),('assistant','.')]:
            self.live._frame(g,'transcript',{'role':role,'delta':delta})
        self.assertEqual([r['text'] for r in self.live.history],['Datenschutz','Verstanden.'])

    def test_closing_preserves_final_transcript_without_returning_to_listening(self):
        self.reserve();g=self.live.generation
        self.live._frame(g,'transcript',{'role':'user','delta':'Daten'})
        self.live.state='closing'
        self.live._frame(g,'state',{'state':'listening'})
        self.live._frame(g,'transcript',{'role':'user','delta':'schutz'})
        self.assertEqual(self.live.state,'closing')
        self.assertEqual(self.live.history[0]['text'],'Datenschutz')
        self.live._frame(g,'closed',{'reason':'user'})
        self.assertFalse(self.live.busy())

    def install_native(self, block=None, fail=False):
        class FakeAudio:
            def __init__(self, config, on_failure):
                self.config=config;self.on_failure=on_failure;self.closed=False;self.muted=False;self.entered=threading.Event();self.reply=None
            def open(inner):
                inner.entered.set()
                if block:block.wait(2)
                if fail or inner.closed:raise ValueError('hardware failed')
                return 'v=0\r\nnative offer'
            def answer(inner, sdp):inner.reply=sdp
            def mute(inner, muted):inner.muted=muted
            def close(inner):inner.closed=True;block.set() if block else None
        self.live.audio_config=lambda:{'device':'plughw:CARD=Array,DEV=0','speaker':'chosen-sink'}
        self.live.audio_factory=FakeAudio

    def test_native_audio_uses_snapshot_mutes_and_stops_before_ownership_release(self):
        self.install_native();lease=self.reserve();self.live.start_native(lease)
        native=self.live.native
        self.wait(lambda:native.reply is not None)
        self.assertEqual(native.config['device'],'plughw:CARD=Array,DEV=0')
        self.live.mute(lease,True);self.assertTrue(native.muted)
        self.live.end(lease);self.wait(lambda:not self.live.busy())
        self.assertTrue(native.closed);self.assertIsNone(self.live.native)

    def test_cancel_during_native_open_stops_hardware_and_never_starts_cloud(self):
        block=threading.Event();self.install_native(block=block)
        lease=self.reserve();self.live.start_native(lease);native=self.live.native
        self.assertTrue(native.entered.wait(1));self.live.end(lease)
        self.wait(lambda:not self.live.busy())
        self.assertTrue(native.closed)
        self.assertFalse(any(path==BASE+'/sessions' for path,_,_ in self.brain.calls))

    def test_native_open_failure_releases_audio_and_reservation(self):
        self.install_native(fail=True);lease=self.reserve();self.live.start_native(lease)
        self.wait(lambda:not self.live.busy())
        self.assertIsNone(self.live.native);self.assertEqual(self.live.state,'error')

    def test_native_constructor_failure_does_not_leave_unclosable_reservation(self):
        self.install_native()
        def broken(config, callback):raise ValueError('failed constructor')
        self.live.audio_factory=broken;lease=self.reserve()
        with self.assertRaises(ValueError):self.live.start_native(lease)
        self.assertFalse(self.live.started_request)
        self.live.end(lease);self.wait(lambda:not self.live.busy())

    def test_browser_lease_timeout_and_account_change_end_sessions(self):
        lease=self.reserve();self.live.deadline=0
        self.wait(lambda:not self.live.busy())
        self.reserve();self.brain.generation+=1
        self.wait(lambda:not self.live.busy())

if __name__=='__main__':unittest.main()

class FeedbackConversationTests(unittest.TestCase):
    setUp=LiveTests.setUp
    tearDown=LiveTests.tearDown
    wait=LiveTests.wait
    reserve=LiveTests.reserve
    def test_search_replay_only_plays_once_and_preferences_survive(self):
        from unittest.mock import Mock
        lease=self.reserve();native=Mock();native.feedback.return_value={};self.live.native=native
        self.live._frame(self.live.generation,'search',{'call_id':'a','status':'started'})
        self.live._frame(self.live.generation,'search',{'call_id':'a','status':'started'})
        self.assertEqual(self.live.feedback()['search']['brain'],1);self.assertEqual(native.update_search.call_count,2)
        with self.assertRaises(ValueError):self.live.preferences(False,'foreign')
        self.live.preferences(False,lease);self.live._frame(self.live.generation,'search',{'call_id':'b','status':'started'})
        self.assertEqual(native.update_search.call_count,3);self.assertFalse(self.live.feedback()['search_sound'])
        self.live._frame(self.live.generation,'search',{'call_id':'a','status':'done'})
        native.update_search.assert_called_with('brain','a','done')
        self.live._frame(self.live.generation-1,'search',{'call_id':'stale','status':'started'})
        self.assertEqual(self.live.feedback()['search']['brain'],1)
        self.live.end(lease);self.wait(lambda:not self.live.busy());self.assertEqual(self.live.feedback()['search']['brain'],0)
        restored=LiveConversation(self.brain,self.root.name)
        try:self.assertFalse(restored.search_sound)
        finally:restored.close()
