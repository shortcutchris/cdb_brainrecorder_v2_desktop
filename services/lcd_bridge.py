"""Opt-in USB companion. Separate process; never starts or controls the recorder."""
import argparse
import json
import re
import time
import uuid
import urllib.request
from pathlib import Path
from .lcd_display import PROTOCOL, MAX_FRAME, label

NONCE = re.compile(r'^[0-9a-f]{32}$')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Unexpected redirect')


def fetch(port=8088, token=''):
    request = urllib.request.Request(f'http://127.0.0.1:{port}/api/lcd/timers',
        headers={'Authorization': 'Bearer '+token} if token else {})
    with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=.7) as response:
        raw = response.read(MAX_FRAME+1)
    if len(raw) > MAX_FRAME: raise ValueError('Oversize source response')
    result = json.loads(raw)
    if result.get('protocol') != PROTOCOL or result.get('type') != 'timers': raise ValueError('Wrong source')
    # Rebuild from an allowlist even if a future source accidentally adds private data.
    timers = result['timers']
    if not isinstance(timers,list) or len(timers)>16: raise ValueError('Invalid timers')
    clean=[]
    for item in timers:
        if (not isinstance(item.get('id'),str) or not 1<=len(item['id'])<=64 or
            type(item.get('revision')) is not int or not 1<=item['revision']<=2147483647 or
            item.get('state') not in ('scheduled','due','missed') or
            type(item.get('remaining_ms')) is not int or not 0<=item['remaining_ms']<=31622400000 or
            type(item.get('time_valid')) is not bool): raise ValueError('Invalid timer')
        clean.append({k:item[k] for k in ('id','revision','state','remaining_ms','time_valid')} | {'label':label(item.get('label',''))})
    if type(result.get('total')) is not int or not len(clean)<=result['total']<=100: raise ValueError('Invalid total')
    return {'timers':clean,'total':result['total'],'clock_ready':result.get('clock_ready') is True}


def encode(message):
    data = json.dumps(message,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n'
    if len(data)>MAX_FRAME: raise ValueError('Frame too large')
    return data


class Bridge:
    def __init__(self, source):
        self.source=label(source,40);self.session=uuid.uuid4().hex
        self.nonce=None;self.bound=False;self.seq=0;self.last_ack=0.

    def receive(self, message, now):
        if message.get('protocol')!=PROTOCOL:return None
        nonce=message.get('nonce','')
        if not isinstance(nonce,str) or not NONCE.fullmatch(nonce):return None
        if message.get('type')=='hello':
            if nonce!=self.nonce:self.nonce=nonce;self.bound=False;self.seq=0
            return {'protocol':PROTOCOL,'type':'bind','nonce':nonce,'session':self.session,'source':self.source}
        if nonce==self.nonce and message.get('session')==self.session and message.get('type') in ('bound','ack'):
            if message.get('type')=='bound' or message.get('seq')==self.seq:
                self.bound=True;self.last_ack=now
        return None

    def frame(self, timers, now):
        if not self.bound or now-self.last_ack>3:return None
        self.seq+=1
        return {'protocol':PROTOCOL,'type':'snapshot','nonce':self.nonce,'session':self.session,'seq':self.seq,**timers}


def run(port, source, api_port, token):
    import serial  # Optional companion dependency; not part of the recorder runtime.
    while True:
        try:
            device=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=.3)
            device.dtr=False;device.rts=False;device.port=port
            with device:
                device.reset_input_buffer();bridge=Bridge(source);buffer=bytearray();dropping=False;next_send=0.
                while True:
                    chunk=device.read(256)
                    for byte in chunk:
                        if byte==10:
                            if not dropping:
                                try:
                                    incoming=json.loads(buffer)
                                    reply=bridge.receive(incoming,time.monotonic()) if isinstance(incoming,dict) else None
                                    if reply:device.write(encode(reply))
                                except (ValueError,UnicodeError,TypeError):pass
                            buffer.clear();dropping=False
                        elif not dropping:
                            buffer.append(byte)
                            if len(buffer)>1024:buffer.clear();dropping=True
                    now=time.monotonic()
                    if bridge.bound and now>=next_send:
                        next_send=now+1
                        try:
                            data=fetch(api_port,token)
                            frame=bridge.frame(data,time.monotonic())
                            if frame:device.write(encode(frame))
                        except (OSError,ValueError,KeyError,TypeError):
                            # No cached snapshots: display timeout truthfully signals source loss.
                            pass
        except (OSError,serial.SerialException):time.sleep(2)


def main():
    parser=argparse.ArgumentParser(description='LCD USB display companion (read-only)')
    parser.add_argument('--port',required=True,help='Explicit /dev/serial/by-id/... or COM port; no scanning')
    parser.add_argument('--source',default='Pi Recorder')
    parser.add_argument('--api-port',type=int,default=8088)
    parser.add_argument('--token-file',type=Path)
    args=parser.parse_args()
    if not 1<=args.api_port<=65535:parser.error('Invalid API port')
    token=args.token_file.read_text().strip() if args.token_file else ''
    try:run(args.port,args.source,args.api_port,token)
    except KeyboardInterrupt:pass

if __name__=='__main__':main()
