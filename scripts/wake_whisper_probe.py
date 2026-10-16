"""Linux-only lab verifier. Audio stays in an anonymous RAM descriptor, never a file.

This does not own a microphone, install models or start Live. The caller must
already hold maintenance when supplying transient room PCM.
"""
import os
import re
import subprocess
import time
import wave


def matches_nabu(text):
    words = re.findall(r'[^\W\d_]+', text.lower())
    return len(words) >= 2 and words[0] in ('ok', 'okay') and words[1] == 'nabu'


def probe_whisper_pcm(pcm, binary, model):
    if not hasattr(os, 'memfd_create'):
        raise RuntimeError('This lab probe requires Linux anonymous RAM descriptors')
    if not pcm or len(pcm) % 2:
        raise ValueError('Expected nonempty mono S16LE PCM at 16 kHz')
    # 256 audio-context positions: use only bounded short candidate windows.
    bounded = bytes(pcm[:153600])  # At most 4.8 seconds; deliberately explicit.
    descriptor = os.memfd_create('cdb-wake-lab', flags=os.MFD_CLOEXEC)
    try:
        with os.fdopen(os.dup(descriptor), 'wb') as stream:
            with wave.open(stream, 'wb') as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                audio.writeframes(bounded)
        os.lseek(descriptor, 0, os.SEEK_SET)
        command = [str(binary), '-m', str(model), '-f', f'/proc/self/fd/{descriptor}',
                   '-l', 'de', '-t', '2', '-bo', '1', '-bs', '1', '-nf', '-nt', '-np',
                   '-ac', '256', '--prompt', 'Nabu.']
        started = time.monotonic()
        report = {'mode': 'post_capture_anonymous_ram', 'audio_seconds': len(bounded)/32000,
                  'truncated': len(pcm) > len(bounded), 'transcript_saved': False,
                  'detected': False}
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    pass_fds=(descriptor,), timeout=10)
            report['returncode'] = result.returncode
            report['detected'] = result.returncode == 0 and matches_nabu(result.stdout)
            report['nonempty_result'] = bool(result.stdout.strip())
        except subprocess.TimeoutExpired:
            report['error'] = 'timeout'
        report['wall_seconds'] = round(time.monotonic()-started, 4)
        return report
    finally:
        os.close(descriptor)
