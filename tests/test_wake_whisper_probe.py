import json
import os
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts.wake_whisper_probe import matches_nabu, probe_whisper_pcm


class WhisperProbeTests(unittest.TestCase):
    def test_whole_words_only_and_no_fuzzy_matching(self):
        for text in ['Okay Nabu.', 'OK, NABU! Wie spät ist es?']:
            self.assertTrue(matches_nabu(text))
        for text in ['Okay, na gut.', 'Okay Nabum.', 'Okay, nable', 'Sag bitte Okay Nabu.', '', 'Nabu.']:
            self.assertFalse(matches_nabu(text))

    def test_anonymous_descriptor_closes_and_no_decoded_text_leaves_probe(self):
        # Fake memfd uses only synthetic zeros; the actual Pi run must use memfd_create.
        with tempfile.TemporaryFile() as synthetic:
            descriptor = os.dup(synthetic.fileno())
            def run(command, **kwargs):
                self.assertIn(f'/proc/self/fd/{descriptor}', command)
                self.assertEqual(kwargs['pass_fds'], (descriptor,))
                return SimpleNamespace(returncode=0, stdout='Okay Nabu. private test words')
            with patch('os.memfd_create', return_value=descriptor, create=True), \
                    patch('os.MFD_CLOEXEC', 1, create=True), \
                    patch('subprocess.run', side_effect=run):
                report = probe_whisper_pcm(bytes(160000), '/lab/whisper', '/lab/model')
            self.assertTrue(report['detected'])
            self.assertTrue(report['truncated'])
            self.assertEqual(report['audio_seconds'], 4.8)
            self.assertNotIn('private', json.dumps(report))
            with self.assertRaises(OSError): os.fstat(descriptor)

    def test_timeout_rejects_and_closes_descriptor(self):
        with tempfile.TemporaryFile() as synthetic:
            descriptor = os.dup(synthetic.fileno())
            with patch('os.memfd_create', return_value=descriptor, create=True), \
                    patch('os.MFD_CLOEXEC', 1, create=True), \
                    patch('subprocess.run', side_effect=subprocess.TimeoutExpired('lab-whisper', 10)):
                report = probe_whisper_pcm(bytes(1600), '/lab/whisper', '/lab/model')
            self.assertFalse(report['detected'])
            self.assertEqual(report['error'], 'timeout')
            with self.assertRaises(OSError): os.fstat(descriptor)


if __name__ == '__main__':
    unittest.main()
