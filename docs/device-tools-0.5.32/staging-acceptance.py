"""Staging acceptance: real CDB/WebRTC/tools, synthetic PCM, isolated Pi storage."""
import sys,os,json,shutil,time,subprocess,threading,urllib.request
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,'/home/chris/recorder-059-code')
from scripts.studio_preview import create_preview
from web_server import StudioServer
from services.live_audio import NativeLiveAudio
from services.live_conversation import BASE
from services.schedules import Schedules
production=json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/state'))
assert not production['recording']['id'] and not production['live']['busy'], 'Production audio is in use'
root=Path('/home/chris/device032-live-test-'+datetime.now().strftime('%H%M%S'));root.mkdir(mode=0o700)
app=create_preview(root,delay=1);app.ambient_stop.set();app.ambient_thread.join(3)
assert subprocess.check_output(['timedatectl','show','-p','NTPSynchronized','--value'],text=True).strip()=='yes'
app.clock_ready=True  # The isolated test stops the ambient clock poll; use verified host NTP.
original=Path('/home/chris/.local/share/cdb-recorder-local/cdb')
result={'tested_at':datetime.now(ZoneInfo('Europe/Berlin')).isoformat(),'tqs_merge':'e15980a3aa2610e465fb6081856a06d5fa402264','synthetic_audio':True,'room_audio':False,'server':'https://staging.cdbos.de','commands':[],'stages':[]}
(root/'capture.py').write_text('''import sys,time
from pathlib import Path
root=Path(sys.argv[1]);index=1;audio=b''
while True:
 if not audio and (root/f'play-{index}.pcm').exists():
  audio=(root/f'play-{index}.pcm').read_bytes();index+=1
 chunk,audio=audio[:640],audio[640:]
 sys.stdout.buffer.write(chunk.ljust(640,b'\\0'));sys.stdout.buffer.flush();time.sleep(.02)
''')
config={'device':'synthetic','speaker':'synthetic','microphone_label':'Synthetischer Sprachtest','speaker_label':'Testausgang ohne Raumwiedergabe'}
app.live_audio_config=lambda:config;app.live.audio_config=lambda:config
app.live.audio_factory=lambda config,failed:NativeLiveAudio(config,failed,capture_command=[sys.executable,str(root/'capture.py'),str(root)],playback_command=[sys.executable,'-c','import sys\nwhile sys.stdin.buffer.read(960):pass'])
original_executor=app.live.device_executor
started=time.monotonic()
last_tool_assistant=[]
def execute(scope,request):
 global last_tool_assistant
 last_tool_assistant=[h['text'] for h in app.live.public()['history'] if h['role']=='assistant']
 answer=original_executor(scope,request)
 item={'at_seconds':round(time.monotonic()-started,2),'name':request['name'],'arguments':request['arguments'],'result':answer}
 result['commands'].append(item)
 print(json.dumps({'tool':item},ensure_ascii=False),flush=True)
 return answer
app.live.device_executor=execute
original_frame=app.live._frame
original_call=app.cdb.call
original_end=app.live.end
def observed_frame(generation,event,data):
 if event=='closed':
  detail={k:data[k] for k in ('reason','state') if k in data}
  result.setdefault('lifecycle',[]).append({'event':'closed','detail':detail,'at_seconds':round(time.monotonic()-started,2)})
  print(json.dumps({'closed':detail}),flush=True)
 return original_frame(generation,event,data)
def observed_call(path,*args,**kwargs):
 try:return original_call(path,*args,**kwargs)
 except Exception as error:
  result.setdefault('transport_errors',[]).append({'route':path.rsplit('/',1)[-1],'type':type(error).__name__,'status':getattr(error,'code',None),'at_seconds':round(time.monotonic()-started,2)})
  print(json.dumps({'transport_error':result['transport_errors'][-1]}),flush=True)
  raise
def observed_end(*args,**kwargs):
 import inspect
 result.setdefault('lifecycle',[]).append({'event':'local_end','caller':inspect.stack()[1].function,'at_seconds':round(time.monotonic()-started,2),'deadline_remaining':round(app.live.deadline-app.live.clock(),2),'maximum_remaining':round(app.live.maximum-app.live.clock(),2)})
 print(json.dumps({'local_end':result['lifecycle'][-1]}),flush=True)
 return original_end(*args,**kwargs)
app.live._frame=observed_frame;app.cdb.call=observed_call;app.live.end=observed_end
server=None;index=0
def wait_for(check,timeout=100,clarification=None):
 confirmed=False
 wait_started=time.monotonic()
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  app.schedules.tick(True)
  state=app.live.public()
  if state['state'] in ('error','ended'):raise RuntimeError('Session '+state['state']+': '+state['error'])
  if check():return
  if clarification and not confirmed and time.monotonic()-wait_started>25:
   last=state['history'][-1] if state['history'] else {}
   if last.get('role')=='assistant' and ('?' in last.get('text','') or 'bestätig' in last.get('text','').lower()):
    speak(clarification);confirmed=True
  time.sleep(.5)
 raise AssertionError('Timeout: '+str({'state':app.live.public()['state'],'history':app.live.public()['history'],'items':app.schedules.items()}))
def speak(text):
 global index
 index+=1
 subprocess.run(['espeak-ng','-v','de','-s','135','-w',str(root/'source.wav'),text],check=True)
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(root/'source.wav'),'-ar','16000','-ac','1','-f','s16le',str(root/'next.pcm')],check=True)
 (root/'next.pcm').replace(root/f'play-{index}.pcm')
 result['stages'].append({'spoken':text,'at_seconds':round(time.monotonic()-started,2)})
 print(json.dumps({'spoken':text},ensure_ascii=False),flush=True)
def settled():
 deadline=time.monotonic()+60
 signature=None;stable=time.monotonic()
 while time.monotonic()<deadline:
  app.schedules.tick(True)
  state=app.live.public()
  current=[h['text'] for h in state['history'] if h['role']=='assistant']
  if current!=signature:signature=current;stable=time.monotonic()
  if current!=last_tool_assistant and time.monotonic()-stable>=4 and not state['feedback']['output']['active']:
   result.setdefault('completed_replies',[]).append({'at_seconds':round(time.monotonic()-started,2),'after_tool':result['commands'][-1]['name'],'text':current[-1]})
   print(json.dumps({'reply_completed':current[-1]},ensure_ascii=False),flush=True)
   return
  if state['state'] in ('error','ended'):raise RuntimeError('Session '+state['state']+': '+state['error'])
  time.sleep(.5)
 raise AssertionError('No completed assistant reply after '+result['commands'][-1]['name'])
def tool_done(name,since):return any(c['name']==name and c['result'].get('ok') for c in result['commands'][since:])
try:
 for name in ('session.json','config.json','destination.json'):
  shutil.copy2(original/name,app.cdb.root/name);os.chmod(app.cdb.root/name,0o600)
 assert app.cdb.config()['server']==result['server']
 caps=app.cdb.call(BASE+'/capabilities',binding=app.live._binding())
 assert caps.get('device_tools_v1') is True, 'Staging capability is not deployed yet'
 setup=app.live.setup();areas=[a['id'] for a in setup['areas'] if a.get('name')=='staging_playground' or a.get('label')=='staging_playground']
 if not areas:
  dest=setup.get('default_area') or {};assert 'staging_playground' in str(dest);areas=[dest['id']]
 app.live.remember_areas(areas[:1],setup['selection_account_key'])
 server=StudioServer(('127.0.0.1',8099),app);threading.Thread(target=server.serve_forever,daemon=True).start()
 app.wake.runtime=True;app.wake.configure(True,app.wake_account())
 with app.control_lock,app.controller.lock,app.engine.recorder.lock:app.wake_start()
 wait_for(lambda:app.live.public()['state']=='listening',45);time.sleep(6)
 assert app.live.public()['device_tools']
 assert not app.capabilities()['record']['allowed'];assert not app.capabilities()['configure']['allowed']
 result['blocked_during_live']=True
 speak('Stelle bitte einen Timer mit dem Namen Test Tee und dem Ton Klangspiel auf sechzig Sekunden.')
 wait_for(lambda:tool_done('create_timer',0));settled()
 timer=next(i for i in app.schedules.items() if i['kind']=='timer');assert timer['tone']=='chime', 'Requested chime but received '+timer['tone']
 tomorrow=datetime.now(ZoneInfo('Europe/Berlin'))+timedelta(days=1)
 # German explicit numeric date avoids reliance on the model clock.
 months=['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
 year='zweitausendsechsundzwanzig' if tomorrow.year==2026 else str(tomorrow.year)
 date=f'{tomorrow.day}. {months[tomorrow.month-1]} {year}'
 since=len(result['commands'])
 speak(f'Erstelle außerdem eine Erinnerung mit dem Namen Test Blumen, am {date} um elf Uhr dreißig, Zeitzone Europa Berlin. Als Ton bitte Glocke.')
 wait_for(lambda:tool_done('create_reminder',since),clarification=f'Ja, bitte erstelle Test Blumen am {date} um elf Uhr dreißig in Europa Berlin mit dem Ton Glocke.');settled()
 reminder=next(i for i in app.schedules.items() if i['kind']=='reminder');assert reminder['tone']=='bell'
 expected=tomorrow.replace(hour=11,minute=30,second=0,microsecond=0).timestamp();assert abs(reminder['due']-expected)<1
 since=len(result['commands']);speak('Welche Timer und Erinnerungen sind gerade auf diesem Gerät vorhanden? Bitte prüfe die aktuelle Liste.')
 wait_for(lambda:tool_done('list_schedules',since));settled()
 wait_for(lambda:any(i['id']==timer['id'] and i['state']=='due' for i in app.schedules.items()),90)
 since=len(result['commands']);speak('Bitte bestätige den abgelaufenen Alarm Test Tee als erledigt. Ich brauche diesen Timer nicht mehr.')
 wait_for(lambda:tool_done('acknowledge_alarm',since));settled()
 since=len(result['commands']);speak('Lösche jetzt bitte die Erinnerung Test Blumen, damit sie morgen nicht mehr ausgelöst wird.')
 wait_for(lambda:tool_done('cancel_schedule',since));settled()
 result['history']=app.live.public()['history'];result['items']=app.schedules.items()
 assert any(i['id']==timer['id'] and i['state']=='done' for i in result['items'])
 assert any(i['id']==reminder['id'] and i['state']=='cancelled' for i in result['items'])
 reopened=Schedules(app.schedules.path.parent)
 assert reopened.items()==app.schedules.items()
 result['durable_after_reopen']=True
 app.action('/api/live/end',{});app.live.finished.wait(10)
 result['released']=not app.live.busy();result['capabilities_after']=app.capabilities()
 after=json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/state'))
 assert [r['id'] for r in after['sessions']]==[r['id'] for r in production['sessions']]
 assert after['config']==production['config'] and after['timers']==production['timers']
 result['production_unchanged']={'recordings':len(after['sessions']),'config':True,'timers':True}
 assert result['released'];assert app.capabilities()['configure']['allowed'];assert app.capabilities()['record']['allowed']
 result['passed']=True
 (root/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('ACCEPTANCE_PASSED',flush=True)
 time.sleep(60)  # Leave the finished UI available briefly for visual acceptance.
except Exception as error:
 result['passed']=False;result['error']=str(error);result['history']=app.live.public()['history'];result['items']=app.schedules.items()
 print(json.dumps({'failure':str(error)},ensure_ascii=False),flush=True)
finally:
 result['seconds']=round(time.monotonic()-started,2)
 (root/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 Path('/tmp/device032-last-result-path').write_text(str(root/'result.json'))
 print('RESULT_PATH '+str(root/'result.json'),flush=True)
 app.live.end();app.live.finished.wait(10)
 if server:server.shutdown();server.server_close()
 app.wake.configure(False,None);app.close();(app.cdb.root/'session.json').unlink(missing_ok=True)
 sys.exit(0 if result.get('passed') else 1)
