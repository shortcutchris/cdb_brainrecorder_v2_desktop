"""Bounded, content-free live feedback: PCM envelope and confirmed tool lifecycle."""
from array import array
from collections import deque
import math
from functools import lru_cache
from pathlib import Path
import wave
import sys
import threading
import time

class AudioEnvelope:
    def __init__(self, clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.values=deque(maxlen=16);self.updated=0;self.voiced=0
    def feed(self, block, *, voice=None):
        samples=array('h');samples.frombytes(block[:len(block)//2*2])
        if sys.byteorder!='little':samples.byteswap()
        rms=math.sqrt(sum(x*x for x in samples)/len(samples))/32768 if samples else 0
        with self.lock:
            self.updated=self.clock();self.values.append(round(min(1,rms*5),3))
            if (rms>.008 if voice is None else voice):self.voiced=self.updated
        return rms
    def clear(self):
        with self.lock:self.values.clear();self.updated=0;self.voiced=0
    def public(self):
        with self.lock:
            fresh=self.clock()-self.updated<.3
            return {'bars':([0]*(16-len(self.values))+list(self.values)) if fresh else [0]*16,
                    'active':fresh and self.clock()-self.voiced<.25}
    def quiet(self, seconds=.4):
        with self.lock:return self.clock()-self.voiced>seconds


class SearchInputEnvelope(AudioEnvelope):
    """Ignore the known six bell partials in the *pause detector*, never in audio.

    A small 80 ms FFT window separates the known cue from energy elsewhere.
    This is cue-specific discrimination, not general acoustic echo cancellation.
    Original microphone PCM and the visual waveform remain unchanged.
    """
    def __init__(self, clock=time.monotonic):
        super().__init__(clock)
        import numpy as np
        self.np=np
        self.analysis_lock=threading.RLock()
        self.buffer=bytearray()
        self.cue_until=0
        self.window=np.hanning(1280)
        frequencies=np.fft.rfftfreq(1280,1/16000)
        self.outside=np.ones(len(frequencies),dtype=bool)
        for base in (523.251,659.255,783.991):
            for frequency in (base,base*2.76):
                self.outside &= abs(frequencies-frequency)>65
        self.speech_frames=0

    def cue_playing(self):
        # Account for Bluetooth latency and the acoustic tail after stopping.
        self.cue_until=self.clock()+.8

    def feed(self, block):
        with self.analysis_lock:
            return self._feed(block)

    def _feed(self, block):
        self.buffer.extend(block)
        del self.buffer[:-2560]
        if self.clock()>self.cue_until:
            self.speech_frames=0
            return super().feed(block)
        np=self.np
        samples=np.frombuffer(self.buffer,dtype='<i2').astype(float)/32768
        if len(samples)<1280:
            samples=np.pad(samples,(1280-len(samples),0))
        power=abs(np.fft.rfft(samples*self.window))**2
        # Parseval with a Hann window; suppress only the exact cue frequency bands.
        residual=float(np.sqrt(2*power[self.outside].sum()/(1280*(self.window**2).sum())))
        self.speech_frames=self.speech_frames+1 if residual>.012 else 0
        return super().feed(block,voice=self.speech_frames>=2)

    def clear(self):
        with self.analysis_lock:
            super().clear()
            self.buffer.clear()
            self.speech_frames=0

class SearchActivity:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.calls={}
    def update(self,kind,identifier,status):
        if kind not in ('brain','web') or status not in ('started','done','failed'):return False
        if not isinstance(identifier,str) or not 1<=len(identifier)<=200:return False
        key=(kind,identifier)
        with self.lock:
            old=self.calls.get(key)
            if old and (old[0] in ('done','failed') or old[0]==status):return False
            self.calls[key]=(status,self.clock())
            while len(self.calls)>128:self.calls.pop(next(iter(self.calls)))
            return status=='started' and old is None
    def public(self):
        with self.lock:
            now=self.clock();active=[k[0] for k,(s,t) in self.calls.items() if s=='started' and now-t<65]
            failed=any(s=='failed' and now-t<5 for s,t in self.calls.values())
            return {'brain':active.count('brain'),'web':active.count('web'),'failed':failed}

def web_search_event(envelope):
    """Only provider-confirmed web calls; delegation/thinking alone are insufficient."""
    if not isinstance(envelope,dict) or envelope.get('type')!='response.event':return None
    event=envelope.get('event')
    if not isinstance(event,dict):return None
    kind=event.get('type','');item=event.get('item');item=item if isinstance(item,dict) else {}
    if not isinstance(kind,str):return None
    if not (kind.startswith('response.web_search_call.') or item.get('type')=='web_search_call'):return None
    identifier=event.get('item_id') or item.get('id')
    status=event.get('status') or item.get('status') or kind.rsplit('.',1)[-1]
    status='done' if status=='completed' else 'failed' if status in ('failed','incomplete','cancelled') else 'started' if status in ('in_progress','searching','added') else None
    return (identifier,status) if status else None

@lru_cache(maxsize=1)
def search_loop_pcm():
    """Load the selected original loop once. Raw little-endian 24 kHz mono PCM."""
    path = Path(__file__).resolve().parents[1] / 'studio/sounds/search-loop.wav'
    with wave.open(str(path), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24000):
            raise ValueError('Invalid search loop audio format')
        pcm = audio.readframes(audio.getnframes())
    if len(pcm) != 144000:
        raise ValueError('Invalid search loop duration')
    # Listening proposals are intentionally louder; room playback stays in the background.
    samples=array('h');samples.frombytes(pcm)
    if sys.byteorder!='little':samples.byteswap()
    samples=array('h',(round(sample*.25) for sample in samples))
    if sys.byteorder!='little':samples.byteswap()
    return samples.tobytes()
