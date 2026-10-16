"""Small local Vosk grammar for Hey Brain. Never saves or uploads audio.

Confusable phrases compete in the decoder rather than being coerced into the
activation phrase. Only a confident adjacent word pair in a completed segment can wake.
"""
import json
import os
from array import array
from collections import deque
import statistics
import sys
from pathlib import Path

WORD = 'Hey Brain'
MODEL_NAME = 'vosk-model-small-en-us-0.15'
MODEL_URL = 'https://alphacephei.com/vosk/models/' + MODEL_NAME + '.zip'
MODEL_SHA256 = '30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498'
GRAMMAR = ['hey brain', 'hey brian', 'hey rain', 'hey train', 'hey jane',
           'hey bring', 'hey brent', 'the brain', '[unk]']
DEFAULT_PHRASE = 'hey-brain'
PHRASES = {
    DEFAULT_PHRASE: {'label': WORD, 'pairs': [('hey', 'brain')], 'grammar': GRAMMAR},
    # Experimental KAI phrase: natural Pi calls scored .526/.657 for "kai".
    # Keep exact words, first-word confidence and duration guards; do not
    # broaden the grammar or change the established Brain/Okay KAI behavior.
    'hey-kai': {'label': 'Hey KAI', 'pairs': [('hey', 'kai')], 'second_confidence': .5,
                'grammar': ['hey kai', 'hey guy', 'hey kyle', 'hey kay', 'hey sky',
                            'hey brain', 'okay kai', 'hi kai', '[unk]']},
    'okay-kai': {'label': 'Okay KAI', 'pairs': [('okay', 'kai')],
                 'grammar': ['okay kai', 'okay guy', 'okay kyle', 'okay kay',
                             'okay sky', 'hey kai', 'hey brain', '[unk]']},
}


def phrase_spec(phrase):
    if not isinstance(phrase, str) or phrase not in PHRASES:
        raise ValueError('Bitte ein verfügbares Aktivierungswort auswählen.')
    return PHRASES[phrase]


def confidence_thresholds(phrase):
    return .8, phrase_spec(phrase).get('second_confidence', .9)


def model_path():
    return Path(os.environ.get('CDB_WAKE_MODEL', str(Path(__file__).resolve().parents[1] / 'models' / MODEL_NAME)))


def model_ready():
    return all((model_path()/part).is_file() for part in ('am/final.mdl', 'conf/mfcc.conf', 'graph/HCLr.fst', 'graph/Gr.fst'))


def is_activation(result, phrase=DEFAULT_PHRASE):
    pairs = phrase_spec(phrase)['pairs']
    first_min, second_min = confidence_thresholds(phrase)
    words = result.get('result', [])
    if ' '.join(w.get('word', '') for w in words) != result.get('text'): return False
    # Wake words occur inside a stream, including after background speech or
    # two repeated calls. Do not require the entire acoustic segment to match.
    for left, right in zip(words, words[1:]):
        if ((left.get('word'), right.get('word')) in pairs
                and left.get('conf', 0) >= first_min and right.get('conf', 0) >= second_min
                and .25 <= right.get('end', 0) - left.get('start', 0) <= 2.5):
            return True
    return False



class LowNoiseOnset:
    """Renew only on signal rise after two seconds of very low nonzero noise.

    Keep 200 ms locally in RAM to avoid clipping the onset. No gate, gain or
    confidence changes. Digital silence and louder backgrounds retain behavior.
    Production feeds fixed 50 ms S16LE/16 kHz blocks; other sizes bypass this.
    """
    def __init__(self):
        self.quiet = deque(maxlen=40)
        self.pre = deque(maxlen=4)
        self.renewals = 0

    def feed(self, audio):
        if len(audio) != 1600:
            self.quiet.clear(); self.pre.clear()
            return None
        values = array('h', audio)
        if sys.byteorder != 'little': values.byteswap()
        rms = (sum(v*v for v in values)/len(values))**.5
        peak = max(abs(v) for v in values)
        floor = statistics.median(self.quiet) if len(self.quiet) == 40 else 0
        replay = None
        if 1 <= floor <= 8 and (rms > max(8, floor*2) or peak > 48):
            replay = list(self.pre)
            self.renewals += 1
            self.quiet.clear()
        if rms <= 8 and peak <= 48: self.quiet.append(rms)
        else: self.quiet.clear()
        self.pre.append(audio)
        return replay


class PhraseDetector:
    def __init__(self, phrase=DEFAULT_PHRASE):
        self.phrase = phrase
        self.spec = phrase_spec(phrase)
        from vosk import Model, SetLogLevel
        SetLogLevel(-1)
        self.model = Model(str(model_path()))
        self.last_decision = None
        self.onset = LowNoiseOnset()
        self._new_segment()

    def _new_segment(self):
        from vosk import KaldiRecognizer
        self.recognizer = KaldiRecognizer(self.model, 16000, json.dumps(self.spec['grammar']))
        self.recognizer.SetWords(True)

    def feed(self, audio):
        self.last_decision = None
        replay = self.onset.feed(audio)
        if replay is not None:
            self._new_segment()
            for previous in replay:
                self.recognizer.AcceptWaveform(previous)
        if not self.recognizer.AcceptWaveform(audio): return False
        result = json.loads(self.recognizer.Result())
        accepted = is_activation(result, self.phrase)
        if result.get('text'):
            # Fixed diagnostic categories only: never expose decoded room speech.
            words = [w.get('word') for w in result.get('result', [])]
            candidate = any((a, b) in self.spec['pairs'] for a, b in zip(words, words[1:]))
            wake_words = {word for pair in self.spec['pairs'] for word in pair}
            self.last_decision = ('accepted' if accepted else 'candidate_rejected' if candidate
                                  else 'partial_wake_word' if wake_words.intersection(words)
                                  else 'other_speech')
        # Keep the acoustic model, but discard completed speech's decoder state.
        # A long mixed stream otherwise reproducibly lost a later Hey Brain.
        # Never reset inside an utterance, or repeatedly rebuild during silence.
        if result.get('text'):
            self._new_segment()
        return accepted
