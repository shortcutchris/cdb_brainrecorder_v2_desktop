"""Bounded file-only wake comparison. Lab environments only; never opens audio devices."""
import argparse,json,time,wave,hashlib,platform,resource
from importlib.metadata import version
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--engine',choices=['micro','sherpa','open','micro-v2'],required=True);p.add_argument('--output',required=True)
p.add_argument('--references',type=Path,required=True)
p.add_argument('--german',type=Path,required=True)
p.add_argument('--sherpa-models',type=Path)
p.add_argument('--micro-config',type=Path)
p.add_argument('--tflite-library',type=Path)
a=p.parse_args()
root=a.sherpa_models
if a.engine=='sherpa' and root is None:p.error('--sherpa-models required')
if a.engine=='micro-v2' and a.micro_config is None:p.error('--micro-config required')
if a.engine=='sherpa':
 import sherpa_onnx
 keys=root/'cdb-keywords.txt';keys.write_text('OW2 K EY1 N AA1 B UW1 @OKAY_NABU\n')
 kw=sherpa_onnx.KeywordSpotter(tokens=str(root/'tokens.txt'),encoder=str(root/'encoder-epoch-13-avg-2-chunk-16-left-64.int8.onnx'),decoder=str(root/'decoder-epoch-13-avg-2-chunk-16-left-64.onnx'),joiner=str(root/'joiner-epoch-13-avg-2-chunk-16-left-64.int8.onnx'),keywords_file=str(keys),num_threads=1)
elif a.engine=='open':
 from pyopen_wakeword import OpenWakeWord, OpenWakeWordFeatures, Model
else:
 from services.wake_detectors import create_detector
files=[(p, p.parent.name=='okay_nabu') for kind in ['okay_nabu','alexa','hey_jarvis','hey_mycroft'] for p in sorted((a.references/kind).glob('*.wav'))]
files +=[(p,p.name=='positive.wav') for p in sorted(a.german.glob('*/*.wav'))]
files=[(path,expected) for path,expected in files if not path.name.startswith('._')]
if not 1 <= len(files) <= 64:raise ValueError('Use 1–64 known test files')
rows=[]
for path,expected in files:
 if path.name.startswith('._'):continue
 with wave.open(str(path)) as f:
  assert (f.getframerate(),f.getsampwidth(),f.getnchannels())==(16000,2,1)
  if f.getnframes()>16000*60:raise ValueError('At most 60 seconds per known test file')
  raw=f.readframes(f.getnframes())
 for gain,noise in [(1.,0.),(.25,0.),(.25,.002)]:
  x=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768*gain
  if noise:x=x+np.random.default_rng(743).normal(0,noise,len(x))
  x=np.concatenate([np.zeros(16000,dtype=np.float32),x,np.zeros(32000,dtype=np.float32)]).astype(np.float32)
  hits=[];probs=[];cpu=time.process_time()
  if a.engine=='sherpa':
   stream=kw.create_stream()
   for i in range(0,len(x),800):
    stream.accept_waveform(16000,x[i:i+800])
    while kw.is_ready(stream):
     kw.decode_stream(stream)
     if kw.get_result(stream):hits.append(round((i+800)/16000,3));kw.reset_stream(stream)
  elif a.engine=='open':
   lib=a.tflite_library
   d=OpenWakeWord.from_builtin(Model.OKAY_NABU,libtensorflowlite_c_path=lib);features=OpenWakeWordFeatures.from_builtin(libtensorflowlite_c_path=lib)
   pcm=(np.clip(x,-1,32767/32768)*32768).astype('<i2').tobytes();pcm+=bytes((-len(pcm))%320)
   for i in range(0,len(pcm),320):
    for f in features.process_streaming(pcm[i:i+320]):
     for probability in d.process_streaming(f):
      probs.append(float(probability))
      if probability>.5:hits.append(round((i+320)/32000,3))
   d.close();features.close()
  else:
   d=create_detector('okay-nabu')
   if a.engine=='micro-v2':
    from pymicro_wakeword import MicroWakeWord
    d.model.close();d.model=MicroWakeWord.from_config(a.micro_config)
    d.probability_cutoff=d.model.probability_cutoff
   old=d.model.process_streaming_prob
   def measured(features):
    v=old(features)
    if v is not None:probs.append(float(v))
    return v
   d.model.process_streaming_prob=measured
   pcm=(np.clip(x,-1,32767/32768)*32768).astype('<i2').tobytes();pcm+=bytes((-len(pcm))%1600)
   for i in range(0,len(pcm),1600):
    if d.feed(pcm[i:i+1600]):hits.append(round((i+1600)/32000,3))
   d.model.close()
  rows.append(dict(file='/'.join(path.parts[-2:]),sha256=hashlib.sha256(raw).hexdigest(),expected=expected,gain=gain,noise_std=noise,detected=bool(hits),hit_frames=len(hits),first_hit_seconds=hits[0] if hits else None,max_probability=max(probs) if probs else None,cpu_seconds=round(time.process_time()-cpu,4),audio_seconds=len(x)/16000))
result=dict(engine=a.engine,runtime_version=version({'micro':'pymicro-wakeword','micro-v2':'pymicro-wakeword','sherpa':'sherpa-onnx','open':'pyopen-wakeword'}[a.engine]),host=platform.machine(),cases=rows,positive_detected=sum(r['detected'] for r in rows if r['expected']),positive_total=sum(r['expected'] for r in rows),false_positives=sum(r['detected'] for r in rows if not r['expected']),negative_total=sum(not r['expected'] for r in rows),cpu_seconds=round(sum(r['cpu_seconds'] for r in rows),3),audio_seconds=sum(r['audio_seconds'] for r in rows),microphone=False,speaker=False)
Path(a.output).write_text(json.dumps(result,indent=2)); print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
