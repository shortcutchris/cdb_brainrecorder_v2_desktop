from pathlib import Path
import json,subprocess,time,urllib.request,os
root=Path('/home/chris/.local/share/cdb-diagnostics/perf-1792104938');pid=806009
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def identity():
 s=Path(f'/proc/{pid}/stat').read_text();f=s[s.rindex(')')+2:].split();return {'pid':pid,'start_ticks':int(f[19]),'user_ticks':int(f[11]),'system_ticks':int(f[12])}
def guard():
 with opener.open('http://127.0.0.1:8088/api/state',timeout=3) as r:s=json.load(r)
 return {'at_epoch':time.time(),'idle':not s.get('activity',{}).get('busy',True) and not s['recording'].get('id') and not s.get('live',{}).get('busy') and not s.get('timers',{}).get('ringing')}
before=identity();assert before['start_ticks']==8935764
checks=[guard()];assert checks[0]['idle']
(root/'maps-before.txt').write_text(Path(f'/proc/{pid}/maps').read_text())
result={'scope':'10-second user-space CPU-clock sample of existing production renderer main thread; no restart, audio or payload capture','before':before,'started_at_epoch':time.time(),'guards':checks,'source':'sample.c','production_mutation':False}
with (root/'sample.json').open('w') as out,(root/'sample-errors.txt').open('w') as err:
 proc=subprocess.Popen([str(root/'sample'),str(pid)],stdout=out,stderr=err,preexec_fn=lambda:os.nice(15))
 try:
  deadline=time.monotonic()+15
  while proc.poll() is None:
   if time.monotonic()>deadline:raise TimeoutError('Bounded sampling exceeded')
   check=guard();checks.append(check)
   if not check['idle']:raise RuntimeError('Activity became busy; stop profiler only')
   time.sleep(.5)
 except Exception as error:
  result['error']=str(error)
 finally:
  if proc.poll() is None:
   proc.terminate()
   try:proc.wait(3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(3)
  result['sampler_exit_code']=proc.returncode
result['ended_at_epoch']=time.time();result['after']=identity();assert result['after']['start_ticks']==before['start_ticks']
(root/'maps-after.txt').write_text(Path(f'/proc/{pid}/maps').read_text())
result['target_identity_unchanged']=True
(root/'metadata.json').write_text(json.dumps(result,indent=2)+'\n')
if proc.returncode==0:
 sample=json.loads((root/'sample.json').read_text());result['samples']=len(sample['samples']);result['lost']=sample['lost'];result['parse_error']=sample['parse_error']
print(json.dumps({k:v for k,v in result.items() if k!='guards'}))
