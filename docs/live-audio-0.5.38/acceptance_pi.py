"""Isolated Pi acceptance: real CDB/WebRTC, synthetic microphone, virtual sink."""
import sys,os,json,shutil,time,subprocess,threading,uuid,signal
from pathlib import Path
from datetime import datetime
sys.path.insert(0,'/home/chris/recorder-059-code')
from scripts.studio_preview import create_preview
from web_server import StudioServer
from services.live_audio import NativeLiveAudio
root=Path('/home/chris/live038-test-'+datetime.now().strftime('%H%M%S'));root.mkdir(mode=0o700)
app=create_preview(root,delay=1);app.ambient_stop.set();app.ambient_thread.join(4)
app.clock_ready=True
module=subprocess.check_output(['pactl','load-module','module-null-sink','sink_name=recorder038_test'],text=True).strip()
app.speakers.public=lambda:{'available':True,'muted':False,'volume':50,'selected':'recorder038_test'}
(root/'capture.py').write_text('''import sys,time
from pathlib import Path
root=Path(sys.argv[1]);index=1;audio=b''
while True:
 if not audio and (root/f'play-{index}.pcm').exists():
  audio=(root/f'play-{index}.pcm').read_bytes();index+=1
 chunk,audio=audio[:640],audio[640:]
 sys.stdout.buffer.write(chunk.ljust(640,b'\\0'));sys.stdout.buffer.flush();time.sleep(.02)
''')
config={'device':'synthetic','speaker':'recorder038_test','microphone_label':'Synthetischer Sprachtest','speaker_label':'Isolierter Testausgang'}
app.live_audio_config=lambda:config;app.live.audio_config=lambda:config
natives=[]
def factory(config,failed):
 native=NativeLiveAudio(config,failed,capture_command=[sys.executable,str(root/'capture.py'),str(root)])
 natives.append(native);return native
app.live.audio_factory=factory
stop=threading.Event();result={'synthetic':True,'room_audio':False,'audio_destination':'isolated null sink','stages':[]}
def tick():
 while not stop.wait(.1):
  app.schedules.tick(True)
  with app.control_lock,app.controller.lock,app.engine.recorder.lock:app.tick_alarm()
threading.Thread(target=tick,daemon=True).start()
server=StudioServer(('127.0.0.1',8099),app);threading.Thread(target=server.serve_forever,daemon=True).start()
def wait(check,seconds=20):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  if check():return
  time.sleep(.1)
 raise AssertionError('Timed out '+str(app.live.public()['state']))
def stage(name,**data):
 result['stages'].append({'name':name,**data});print(json.dumps(result['stages'][-1]),flush=True)
index=0
def speak(text):
 global index
 index+=1
 subprocess.run(['espeak-ng','-v','de','-s','135','-w',str(root/'source.wav'),text],check=True)
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(root/'source.wav'),'-ar','16000','-ac','1','-f','s16le',str(root/'next.pcm')],check=True)
 (root/'next.pcm').replace(root/f'play-{index}.pcm')
 stage('synthetic_utterance',text=text)
def row(ident):return next(r for r in app.schedules.items() if r['id']==ident)
def create_timer():return app.action('/api/timers',{'action':'create','kind':'timer','seconds':1,'label':'Test · Alarm im Gespräch','request_id':str(uuid.uuid4()),'tone':'bell'})['id']
try:
 original=Path('/home/chris/.local/share/cdb-recorder-local/cdb')
 for name in ('session.json','config.json','destination.json'):
  shutil.copy2(original/name,app.cdb.root/name);os.chmod(app.cdb.root/name,0o600)
 assert app.cdb.config()['server']=='https://staging.cdbos.de'
 setup=app.live.setup();areas=[a['id'] for a in setup['areas'] if a.get('name')=='staging_playground'];assert areas
 lease=app.live.reserve(areas[:1],owner_kind='device')['lease'];app.live.start_native(lease)
 wait(lambda:natives and natives[0].stats()['ready_tone']=='played',55)
 native=natives[0];assert native.peer.connectionState=='connected'
 stage('ready_chime_after_actual_connection',state=native.peer.connectionState,ready_tone=native.stats()['ready_tone'])
 speak('Bitte zähle langsam von eins bis dreißig. Sage jede Zahl einzeln.')
 wait(lambda:native.feedback()['output']['active'],40)
 ident=create_timer();wait(lambda:app.alarm_id==ident)
 before=native.received_frames;time.sleep(3)
 inputs=json.loads(subprocess.check_output(['pactl','-f','json','list','sink-inputs'],text=True))
 sinks=json.loads(subprocess.check_output(['pactl','-f','json','list','sinks'],text=True))
 sink=next(s for s in sinks if s['name']=='recorder038_test')
 streams=[s for s in inputs if str(s.get('sink'))==str(sink['index'])]
 assert len(streams)>=2 and app.live.busy() and app.speakers.test_status()['state']=='running'
 assert native.received_frames>before
 stage('simultaneous_timer_and_live',streams=len(streams),live_frames_before=before,live_frames_after=native.received_frames,alarm_state=app.speakers.test_status()['state'])
 # Leave the real isolated live state visible briefly for screenshot capture.
 print('SCREENSHOT_READY',flush=True)
 time.sleep(35)
 app.action('/api/timers',{'action':'ack','id':ident,'revision':row(ident)['revision']})
 wait(lambda:app.alarm_id is None);assert app.live.busy();assert not native.closed.is_set()
 stage('alarm_stop_preserves_conversation')
 speak('Wie kann ich das Gespräch beenden?')
 wait(lambda:any('beenden' in h['text'].lower() for h in app.live.public()['history'] if h['role']=='user'),40)
 time.sleep(4);assert app.live.busy();stage('question_does_not_close')
 ident=create_timer();wait(lambda:app.alarm_id==ident)
 speak('Okay, beende das Gespräch.')
 assert app.live.finished.wait(40),'Voice end did not finish'
 assert app.live.public()['end_reason']=='voice_command'
 assert native.closed.is_set() and native.stats()['processes_alive']==0
 stage('natural_voice_end_releases_audio',end_reason=app.live.public()['end_reason'],stats=native.stats())
 assert app.speakers.test_status()['state']=='running'
 stage('voice_end_preserves_alarm')
 app.action('/api/timers',{'action':'ack','id':ident,'revision':row(ident)['revision']})
 wait(lambda:app.alarm_id is None)
 assert app.capabilities()['record']['allowed'] and app.capabilities()['configure']['allowed']
 stage('recording_and_settings_unlocked')
 result['passed']=True
except Exception as error:
 result.update(passed=False,error=str(error))
 # Only synthetic speech; no production history.
 result['history']=app.live.public()['history']
finally:
 stop.set();app.live.close();app.speakers.stop_test();server.shutdown();server.server_close();app.close()
 subprocess.run(['pactl','unload-module',module],check=True)
 (root/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
 print('RESULT_PATH='+str(root/'result.json'),flush=True)
