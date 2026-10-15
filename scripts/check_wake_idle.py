"""Bounded synthetic idle-audio tests; never opens hardware or cloud sessions.

Audio is processed faster than real time. This does not replace a wall-clock
standby test. Each scenario keeps one recognizer until the first target phrase,
matching the production lifetime before an activation.
"""
import argparse
import json
import time

from scripts.check_wake_stream import EndpointRefreshExperiment, pcm, rss
from services.wake_phrase import PhraseDetector


def scenario(minutes, background, refresh=False):
    detector = (EndpointRefreshExperiment if refresh else PhraseDetector)()
    initial_rss = rss()
    cpu, started = time.process_time(), time.monotonic()
    target = pcm('Hey Brain')
    # No target words in this fixture; includes the deliberately confusable Brian.
    negative = pcm('Good morning. Hey Brian. We have a meeting today.')
    silence = bytes(1600)
    total_blocks = round(minutes * 60 * 20)
    unexpected, peak_rss = 0, initial_rss
    checkpoints = []
    for block in range(total_blocks):
        offset = block % 600  # one non-target passage every 30 audio seconds
        chunk = (negative[offset * 1600:(offset + 1) * 1600]
                 if background and offset * 1600 < len(negative) else silence)
        unexpected += bool(detector.feed(chunk.ljust(1600, b'\0')))
        if block % 12000 == 0:
            current = rss()
            peak_rss = max(peak_rss or 0, current or 0)
            checkpoints.append({'audio_seconds': round(block / 20, 2), 'rss_mb': current})
    hits, first = 0, None
    for offset in range(0, len(target), 1600):
        if detector.feed(target[offset:offset + 1600]):
            hits += 1
            if first is None:
                first = round((offset + 1600) / 32000, 2)
    return {'idle_audio_minutes': minutes, 'background_speech': background,
            'endpoint_refresh_experiment': refresh,
            'unexpected_activations': unexpected, 'target_detections': hits,
            'target_audio_latency_s': first, 'passed': unexpected == 0 and hits == 1,
            'cpu_seconds': round(time.process_time() - cpu, 2),
            'wall_seconds': round(time.monotonic() - started, 2),
            'initial_rss_mb': initial_rss, 'final_rss_mb': rss(),
            'sampled_peak_rss_mb': peak_rss, 'checkpoints': checkpoints}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minutes', type=float, nargs='+', default=[0, 10, 60])
    parser.add_argument('--background-speech', action='store_true')
    parser.add_argument('--endpoint-refresh-experiment', action='store_true')
    args = parser.parse_args()
    if len(args.minutes) > 8 or any(not 0 <= n <= 480 for n in args.minutes):
        parser.error('Use at most eight scenarios of 0–480 audio minutes.')
    rows = []
    for minutes in args.minutes:
        row = scenario(minutes, args.background_speech, args.endpoint_refresh_experiment)
        rows.append(row)
        print(json.dumps({'scenario_complete': row}), flush=True)
    print(json.dumps({'synthetic_audio': True, 'accelerated_not_wall_clock': True,
                      'passed': all(row['passed'] for row in rows), 'scenarios': rows}))
    return 0 if all(row['passed'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
