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

    def test_model_peak_is_bounded_windowed_and_does_not_imply_detection(self):
        d=AudioDiagnostics()
        d.feed(bytes(1600),None,probability=.6,cutoff=.85)
        d.feed(bytes(1600),None,probability=.2,cutoff=.85)
        value=d.snapshot()
        self.assertEqual(value['model_peak'],.6)
        self.assertEqual(value['model_cutoff'],.85)
        self.assertEqual(value['accepted'],0)
        self.assertEqual(validate(value),value)
        self.assertNotIn('model_peak',d.snapshot())
        for change in [{'model_peak':True},{'model_peak':float('nan')},
                       {'model_cutoff':-1},{'model_cutoff':None}]:
            self.assertIsNone(validate({**value,**change}))
        for invalid in [True,float('inf'),-.1,1.1]:
            with self.assertRaises(ValueError):d.feed(bytes(1600),None,probability=invalid,cutoff=.85)

    def test_missed_nabu_scores_retained_without_cloud_or_heartbeat_side_effects(self):
        with tempfile.TemporaryDirectory() as root,patch('services.wake_word.runtime_ready',return_value=True):
            wake=WakeWord(root,lambda:100);wake.enabled=True;wake.mode='listening'
            child=Mock();child.poll.return_value=None;wake.process=child
            d=AudioDiagnostics();trigger=Mock()
            with patch('services.wake_word.select.select',return_value=([True],[],[])):
                for _ in range(20):
                    d.feed(bytes(1600),None,probability=.4,cutoff=.85)
                    child.stdout=io.BytesIO(('diagnostic '+json.dumps(d.snapshot())+'\n').encode())
                    wake.tick(account=None,reason='',config={'device':'test'},trigger=trigger)
            recent=wake.public()['diagnostics']['recent_decisions']
            self.assertEqual(len(recent),16)
            self.assertEqual(recent[-1]['model_peak'],.4)
            self.assertEqual(wake.count,0);trigger.assert_not_called()
            wake.process=None

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
