"""Synthetic, microphone-free Pi acceptance; prints aggregate timing and cases.

Run with venv-local-ai/bin/python -m scripts.check_wake_phrase.
Requires espeak-ng and ffmpeg. This is a reproducible smoke corpus, not a
field false-accept-rate benchmark or a substitute for the owner's accent test.
"""
import json
import resource
import subprocess
import time
from services.wake_phrase import PhraseDetector


def main():
    cases = [('en-us', 'Hey Brain', True), ('en-gb', 'Hey Brain', True),
             ('en-us+f3', 'Hey Brain', True), ('en-us+m3', 'Hey Brain', True), ('en-gb+f2', 'Hey Brain', True),
             ('en-us+m2', 'Hey Brain', True)]
    cases += [('en-us', text, False) for text in ('Hey Brian', 'Hey rain', 'Hey train', 'Hey Jane',
             'The brain', 'Please bring me some tea', 'Good morning', 'Hey', 'Brain', 'Hey bring',
             'What is the weather today?', 'Open the library', 'Set a timer for five minutes')]
    cases += [('de', text, False) for text in ('Okay Nabu', 'Gespräch beenden', 'Guten Morgen',
             'Heute machen wir ein Meeting und schreiben Notizen.', 'Ich brauche einen neuen Termin.',
             'Bitte schalte das Mikrofon aus.', 'Was gibt es heute zu essen?')]
    result=[];cpu_total=0;seconds_total=0
    for voice,text,expected in cases:
        wav=subprocess.check_output(['espeak-ng','-v',voice,'-s','145','--stdout',text])
        pcm=subprocess.run(['ffmpeg','-v','error','-i','pipe:0','-ar','16000','-ac','1','-f','s16le','pipe:1'],input=wav,capture_output=True,check=True).stdout+bytes(48000)
        detector=PhraseDetector();found=0;start=time.process_time()
        for i in range(0,len(pcm),1600): found+=int(detector.feed(pcm[i:i+1600]))
        cpu=time.process_time()-start;seconds=len(pcm)/32000
        cpu_total+=cpu;seconds_total+=seconds
        result.append({'voice':voice,'text':text,'expected':expected,'detections':found,'passed':bool(found)==expected})
    detector=PhraseDetector();start=time.process_time();silence_hits=0
    for _ in range(1200):silence_hits+=int(detector.feed(bytes(1600)))
    silence_cpu=time.process_time()-start
    report={'cases':result,'passed':all(c['passed'] for c in result) and not silence_hits,
            'audio_seconds':round(seconds_total,2),'cpu_seconds':round(cpu_total,3),
            'one_core_percent':round(100*cpu_total/seconds_total,2),
            'silence_60_seconds':{'detections':silence_hits,'cpu_seconds':round(silence_cpu,3)},
            'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
