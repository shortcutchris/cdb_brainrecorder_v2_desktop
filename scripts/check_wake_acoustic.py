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
from services.wake_detectors import create_detector, PHRASES, DEFAULT_PHRASE
from services.wake_diagnostics import AudioDiagnostics


def probe_vosk_pcm(model, grammar, accepted, pcm, recognizer_factory=None):
    """File-equivalent second opinion on transient PCM; never returns decoded text.

    Timing here is decoder CPU cost after capture, not measured Live wake latency.
    The same captured mono samples are used as for the primary detector.
    """
    if recognizer_factory is None:
        from vosk import KaldiRecognizer
        recognizer_factory = KaldiRecognizer
    started = time.process_time()
    recognizer = recognizer_factory(model, 16000, json.dumps(grammar))
    hits = 0
    segments = 0
    def consume(payload):
        nonlocal hits, segments
        result = json.loads(payload)
        text = result.get('text', '')
        if text:
            segments += 1
            hits += int(text in accepted)
    # No stored transcript, timestamps or word hypotheses leave this function.
    for index in range(0, len(pcm), 1600):
        if recognizer.AcceptWaveform(bytes(pcm[index:index+1600])):
            consume(recognizer.Result())
    consume(recognizer.FinalResult())
    return {'detected': hits > 0, 'accepted_segments': hits,
            'nonempty_segments': segments, 'cpu_seconds': round(time.process_time()-started, 4),
            'mode': 'post_capture_same_pcm', 'transcript_saved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clips', nargs='+', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--phrase', choices=PHRASES, default=DEFAULT_PHRASE)
    parser.add_argument('--external-playback', action='store_true',
                        help='Emit playback cues for an external room speaker; no Pi playback.')
    parser.add_argument('--signal-diagnostics', action='store_true',
                        help='Compare known WAV to transient microphone PCM; save only scores.')
    parser.add_argument('--compare-stereo', action='store_true',
                        help='ReSpeaker/Nabu only: compare both processed channels to their mean.')
    parser.add_argument('--quiet-seconds', type=float, default=1,
                        help='Bounded real quiet time before each acoustic call (1–120 seconds).')
    parser.add_argument('--vosk-model', type=Path,
                        help='Existing lab-only Vosk model for a second opinion on the same PCM.')
    parser.add_argument('--vosk-grammar', type=Path,
                        help='Explicit grammar/accepted JSON; requires --vosk-model. No room text saved.')
    parser.add_argument('--whisper-binary', type=Path,
                        help='Existing Linux whisper-cli for a bounded anonymous-RAM lab probe.')
    parser.add_argument('--whisper-model', type=Path,
                        help='Existing lab-only Tiny model; requires --whisper-binary. No room text saved.')
    args = parser.parse_args()
    if not 1 <= len(args.clips) <= 4: parser.error('Use 1–4 synthetic test files.')
    if not 1 <= args.quiet_seconds <= 120: parser.error('Use 1–120 quiet seconds.')
    if args.compare_stereo and args.phrase!='okay-nabu': parser.error('Stereo comparison requires Nabu.')
    if bool(args.vosk_model) != bool(args.vosk_grammar): parser.error('Specify both Vosk lab arguments.')
    if bool(args.whisper_binary) != bool(args.whisper_model): parser.error('Specify both Whisper lab arguments.')
    if args.whisper_binary and (not args.whisper_binary.is_file() or not args.whisper_model.is_file()):
        parser.error('Whisper binary and model must already exist.')
    clips = []
    for path in args.clips:
        with wave.open(str(path)) as source:
            duration = source.getnframes() / source.getframerate()
            if not 0 < duration <= 8: parser.error('Test files must be at most eight seconds.')
        clips.append((path, duration))
    verifier = None
    verifier_spec = None
    if args.vosk_model:
        from vosk import Model, SetLogLevel
        from benchmark_vosk_wake import validate_grammar
        SetLogLevel(-1)
        verifier_spec = json.loads(args.vosk_grammar.read_text())
        verifier = Model(str(args.vosk_model))
        validate_grammar(verifier, verifier_spec['grammar'], verifier_spec['accepted'])
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
    speaker=None
    if not args.external_playback:
        speaker=request('/api/speakers')
        assert speaker['available'] and not speaker['muted'] and speaker['volume']>0, 'Speaker unavailable'
    capture=playback=None
    reserved=False
    ident=str(uuid.uuid4())
    report={'synthetic_acoustic':True,'production_live_handoff':False,
            'phrase':args.phrase, 'external_playback':args.external_playback,
            'compare_stereo':args.compare_stereo,'signal_diagnostics':args.signal_diagnostics,
            'version':health['version'],'quiet_seconds':args.quiet_seconds,'started_epoch':time.time(),'cases':[]}
    if verifier is not None:
        report['vosk_lab'] = {'model': args.vosk_model.name,
                             'grammar_sha256': hashlib.sha256(args.vosk_grammar.read_bytes()).hexdigest(),
                             'production_integration': False, 'room_text_saved': False}
    if args.whisper_binary:
        report['whisper_lab'] = {'model_sha256': hashlib.sha256(args.whisper_model.read_bytes()).hexdigest(),
                                'binary_sha256': hashlib.sha256(args.whisper_binary.read_bytes()).hexdigest(),
                                'audio_context': 256, 'initial_prompt': 'Nabu.',
                                'production_integration': False, 'room_text_saved': False}
    def stop(*_): raise SystemExit('Acoustic test interrupted')
    signal.signal(signal.SIGTERM,stop)
    try:
        request('/api/management/prepare',{'command':ident});reserved=True
        config={'device':request('/api/state')['config']['device']}
        command=native_capture_command(config)
        if args.compare_stereo:
            assert command[0]=='parec' and any('respeaker_xvf3800' in x.lower() for x in command), 'Expected explicit ReSpeaker source'
            command=[x.replace('--channels=1','--channels=2') for x in command]
        capture=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True,bufsize=0)
        detector=create_detector(args.phrase);measure=AudioDiagnostics();buffer=b''
        channels=[create_detector(args.phrase) for _ in range(2)] if args.compare_stereo else []
        probabilities=[]
        if args.signal_diagnostics and args.phrase=='okay-nabu':
            original=detector.model.process_streaming_prob
            def measured(features):
                result=original(features)
                if result is not None: probabilities.append(float(result))
                return result
            detector.model.process_streaming_prob=measured
        for path,duration in clips:
            row={'clip':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'detections':0,'decisions':[]}
            captured=bytearray();probabilities.clear();measure=AudioDiagnostics()
            channel_rows=[{'channel':i,'detections':0,'max_model_probability':0.} for i in range(len(channels))]
            for extra,summary in zip(channels,channel_rows):
                if hasattr(extra.model,'_diagnostic_original'): original_extra=extra.model._diagnostic_original
                else:
                    original_extra=extra.model.process_streaming_prob
                    extra.model._diagnostic_original=original_extra
                def measure_extra(features,original=original_extra,summary=summary):
                    value=original(features)
                    if value is not None: summary['max_model_probability']=max(summary['max_model_probability'],float(value))
                    return value
                extra.model.process_streaming_prob=measure_extra
            start=time.monotonic();last_data=start;played=False
            while time.monotonic()-start < args.quiet_seconds+duration+3:
                if not played and time.monotonic()-start >= args.quiet_seconds:
                    if args.external_playback:
                        print(json.dumps({'event':'play_clip','clip':path.name}),flush=True)
                    else:
                        playback=subprocess.Popen(['paplay','--device='+speaker['selected'],str(path)],
                                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                    played=True;row['play_at_seconds']=round(time.monotonic()-start,2)
                if not select.select([capture.stdout],[],[],.2)[0]:
                    if time.monotonic()-last_data > 3: raise RuntimeError('No microphone frames')
                    continue
                frame_bytes=3200 if args.compare_stereo else 1600
                block=capture.stdout.read(frame_bytes)
                if not block: raise RuntimeError('Microphone capture ended')
                buffer+=block;last_data=time.monotonic()
                while len(buffer)>=frame_bytes:
                    pcm,buffer=buffer[:frame_bytes],buffer[frame_bytes:]
                    if args.compare_stereo:
                        from wake_acoustic_metrics import split_stereo
                        pcm,left,right=split_stereo(pcm)
                        for extra,summary,audio in zip(channels,channel_rows,(left,right)):
                            summary['detections']+=int(extra.feed(audio))
                    if (args.signal_diagnostics or verifier is not None or args.whisper_binary) and played:
                        captured.extend(pcm)
                    detected=detector.feed(pcm);measure.feed(pcm,detector.last_decision,detector.onset.renewals)
                    if detector.last_decision:
                        row['decisions'].append({'at_seconds':round(time.monotonic()-start,2),'category':detector.last_decision})
                        row['decisions']=row['decisions'][-16:]
                    row['detections']+=int(detected)
            if playback is not None:
                playback.wait(timeout=2);row['playback_exit']=playback.returncode;playback=None
            else:
                row['playback_exit']=None  # External controller must supply playback evidence.
            row['audio']=measure.snapshot();report['cases'].append(row)
            if args.compare_stereo: row['channel_comparison']=channel_rows
            if verifier is not None:
                row['vosk_lab'] = probe_vosk_pcm(verifier, verifier_spec['grammar'],
                                                 verifier_spec['accepted'], captured)
            if args.whisper_binary:
                from wake_whisper_probe import probe_whisper_pcm
                row['whisper_lab'] = probe_whisper_pcm(captured, args.whisper_binary, args.whisper_model)
            if args.signal_diagnostics:
                from wake_acoustic_metrics import alignment
                with wave.open(str(path)) as source:
                    if (source.getframerate(),source.getsampwidth(),source.getnchannels())==(16000,2,1):
                        row['signal_alignment']=alignment(source.readframes(source.getnframes()),captured)
                if probabilities:
                    row['max_model_probability']=round(max(probabilities),5)
                    row['unchanged_probability_cutoff']=detector.model.probability_cutoff
            captured.clear()
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
