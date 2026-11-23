import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from services.nfc_tokens import NfcTokens


class TokensTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.now=10.;self.sample={'state':'absent'}
        self.reader=Mock();self.reader.snapshot.side_effect=lambda:dict(self.sample)
        self.n=NfcTokens(self.tmp.name,self.reader,lambda:self.now)
        self.n.tags={'talk':'a'*64,'meeting':'b'*64};self.n.enabled=True
        self.start=Mock(return_value='session-1');self.stop=Mock();self.alive=Mock(return_value=True)
    def tick(self,state,tag=None,seconds=.5):
        self.now+=seconds;self.sample={'state':state,'tag':tag}
        self.n.tick(self.start,self.stop,self.alive)
    def arm(self):
        self.tick('absent');self.tick('absent',seconds=1.5)
    def place(self,mode='meeting'):
        self.tick('present',self.n.tags[mode]);self.tick('present',self.n.tags[mode])
    def test_startup_held_no_start_then_single_start_and_debounced_stop(self):
        self.place();self.start.assert_not_called()
        self.arm();self.place();self.start.assert_called_once_with('meeting')
        for _ in range(20):self.tick('present','b'*64)
        self.start.assert_called_once();self.tick('absent');self.tick('present','b'*64)
        self.stop.assert_not_called();self.arm();self.stop.assert_called_once_with('meeting','session-1')
    def test_disconnect_is_not_removal_and_reconnect_held_no_duplicate(self):
        self.arm();self.place()
        for _ in range(10):self.tick('error')
        self.stop.assert_not_called();self.place();self.start.assert_called_once()
        self.arm();self.stop.assert_called_once()
    def test_error_breaks_removal_timer(self):
        self.arm();self.place();self.tick('absent');self.tick('error',seconds=5)
        self.tick('absent');self.stop.assert_not_called()
        self.tick('absent',seconds=1.5);self.stop.assert_called_once()
    def test_manual_stop_requires_remove_even_if_another_session_is_active(self):
        self.arm();self.place();self.alive.return_value=False
        self.place();self.start.assert_called_once();self.arm();self.stop.assert_not_called()
        self.place('talk');self.assertEqual(self.start.call_count,2)
    def test_different_or_unknown_tag_never_switches_active_mode(self):
        self.arm();self.place();self.place('talk');self.tick('present','c'*64,seconds=3)
        self.start.assert_called_once();self.stop.assert_not_called()
        self.arm();self.stop.assert_called_once_with('meeting','session-1')
    def test_blocked_start_does_not_retry_held_token(self):
        self.start.side_effect=ValueError('Aufnahme läuft.')
        self.arm();self.place();self.place();self.start.assert_called_once()
        self.assertIsNone(self.n.owner)
    def test_disable_does_not_stop_capture_or_change_wake_preferences(self):
        p=Path(self.tmp.name)/'wake-word.json';p.write_text('{"enabled":true}')
        self.arm();self.place();self.n.configure({'action':'off'});self.arm()
        self.stop.assert_not_called();self.assertEqual(p.read_text(),'{"enabled":true}')
        self.assertFalse(NfcTokens(self.tmp.name,self.reader).enabled)
    def test_enrollment_distinct_tags_no_raw_id_in_public_state(self):
        self.n.enabled=False;self.sample={'state':'present','tag':'a'*64}
        with self.assertRaises(ValueError):self.n.configure({'action':'enroll','mode':'meeting'})
        self.sample['tag']='c'*64;self.n.configure({'action':'enroll','mode':'meeting'})
        self.assertNotIn('c'*64,json.dumps(self.n.public()))
        restored=NfcTokens(self.tmp.name,self.reader);self.assertEqual(restored.tags['meeting'],'c'*64)
    def test_failed_settings_write_never_enables_in_memory(self):
        self.n.enabled=False
        with patch('services.nfc_tokens.atomic_write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.n.configure({'action':'on'})
        self.assertFalse(self.n.enabled)

    def test_factory_default_is_off_without_starting_reader(self):
        n=NfcTokens(Path(self.tmp.name)/'fresh',self.reader)
        self.assertFalse(n.enabled);self.reader.start.assert_not_called()
        self.assertEqual(n.direct_start,{'talk':False,'meeting':False})
        self.assertEqual(n.stop_on_remove,{'talk':True,'meeting':True})

    def test_remove_to_stop_setting_persists_without_changing_other_mode_or_tags(self):
        self.n.configure({'action':'stop-on-remove','mode':'meeting','enabled':False})
        restored=NfcTokens(self.tmp.name,self.reader)
        self.assertEqual(restored.stop_on_remove,{'talk':True,'meeting':False})
        self.assertEqual(restored.tags,self.n.tags)
        self.assertEqual(restored.direct_start,self.n.direct_start)

    def test_disabled_removal_keeps_owner_until_manual_end_for_both_modes(self):
        for mode in ('talk','meeting'):
            with self.subTest(mode=mode):
                self.n.owner=None;self.n.reset_edge();self.start.reset_mock();self.stop.reset_mock()
                self.alive.return_value=True
                self.n.configure({'action':'stop-on-remove','mode':mode,'enabled':False})
                self.arm();self.place(mode);self.arm();self.tick('absent',seconds=30)
                self.stop.assert_not_called();self.assertEqual(self.n.owner,(mode,'session-1'))
                self.assertIn('Am Bildschirm beenden',self.n.public()['message'])
                self.place('talk' if mode=='meeting' else 'meeting')
                self.start.assert_called_once_with(mode)
                self.alive.return_value=False;self.tick('absent');self.tick('absent',seconds=2)
                self.assertIsNone(self.n.owner);self.stop.assert_not_called()
                self.alive.return_value=True;self.place(mode)
                self.assertEqual(self.start.call_count,2)

    def test_remove_to_stop_failed_save_invalid_values_and_active_owner(self):
        with patch('services.nfc_tokens.atomic_write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.n.configure({'action':'stop-on-remove','mode':'talk','enabled':False})
        self.assertTrue(self.n.stop_on_remove['talk'])
        for value in ('false',0,None):
            with self.assertRaises(ValueError):self.n.configure({'action':'stop-on-remove','mode':'talk','enabled':value})
        self.arm();self.place('talk')
        with self.assertRaises(ValueError):self.n.configure({'action':'stop-on-remove','mode':'talk','enabled':False})
        self.arm();self.stop.assert_called_once_with('talk','session-1')

    def test_direct_start_persists_per_mode_and_rearms_only_after_removal(self):
        self.arm()
        self.n.configure({'action':'direct-start','mode':'meeting','enabled':True})
        self.assertFalse(self.n.armed)
        self.place();self.start.assert_not_called()
        self.assertEqual(NfcTokens(self.tmp.name,self.reader).direct_start,{'talk':False,'meeting':True})
        self.assertEqual(NfcTokens(self.tmp.name,self.reader).tags,self.n.tags)
        self.arm();self.place();self.start.assert_called_once()

    def test_direct_start_failed_save_rolls_back_and_rejects_non_boolean(self):
        with patch('services.nfc_tokens.atomic_write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.n.configure({'action':'direct-start','mode':'talk','enabled':True})
        self.assertFalse(self.n.direct_start['talk'])
        for value in ('true',1,None):
            with self.assertRaises(ValueError):self.n.configure({'action':'direct-start','mode':'talk','enabled':value})

    def test_upgrade_preserves_tags_without_enabling_direct_start(self):
        self.n.path.write_text(json.dumps({'enabled':True,'tags':self.n.tags}))
        upgraded=NfcTokens(self.tmp.name,self.reader)
        self.assertTrue(upgraded.enabled);self.assertEqual(upgraded.tags,self.n.tags)
        self.assertEqual(upgraded.direct_start,{'talk':False,'meeting':False})
        self.assertEqual(upgraded.stop_on_remove,{'talk':True,'meeting':True})


class OwnershipTests(unittest.TestCase):
    def test_replaced_recording_or_live_is_not_stopped(self):
        from web_server import StudioApp
        app=Mock();app.nfc_still_owned=Mock(return_value=False)
        StudioApp.nfc_stop(app,'meeting','old');StudioApp.nfc_stop(app,'talk','old')
        app.action.assert_not_called();app.live.end.assert_not_called()
    def test_meeting_uses_existing_start_and_stop(self):
        from web_server import StudioApp
        app=Mock();app.room.enabled=False;app.wake_reason.return_value='';app.action.return_value={'id':'same-engine'}
        self.assertEqual(StudioApp.nfc_start(app,'meeting'),'same-engine')
        app.action.assert_called_once_with('/api/record/start',{})
        app.nfc_still_owned.return_value=True;StudioApp.nfc_stop(app,'meeting','same-engine')
        self.assertEqual(app.action.call_args.args,('/api/record/stop',{}))


if __name__=='__main__':unittest.main()
