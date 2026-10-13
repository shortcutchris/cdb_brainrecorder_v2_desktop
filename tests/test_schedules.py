import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from services.schedules import Schedules, local_due

class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.wall=1770000000.;self.elapsed=10.
        self.service=Schedules(self.tmp.name,lambda:self.wall,lambda:self.elapsed,'boot-a')
    def tearDown(self):self.tmp.cleanup()
    def create(self,seconds=10,request='request-1'):
        return self.service.create({'kind':'timer','label':'Tee','seconds':seconds,'request_id':request})
    def test_timer_ignores_wall_clock_jump_and_fires_once(self):
        self.create();self.wall+=3600;self.service.tick();self.assertEqual(self.service.items()[0]['remaining'],10)
        self.elapsed+=10;self.service.tick();item=self.service.items()[0];self.assertEqual(item['state'],'due')
        self.service.tick();self.assertEqual(self.service.items()[0]['revision'],item['revision'])
    def test_persistent_boot_and_unsynchronized_clock(self):
        self.create();self.wall+=20
        restored=Schedules(self.tmp.name,lambda:self.wall,lambda:0,'boot-b')
        restored.tick(False);self.assertEqual(restored.items()[0]['state'],'scheduled')
        restored.tick(True);self.assertEqual(restored.items()[0]['state'],'due')
    def test_missed_no_alarm_storm(self):
        self.create();self.elapsed+=1000;self.service.tick();self.assertEqual(self.service.items()[0]['state'],'missed')
    def test_idempotent_concurrent_create(self):
        with ThreadPoolExecutor(4) as pool:list(pool.map(lambda _:self.create(),range(8)))
        self.assertEqual(len(self.service.items()),1)
        with self.assertRaises(ValueError):self.create(20)
    def test_revision_prevents_stale_cancel_and_snooze(self):
        self.create();self.elapsed+=10;self.service.tick();old=self.service.items()[0]
        self.service.change({'id':old['id'],'revision':old['revision'],'action':'snooze'})
        row=self.service.items()[0];self.assertEqual(row['remaining'],300)
        with self.assertRaises(ValueError):self.service.change({'id':old['id'],'revision':old['revision'],'action':'cancel'})
        self.service.change({'id':row['id'],'revision':row['revision'],'action':'cancel'})
        self.elapsed+=1000;self.service.tick();self.assertEqual(self.service.items()[0]['state'],'cancelled')
    def test_invalid_input_and_dst(self):
        for value in [True,0,-1,604801,1.2,'5']:
            with self.assertRaises(ValueError):self.create(value)
        with self.assertRaises(ValueError):local_due('2026-03-29T02:30')
        with self.assertRaises(ValueError):local_due('2026-10-25T02:30')
        self.assertEqual(local_due('2026-10-25T02:30',fold=1)-local_due('2026-10-25T02:30',fold=0),3600)
    def test_reminder_and_ack_remain_after_restart(self):
        stamp=local_due('2026-10-14T09:00');self.wall=stamp-60
        self.service.create({'kind':'reminder','label':'Anruf','local_time':'2026-10-14T09:00','request_id':'reminder-1'})
        self.wall=stamp;self.service.tick();row=self.service.items()[0]
        self.service.change({'id':row['id'],'revision':row['revision'],'action':'ack'})
        self.assertEqual(Schedules(self.tmp.name).items()[0]['state'],'done')
    def tool(self, name='create_timer', args=None, ident='tool-request-0001'):
        return {'id':ident,'name':name,'arguments':args or {'label':'Tee','seconds':60,'tone':'chime'},'expires_at':self.wall+60}
    def test_tool_receipt_survives_restart_and_lost_ack(self):
        request=self.tool();first=self.service.execute_tool('scope-a',request)
        self.assertTrue(first['ok'])
        self.assertEqual(first,self.service.execute_tool('scope-a',request))
        self.assertEqual(first,Schedules(self.tmp.name).execute_tool('scope-a',request))
        self.assertEqual(len(self.service.items()),1)
        self.assertEqual(self.service.items()[0]['tone'],'chime')
    def test_tool_expiry_invalid_args_and_payload_conflict(self):
        request=self.tool();request['expires_at']=self.wall-1
        self.assertFalse(self.service.execute_tool('scope-a',request)['ok'])
        self.assertEqual(self.service.items(),[])
        request=self.tool();request['arguments']['seconds']=True
        self.assertFalse(self.service.execute_tool('scope-b',request)['ok'])
        request=self.tool();self.service.execute_tool('scope-c',request)
        request['arguments']['seconds']=90
        with self.assertRaises(ValueError):self.service.execute_tool('scope-c',request)
    def test_tool_mutation_and_receipt_rollback_together(self):
        import sqlite3
        with self.service.db() as db:
            db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON tool_results BEGIN SELECT RAISE(ABORT,'disk full simulation'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.service.execute_tool('scope',self.tool())
        self.assertEqual(self.service.items(),[])
    def test_tool_cancel_is_idempotent_and_stale_revision_fails(self):
        self.create();row=self.service.items()[0]
        request=self.tool('cancel_schedule',{'id':row['id'],'revision':row['revision']})
        first=self.service.execute_tool('scope',request)
        self.assertTrue(first['ok']);self.assertEqual(first,self.service.execute_tool('scope',request))
        request['id']='tool-request-0002'
        self.assertFalse(self.service.execute_tool('scope',request)['ok'])
    def test_tone_validation_and_alarm_samples(self):
        import wave
        from services.alarm_tones import write_alarm
        from pathlib import Path
        for tone in ('bell','chime','pulse'):
            path=Path(self.tmp.name)/(tone+'.wav');write_alarm(path,tone)
            with wave.open(str(path)) as wav:
                self.assertEqual(wav.getnframes(),72000);self.assertEqual(wav.getnchannels(),2)
        with self.assertRaises(ValueError):self.service.create({'kind':'timer','label':'x','seconds':5,'request_id':'invalid-tone','tone':'/etc/passwd'})
