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
        self.model_peak = self.model_cutoff = None

    def feed(self, pcm, decision, onset_renewals=0, *, probability=None, cutoff=None):
        values = array('h', pcm)
        if sys.byteorder != 'little': values.byteswap()
        if probability is not None and cutoff is not None:
            if any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1
                   for v in (probability, cutoff)):
                raise ValueError('Invalid wake model diagnostic')
            self.model_peak = max(self.model_peak or 0., probability)
            self.model_cutoff = cutoff
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
        if self.model_peak is not None:
            result.update(model_peak=round(self.model_peak, 5), model_cutoff=self.model_cutoff)
        self.peak = self.squares = self.samples = 0
        self.model_peak = self.model_cutoff = None
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
    result = {k: value[k] for k in (*COUNTERS, 'decision', 'peak_dbfs', 'rms_dbfs')}
    if 'model_peak' in value or 'model_cutoff' in value:
        if any(type(value.get(k)) not in (int, float) or not math.isfinite(value[k]) or
               not 0 <= value[k] <= 1 for k in ('model_peak', 'model_cutoff')):
            return None
        result.update(model_peak=value['model_peak'], model_cutoff=value['model_cutoff'])
    return result
