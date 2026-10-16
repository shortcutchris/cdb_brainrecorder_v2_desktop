import json
import unittest

from scripts.check_wake_acoustic import probe_vosk_pcm


class AcousticVerifierTests(unittest.TestCase):
    def test_only_exact_approved_phrase_counts_and_room_text_is_not_returned(self):
        class Decoder:
            def __init__(self, *args): self.calls = 0
            def AcceptWaveform(self, audio):
                self.calls += 1
                return self.calls == 1
            def Result(self): return json.dumps({'text': 'private room sentence'})
            def FinalResult(self): return json.dumps({'text': 'okay naboo'})
        result = probe_vosk_pcm(None, ['okay naboo', '[unk]'], ['okay naboo'], bytes(3200), Decoder)
        self.assertTrue(result['detected'])
        self.assertEqual(result['accepted_segments'], 1)
        self.assertEqual(result['nonempty_segments'], 2)
        self.assertFalse(result['transcript_saved'])
        self.assertNotIn('private', json.dumps(result))
        self.assertNotIn('naboo', json.dumps(result))

    def test_partial_match_is_not_an_activation(self):
        class Decoder:
            def __init__(self, *args): pass
            def AcceptWaveform(self, audio): return False
            def FinalResult(self): return json.dumps({'text': 'okay naboo later'})
        result = probe_vosk_pcm(None, ['okay naboo'], ['okay naboo'], bytes(1600), Decoder)
        self.assertFalse(result['detected'])


if __name__ == '__main__':
    unittest.main()
