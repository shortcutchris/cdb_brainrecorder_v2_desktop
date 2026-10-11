"""Local audio/model controls embedded in the original native settings dialog."""
import json
from pathlib import Path
import subprocess
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QComboBox,
    QProgressBar,QTabWidget,QScrollArea,QFormLayout,QGroupBox,QLineEdit,QMessageBox,QScroller)
from meeting_recorder.audio import devices
from meeting_recorder.core import atomic_write
from player import AudioPlayer

STATE={'recording':'Aufnahme','importing':'Audio vorbereiten','queued':'Wartet',
       'transcribing':'Transkription läuft','summarizing':'Zusammenfassung läuft','completed':'Fertig','failed':'Fehler'}

def label(text,heading=False):
    w=QLabel(text);w.setWordWrap(True);return w

def button(text,callback,primary=False):
    w=QPushButton(text);w.setMinimumHeight(44);w.clicked.connect(callback);return w

def touch_scroll(widget):
    QScroller.grabGesture(widget.viewport(),QScroller.ScrollerGestureType.TouchGesture)

class LocalSettingsPanel(QWidget):
    def __init__(self,host):
        super().__init__()
        self.host=host;self.engine=host.engine;self.player=AudioPlayer()
        self.player.error.connect(self.error)
        self.catalog={};self.state={};self.test_job=None;self.last_download=None
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        self.notice=label('Audio- und Modellauswahl werden direkt gespeichert. Neue Aufnahmen werden nach Stop automatisch lokal verarbeitet.');outer.addWidget(self.notice)
        self.stack=QVBoxLayout();outer.addLayout(self.stack)
        self.build_settings();self.load_setup()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(1000)

    def task(self,fn,done=None,exclusive=False):
        self.host.task(fn,done,exclusive,error=self.error)

    def error(self,message):self.notice.setText(message)

    def refresh(self):
        self.state=self.host.state
        self.update_setup_status()

    def shutdown(self):
        self.timer.stop();self.player.close()

    def scrolled(self):
        scroll=QScrollArea(); scroll.setWidgetResizable(True); touch_scroll(scroll)
        inner=QWidget(); layout=QVBoxLayout(inner); layout.setSpacing(14); scroll.setWidget(inner)
        return scroll,layout


    def build_settings(self):
        page=QWidget(); v=QVBoxLayout(page); v.setContentsMargins(0,0,0,0)
        v.addWidget(label('Lokale Aufnahme und KI-Verarbeitung'))
        self.setup_tabs=QTabWidget(); v.addWidget(self.setup_tabs,1)
        audio,a=self.scrolled(); self.setup_tabs.addTab(audio,'1 · Audio')
        a.addWidget(label('Mikrofon auswählen und fünf Sekunden testen.'))
        self.mic=QComboBox(); self.mic.setMinimumHeight(54); a.addWidget(self.mic)
        self.mic.activated.connect(self.save_mic)
        a.addWidget(button('Geräte aktualisieren',self.load_setup))
        self.mic_note=label(''); a.addWidget(self.mic_note)
        self.probe_button=button('Mikrofon testen · 5 Sekunden',self.start_probe,True); a.addWidget(self.probe_button)
        self.probe_meter=QProgressBar(); a.addWidget(self.probe_meter)
        self.probe_note=label(''); a.addWidget(self.probe_note)
        a.addWidget(button('Testaufnahme anhören',self.play_probe))
        a.addWidget(button('Weiter zu Modelle',lambda:self.setup_tabs.setCurrentIndex(1))); a.addStretch()
        models,m=self.scrolled(); self.setup_tabs.addTab(models,'2 · Modelle')
        m.addWidget(label('Qualitätsorientierter Einstieg für 8 GB · medium + Qwen3 4B Instruct.'))
        self.asr=QComboBox(); self.llm=QComboBox()
        m.addWidget(label('Sprache erkennen · Whisper')); m.addWidget(self.asr)
        self.asr_note=label(''); m.addWidget(self.asr_note)
        self.asr_install=button('Whisper bewusst herunterladen',lambda:self.install('whisper'),True); m.addWidget(self.asr_install)
        m.addWidget(label('Zusammenfassen · lokales Sprachmodell')); m.addWidget(self.llm)
        self.llm_note=label(''); m.addWidget(self.llm_note)
        self.llm_install=button('Sprachmodell bewusst herunterladen',lambda:self.install('ollama'),True); m.addWidget(self.llm_install)
        self.asr.activated.connect(self.save_models); self.llm.activated.connect(self.save_models)
        self.download=QProgressBar(); m.addWidget(self.download); self.download_note=label(''); m.addWidget(self.download_note)
        self.test_button=button('Beide Modelle mit Testaufnahme prüfen',self.test_models); m.addWidget(self.test_button)
        self.test_note=label('Test nutzt künstlich erzeugte deutsche Sprache, keine vorhandenen Meetings.'); m.addWidget(self.test_note)
        m.addWidget(button('Weiter zu Bereit',lambda:self.setup_tabs.setCurrentIndex(2)))
        ready,r=self.scrolled(); self.setup_tabs.addTab(ready,'3 · Bereit')
        self.checks=label(''); r.addWidget(self.checks)
        r.addWidget(button('Bereitschaft erneut prüfen',self.load_setup))
        self.finish_button=button('Einrichtung abschließen',self.finish_setup,True); r.addWidget(self.finish_button)
        r.addWidget(label('Keine automatische Löschung. Exportiere Aufnahmen, bevor du sie bewusst entfernst.'))
        advanced=QGroupBox('Erweiterte Einstellungen'); f=QFormLayout(advanced)
        self.binary=QLineEdit(); f.addRow('Whisper-Programm',self.binary)
        f.addRow(button('Programmpfad speichern',self.save_advanced)); r.addWidget(advanced); r.addStretch()
        self.stack.addWidget(page)

    def load_setup(self):
        def read():return self.engine.models.catalog(),devices(),self.engine.store.config()
        def done(result):
            catalog,audio,c=result;self.catalog=catalog
            for combo,items,key,current in [(self.asr,catalog['asr'],'path',c['whisper_model']),(self.llm,catalog['llm'],'id',c['summary_model'])]:
                combo.clear()
                for item in items:combo.addItem(item['label']+' · '+('installiert' if item['installed'] else 'fehlt'),item[key])
                combo.setCurrentIndex(max(0,combo.findData(current)))
            self.mic.clear()
            for item in audio['devices']:self.mic.addItem(item['label'],item['id'])
            if not audio['devices']:self.mic.addItem('Kein Mikrofon gefunden',None)
            self.mic.setCurrentIndex(max(0,self.mic.findData(c['device'])))
            self.mic_note.setText('Bitte USB-Mikrofon anschließen und aktualisieren.' if not audio['devices'] else 'Auswahl wird gespeichert. Der Ton wird am Pi aufgenommen.')
            self.binary.setText(c['whisper_binary']);self.update_setup_status()
        self.task(read,done)


    def save_mic(self):
        value=self.mic.currentData()
        if value:self.task(lambda:self.engine.configure({'device':value,'setup_complete':False}),lambda _:self.load_setup(),True)


    def save_models(self):
        changes={'whisper_model':self.asr.currentData(),'summary_model':self.llm.currentData(),'setup_complete':False}
        self.task(lambda:self.engine.configure(changes),lambda _:self.load_setup(),True)


    def save_advanced(self):
        value=self.binary.text();self.task(lambda:self.engine.configure({'whisper_binary':value,'setup_complete':False}),lambda _:self.load_setup(),True)


    def install(self,backend):
        entries=self.catalog.get('asr' if backend=='whisper' else 'llm',[])
        selected=self.asr.currentData() if backend=='whisper' else self.llm.currentData()
        model=next((m for m in entries if m['path' if backend=='whisper' else 'id']==selected),None)
        if not model:return
        if QMessageBox.question(self,'Modell herunterladen',f"{model['label']} bewusst herunterladen?\nUngefähr {model['bytes']/1e9:.1f} GB plus Reserve.\n{model['license']}\nEs werden keine Meetings übertragen.")!=QMessageBox.StandardButton.Yes:return
        self.task(lambda:self.engine.models.install(backend,model['id']),lambda _:self.load_setup(),True)


    def update_setup_status(self):
        if not self.state:return
        s=self.state;p=s['microphone_test'];d=s['installation'];c=s['config']
        self.probe_note.setText(p.get('message',''));self.probe_meter.setValue(p.get('level',0))
        active=bool(s['recording']['id']) or p['state']=='running'
        self.probe_button.setEnabled(not active);self.mic.setEnabled(not active and self.mic.currentData() is not None)
        self.asr.setEnabled(not active);self.llm.setEnabled(not active)
        for combo,entries,note,install,key in [(self.asr,self.catalog.get('asr',[]),self.asr_note,self.asr_install,'path'),(self.llm,self.catalog.get('llm',[]),self.llm_note,self.llm_install,'id')]:
            item=next((i for i in entries if i[key]==combo.currentData()),None)
            if item:
                note.setText(item['description']+' · '+item['license'])
                install.setEnabled(not item['installed'] and item['id']!='custom' and d['state']!='running')
        self.download.setRange(0,100);self.download.setValue(int(d.get('completed',0)/max(1,d.get('total',1))*100))
        self.download_note.setText(d.get('message','')+(f" · {d.get('completed',0)/1e6:.0f}/{d.get('total',0)/1e6:.0f} MB" if d.get('total') else ''))
        if d['state']=='completed' and getattr(self,'last_download',None)!='completed':self.load_setup()
        self.last_download=d['state']
        checks=[('Mikrofon getestet',p['state']=='completed' and p.get('device')==c['device']),
                ('Whisper-Programm',self.catalog.get('whisper_runtime',False)),
                ('Whisper-Modell',Path(c['whisper_model']).is_file()),
                ('Lokaler Modelldienst',self.catalog.get('ollama',False)),
                ('Zusammenfassungsmodell',any(m['id']==c['summary_model'] and m['installed'] for m in self.catalog.get('llm',[])))]
        self.checks.setText('\n\n'.join(('✓  ' if ok else '○  ')+name+(' · bereit' if ok else ' · offen') for name,ok in checks))
        self.ready=all(ok for _,ok in checks);self.finish_button.setEnabled(self.ready)
        self.test_button.setEnabled(not self.test_job and checks[1][1] and checks[2][1] and checks[3][1] and checks[4][1])
        if self.test_job:
            j=next((j for j in s['jobs'] if j['id']==self.test_job),None)
            if j:
                self.test_note.setText('Modelltest · '+STATE.get(j['state'],j['state'])+'\n'+j['error'])
                if j['state'] in ('completed','failed'):
                    metrics=json.loads(j['metrics']);self.test_note.setText(self.test_note.text()+'\n'+json.dumps(metrics,ensure_ascii=False));self.test_job=None


    def start_probe(self):self.task(self.engine.probe.start,exclusive=True)


    def play_probe(self):
        try:self.player.load_file(str(self.engine.probe.folder/'audio.wav'));self.player.play()
        except Exception as e:self.error(str(e))


    def test_models(self):
        def create():
            folder=self.engine.store.root/'model-test';folder.mkdir(exist_ok=True)
            source=folder/'spoken.wav'
            text='Dies ist ein technischer Modelltest. Das Team entscheidet, die Besprechung am Freitag um zehn Uhr fortzusetzen. Anna erstellt bis Donnerstag eine Liste der offenen Aufgaben. Die Kosten sind noch ungeklärt.'
            subprocess.run(['espeak-ng','-v','de','-s','145','-w',str(source),text],check=True,timeout=30,capture_output=True)
            ident=self.engine.enqueue(source,'Technischer Modelltest · künstliche Sprache')
            atomic_write(folder/'expected.txt',text)
            return ident
        self.task(create,lambda ident:setattr(self,'test_job',ident),True)


    def finish_setup(self):
        if self.ready:
            self.task(lambda:self.engine.configure({'setup_complete':True}),lambda _:self.error('Einrichtung gespeichert.'),True)
