"""File-only confidence comparison, including explicit negative scripts. No Pi I/O."""
import sys,json,time,hashlib,subprocess
import importlib.metadata
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import wake_phrase
from scripts.diagnose_wake_candidate import candidate_metrics


def main(output):
    root=Path(__file__).resolve().parents[1]/'tests/fixtures/wake'
    clips=json.loads((root/'multivoice/manifest.json').read_text())['clips']
    clips=[dict(c,path=root/'multivoice'/c['file']) for c in clips]
    clips += [dict(c,path=root/'confusers'/c['file']) for c in json.loads((root/'confusers/manifest.json').read_text())['clips']]
    for f,target in [('hey-brain-vincent-slow.mp3','hey-brain'),('hey-kai-vincent.mp3','hey-kai'),('okay-kai-vincent.mp3','okay-kai'),('hey-guy-vincent.mp3',None),('okay-karl-vincent.mp3',None),('kai-later-vincent.mp3',None)]:
        clips.append(dict(file=f,path=root/f,target=target,ambiguous=False,voice='vincent'))
    policies=[(.8,.9),(.8,.8),(.8,.7),(.8,.5),(.7,.7),(.5,.5)]
    original=wake_phrase.is_activation
    segments=[]
    def inspect(result,phrase):
        nonlocal segments
        metrics=candidate_metrics(result,phrase)
        if result.get('text'):segments.append(metrics)
        return original(result,phrase)
    rows=[];start=time.monotonic()
    with patch.object(wake_phrase, 'is_activation', inspect):
        for clip in clips:
            for gain in [1,.03]:
                pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(clip['path']),'-af',f'volume={gain}','-ar','16000','-ac','1','-f','s16le','-'])
                for phrase in wake_phrase.PHRASES:
                    for repeat in [1,2]:
                        segments=[];d=wake_phrase.PhraseDetector(phrase);found=0
                        stream=bytes(64000)+(pcm+bytes(32000))*repeat+bytes(64000)
                        for i in range(0,len(stream),1600):found+=bool(d.feed(stream[i:i+1600]))
                        counts={}
                        for first,second in policies:
                            counts[f'{first}/{second}']=sum(any(m.get('first_confidence',-1)>=first and m.get('second_confidence',-1)>=second and .25<=m.get('duration_seconds',0)<=2.5 and not set(m['reasons']).intersection({'text_mismatch','invalid_numeric_result'}) for m in segment) for segment in segments)
                        a,b=wake_phrase.confidence_thresholds(phrase)
                        assert counts[f'{a}/{b}']==found
                        rows.append(dict(file=clip['file'],voice=clip['voice'],phrase=phrase,gain=gain,repeat=repeat,target=clip['target'],ambiguous=clip['ambiguous'],expected=repeat if clip['target']==phrase else 0,actual=found,threshold_counts=counts,candidates=[m for s in segments for m in s],nonempty_segments=len(segments)))
            print(json.dumps({'completed':clip['file'],'cases':len(rows)}),flush=True)
    report=dict(vosk_version=importlib.metadata.version('vosk'),synthetic_files_only=True,real_microphone=False,production_changed=False,model=wake_phrase.model_path().name,seconds=round(time.monotonic()-start,2),fixtures={c['file']:hashlib.sha256(c['path'].read_bytes()).hexdigest() for c in clips},policies=policies,cases=rows)
    out=output;out.write_text(json.dumps(report,indent=2)+'\n')
    for phrase in wake_phrase.PHRASES:
        for first,second in policies:
            key=f'{first}/{second}';positive=[r for r in rows if r['phrase']==phrase and r['expected'] and not r['ambiguous']];negative=[r for r in rows if r['phrase']==phrase and not r['expected'] and not r['ambiguous']]
            print(json.dumps({'phrase':phrase,'policy':key,'positive_exact':sum(r['threshold_counts'][key]==r['expected'] for r in positive),'positive_cases':len(positive),'false_positive_cases':sum(r['threshold_counts'][key]>0 for r in negative),'negative_cases':len(negative)}))


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
