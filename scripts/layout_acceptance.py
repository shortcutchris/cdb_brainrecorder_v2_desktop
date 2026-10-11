"""Explicit isolated Pi UI acceptance; synthetic PCM and controlled inference only.

This checks UI/capture integration without loading hot models on a Pi with no fan.
Never point its output directory at the production database or queue.
"""
import os, sys, time, json, threading, wave
from pathlib import Path
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

root = Path(sys.argv[1]).resolve()
if root.exists(): raise SystemExit('Use a new empty acceptance directory.')
root.mkdir(parents=True)
os.environ['CDB_LOCAL_DATA'] = str(root/'queue')
os.environ['CDB_SESSION_DB'] = str(root/'sessions.db')
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(root/'qt-settings'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.main_window import MainWindow

class Backend:
    def __init__(self):
        self.asr = threading.Event(); self.summary = threading.Event(); self.calls = 0
        self.fail_once = True
    def transcribe(self, folder, config):
        if not self.asr.wait(45): raise RuntimeError('Test deadline')
        return 'Testdaten: Anna erstellt bis Donnerstag eine Aufgabenliste.'
    def generate(self, text, config, merge=False):
        if not self.summary.wait(45): raise RuntimeError('Test deadline')
        self.calls += 1
        if self.calls == 2 and self.fail_once:
            self.fail_once = False
            raise RuntimeError('Künstlicher Testfehler · Wiederholen prüfen')
        return 'Test-Zusammenfassung: Anna erstellt bis Donnerstag die Aufgabenliste.'

app = QApplication([])
w = MainWindow()
w.showFullScreen()
if w.splash_widget: w.splash_widget.hide()
backend = Backend()
w.engine.worker.backend = backend
w.engine.configure({'setup_complete': True})
capture = "import sys,time,signal;signal.signal(signal.SIGINT,lambda *_:sys.exit(0));\nwhile True:\n sys.stdout.buffer.write(b'\\x01\\x00'*1600);sys.stdout.buffer.flush();time.sleep(.1)"
w.engine.recorder.command_factory = lambda _: [sys.executable, '-u', '-c', capture]
audio = root/'synthetic.wav'
with wave.open(str(audio), 'wb') as f:
    f.setparams((1,2,16000,0,'NONE','none'));f.writeframes(b'\0\0'*16000)
sid = w.repo.create('Testmeeting · eigene Notizen', '2026-10-11T12:00:00', str(audio),
                    notes='Künstliche Testdaten\n\nAnna: Aufgabenliste bis Donnerstag.\n\nFortsetzung am Freitag um 10 Uhr.\n\nKosten im nächsten Gespräch klären.')
w.repo.update(sid, transcript_text='Test-Transkript: Anna erstellt bis Donnerstag eine Liste.',
              summary_text='Test-Zusammenfassung: Aufgabenliste bis Donnerstag.', transcription_status='completed')
for i in range(20): w.repo.create('Testmeeting '+str(i+1), '2026-10-11T10:00:00', str(audio))
w._load_sessions();w.session_table.select_session_by_id(sid)
w.error('ABNAHMETEST · künstliche Daten / künstliche Audioquelle · keine persönlichen Meetings')

def pump(seconds=.1):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        app.processEvents();time.sleep(.01)

def until(predicate):
    deadline=time.monotonic()+30
    while not predicate():
        if time.monotonic()>deadline: raise AssertionError('UI acceptance timeout')
        pump(.05)
    pump(.1)

def shot(name):
    pump(.2)
    w.grab().save(str(root/(name+'.png')))

evidence = {'synthetic_inference':True, 'synthetic_capture':True, 'sizes':[]}
try:
    pump(1)
    until(lambda: not w.polling)
    shot('01-notes-collapsed-1280x720')
    button=w.record_button
    evidence['record_hitbox']={'width':button.width(),'height':button.height(),
                               'text':button.text(),'alignment':'QPushButton default centered'}
    w.record_button.click();w.record_button.click();pump(.2);w.record_button.click()
    until(lambda: bool(w.state.get('recording',{}).get('id')) and not w.busy)
    first=w.engine.recorder.active
    assert len([j for j in w.engine.store.list() if j['state']=='recording']) == 1
    pump(2)
    shot('02-recording-large-touch')
    w.record_button.click()
    until(lambda: any(j['id']==first and j['state']=='transcribing' for j in w.state.get('jobs',[])) and not w.busy)
    w.record_button.click()
    until(lambda: bool(w.state.get('recording',{}).get('id')) and not w.busy)
    second=w.engine.recorder.active
    pump(1)
    w.record_button.click()
    until(lambda: not w.state.get('recording',{}).get('id') and not w.busy)
    w.queue_toggle.click()
    shot('03-queue-expanded-asr')
    before=w.activity_icon.text();w.animate_activity();assert before != w.activity_icon.text()
    backend.asr.set()
    until(lambda: any(j['id']==first and j['state']=='summarizing' for j in w.state.get('jobs',[])))
    w.record_button.click()
    until(lambda: bool(w.state.get('recording',{}).get('id')) and not w.busy)
    third=w.engine.recorder.active
    pump(1)
    assert w.engine.recorder.active == third and third
    assert 'stoppen' in w.record_button.text()
    shot('04-recording-during-summary-queue-expanded')
    w.record_button.click()
    until(lambda: not w.state.get('recording',{}).get('id') and not w.busy)
    assert w.session_form.get_current_session_id()==sid
    w.queue_toggle.click()
    for index,name in [(1,'05-transcript'),(2,'06-summary'),(0,'07-notes')]:
        w.session_form.tabs.setCurrentIndex(index);shot(name)
    w.session_form.details_button.click();shot('08-details');w.session_form.details_button.click()
    w.showNormal();pump(.5)
    for width,height in [(1024,600),(1280,800)]:
        w.resize(width,height);pump(.5)
        assert (w.width(),w.height()) == (width,height)
        for opened in (False,True):
            w.queue_toggle.setChecked(opened);pump(.2)
            assert w.record_button.height()>=72
            assert w.session_form.notes_edit.height()>=60
            evidence['sizes'].append({'window':[w.width(),w.height()], 'queue_open':opened,
                'record':[w.record_button.width(),w.record_button.height()],
                'editor_height':w.session_form.notes_edit.height()})
            shot(f'09-size-{width}x{height}-queue-{opened}')
    w.showFullScreen();w.queue_toggle.setChecked(False)
    backend.summary.set()
    until(lambda: all(w.engine.store.get(j)['state'] in ('completed','failed') for j in (first,second,third)))
    w.poll();pump(1.5)
    shot('10-error-closed-footer')
    w.queue_toggle.setChecked(True);shot('11-error-expanded-retry')
    failed=next(j for j in w.engine.store.list() if j['state']=='failed')
    failed_session=next(r for r in w.repo.get_all() if r.get('local_job_id')==failed['id'])
    w.retry_queue_session(failed_session['id'],failed['id'])
    until(lambda: w.engine.store.get(failed['id'])['state']=='completed')
    assert len(w.engine.store.list()) == 3
    evidence.update({'double_tap_created_one_recording':True,
        'capture_during_asr':True,'capture_during_summary':True,'retry_completed':True,
        'selected_session_independent':w.session_form.get_current_session_id()==sid,
        'result_states':[w.engine.store.get(j)['state'] for j in (first,second,third)]})
    (root/'evidence.json').write_text(json.dumps(evidence,indent=2))
    print('LAYOUT_ACCEPTANCE_OK',json.dumps(evidence),flush=True)
finally:
    backend.asr.set();backend.summary.set()
    w.timer.stop();w.activity_timer.stop()
    if w.engine.recorder.active:w.engine.stop()
    for task in list(w.tasks):task.wait(5000)
    app.processEvents();w.session_form.flush();w.player_widget.player.close();w.engine.close();w.hide()
