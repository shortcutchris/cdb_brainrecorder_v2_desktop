"""Operator-run CDB staging acceptance with synthetic input and silent output.

Uses a private temporary copy of the existing Brain session; never opens the Pi
microphone/speaker or modifies production configuration. Real cloud API calls.
Pass --end-audio with a synthetic speech file and --output outside the repository.
Up to five cycles, including duplicate wakes and one expired-token refresh.
"""
import argparse,json,os,sys,time,tempfile,subprocess,shutil
from pathlib import Path
from services.cdb_integration import CdbService
from services.live_conversation import LiveConversation
from services.live_audio import NativeLiveAudio
from services.wake_word import WakeWord

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--end-audio',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
parser.add_argument('--rounds',type=int,default=5)
args=parser.parse_args()
if not args.end_audio.is_file() or not 1<=args.rounds<=5:parser.error('Synthetic audio file and 1–5 rounds required')
base=Path.home()/'.local/share/cdb-recorder-local' 
result={'synthetic_audio':True,'production_configuration_changed':False,'cycles':[]}
with tempfile.TemporaryDirectory(prefix='cdb-idle-check-') as temp:
 root=Path(temp);os.chmod(root,0o700);cdb=CdbService(root)
 for name in ('config.json','session.json'):
  cdb.write(name,json.loads((base/'cdb'/name).read_text()))
 if cdb.config()['server']!='https://staging.cdbos.de':raise RuntimeError('Staging required')
 saved=cdb.read('session.json',{});binding={'server':saved['server'],**{k:saved['identity'][k] for k in ('user_id','client_id')}}
 areas=cdb.areas(binding);area=next(a['id'] for a in areas if a['name']=='staging_playground')
 for label,text,voice in [('wake','Hey Brain','en-us'),('double','Hey Brain Hey Brain','en-us'),('end','Beende bitte das Gespräch','de')]:
  subprocess.run(['espeak-ng','-v',voice,'-s','140','-w',str(root/(label+'.wav')),text],check=True)
  subprocess.run(['ffmpeg','-v','error','-y','-i',(str(args.end_audio) if label=='end' else str(root/(label+'.wav'))),'-ar','16000','-ac','1','-f','s16le',str(root/(label+'.pcm'))],check=True)
 source=root/'source.py';source.write_text('''import sys,time
from pathlib import Path
p=Path(sys.argv[1]); gate=Path(sys.argv[2]); data=b'';sent=False
while True:
 if not sent and gate.exists():data=p.read_bytes();sent=True
 b=data[:640];data=data[640:];sys.stdout.buffer.write(b.ljust(640,b'\\0'));sys.stdout.buffer.flush();time.sleep(.02)
''')
 drain=[sys.executable,'-c','import sys;\nwhile sys.stdin.buffer.read(4096):pass']
 config={'device':'synthetic','speaker':'synthetic','volume':30}
 gate=root/'speak'
 factory=lambda conf,fail:NativeLiveAudio(conf,fail,capture_command=[sys.executable,str(source),str(root/'end.pcm'),str(gate)],playback_command=drain)
 live=LiveConversation(cdb,root,audio_config=lambda:config,audio_factory=factory)
 try:
  for n in range(args.rounds):
   gate.unlink(missing_ok=True)
   # Simulate a long idle access-token expiry without changing the real account.
   if n==0:
    saved=cdb.read('session.json',{});saved['expires']=0;cdb.write('session.json',saved)
   wake=WakeWord(root);wake.runtime=True;wake.configure(True,binding);wake.cooldown=0
   detector=[sys.executable,'-u','-c','from services.wake_word import detect; import sys; detect(capture_command=sys.argv[1:])',sys.executable,str(source),str(root/('double.pcm' if n%2 else 'wake.pcm')),str(source)]
   wake.process=subprocess.Popen(detector,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True,bufsize=0)
   started=time.monotonic();row={'round':n+1,'expired_token':n==0,'double_wake':bool(n%2),'end_voice':'supplied synthetic file'};input_peak=output_peak=0;greeting=False;triggered=False
   def trigger():
    global triggered
    t=time.monotonic();lease=live.reserve([area],owner_kind='device',cached_binding=binding)['lease'];row['reserve_ms']=round((time.monotonic()-t)*1000,2)
    live.start_native(lease);row['detection_s']=round(time.monotonic()-started,2);triggered=True
   deadline=time.monotonic()+95
   while time.monotonic()<deadline:
    if not triggered:wake.tick(account=binding,reason='',config=config,trigger=trigger)
    s=live.public();f=s.get('feedback',{});input_peak=max(input_peak,max(f.get('input',{}).get('bars',[0])));output_peak=max(output_peak,max(f.get('output',{}).get('bars',[0])))
    if triggered and not greeting and any(h['role']=='assistant' and h['text'].lower().startswith('hallo') for h in s['history']):
     greeting=True;row['greeting_s']=round(time.monotonic()-started,2);speak_at=time.monotonic()+8
    if greeting and time.monotonic()>=speak_at and not gate.exists():gate.touch()
    if triggered and not s['busy']:
     row.update(state=s['state'],end_reason=s['end_reason']);break
    time.sleep(.05)
   wake.suspend();row.update(greeting=greeting,input_wave=input_peak>0,output_wave=output_peak>0,recognitions=wake.count)
   row['user_transcripts']=[h['text'] for h in s['history'] if h['role']=='user']
   row['passed']=greeting and row.get('end_reason')=='voice_command' and input_peak>0 and output_peak>0 and wake.count==1
   result['cycles'].append(row);print(json.dumps(row),flush=True)
   if live.busy():live.end();live.finished.wait(8)
  result['passed']=all(r['passed'] for r in result['cycles'])
 finally:live.close();cdb.close()
args.output.write_text(json.dumps(result,indent=2))
