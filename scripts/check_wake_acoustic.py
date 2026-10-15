"""Operator-only acoustic test under atomic maintenance; requires explicit audio-test consent.

Plays supplied synthetic WAVs over the selected Pi speaker. Never saves microphone
PCM or decoded room text; reports only fixed decisions and levels. This tests the
real acoustic path, not production Live handoff (own output deliberately inhibits
production wake). Does not change audio settings, firmware or installed code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import urllib.request
import uuid
import wave

from services.live_audio import native_capture_command
from services.wake_phrase import PhraseDetector
from services.wake_diagnostics import AudioDiagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clips', nargs='+', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--quiet-seconds', type=float, default=1,
                        help='Bounded real quiet time before each acoustic call (1–120 seconds).')
    args = parser.parse_args()
    if not 1 <= len(args.clips) <= 4: parser.error('Use 1–4 synthetic test files.')
    if not 1 <= args.quiet_seconds <= 120: parser.error('Use 1–120 quiet seconds.')
    clips = []
    for path in args.clips:
        with wave.open(str(path)) as source:
            duration = source.getnframes() / source.getframerate()
            if not 0 < duration <= 8: parser.error('Test files must be at most eight seconds.')
        clips.append((path, duration))
    os.umask(0o077)
    root = Path.home()/'.local/share/cdb-recorder-local'
    token = json.loads((root/'management/local-auth.json').read_text())['token']
    def request(path, body=None):
        req=urllib.request.Request('http://127.0.0.1:8088'+path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=5) as response: return json.load(response)
    health=request('/api/management/health')
    assert health['activity']=='idle', 'Device is occupied; no test started'
    speaker=request('/api/speakers')
    assert speaker['available'] and not speaker['muted'] and speaker['volume']>0, 'Speaker unavailable'
    capture=playback=None
    reserved=False
    ident=str(uuid.uuid4())
    report={'synthetic_acoustic':True,'production_live_handoff':False,
            'version':health['version'],'quiet_seconds':args.quiet_seconds,'started_epoch':time.time(),'cases':[]}
    def stop(*_): raise SystemExit('Acoustic test interrupted')
    signal.signal(signal.SIGTERM,stop)
    try:
        request('/api/management/prepare',{'command':ident});reserved=True
        config={'device':request('/api/state')['config']['device']}
        command=native_capture_command(config)
        capture=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True,bufsize=0)
        detector=PhraseDetector();measure=AudioDiagnostics();buffer=b''
        for path,duration in clips:
            row={'clip':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'detections':0,'decisions':[]}
            start=time.monotonic();last_data=start;played=False
            while time.monotonic()-start < args.quiet_seconds+duration+3:
                if not played and time.monotonic()-start >= args.quiet_seconds:
                    playback=subprocess.Popen(['paplay','--device='+speaker['selected'],str(path)],
                                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                    played=True;row['play_at_seconds']=round(time.monotonic()-start,2)
                if not select.select([capture.stdout],[],[],.2)[0]:
                    if time.monotonic()-last_data > 3: raise RuntimeError('No microphone frames')
                    continue
                block=capture.stdout.read(1600)
                if not block: raise RuntimeError('Microphone capture ended')
                buffer+=block;last_data=time.monotonic()
                while len(buffer)>=1600:
                    pcm,buffer=buffer[:1600],buffer[1600:]
                    detected=detector.feed(pcm);measure.feed(pcm,detector.last_decision,detector.onset.renewals)
                    if detector.last_decision:
                        row['decisions'].append({'at_seconds':round(time.monotonic()-start,2),'category':detector.last_decision})
                        row['decisions']=row['decisions'][-16:]
                    row['detections']+=int(detected)
            playback.wait(timeout=2);row['playback_exit']=playback.returncode;playback=None
            row['audio']=measure.snapshot();report['cases'].append(row)
    finally:
        for proc in (playback,capture):
            if proc is not None:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=2)
                if proc.stdout:proc.stdout.close()
        if reserved:
            request('/api/management/release',{'command':ident})
            report['maintenance_released']=True
        report['finished_epoch']=time.time()
        args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':main()
