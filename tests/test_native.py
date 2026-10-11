import json
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import tempfile
import time
import unittest
import wave
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QSplitter
from PySide6.QtCore import Qt, QPoint, QPointF, QSettings
from PySide6.QtGui import QWheelEvent
from data.repo import SessionRepository
from services.local_controller import LocalController
from player import AudioPlayer

_qt_settings=tempfile.TemporaryDirectory()
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,_qt_settings.name)
app=QApplication.instance() or QApplication([])

class Backend:
    def transcribe(self,folder,c):return 'Transkript für genau diese Session.'
    def generate(self,text,c,merge=False):return 'Zusammenfassung dieser Session.'

def wait_for(fn):
    end=time.monotonic()+8
    while time.monotonic()<end:
        if fn():return
        time.sleep(.05)
    raise AssertionError('Timeout')

class NativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.repo=SessionRepository(str(self.root/'sessions.db'))
        self.audio=self.root/'test.wav'
        with wave.open(str(self.audio),'wb') as w:
            w.setparams((1,2,16000,0,'NONE','none'));w.writeframes(b'\0\0'*16000)
    def tearDown(self):self.tmp.cleanup()
    def test_migration_preserves_existing_notes_and_transcript(self):
        sid=self.repo.create('Original','2025-01-01',str(self.audio),notes='Unverändert')
        self.repo.update_transcript(sid,'Bestehender Text',17)
        reopened=SessionRepository(self.repo.db_path)
        r=reopened.get_by_id(sid)
        self.assertEqual(r['notes'],'Unverändert');self.assertEqual(r['transcript_text'],'Bestehender Text')
        self.assertIn('summary_text',r)
    def test_stale_legacy_pending_is_actionable_without_losing_content(self):
        sid=self.repo.create('Original','2025-01-01',str(self.audio),notes='Keep')
        self.repo.update_transcript(sid,'Checkpoint',17,'pending')
        c=LocalController(self.repo,self.root/'local',backend=Backend())
        try:
            row=self.repo.get_by_id(sid)
            self.assertEqual(row['transcription_status'],'failed')
            self.assertIn('unterbrochen',row['local_error'])
            self.assertEqual(row['transcript_text'],'Checkpoint')
            self.assertEqual(row['notes'],'Keep')
            self.assertEqual(c.engine.store.list(),[])
        finally:c.engine.close()

    def test_original_session_mapping_no_selected_row_dependency(self):
        first=self.repo.create('A','2025-01-01',str(self.audio));second=self.repo.create('B','2025-01-02',str(self.audio))
        c=LocalController(self.repo,self.root/'local',backend=Backend())
        try:
            jid=c.process(first,'Auftrag A');wait_for(lambda:c.engine.store.get(jid)['state']=='completed');c.sync()
            self.assertEqual(self.repo.get_by_id(first)['transcript_text'],'Transkript für genau diese Session.')
            self.assertIsNone(self.repo.get_by_id(second)['transcript_text'])
            jid2=c.process(first,'Auftrag A2');wait_for(lambda:c.engine.store.get(jid2)['state']=='completed');c.sync()
            self.assertEqual(len(self.repo.get_all()),2)
        finally:c.engine.close()
    def test_player_loads_metadata_and_callback_reads_bounded_block(self):
        p=AudioPlayer()
        with patch('soundfile.read',side_effect=AssertionError('Full audio read forbidden')):
            self.assertTrue(p.load_file(str(self.audio)))
        self.assertFalse(hasattr(p,'audio_data'))
        import numpy as np
        out=np.empty((2048,1),dtype='float32');p._callback(out,2048,None,None)
        self.assertEqual(p.current_frame,2048);p.close()
    def test_deleted_session_does_not_resurrect_from_queue(self):
        sid=self.repo.create('Delete','2025-01-01',str(self.audio))
        c=LocalController(self.repo,self.root/'local',backend=Backend())
        try:
            jid=c.process(sid);wait_for(lambda:c.engine.store.get(jid)['state']=='completed');c.sync()
            c.delete(sid);c.sync();self.assertEqual(self.repo.get_all(),[])
        finally:c.engine.close()

    def test_missing_output_device_reports_error_without_starting_playback(self):
        p=AudioPlayer();messages=[];p.error.connect(messages.append);p.load_file(str(self.audio))
        try:
            with patch('sounddevice.OutputStream',side_effect=RuntimeError('No device')):p.play()
            self.assertFalse(p.is_playing);self.assertIn('Audioausgabe',messages[0])
        finally:p.close()

    def test_activity_animation_fifo_and_elapsed_are_honest(self):
        from ui.queue_status import describe_queue
        state={'sessions':[{'local_job_id':key,'title':key} for key in ('active','a','b')],
               'jobs':[{'id':'active','state':'transcribing','updated':100,'created':1},
                       {'id':'a','state':'queued','updated':1,'created':1,'queued_at':30},
                       {'id':'b','state':'queued','updated':1,'created':2,'queued_at':20}]}
        moving,text,failed=describe_queue(state,165)
        self.assertTrue(moving);self.assertFalse(failed)
        self.assertIn('Transkription läuft · 01:05',text)
        self.assertIn('1. b → 2. a',text)
        self.assertNotIn('%',text)

    def test_original_ui_and_local_settings_at_two_display_sizes(self):
        from ui.main_window import MainWindow
        from ui.settings_dialog import SettingsDialog
        with patch.dict(os.environ,{'CDB_LOCAL_DATA':str(self.root/'ui'),'CDB_SESSION_DB':str(self.root/'ui.db')}):
            for i in range(35):SessionRepository(str(self.root/'ui.db')).create('Test '+str(i),'2026-10-11','')
            w=MainWindow();w.show()
            if w.splash_widget:w.splash_widget.hide()
            try:
                for width,height in [(1280,720),(1024,600)]:
                    w.resize(width,height);app.processEvents()
                    self.assertEqual((w.width(),w.height()),(width,height))
                    self.assertEqual(w.stacked_widget.count(),2)
                    self.assertGreater(w.main_view.findChild(QSplitter).height(),height-220)
                    self.assertFalse(w.pause_button.isVisible())
                    self.assertTrue(w.session_table.isVisible())
                    before=w.toolbar_settings_button.pos()
                    w.session_table.verticalScrollBar().setValue(0)
                    event=QWheelEvent(QPointF(200,150),QPointF(400,200),QPoint(),QPoint(0,-1200),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
                    app.sendEvent(w.session_table.viewport(),event);app.processEvents()
                    self.assertGreater(w.session_table.verticalScrollBar().value(),0)
                    self.assertEqual(w.toolbar_settings_button.pos(),before)
                w.state={'sessions':[{'local_job_id':'test','title':'Test'}],
                         'jobs':[{'id':'test','state':'transcribing','updated':time.time(),'created':time.time()}]}
                w.animate_activity();before=w.activity_icon.text();w.animate_activity()
                self.assertNotEqual(w.activity_icon.text(),before)
                d=SettingsDialog(w.settings_manager,w,local_host=w);d.show();app.processEvents()
                self.assertEqual(d.tabs.count(),2)
                self.assertEqual(d.local_panel.setup_tabs.count(),3)
                self.assertFalse(d.openai_group.isVisible())
                d.local_panel.shutdown();d.hide()
            finally:
                w.timer.stop()
                for t in list(w.tasks):t.wait(5000)
                app.processEvents()
                w.engine.close();w.hide()
