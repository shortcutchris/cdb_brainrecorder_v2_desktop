"""Native Pi WebRTC audio, without browser permissions or audio files.

Only the configured ALSA/Pulse input and PipeWire output are used. Audio subprocesses
are parent-owned; microphone frames are continuously drained into an 80 ms queue.
"""
import asyncio
from array import array
import sys
from fractions import Fraction
import importlib.util
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import queue
import signal
import threading
import time
from services.live_feedback import AudioEnvelope, SearchInputEnvelope, SearchActivity, web_search_event, search_loop_pcm

from meeting_recorder.audio import Recorder
from meeting_recorder.child_process import owned_command


def native_capture_command(config, *, proc_root='/proc/asound'):
    """Use the exact ALSA card's PipeWire source to share duplex USB hardware.

    Never chooses a default source or matches a display name. Without a mapped
    source the original explicit ALSA device remains the only fallback.
    """
    device = config['device']
    direct_pulse = device.startswith('pulse:')
    if not shutil.which('parec') or not shutil.which('pactl'):
        if direct_pulse: raise ValueError('Pulse-Audioaufnahme benötigt parec und pactl auf dem Pi.')
        return Recorder.command(config)
    try:
        result = subprocess.run(['pactl', '-f', 'json', 'list', 'sources'], capture_output=True,
                                text=True, check=True, timeout=4)
        sources = json.loads(result.stdout)
        if not isinstance(sources, list): raise ValueError('Invalid source list')
    except (OSError, subprocess.SubprocessError, ValueError):
        if direct_pulse: raise ValueError('Gewählte Audioquelle am Pi nicht erreichbar.') from None
        return Recorder.command(config)
    sources = [s for s in sources if isinstance(s, dict) and isinstance(s.get('name'), str)
               and not s['name'].endswith('.monitor') and s.get('properties', {}).get('device.class') != 'monitor']
    if direct_pulse:
        matches = [s for s in sources if s['name'] == device[6:]]
        if not matches: raise ValueError('Gewählte Audioquelle am Pi ist nicht verbunden.')
    else:
        match = re.fullmatch(r'(?:plug)?hw:(?:CARD=)?([^,]+),(?:DEV=)?([0-9]+)', device)
        if not match: return Recorder.command(config)
        card, number = match.groups()
        if not card.isdigit():
            cards = []
            for path in Path(proc_root).glob('card[0-9]*/id'):
                try:
                    if path.read_text().strip() == card: cards.append(path.parent.name[4:])
                except OSError: continue
            if len(cards) != 1: return Recorder.command(config)
            card = cards[0]
        matches = [s for s in sources if str(s.get('properties', {}).get('alsa.card')) == card
                   and str(s.get('properties', {}).get('alsa.device')) == number]
        if not matches: return Recorder.command(config)
    if len(matches) != 1: raise ValueError('Mehrere Audioquellen passen zum Mikrofon. Audioeinstellungen prüfen.')
    return ['parec', '--device=' + matches[0]['name'], '--raw', '--format=s16le', '--rate=16000',
            '--channels=1', '--latency-msec=40']


class PcmGate:
    """Bounded capture buffer. Muted/stale blocks can never reappear after unmute."""
    def __init__(self):
        self.lock = threading.Lock()
        self.frames = queue.Queue(maxsize=4)
        self.muted = False
        self.epoch = 0

    def mute(self, value):
        with self.lock:
            self.muted = value
            self.epoch += 1
            while not self.frames.empty():
                try: self.frames.get_nowait()
                except queue.Empty: break

    def snapshot(self):
        with self.lock: return self.epoch, self.muted

    def put(self, block, captured_epoch=None, captured_muted=False):
        with self.lock:
            if self.muted or captured_muted or (captured_epoch is not None and captured_epoch != self.epoch):
                block = bytes(len(block))
            if self.frames.full(): self.frames.get_nowait()
            self.frames.put_nowait((self.epoch, block))

    def take(self):
        with self.lock:
            try: epoch, block = self.frames.get_nowait()
            except queue.Empty: return bytes(640)
            return bytes(len(block)) if self.muted or epoch != self.epoch else block


class NativeLiveAudio:
    @staticmethod
    def available():
        return importlib.util.find_spec('aiortc') is not None and importlib.util.find_spec('av') is not None

    def __init__(self, config, on_failure=None, *, capture_command=None, playback_command=None):
        self.config = dict(config)
        self.on_failure = on_failure or (lambda: None)
        self.capture_command = capture_command or native_capture_command(config)
        self.playback_command = playback_command or ['paplay', '--raw', '--format=s16le', '--rate=24000',
                                                     '--channels=1', '--latency-msec=80', '--device=' + config['speaker']]
        self.gate = PcmGate()
        self.input_meter=SearchInputEnvelope();self.output_meter=AudioEnvelope();self.searches=SearchActivity()
        self.search_sound=True;self.cue_task=None;self.cue_serial=0;self.cue_requested_at=0;self.user_speech_at=0;self.search_loop_blocks=0;self.search_loop_pauses=0;self.web_event_count=0;self.event_types={};self.search_tones=0
        self.closed = threading.Event()
        self.loop = asyncio.new_event_loop()
        self.processes = []
        self.tasks = set()
        self.peer = None
        self.opening_task = None
        self.received_frames = 0
        self.captured_frames = 0
        self.sent_frames = 0
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.close_lock = threading.Lock()
        self.failure_sent = False

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for task in pending: task.cancel()
        if pending: self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def _submit(self, coroutine, timeout=12):
        if self.closed.is_set():
            coroutine.close()
            raise ValueError('Pi-Audio wurde beendet.')
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        try: return future.result(timeout)
        except TimeoutError:
            future.cancel()
            raise

    async def _spawn(self, command, **kwargs):
        process = await asyncio.create_subprocess_exec(*owned_command(command), start_new_session=True,
                                                       stderr=asyncio.subprocess.DEVNULL, **kwargs)
        self.processes.append(process)
        if self.closed.is_set():
            await self._terminate(process)
            raise asyncio.CancelledError()
        return process

    def _task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def _fail(self):
        if not self.closed.is_set() and not self.failure_sent:
            self.failure_sent = True
            # Service cleanup may synchronously wait for this event loop.
            threading.Thread(target=self.on_failure, daemon=True).start()

    async def _open(self):
        self.opening_task = asyncio.current_task()
        from aiortc import AudioStreamTrack, RTCPeerConnection
        import av
        transport = self
        capture = await self._spawn(self.capture_command, stdout=asyncio.subprocess.PIPE, limit=2560)
        playback = await self._spawn(self.playback_command, stdin=asyncio.subprocess.PIPE)
        playback.stdin.transport.set_write_buffer_limits(high=9600, low=4800)
        first = asyncio.Event()
        async def watch_output():
            await playback.wait()
            self._fail()
        self._task(watch_output())

        async def read_capture():
            try:
                while not self.closed.is_set():
                    epoch, muted = self.gate.snapshot()
                    block = await asyncio.wait_for(capture.stdout.readexactly(640), 3)
                    self.gate.put(block, epoch, muted)
                    self.captured_frames += 1
                    first.set()
            except asyncio.CancelledError: raise
            except Exception: self._fail()
        self._task(read_capture())
        await asyncio.wait_for(first.wait(), 4)
        if capture.returncode is not None or playback.returncode is not None:
            raise ValueError('Mikrofon oder Lautsprecher am Pi nicht verfügbar.')

        class InputTrack(AudioStreamTrack):
            def __init__(self):
                super().__init__(); self.samples = 0; self.origin = None
            async def recv(self):
                if transport.closed.is_set():
                    from aiortc.mediastreams import MediaStreamError
                    raise MediaStreamError
                now = asyncio.get_running_loop().time()
                if self.origin is None: self.origin = now
                await asyncio.sleep(max(0, self.origin + self.samples / 16000 - now))
                frame = av.AudioFrame(format='s16', layout='mono', samples=320)
                block=transport.gate.take()
                transport.input_meter.feed(block)
                frame.planes[0].update(block)
                transport.sent_frames += 1
                frame.sample_rate = 16000; frame.pts = self.samples; frame.time_base = Fraction(1, 16000)
                self.samples += 320
                return frame

        self.peer = RTCPeerConnection()
        self.peer.addTransceiver(InputTrack(), direction='sendrecv')
        channel=self.peer.createDataChannel('oai-events')  # Read-only: never send commands.
        @channel.on('message')
        def provider_event(message):
            if not isinstance(message,str) or len(message)>1_000_000:return
            try:event=json.loads(message)
            except (ValueError,TypeError):return
            if isinstance(event,dict):
                name=event.get('type','')
                if name=='response.event' and isinstance(event.get('event'),dict):name+=':'+str(event['event'].get('type',''))
                if isinstance(name,str) and re.fullmatch(r'[a-zA-Z_.:]{1,100}',name) and (name in self.event_types or len(self.event_types)<64):self.event_types[name]=self.event_types.get(name,0)+1
            found=web_search_event(event)
            if found:
                self.web_event_count+=1
                self.update_search('web',*found)
        @self.peer.on('connectionstatechange')
        def state_changed():
            if self.peer.connectionState == 'failed': self._fail()
        @self.peer.on('track')
        def track_received(track):
            if track.kind != 'audio': return
            async def play():
                resampler = av.AudioResampler(format='s16', layout='mono', rate=24000)
                try:
                    while not self.closed.is_set():
                        frame = await track.recv()
                        for pcm in resampler.resample(frame):
                            block=bytes(pcm.planes[0])[:pcm.samples * 2]
                            self.output_meter.feed(block)
                            playback.stdin.write(block)
                            await asyncio.wait_for(playback.stdin.drain(), 2)
                            self.received_frames += 1
                except asyncio.CancelledError: raise
                except Exception: self._fail()
            self._task(play())
        await self.peer.setLocalDescription(await self.peer.createOffer())
        return self.peer.localDescription.sdp

    def open(self):
        try: return self._submit(self._open(), 15)
        except Exception:
            self.close()
            raise ValueError('Pi-Audio konnte nicht gestartet werden. Mikrofon und Lautsprecher prüfen.') from None

    async def _answer(self, sdp):
        from aiortc import RTCSessionDescription
        if not self.peer: raise ValueError('Audioverbindung fehlt.')
        await self.peer.setRemoteDescription(RTCSessionDescription(sdp=sdp, type='answer'))

    def answer(self, sdp):
        return self._submit(self._answer(sdp))

    def mute(self, value):
        self.gate.mute(value)
        self.input_meter.clear()

    def feedback(self):
        return {'input':self.input_meter.public(),'output':self.output_meter.public(),
                'search':self.searches.public(),'web_events':self.web_event_count}

    def set_search_sound(self, enabled):
        self.search_sound=enabled
        # Keep lifecycle state even when disabled; enabling during a search resumes it.
        self.request_search_tone()

    def update_search(self, kind, identifier, status):
        if self.searches.update(kind, identifier, status):
            self.cue_serial+=1
            self.cue_requested_at=time.monotonic()
        self.request_search_tone()

    def note_user_speech(self):
        # Provider-confirmed input distinguishes a real interruption from speaker echo.
        self.user_speech_at=time.monotonic()

    def _search_pending(self):
        search=self.searches.public()
        return bool(search['brain'] or search['web'])

    def request_search_tone(self):
        if self.closed.is_set() or self.loop.is_closed():return
        def schedule():
            if self.closed.is_set() or (not self._search_pending() and time.monotonic()-self.cue_requested_at>2):return
            if self.cue_task and not self.cue_task.done():return
            self.cue_task=self._task(self._search_tone())
        self.loop.call_soon_threadsafe(schedule)

    async def _search_tone(self):
        """Coalesce tool calls and finish one 1.6 s motif with a soft release.

        Answer onset ducks an already-started motif; it does not cut it off.
        Human speech, sound off and session close retain interruption priority.
        """
        process=None
        offset=total=handled=0
        deadline=0
        idle_since=None
        waiting_output=False
        gain=1.0
        fade=None
        fade_reason=None
        try:
            pcm=search_loop_pcm()
            while not self.closed.is_set():
                now=time.monotonic()
                pending=self._search_pending()
                output_speech=not self.output_meter.quiet(.25)
                # During answer playback the room mic also hears the speaker.
                human_speech=(now-self.user_speech_at<.35 or
                              (not output_speech and not self.input_meter.quiet(.3)))
                fresh=self.cue_serial>handled and now-self.cue_requested_at<2
                if pending:idle_since=None
                elif idle_since is None:idle_since=now
                if not output_speech:waiting_output=False
                if not self.search_sound:
                    if process:await self._terminate(process);process=None;self.search_loop_pauses+=1
                    handled=self.cue_serial
                    offset=total=0;deadline=0;fade=None
                    await asyncio.sleep(.02 if pending else .1)
                    continue
                if process is None:
                    if human_speech or waiting_output or not (pending or fresh):
                        await asyncio.sleep(.02 if pending or fresh else .1)
                        continue
                    process=await self._spawn(self.playback_command,stdin=asyncio.subprocess.PIPE)
                    process.stdin.transport.set_write_buffer_limits(high=1920,low=960)
                    self.search_tones+=1
                    offset=total=0;deadline=0;fade=None;gain=.2 if output_speech else 1.0
                handled=self.cue_serial
                if process.returncode is not None:break
                stop_reason=('human' if human_speech else
                             'answer' if output_speech and total>=80 else
                             'complete' if not pending and total>=80 and now-idle_since>=.45 else None)
                if stop_reason:
                    steps=2 if stop_reason=='human' else 9
                    if fade is None or (stop_reason=='human' and fade>2):
                        fade=steps;fade_reason=stop_reason
                elif fade_reason=='complete' and pending:
                    fade=None;fade_reason=None
                target=.2 if output_speech else 1.0
                next_gain=gain+(target-gain)*.35
                if fade is not None:next_gain=min(next_gain,gain*(fade-1)/fade)
                block=array('h');block.frombytes(pcm[offset:offset+960])
                if sys.byteorder!='little':block.byteswap()
                count=len(block)
                block=array('h',(round(v*(gain+(next_gain-gain)*(i+1)/count)) for i,v in enumerate(block)))
                if sys.byteorder!='little':block.byteswap()
                self.input_meter.cue_playing()
                process.stdin.write(block.tobytes())
                await asyncio.wait_for(process.stdin.drain(),.5)
                offset=(offset+960)%len(pcm);total+=1;self.search_loop_blocks+=1;gain=next_gain
                clock=asyncio.get_running_loop().time()
                deadline=max(deadline+.02,clock) if deadline else clock+.02
                await asyncio.sleep(max(0,deadline-clock))
                if fade is not None:
                    fade-=1
                    if fade<=0:
                        # Give the short fade time to reach the sink before releasing it.
                        process.stdin.close()
                        try:await asyncio.wait_for(process.wait(),.25)
                        except asyncio.TimeoutError:pass
                        await self._terminate(process);process=None;self.search_loop_pauses+=1
                        waiting_output=fade_reason=='answer'
                        offset=total=0;deadline=0;fade=None;fade_reason=None
        except (OSError,ValueError,EOFError,asyncio.TimeoutError,ConnectionError):
            pass  # An optional sound failure must not end the conversation.
        finally:
            if process:await self._terminate(process)

    async def _terminate(self, process):
        if process.returncode is None:
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: await asyncio.wait_for(process.wait(), .5)
            except asyncio.TimeoutError:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                await process.wait()
        for stream in (process.stdin,):
            if stream: stream.close()
        if process in self.processes:self.processes.remove(process)

    async def _shutdown(self):
        if self.opening_task and not self.opening_task.done():
            self.opening_task.cancel()
            await asyncio.gather(self.opening_task, return_exceptions=True)
        # Close input/output hardware before allowing the service to release ownership.
        await asyncio.gather(*(self._terminate(p) for p in list(self.processes)), return_exceptions=True)
        for task in list(self.tasks): task.cancel()
        if self.tasks: await asyncio.gather(*list(self.tasks), return_exceptions=True)
        if self.peer: await self.peer.close()

    def stats(self):
        return {'capture_backend': 'pipewire' if self.capture_command[0] == 'parec' else 'explicit-device',
                'captured_frames': self.captured_frames, 'sent_frames': self.sent_frames,
                'played_frames': self.received_frames, 'search_tones':self.search_tones, 'search_loop_blocks':self.search_loop_blocks, 'search_loop_pauses':self.search_loop_pauses, 'event_types':dict(self.event_types), 'processes_alive': sum(p.returncode is None for p in list(self.processes)),
                'closed': self.closed.is_set()}

    def close(self):
        with self.close_lock:
            if self.closed.is_set(): return
            self.closed.set(); self.gate.mute(True)
            try: asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop).result(5)
            finally:
                # Final protection if an audio process or coroutine ignored shutdown.
                for process in self.processes:
                    if process.returncode is None:
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                async def reap():
                    await asyncio.gather(*(p.wait() for p in list(self.processes)), return_exceptions=True)
                try: asyncio.run_coroutine_threadsafe(reap(), self.loop).result(2)
                finally:
                    self.loop.call_soon_threadsafe(self.loop.stop)
                    self.thread.join(timeout=2)
