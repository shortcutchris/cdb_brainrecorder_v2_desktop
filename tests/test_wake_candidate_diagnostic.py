import json
import unittest
from unittest.mock import Mock, patch

from scripts.diagnose_wake_candidate import candidate_metrics, main
from services.wake_phrase import is_activation


class CandidateDiagnosticTests(unittest.TestCase):
    def result(self, first=1, second=1, duration=.8):
        return {'text': 'okay kai', 'result': [
            {'word': 'okay', 'conf': first, 'start': 0},
            {'word': 'kai', 'conf': second, 'end': duration}]}

    def test_reasons_agree_with_actual_detector_boundaries(self):
        for first, second, duration, reasons in [
            (.8, .9, .25, []), (1, 1, 2.5, []),
            (.79, 1, .8, ['first_word_confidence']),
            (1, .89, .8, ['second_word_confidence']),
            (1, 1, 2.51, ['duration']),
            (.7, .8, .1, ['first_word_confidence', 'second_word_confidence', 'duration'])]:
            with self.subTest(first=first, second=second, duration=duration):
                result = self.result(first, second, duration)
                self.assertEqual(candidate_metrics(result, 'okay-kai')[0]['reasons'], reasons)
                self.assertEqual(is_activation(result, 'okay-kai'), not reasons)

    def test_text_is_not_exported_and_results_are_bounded(self):
        result = self.result(); result['text'] = 'private room speech'
        result['result'] *= 20
        rows = candidate_metrics(result, 'okay-kai')
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]['reasons'], ['text_mismatch'])
        self.assertNotIn('private', json.dumps(rows))
        self.assertEqual(candidate_metrics(result, 'hey-brain'), [])
        result = self.result(second=float('nan'))
        self.assertEqual(candidate_metrics(result, 'okay-kai')[0]['reasons'], ['invalid_numeric_result'])

    def test_diagnostic_uses_selected_phrase_threshold(self):
        result = self.result(second=.525806)
        result['text'] = 'hey kai'; result['result'][0]['word'] = 'hey'
        self.assertEqual(candidate_metrics(result, 'hey-kai')[0]['reasons'], [])
        result['result'][1]['conf'] = .4999
        self.assertEqual(candidate_metrics(result, 'hey-kai')[0]['reasons'], ['second_word_confidence'])

    def test_capture_failure_releases_lease_and_restores_detector(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.side_effect = [b'{}', b'{"diagnostics":{"capture_running":false}}',
                                     b'{"config":{"device":"test"}}', b'{}']
        capture = Mock(); capture.stdout.read.return_value = b''
        capture.poll.return_value = None
        with patch('sys.argv', ['diagnose', '--phrase', 'okay-kai']), \
             patch('pathlib.Path.read_text', return_value='{"token":"test"}'), \
             patch('urllib.request.urlopen', return_value=response) as request, \
             patch('scripts.diagnose_wake_candidate.wake_phrase.PhraseDetector'), \
             patch('scripts.diagnose_wake_candidate.native_capture_command', return_value=['capture']), \
             patch('subprocess.Popen', return_value=capture), \
             patch('select.select', return_value=([True], [], [])), \
             patch('os.killpg') as kill:
            with self.assertRaisesRegex(RuntimeError, 'capture ended'): main()
        self.assertTrue(request.call_args.args[0].full_url.endswith('/release'))
        kill.assert_called_once(); capture.wait.assert_called_once(); capture.stdout.close.assert_called_once()
        from services import wake_phrase
        self.assertIs(wake_phrase.is_activation, is_activation)

    def test_busy_device_never_opens_microphone(self):
        with patch('sys.argv', ['diagnose', '--phrase', 'okay-kai']), \
             patch('pathlib.Path.read_text', return_value='{"token":"test"}'), \
             patch('urllib.request.urlopen', side_effect=RuntimeError('busy')), \
             patch('subprocess.Popen') as capture:
            with self.assertRaisesRegex(RuntimeError, 'busy'): main()
        capture.assert_not_called()

    def test_retained_production_capture_prevents_second_microphone_owner(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.side_effect = [b'{}', b'{"diagnostics":{"capture_running":true}}', b'{}']
        with patch('sys.argv', ['diagnose', '--phrase', 'okay-kai']), \
             patch('pathlib.Path.read_text', return_value='{"token":"test"}'), \
             patch('urllib.request.urlopen', return_value=response) as request, \
             patch('scripts.diagnose_wake_candidate.wake_phrase.PhraseDetector') as detector, \
             patch('subprocess.Popen') as capture:
            with self.assertRaisesRegex(RuntimeError, 'did not stop'): main()
        detector.assert_not_called()
        capture.assert_not_called()
        self.assertTrue(request.call_args.args[0].full_url.endswith('/release'))

    def test_missing_capture_status_fails_closed_before_microphone_open(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.side_effect = [b'{}', b'{}', b'{}']
        with patch('sys.argv', ['diagnose', '--phrase', 'okay-kai']), \
             patch('pathlib.Path.read_text', return_value='{"token":"test"}'), \
             patch('urllib.request.urlopen', return_value=response) as request, \
             patch('subprocess.Popen') as capture:
            with self.assertRaises(KeyError): main()
        capture.assert_not_called()
        self.assertTrue(request.call_args.args[0].full_url.endswith('/release'))


if __name__ == '__main__': unittest.main()
