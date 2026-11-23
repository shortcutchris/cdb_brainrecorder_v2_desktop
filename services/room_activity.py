"""Local level changes only. No speech recognition, recording or network I/O.

Shares the wake worker's 16 kHz mono stream. Retains only 100 scalar RMS values
(five seconds), never PCM between calls. Steady noise establishes a floor;
three elevated blocks are needed, so a single elevated 50 ms block does not extend a session.
This is a convenience signal, not a reliable human-presence detector.
"""
from array import array
from collections import deque
import math
import sys


class RoomActivity:
    def __init__(self):
        self.levels = deque(maxlen=100)
        self.blocks = self.elevated = 0
        self.last_event = -100

    def feed(self, pcm):
        values = array('h', pcm)
        if sys.byteorder != 'little': values.byteswap()
        if not values: return False
        mean = sum(values) / len(values)
        level = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)) / 32768
        self.blocks += 1
        floor = sorted(self.levels)[len(self.levels) // 5] if self.levels else level
        self.levels.append(level)
        high = len(self.levels) >= 20 and level > max(.008, floor * 2.5)
        self.elevated = self.elevated + 1 if high else 0
        if self.elevated >= 3 and self.blocks - self.last_event >= 100:
            self.last_event = self.blocks
            return True
        return False
