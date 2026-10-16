"""Fixed 2026-10-16 lab reproduction, not installed app code.
Known synthetic inputs only; use a process timeout. No microphone or network.
"""
import subprocess,json,time,pathlib,hashlib,wave,re,tempfile
import numpy as np
binary='/opt/meeting-recorder/whisper.cpp/build/bin/whisper-cli'
model='/tmp/cdb-whisper-verifier/ggml-tiny.bin'
files=[]
for kind in ['okay_nabu','alexa','hey_jarvis','hey_mycroft']:
 for i in [1,2,3]:files.append((pathlib.Path('/tmp/cdb-nabu-reference-059/tests')/kind/f'{i}.wav',kind=='okay_nabu'))
for path,expected in [('/tmp/cdb-nabu-german/vincent/positive.wav',True),('/tmp/cdb-nabu-german/pauli/positive.wav',True),('/tmp/cdb-nabu-holdout/otto-pos/positive.wav',True),('/tmp/cdb-nabu-holdout/ben-pos/positive.wav',True),('/tmp/cdb-nabu-german/confuser.wav',False),('/tmp/cdb-nabu-holdout/otto-neg/negative.wav',False),('/tmp/cdb-nabu-holdout/ben-neg/negative.wav',False)]:files.append((pathlib.Path(path),expected))
rows=[]
with tempfile.TemporaryDirectory(prefix='cdb-synthetic-wake-') as temp:
 for path,expected in files:
  with wave.open(str(path)) as w:
   assert (w.getframerate(),w.getsampwidth(),w.getnchannels())==(16000,2,1)
   total=w.getnframes();raw=w.readframes(min(total,76800))
  for gain,noise in [(1.,0.),(.25,0.),(.25,.002)]:
   x=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768*gain
   if noise:x=x+np.random.default_rng(743).normal(0,noise,len(x))
   pcm=(np.clip(x,-1,32767/32768)*32768).astype('<i2').tobytes()
   wav=pathlib.Path(temp)/'synthetic.wav'
   with wave.open(str(wav),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)
   start=time.monotonic()
   cmd=[binary,'-m',model,'-f',str(wav),'-l','de','-t','2','-bo','1','-bs','1','-nf','-nt','-np','-ac','256','--prompt','Nabu.']
   try:
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
    transcript=r.stdout.strip();words=re.findall(r'[^\W\d_]+',transcript.lower())
    found=len(words)>=2 and words[0] in ('okay','ok') and words[1]=='nabu' and r.returncode==0
    row=dict(file='/'.join(path.parts[-2:]),expected=expected,gain=gain,noise_std=noise,source_pcm_sha256=hashlib.sha256(raw).hexdigest(),truncated=total>76800,audio_seconds=len(pcm)/32000,wall_seconds=time.monotonic()-start,returncode=r.returncode,detected=found,synthetic_transcript=transcript,error=r.stderr[-500:])
   except subprocess.TimeoutExpired:
    row=dict(file='/'.join(path.parts[-2:]),expected=expected,gain=gain,noise_std=noise,wall_seconds=time.monotonic()-start,result='timeout',detected=False)
   rows.append(row)
report=dict(model='whisper-tiny-multilingual',audio_context=256,model_sha256=hashlib.sha256(pathlib.Path(model).read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),greedy=True,initial_prompt='Nabu.',threads=2,synthetic_files_only=True,microphone=False,speaker=False,decision='first two normalized words exactly okay/ok and nabu',positive_detected=sum(r['detected'] for r in rows if r['expected']),positive_total=sum(r['expected'] for r in rows),false_positives=sum(r['detected'] for r in rows if not r['expected']),negative_total=sum(not r['expected'] for r in rows),timeouts=sum(r.get('result')=='timeout' for r in rows),cases=rows)
pathlib.Path('/tmp/cdb-whisper-matrix.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)
