"""Real companion subprocess over a pseudo-terminal; synthetic HTTP data only."""
import json,os,pty,select,subprocess,sys,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

class SerialIntegration(unittest.TestCase):
 def test_handshake_filtering_failure_and_new_challenge(self):
  mode={'online':True}
  class Handler(BaseHTTPRequestHandler):
   def do_GET(self):
    self.send_response(200 if mode['online'] else 503);self.end_headers()
    self.wfile.write(json.dumps({'protocol':'cdb.lcd/1','type':'timers','clock_ready':True,'total':1,'private':'must-never-be-sent','timers':[{'id':'test','label':'Küche','state':'scheduled','revision':1,'remaining_ms':10000,'time_valid':True,'private':'must-never-be-sent'}]}).encode())
   def log_message(self,*args):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever);worker.start()
  master,slave=pty.openpty();port=os.ttyname(slave)
  process=subprocess.Popen([sys.executable,'-m','services.lcd_bridge','--port',port,'--api-port',str(server.server_port)],cwd=Path(__file__).resolve().parents[2],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  buffer=bytearray()
  def send(message):os.write(master,json.dumps(message).encode()+b'\n')
  def receive(timeout=2):
   deadline=time.monotonic()+timeout
   while time.monotonic()<deadline:
    if b'\n' in buffer:
     line,_,rest=buffer.partition(b'\n');buffer[:]=rest
     try:return json.loads(line)
     except ValueError:continue
    if select.select([master],[],[],.05)[0]:buffer.extend(os.read(master,16384))
   return None
  try:
   time.sleep(.3);self.assertIsNone(process.poll());self.assertIsNone(receive(.2))
   hello={'protocol':'cdb.lcd/1','type':'hello','nonce':'a'*32}
   # Overflow and fragmented messages must recover at the following newline.
   os.write(master,b'x'*1500+b'\n{invalid}\n');raw=json.dumps(hello).encode()+b'\n'
   os.write(master,raw[:19]);time.sleep(.05);os.write(master,raw[19:]);bind=receive()
   self.assertEqual(bind['type'],'bind');self.assertIsNone(receive(.3))
   ack=dict(bind,type='bound');send(ack);frame=receive();self.assertEqual(frame['type'],'snapshot')
   self.assertNotIn('must-never-be-sent',json.dumps(frame));self.assertEqual(frame['timers'][0]['label'],'Küche')
   send(dict(ack,type='ack',seq=frame['seq']));mode['online']=False
   self.assertIsNone(receive(1.5))
   mode['online']=True;hello['nonce']='c'*32;send(hello);bind=receive();self.assertEqual(bind['nonce'],'c'*32)
   send(dict(bind,type='bound'));frame=receive();self.assertEqual(frame['seq'],1);self.assertEqual(frame['nonce'],'c'*32)
  finally:
   process.terminate();out,err=process.communicate(timeout=3);os.close(master);os.close(slave);server.shutdown();server.server_close();worker.join()
   if err:print(err.decode(),file=sys.stderr)

if __name__=='__main__':unittest.main()
