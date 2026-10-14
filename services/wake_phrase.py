"""Small local Vosk grammar for Hey Brain. Never saves or uploads audio.

Confusable phrases compete in the decoder rather than being coerced into the
activation phrase. Only a confident adjacent word pair in a completed segment can wake.
"""
import json
import os
from pathlib import Path

WORD = 'Hey Brain'
MODEL_NAME = 'vosk-model-small-en-us-0.15'
MODEL_URL = 'https://alphacephei.com/vosk/models/' + MODEL_NAME + '.zip'
MODEL_SHA256 = '30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498'
GRAMMAR = ['hey brain', 'hey brian', 'hey rain', 'hey train', 'hey jane',
           'hey bring', 'hey brent', 'the brain', '[unk]']


def model_path():
    return Path(os.environ.get('CDB_WAKE_MODEL', str(Path(__file__).resolve().parents[1] / 'models' / MODEL_NAME)))


def model_ready():
    return all((model_path()/part).is_file() for part in ('am/final.mdl', 'conf/mfcc.conf', 'graph/HCLr.fst', 'graph/Gr.fst'))


def is_activation(result):
    words = result.get('result', [])
    if ' '.join(w.get('word', '') for w in words) != result.get('text'): return False
    # Wake words occur inside a stream, including after background speech or
    # two repeated calls. Do not require the entire acoustic segment to match.
    for left, right in zip(words, words[1:]):
        if (left.get('word') == 'hey' and right.get('word') == 'brain'
                and left.get('conf', 0) >= .8 and right.get('conf', 0) >= .9
                and .25 <= right.get('end', 0) - left.get('start', 0) <= 2.5):
            return True
    return False



class PhraseDetector:
    def __init__(self):
        from vosk import Model, KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)
        self.model = Model(str(model_path()))
        self.recognizer = KaldiRecognizer(self.model, 16000, json.dumps(GRAMMAR))
        self.recognizer.SetWords(True)

    def feed(self, audio):
        if not self.recognizer.AcceptWaveform(audio): return False
        return is_activation(json.loads(self.recognizer.Result()))
