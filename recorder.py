"""Qt signal facade for the shared disk-streaming recorder; no sample accumulation."""
from PySide6.QtCore import QObject,Signal
from meeting_recorder.audio import devices

class AudioRecorder(QObject):
    level_updated=Signal(float)
    duration_updated=Signal(float)
    waveform_updated=Signal(object)
    samplerate=16000
    channels=1
    is_paused=False
    def __init__(self,engine):super().__init__();self.engine=engine
    @property
    def is_recording(self):return bool(self.engine.recorder.active)
    def get_devices(self):return [{'index':d['id'],'name':d['label']} for d in devices()['devices']]
    def get_duration_seconds(self):return self.engine.recorder.status()['seconds']
