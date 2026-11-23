"""Original, local device cues; never change output volume or require a network."""
import array
from functools import lru_cache
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

from fleet.common import read, save

KINDS = ('startup', 'shutdown')
RATE = 24000


@lru_cache(maxsize=2)
def cue(kind):
    """A soft rising chord and its short falling answer, mono PCM16."""
    if kind not in KINDS:
        raise ValueError('Unbekannter Geräteklang.')
    seconds = 1.2 if kind == 'startup' else .7
    notes = [(261.63, 0), (329.63, .06), (392.0, .12), (587.33, .18)] if kind == 'startup' else [(392.0, 0), (329.63, .1), (261.63, .2)]
    samples = array.array('h')
    for i in range(round(seconds * RATE)):
        t = i / RATE
        value = 0
        for frequency, onset in notes:
            age = t - onset
            if age < 0:
                continue
            envelope = min(1, age / .025) * math.exp(-3.5 * age)
            envelope *= min(1, max(0, seconds - t) / .15)
            phase = 2 * math.pi * frequency * age
            value += envelope * (math.sin(phase) + .12 * math.sin(2 * phase))
        samples.append(round(32767 * .055 * value))
    if sys.byteorder != 'little':
        samples.byteswap()
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(samples.tobytes())
    return output.getvalue()


class DeviceSounds:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / 'device-sounds.json'
        self.startup_pending = False

    def public(self):
        try:
            settings = read(self.path, {})
        except (OSError, ValueError):
            settings = {}
        if not isinstance(settings, dict):
            settings = {}
        return {kind: settings.get(kind) is True for kind in KINDS}

    def configure(self, body):
        if not body or set(body) - set(KINDS) or any(type(v) is not bool for v in body.values()):
            raise ValueError('Ungültige Geräteklang-Einstellung.')
        save(self.path, self.public() | body)
        return self.public()

    def ready(self, boot):
        """One claim per OS boot, including disabled/muted/unsuccessful attempts.

        The separate lock survives atomic marker replacement and prevents two
        app instances or browser tabs from replaying the welcome cue.
        """
        if not boot:
            return
        import fcntl
        folder = self.root / 'management'
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'startup-sound.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            marker = folder / 'startup-sound.json'
            try:
                previous = read(marker, {})
            except (OSError, ValueError):
                previous = {}
            if isinstance(previous, dict) and previous.get('boot') == boot:
                return
            save(marker, {'boot': boot})
            self.startup_pending = self.public()['startup']

    def take_startup(self):
        pending, self.startup_pending = self.startup_pending, False
        return pending and self.public()['startup']


def play_shutdown(root, runner=subprocess.run):
    """Best-effort farewell inside the shutdown lease, at most ~2s for audio.

    The independent power worker owns this process. A missing, muted or hung
    audio service must never prevent poweroff. No alternate speaker fallback.
    """
    root = Path(root)
    if not DeviceSounds(root).public()['shutdown']:
        return False
    try:
        selected = read(root / 'speaker.json', {}).get('device', '')
        if not selected:
            selected = runner(['pactl', 'get-default-sink'], check=True, capture_output=True,
                              text=True, timeout=.35).stdout.strip()
        sinks = json.loads(runner(['pactl', '-f', 'json', 'list', 'sinks'], check=True,
                                  capture_output=True, text=True, timeout=.35).stdout)
        sink = next((s for s in sinks if s['name'] == selected), None)
        if not sink or sink.get('mute') or selected == 'auto_null':
            return False
        props = sink.get('properties', {})
        if str(props.get('node.virtual', '')).lower() == 'true' or props.get('factory.name') == 'support.null-audio-sink':
            return False
        if not any(v.get('value', 0) > 0 for v in sink.get('volume', {}).values()):
            return False
        with wave.open(io.BytesIO(cue('shutdown')), 'rb') as wav:
            pcm = wav.readframes(wav.getnframes())
        runner(['paplay', '--device=' + selected, '--raw', '--format=s16le',
                '--rate=24000', '--channels=1'], input=pcm, capture_output=True,
               check=True, timeout=1.3)
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        return False
