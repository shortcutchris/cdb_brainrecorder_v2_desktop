"""Frozen Base-verifier holdout: complete real-time file streams, no device audio."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import time
import wave

from services.wake_detectors import create_detector
from wake_streaming_probe import AsyncVerifier, StreamingCandidate
from wake_whisper_probe import matches_nabu, matches_nabu_joined


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--voices', nargs='+', default=['charlie','hl'])
    parser.add_argument('--joined-spelling',action='store_true',help='Experimental exact joined spelling; prior reports keep original rule')
    args=parser.parse_args()
    if not all(re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',v) for v in args.voices): parser.error('Invalid fixture label')
    assert hashlib.sha256(args.model.read_bytes()).hexdigest()=='60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe'
    rows=[];started_epoch=time.time()
    for voice in args.voices:
        for kind in ('single','double','negative'):
            path=args.fixtures/(voice+('-negative.wav' if kind=='negative' else '-positive.wav'))
            with wave.open(str(path)) as source:
                assert (source.getframerate(),source.getnchannels(),source.getsampwidth())==(16000,1,2)
                assert 0<source.getnframes()<=160000
                raw=source.readframes(source.getnframes())
            # Five seconds separate repeated calls. Acceptance stays latched;
            # a late hit only on the second call cannot pass first-call coverage.
            first_end=2+len(raw)/32000
            second_start=first_end+5 if kind=='double' else None
            pcm=bytes(64000)+raw+(bytes(160000)+raw if kind=='double' else b'')+bytes(256000)
            pcm+=bytes((-len(pcm))%1600)
            detector=create_detector('okay-nabu')
            verifier=AsyncVerifier(args.binary,args.model,matcher=matches_nabu_joined if args.joined_spelling else matches_nabu)
            stream=StreamingCandidate(detector,verifier)
            row={'voice':voice,'kind':kind,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'audio_seconds':len(pcm)/32000,'second_call_starts_at':second_start,
                 'first_call_deadline':first_end+4,
                 'detections':[],'decisions':[],'feed_max_seconds':0.,'primary_max':0.}
            started=time.monotonic()
            try:
                for offset in range(0,len(pcm),1600):
                    at=time.monotonic();hit=stream.feed(pcm[offset:offset+1600]);elapsed=time.monotonic()-at
                    seconds=(offset+1600)/32000
                    row['feed_max_seconds']=max(row['feed_max_seconds'],elapsed)
                    row['primary_max']=max(row['primary_max'],stream.last_probability or 0.)
                    if hit:row['detections'].append(seconds)
                    if stream.last_decision:
                        row['decisions'].append({'audio_seconds':seconds,'decision':stream.last_decision,'report':stream.last_report})
                    time.sleep(max(0,started+seconds-time.monotonic()))
                row.update(submitted=stream.submitted,rejected=stream.rejected,state=stream.state,
                           wall_seconds=time.monotonic()-started,
                           pending_at_end=stream.state in ('tail','verifying'))
                hits=row['detections']
                row['passed']=(not hits if kind=='negative' else len(hits)==1 and hits[0]<=first_end+4 and
                               (second_start is None or hits[0]<second_start)) and not row['pending_at_end']
            finally:
                stream.close();detector.model.close()
            row['verifier_released']=verifier.process is None and verifier.descriptor is None
            row['passed']=row['passed'] and row['verifier_released']
            rows.append(row);print(json.dumps(row),flush=True)
    report={'microphone':False,'speaker':False,'cloud':False,'production_integration':False,
            'matcher':'exact_joined_v2' if args.joined_spelling else 'two_words_v1',
            'started_epoch':started_epoch,'finished_epoch':time.time(),
            'real_time_file_stream':True,'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
            'binary_sha256':hashlib.sha256(args.binary.read_bytes()).hexdigest(),
            'candidate_threshold':.15,'tail_seconds':.8,'lookback_seconds':2,
            'passed':sum(r['passed'] for r in rows),'cases':rows}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if all(r['passed'] for r in rows) else 2


if __name__=='__main__':raise SystemExit(main())
