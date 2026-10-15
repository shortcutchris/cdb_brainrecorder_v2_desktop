"""Bounded file-only wake comparison: no microphone, speaker, cloud or settings."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.wake_phrase import PhraseDetector, PHRASES, model_path


def score_case(expected_activation, repeat, found):
    """Count each separated file utterance; cloud-session dedup is a separate test."""
    expected = repeat if expected_activation else 0
    return {
        'expected_detections': expected,
        'activation_presence_passed': bool(found) == expected_activation,
        'passed': found == expected,
    }


def main():
    root=Path(__file__).resolve().parents[1]/'tests/fixtures/wake'
    cases=[('hey-brain-vincent-slow.mp3','hey-brain'),('hey-kai-vincent.mp3','hey-kai'),
           ('okay-kai-vincent.mp3','okay-kai'),('hey-guy-vincent.mp3',None),
           ('okay-karl-vincent.mp3',None),('kai-later-vincent.mp3',None)]
    rows=[];missing_words={};start=time.process_time()
    for filename,expected in cases:
        for gain in (1,.3,.03):
            pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/filename),
                '-af',f'volume={gain}','-ar','16000','-ac','1','-f','s16le','-'])
            for phrase in PHRASES:
                for repeat in (1,2):
                    d=PhraseDetector(phrase);found=0
                    if phrase not in missing_words:
                        vocabulary={w for g in PHRASES[phrase]['grammar'] for w in g.split()}
                        missing_words[phrase]=sorted(w for w in vocabulary if d.model.vosk_model_find_word(w)<0)
                    stream=(pcm+bytes(32000))*repeat+bytes(64000)
                    for i in range(0,len(stream),1600):found+=int(d.feed(stream[i:i+1600]))
                    rows.append({'clip':filename,'phrase':phrase,'gain':gain,'repeat':repeat,
                                 'expected_activation':expected==phrase,'detections':found,
                                 **score_case(expected==phrase, repeat, found)})
    report={'synthetic_files_only':True,'real_acoustic_path':False,
            'voices':1,'vosk_version':importlib.metadata.version('vosk'),
            'model':model_path().name,'missing_grammar_words':missing_words,
            'cpu_seconds':round(time.process_time()-start,2),
            'fixtures':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f,_ in cases},
            'cases':rows,'passed':all(r['passed'] for r in rows)}
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
