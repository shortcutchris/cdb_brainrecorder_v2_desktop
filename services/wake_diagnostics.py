"""Bounded, text-free wake measurements. PCM stays in memory for one block."""
from array import array
import math
import sys

DECISIONS = ('none', 'accepted', 'candidate_rejected', 'partial_wake_word', 'other_speech')
COUNTERS = ('blocks', 'speech_segments', 'accepted', 'candidate_rejected', 'partial_wake_word', 'other_speech', 'onset_renewals')


class AudioDiagnostics:
    def __init__(self):
        self.counts = dict.fromkeys(COUNTERS, 0)
        self.last_decision = 'none'
        self.peak = self.squares = self.samples = 0

    def feed(self, pcm, decision, onset_renewals=0):
        values = array('h', pcm)
        if sys.byteorder != 'little': values.byteswap()
        self.counts['blocks'] += 1
        self.counts['onset_renewals'] = onset_renewals
        self.samples += len(values)
        self.peak = max(self.peak, max((abs(v) for v in values), default=0))
        self.squares += sum(v * v for v in values)
        if decision in DECISIONS[1:]:
            self.counts['speech_segments'] += 1
            self.counts[decision] += 1
            self.last_decision = decision

    def snapshot(self):
        def db(value): return round(max(-96, 20 * math.log10(max(value, 1e-9) / 32768)), 1)
        result = {**self.counts, 'decision': self.last_decision, 'peak_dbfs': db(self.peak),
                  'rms_dbfs': db(math.sqrt(self.squares / max(self.samples, 1)))}
        self.peak = self.squares = self.samples = 0
        return result


def validate(value):
    """Whitelist child diagnostics; never pass through arbitrary keys or strings."""
    if not isinstance(value, dict) or value.get('decision') not in DECISIONS:
        return None
    if any(type(value.get(k)) is not int or not 0 <= value[k] <= 10**10 for k in COUNTERS):
        return None
    if any(type(value.get(k)) not in (int, float) or not math.isfinite(value[k]) or
           not -96 <= value[k] <= 1 for k in ('peak_dbfs', 'rms_dbfs')):
        return None
    return {k: value[k] for k in (*COUNTERS, 'decision', 'peak_dbfs', 'rms_dbfs')}
