"""Unreleased wake experiment: bounded streaming candidate + asynchronous verifier.

No microphone, settings, model download or Live connection is owned here. A caller
supplies 50-ms PCM blocks. This module is deliberately outside the app allowlist.
"""
from collections import deque
import os
import select
import subprocess
import time
import wave

from meeting_recorder.child_process import owned_command
try:
    from .wake_whisper_probe import matches_nabu
except ImportError:
    from wake_whisper_probe import matches_nabu


class AsyncVerifier:
    """One owned native process, bounded output, anonymous RAM input, no threads."""
    def __init__(self, binary, model, clock=time.monotonic):
        self.binary, self.model, self.clock = str(binary), str(model), clock
        self.process = None
        self.descriptor = None
        self.output = bytearray()
        self.started = 0.
        self.closed = False

    def submit(self, pcm):
        if self.closed or self.process is not None:
            raise RuntimeError('Verifier is closed or already occupied')
        if not pcm or len(pcm) % 2 or len(pcm) > 153600:
            raise ValueError('Use a bounded S16LE candidate window, at most 4.8 seconds')
        if not hasattr(os, 'memfd_create'):
            raise RuntimeError('Linux anonymous RAM descriptors required')
        self.descriptor = os.memfd_create('cdb-wake-stream-lab', flags=os.MFD_CLOEXEC)
        try:
            with os.fdopen(os.dup(self.descriptor), 'wb') as stream:
                with wave.open(stream, 'wb') as audio:
                    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                    audio.writeframes(pcm)
            os.lseek(self.descriptor, 0, os.SEEK_SET)
            command = [self.binary, '-m', self.model, '-f', f'/proc/self/fd/{self.descriptor}',
                       '-l', 'de', '-t', '2', '-bo', '1', '-bs', '1', '-nf', '-nt', '-np',
                       '-ac', '256', '--prompt', 'Nabu.']
            self.process = subprocess.Popen(owned_command(command), stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, pass_fds=(self.descriptor,),
                                            bufsize=0)
            os.set_blocking(self.process.stdout.fileno(), False)
            self.output.clear()
            self.started = self.clock()
        except BaseException:
            self.cancel()
            raise

    def poll(self):
        if self.process is None: return None
        # Even a partial native line must not stop the audio reader.
        if select.select([self.process.stdout], [], [], 0)[0]:
            chunk = self.process.stdout.read(4096)
            if chunk: self.output.extend(chunk)
        error = None
        if len(self.output) > 8192: error = 'output_limit'
        elif self.clock() - self.started > 3: error = 'timeout'
        code = self.process.poll()
        if code is None and error is None: return None
        if code is not None and error is None:
            # Drain only bounded available bytes after confirmed native exit.
            rest = self.process.stdout.read(8193-len(self.output))
            if rest: self.output.extend(rest)
            if len(self.output) > 8192: error = 'output_limit'
        detected = False
        if code == 0 and error is None:
            try: detected = matches_nabu(self.output.decode('utf-8'))
            except UnicodeError: error = 'invalid_result'
        report = {'detected': detected, 'returncode': code, 'error': error,
                  'wall_seconds': round(self.clock()-self.started, 4)}
        self.cancel()
        return report

    def cancel(self):
        # Keep ownership if termination cannot be confirmed; never spawn over it.
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try: self.process.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    self.process.kill(); self.process.wait(timeout=.5)
            else:
                self.process.wait()
            self.process.stdout.close()
            self.process = None
        if self.descriptor is not None:
            os.close(self.descriptor); self.descriptor = None
        self.output.clear()

    def close(self):
        self.closed = True
        self.cancel()


class StreamingCandidate:
    """Candidate threshold cannot activate; only the bounded verifier can accept.

    Experimental constants are frozen before new acoustic evaluation. 2 seconds
    of look-back and 0.8 seconds of tail form one 2.8-second candidate window.
    Re-arm requires both minimum spacing and a sustained low primary score.
    """
    def __init__(self, detector, verifier):
        self.detector, self.verifier = detector, verifier
        self.model = detector.model if hasattr(detector, 'model') else None
        self.onset = detector.onset if hasattr(detector, 'onset') else None
        self.ring = deque(maxlen=96)
        self.frame = self.due = self.rearm_at = self.low_frames = 0
        self.state = 'ready'
        self.last_decision = None
        self.last_probability = None
        self.submitted = self.rejected = 0
        self.last_report = None

    def feed(self, pcm):
        if self.state == 'closed': raise RuntimeError('Candidate detector is closed')
        if len(pcm) != 1600: raise ValueError('Use 50-ms mono S16LE blocks at 16 kHz')
        self.last_decision = None
        if self.state == 'accepted': return False  # Parent must release/recreate after acceptance.
        self.frame += 1
        self.ring.append(bytes(pcm))
        self.detector.feed(pcm)  # Primary acceptance is deliberately not forwarded.
        self.last_probability = self.detector.last_probability
        probability = self.last_probability or 0.
        self.low_frames = self.low_frames+1 if probability < .05 else 0
        if self.state == 'verifying':
            result = self.verifier.poll()
            if result is not None:
                self.last_report = result
                if result['detected']:
                    self.state = 'accepted'; self.last_decision = 'accepted'
                    self.ring.clear()
                    return True
                self.rejected += 1
                self.state = 'cooldown'; self.last_decision = 'candidate_rejected'
        if self.state == 'cooldown' and self.frame >= self.rearm_at and self.low_frames >= 6:
            self.state = 'ready'
        if self.state == 'ready' and probability >= .15:
            self.state = 'tail'; self.due = self.frame + 16
        if self.state == 'tail' and self.frame >= self.due:
            self.verifier.submit(b''.join(list(self.ring)[-56:]))
            self.submitted += 1
            self.state = 'verifying'; self.rearm_at = self.frame + 40
        return False

    def close(self):
        self.state = 'closed'
        try: self.verifier.close()
        finally: self.ring.clear()
