"""Local wake engines. Native inference is loaded only by the owned child."""
import importlib.util
import math
from types import SimpleNamespace
from services import wake_phrase

PHRASES = {'okay-nabu': {'label': 'Okay Nabu', 'engine': 'microWakeWord'}, **wake_phrase.PHRASES}
DEFAULT_PHRASE = wake_phrase.DEFAULT_PHRASE  # Preserve existing profiles and opt-in.


def phrase_spec(phrase):
    if not isinstance(phrase, str) or phrase not in PHRASES:
        raise ValueError('Bitte ein verfügbares Aktivierungswort auswählen.')
    return PHRASES[phrase]


def runtime_ready(phrase):
    phrase_spec(phrase)
    if phrase == 'okay-nabu':
        return (importlib.util.find_spec('pymicro_wakeword') is not None
                and importlib.util.find_spec('pymicro_features') is not None)
    return importlib.util.find_spec('vosk') is not None and wake_phrase.model_ready()


class NabuDetector:
    """Feed all five 10 ms subframes; no word/confidence emulation or Vosk fallback."""
    def __init__(self):
        from pymicro_wakeword import MicroWakeWord, MicroWakeWordFeatures, Model
        self.model = MicroWakeWord.from_builtin(Model.OKAY_NABU)
        self.features = MicroWakeWordFeatures()
        self.last_decision = None
        self.last_probability = None
        self.probability_cutoff = self.model.probability_cutoff
        # Unified technical diagnostic interface; this engine has no Vosk onset resets.
        self.onset = SimpleNamespace(renewals=0)

    def feed(self, audio):
        self.last_decision = None
        self.last_probability = None
        if len(audio) != 1600:
            raise ValueError('Wake input must be 50 ms S16LE mono at 16 kHz.')
        detected = False
        for offset in range(0, len(audio), 320):
            for features in self.features.process_streaming(audio[offset:offset+320]):
                # Never short circuit feature processing after a hit.
                probability = self.model.process_streaming_prob(features)
                if probability is None:
                    continue
                probability = float(probability)
                if not math.isfinite(probability) or not 0 <= probability <= 1:
                    raise ValueError('Invalid wake model probability')
                self.last_probability = max(self.last_probability or 0., probability)
                # Same strict comparison as upstream process_streaming; no calibration.
                detected = probability > self.probability_cutoff or detected
        if detected: self.last_decision = 'accepted'
        return detected


def create_detector(phrase):
    phrase_spec(phrase)
    if phrase == 'okay-nabu': return NabuDetector()
    return wake_phrase.PhraseDetector(phrase)
