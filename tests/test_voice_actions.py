import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.voice_actions import VoiceActions, valid_action
from services.voice_device import VoiceDevice
from services.schedules import Schedules
from services.lcd_display import snapshot


class VoiceActionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = 100.
        self.account = {'user_id': 'test-user', 'client_id': 'test-tenant'}
        self.schedules = Schedules(self.root, lambda: self.now, lambda: self.now, 'boot')
        self.schedules.room_policy = lambda: (True, self.account)
        self.app = SimpleNamespace(room=SimpleNamespace(account=lambda: self.account, epoch='epoch', require_operator=Mock()),
            live=SimpleNamespace(generation=1, lock=threading.RLock(), end=Mock()), schedules=self.schedules,
            speakers=Mock(), playback_leases={}, countdown=None, require=Mock(), store=Mock())
        self.actions = VoiceActions(self.app, clock=lambda: self.now)
        self.executor = VoiceDevice(self.root, self.app.speakers, Mock(), actions=self.actions)
        self.reqnum = 0

    def tearDown(self): self.tmp.cleanup()

    def request(self, name, args=None):
        self.reqnum += 1
        return {'id': f'request-{self.reqnum:016d}', 'name': name, 'arguments': args or {}, 'expires_at': time.time()+60}

    def offer(self, name, args=None):
        self.req = self.request(name, args)
        return self.actions.request({}, self.req)

    def touch(self, action): return self.actions.touch({'id': self.req['id'], 'action': action})

    def timer(self, label='Test'):
        return self.schedules.create({'kind':'timer','label':label,'seconds':50,'request_id':label+'-request'})['id']

    def test_strict_allowlist_has_no_urls_shell_power_or_unbounded_topics(self):
        for name,args in [('open_device_help',{'topic':'https://evil.example'}),('show_device_timer',{'id':''}),
                          ('show_device_clock',{'force':True}),('prepare_device_move',{'confirm':True}),('shutdown',{})]:
            self.assertFalse(valid_action(name,args))

    def test_one_timer_auto_selection_and_multiple_timers_require_choice(self):
        one = self.timer()
        self.assertTrue(self.offer('show_device_timer',{'id':'current'})['ok'])
        self.assertEqual(self.actions.public()['data']['timer_id'],one)
        two = self.timer('Other')
        self.assertEqual(self.offer('show_device_timer',{'id':'current'})['code'],'choose_timer')
        self.assertTrue(self.offer('show_device_timer',{'id':two})['ok'])
        self.assertEqual(self.actions.project_lcd(snapshot(self.schedules,True))['timers'][0]['id'],two)

    def test_foreign_timer_never_becomes_visible(self):
        ident=self.timer();self.account={'user_id':'other','client_id':'test-tenant'}
        with self.assertRaises(ValueError): self.offer('show_device_timer',{'id':ident})

    def test_clock_changes_presentation_not_timer_and_due_alarm_wins(self):
        self.timer();before=self.schedules.path.read_bytes()
        self.offer('show_device_clock')
        self.assertEqual(self.actions.project_lcd(snapshot(self.schedules,True))['timers'],[])
        self.assertEqual(before,self.schedules.path.read_bytes())
        self.now += 51;self.schedules.tick()
        self.assertEqual(self.actions.project_lcd(snapshot(self.schedules,True))['timers'][0]['state'],'due')

    def test_logout_epoch_change_and_expiry_revoke_pending_actions_and_lcd(self):
        self.timer();self.offer('show_device_clock');self.app.room.epoch='new-epoch'
        self.assertIsNone(self.actions.public())
        self.assertEqual(len(self.actions.project_lcd(snapshot(self.schedules,True))['timers']),1)
        self.offer('prepare_device_move');self.now+=121
        with self.assertRaises(ValueError): self.touch('end_talk')
        self.app.live.end.assert_not_called()

    def test_help_is_local_article_and_does_not_stop_talk(self):
        self.offer('open_device_help',{'topic':'kabel'})
        self.assertEqual(self.actions.public()['data']['article']['id'],'kabel')
        self.app.live.end.assert_not_called()
        self.app.speakers.start_test.assert_not_called()
        self.assertNotIn('test-user',json.dumps(self.actions.public()))

    def test_prepare_is_idempotent_and_never_plays_or_powers_off(self):
        req=self.request('prepare_speaker_test')
        scope={'handle':'one'}
        self.assertTrue(self.executor.execute(scope,req)['confirmation_required'])
        self.actions.touch({'id':req['id'],'action':'dismiss'})
        self.assertTrue(self.executor.execute(scope,req)['ok'])
        self.assertIsNone(self.actions.public())
        self.app.live.end.assert_not_called();self.app.speakers.start_test.assert_not_called()

    def test_pending_confirmation_cannot_be_replaced_or_close_a_new_talk(self):
        self.offer('prepare_device_move');original=self.req
        self.assertFalse(self.actions.request({},self.request('open_device_help',{'topic':'audio'}))['ok'])
        self.app.live.generation=2
        with self.assertRaises(ValueError): self.actions.touch({'id':original['id'],'action':'end_talk'})
        self.app.live.end.assert_not_called()
        with self.assertRaises(ValueError): self.actions.touch({'id':original['id'],'action':'shutdown'})

    def test_test_requires_idle_operator_and_fresh_explicit_human_confirmation(self):
        self.offer('prepare_speaker_test')
        self.app.require.side_effect=ValueError('Talk läuft')
        with self.assertRaises(ValueError): self.touch('start_test')
        self.app.speakers.start_test.assert_not_called()
        self.app.require.side_effect=None;self.app.room.require_operator.side_effect=ValueError('PIN')
        with self.assertRaises(ValueError): self.touch('start_test')
        self.app.room.require_operator.side_effect=None
        self.app.speakers.start_test.return_value={'id':'one','state':'running'}
        self.assertEqual(self.touch('start_test')['stage'],'testing')
        with self.assertRaises(ValueError): self.touch('start_test')
        self.app.speakers.test_status.return_value={'id':'one','state':'running'}
        with self.assertRaises(ValueError): self.touch('heard')
        self.app.speakers.test_status.return_value={'id':'other','state':'completed'}
        with self.assertRaises(ValueError): self.touch('heard')
        self.app.speakers.test_status.return_value={'id':'one','state':'completed'}
        self.assertEqual(self.touch('not_heard')['stage'],'not_heard')
        self.app.speakers.start_test.assert_called_once()

    def test_readiness_unknown_never_claims_ready_and_starts_nothing(self):
        components={'account':{'signed_in':True},'microphone':{'state':'unknown'},'storage':{},
                    'speakers':{'audible_expected':True},'respeaker_leds':{},'processing':{'transcription':'local'}}
        with patch('services.voice_device.device_status',return_value={'components':components}):
            result=self.offer('check_meeting_readiness')
        self.assertFalse(result['can_start_now'])
        self.assertTrue(any(c['state']=='unknown' for c in result['checks']))
        self.app.speakers.start_test.assert_not_called();self.app.live.end.assert_not_called()
