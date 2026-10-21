"""Opt-in fixed speech. No model, network, microphone or synthesis at runtime."""
import hashlib
import io
import json
from pathlib import Path
import time
import wave


PHRASES = {
    'connecting': 'Ich verbinde dich.',
    'offline': 'Das Gespräch ist gerade nicht verfügbar. Bitte prüfe die Anzeige und versuche es erneut.',
    'timer': 'Dein Timer ist abgelaufen.',
    'reminder': 'Eine Erinnerung ist fällig. Bitte prüfe die Anzeige.',
}
PACK_VERSION = 1
REQUIRED_CLIPS = {'offline', 'timer', 'reminder'}
MAX_WAV_BYTES = 24_000 * 2 * 15 + 4096


def bounded_file(path, limit):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Sprachdatei fehlt oder ist ein Verweis.')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Sprachdatei ist zu groß.')
    return data


def validate_wav(data):
    """Return immutable, validated bytes; playback never reopens pack files."""
    if not isinstance(data, bytes) or len(data) > MAX_WAV_BYTES:
        raise ValueError('Ungültige Sprachdatei.')
    try:
        with wave.open(io.BytesIO(data)) as audio:
            frames = audio.getnframes()
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 24000, 'NONE'):
                raise ValueError('Sprache benötigt Mono-PCM mit 24 kHz und 16 Bit.')
            if not 2400 <= frames <= 24000 * 15 or len(audio.readframes(frames)) != frames * 2:
                raise ValueError('Sprachdatei ist leer, abgeschnitten oder zu lang.')
    except (wave.Error, EOFError) as error:
        raise ValueError('Ungültige Sprachdatei.') from error
    return data


def load_pack(folder):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Sprachpaket fehlt.')
    try:
        manifest = json.loads(bounded_file(folder / 'manifest.json', 8192))
        if not isinstance(manifest, dict) or type(manifest.get('version')) is not int or manifest.get('version') != PACK_VERSION or not REQUIRED_CLIPS <= set(manifest.get('clips', {})) <= set(PHRASES):
            raise ValueError('Sprachpaket passt nicht zu dieser App.')
        clips = {}
        for key, entry in manifest['clips'].items():
            text = PHRASES[key]
            if not isinstance(entry, dict) or entry.get('text') != text:
                raise ValueError('Text des Sprachpakets passt nicht zur App.')
            data = bounded_file(folder / (key + '.wav'), MAX_WAV_BYTES)
            if hashlib.sha256(data).hexdigest() != entry.get('sha256'):
                raise ValueError('Sprachdatei wurde verändert.')
            clips[key] = validate_wav(data)
            if key == 'connecting':
                with wave.open(io.BytesIO(data)) as audio:
                    if audio.getnframes() > 24000 * 3:
                        raise ValueError('Verbindungsansage darf höchstens drei Sekunden dauern.')
        return clips
    except (OSError, TypeError, AttributeError, KeyError) as error:
        raise ValueError('Sprachpaket kann nicht gelesen werden.') from error


class Announcements:
    def __init__(self, root, clock=time.monotonic):
        self.root = Path(root)
        self.preference = self.root / 'announcements.json'
        self.clock = clock
        self.enabled = {'offline': False, 'timers': False, 'connecting': False}
        try:
            saved = json.loads(self.preference.read_text())
            if isinstance(saved, dict):
                for key in self.enabled:
                    if type(saved.get(key)) is bool: self.enabled[key] = saved[key]
        except (OSError, ValueError): pass
        self.clips = {}
        self.message = ''
        self.seen_failure = 0
        self.last_offline = float('-inf')
        self.reload()

    def reload(self):
        try:
            self.clips = load_pack(self.root / 'announcements-pack')
            self.message = 'Deutsches Sprachpaket bereit. Änderungen werden beim Speichern neu geprüft.'
        except ValueError:
            self.clips = {}
            self.message = 'Sprachpaket fehlt oder ist ungültig. Die bisherigen Alarmtöne bleiben verfügbar.'

    def public(self):
        return dict(self.enabled, ready=bool(self.clips), connecting_ready='connecting' in self.clips, message=self.message)

    def configure(self, body):
        if not body or set(body) - set(self.enabled) or any(type(value) is not bool for value in body.values()):
            raise ValueError('Ungültige Ansage-Einstellung.')
        self.reload()
        if any(body.values()) and not self.clips:
            raise ValueError(self.message)
        if body.get('connecting') and 'connecting' not in self.clips:
            raise ValueError('Sprachpaket mit Verbindungsansage zuerst bereitstellen.')
        updated = self.enabled | body
        from meeting_recorder.core import atomic_write
        atomic_write(self.preference, json.dumps(updated))
        self.enabled = updated
        return self.public()

    def connecting_clip(self):
        return self.clips.get('connecting') if self.enabled['connecting'] else None

    def timer_clip(self, kind):
        return self.clips.get(kind) if self.enabled['timers'] else None

    def failure_clip(self, event, safe, quiet=True):
        # Consume even when disabled/busy: never speak stale errors after a
        # recording, new conversation, opt-in or account change.
        if not event or event['sequence'] <= self.seen_failure:
            return None
        now = self.clock()
        eligible = safe and self.enabled['offline'] and 0 <= now - event['at'] <= 15 and now - self.last_offline >= 60
        # The just-ended conversation may still have an output tail. Wait only
        # within the original event's TTL; any user activity consumes it below.
        if eligible and not quiet: return None
        self.seen_failure = event['sequence']
        if not eligible: return None
        clip = self.clips.get('offline')
        if clip: self.last_offline = now
        return clip
