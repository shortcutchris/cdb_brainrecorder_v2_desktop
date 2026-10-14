import array
import json
import tempfile
import time
import unittest
import wave
from pathlib import Path
from unittest.mock import patch, Mock
from services.audio_output import AudioOutput


class SpeakersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.output = AudioOutput(self.root)
        self.sink = {'name':'usb-speaker','description':'USB Audio','mute':False,
                     'volume':{'left':{'value_percent':'45%'}},'properties':{}}
        self.commands = []
        def command(*args):
            self.commands.append(args)
            if args == ('-f','json','list','sinks'):return json.dumps([self.sink])
            if args == ('get-default-sink',):return 'usb-speaker'
            if args[0] == 'set-sink-volume':self.sink['volume']['left']['value_percent']=args[2]
            if args[0] == 'set-sink-mute':self.sink['mute']=args[2]=='1'
            return ''
        self.output.command = command
        self.which = patch('services.audio_output.shutil.which',return_value='/usr/bin/tool');self.which.start()
    def tearDown(self):
        self.output.stop_test();self.which.stop();self.tmp.cleanup()
    def test_dummy_sink_is_not_a_speaker(self):
        self.sink['name']='auto_null'
        self.assertFalse(self.output.public()['available'])
        with self.assertRaises(ValueError):self.output.start_test()
    def test_ignored_hardware_volume_is_not_reported_as_success(self):
        original=self.output.command
        self.output.command=lambda *args: '' if args[0]=='set-sink-volume' else original(*args)
        with self.assertRaisesRegex(ValueError,'nicht übernommen'):
            self.output.configure({'volume':80})

    def test_selection_persists_and_missing_device_does_not_fall_back(self):
        self.output.configure({'device':'usb-speaker'})
        self.assertEqual(AudioOutput(self.root).saved_device(),'usb-speaker')
        self.sink['name']='hdmi-other'
        self.assertFalse(self.output.public()['available'])
        with self.assertRaises(ValueError):self.output.configure({'volume':50})
        self.assertNotIn(('set-sink-volume','hdmi-other','50%'),self.commands)
    def test_only_enumerated_sinks_and_bounded_values_can_be_changed(self):
        for payload in ({'device':'--help'},{'volume':101},{'volume':-1},{'volume':True},{'muted':'false'},{'untrusted':True}):
            with self.assertRaises(ValueError):self.output.configure(payload)
        self.assertFalse(any(c[0].startswith('set-') for c in self.commands))
        result=self.output.configure({'volume':50,'muted':True})
        self.assertEqual(result['volume'],50);self.assertTrue(result['muted'])
        with self.assertRaises(ValueError):self.output.start_test()
    def test_two_second_tone_is_bounded_stereo_with_separate_channels(self):
        path=self.root/'test.wav';self.output.write_tone(path)
        with wave.open(str(path)) as f:
            self.assertEqual((f.getnchannels(),f.getframerate(),f.getnframes()),(2,24000,48000))
            data=array.array('h',f.readframes(f.getnframes()))
        self.assertLessEqual(max(abs(n) for n in data),6000)
        self.assertTrue(any(data[:24000:2]));self.assertFalse(any(data[1:24000:2]))
        self.assertFalse(any(data[48000::2]));self.assertTrue(any(data[48001::2]))
    def test_playback_runs_on_selected_pi_sink_and_reports_failure(self):
        fake=Mock();fake.wait.return_value=1;fake.poll.return_value=1
        with patch('services.audio_output.subprocess.Popen',return_value=fake) as popen:
            self.output.start_test();self.output.thread.join(2)
            self.assertEqual(self.output.test_status()['state'],'failed')
            self.assertEqual(popen.call_args.args[0][:2],['paplay','--device=usb-speaker'])
    def test_running_tone_blocks_changes_and_stop_cancels_process(self):
        import threading
        ended=threading.Event();started=threading.Event()
        fake=Mock();fake.poll.return_value=None
        fake.wait.side_effect=lambda **_: (started.set(),ended.wait(3),0)[2]
        fake.terminate.side_effect=ended.set
        with patch('services.audio_output.subprocess.Popen',return_value=fake):
            self.output.start_test();self.assertTrue(started.wait(2))
            with self.assertRaises(ValueError):self.output.configure({'volume':90})
            with self.assertRaises(ValueError):self.output.start_test()
            self.assertEqual(self.output.stop_test()['state'],'cancelled')
            fake.terminate.assert_called_once()


class AlarmDurationTests(unittest.TestCase):
    def test_alarm_repeats_for_one_minute_preview_stays_short(self):
        from services.alarm_tones import write_alarm
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'alarm.wav'
            write_alarm(path,'bell',60)
            with wave.open(str(path)) as audio:
                self.assertEqual(audio.getnframes()/audio.getframerate(),60)
                first=audio.readframes(72000);self.assertTrue(any(first))
                self.assertFalse(any(audio.readframes(24000)))
                self.assertEqual(audio.readframes(72000),first)
            write_alarm(path,'bell')
            with wave.open(str(path)) as audio:self.assertEqual(audio.getnframes()/audio.getframerate(),3)
            with self.assertRaises(ValueError):write_alarm(path,'bell',3600)
