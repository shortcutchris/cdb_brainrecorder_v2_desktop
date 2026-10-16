import os
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

from scripts.wake_streaming_probe import StreamingCandidate, AsyncVerifier
from scripts.wake_whisper_probe import matches_nabu, matches_nabu_joined


class Detector:
    last_probability = 0.
    def feed(self, pcm): return self.last_probability > .85


class Verifier:
    def __init__(self): self.windows = []; self.result = None; self.closed = False
    def submit(self, pcm): self.windows.append(pcm)
    def poll(self):
        result, self.result = self.result, None
        return result
    def close(self): self.closed = True


class StreamingCandidateTests(unittest.TestCase):
    def make(self):
        detector, verifier = Detector(), Verifier()
        return detector, verifier, StreamingCandidate(detector, verifier)

    def tick(self, stream, count):
        return [stream.feed(bytes(1600)) for _ in range(count)]

    def test_primary_high_score_never_bypasses_verification(self):
        detector, verifier, stream = self.make()
        self.tick(stream, 60)
        detector.last_probability = .99
        self.assertFalse(any(self.tick(stream, 100)))
        self.assertEqual(len(verifier.windows), 1)
        self.assertEqual(len(verifier.windows[0]), 56*1600)
        verifier.result = {'detected': False}
        self.assertFalse(stream.feed(bytes(1600)))
        self.assertEqual(stream.last_decision, 'candidate_rejected')
        self.tick(stream, 100)
        self.assertEqual(len(verifier.windows), 1)
        self.assertLessEqual(len(stream.ring), 96)

    def test_100_acceptances_latch_once_and_close_releases_each_owner(self):
        for _ in range(100):
            detector, verifier, stream = self.make()
            detector.last_probability = .2
            self.assertFalse(any(self.tick(stream, 17)))
            verifier.result = {'detected': True}
            self.assertTrue(stream.feed(bytes(1600)))
            self.assertFalse(any(self.tick(stream, 10)))
            self.assertEqual(len(verifier.windows), 1)
            stream.close()
            self.assertTrue(verifier.closed)
            self.assertEqual(len(stream.ring), 0)
            with self.assertRaises(RuntimeError): stream.feed(bytes(1600))

    def test_rejection_requires_score_decay_and_spacing_before_retry(self):
        detector, verifier, stream = self.make()
        detector.last_probability = .2
        self.tick(stream, 17)
        verifier.result = {'detected': False, 'error': 'timeout'}
        self.tick(stream, 1)
        detector.last_probability = 0.
        self.tick(stream, 10)
        self.assertEqual(stream.state, 'cooldown')
        self.tick(stream, 40)
        self.assertEqual(stream.state, 'ready')
        detector.last_probability = .2
        self.tick(stream, 17)
        self.assertEqual(len(verifier.windows), 2)

    def test_cancel_during_tail_or_verification_discards_pcm_and_no_result_can_fire(self):
        for frames in [1, 17]:
            detector, verifier, stream = self.make()
            detector.last_probability = .2
            self.tick(stream, frames)
            stream.close()
            verifier.result = {'detected': True}
            self.assertTrue(verifier.closed)
            with self.assertRaises(RuntimeError): stream.feed(bytes(1600))


class AsyncVerifierTests(unittest.TestCase):
    def exercise(self, body, check, matcher=matches_nabu):
        # Real isolated child process; fake memfd contains only synthetic zeros.
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as pcm:
            binary = Path(directory)/'fake-whisper'
            binary.write_text(f'#!{sys.executable}\nimport sys,time\n'+body)
            binary.chmod(0o700)
            descriptor = os.dup(pcm.fileno())
            verifier = AsyncVerifier(binary, '/unused-synthetic-model', matcher=matcher)
            with patch('os.memfd_create', return_value=descriptor, create=True), \
                    patch('os.MFD_CLOEXEC', 1, create=True):
                try:
                    verifier.submit(bytes(1600))
                    child = verifier.process
                    check(verifier)
                finally:
                    verifier.close()
            self.assertIsNotNone(child.poll())
            with self.assertRaises(OSError): os.fstat(descriptor)

    def result(self, verifier):
        deadline = time.monotonic()+3
        while time.monotonic() < deadline:
            result = verifier.poll()
            if result is not None: return result
            time.sleep(.01)
        self.fail('Native test child did not finish')

    def test_real_partial_output_is_nonblocking_and_timeout_is_fail_closed(self):
        def check(verifier):
            deadline = time.monotonic()+2
            while not verifier.output and time.monotonic() < deadline:
                start = time.monotonic()
                self.assertIsNone(verifier.poll())
                self.assertLess(time.monotonic()-start, .2)
                time.sleep(.01)
            self.assertTrue(verifier.output)
            verifier.clock = lambda: verifier.started+4
            report = verifier.poll()
            self.assertFalse(report['detected'])
            self.assertEqual(report['error'], 'timeout')
            self.assertIsNone(verifier.process)
        self.exercise("sys.stdout.write('Okay Na');sys.stdout.flush();time.sleep(30)\n", check)

    def test_nonzero_exit_never_accepts_even_with_matching_text(self):
        def check(verifier):
            report = self.result(verifier)
            self.assertEqual(report['returncode'], 2)
            self.assertFalse(report['detected'])
        self.exercise("print('Okay Nabu.');sys.exit(2)\n", check)

    def test_positive_process_result_accepts_only_after_process_is_reaped(self):
        def check(verifier):
            report = self.result(verifier)
            self.assertTrue(report['detected'])
            self.assertIsNone(verifier.process)
            self.assertIsNone(verifier.descriptor)
        self.exercise("print('Okay Nabu.')\n", check)

    def test_joined_rule_is_opt_in_and_native_failure_still_rejects(self):
        for matcher, code, expected in [(matches_nabu, 0, False),
                                         (matches_nabu_joined, 0, True),
                                         (matches_nabu_joined, 2, False)]:
            def check(verifier):
                report = self.result(verifier)
                self.assertEqual(report['detected'], expected)
                self.assertIsNone(verifier.process)
                self.assertIsNone(verifier.descriptor)
            self.exercise(f"print('Oknabu.');sys.exit({code})\n", check, matcher)

    def test_failed_termination_keeps_ownership_and_prevents_second_child(self):
        verifier = AsyncVerifier('/unused', '/unused')
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('child', .5)
        verifier.process = child
        with self.assertRaises(subprocess.TimeoutExpired): verifier.cancel()
        self.assertIs(verifier.process, child)
        with self.assertRaises(RuntimeError): verifier.submit(bytes(1600))
        child.poll.return_value = 0
        child.wait.side_effect = None
        verifier.close()
        self.assertIsNone(verifier.process)

    def test_output_is_capped_and_process_reaped(self):
        def check(verifier):
            report = self.result(verifier)
            self.assertEqual(report['error'], 'output_limit')
            self.assertFalse(report['detected'])
            self.assertEqual(len(verifier.output), 0)
        self.exercise("print('x'*20000)\n", check)


if __name__ == '__main__': unittest.main()
