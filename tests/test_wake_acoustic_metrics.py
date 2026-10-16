import unittest
import numpy as np
from scripts.wake_acoustic_metrics import alignment, split_stereo

class AcousticMetricTests(unittest.TestCase):
    def test_stereo_keeps_channels_separate_without_overflow(self):
        pcm=np.tile(np.array([32767,-32768],dtype='<i2'),800).tobytes()
        mixed,left,right=split_stereo(pcm)
        self.assertTrue(np.all(np.frombuffer(mixed,dtype='<i2')==0))
        self.assertTrue(np.all(np.frombuffer(left,dtype='<i2')==32767))
        self.assertTrue(np.all(np.frombuffer(right,dtype='<i2')==-32768))
        with self.assertRaises(ValueError): split_stereo(pcm[:-2])
    def test_delayed_attenuated_reference_matches(self):
        rng=np.random.default_rng(7)
        ref=rng.integers(-20000,20000,16000,dtype=np.int16)
        got=np.concatenate((np.zeros(4000,dtype=np.int16),(ref*.25).astype(np.int16),np.zeros(4000,dtype=np.int16)))
        result=alignment(ref.tobytes(),got.tobytes())
        self.assertGreater(result['correlation'],.999)
        self.assertEqual(result['lag_seconds'],.25)
    def test_unrelated_sound_is_not_signal_evidence(self):
        rng=np.random.default_rng(9)
        ref=rng.integers(-20000,20000,16000,dtype=np.int16)
        got=rng.integers(-20000,20000,32000,dtype=np.int16)
        self.assertLess(alignment(ref.tobytes(),got.tobytes())['correlation'],.05)
    def test_silence_and_truncated_reference_are_not_matches(self):
        self.assertIsNone(alignment(bytes(32000),bytes(64000))['correlation'])
        self.assertIsNone(alignment(bytes(32000),bytes(200))['correlation'])
