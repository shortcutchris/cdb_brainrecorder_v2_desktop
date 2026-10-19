"""Paired lab comparisons on identical transient PCM; never returns room text."""
import time

try:
    from .wake_streaming_probe import AsyncVerifier
except ImportError:
    from wake_streaming_probe import AsyncVerifier


def verify(pcm, binary, model):
    verifier = AsyncVerifier(binary, model)
    try:
        verifier.submit(pcm)
        while True:
            result = verifier.poll()
            if result is not None:
                return result
            time.sleep(.01)
    finally:
        verifier.close()


def compare_windows(pcm, candidate_frame, binary, models, probe=verify):
    """One-based 50-ms candidate end; 2s lookback and fixed .8/1.6s tails.

    Capture must contain real pre-roll. Never pad missing context, silently
    truncate a window, infer a candidate from clip labels or aggregate decisions
    into a production trigger. Models receive the same immutable window bytes.
    """
    if not pcm or len(pcm) % 1600 or len(pcm) > 640000:
        raise ValueError('Use at most 20 seconds of complete 50-ms S16LE blocks')
    if len(models) != 2 or len(set(models)) != 2:
        raise ValueError('Provide exactly two distinct model labels')
    frames = len(pcm)//1600
    if candidate_frame is not None and (type(candidate_frame) is not int or not 1 <= candidate_frame <= frames):
        raise ValueError('Candidate must reference a captured block')
    report = {'mode': 'paired_post_capture', 'candidate_frame': candidate_frame,
              'lookback_seconds': 2, 'candidate_threshold': .15,
              'transcript_saved': False, 'production_trigger': False, 'windows': []}
    if candidate_frame is None:
        report['unavailable'] = 'no_candidate'
        return report
    for tail in (16, 32):
        start, end = candidate_frame-40, candidate_frame+tail
        row = {'tail_seconds': tail*.05, 'start_frame': start, 'end_frame': end}
        report['windows'].append(row)
        if start < 0 or end > frames:
            row['unavailable'] = 'incomplete_context'
            continue
        window = bytes(pcm[start*1600:end*1600])
        row['audio_seconds'] = len(window)/32000
        row['models'] = {label: probe(window, binary, path) for label, path in models.items()}
    return report
