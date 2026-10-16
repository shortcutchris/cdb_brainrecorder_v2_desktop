"""Operator-only, bounded human wake test. No room text/audio is retained.

Requires a present, informed tester. Reserves the microphone atomically; the
production wake listener resumes after cleanup. Does not start a cloud session.
Run with the installed app on PYTHONPATH and its configured wake model.
"""
import argparse
import json
import math
import os
from pathlib import Path
import select
import signal
import subprocess
import time
import urllib.request
import uuid

from services import wake_phrase
from services.live_audio import native_capture_command
from services.wake_diagnostics import AudioDiagnostics


def candidate_metrics(result, phrase):
    """Only the selected fixed phrase's scores, never arbitrary recognized words."""
    words = result.get('result', [])
    consistent = ' '.join(w.get('word', '') for w in words) == result.get('text')
    rows = []
    for left, right in zip(words, words[1:]):
        if (left.get('word'), right.get('word')) not in wake_phrase.phrase_spec(phrase)['pairs']:
            continue
        first, second = left.get('conf', 0), right.get('conf', 0)
        duration = right.get('end', 0) - left.get('start', 0)
        if any(type(v) not in (float, int) or not math.isfinite(v)
               for v in (first, second, duration)):
            rows.append({'reasons': ['invalid_numeric_result']})
            continue
        reasons = []
        if not consistent: reasons.append('text_mismatch')
        if first < .8: reasons.append('first_word_confidence')
        if second < .9: reasons.append('second_word_confidence')
        if not .25 <= duration <= 2.5: reasons.append('duration')
        rows.append({'first_confidence': round(first, 6),
                     'second_confidence': round(second, 6),
                     'duration_seconds': round(duration, 3), 'reasons': reasons})
    return rows[:8]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phrase', choices=wake_phrase.PHRASES, required=True)
    parser.add_argument('--seconds', type=int, default=45)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 60: parser.error('Use 10–60 seconds.')
    root = Path.home()/'.local/share/cdb-recorder-local'
    token = json.loads((root/'management/local-auth.json').read_text())['token']
    def request(path, body=None):
        req = urllib.request.Request('http://127.0.0.1:8088'+path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response: return json.load(response)
    def emit(value): print(json.dumps(value), flush=True)
    def stop(*_): raise SystemExit('Test interrupted')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    ident = str(uuid.uuid4())
    capture = None
    reserved = False
    original = wake_phrase.is_activation
    def inspect(result, phrase):
        candidates = candidate_metrics(result, phrase)
        if candidates: emit({'event': 'candidate', 'candidates': candidates})
        return original(result, phrase)
    try:
        request('/api/management/prepare', {'command': ident}); reserved = True
        if request('/api/wake/status')['diagnostics']['capture_running']:
            raise RuntimeError('Production microphone capture did not stop')
        config = {'device': request('/api/state')['config']['device']}
        detector = wake_phrase.PhraseDetector(args.phrase)
        wake_phrase.is_activation = inspect
        capture = subprocess.Popen(native_capture_command(config), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)
        measure = AudioDiagnostics(); buffer = b''
        start = last_data = time.monotonic()
        ready = False
        while time.monotonic()-start < args.seconds:
            if not select.select([capture.stdout], [], [], .2)[0]:
                if time.monotonic()-last_data > 3: raise RuntimeError('No microphone frames')
                continue
            block = capture.stdout.read(1600)
            if not block: raise RuntimeError('Microphone capture ended')
            last_data = time.monotonic(); buffer += block
            if not ready:
                emit({'event': 'ready', 'phrase': args.phrase, 'seconds': args.seconds}); ready = True
            while len(buffer) >= 1600:
                pcm, buffer = buffer[:1600], buffer[1600:]
                detector.feed(pcm)
                measure.feed(pcm, detector.last_decision, detector.onset.renewals)
                if detector.last_decision: emit({'event': 'decision', **measure.snapshot()})
        emit({'event': 'finished', **measure.snapshot()})
    finally:
        wake_phrase.is_activation = original
        if capture is not None:
            if capture.poll() is None:
                os.killpg(capture.pid, signal.SIGTERM)
                try: capture.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(capture.pid, signal.SIGKILL); capture.wait(timeout=2)
            if capture.stdout: capture.stdout.close()
        if reserved:
            request('/api/management/release', {'command': ident})
            emit({'event': 'maintenance_released'})


if __name__ == '__main__': main()
