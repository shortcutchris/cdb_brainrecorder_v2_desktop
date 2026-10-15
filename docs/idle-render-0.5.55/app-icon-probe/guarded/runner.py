"""Bounded, read-only, silent UI profiling in a separate Chromium profile."""
import hashlib,json,mimetypes,os,re,shutil,signal,subprocess,sys,threading,time,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parent
APP=(Path.home()/'.local/share/cdb-recorder-app/current').resolve()
PROFILE=ROOT/'browser-profile'
BASE='http://127.0.0.1:8088'
GET=urllib.request.build_opener(urllib.request.ProxyHandler({}))
abort=threading.Event();requests={};errors=[];guard_samples=[];lock=threading.Lock()

def get(path):
 with GET.open(BASE+path,timeout=5) as response:return response.read()
def guard():
 s=json.loads(get('/api/state'))
 safe=s['version']=='0.5.55' and s['activity']['mode']=='idle' and not s['recording']['id'] and not s['live']['busy'] and not s.get('timers',{}).get('ringing_id')
 guard_samples.append({'at_epoch':time.time(),'idle':safe})
 if not safe:abort.set();raise RuntimeError('Production became active; stop isolated diagnostic')
 return s

def monitor():
 while not abort.wait(2):
  try:guard()
  except Exception:abort.set();return

MODE=sys.argv[1]
assert MODE in ('original','guarded')
state=guard()
fixtures={'/api/state':json.dumps(state).encode(),'/api/wake/status':json.dumps(state['wake']).encode()}
for path in ['/api/devices','/api/prompts','/api/setup']:fixtures[path]=get(path)
index=get('/')
assert not PROFILE.exists()
PROFILE.mkdir(mode=0o700)
started=time.time()
source_hashes={n:hashlib.sha256((APP/'studio'/n).read_bytes()).hexdigest() for n in ['app.js','device-status.js','touch.js','microphone.js']}

old_source=(APP/'studio/microphone.js').read_bytes()
old=b"$('probe-play-icon').src='/assets/'+(probeAudio.paused?'play':'pause')+'.svg';"
new=b"setIcon($('probe-play-icon'),probeAudio.paused?'play':'pause');"
assert old_source.count(old)==1,'Expected exact deployed source'
source_hashes['served_microphone.js']=hashlib.sha256(old_source.replace(old,new) if MODE=='guarded' else old_source).hexdigest()

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,code,data,content_type):
  self.send_response(code);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
  self.send_header('Content-Security-Policy',"default-src 'self' data: blob:; connect-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-src 'none'")
  self.end_headers();self.wfile.write(data)
 def do_POST(self):
  with lock:errors.append({'type':'blocked_write','at_epoch':time.time()})
  abort.set();self.reply(405,b'Blocked','text/plain')
 def do_GET(self):
  path=self.path.split('?',1)[0]
  try:
   if path=='/':data,kind=index,'text/html'
   elif path in fixtures:data,kind=fixtures[path],'application/json'
   elif path.startswith('/api/'):
    with lock:errors.append({'type':'unknown_api','path':path})
    self.reply(404,b'{}','application/json');return
   else:
    file=(APP/'studio'/path.lstrip('/')).resolve()
    if not file.is_relative_to(APP/'studio') or not file.is_file():self.reply(404,b'Not found','text/plain');return
    data=file.read_bytes();kind=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
    if path=='/microphone.js' and MODE=='guarded':
     old=b"$('probe-play-icon').src='/assets/'+(probeAudio.paused?'play':'pause')+'.svg';"
     new=b"setIcon($('probe-play-icon'),probeAudio.paused?'play':'pause');"
     assert data.count(old)==1,'Expected exact deployed source'
     data=data.replace(old,new)

   self.reply(200,data,kind)
   with lock:requests[path]=requests.get(path,0)+1
  except OSError:
   with lock:errors.append({'type':'local_response_failed','path':path})

server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
watch=threading.Thread(target=monitor,daemon=True);watch.start()
url='http://127.0.0.1:'+str(server.server_port)+'/'
log=(ROOT/'chrome-private.log').open('w');browser=None;report=None;owned={}

def census():
 all_rows={}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   f=(p/'stat').read_text().rsplit(')',1)[1].split();all_rows[int(p.name)]={'parent':int(f[1]),'start':int(f[19]),'user_ticks':int(f[11]),'system_ticks':int(f[12]),'rss_kib':int(f[21])*os.sysconf('SC_PAGESIZE')//1024}
  except (OSError,ValueError,IndexError):pass
 selected={browser.pid}
 while True:
  new={pid for pid,r in all_rows.items() if r['parent'] in selected}
  if new<=selected:break
  selected|=new
 return {pid:all_rows[pid] for pid in selected if pid in all_rows}

try:
 with GET.open(url,timeout=5) as response:assert response.read()==index
 args=['/usr/lib/chromium/chromium','--js-flags=--no-decommit-pooled-pages','--force-renderer-accessibility','--disable-gpu','--password-store=basic','--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--mute-audio','--window-size=1280,720','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+str(PROFILE),url]
 browser=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 deadline=time.monotonic()+25
 portfile=PROFILE/'DevToolsActivePort'
 while not portfile.exists():
  if abort.is_set() or browser.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Diagnostic browser did not become ready')
  time.sleep(.2)
 port=int(portfile.read_text().splitlines()[0])
 with GET.open('http://127.0.0.1:'+str(port)+'/json/list',timeout=5) as r:targets=json.load(r)
 target=next(t for t in targets if t.get('type')=='page' and t.get('url')==url)
 with connect(target['webSocketDebuggerUrl'],open_timeout=5,close_timeout=2,max_size=16*1024*1024) as ws:
  serial=0
  def cmd(method,params=None):
   global serial
   if abort.is_set():raise RuntimeError('Diagnostic guard stopped the run')
   serial+=1;ws.send(json.dumps({'id':serial,'method':method,'params':params or {}}))
   while True:
    message=json.loads(ws.recv(timeout=8))
    if message.get('id')!=serial:continue
    if 'error' in message:raise RuntimeError('CDP command failed: '+method)
    return message.get('result',{})
  def wait(seconds):
   if abort.wait(seconds):raise RuntimeError('Production activity interrupted diagnostic')
  cmd('Page.enable')
  cmd('Emulation.setDeviceMetricsOverride',{'width':1280,'height':720,'deviceScaleFactor':1,'mobile':False})
  navigation=cmd('Page.navigate',{'url':url})
  (ROOT/'navigation.json').write_text(json.dumps(navigation))
  if navigation.get('errorText'):raise RuntimeError('Diagnostic navigation failed: '+navigation['errorText'])
  for _ in range(50):
   ready=cmd('Runtime.evaluate',{'expression':'typeof state!=="undefined" && !!state && document.body.dataset.workspace === "start-view"','returnByValue':True})
   if ready.get('result',{}).get('value'):break
   wait(.2)
  else:
   details=cmd('Runtime.evaluate',{'expression':'JSON.stringify({url:location.pathname,ready:document.readyState,workspace:document.body?.dataset.workspace,nodes:document.querySelectorAll("*").length,online:typeof online==="undefined"?null:online,stateLoaded:typeof state!=="undefined"&&!!state})','returnByValue':True})
   (ROOT/'readiness-failure.json').write_text(json.dumps(details))
   raise RuntimeError('Home view readiness not established')
  wait(5);owned=census()
  report={'scope':'Isolated Pi Chromium with in-memory read-only app snapshot; no production browser changes or audio','started_at_epoch':started,'browser_pid':browser.pid,'browser':cmd('Browser.getVersion'),'source_hashes':source_hashes,'startup_flags':[a for a in args[1:] if not a.startswith('--user-data-dir=') and a!=url],'fixture_counts':{'sessions':len(state['sessions']),'jobs':len(state['jobs']),'live_history':len(state['live'].get('history',[]))},'runs':[],'overall_goal_complete':False,'mode':MODE,'clock_ticks':os.sysconf('SC_CLK_TCK'),'planned_seconds':300}
  cmd('Performance.enable')
  def snapshot():
   ui=cmd('Runtime.evaluate',{'expression':'JSON.stringify({workspace:document.body.dataset.workspace,nodes:document.querySelectorAll("*").length,hidden:document.hidden,online:online,version:state.version})','returnByValue':True})
   return {'at_epoch':time.time(),'metrics':cmd('Performance.getMetrics'),'heap':cmd('Runtime.getHeapUsage'),'dom':cmd('Memory.getDOMCounters'),'processes':census(),'ui':json.loads(ui['result']['value']),'requests':dict(requests)}
  started_measure=time.monotonic()
  for number in range(11):
   delay=started_measure+number*30-time.monotonic()
   if delay>0:wait(delay)
   report['runs'].append(snapshot())
   (ROOT/'partial.json').write_text(json.dumps(report))
  report['ended_at_epoch']=time.time();report['requests']=requests;report['errors']=errors;report['guard_samples']=guard_samples
  (ROOT/'profile.json').write_text(json.dumps(report))
  print(json.dumps({'completed':True,'seconds':report['ended_at_epoch']-started,'errors':errors}),flush=True)
except Exception as error:
 (ROOT/'failure.json').write_text(json.dumps({'type':type(error).__name__,'message':str(error),'at_epoch':time.time(),'requests':requests,'errors':errors,'guard_samples':guard_samples},indent=2)+'\n')
 raise
finally:
 abort.set();owned.update(census() if browser else {})
 if browser and browser.poll() is None:
  browser.terminate()
  try:browser.wait(timeout=8)
  except subprocess.TimeoutExpired:os.killpg(browser.pid,signal.SIGKILL);browser.wait(timeout=3)
 server.shutdown();server.server_close();thread.join(2);watch.join(6);log.close();time.sleep(.5)
 remaining=[]
 for pid,info in owned.items():
  try:
   f=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
   if int(f[19])==info['start']:remaining.append(pid)
  except OSError:pass
 cleanup={'at_epoch':time.time(),'closed':not remaining,'remaining':remaining,'browser_exit_code':browser.returncode if browser else None,'server_stopped':not thread.is_alive(),'guard_stopped':not watch.is_alive(),'profile_written':(ROOT/'profile.json').exists()}
 if not remaining:shutil.rmtree(PROFILE)
 (ROOT/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n');print(json.dumps(cleanup),flush=True)
