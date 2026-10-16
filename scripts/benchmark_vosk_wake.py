"""File-only exploratory Vosk wake benchmark; never opens an audio device.

Use a manifest declaring synthetic_files_only=true and 1–64 cases containing
file (relative to the manifest), label, and boolean expected. Model and grammar
must already exist. This is not a production detector or a model installer.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import time
import wave


def load_cases(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('synthetic_files_only') is not True:
        raise ValueError('Explicit synthetic-files declaration required')
    cases = manifest.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise ValueError('Use 1–64 known synthetic files')
    result = []
    for case in cases:
        if type(case.get('expected')) is not bool:
            raise ValueError('expected must be a boolean')
        label = case.get('label')
        if not isinstance(label, str) or not 1 <= len(label) <= 160:
            raise ValueError('A bounded case label is required')
        path = manifest_path.parent / case['file']
        with wave.open(str(path)) as source:
            if (source.getframerate(), source.getsampwidth(), source.getnchannels()) != (16000, 2, 1):
                raise ValueError('Use 16 kHz mono signed 16-bit WAV')
            if not 0 < source.getnframes() <= 16000 * 60:
                raise ValueError('Use nonempty clips no longer than 60 seconds')
            pcm = source.readframes(source.getnframes())
        result.append((label, case['expected'], pcm))
    return result


def validate_grammar(model, grammar, accepted):
    if (not isinstance(grammar, list) or not 1 <= len(grammar) <= 128
            or any(not isinstance(p, str) or not 0 < len(p) <= 200 for p in grammar)):
        raise ValueError('Use 1–128 bounded grammar phrases')
    if not isinstance(accepted, list) or not accepted or any(p not in grammar for p in accepted):
        raise ValueError('Accepted phrases must belong to the declared grammar')
    words = set(' '.join(grammar).split()) - {'[unk]'}
    missing = sorted(word for word in words if model.vosk_model_find_word(word) < 0)
    if missing:
        raise ValueError('Out-of-vocabulary grammar words: ' + ', '.join(missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--grammar', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    cases = load_cases(args.manifest)
    spec = json.loads(args.grammar.read_text())
    # Optional lab packages are deliberately imported only after input validation.
    import numpy as np
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    started = time.monotonic()
    model = Model(str(args.model))
    load_seconds = time.monotonic() - started
    grammar, accepted = spec['grammar'], spec['accepted']
    validate_grammar(model, grammar, accepted)
    rows = []
    for label, expected, raw in cases:
        for gain, noise in [(1., 0.), (.25, 0.), (.25, .002)]:
            x = np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768 * gain
            if noise:
                x = x + np.random.default_rng(743).normal(0, noise, len(x))
            data = bytes(32000) + (np.clip(x, -1, 32767/32768)*32768).astype('<i2').tobytes() + bytes(64000)
            cpu = time.process_time()
            rec = KaldiRecognizer(model, 16000, json.dumps(grammar))
            rec.SetWords(True)
            parts = []
            for i in range(0, len(data), 1600):
                if rec.AcceptWaveform(data[i:i+1600]):
                    parts.append(json.loads(rec.Result()))
            parts.append(json.loads(rec.FinalResult()))
            texts = [part.get('text', '') for part in parts]
            duration = time.process_time() - cpu
            assert math.isfinite(duration)
            rows.append(dict(file=label, expected=expected, gain=gain, noise_std=noise,
                             sha256=hashlib.sha256(raw).hexdigest(),
                             detected=any(text in accepted for text in texts),
                             synthetic_decoded_texts=texts, cpu_seconds=duration,
                             audio_seconds=len(data)/32000))
    report = dict(engine=args.model.name, runtime_version=importlib.metadata.version('vosk'),
                  host=platform.machine(), exploratory=True, microphone=False, speaker=False,
                  synthetic_files_only=True, grammar=grammar, accepted=accepted,
                  manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                  grammar_sha256=hashlib.sha256(args.grammar.read_bytes()).hexdigest(),
                  load_seconds=load_seconds, cpu_timing='recognizer creation and inference; model load excluded',
                  cases=rows, positive_detected=sum(r['detected'] for r in rows if r['expected']),
                  positive_total=sum(r['expected'] for r in rows),
                  false_positives=sum(r['detected'] for r in rows if not r['expected']),
                  negative_total=sum(not r['expected'] for r in rows),
                  cpu_seconds=sum(r['cpu_seconds'] for r in rows))
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}))


if __name__ == '__main__':
    main()
