"""Functional local Studio preview with an isolated, persistent synthetic library."""
import argparse, os, sys, signal, threading, time, wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from meeting_recorder.processing import Interrupted
from web_server import StudioApp, StudioServer


class PreviewBackend:
    def __init__(self, delay=12):self.delay=delay;self.stopping=threading.Event()
    def wait(self):
        if self.stopping.wait(self.delay):raise Interrupted()
    def transcribe(self,folder,config):
        self.wait();return 'Künstlicher Audiotest: Anna erstellt bis Donnerstag eine Aufgabenliste. Fortsetzung am Freitag um zehn Uhr. Die Kosten sind noch ungeklärt.'
    def generate(self,text,config,merge=False):
        self.wait();return 'Aufgabe: Anna erstellt bis Donnerstag die Aufgabenliste.\n\nFortsetzung: Freitag um 10 Uhr.\n\nOffen: Kosten klären.'


def create_preview(root, delay=12):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(root/'qt-settings'))
    source=root/'preview.wav'
    if not source.exists():
        import numpy as np
        times=np.arange(61*16000)/16000
        envelope=.1+.3*np.sin(times*2.3)**2
        data=(np.sin(times*2*np.pi*220)*envelope*32767).astype('<i2')
        with wave.open(str(source),'wb') as f:
            f.setparams((1,2,16000,0,'NONE','none'));f.writeframes(data.tobytes())
        (root/'capture.pcm').write_bytes(data[:32000].tobytes())
    script="import sys,time,signal;signal.signal(signal.SIGINT,lambda *_:sys.exit(0));data=open(sys.argv[1],'rb').read();\nwhile True:\n sys.stdout.buffer.write(data[:3200]);sys.stdout.buffer.flush();data=data[3200:]+data[:3200];time.sleep(.1)"
    backend=PreviewBackend(delay)
    app=StudioApp(root/'queue',root/'sessions.db',backend=backend,
        command_factory=lambda _:[sys.executable,'-u','-c',script,str(root/'capture.pcm')],preview=True)
    backend.stopping=app.engine.worker.stopping
    app.engine.configure({'setup_complete':True})
    if not app.repo.get_all():
        notes='Anna: Aufgabenliste bis Donnerstag.\nFortsetzung am Freitag um 10 Uhr.\nKosten im nächsten Gespräch klären.\nNächste Schritte und Verantwortlichkeiten festhalten.'
        for title,date in [('Teamrunde','2026-10-11T10:00:00'),('Produktplanung Q4','2026-10-08T14:30:00'),('Kundengespräch Müller','2026-10-06T11:00:00')]:
            sid=app.repo.create(title,date,str(source),duration_sec=61,samplerate=16000,notes=notes)
            app.repo.update(sid,transcript_text='Anna erstellt bis Donnerstag eine Liste. Fortsetzung am Freitag um zehn Uhr.',
                            summary_text='Anna: Aufgabenliste bis Donnerstag.\nFortsetzung am Freitag um 10 Uhr.',transcription_status='completed')
    return app


def main():
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('--port',type=int,default=8094);parser.add_argument('--delay',type=float,default=12)
    args=parser.parse_args();app=create_preview(args.root,args.delay);server=StudioServer(('127.0.0.1',args.port),app);server.timeout=.5
    stopping=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stopping.set());signal.signal(signal.SIGINT,lambda *_:stopping.set())
    print('STUDIO_PREVIEW http://127.0.0.1:'+str(args.port),flush=True)
    try:
        while not stopping.is_set():server.handle_request()
    finally:server.server_close();app.close()

if __name__=='__main__':main()
