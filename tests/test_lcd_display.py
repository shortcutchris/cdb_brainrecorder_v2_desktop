import json,tempfile,unittest,threading,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import Mock,patch
from services.schedules import Schedules
from services.lcd_display import snapshot,MAX_FRAME
from services.lcd_bridge import Bridge,encode,fetch

class LCDTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.now=100.
  self.s=Schedules(Path(self.tmp.name),lambda:self.now,lambda:self.now,'boot')
 def tearDown(self):self.tmp.cleanup()
 def add(self,name='Küche',seconds=10):return self.s.create({'kind':'timer','label':name,'seconds':seconds,'request_id':name+'-request'})['id']
 def test_read_only_projection_preserves_database_and_precise_monotonic_time(self):
  self.add();before=self.s.path.read_bytes();self.now+=.125
  result=snapshot(self.s,False);self.assertEqual(result['timers'][0]['remaining_ms'],9875)
  self.assertTrue(result['timers'][0]['time_valid']);self.assertEqual(before,self.s.path.read_bytes())
  self.assertEqual(set(result),{'protocol','type','clock_ready','total','timers'})
 def test_reboot_clock_untrusted_and_due_cancel_removal(self):
  ident=self.add();other=Schedules(Path(self.tmp.name),lambda:self.now,lambda:self.now,'new-boot')
  self.assertFalse(snapshot(other,False)['timers'][0]['time_valid'])
  self.now+=11;self.s.tick();r=snapshot(self.s,True)['timers'][0];self.assertEqual(r['state'],'due')
  self.s.change({'action':'ack','id':ident,'revision':r['revision']});self.assertEqual(snapshot(self.s,True)['timers'],[])
 def test_bound_and_bounded_frames_no_control_characters(self):
  for i in range(20):self.add(str(i)+'\n'+ 'ü'*75)
  result=snapshot(self.s,True);self.assertEqual(len(result['timers']),16);self.assertEqual(result['total'],20)
  self.assertNotIn('\n',result['timers'][0]['label']);self.assertLess(len(encode(result)),MAX_FRAME)
 def test_handshake_stale_ack_replay_and_reconnect(self):
  b=Bridge('Pi');nonce='a'*32
  self.assertIsNone(b.frame({},0))
  bind=b.receive({'protocol':'cdb.lcd/1','type':'hello','nonce':nonce},0);self.assertEqual(bind['type'],'bind')
  self.assertIsNone(b.frame({},0))
  bound={'protocol':'cdb.lcd/1','type':'bound','nonce':nonce,'session':b.session}
  b.receive(bound,0);f=b.frame({},1);self.assertEqual(f['seq'],1)
  b.receive(dict(bound,type='ack',seq=0),2);self.assertIsNone(b.frame({},3.1))
  b.receive(dict(bound,type='ack',seq=1),3.2);self.assertIsNotNone(b.frame({},3.3))
  b.receive({'protocol':'cdb.lcd/1','type':'hello','nonce':'b'*32},4);self.assertFalse(b.bound)
  b.receive(bound,4);self.assertFalse(b.bound)

class LCDHttpTests(unittest.TestCase):
 def test_minimal_route_retains_auth_and_never_reads_full_app_state(self):
  from web_server import StudioApp,StudioServer
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);app=StudioApp(root/'queue',root/'db',backend=Mock(),preview=True,settings_file=root/'settings')
   app.ambient_stop.set();app.ambient_thread.join(3);app.token='test-only'
   server=StudioServer(('127.0.0.1',0),app);thread=threading.Thread(target=server.serve_forever);thread.start()
   try:
    with patch.object(app,'state',side_effect=AssertionError('Private full state accessed')):
     with self.assertRaises(urllib.error.HTTPError) as error:fetch(server.server_port)
     self.assertEqual(error.exception.code,401)
     self.assertEqual(fetch(server.server_port,'test-only')['timers'],[])
   finally:server.shutdown();server.server_close();thread.join();app.close()

if __name__=='__main__':unittest.main()
