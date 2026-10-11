"""Compatibility adapter for older Qt views. Local only; API keys are ignored.

Primary native product uses DesktopEngine's durable jobs instead of transient
workers. This adapter retains the historical result shape for external clients.
"""
from pathlib import Path
import subprocess
import tempfile
import threading
from meeting_recorder.core import Store
from meeting_recorder.processing import LocalModels, summarize
from settings import SettingsManager


class AudioSessionService:
    def __init__(self, api_key=None, cache_dir=None):
        self.store=Store(Path.home()/'.local/share/cdb-recorder-local')
        self.stopping=threading.Event()
        self.backend=LocalModels(self.stopping)

    def transcribe(self,audio_file_path,language='de',use_cache=True,progress_callback=None):
        try:
            with tempfile.TemporaryDirectory(dir=self.store.root) as folder:
                folder=Path(folder)
                subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(audio_file_path),
                   '-ar','16000','-ac','1','-c:a','pcm_s16le',str(folder/'audio.wav')],check=True,timeout=1800)
                if progress_callback:progress_callback(1,1)
                text=self.backend.transcribe(folder,self.store.config())
                return {'success':True,'text':text,'tokens_used':0,'language':'de'}
        except Exception as e:return {'success':False,'error':str(e)}

    def transform(self,text,prompt_id='zusammenfassen',reasoning_effort='medium',verbosity='low'):
        try:
            c=self.store.config()|{'context_size':4096}
            prompt=SettingsManager().get_prompt_by_id(prompt_id)
            if prompt:c['prompt']=prompt['prompt_text']
            result=summarize(text,c,self.backend,self.stopping,lambda _:None)
            return {'success':True,'result':result,'tokens_used':0}
        except Exception as e:return {'success':False,'error':str(e)}
