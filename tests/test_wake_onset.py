from array import array
import unittest
from services.wake_phrase import LowNoiseOnset


def block(level):
    return array('h', [level, -level] * 400).tobytes()


class OnsetTests(unittest.TestCase):
    def test_low_nonzero_floor_renews_once_and_preserves_preceding_pcm(self):
        onset=LowNoiseOnset();quiet=block(4);speech=block(1200)
        for _ in range(40):self.assertIsNone(onset.feed(quiet))
        self.assertEqual(onset.feed(speech),[quiet]*4)
        self.assertEqual(onset.renewals,1)
        for _ in range(20):self.assertIsNone(onset.feed(speech))
        self.assertEqual(onset.renewals,1)

    def test_digital_silence_keeps_very_quiet_speech_unchanged(self):
        onset=LowNoiseOnset()
        for _ in range(100):self.assertIsNone(onset.feed(bytes(1600)))
        for _ in range(10):self.assertIsNone(onset.feed(block(2)))
        self.assertEqual(onset.renewals,0)

    def test_short_pause_inside_phrase_does_not_reset(self):
        onset=LowNoiseOnset()
        for _ in range(40):onset.feed(block(4))
        onset.feed(block(1200))
        for _ in range(30):onset.feed(block(4))
        self.assertIsNone(onset.feed(block(1200)))
        self.assertEqual(onset.renewals,1)

    def test_louder_background_and_interrupted_quiet_never_arm(self):
        for sequence in ([block(64)]*100, [block(4)]*39+[block(100)]+[block(4)]*39):
            onset=LowNoiseOnset()
            for pcm in sequence:self.assertIsNone(onset.feed(pcm))
            self.assertIsNone(onset.feed(block(1000)))
            self.assertEqual(onset.renewals,0)

    def test_buffers_are_bounded_and_other_chunk_sizes_do_not_shorten_quiet(self):
        onset=LowNoiseOnset()
        for _ in range(1000):onset.feed(block(4))
        self.assertEqual(len(onset.pre),4);self.assertEqual(len(onset.quiet),40)
        self.assertIsNone(onset.feed(b'odd'))
        self.assertIsNone(onset.feed(block(1200)))
        self.assertEqual(onset.renewals,0)


if __name__=='__main__':unittest.main()
