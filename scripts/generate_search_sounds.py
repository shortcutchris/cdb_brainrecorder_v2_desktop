#!/usr/bin/env python3
"""Render original search-loop proposals using only the Python standard library.

No external samples, network calls or runtime synthesis on the Pi are required.
The listening previews repeat the exact loop four times, at +10 dB for comparison.
"""
from array import array
import json
import math
from pathlib import Path
import sys
import wave

RATE = 24000
SECONDS = 3
OUT = Path(__file__).resolve().parents[1] / "docs/search-sound-study"


def render(warm=False):
    values = [0.0] * (RATE * SECONDS)
    # Four gentle notes, then breathing space. Tails finish before the loop seam.
    for start, frequency, gain in zip(
        (.08, .43, .78, 1.13),
        (523.251, 659.255, 783.991, 659.255),
        (1.0, .88, .82, .72),
    ):
        if warm:
            frequency *= .75
        duration = 1.5
        for i in range(int(duration * RATE)):
            t = i / RATE
            attack = min(1, t / .022)
            release = min(1, (duration - t) / .15)
            envelope = math.sin(attack * math.pi / 2) ** 2 * release ** 2
            fundamental = math.sin(2 * math.pi * frequency * t) * math.exp(-t / .23)
            overtone = (.12 if warm else .3) * math.sin(
                2 * math.pi * frequency * (2 if warm else 2.76) * t
            ) * math.exp(-t / .09)
            values[int(start * RATE) + i] += gain * envelope * (fundamental + overtone)
    peak = max(abs(v) for v in values)
    # Runtime proposal peak -24 dBFS. Actual room volume needs a Pi listening test.
    return [v / peak * 10 ** (-24 / 20) for v in values]


def write(name, values):
    pcm = array('h', (round(max(-1, min(1, x)) * 32767) for x in values))
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(OUT / name), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm.tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, warm in [('soft-bells', False), ('warm-plucks', True)]:
        values = render(warm)
        write(name + '-loop.wav', values)
        write(name + '-preview.wav', [v * 10 ** (.5) for v in values] * 4)
        report[name] = {
            'sample_rate': RATE, 'channels': 1, 'bits': 16,
            'loop_seconds': SECONDS, 'preview_seconds': SECONDS * 4,
            'peak_dbfs': round(20 * math.log10(max(abs(v) for v in values)), 2),
            'rms_dbfs': round(20 * math.log10(math.sqrt(sum(v*v for v in values) / len(values))), 2),
            'first_sample': values[0], 'last_sample': values[-1],
            'preview_gain_db': 10,
        }
        assert values[0] == values[-1] == 0
        assert max(abs(v) for v in values) * 10 ** .5 < 1
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
