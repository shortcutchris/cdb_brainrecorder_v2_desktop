import io
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import wave

from meeting_recorder.processing import Interrupted
from services.queued_whisper import QueuedWhisper


class QueuedWhisperTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.worker = QueuedWhisper(threading.Event())
        self.cli = self.folder / 'fake-cli'
        self.model = self.folder / 'model.bin'
        self.model.touch()
        self.config = dict(whisper_binary=str(self.cli), whisper_model=str(self.model),
                           threads=3, process_timeout=8)
        with wave.open(str(self.folder / 'audio.wav'), 'wb') as audio:
            audio.setparams((1, 2, 16000, 0, 'NONE', 'none'))
            audio.writeframes(bytes(16000 * 2 * 8))

    def script(self, body):
        self.cli.write_text(f'#!{sys.executable}\n' + body)
        self.cli.chmod(0o700)

    def test_native_progress_while_worker_runs(self):
        self.script("""import sys, time
from pathlib import Path
assert '--print-progress' in sys.argv
print('whisper_print_progress_callback: progress =  25%', file=sys.stderr, flush=True)
prefix = Path(sys.argv[sys.argv.index('-of')+1])
while not prefix.with_suffix('.release').exists():
    time.sleep(.02)
prefix.with_suffix('.txt').write_text('Beispiel')
""")
        result = []
        thread = threading.Thread(target=lambda: result.append(self.worker.transcribe(self.folder, self.config)))
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                status = self.worker.progress_for(self.folder.name)
                if status and status['percent'] is not None:
                    break
                time.sleep(.02)
            self.assertIsNotNone(status)
            self.assertEqual((status['percent'], status['duration_seconds']), (25, 8))
            self.assertGreaterEqual(status['remaining_seconds'], 0)
            self.assertIsNone(self.worker.progress_for('other-job'))
        finally:
            (self.folder/'whisper-output.release').touch()
            thread.join(6)
        self.assertEqual(result, ['Beispiel'])
        self.assertIsNone(self.worker.progress_for(self.folder.name))

    def test_estimate_uses_only_forward_native_reports(self):
        self.worker._progress = dict(percent=None, remaining_seconds=None)
        diagnostics = (b'ordinary output 60%\nwhisper_print_progress_callback: progress =  25%\n'
                       b'whisper_print_progress_callback: progress =  10%\n'
                       b'whisper_print_progress_callback: progress = 110%\n')
        with patch('services.queued_whisper.time.monotonic', return_value=110):
            self.worker._read_diagnostics(io.BytesIO(diagnostics), io.BytesIO(), started=100)
        self.assertEqual(self.worker._progress, dict(percent=25, remaining_seconds=30))

    def test_failed_retry_clears_progress_and_old_text(self):
        self.script("import sys\nprint('whisper_print_progress_callback: progress = 100%', file=sys.stderr)\nsys.exit(2)")
        (self.folder/'whisper-output.txt').write_text('Alt')
        with self.assertRaisesRegex(RuntimeError, 'Code 2'):
            self.worker.transcribe(self.folder, self.config)
        self.assertIsNone(self.worker.progress_for(self.folder.name))
        self.assertFalse((self.folder/'whisper-output.txt').exists())

    def test_silent_cli_still_honours_stop_and_timeout(self):
        self.script('import time\ntime.sleep(30)')
        for stopped, error in ((False, RuntimeError), (True, Interrupted)):
            if stopped:
                self.worker.stopping.set()
            with self.assertRaises(error):
                self.worker.transcribe(self.folder, self.config | {'process_timeout': 0.1})
            self.assertIsNone(self.worker.progress_for(self.folder.name))
