"""Bounded synthetic continuous KAI stress; no hardware, network or profile access.

Uses existing generated speech, real production detector and fixed-size frames.
Accelerated audio time does not establish real wall-clock idle reliability.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import wake_phrase


def rss_mb():
    if sys.platform.startswith('linux'):
        return round(int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE') / 1048576, 2)
    if sys.platform == 'darwin':
        return round(int(subprocess.check_output(['ps', '-p', str(os.getpid()), '-o', 'rss='])) / 1024, 2)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minutes', type=int, default=60)
    parser.add_argument('--cycles', type=int, default=300)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.minutes <= 120 or not 1 <= args.cycles <= 1000:
        parser.error('Use 1–120 negative audio minutes and 1–1000 mixed cycles.')
    root = Path(__file__).resolve().parents[1]/'tests/fixtures/wake'
    negatives = [root/'confusers'/('kai-confusers-'+voice+'.mp3') for voice in ('pauli','otto')]
    targets = [root/'hey-kai-vincent.mp3'] + [root/'multivoice'/('hey-kai-'+voice+'.mp3') for voice in ('pauli','otto')]
    def load(path):
        value = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
            '-ar', '16000', '-ac', '1', '-f', 's16le', '-'])
        # Match production's 50 ms input frames, including fixture boundaries.
        value += bytes((-len(value)) % 1600)
        return [value[i:i+1600] for i in range(0, len(value), 1600)]
    clips = {p: load(p) for p in negatives+targets}
    detector = wake_phrase.PhraseDetector('hey-kai')
    started = time.monotonic(); cpu = time.process_time(); initial = rss_mb()
    total = 0; last_hit = None
    def feed(frames):
        nonlocal total, last_hit
        count = 0
        for frame in frames:
            total += 1
            if detector.feed(frame): count += 1; last_hit = total
        return count
    silence = [bytes(1600)]*40
    negative_hits = 0; segments = 0; checkpoints = []
    while total < args.minutes*1200:
        frames = clips[negatives[segments % len(negatives)]]+silence
        frames = frames[:args.minutes*1200-total]
        negative_hits += feed(frames); segments += 1
        if segments % 30 == 0:
            point = {'phase':'negative','audio_seconds':total/20,'unexpected':negative_hits,'rss_mb':rss_mb()}
            checkpoints.append(point); print(json.dumps(point), flush=True)
    negative_result = {'audio_seconds':total/20,'unexpected':negative_hits,'segments':segments,'rss_mb':rss_mb()}
    print(json.dumps({'negative_complete':negative_result}), flush=True)
    rows = []
    for cycle in range(args.cycles):
        false_hits = feed(clips[negatives[cycle % len(negatives)]]+silence)
        target = targets[cycle % len(targets)]; repeat = 1+cycle%2
        hits = 0; latencies = []
        for _ in range(repeat):
            begin = total
            detected = feed(clips[target]+silence)
            hits += detected
            latencies.append((last_hit-begin)/20 if detected else None)
        rows.append({'cycle':cycle+1,'fixture':target.name,'expected':repeat,'detections':hits,
                     'unexpected':false_hits,'target_audio_latency_seconds':latencies,
                     'passed':hits==repeat and false_hits==0})
        if (cycle+1) % 25 == 0:
            point = {'phase':'mixed','cycle':cycle+1,'audio_seconds':total/20,
                     'failed_cases':sum(not r['passed'] for r in rows),'rss_mb':rss_mb()}
            checkpoints.append(point);print(json.dumps(point),flush=True)
    result = {'synthetic_only':True,'accelerated_not_wall_clock':True,
              'continuous_detector':True,'phrase':'hey-kai','thresholds':wake_phrase.confidence_thresholds('hey-kai'),
              'source_sha256':hashlib.sha256(Path(wake_phrase.__file__).read_bytes()).hexdigest(),
              'vosk_version':importlib.metadata.version('vosk'),'model':wake_phrase.model_path().name,
              'fixtures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in negatives+targets},
              'negative_phase':negative_result,'cycles':rows,'checkpoints':checkpoints,
              'audio_seconds':total/20,'wall_seconds':round(time.monotonic()-started,2),
              'cpu_seconds':round(time.process_time()-cpu,2),'initial_rss_mb':initial,'final_rss_mb':rss_mb(),
              'passed':negative_hits==0 and all(r['passed'] for r in rows)}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'cycles':len(rows),'audio_seconds':result['audio_seconds']}),flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
