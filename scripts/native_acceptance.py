"""Opt-in real Qt/Pi model acceptance; synthetic audio and isolated DB/config only."""
import os
from pathlib import Path
import json,subprocess,sys,time
root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True)
os.environ['CDB_LOCAL_DATA']=str(root/'queue');os.environ['CDB_SESSION_DB']=str(root/'sessions.db')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,Qt,QPoint,QPointF,QSettings
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(root/'qt-settings'))
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
text='Dies ist ein technischer Modelltest. Das Team entscheidet, die Besprechung am Freitag um zehn Uhr fortzusetzen. Anna erstellt bis Donnerstag eine Liste der offenen Aufgaben. Die Kosten sind noch ungeklärt.'
subprocess.run(['espeak-ng','-v','de','-s','145','-w',str(root/'spoken.wav'),text],check=True)
subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(root/'spoken.wav'),'-ar','16000','-ac','1','-f','s16le',str(root/'spoken.pcm')],check=True)
app=QApplication([]);w=MainWindow();w.showFullScreen()
if w.splash_widget:w.splash_widget.hide()
w.engine.configure({'whisper_model':str(Path.home()/'.local/share/cdb-recorder-local/models/ggml-medium.bin'),'summary_model':'qwen3:4b-instruct','setup_complete':True})
# Synthetic process stands in for capture hardware, but real streaming recorder,
# Qt start/stop, durable queue, Whisper and Ollama are used without inference mocks.
script="import sys,time,signal;signal.signal(signal.SIGINT,lambda *_:sys.exit(0));f=open(sys.argv[1],'rb');\nwhile True:\n b=f.read(3200)\n if not b:f.seek(0);continue\n sys.stdout.buffer.write(b);sys.stdout.buffer.flush();time.sleep(.1)"
w.engine.recorder.command_factory=lambda _:[sys.executable,'-u','-c',script,str(root/'spoken.pcm')]
w.notice.setText('ABNAHMETEST · künstliches Audio · getrennte Testdaten')
started=time.monotonic();phase='init';first=None;second=None;third=None;events=[];history=[];last_states={};deadline=started+2400;dialog=None

def snapshot(name):w.grab().save(str(root/(name+'.png')))

def tick():
 global phase,first,second,third,started,dialog
 if time.monotonic()>deadline:finish('timeout');return
 s=w.state
 if not s:return
 for job in s['jobs']:
  if last_states.get(job['id'])!=job['state']:
   history.append({'id':job['id'],'state':job['state'],'at':time.time()})
   last_states[job['id']]=job['state']
 if phase=='init' and time.monotonic()-started>2:
  QTest.mouseClick(w.record_button,Qt.MouseButton.LeftButton);phase='recording';started=time.monotonic()
 elif phase=='recording' and s['recording']['id']:
  first=s['recording']['id']
  if time.monotonic()-started>20:
   snapshot('native-recording-pi');QTest.mouseClick(w.record_button,Qt.MouseButton.LeftButton);phase='processing'
 elif phase=='processing':
  j=next((x for x in s['jobs'] if x['id']==first),None)
  if j and j['state'] in ('transcribing','summarizing') and not w.busy:
   events.append('new_recording_while_'+j['state']);QTest.mouseClick(w.record_button,Qt.MouseButton.LeftButton);started=time.monotonic();phase='second'
 elif phase=='second' and s['recording']['id']:
  second=s['recording']['id']
  if time.monotonic()-started>3:
   QTest.mouseClick(w.record_button,Qt.MouseButton.LeftButton);phase='wait_summary'
 elif phase=='wait_summary':
  job=next((j for j in s['jobs'] if j['id']==first),None)
  if job and job['state']=='summarizing' and not w.busy and not s['recording']['id']:
   snapshot('native-summary-active-pi');events.append('new_recording_while_summarizing')
   QTest.mouseClick(w.record_button,Qt.MouseButton.LeftButton);phase='third';started=time.monotonic()
  elif job and job['state']=='failed':finish('first_failed');return
 elif phase=='third' and s['recording']['id']:
  third=s['recording']['id']
  if time.monotonic()-started>3:
   QTest.mouseClick(w.record_button,Qt.MouseButton.LeftButton);phase='wait'
 elif phase=='wait':
  jobs={x['id']:x for x in s['jobs']}
  if all(ident in jobs and jobs[ident]['state'] in ('completed','failed') for ident in (first,second,third)):
   for ident in (first,second,third):
    result=w.engine.result(ident)
    (root/('result-'+ident+'.json')).write_text(json.dumps({'job':jobs[ident],'result':result,'expected':text},ensure_ascii=False,indent=2))
   events.append({'all_completed':all(jobs[x]['state']=='completed' for x in (first,second,third))})
   first_session=next(r for r in w.repo.get_all() if r.get('local_job_id')==first)
   w._on_ai_view_requested(first_session['id']);snapshot('native-result-pi');w._on_ai_back()
   for i in range(30):w.repo.create('Testmeeting '+str(i),'2026-10-11T10:00:00','')
   w._load_sessions();app.processEvents()
   before=w.toolbar_settings_button.pos()
   ev=QWheelEvent(QPointF(300,200),QPointF(500,300),QPoint(),QPoint(0,-1200),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
   app.sendEvent(w.session_table.viewport(),ev)
   events.append({'scroll':w.session_table.verticalScrollBar().value(),'toolbar_fixed':w.toolbar_settings_button.pos()==before})
   snapshot('native-meetings-pi')
   dialog=SettingsDialog(w.settings_manager,w,local_host=w);dialog.show();dialog.local_panel.setup_tabs.setCurrentIndex(1)
   phase='screens';started=time.monotonic()
 elif phase=='screens' and time.monotonic()-started>3:
  dialog.grab().save(str(root/'native-models-pi.png'));dialog.local_panel.setup_tabs.setCurrentIndex(0)
  dialog.grab().save(str(root/'native-audio-pi.png'));dialog.reject()
  (root/'events.json').write_text(json.dumps({'events':events,'history':history},indent=2));phase='finish';started=time.monotonic()
 elif phase=='finish' and time.monotonic()-started>2:finish('completed')

def finish(status):
 timer.stop();w.timer.stop();w.activity_timer.stop()
 if w.engine.recorder.active:w.engine.stop()
 for t in list(w.tasks):t.wait(5000)
 w.engine.close();w.player_widget.player.close()
 print('ACCEPTANCE',status,events,flush=True);app.quit()

timer=QTimer();timer.timeout.connect(tick);timer.start(500);app.exec()
