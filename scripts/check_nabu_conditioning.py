"""Synthetic conditioning experiment; no microphone, settings or Live session.

32s versus 2s adds exactly 30s, preserving the 30ms inference stride phase.
Noise levels bracket scenarios, not measurements of the user's room.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import wave
import numpy as np
from services.wake_detectors import create_detector

KNOWN={'charlie':'69a4de7344f9b2a5c1e10aa35b0850c316e4323e6d86d9bab9205fb3e14a4ac9',
       'hl':'d0772f19f9781eef86438488ffa4cacc87660fd1c26dc43dd8e18b37da4bfdc9',
       'will':'ca1cd669324192348c145f40607f40ab2e1c80ba6f85f5f6096ad47ce07ac452',
       'sarah':'268d125bb3b722e572c716fdb5b45c7f735e460a479c1b984e2c767f557e1a85'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report={'started_epoch':time.time(),'synthetic_only':True,'real_time':False,'production_integration':False,
            'engine_version':importlib.metadata.version('pymicro-wakeword'),'seed':20261016,'cases':[]}
    for voice,expected_hash in KNOWN.items():
        path=a.fixtures/(voice+'-positive.wav');assert hashlib.sha256(path.read_bytes()).hexdigest()==expected_hash
        with wave.open(str(path)) as w:
            assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(16000,1,2)
            raw=w.readframes(w.getnframes())
        for seconds,noise_db in [(2,None),(32,None),(32,-60),(32,-40)]:
            rng=np.random.default_rng(20261016)
            if noise_db is None:pre=bytes(seconds*32000)
            else:
                noise=rng.normal(size=seconds*16000);noise*=32768*10**(noise_db/20)/np.sqrt(np.mean(noise**2));pre=np.clip(noise,-32768,32767).astype('<i2').tobytes()
            first_start=len(pre)/32000;first_end=first_start+len(raw)/32000
            second_start=first_end+5
            pcm=pre+raw+bytes(160000)+raw+bytes(96000);pcm+=bytes(-len(pcm)%1600)
            d=create_detector('okay-nabu');row={'voice':voice,'sha256':expected_hash,'prelude_seconds':seconds,'noise_rms_dbfs':noise_db,'cutoff':d.probability_cutoff,'primary_max':[0.,0.,0.],'hit_frames':[0,0,0],'first_hit':[None,None,None]}
            start=time.monotonic()
            try:
                for offset in range(0,len(pcm),1600):
                    t=(offset+1600)/32000;region=0 if t<=first_start else 1 if t<second_start else 2
                    hit=d.feed(pcm[offset:offset+1600]);row['primary_max'][region]=max(row['primary_max'][region],d.last_probability or 0.)
                    if hit:
                        row['hit_frames'][region]+=1
                        if row['first_hit'][region] is None:row['first_hit'][region]=round(t-(0 if region==0 else first_start if region==1 else second_start),4)
            finally:d.model.close()
            row['wall_seconds']=time.monotonic()-start;report['cases'].append(row);print(json.dumps(row),flush=True)
    report['finished_epoch']=time.time();a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
