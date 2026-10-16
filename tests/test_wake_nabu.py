import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from services.wake_detectors import NabuDetector, create_detector, runtime_ready
from services.wake_word import WakeWord


class NabuTests(unittest.TestCase):
    def test_all_subframes_processed_and_acceptance_is_per_input_block(self):
        features=Mock();features.process_streaming.side_effect=lambda pcm: [pcm]
        model=Mock();model.probability_cutoff=.85
        model.process_streaming_prob.side_effect=[0.,.9,.95,.85,None]+[0.]*5
        factory=Mock(return_value=model)
        module=SimpleNamespace(MicroWakeWord=SimpleNamespace(from_builtin=factory),
            MicroWakeWordFeatures=Mock(return_value=features),Model=SimpleNamespace(OKAY_NABU='nabu-model'))
        with patch.dict(sys.modules,{'pymicro_wakeword':module}):
            detector=NabuDetector()
            pcm=b''.join(bytes([i])*320 for i in range(5))
            self.assertTrue(detector.feed(pcm));self.assertEqual(detector.last_decision,'accepted')
            self.assertEqual(detector.last_probability,.95)
            self.assertEqual([c.args[0] for c in features.process_streaming.call_args_list],
                             [bytes([i])*320 for i in range(5)])
            self.assertFalse(detector.feed(bytes(1600)));self.assertIsNone(detector.last_decision)
            self.assertEqual(model.process_streaming_prob.call_count,10)
            factory.assert_called_once_with('nabu-model')
            with self.assertRaises(ValueError):detector.feed(bytes(320))

    def test_probability_diagnostics_preserve_strict_upstream_threshold(self):
        features=Mock();features.process_streaming.side_effect=lambda pcm:[pcm]
        model=Mock();model.probability_cutoff=.85
        module=SimpleNamespace(MicroWakeWord=SimpleNamespace(from_builtin=Mock(return_value=model)),
            MicroWakeWordFeatures=Mock(return_value=features),Model=SimpleNamespace(OKAY_NABU='nabu'))
        with patch.dict(sys.modules,{'pymicro_wakeword':module}):
            d=NabuDetector()
            for probability,expected in [(None,False),(0.,False),(.85,False),(.850001,True),(1.,True)]:
                model.process_streaming_prob.side_effect=None
                model.process_streaming_prob.return_value=probability
                self.assertEqual(d.feed(bytes(1600)),expected)
                self.assertEqual(d.last_probability,probability)
            for invalid in [float('nan'),float('inf'),-0.1,1.1]:
                model.process_streaming_prob.return_value=invalid
                with self.assertRaises(ValueError):d.feed(bytes(1600))

    def test_nabu_cannot_silently_use_vosk(self):
        with patch('services.wake_detectors.NabuDetector',side_effect=ImportError('missing')), \
             patch('services.wake_detectors.wake_phrase.PhraseDetector') as vosk:
            with self.assertRaises(ImportError):create_detector('okay-nabu')
            vosk.assert_not_called()
        with self.assertRaises(ValueError):create_detector('nabu')

    def test_runtime_depends_on_selected_engine(self):
        with patch('services.wake_detectors.importlib.util.find_spec',side_effect=lambda name: object() if name.startswith('pymicro') else None), \
             patch('services.wake_detectors.wake_phrase.model_ready',return_value=False):
            self.assertTrue(runtime_ready('okay-nabu'))
            self.assertFalse(runtime_ready('hey-brain'))
        with patch('services.wake_detectors.importlib.util.find_spec',return_value=None):
            self.assertFalse(runtime_ready('okay-nabu'))

    def test_existing_accounts_are_not_migrated_and_selected_nabu_survives_restart(self):
        with tempfile.TemporaryDirectory() as root,patch('services.wake_word.runtime_ready',return_value=True):
            path=Path(root)/'wake-word.json'
            path.write_text(json.dumps({'enabled':True,'account':{'user_id':'a'},'phrase':'hey-kai'}))
            wake=WakeWord(root);self.assertEqual(wake.phrase,'hey-kai')
            with self.assertRaises(ValueError):wake.select_phrase('okay-nabu')
            wake.configure(False,None);wake.select_phrase('okay-nabu');wake.configure(True,{'user_id':'a'})
            restored=WakeWord(root)
            self.assertEqual(restored.public()['word'],'Okay Nabu');self.assertTrue(restored.enabled)
            self.assertEqual(restored.account,{'user_id':'a'})
            self.assertIn('okay-nabu',[p['id'] for p in restored.public()['phrases']])

    def test_missing_nabu_runtime_blocks_enable_after_selection(self):
        with tempfile.TemporaryDirectory() as root,patch('services.wake_word.runtime_ready',return_value=False):
            wake=WakeWord(root);wake.select_phrase('okay-nabu')
            with self.assertRaises(ValueError):wake.configure(True,{'user_id':'a'})
            self.assertFalse(wake.enabled)

    def test_nabu_uses_existing_record_and_live_reservation(self):
        with tempfile.TemporaryDirectory() as root,patch('services.wake_word.runtime_ready',return_value=True):
            wake=WakeWord(root);wake.select_phrase('okay-nabu');wake.configure(True,{'user_id':'a'})
            with patch('services.wake_word.subprocess.Popen') as spawn:
                for reason in ['Aufnahme läuft.','Aufnahme pausiert.','Live-Gespräch läuft.','Audiowiedergabe läuft.']:
                    wake.tick(account={'user_id':'a'},reason=reason,config={'device':'test'},trigger=Mock())
                    self.assertEqual(wake.mode,'waiting')
                spawn.assert_not_called()

    def test_image_and_ui_include_explicit_nabu_support(self):
        root=Path(__file__).resolve().parents[1]
        self.assertIn('value="okay-nabu">Okay Nabu', (root/'studio/index.html').read_text())
        self.assertIn('-r requirements-wake.txt',(root/'deploy/customer-image/01-run-chroot.sh').read_text())
        for pin in ['pymicro-wakeword==2.5.0','pymicro-features==2.0.2']:
            self.assertIn(pin,(root/'requirements-wake.txt').read_text())
