"""Deadline, opt-in and protected audio tests; no real audio hardware."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import wave
from services.announcements import Announcements, load_pack
from services.schedules import Schedules
from services.app_activity import AppActivity
from services.audio_output import AudioOutput
from tests.test_announcements import pack, wav


class CountdownTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.elapsed = 10.; self.wall = 1000.
        self.s = Schedules(self.root, lambda: self.wall, lambda: self.elapsed, 'boot')
    def tearDown(self): self.tmp.cleanup()
    def timer(self, seconds=10, tone='bell', request='timer-one'):
        return self.s.create({'kind':'timer','label':'Private label never spoken','seconds':seconds,'tone':tone,'request_id':request})['id']

    def test_window_durable_claim_no_wall_clock_drift_or_alarm_mutation(self):
        ident=self.timer(); self.assertIsNone(self.s.claim_countdown())
        self.elapsed+=3.5; self.wall+=10000
        before=self.s.items();claim=self.s.claim_countdown();self.assertEqual(claim['id'],ident)
        self.assertAlmostEqual(claim['end_at']-time.monotonic(),6.5,places=1)
        self.assertEqual(self.s.items(),before)
        restored=Schedules(self.root,lambda:self.wall,lambda:self.elapsed,'boot')
        self.assertIsNone(restored.claim_countdown())
        self.elapsed+=6.5;self.s.tick();self.assertEqual(self.s.items()[0]['state'],'due');self.assertEqual(self.s.items()[0]['sound'],'pending')

    def test_overlapping_and_short_silent_timers_no_late_catchup(self):
        self.timer(6,request='timer-one');self.timer(7,request='timer-two')
        self.assertIsNotNone(self.s.claim_countdown());self.assertIsNone(self.s.claim_countdown())
        self.timer(4,request='timer-short');self.timer(6,tone='silent',request='timer-silent')
        self.assertIsNone(self.s.claim_countdown())
        self.elapsed+=2;self.assertIsNone(self.s.claim_countdown())

    def test_reboot_clock_gate_and_snooze_new_revision(self):
        ident=self.timer(6)
        rebooted=Schedules(self.root,lambda:self.wall,lambda:0,'other-boot')
        self.assertIsNone(rebooted.claim_countdown(False));self.assertIsNotNone(rebooted.claim_countdown(True))
        self.elapsed+=6;self.s.tick();row=self.s.items()[0]
        self.s.change({'id':ident,'revision':row['revision'],'action':'snooze'})
        self.elapsed+=294;self.assertIsNotNone(self.s.claim_countdown())

    def test_corrupt_or_unwritable_receipts_skip_countdown_but_alarm_still_fires(self):
        self.timer(6)
        receipt=self.root/'timer-countdowns.json';receipt.write_text('broken')
        self.assertIsNone(self.s.claim_countdown())
        receipt.unlink()
        with patch('meeting_recorder.core.atomic_write',side_effect=OSError('disk full')):
            self.assertIsNone(self.s.claim_countdown())
        self.elapsed+=6;self.s.tick();self.assertEqual(self.s.items()[0]['state'],'due')
        self.assertEqual(self.s.items()[0]['sound'],'pending')

    def test_reminders_never_count_down(self):
        self.timer(6)
        with self.s.db() as db: db.execute("UPDATE schedules SET kind='reminder'")
        self.assertIsNone(self.s.claim_countdown())

    def test_old_pack_preserves_flags_new_opt_in_requires_five_second_clip(self):
        folder=pack(self.root);manifest=json.loads((folder/'manifest.json').read_text());del manifest['clips']['countdown'];(folder/'manifest.json').write_text(json.dumps(manifest))
        (self.root/'announcements.json').write_text('{"offline":true,"timers":true,"connecting":true}')
        a=Announcements(self.root);self.assertFalse(a.enabled['countdown']);self.assertTrue(a.enabled['connecting'])
        with self.assertRaises(ValueError):a.configure({'countdown':True})
        data=wav(seconds=4);(folder/'countdown.wav').write_bytes(data);manifest['clips']['countdown']={'text':'Fünf, vier, drei, zwei, eins.','sha256':hashlib.sha256(data).hexdigest()};(folder/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):load_pack(folder)
        data=wav(seconds=5);(folder/'countdown.wav').write_bytes(data);manifest['clips']['countdown']['sha256']=hashlib.sha256(data).hexdigest();(folder/'manifest.json').write_text(json.dumps(manifest))
        a.configure({'countdown':True});self.assertEqual(a.countdown_clip(),data);self.assertTrue(Announcements(self.root).enabled['countdown'])


class CountdownIntegrationTests(unittest.TestCase):
    def setUp(self):
        from web_server import StudioApp
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=StudioApp(self.root/'queue',self.root/'db',backend=Mock(),preview=True,settings_file=self.root/'settings.ini')
        self.app.ambient_stop.set();self.app.ambient_thread.join(3)
        pack(self.app.store.root);self.app.announcements.configure({'countdown':True})
        self.candidate={'id':'timer','revision':1,'end_at':time.monotonic()+6}
    def tearDown(self):self.app.close();self.tmp.cleanup()
    def test_busy_skip_without_output_or_wake_mutation(self):
        for activity in [AppActivity(recording=True),AppActivity(recording=True,paused=True),AppActivity(live='active'),AppActivity(live_reserved=True),AppActivity(maintenance=True),AppActivity(pending=True),AppActivity(microphone_test=True),AppActivity(speaker_test=True),AppActivity(bluetooth=True),AppActivity(download=True),AppActivity(model_test=True)]:
            with self.subTest(activity=activity),patch.object(self.app,'activity',return_value=activity),patch.object(self.app.schedules,'claim_countdown',return_value=self.candidate) as claim,patch.object(self.app.wake,'suspend') as suspend,patch.object(self.app.speakers,'start_countdown') as play:
                self.app.tick_countdown();claim.assert_called_once();suspend.assert_not_called();play.assert_not_called()
    def test_external_playback_wake_test_and_disabled_skip(self):
        for mode in ['browser','output','wake-test','disabled']:
            self.app.playback_leases={'x':time.monotonic()+10} if mode=='browser' else {}
            self.app.output_busy_until=time.monotonic()+10 if mode=='output' else 0
            self.app.wake.test_until=time.monotonic()+10 if mode=='wake-test' else 0
            self.app.announcements.enabled['countdown']=mode!='disabled'
            with patch.object(self.app,'activity',return_value=AppActivity()),patch.object(self.app.schedules,'claim_countdown',return_value=self.candidate),patch.object(self.app.speakers,'start_countdown') as play:
                self.app.tick_countdown();play.assert_not_called()
    def test_start_suspends_wake_and_cancel_or_due_stops_owned_output(self):
        order=[]
        with patch.object(self.app,'activity',return_value=AppActivity()),patch.object(self.app.schedules,'claim_countdown',return_value=self.candidate),patch.object(self.app.wake,'suspend',side_effect=lambda *a:order.append('wake')),patch.object(self.app.speakers,'start_countdown',side_effect=lambda *a:order.append('play')):
            self.app.tick_countdown()
        self.assertEqual(order,['wake','play']);self.assertTrue(self.app.announcement_playing)
        with patch.object(self.app.schedules,'claim_countdown',return_value=None),patch.object(self.app.schedules,'items',return_value=[]),patch.object(self.app.speakers,'stop_test') as stop:
            self.app.tick_countdown();stop.assert_called_once()
        self.assertIsNone(self.app.countdown);self.assertFalse(self.app.announcement_playing)
    def test_failed_cleanup_blocks_capture_and_retains_owner(self):
        for path in ['/api/record/start','/api/live/reserve','/api/microphone/test']:
            self.app.countdown=self.candidate;self.app.announcement_playing=True
            with patch.object(self.app.speakers,'stop_test',side_effect=ValueError('cleanup')),patch.object(self.app.engine,'start') as capture,patch.object(self.app.live,'reserve') as live:
                with self.assertRaisesRegex(ValueError,'cleanup'):self.app.action(path,{})
                capture.assert_not_called();live.assert_not_called();self.assertEqual(self.app.countdown,self.candidate)
        self.app.countdown=None;self.app.announcement_playing=False
    def test_failed_wake_shutdown_never_plays_and_expired_start_skipped(self):
        with patch.object(self.app,'activity',return_value=AppActivity()),patch.object(self.app.schedules,'claim_countdown',return_value=self.candidate),patch.object(self.app.wake,'suspend',side_effect=ValueError('wake')),patch.object(self.app.speakers,'start_countdown') as play:
            with self.assertRaises(ValueError):self.app.tick_countdown()
            play.assert_not_called()
        with patch.object(self.app,'activity',return_value=AppActivity()),patch.object(self.app.schedules,'claim_countdown',return_value=self.candidate),patch.object(self.app.wake,'suspend'),patch.object(self.app.speakers,'start_countdown',side_effect=ValueError('late')):
            self.app.tick_countdown();self.assertIsNone(self.app.countdown)


class CountdownPlaybackTests(unittest.TestCase):
    def test_preroll_cancel_does_not_launch_audio_child(self):
        with tempfile.TemporaryDirectory() as folder:
            output=AudioOutput(folder);output.public=lambda:{'available':True,'muted':False,'volume':30,'selected':'fake'}
            with patch('services.audio_output.subprocess.Popen') as launch:
                output.start_countdown(wav(seconds=5),time.monotonic()+6)
                output.stop_test();launch.assert_not_called();self.assertFalse(output.thread.is_alive())
    def test_late_worker_does_not_play_and_deadline_reaps_child(self):
        with tempfile.TemporaryDirectory() as folder:
            output=AudioOutput(folder)
            with patch('services.audio_output.subprocess.Popen') as launch:
                output._play('fake',announcement=wav(seconds=5),countdown_end=time.monotonic()+4)
                launch.assert_not_called()
            child=Mock();child.wait.side_effect=[subprocess.TimeoutExpired('silent',1),0];child.poll.return_value=None
            now=[100.]
            def advance(seconds):now[0]+=seconds
            with patch('services.audio_output.time.monotonic',side_effect=lambda:now[0]),patch('services.audio_output.time.sleep',side_effect=advance),patch('services.audio_output.subprocess.Popen',return_value=child):
                output._play('fake',announcement=wav(seconds=5),countdown_end=105.05)
            child.terminate.assert_called_once();self.assertIsNone(output.process)
            self.assertEqual(output.test_status()['state'],'completed')

    def test_non_countdown_timeout_remains_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            output=AudioOutput(folder)
            child=Mock();child.wait.side_effect=[subprocess.TimeoutExpired('silent',1),0];child.poll.return_value=None
            with patch('services.audio_output.subprocess.Popen',return_value=child):
                output._play('fake',announcement=wav(seconds=5))
            self.assertEqual(output.test_status()['state'],'failed')
            self.assertIsNone(output.process)

    def test_countdown_failed_cleanup_retains_busy_child(self):
        with tempfile.TemporaryDirectory() as folder:
            output=AudioOutput(folder)
            child=Mock();child.wait.side_effect=subprocess.TimeoutExpired('silent',1);child.poll.return_value=None
            with patch('services.audio_output.time.monotonic',return_value=100.),patch('services.audio_output.subprocess.Popen',return_value=child):
                output._play('fake',announcement=wav(seconds=5),countdown_end=105.)
            self.assertEqual(output.test_status()['state'],'running')
            self.assertIs(output.process,child)
            child.terminate.assert_called_once();child.kill.assert_called_once()


class CountdownBuildTests(unittest.TestCase):
    def test_five_slots_and_silence_trim_without_cutting_long_digits(self):
        import numpy as np
        from scripts.prepare_announcements import countdown_pcm
        parts=[np.concatenate([np.zeros(500),np.ones(7000)*(.1+i*.1),np.zeros(600)]) for i in range(5)]
        result=countdown_pcm(parts)
        self.assertEqual(len(result),120000)
        for i in range(5):
            self.assertAlmostEqual(float(result[i*24000+1000]),.1+i*.1,places=5)
            self.assertTrue(np.all(result[i*24000+22000:(i+1)*24000]==0))
        with self.assertRaises(ValueError):countdown_pcm([np.ones(24000)]*5)
        with self.assertRaises(ValueError):countdown_pcm([np.zeros(500)]*5)

    def test_countdown_cancel_reaps_actual_silent_child(self):
        with tempfile.TemporaryDirectory() as folder:
            output=AudioOutput(folder);output.public=lambda:{'available':True,'muted':False,'volume':30,'selected':'fake'}
            launch=subprocess.Popen;ready=threading.Event();children=[]
            def silent(*args,**kwargs):
                child=launch([sys.executable,'-c','import time; time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                children.append(child);ready.set();return child
            try:
                with patch('services.audio_output.subprocess.Popen',side_effect=silent):
                    output.start_countdown(wav(seconds=5),time.monotonic()+5.2)
                    self.assertTrue(ready.wait(2));output.stop_test()
                self.assertIsNotNone(children[0].poll());self.assertFalse(output.thread.is_alive())
            finally:output.stop_test()
