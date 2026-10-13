"""Bounded, content-free live feedback: PCM envelope and confirmed tool lifecycle."""
from array import array
from collections import deque
import math
import sys
import threading
import time

class AudioEnvelope:
    def __init__(self, clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.values=deque(maxlen=16);self.updated=0;self.voiced=0
    def feed(self, block):
        samples=array('h');samples.frombytes(block[:len(block)//2*2])
        if sys.byteorder!='little':samples.byteswap()
        rms=math.sqrt(sum(x*x for x in samples)/len(samples))/32768 if samples else 0
        with self.lock:
            self.updated=self.clock();self.values.append(round(min(1,rms*5),3))
            if rms>.008:self.voiced=self.updated
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

def search_chime():
    # 120 ms, gentle attack/release, no file or synthesizer dependency.
    samples=array('h',(int(900*math.sin(2*math.pi*660*i/24000)*math.sin(math.pi*i/2880)**2) for i in range(2880)))
    if sys.byteorder!='little':samples.byteswap()
    return samples.tobytes()
