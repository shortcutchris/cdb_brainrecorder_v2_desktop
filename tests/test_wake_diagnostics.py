from array import array
import io
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from services.wake_diagnostics import AudioDiagnostics, validate
from services.wake_word import WakeWord


class DiagnosticsTests(unittest.TestCase):
    def test_energy_and_counters_are_text_free_and_window_is_reset(self):
        d = AudioDiagnostics()
        d.feed(array('h', [16384, -16384] * 400).tobytes(), 'candidate_rejected')
        first = d.snapshot()
        self.assertEqual(first['peak_dbfs'], -6)
        self.assertEqual(first['rms_dbfs'], -6)
        self.assertEqual(first['speech_segments'], 1)
        self.assertEqual(first['candidate_rejected'], 1)
        d.feed(bytes(1600), None)
        second = d.snapshot()
        self.assertEqual(second['peak_dbfs'], -96)
        self.assertEqual(second['speech_segments'], 1)
        self.assertEqual(second['blocks'], 2)

    def test_child_data_whitelist_rejects_invalid_numbers_and_text(self):
        d = AudioDiagnostics(); d.feed(bytes(1600), None); value = d.snapshot()
        self.assertEqual(validate({**value, 'transcript': 'private room speech'}), value)
        for replacement in ({'blocks': -1}, {'blocks': True}, {'rms_dbfs': float('nan')},
                            {'peak_dbfs': 999}, {'decision': 'private room speech'}):
            self.assertIsNone(validate({**value, **replacement}))

    def test_parent_keeps_bounded_decisions_and_diagnostics_do_not_trigger(self):
        with tempfile.TemporaryDirectory() as root:
            clock = Mock(return_value=100)
            wake = WakeWord(root, clock);wake.runtime=True;wake.enabled=True
            child=Mock();child.poll.return_value=None;wake.process=child
            d=AudioDiagnostics();trigger=Mock()
            with patch('services.wake_word.select.select',return_value=([True],[],[])):
                for i in range(30):
                    d.feed(bytes(1600),'other_speech')
                    child.stdout=io.BytesIO(('diagnostic '+json.dumps(d.snapshot())+'\n').encode())
                    wake.tick(account=None,reason='',config={'device':'test'},trigger=trigger)
            self.assertEqual(len(wake.public()['diagnostics']['recent_decisions']),16)
            self.assertEqual(wake.public()['diagnostics']['latest']['speech_segments'],30)
            self.assertEqual(wake.count,0);trigger.assert_not_called()
            wake.process=None

    def test_diagnostic_messages_cannot_hide_missing_ready_or_alive(self):
        with tempfile.TemporaryDirectory() as root:
            clock=Mock(return_value=100);wake=WakeWord(root,clock)
            wake.runtime=True;wake.enabled=True;wake.mode='listening'
            child=Mock();child.poll.return_value=None;wake.process=child
            d=AudioDiagnostics();d.feed(bytes(1600),None)
            line=('diagnostic '+json.dumps(d.snapshot())+'\n').encode()
            child.stdout=io.BytesIO(line)
            with patch('services.wake_word.select.select',return_value=([True],[],[])),patch('services.wake_word.os.killpg'):
                wake.tick(account=None,reason='',config={'device':'test'},trigger=Mock())
                clock.return_value=116;child.stdout=io.BytesIO(line)
                wake.tick(account=None,reason='',config={'device':'test'},trigger=Mock())
            self.assertEqual(wake.mode,'error')
            self.assertIsNone(wake.process)

    def test_categories_do_not_change_rejection_thresholds(self):
        import sys
        from types import SimpleNamespace
        from services.wake_phrase import PhraseDetector
        result={'text':'hey brain','result':[{'word':'hey','conf':1,'start':0,'end':.3},
                                            {'word':'brain','conf':.89,'start':.3,'end':.8}]}
        decoder=Mock();decoder.AcceptWaveform.return_value=True
        decoder.Result.return_value=json.dumps(result)
        fake=SimpleNamespace(Model=Mock(),SetLogLevel=Mock(),KaldiRecognizer=Mock(return_value=decoder))
        with patch.dict(sys.modules,{'vosk':fake}):
            d=PhraseDetector();self.assertFalse(d.feed(bytes(1600)))
            self.assertEqual(d.last_decision,'candidate_rejected')
            result['result'][1]['conf']=1;decoder.Result.return_value=json.dumps(result)
            self.assertTrue(d.feed(bytes(1600)));self.assertEqual(d.last_decision,'accepted')
            decoder.AcceptWaveform.return_value=False
            self.assertFalse(d.feed(bytes(1600)));self.assertIsNone(d.last_decision)


if __name__=='__main__':unittest.main()
