import tempfile
import threading
import time
import unittest
from pathlib import Path
from services.live_conversation import LiveConversation, BASE
from services.cdb_integration import CdbFailure

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
    def test_device_owner_retains_browser_timeout_and_activity_extension(self):
        now=[100.];self.live.clock=lambda:now[0]
        self.live.reserve([AREA],owner_kind='device')
        self.assertEqual(self.live.deadline,220)
        self.assertEqual(self.live.public()['owner_kind'],'device')
        now[0]=130;self.live._transcript({'role':'user','delta':'Hallo'})
        self.assertEqual(self.live.deadline,250)
        self.live._finish('ended');self.live.reserve([AREA])
        self.assertEqual(self.live.deadline,155)

    def test_display_preserves_more_than_200_turns_and_long_messages_after_restart(self):
        self.reserve()
        for i in range(305):
            self.live._transcript({'role':'user' if i%2 else 'assistant','delta':f'Beitrag {i}', 'item_id':str(i)})
        self.live._transcript({'role':'assistant','delta':'x'*60001,'item_id':'long'})
        binding=self.live.binding
        snapshot=self.live.display_snapshot(binding)
        self.assertEqual(len(snapshot['history']),306)
        self.assertEqual(snapshot['history'][0]['text'],'Beitrag 0')
        self.assertEqual(len(snapshot['history'][-1]['text']),60001)
        self.live._finish('ended')
        restored=LiveConversation(self.brain,self.root.name,events=lambda *args:None)
        try:
            restored.setup()
            self.assertEqual(restored.display_snapshot(binding)['history'],snapshot['history'])
            self.assertEqual(restored.display_snapshot({'user_id':'other'})['history'],[])
            self.brain.generation+=1
            self.assertEqual(restored.display_snapshot(binding)['history'],[])
        finally:restored.close()

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
    def test_denied_area_selection_is_actionable_and_releases_device(self):
        original = self.brain.call
        def call(path, body=None, binding=None):
            if path == BASE + '/sessions':
                raise CdbFailure('Keine Berechtigung für diese CDB-Aktion.')
            return original(path, body, binding)
        self.brain.call = call
        lease = self.reserve(); self.live.start(lease, 'v=0\r\n')
        self.wait(lambda: not self.live.busy())
        self.assertIn('Bereichsauswahl nicht freigegeben', self.live.public()['error'])
        self.reserve()

    def test_area_selection_survives_restart_and_isolated_by_user_tenant_and_server(self):
        first = self.live.setup(); key = first['selection_account_key']
        self.assertIsNone(first['remembered_area_ids'])
        self.live.remember_areas([AREA], key)
        other = LiveConversation(self.brain, self.root.name, events=lambda *args: None)
        try:
            self.assertEqual(other.setup()['remembered_area_ids'], [AREA])
            original = self.brain.session
            for field in ('user_id', 'client_id', 'server'):
                def session(binding=None, field=field):
                    row = original(binding)
                    if field == 'server': row['server'] = 'https://other.example'
                    else: row['identity'][field] = 'different-account'
                    return row
                self.brain.session = session
                self.assertIsNone(other.setup()['remembered_area_ids'])
                with self.assertRaisesRegex(ValueError, 'Konto hat sich geändert'):
                    other.remember_areas([AREA], key)
                self.brain.session = original
            self.assertEqual(other.setup()['remembered_area_ids'], [AREA])
        finally: other.close()
        path = next((Path(self.root.name) / 'live').glob('areas-*.json'))
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_remembered_empty_missing_and_corrupt_areas_are_handled_safely(self):
        key = self.live.setup()['selection_account_key']
        self.live.remember_areas([], key)
        self.assertEqual(self.live.setup()['remembered_area_ids'], [])
        self.live.remember_areas([AREA], key)
        self.brain.areas = lambda binding=None: []
        self.assertEqual(self.live.setup()['remembered_area_ids'], [])
        path = next((Path(self.root.name) / 'live').glob('areas-*.json'))
        path.write_text('not json')
        self.assertIsNone(self.live.setup()['remembered_area_ids'])
        path.write_text('null')
        self.assertIsNone(self.live.setup()['remembered_area_ids'])

    def test_remembering_rejects_invalid_values_and_running_session(self):
        key = self.live.setup()['selection_account_key']
        for value in (None, 'x', [AREA, AREA], ['../x'], [AREA] * 9):
            with self.assertRaises(ValueError): self.live.remember_areas(value, key)
        self.reserve()
        with self.assertRaisesRegex(ValueError, 'gesperrt'): self.live.remember_areas([AREA], key)

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
        lease=self.reserve();native=Mock();native.feedback.return_value={'search_audio':{'playing':True}};self.live.native=native
        self.assertTrue(self.live.feedback()['search_audio']['playing'])
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
        self.assertFalse(self.live.feedback()['search_audio']['playing'])
        restored=LiveConversation(self.brain,self.root.name)
        try:self.assertFalse(restored.search_sound)
        finally:restored.close()

    def test_device_receipt_retry_and_account_change(self):
        from services.schedules import Schedules
        schedules=Schedules(self.root.name)
        self.reserve();self.live.handle='safe-handle';self.live.device_key='private-device-key';self.live.device_tools=True
        self.live.device_executor=lambda scope,request:schedules.execute_tool(scope,request)
        request={'id':'request-device-0001','name':'create_timer','arguments':{'label':'Tee','seconds':60,'tone':'bell'},'expires_at':time.time()+60}
        answers=[]
        def call(path,body=None,binding=None):
            if 'result' not in body:return {'requests':[request]}
            answers.append(body['result'])
            if len(answers)==1:raise OSError('lost ack')
            return {'ok':True}
        self.brain.call=call
        with self.assertRaises(OSError):self.live._device_commands('safe-handle',self.live.binding)
        self.live._device_commands('safe-handle',self.live.binding)
        self.assertEqual(len(schedules.items()),1);self.assertEqual(answers[0],answers[1])
        self.assertNotIn('private-device-key',str(self.live.public()))
        request['id']='request-device-0002';self.brain.generation+=1
        self.live._device_commands('safe-handle',self.live.binding)
        self.assertEqual(len(schedules.items()),1)

class VoiceEndTests(unittest.TestCase):
    setUp = LiveTests.setUp
    tearDown = LiveTests.tearDown
    wait = LiveTests.wait
    reserve = LiveTests.reserve
    # Isolated unit coverage uses no microphone and no network.
    def test_explicit_command_closes_and_releases_audio(self):
        from unittest.mock import Mock
        lease=self.reserve();self.live.start(lease,'v=0\r\noffer')
        self.wait(lambda:self.live.state=='listening')
        native=Mock();self.live.native=native
        self.live._frame(self.live.generation,'transcript',{'role':'user','delta':'Okay, Gespräch beenden.'})
        self.assertFalse(self.live._voice_end_requested())
        self.wait(lambda:not self.live.busy())
        native.close.assert_called()
        self.assertEqual(self.live.public()['end_reason'],'voice_command')
        self.assertTrue(any(p.endswith('/close') for p,_,_ in self.brain.calls))
        self.reserve();self.assertEqual(self.live.end_reason,'')

    def test_negations_questions_quotes_assistant_and_partial_commands_do_not_close(self):
        self.reserve();self.live.state='listening';self.live.clock=lambda:100
        for text in ['Gespräch beenden?','Nicht das Gespräch beenden','Gespräch beenden bitte nicht',
                     'Wie kann ich das Gespräch beenden?','Sage Gespräch beenden','„Gespräch beenden“',
                     'Gespräch beenden ist ein Befehl','Gespräch','Beende das Gespräch bitte nicht',
                     'Kannst du das Gespräch beenden?', 'Ich beende das Gespräch jetzt',
                     'Alles klar, ich beende das Gespräch jetzt', 'Das wars noch nicht',
                     'Am Ende reden wir weiter', 'Bitte nicht beenden']:
            self.live.transcript_turns={}
            self.live._transcript({'role':'user','delta':text})
            self.live.transcript_turns['user']['received']=98
            self.assertFalse(self.live._voice_end_requested(),text)
        self.live.transcript_turns={}
        self.live._transcript({'role':'assistant','delta':'Gespräch beenden'})
        self.assertFalse(self.live._voice_end_requested())

    def test_split_command_mute_stale_account_and_continuation(self):
        self.reserve();self.live.state='listening';now=[100.];self.live.clock=lambda:now[0]
        self.live._transcript({'role':'user','delta':'Gespräch '})
        now[0]+=.3;self.live._transcript({'role':'user','delta':'beenden'})
        self.assertFalse(self.live._voice_end_requested())
        now[0]+=1.6;self.assertTrue(self.live._voice_end_requested())
        self.live.muted=True;self.assertFalse(self.live._voice_end_requested());self.live.muted=False
        self.brain.generation+=1;self.assertFalse(self.live._voice_end_requested());self.brain.generation-=1
        self.live._transcript({'role':'user','delta':' bitte noch nicht'})
        now[0]+=2;self.assertFalse(self.live._voice_end_requested())

    def test_natural_end_commands_are_whole_user_utterances(self):
        self.reserve(); self.live.state='listening'; self.live.clock=lambda:100
        for text in ['Okay, beende das Gespräch', 'Beende bitte das Gespräch',
                     'Bitte beende das Gespräch jetzt.', 'Gespräch jetzt beenden!',
                     'Unterhaltung beenden', 'Beende die Unterhaltung', 'Ende',
                     'Bitte beenden', 'Das war’s', "Danke, das war's."]:
            with self.subTest(text=text):
                self.live.transcript_turns={}
                self.live._transcript({'role':'user','delta':text})
                self.live.transcript_turns['user']['received']=98
                self.assertTrue(self.live._voice_end_requested())
