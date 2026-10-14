import io
import tempfile
import unittest
from unittest.mock import patch, Mock
from services.wake_word import WakeWord

class WakeTests(unittest.TestCase):
    def setUp(self):
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


class PhraseTests(unittest.TestCase):
    def test_only_confident_complete_phrase_wakes(self):
        from services.wake_phrase import is_activation
        result={'text':'hey brain','result':[{'word':'hey','conf':1,'start':0,'end':.3},{'word':'brain','conf':1,'start':.3,'end':.8}]}
        self.assertTrue(is_activation(result))
        for text in ['hey brian','hey rain','[unk]','hey brain [unk]','the brain','hey']:
            self.assertFalse(is_activation({**result,'text':text}))
        result['result'][1]['conf']=.89
        self.assertFalse(is_activation(result))
        self.assertFalse(is_activation({'text':'hey brain'}))
