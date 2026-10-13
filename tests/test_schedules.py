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
