"""Small local Vosk grammar for Hey Brain. Never saves or uploads audio.

Confusable phrases compete in the decoder rather than being coerced into the
activation phrase. Only a completed, confident two-word utterance can wake.
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
    return (result.get('text') == 'hey brain' and len(words) == 2
            and [w.get('word') for w in words] == ['hey', 'brain']
            and words[0].get('conf', 0) >= .8 and words[1].get('conf', 0) >= .9
            and .25 <= words[-1].get('end', 0) - words[0].get('start', 0) <= 2.5)


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
