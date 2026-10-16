"""Reproducible synthetic-only short-window probe, not an application component.
Known generated files only; no microphone, playback, network or user settings.
"""
import hashlib,json,pathlib,re,subprocess,tempfile,time,wave,statistics
binary='/opt/meeting-recorder/whisper.cpp/build/bin/whisper-cli'
models={'tiny':'be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21', 'base':'60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe'}
paths=[('/tmp/cdb-nabu-german/vincent/positive.wav',True),('/tmp/cdb-nabu-german/pauli/positive.wav',True),('/tmp/cdb-nabu-holdout/otto-pos/positive.wav',True),('/tmp/cdb-nabu-holdout/ben-pos/positive.wav',True),('/tmp/cdb-nabu-german/confuser.wav',False),('/tmp/cdb-nabu-holdout/otto-neg/negative.wav',False),('/tmp/cdb-nabu-holdout/ben-neg/negative.wav',False)]
for model,sha in models.items():
 assert hashlib.sha256(pathlib.Path('/tmp/cdb-whisper-verifier/ggml-'+model+'.bin').read_bytes()).hexdigest()==sha
rows=[];started=time.time()
with tempfile.TemporaryDirectory(prefix='cdb-known-synthetic-window-') as td:
 for path,expected in paths+[(None,False)]:
  if path:
   with wave.open(path) as f:
    assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
    total=f.getnframes();raw=f.readframes(min(total,32000))
  else:raw=bytes(64000);total=32000
  for before in [0.,1.6]:
   pcm=bytes(int(before*32000))+raw+bytes(6400)
   wav=pathlib.Path(td)/'known.wav'
   with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm)
   for model in models:
    for prompt in ['', 'Nabu.']:
     cmd=[binary,'-m','/tmp/cdb-whisper-verifier/ggml-'+model+'.bin','-f',str(wav),'-l','de','-t','2','-bo','1','-bs','1','-nf','-nt','-np','-ac','256']
     if prompt:cmd+=['--prompt',prompt]
     at=time.monotonic();row=dict(file='/'.join(pathlib.Path(path).parts[-2:]) if path else 'synthetic-silence',expected=expected,model=model,prompt=prompt,padding_before=before,padding_after=.2,source_pcm_sha256=hashlib.sha256(raw).hexdigest(),source_truncated=total>32000,audio_seconds=len(pcm)/32000)
     try:
      result=subprocess.run(cmd,capture_output=True,text=True,timeout=8)
      words=re.findall(r'[^\W\d_]+',result.stdout.lower())
      row.update(returncode=result.returncode,detected=result.returncode==0 and len(words)>=2 and words[0] in ('okay','ok') and words[1]=='nabu',synthetic_transcript=result.stdout.strip())
     except subprocess.TimeoutExpired:row.update(error='timeout',detected=False)
     row['wall_seconds']=round(time.monotonic()-at,4);rows.append(row)
  print(json.dumps({'completed_source':path or 'synthetic-silence','cases':len(rows)}),flush=True)
summary=[]
for model in models:
 for prompt in ['', 'Nabu.']:
  group=[r for r in rows if r['model']==model and r['prompt']==prompt]
  summary.append(dict(model=model,prompt=prompt,positive_detected=sum(r['detected'] for r in group if r['expected']),positive_total=sum(r['expected'] for r in group),negative_activated=sum(r['detected'] for r in group if not r['expected']),negative_total=sum(not r['expected'] for r in group),median_seconds=statistics.median(r['wall_seconds'] for r in group),max_seconds=max(r['wall_seconds'] for r in group),timeouts=sum(r.get('error')=='timeout' for r in group)))
report=dict(start_epoch=started,end_epoch=time.time(),microphone=False,speaker=False,synthetic_only=True,models={m:{'sha256':v} for m,v in models.items()},binary_sha256=hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),audio_context=256,decision='first two normalized words exactly okay/ok and nabu',threads=2,summary=summary,cases=rows)
pathlib.Path('/tmp/cdb-window-comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(summary),flush=True)
