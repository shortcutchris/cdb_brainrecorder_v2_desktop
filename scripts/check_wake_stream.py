"""Synthetic continuous-detector stress; no microphone, speaker, or cloud calls."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time
from services.wake_phrase import PhraseDetector, GRAMMAR, is_activation
from services import wake_phrase

DETECTOR_SOURCE_SHA256 = hashlib.sha256(Path(wake_phrase.__file__).read_bytes()).hexdigest()


class EndpointRefreshExperiment(PhraseDetector):
    """Lab-only comparison. Does not change the installed app's detector."""
    def feed(self, audio):
        if not self.recognizer.AcceptWaveform(audio):
            return False
        found = is_activation(json.loads(self.recognizer.Result()))
        from vosk import KaldiRecognizer
        self.recognizer = KaldiRecognizer(self.model, 16000, json.dumps(GRAMMAR))
        self.recognizer.SetWords(True)
        return found


def pcm(text):
    wav = subprocess.check_output(['espeak-ng', '-v', 'en-us', '-s', '145', '--stdout', text])
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-ar', '16000',
        '-ac', '1', '-f', 's16le', 'pipe:1'], input=wav, capture_output=True, check=True).stdout + bytes(64000)


def rss():
    try:
        return round(int(Path('/proc/self/statm').read_text().split()[1]) * resource.getpagesize() / 1048576, 2)
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=int, default=100)
    parser.add_argument('--endpoint-refresh-experiment', action='store_true',
                        help='Lab comparison only: replace recognizer after completed segments.')
    args = parser.parse_args()
    if not 4 <= args.cycles <= 2000:
        parser.error('Use 4–2000 bounded cycles.')
    clips = [(pcm('Hey Brain'), True), (pcm('Hey Brain Hey Brain'), True),
             (pcm('Hey Brian'), False), (pcm('Good morning'), False)]
    detector = (EndpointRefreshExperiment if args.endpoint_refresh_experiment else PhraseDetector)()
    before, cpu = rss(), time.process_time()
    rows, seconds = [], 0
    for cycle in range(args.cycles):
        audio, expected = clips[cycle % len(clips)]
        hits = sum(bool(detector.feed(audio[i:i+1600])) for i in range(0, len(audio), 1600))
        seconds += len(audio) / 32000
        rows.append({'cycle': cycle + 1, 'expected': expected, 'detections': hits,
                     'passed': bool(hits) == expected, 'rss_mb': rss()})
    result = {'synthetic_audio': True, 'continuous_detector': True,
              'detector_source_sha256': DETECTOR_SOURCE_SHA256,
              'endpoint_refresh_experiment': args.endpoint_refresh_experiment, 'cycles': args.cycles,
              'passed': all(r['passed'] for r in rows), 'audio_seconds': round(seconds, 2),
              'cpu_seconds': round(time.process_time() - cpu, 2), 'initial_rss_mb': before,
              'final_rss_mb': rss(), 'failed_cases': [r for r in rows if not r['passed']],
              'checkpoints': [r for r in rows if r['cycle'] % max(10, args.cycles // 20) == 0]}
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
