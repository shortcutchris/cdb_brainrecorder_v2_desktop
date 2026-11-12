"""Bounded, synthetic-only Pi profiling; no microphone or production settings.

Diagnostic eight-second ceiling measures whether the unchanged three-second
candidate-lab deadline would fail. No Whisper wake verifier runs in production.
No decoded text or raw stderr is persisted. OS caches are not flushed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time
import wave
import numpy as np
from meeting_recorder.child_process import owned_command
from wake_whisper_probe import matches_nabu_joined


def timings(stderr):
    return {m[0]: float(m[1]) for m in re.findall(
        r'whisper_print_timings:\s+(load|mel|sample|encode|decode|batchd|prompt|total) time =\s+([0-9.]+) ms', stderr)}


def run(pcm, binary, model):
    descriptor=os.memfd_create('cdb-wake-synthetic-profile',flags=os.MFD_CLOEXEC)
    process=None;before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
    try:
        with os.fdopen(os.dup(descriptor),'wb') as stream:
            with wave.open(stream,'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(pcm)
        os.lseek(descriptor,0,os.SEEK_SET)
        command=[str(binary),'-m',str(model),'-f',f'/proc/self/fd/{descriptor}',
                 '-l','de','-t','2','-bo','1','-bs','1','-nf','-nt','-ac','256','--prompt','Nabu.']
        process=subprocess.Popen(owned_command(command),stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(descriptor,))
        error=None
        try:stdout,stderr=process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            error='diagnostic_timeout';process.kill();stdout,stderr=process.communicate(timeout=1)
        elapsed=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
        return {'wall_seconds':elapsed,'would_exceed_candidate_deadline':elapsed>3,
                'diagnostic_error':error,'returncode':process.returncode,
                'timings_ms':timings(stderr.decode('utf-8',errors='replace')),
                'recognized':not error and process.returncode==0 and matches_nabu_joined(stdout.decode('utf-8',errors='replace')),
                'stdout_bytes':len(stdout),'child_cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                'major_faults':after.ru_majflt-before.ru_majflt}
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=1)
            process.stdout.close();process.stderr.close()
        os.close(descriptor)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    # Known generated Charlie recording only: never arbitrary room audio.
    assert hashlib.sha256(a.fixture.read_bytes()).hexdigest()=='69a4de7344f9b2a5c1e10aa35b0850c316e4323e6d86d9bab9205fb3e14a4ac9'
    with wave.open(str(a.fixture)) as w:
        assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(16000,1,2)
        raw=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)/32768
    source=np.zeros(44800);source[16000:16000+len(raw)]=raw
    rng=np.random.default_rng(20261016);noise=rng.normal(size=len(source));noise/=np.sqrt(np.mean(noise**2))
    rms=np.sqrt(np.mean(raw**2));echo=source.copy()
    for delay,gain in [(1120,.55),(2400,.3),(4800,.15)]:echo[delay:]+=source[:-delay]*gain
    cases={'clean':source,'echo':echo,'snr_10db':source+noise*rms/np.sqrt(10),
           'snr_0db':source+noise*rms,'noise_only':noise*rms,'digital_silence':np.zeros_like(source)}
    result={'started_epoch':time.time(),'synthetic_only':True,'production_integration':False,'cache_controlled':False,
            'prompt':'Nabu.','candidate_deadline_seconds':3,'diagnostic_ceiling_seconds':8,
            'model_sha256':hashlib.sha256(a.model.read_bytes()).hexdigest(),
            'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest(),'cases':[]}
    for name,audio in cases.items():
        pcm=(np.clip(audio,-1,32767/32768)*32768).astype('<i2').tobytes()
        for repeat in range(2):
            row={'case':name,'repeat':repeat,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),**run(pcm,a.binary,a.model)}
            result['cases'].append(row);print(json.dumps(row),flush=True)
    result['finished_epoch']=time.time();a.output.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
