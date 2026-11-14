"""Local Whisper adapter for Studio's queue. Only numeric progress reaches the UI."""
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
import wave

from meeting_recorder.child_process import owned_command
from meeting_recorder.processing import Interrupted, LocalModels


PROGRESS = re.compile(rb'whisper_print_progress_callback: progress =\s*(\d{1,3})%')


class QueuedWhisper(LocalModels):
    def __init__(self, stopping):
        super().__init__(stopping)
        self._lock = threading.Lock()
        self._job = None
        self._progress = {}

    def progress_for(self, job_id):
        with self._lock:
            return self._progress.copy() if self._job == job_id else None

    def _read_diagnostics(self, stream, log, started):
        for line in stream:
            log.write(line)
            match = PROGRESS.fullmatch(line.strip())
            if match is None:
                continue
            percent = int(match[1])
            with self._lock:
                previous = self._progress['percent'] or 0
                if not previous < percent <= 100:
                    continue
                elapsed = time.monotonic() - started
                self._progress.update(percent=percent,
                                      remaining_seconds=round(elapsed * (100 - percent) / percent))

    def transcribe(self, folder, config):
        binary, model = Path(config['whisper_binary']), Path(config['whisper_model'])
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise RuntimeError('whisper-cli fehlt oder ist nicht ausführbar. Installation/Einstellungen prüfen.')
        if not model.is_file():
            raise RuntimeError('Whisper-Modell fehlt. Modell herunterladen und Pfad in Einstellungen prüfen.')
        audio = folder / 'audio.wav'
        try:
            with wave.open(str(audio), 'rb') as wav:
                duration = wav.getnframes() / wav.getframerate()
        except (OSError, EOFError, wave.Error):
            duration = None  # A format readable by the CLI may have an unfamiliar WAV header.
        prefix = folder / 'whisper-output'
        output = prefix.with_suffix('.txt')
        output.unlink(missing_ok=True)
        command = [str(binary), '-m', str(model), '-f', str(audio), '-l', 'de',
                   '-t', str(config['threads']), '-otxt', '-of', str(prefix), '-nt', '--print-progress']
        with self._lock:
            self._job = folder.name
            self._progress = dict(duration_seconds=duration, percent=None, remaining_seconds=None)
        try:
            self._run(command, folder, config['process_timeout'])
        finally:
            with self._lock:
                self._job = None
                self._progress = {}
        if not output.exists():
            raise RuntimeError('Whisper hat keine Textdatei erzeugt.')
        return output.read_text(encoding='utf-8').strip()

    def _run(self, command, folder, timeout):
        started = time.monotonic()
        peak_kib = 0
        with (folder / 'processing.log').open('ab', buffering=0) as log:
            with subprocess.Popen(owned_command(command), stdout=log, stderr=subprocess.PIPE,
                                  start_new_session=True) as proc:
                reader = threading.Thread(target=self._read_diagnostics, args=(proc.stderr, log, started))
                reader.start()
                try:
                    while proc.poll() is None:
                        try:
                            for line in Path(f'/proc/{proc.pid}/status').read_text().splitlines():
                                if line.startswith('VmRSS:'):
                                    peak_kib = max(peak_kib, int(line.split()[1]))
                                    break
                        except (OSError, ValueError):
                            pass
                        if self.stopping.wait(.25):
                            raise Interrupted()
                        if time.monotonic() - started > timeout:
                            raise RuntimeError('Transkriptions-Zeitlimit erreicht. Einstellungen oder Modell prüfen.')
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait()
                    reader.join()
                if proc.returncode:
                    raise RuntimeError(f'whisper-cli beendet mit Code {proc.returncode}. processing.log prüfen.')
        self.last_asr_peak_mib = round(peak_kib / 1024, 1) if peak_kib else None
