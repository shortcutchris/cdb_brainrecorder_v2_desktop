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



class ReadyToneTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import asyncio, threading, sys
        from services.live_audio import NativeLiveAudio
        self.audio=NativeLiveAudio.__new__(NativeLiveAudio)
        self.audio.closed=threading.Event();self.audio.tasks=set();self.audio.processes=[]
        self.audio.ready_tone_started=False;self.audio.ready_tone_state='waiting'
        self.audio.connecting_task=None;self.audio.connecting_stop=asyncio.Event()
        self.audio.connecting_tone_state='waiting';self.audio.connecting_blocks=0
        self.audio.startup_input_blocked=True;self.audio.gate=PcmGate()
        self.audio.session_started=asyncio.Event();self.audio.session_started.set()
        self.audio.greeting_ack=asyncio.Event();self.audio.greeting_id=None;self.audio.greeting_expected=None;self.audio.greeting_state='waiting'
        self.commands=[]
        def send(raw):
            event=json.loads(raw);self.commands.append(event)
            self.audio._welcome_event({'type':event['type']+'ed','client_event_id':event['event_id']})
        self.audio.channel=SimpleNamespace(readyState='open',send=send)
        self.audio.peer=SimpleNamespace(connectionState='connecting')
        self.tmp=tempfile.TemporaryDirectory();self.output=Path(self.tmp.name)/'cue.pcm'
        self.audio.playback_command=[sys.executable,'-c',
            'import sys;from pathlib import Path;Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())',str(self.output)]

    async def asyncTearDown(self):
        import asyncio
        for task in list(self.audio.tasks):task.cancel()
        if self.audio.tasks:await asyncio.gather(*self.audio.tasks,return_exceptions=True)
        self.tmp.cleanup()

    async def test_chime_only_after_connected_once_and_real_pcm_is_written(self):
        import asyncio
        from services.live_audio import ready_tone_pcm
        self.audio._connection_changed()
        self.assertFalse(self.audio.ready_tone_started)
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        self.audio._connection_changed()
        self.assertEqual(len(self.audio.tasks),1)
        await asyncio.gather(*self.audio.tasks)
        self.assertEqual(self.audio.ready_tone_state,'played')
        self.assertEqual(self.output.read_bytes(),ready_tone_pcm())
        self.assertEqual(len(self.output.read_bytes()),8640*2)
        self.assertFalse(self.audio.processes)
        self.audio.peer.connectionState='disconnected';self.audio._connection_changed()
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        self.assertFalse(self.audio.tasks)
        self.assertEqual(len(self.commands),2)
        self.assertEqual(self.audio.greeting_state,'accepted')

    async def test_failed_connection_and_closed_session_never_signal_ready(self):
        from unittest.mock import Mock
        self.audio._fail=Mock();self.audio.peer.connectionState='failed'
        self.audio._connection_changed();self.audio._fail.assert_called_once()
        self.assertFalse(self.audio.ready_tone_started)
        self.audio.closed.set();self.audio.peer.connectionState='connected'
        self.audio._connection_changed();self.assertFalse(self.audio.tasks)

    async def test_optional_chime_failure_does_not_end_live(self):
        import asyncio
        from unittest.mock import Mock
        self.audio._fail=Mock();self.audio.playback_command=['/missing/test-cue-player']
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        await asyncio.gather(*self.audio.tasks)
        self.assertEqual(self.audio.ready_tone_state,'failed')
        self.audio._fail.assert_not_called();self.assertFalse(self.audio.closed.is_set())

    async def test_close_cancels_pending_chime_and_reaps_process(self):
        import asyncio, sys
        self.audio.playback_command=[sys.executable,'-c','import time;time.sleep(10)']
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        for _ in range(100):
            if self.audio.processes:break
            await asyncio.sleep(.01)
        self.assertTrue(self.audio.processes)
        processes=list(self.audio.processes)
        self.audio.closed.set()
        tasks=list(self.audio.tasks)
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        self.assertEqual(self.audio.ready_tone_state,'cancelled')
        self.assertTrue(all(p.returncode is not None for p in processes))
        self.assertFalse(self.audio.processes)

    async def test_loop_stops_before_ready_cue_and_greeting(self):
        import asyncio
        self.audio.connecting_task=self.audio._task(self.audio._connecting_tone())
        for _ in range(100):
            if self.audio.connecting_blocks >= 3: break
            await asyncio.sleep(.01)
        self.assertGreater(self.audio.connecting_blocks,0)
        self.assertTrue(self.audio.startup_input_blocked)
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        await asyncio.gather(*self.audio.tasks)
        self.assertEqual(self.audio.connecting_tone_state,'stopped')
        self.assertEqual(self.audio.greeting_state,'accepted')
        self.assertFalse(self.audio.startup_input_blocked)
        self.assertFalse(self.audio.processes)

    async def test_cancel_during_connecting_reaps_loop_without_greeting(self):
        import asyncio
        task=self.audio._task(self.audio._connecting_tone())
        for _ in range(100):
            if self.audio.connecting_blocks:break
            await asyncio.sleep(.01)
        processes=list(self.audio.processes)
        self.audio.closed.set();task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        self.assertFalse(self.commands)
        self.assertFalse(self.audio.processes)
        self.assertTrue(all(p.returncode is not None for p in processes))

    async def test_welcome_waits_for_provider_session_and_keeps_user_mute(self):
        import asyncio
        self.audio.session_started.clear();self.audio.gate.mute(True)
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        await asyncio.sleep(.2)
        self.assertFalse(self.commands)
        self.audio._welcome_event({'type':'session.started'})
        await asyncio.gather(*self.audio.tasks)
        self.assertEqual(len(self.commands),2)
        self.assertTrue(self.audio.gate.muted)
        self.assertIn('Hallo, wie kann ich dir helfen?',self.commands[1]['content'])

    async def test_welcome_only_accepts_matching_ack_and_never_retries_rejection(self):
        import asyncio
        self.audio.channel.send=lambda raw:self.commands.append(json.loads(raw))
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        for _ in range(100):
            if self.commands:break
            await asyncio.sleep(.01)
        self.audio._welcome_event({'type':'session.instructions.appended','client_event_id':'wrong'})
        self.assertFalse(self.audio.greeting_ack.is_set())
        self.audio._welcome_event({'type':'error','error':{'client_event_id':self.audio.greeting_id}})
        await asyncio.gather(*self.audio.tasks)
        self.assertEqual(self.audio.greeting_state,'rejected')
        self.assertEqual(len(self.commands),1)
        self.assertFalse(self.audio.closed.is_set())

    async def test_greeting_speech_waits_for_instruction_ack_and_ignores_stale_ack(self):
        import asyncio
        self.audio.channel.send=lambda raw:self.commands.append(json.loads(raw))
        self.audio.peer.connectionState='connected';self.audio._connection_changed()
        for _ in range(100):
            if self.commands:break
            await asyncio.sleep(.01)
        instruction=self.commands[0]
        self.assertEqual(instruction['type'],'session.instructions.append')
        self.assertEqual(len(self.commands),1)
        self.audio._welcome_event({'type':'session.instructions.appended','client_event_id':instruction['event_id']})
        for _ in range(100):
            if len(self.commands)==2:break
            await asyncio.sleep(.01)
        speech=self.commands[1]
        self.assertEqual(speech['type'],'session.commentary.append')
        self.assertEqual(speech['content'],'Hallo, wie kann ich dir helfen?')
        self.assertNotEqual(instruction['event_id'],speech['event_id'])
        self.audio._welcome_event({'type':'session.instructions.appended','client_event_id':instruction['event_id']})
        self.assertFalse(self.audio.greeting_ack.is_set())
        self.audio._welcome_event({'type':'session.commentary.appended','client_event_id':speech['event_id']})
        await asyncio.gather(*self.audio.tasks)
        self.assertEqual(self.audio.greeting_state,'accepted')
        self.audio._connection_changed()
        self.assertEqual(len(self.commands),2)

if __name__=='__main__':unittest.main()
