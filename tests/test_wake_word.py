import io
import tempfile
import unittest
from unittest.mock import patch, Mock
from services.wake_word import WakeWord

class WakeTests(unittest.TestCase):
    def setUp(self):
        runtime=patch('services.wake_word.runtime_ready',return_value=True)
        runtime.start();self.addCleanup(runtime.stop)
        self.tmp=tempfile.TemporaryDirectory();self.now=100
        self.wake=WakeWord(self.tmp.name,lambda:self.now);self.wake.runtime=True
        self.account={'user_id':'a','client_id':'b','server':'https://example.test'}
    def tearDown(self):self.wake.process=None;self.tmp.cleanup()
    def tick(self,reason='',trigger=None,account=None):
        return self.wake.tick(account=self.account if account is None else account,reason=reason,config={'device':'test'},trigger=trigger or Mock())
    def test_opt_in_persistence_and_account_reset(self):
        self.assertFalse(self.wake.enabled);self.wake.configure(True,self.account)
        restored=WakeWord(self.tmp.name);self.assertTrue(restored.enabled)
        self.tick(account={'user_id':'other'});self.assertFalse(self.wake.enabled)
        self.assertFalse(WakeWord(self.tmp.name).enabled)
    def test_record_pause_live_and_playback_block_detector(self):
        self.wake.configure(True,self.account);self.now+=2
        with patch('services.wake_word.subprocess.Popen') as spawn:
            for reason in ['Aufnahme läuft.','Aufnahme pausiert.','Live-Gespräch wird verbunden.','Audiowiedergabe läuft.']:
                self.tick(reason);self.assertEqual(self.wake.mode,'waiting')
            spawn.assert_not_called()
    def test_detection_handoff_after_capture_release(self):
        self.wake.configure(True,self.account);self.now+=2
        process=Mock();process.poll.return_value=None;process.stdout=io.BytesIO(b'detected\n');self.wake.process=process
        def trigger():self.assertIsNone(self.wake.process);process.wait.assert_called_once()
        with patch('services.wake_word.select.select',return_value=([process.stdout],[],[])),patch('services.wake_word.os.killpg'):
            self.tick(trigger=trigger)
        self.assertEqual(self.wake.count,1)
        self.assertGreater(self.wake.public()['recognized_for'],0)
        self.now+=9;self.assertEqual(self.wake.public()['recognized_for'],0)
    def test_test_mode_never_starts_cloud(self):
        self.wake.test();self.now+=2
        process=Mock();process.poll.return_value=None;process.stdout=io.BytesIO(b'detected\n');self.wake.process=process;trigger=Mock()
        with patch('services.wake_word.select.select',return_value=([process.stdout],[],[])),patch('services.wake_word.os.killpg'):
            self.tick(trigger=trigger)
        trigger.assert_not_called();self.assertEqual(self.wake.count,1)

    def test_returns_to_listening_after_live_ends(self):
        self.wake.configure(True,self.account);self.now+=2
        self.tick(reason='Live-Gespräch läuft.')
        process=Mock();process.poll.return_value=None;process.stdout=io.BytesIO(b'ready\n')
        with patch('services.wake_word.subprocess.Popen',return_value=process),patch('services.wake_word.select.select',return_value=([process.stdout],[],[])):
            self.now+=4;self.tick()
        self.assertEqual(self.wake.mode,'listening')
        self.assertEqual(self.wake.public()['word'],'Hey Brain')

    def test_missing_model_cannot_enable(self):
        self.wake.runtime=False
        with self.assertRaises(ValueError):self.wake.configure(True,self.account)
        self.assertFalse(self.wake.enabled)

    def test_phrase_is_persisted_and_old_settings_keep_brain(self):
        import json
        self.wake.path.write_text(json.dumps({'enabled':True,'account':self.account}))
        self.assertEqual(WakeWord(self.tmp.name).phrase,'hey-brain')
        old_instance=self.wake.instance
        self.wake.select_phrase('okay-kai')
        self.assertNotEqual(self.wake.instance,old_instance)
        restored=WakeWord(self.tmp.name)
        self.assertEqual(restored.phrase,'okay-kai')
        self.assertEqual(restored.public()['word'],'Okay KAI')
        self.wake.configure(True,self.account)
        self.wake.configure(False,None)
        self.assertEqual(WakeWord(self.tmp.name).phrase,'okay-kai')
        self.wake.path.write_text(json.dumps({'enabled':True,'phrase':['invalid']}))
        restored=WakeWord(self.tmp.name)
        self.assertFalse(restored.enabled)
        self.assertEqual(restored.phrase,'hey-brain')

    def test_phrase_cannot_change_during_listening_or_test(self):
        self.wake.configure(True,self.account)
        with self.assertRaises(ValueError):self.wake.select_phrase('hey-kai')
        self.wake.configure(False,None);self.wake.test()
        with self.assertRaises(ValueError):self.wake.select_phrase('okay-kai')
        self.assertEqual(self.wake.phrase,'hey-brain')
        for invalid in ('arbitrary word',None,[],{}):
            with self.assertRaises(ValueError):self.wake.select_phrase(invalid)

    def test_selected_phrase_reaches_owned_child_and_readiness_message(self):
        self.wake.select_phrase('hey-kai');self.wake.configure(True,self.account)
        process=Mock();process.poll.return_value=None;process.stdout=io.BytesIO(b'ready\n')
        with patch('services.wake_word.subprocess.Popen',return_value=process) as spawn,patch('services.wake_word.select.select',return_value=([process.stdout],[],[])):
            self.now+=4;self.tick()
        self.assertIn('hey-kai',spawn.call_args.args[0])
        self.assertIn('Hey KAI',self.wake.message)


class PhraseTests(unittest.TestCase):
    def test_selected_phrase_only_and_confusable_rejection(self):
        from services.wake_phrase import is_activation
        def result(text):
            return {'text':text,'result':[{'word':w,'conf':1,'start':i*.3,'end':(i+1)*.3} for i,w in enumerate(text.split())]}
        for phrase,text in [('hey-brain','hey brain'),('hey-kai','hey kai'),('okay-kai','okay kai')]:
            self.assertTrue(is_activation(result(text),phrase))
            self.assertTrue(is_activation(result(text+' '+text),phrase))
            for other in ('hey brain','hey kai','okay kai','hey guy','okay kyle','okay','kai'):
                if other!=text:self.assertFalse(is_activation(result(other),phrase))
            weak=result(text);weak['result'][1]['conf']=.49 if phrase=='hey-kai' else .89
            self.assertFalse(is_activation(weak,phrase))

    def test_hey_kai_calibration_preserves_other_phrase_and_boundary_guards(self):
        from services.wake_phrase import is_activation
        def result(left='hey', right='kai', first=1, second=.525806, duration=.72):
            return {'text':left+' '+right, 'result':[
                {'word':left, 'conf':first, 'start':0, 'end':.3},
                {'word':right, 'conf':second, 'start':.3, 'end':duration}]}
        for score in (.525806, .657463, .5):
            self.assertTrue(is_activation(result(second=score), 'hey-kai'))
        for sample in (result(second=.4999), result(first=.7999), result(duration=.249),
                       result(duration=2.501), result(right='guy'), result(right='kyle'),
                       result(right='kay'), result(left='okay'), result(left='hi')):
            self.assertFalse(is_activation(sample, 'hey-kai'))
        self.assertFalse(is_activation(result(right='brain',second=.89), 'hey-brain'))
        self.assertFalse(is_activation(result(left='okay',second=.89), 'okay-kai'))

    def test_only_confident_complete_phrase_wakes(self):
        from services.wake_phrase import is_activation
        result={'text':'hey brain','result':[{'word':'hey','conf':1,'start':0,'end':.3},{'word':'brain','conf':1,'start':.3,'end':.8}]}
        self.assertTrue(is_activation(result))
        for text in ['hey brian','hey rain','[unk]','hey brain [unk]','the brain','hey']:
            self.assertFalse(is_activation({**result,'text':text}))
        result['result'][1]['conf']=.89
        self.assertFalse(is_activation(result))
        self.assertFalse(is_activation({'text':'hey brain'}))

    def test_completed_background_does_not_leak_into_next_split_phrase(self):
        import json
        import sys
        from types import SimpleNamespace
        from services.wake_phrase import PhraseDetector
        class Decoder:
            def __init__(self, *args): self.words=[]
            def SetWords(self, enabled): pass
            def AcceptWaveform(self, block):
                if block: self.words.append(block.decode())
                return not block
            def Result(self):
                return json.dumps({'text':' '.join(self.words), 'result':[
                    {'word':w,'conf':1,'start':i*.3,'end':(i+1)*.3}
                    for i,w in enumerate(self.words)]})
        model=Mock();decoder=Mock(side_effect=Decoder)
        fake=SimpleNamespace(Model=model,KaldiRecognizer=decoder,SetLogLevel=Mock())
        with patch.dict(sys.modules, {'vosk':fake}):
            d=PhraseDetector()
            self.assertFalse(d.feed(b''))  # Quiet input must not churn decoders.
            self.assertEqual(decoder.call_count,1)
            self.assertFalse(d.feed(b'background'))
            self.assertFalse(d.feed(b''))
            self.assertFalse(d.feed(b'hey'))
            self.assertFalse(d.feed(b'brain'))
            self.assertEqual(decoder.call_count,2)  # No reset between the words.
            self.assertTrue(d.feed(b''))
            self.assertFalse(d.feed(b''))
            self.assertEqual(decoder.call_count,3)
            model.assert_called_once()


class WakeAccountTests(unittest.TestCase):
    def test_token_expiry_preserves_opt_in_but_logout_and_config_change_do_not(self):
        from web_server import StudioApp
        app=StudioApp.__new__(StudioApp);app.cdb=Mock()
        config={'server':'https://staging.example.test','client_id':'oauth-app'}
        saved={**config,'expires':1,'identity':{'user_id':'owner','client_id':'tenant'}}
        app.cdb.config.return_value=config;app.cdb.read.return_value=saved
        self.assertEqual(app.wake_account(),{'server':config['server'],'user_id':'owner','client_id':'tenant'})
        app.cdb.session.assert_not_called()  # No network in the locked ambient loop.
        app.cdb.read.return_value={};self.assertIsNone(app.wake_account())
        app.cdb.read.return_value={**saved,'server':'https://other.example.test'};self.assertIsNone(app.wake_account())
        app.cdb.read.return_value={**saved,'client_id':'other-app'};self.assertIsNone(app.wake_account())


class ContinuousPhraseTests(unittest.TestCase):
    def test_wake_phrase_after_background_and_repeated_call(self):
        from services.wake_phrase import is_activation
        hey={'word':'hey','conf':1,'start':1,'end':1.3}
        brain={'word':'brain','conf':1,'start':1.3,'end':1.9}
        prefix={'word':'[unk]','conf':1,'start':0,'end':.8}
        self.assertTrue(is_activation({'text':'[unk] hey brain','result':[prefix,hey,brain]}))
        self.assertTrue(is_activation({'text':'hey brain hey brain','result':[hey,brain,hey,brain]}))
        self.assertFalse(is_activation({'text':'hey brian','result':[hey,{**brain,'word':'brian'}]}))
        self.assertFalse(is_activation({'text':'hey brain','result':[hey,{**brain,'conf':.6}]}))
