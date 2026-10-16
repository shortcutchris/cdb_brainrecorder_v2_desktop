import hashlib,json,sys,time,wave,resource
from pathlib import Path
from importlib.metadata import version
from services.wake_detectors import create_detector
import argparse
parser=argparse.ArgumentParser(description='File-only Okay Nabu regression on Pi; no microphone or speaker.')
parser.add_argument('--references',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
base=args.references
rows=[]
def frames(path):
 with wave.open(str(path)) as f:
  assert (f.getframerate(),f.getsampwidth(),f.getnchannels())==(16000,2,1)
  data=f.readframes(f.getnframes())
 data+=bytes((-len(data))%1600)+bytes(32000)
 return [data[i:i+1600] for i in range(0,len(data),1600)]
for kind in ['okay_nabu','alexa','hey_jarvis','hey_mycroft']:
 for path in sorted((base/kind).glob('*.wav')):
  if path.name.startswith('._'):continue  # macOS archive metadata is not audio.
  d=create_detector('okay-nabu');found=False;start=time.process_time()
  for frame in frames(path):found=d.feed(frame) or found
  rows.append({'file':kind+'/'+path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'expected':kind=='okay_nabu','detected':found,'cpu_seconds':round(time.process_time()-start,4)})
# Production retires the detector on first accepted block; mimic repeated ownership cycles.
cycles=[]
for i in range(100):
 d=create_detector('okay-nabu');hits=0
 for frame in frames(base/'okay_nabu'/f'{1+i%3}.wav'):
  if d.feed(frame):hits+=1;break
 cycles.append(hits)
# Continuous digital silence followed by a wake, accelerated (not real idle time).
d=create_detector('okay-nabu');silence_hits=0;start=time.process_time()
for _ in range(1200*10):silence_hits+=bool(d.feed(bytes(1600)))
after_idle=any(d.feed(frame) for frame in frames(base/'okay_nabu/1.wav'))
result={'reference_commit':'333da550c54b95192af472cfe37d98dab2f2086e','pymicro_wakeword':version('pymicro-wakeword'),'pymicro_features':version('pymicro-features'),'files':rows,'positive_passed':sum(r['detected'] for r in rows if r['expected']),'negative_false_hits':sum(r['detected'] for r in rows if not r['expected']),'cycles':len(cycles),'cycles_passed':sum(n==1 for n in cycles),'synthetic_silence_seconds':600,'silence_false_hits':silence_hits,'wake_after_silence':after_idle,'silence_cpu_seconds':round(time.process_time()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'microphone_used':False,'speaker_used':False}
args.output.write_text(json.dumps(result,indent=2))
print(json.dumps(result));assert result['positive_passed']==3 and result['negative_false_hits']==0 and result['cycles_passed']==100 and not silence_hits and after_idle
