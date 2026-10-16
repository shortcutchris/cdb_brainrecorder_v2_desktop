import json
from pathlib import Path
import tempfile
import unittest
import wave

from scripts.benchmark_vosk_wake import load_cases, validate_grammar


class VoskBenchmarkTests(unittest.TestCase):
    def test_oov_must_not_silently_drop_nabu(self):
        class Model:
            def vosk_model_find_word(self, word):
                return -1 if word == 'nabu' else 1
        with self.assertRaisesRegex(ValueError, 'nabu'):
            validate_grammar(Model(), ['okay nabu', '[unk]'], ['okay nabu'])
        validate_grammar(Model(), ['okay naboo', '[unk]'], ['okay naboo'])
        with self.assertRaises(ValueError):
            validate_grammar(Model(), ['okay naboo'], ['okay nabu'])

    def test_only_declared_bounded_synthetic_pcm_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with wave.open(str(root/'clip.wav'), 'wb') as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                audio.writeframes(bytes(3200))
            data = dict(synthetic_files_only=True,
                        cases=[dict(file='clip.wav', label='known-synthetic', expected=False)])
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps(data))
            self.assertEqual(load_cases(manifest), [('known-synthetic', False, bytes(3200))])
            data['cases'][0]['expected'] = 'false'
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_cases(manifest)
            data['synthetic_files_only'] = False
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_cases(manifest)
            data['synthetic_files_only'] = True
            data['cases'][0]['expected'] = False
            manifest.write_text(json.dumps(data))
            for rate, frames in [(8000, 800), (16000, 16000 * 60 + 1)]:
                with wave.open(str(root/'clip.wav'), 'wb') as audio:
                    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(rate)
                    audio.writeframes(bytes(frames * 2))
                with self.assertRaises(ValueError): load_cases(manifest)


if __name__ == '__main__':
    unittest.main()
