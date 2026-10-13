import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from services.live_audio import PcmGate, native_capture_command

class PcmGateTests(unittest.TestCase):
    def test_muted_audio_is_zero_and_buffer_is_cleared_before_unmute(self):
        gate=PcmGate();speech=b'\x01\x02'*320
        gate.put(speech);self.assertEqual(gate.take(),speech)
        gate.put(speech);gate.mute(True)
        self.assertEqual(gate.take(),bytes(640))
        gate.put(speech);self.assertEqual(gate.take(),bytes(640))
        gate.put(speech);gate.mute(False)
        self.assertEqual(gate.take(),bytes(640))
        gate.put(speech);self.assertEqual(gate.take(),speech)
    def test_block_started_while_muted_is_zero_after_unmute(self):
        gate=PcmGate();speech=b'\x01\x02'*320
        gate.mute(True);epoch,muted=gate.snapshot();gate.mute(False)
        gate.put(speech,epoch,muted)
        self.assertEqual(gate.take(),bytes(640))
        epoch,muted=gate.snapshot();gate.mute(True);gate.mute(False)
        gate.put(speech,epoch,muted)
        self.assertEqual(gate.take(),bytes(640))

    def test_slow_network_has_bounded_latency_not_unbounded_pcm_queue(self):
        gate=PcmGate()
        for n in range(200):gate.put(bytes([n])*640)
        self.assertEqual(gate.frames.qsize(),4)
        self.assertEqual(gate.take(),bytes([196])*640)

class CaptureSourceTests(unittest.TestCase):
    def resolve(self, device, sources, root):
        with patch('services.live_audio.shutil.which', return_value='/usr/bin/tool'), patch('services.live_audio.subprocess.run', return_value=SimpleNamespace(stdout=json.dumps(sources))):
            return native_capture_command({'device':device}, proc_root=root)

    def test_maps_exact_card_id_and_device_not_display_label(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'card2';path.mkdir();(path/'id').write_text('Array\n')
            source={'name':'alsa_input.exact-array','properties':{'alsa.card':'2','alsa.device':'0'}}
            wrong={'name':'another','description':'ReSpeaker','properties':{'alsa.card':'3','alsa.device':'0'}}
            command=self.resolve('plughw:CARD=Array,DEV=0',[wrong,source],root)
            self.assertEqual(command[0],'parec');self.assertIn('--device=alsa_input.exact-array',command)
            self.assertIn('--channels=1',command);self.assertIn('--rate=16000',command)
            self.assertEqual(self.resolve('plughw:2,0',[source],root),command)

    def test_explicit_pulse_source_missing_or_monitor_never_falls_back(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):self.resolve('pulse:missing',[{'name':'other'}],root)
            with self.assertRaises(ValueError):self.resolve('pulse:other.monitor',[{'name':'other.monitor'}],root)
            command=self.resolve('pulse:bluez_input.known',[{'name':'bluez_input.known'}],root)
            self.assertIn('--device=bluez_input.known',command)

    def test_unmapped_alsa_remains_exact_original_device_and_ambiguity_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            command=self.resolve('plughw:4,0',[{'name':'other'}],root)
            self.assertEqual(command[0],'arecord');self.assertIn('plughw:4,0',command)
            rows=[{'name':name,'properties':{'alsa.card':'4','alsa.device':'0'}} for name in ['first','second']]
            with self.assertRaises(ValueError):self.resolve('plughw:4,0',rows,root)

if __name__=='__main__':unittest.main()
