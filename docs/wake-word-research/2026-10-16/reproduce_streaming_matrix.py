"""Bounded real-time synthetic-file experiment; never owns a microphone.
Run only in the isolated Pi lab with explicit timeout 120.
"""
import sys,time,wave,json,pathlib,hashlib
import numpy as np
from services.wake_detectors import create_detector
from wake_streaming_probe import AsyncVerifier,StreamingCandidate
cases=[('/tmp/cdb-nabu-holdout/otto-pos/positive.wav',True,1,0),('/tmp/cdb-nabu-holdout/ben-pos/positive.wav',True,1,0),('/tmp/cdb-nabu-german/vincent/positive.wav',True,.25,.002),('/tmp/cdb-nabu-german/pauli/positive.wav',True,.25,.002),('/tmp/cdb-nabu-german/confuser.wav',False,1,0),('/tmp/cdb-nabu-holdout/otto-neg/negative.wav',False,.25,.002)]
rows=[]
for name,expected,gain,noise in cases:
 with wave.open(name) as f:
  assert (f.getframerate(),f.getsampwidth(),f.getnchannels())==(16000,2,1)
  raw=f.readframes(min(f.getnframes(),76800))
 x=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768*gain
 if noise:x+=np.random.default_rng(743).normal(0,noise,len(x))
 pcm=bytes(64000)+(np.clip(x,-1,32767/32768)*32768).astype('<i2').tobytes()+bytes(192000)
 pcm+=bytes((-len(pcm))%1600)
 d=create_detector('okay-nabu');v=AsyncVerifier('/opt/meeting-recorder/whisper.cpp/build/bin/whisper-cli','/tmp/cdb-whisper-verifier/ggml-tiny.bin');s=StreamingCandidate(d,v)
 row=dict(file='/'.join(pathlib.Path(name).parts[-2:]),expected=expected,gain=gain,noise_std=noise,source_pcm_sha256=hashlib.sha256(raw).hexdigest(),audio_seconds=len(pcm)/32000,events=[],detections=0,primary_max=0,feed_max_seconds=0)
 begin=time.monotonic()
 try:
  for i in range(0,len(pcm),1600):
   old=s.state;at=time.monotonic();hit=s.feed(pcm[i:i+1600]);elapsed=time.monotonic()-at
   row['feed_max_seconds']=max(row['feed_max_seconds'],elapsed);row['detections']+=int(hit);row['primary_max']=max(row['primary_max'],s.last_probability or 0.)
   if old!=s.state:row['events'].append(dict(audio_seconds=(i+1600)/32000,wall_seconds=time.monotonic()-begin,state=s.state))
   time.sleep(max(0,begin+(i+1600)/32000-time.monotonic()))
  row.update(submitted=s.submitted,rejected=s.rejected,last_report=s.last_report,wall_seconds=time.monotonic()-begin,passed=(row['detections']==int(expected)))
 finally:s.close();d.model.close()
 rows.append(row);print(json.dumps(row),flush=True)
pathlib.Path('/tmp/cdb-stream-matrix.json').write_text(json.dumps(dict(microphone=False,speaker=False,real_time_file_stream=True,production_integration=False,candidate_threshold=.15,tail_seconds=.8,lookback_seconds=2,positive_passed=sum(r['passed'] for r in rows if r['expected']),negative_passed=sum(r['passed'] for r in rows if not r['expected']),cases=rows),indent=2))
