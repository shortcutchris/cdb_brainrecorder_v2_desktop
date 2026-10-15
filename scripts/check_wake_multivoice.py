"""Bounded synthetic-file comparison; no room audio, cloud calls or Pi changes."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.wake_phrase import PHRASES, PhraseDetector, model_path
from scripts.check_wake_candidates import score_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / 'tests/fixtures/wake/multivoice'
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    rows = []
    missing = {}
    hashes = {}
    for clip in manifest['clips']:
        path = root / clip['file']
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for gain in (1, .03):
            pcm = subprocess.check_output([
                'ffmpeg', '-v', 'error', '-i', str(path), '-af', f'volume={gain}',
                '-ar', '16000', '-ac', '1', '-f', 's16le', '-'])
            for phrase in PHRASES:
                for repeat in (1, 2):
                    detector = PhraseDetector(phrase)
                    if phrase not in missing:
                        vocabulary = {w for g in PHRASES[phrase]['grammar'] for w in g.split()}
                        missing[phrase] = sorted(
                            w for w in vocabulary if detector.model.vosk_model_find_word(w) < 0)
                    stream = bytes(64000) + (pcm + bytes(32000)) * repeat + bytes(64000)
                    found = sum(bool(detector.feed(stream[i:i + 1600]))
                                for i in range(0, len(stream), 1600))
                    score = score_case(clip['target'] == phrase, repeat, found)
                    if clip['ambiguous']:
                        score = {'expected_detections': None,
                                 'activation_presence_passed': None, 'passed': None}
                    rows.append({'file': path.name, 'voice': clip['voice'], 'phrase': phrase,
                                 'gain': gain, 'repeat': repeat, 'detections': found,
                                 'target': clip['target'], 'ambiguous': clip['ambiguous'], **score})
    scored = [row for row in rows if row['passed'] is not None]
    report = {
        'synthetic_files_only': True, 'room_audio': False,
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'model': model_path().name, 'vosk_version': importlib.metadata.version('vosk'),
        'execution_host': 'local development machine; not production Pi',
        'voices': sorted({clip['voice'] for clip in manifest['clips']}),
        'leading_silence_seconds': 2, 'missing_grammar_words': missing,
        'fixtures': hashes, 'cases': rows,
        'passed_cases': sum(row['passed'] for row in scored), 'scored_cases': len(scored),
        'ambiguous_cases': len(rows) - len(scored), 'passed': all(row['passed'] for row in scored),
    }
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('model', 'passed_cases', 'scored_cases', 'ambiguous_cases')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
