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
svg=(APP/'studio/assets/play.svg').read_bytes()
fixtures={'/icon.svg':svg}
index=("""<!doctype html><html><head><meta charset="utf-8"><title>Isolated SVG probe</title></head><body><img id="target" width="24" height="24"><script>
window.probe={mode:MODE,loads:0,iterations:0,heartbeat:0,done:false,started:null,ended:null};
const target=document.getElementById('target');target.addEventListener('load',()=>probe.loads++);target.src='/icon.svg';
setInterval(()=>probe.heartbeat++,100);
window.runStress=()=>{probe.started=performance.now();const timer=setInterval(()=>{if(probe.mode==='original'||target.getAttribute('src')!=='/icon.svg')target.src='/icon.svg';probe.iterations++;if(probe.iterations===500){clearInterval(timer);probe.done=true;probe.ended=performance.now()}},8)};
</script></body></html>""".replace('mode:MODE','mode:'+json.dumps(MODE))).encode()
assert not PROFILE.exists()
PROFILE.mkdir(mode=0o700)
started=time.time()
source_hashes={'play.svg':hashlib.sha256(svg).hexdigest(),'fixture.html':hashlib.sha256(index).hexdigest()}

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
   elif path in fixtures:data,kind=fixtures[path],'image/svg+xml'
   elif path.startswith('/api/'):
    with lock:errors.append({'type':'unknown_api','path':path})
    self.reply(404,b'{}','application/json');return
   else:
    file=(APP/'studio'/path.lstrip('/')).resolve()
    if not file.is_relative_to(APP/'studio') or not file.is_file():self.reply(404,b'Not found','text/plain');return
    data=file.read_bytes();kind=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
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
   ready=cmd('Runtime.evaluate',{'expression':'typeof probe!=="undefined" && target.complete && target.naturalWidth>0','returnByValue':True})
   if ready.get('result',{}).get('value'):break
   wait(.2)
  else:raise RuntimeError('SVG fixture readiness not established')
  wait(2);owned=census()
  report={'scope':'Isolated minimal SVG repeated-src reproduction, actual Pi Chromium; not production UI or acoustic acceptance','mode':MODE,'started_at_epoch':started,'browser_pid':browser.pid,'browser':cmd('Browser.getVersion'),'source_hashes':source_hashes,'startup_flags':[a for a in args[1:] if not a.startswith('--user-data-dir=') and a!=url],'runs':[],'overall_goal_complete':False,'forced_gc_only_final_phase':True,'clock_ticks':os.sysconf('SC_CLK_TCK'),'expected_iterations':500,'revision':2}
  cmd('Performance.enable')
  def snapshot():
   value=cmd('Runtime.evaluate',{'expression':'JSON.stringify(probe)','returnByValue':True})
   return {'at_epoch':time.time(),'metrics':cmd('Performance.getMetrics'),'heap':cmd('Runtime.getHeapUsage'),'dom':cmd('Memory.getDOMCounters'),'probe':json.loads(value['result']['value']),'processes':census()}
  def checkpoint():
   report['requests']=dict(requests);report['errors']=list(errors);report['guard_samples']=list(guard_samples)
   (ROOT/'partial.json').write_text(json.dumps(report))
  def idle_phase(name):
   before=snapshot();wait(5);after=snapshot();report['runs'].append({'phase':name,'before':before,'after':after});checkpoint()
  idle_phase('baseline')
  cmd('Runtime.evaluate',{'expression':'runStress()'})
  deadline=time.monotonic()+40
  while True:
   status=cmd('Runtime.evaluate',{'expression':'probe.done','returnByValue':True})
   if status.get('result',{}).get('value'):break
   if time.monotonic()>deadline:
    report['timeout_snapshot']=snapshot();checkpoint();raise RuntimeError('Bounded SVG stress did not complete')
   wait(.5)
  report['after_stress_immediate']=snapshot();checkpoint()
  idle_phase('after_stress')
  cmd('HeapProfiler.collectGarbage')
  idle_phase('after_forced_gc')
  report['ended_at_epoch']=time.time();report['requests']=requests;report['errors']=errors;report['guard_samples']=guard_samples
  (ROOT/'profile.json').write_text(json.dumps(report))
  print(json.dumps({'completed':True,'mode':MODE,'seconds':report['ended_at_epoch']-started,'errors':errors}),flush=True)

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
