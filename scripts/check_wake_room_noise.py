"""Reproducible, hardware-free low-noise wake comparison using synthetic speech.

An optional historical source file supplies the baseline. Reports every miss;
no microphone, speaker, network or production settings are touched.
"""
import argparse
from array import array
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import time
from services.wake_phrase import PhraseDetector


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-source',type=Path)
    p.add_argument('--minutes',type=float,default=2)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if not .1<=args.minutes<=20:p.error('Use 0.1–20 audio minutes per case.')
    fixture=Path(__file__).resolve().parents[1]/'tests/fixtures/wake/hey-brain-vincent-slow.mp3'
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(fixture),'-af','adelay=2000,apad=pad_dur=1',
                                 '-ar','16000','-ac','1','-f','s16le','pipe:1'])
    target=array('h',raw)
    classes=[]
    if args.baseline_source:
        spec=importlib.util.spec_from_file_location('historical_wake',args.baseline_source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        classes.append(('baseline',module.PhraseDetector))
    classes.append(('candidate',PhraseDetector))
    random.seed(42);rows=[]
    for std in (0,4,16,64):
        noise=[array('h',[round(random.gauss(0,std)) for _ in range(800)]) for _ in range(40)]
        for label,cls in classes:
            for scale in (1,.03,.003):
                detector=cls();start=time.process_time();false_wakes=0;hits=[]
                for i in range(round(args.minutes*1200)):
                    false_wakes+=bool(detector.feed(noise[i%40].tobytes()))
                for offset in range(0,len(target)+96000,800):
                    values=target[offset:offset+800];values.extend([0]*(800-len(values)))
                    pcm=array('h',[max(-32768,min(32767,round(v*scale)+n))
                                   for v,n in zip(values,noise[(offset//800)%40])]).tobytes()
                    if detector.feed(pcm):hits.append((offset+800)/16000)
                row={'source':label,'noise_std_pcm':std,'scale':scale,'idle_audio_minutes':args.minutes,
                     'false_wakes':false_wakes,'target_detections':len(hits),'target_audio_seconds':hits,
                     'onset_renewals':getattr(getattr(detector,'onset',None),'renewals',0),
                     'cpu_seconds':round(time.process_time()-start,3)}
                rows.append(row);print(json.dumps(row),flush=True)
    report={'synthetic_audio':True,'accelerated_not_wall_clock':True,
            'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
            'candidate_source_sha256':hashlib.sha256(Path(__import__('services.wake_phrase',fromlist=['x']).__file__).read_bytes()).hexdigest(),
            'baseline_source_sha256':hashlib.sha256(args.baseline_source.read_bytes()).hexdigest() if args.baseline_source else None,
            'cases':rows}
    args.output.write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
