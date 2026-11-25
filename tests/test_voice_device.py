import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.audio_output import AudioOutput
from services.voice_device import VoiceDevice, device_status


class VoiceDeviceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.speakers = AudioOutput(self.root)
        self.sink = {'name': 'soundbar', 'mute': False, 'volume': {'left': {'value_percent': '40%'}}}
        self.writes = []
        def command(*args):
            if args == ('-f', 'json', 'list', 'sinks'): return json.dumps([self.sink])
            if args == ('get-default-sink',): return 'soundbar'
            self.writes.append(args)
            if args[0] == 'set-sink-volume': self.sink['volume']['left']['value_percent'] = args[2]
            if args[0] == 'set-sink-mute': self.sink['mute'] = args[2] == '1'
        self.speakers.command = command
        self.which = patch('services.audio_output.shutil.which', return_value='/fake/tool')
        self.which.start()
        self.status = Mock(return_value={'components': {'speakers': {'volume_percent': 40}}})
        self.tool = VoiceDevice(self.root, self.speakers, self.status)
        self.scope = {'binding': ['synthetic-account'], 'handle': 'session-one'}

    def tearDown(self):
        self.which.stop()
        self.tmp.cleanup()

    def request(self, name='adjust_device_volume', arguments=None, ident='voice-request-0001'):
        return {'id': ident, 'name': name, 'arguments': arguments if arguments is not None else {'delta': 10},
                'expires_at': time.time() + 60}

    def test_relative_volume_survives_lost_ack_and_executor_restart_without_second_write(self):
        req = self.request()
        result = self.tool.execute(self.scope, req)
        self.assertTrue(result['ok']); self.assertEqual(result['volume_percent'], 50)
        writes = len(self.writes)
        restarted = VoiceDevice(self.root, self.speakers, self.status)
        self.assertEqual(restarted.execute(self.scope, req), result)
        self.assertEqual(len(self.writes), writes)
        self.assertEqual(self.speakers.public()['volume'], 50)
        self.assertNotIn('soundbar', json.dumps(result))

    def test_crash_after_hardware_write_never_reexecutes(self):
        req = self.request()
        original = self.speakers.configure
        def crash(body):
            original(body)
            raise KeyboardInterrupt('simulate power loss before receipt')
        with patch.object(self.speakers, 'configure', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt): self.tool.execute(self.scope, req)
        writes = len(self.writes)
        restarted = VoiceDevice(self.root, self.speakers, self.status)
        result = restarted.execute(self.scope, req)
        self.assertFalse(result['ok']); self.assertEqual(result['code'], 'device_result_unconfirmed')
        self.assertEqual(len(self.writes), writes)

    def test_duplicate_conflict_and_expiry_cannot_change_hardware(self):
        req = self.request()
        self.tool.execute(self.scope, req)
        count = len(self.writes)
        with self.assertRaises(ValueError): self.tool.execute(self.scope, req | {'arguments': {'delta': 20}})
        self.assertFalse(self.tool.execute(self.scope, self.request(ident='expired-request-1') | {'expires_at': 0})['ok'])
        self.assertEqual(len(self.writes), count)

    def test_concurrent_delivery_only_changes_volume_once(self):
        req = self.request()
        second = VoiceDevice(self.root, self.speakers, self.status)
        threads = [threading.Thread(target=tool.execute, args=(self.scope, req)) for tool in (self.tool, second)]
        for t in threads: t.start()
        for t in threads: t.join(5); self.assertFalse(t.is_alive())
        self.assertEqual(len([c for c in self.writes if c[0] == 'set-sink-volume']), 1)
        self.assertEqual(self.speakers.public()['volume'], 50)

    def test_strict_parameters_and_no_device_switch_or_shell(self):
        for name, args in [('adjust_device_volume', {'delta': 0}), ('adjust_device_volume', {'delta': 101}),
                           ('set_device_volume', {'percent': True}), ('set_device_volume', {'percent': -1}),
                           ('set_device_volume', {'percent': '50'}), ('set_device_volume', {'percent': 50, 'device': 'HDMI'}),
                           ('set_device_mute', {'muted': 1}), ('get_device_status', {'path': '/etc'}), ('reboot', {})]:
            with self.subTest(name=name, args=args):
                self.assertFalse(self.tool.execute(self.scope, self.request(name, args))['ok'])
        self.assertEqual(self.writes, [])

    def test_clamping_mute_and_explicit_volume_restore(self):
        result = self.tool.execute(self.scope, self.request(arguments={'delta': -80}))
        self.assertEqual(result['volume_percent'], 0); self.assertFalse(result['audible'])
        result = self.tool.execute(self.scope, self.request('set_device_mute', {'muted': True}, 'voice-request-0002'))
        self.assertTrue(result['muted'])
        result = self.tool.execute(self.scope, self.request('set_device_volume', {'percent': 30}, 'voice-request-0003'))
        self.assertEqual(result['volume_percent'], 30); self.assertTrue(result['audible'])
        result = self.tool.execute(self.scope, self.request(arguments={'delta': 100}, ident='voice-request-0004'))
        self.assertEqual(result['volume_percent'], 100)

    def test_failed_readback_or_missing_output_never_claims_success(self):
        original = self.speakers.command
        self.speakers.command = lambda *args: None if args[0] == 'set-sink-volume' else original(*args)
        self.assertFalse(self.tool.execute(self.scope, self.request())['ok'])
        self.sink['name'] = 'other-speaker'
        self.assertFalse(self.tool.execute(self.scope, self.request(ident='voice-request-0002'))['ok'])
        self.assertFalse(any(c[1] == 'other-speaker' for c in self.writes))

    def test_disconnect_while_setting_zero_is_not_success(self):
        original = self.speakers.command
        def disconnect(*args):
            if args[0] == 'set-sink-volume': self.sink['name'] = 'other-speaker'
            return original(*args)
        self.speakers.command = disconnect
        result = self.tool.execute(self.scope, self.request('set_device_volume', {'percent': 0}))
        self.assertFalse(result['ok'])

    def test_status_never_mutates_or_reads_private_content(self):
        app = SimpleNamespace(
            speakers=self.speakers, store=SimpleNamespace(root=self.root, config=lambda: {'device': 'mic'}),
            audio_devices=lambda: {'devices': [{'id': 'mic', 'label': 'private device label'}]},
            room=SimpleNamespace(account=lambda: {'user_id': 'secret-account', 'name': 'Private Person'}),
            nfc=SimpleNamespace(public=lambda: {'enabled': True, 'state': 'absent', 'assigned': {'talk': True}, 'tag': 'secret-tag'}),
            respeaker=SimpleNamespace(public=lambda: {'connected': True, 'state': 'idle', 'hardware_muted': False}),
            cdb=SimpleNamespace(config=lambda: {'transcription': 'local', 'summary': 'local', 'token': 'secret-token'}),
            live=SimpleNamespace(public=lambda: {'state': 'listening', 'transcript': 'private conversation'}), clock_ready=True)
        with patch('services.device_health.lcd_usb_status', return_value={'state': 'detected'}):
            result = device_status(app)
            self.assertTrue(result['components']['account']['signed_in'])
            self.assertEqual(result['components']['timer_display']['visual_test'], 'not_performed')
            app.audio_devices = Mock(side_effect=OSError('private path'))
            self.assertEqual(device_status(app)['components']['microphone'], {'state': 'unknown'})
        for private in ('secret-', 'private conversation', 'Private Person', 'private device'):
            self.assertNotIn(private, json.dumps(result))
        self.assertEqual(self.writes, [])

    def test_new_module_is_in_clean_image_and_update_allowlist(self):
        from fleet.releases import allowed
        self.assertTrue(allowed('services/voice_device.py'))
