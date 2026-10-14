import sys,os,json,shutil,time,threading
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0,'/home/chris/recorder-059-code')
from scripts.studio_preview import create_preview
from services.live_audio import NativeLiveAudio
root=Path('/home/chris/start039-probe-'+str(int(time.time())));root.mkdir(mode=0o700)
app=create_preview(root);app.ambient_stop.set();app.ambient_thread.join(3)
rows=[];origin=time.monotonic()
def note(event,**kwargs):
 row={'event':event,'elapsed':round(time.monotonic()-origin,3),**kwargs};rows.append(row);print(json.dumps(row),flush=True)
request=app.cdb.transport.request
def measured(url,*args,**kwargs):
 # No credentials, area IDs or SDP in diagnostics.
 route=urlsplit(url).path;route=route if '/sessions/' not in route else '/sessions/'+route.rsplit('/',1)[-1]
 start=time.monotonic();note('http_start',route=route)
 try:return request(url,*args,**kwargs)
 finally:note('http_end',route=route,seconds=round(time.monotonic()-start,3))
app.cdb.transport.request=measured
config={'device':'synthetic','speaker':'silent'};app.live.audio_config=lambda:config
natives=[]
class MeasuredAudio(NativeLiveAudio):
 def open(self):
  start=time.monotonic();note('native_open')
  try:return super().open()
  finally:note('native_offer_ready',seconds=round(time.monotonic()-start,3))
 def answer(self,sdp):
  note('answer_received');return super().answer(sdp)
 def _connection_changed(self):
  note('peer_state',state=self.peer.connectionState);super()._connection_changed()
def factory(config,failed):
 a=MeasuredAudio(config,failed,capture_command=[sys.executable,'-u','-c','import sys,time\nwhile True:sys.stdout.buffer.write(bytes(640));sys.stdout.buffer.flush();time.sleep(.02)'],playback_command=[sys.executable,'-c','import sys\nwhile sys.stdin.buffer.read(960):pass'])
 natives.append(a);return a
app.live.audio_factory=factory
try:
 original=Path('/home/chris/.local/share/cdb-recorder-local/cdb')
 for name in ('session.json','config.json','destination.json'):
  shutil.copy2(original/name,app.cdb.root/name);os.chmod(app.cdb.root/name,0o600)
 setup=app.live.setup();areas=[a['id'] for a in setup['areas'] if a.get('name')=='staging_playground'];assert areas
 for trial in range(2):
  note('start_requested',trial=trial+1)
  lease=app.live.reserve(areas[:1],owner_kind='device')['lease'];app.live.start_native(lease)
  deadline=time.monotonic()+100
  while time.monotonic()<deadline:
   if natives[-1].stats()['ready_tone']=='played':break
   if app.live.state in ('error','ended'):raise RuntimeError(app.live.error)
   time.sleep(.1)
  assert natives[-1].stats()['ready_tone']=='played'
  note('ready',trial=trial+1,stats=natives[-1].stats());app.live.end();assert app.live.finished.wait(30);time.sleep(1)
finally:
 app.close();(root/'timings.json').write_text(json.dumps(rows,indent=2));print('RESULT_PATH='+str(root/'timings.json'),flush=True)
