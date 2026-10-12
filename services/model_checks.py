"""Independent, persistent synthetic model checks; never changes active settings."""
import json
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from meeting_recorder.core import atomic_write
from meeting_recorder.processing import LocalModels
from meeting_recorder.child_process import owned_command
from services.cdb_integration import CdbBackend

SAMPLE = 'Anna erstellt bis Donnerstag eine Aufgabenliste. Die Kosten sind noch ungeklärt.'

class ModelChecks:
    def __init__(self, app):
        self.app=app; self.root=app.store.root/'model-checks'; self.root.mkdir(exist_ok=True)
        self.path=self.root/'latest.json'; self.lock=threading.RLock(); self.thread=None
        self.stopping=threading.Event()
        try:self.latest=json.loads(self.path.read_text())
        except (OSError,ValueError):self.latest={'state':'idle'}
        if self.latest['state']=='running':self.save(state='failed',message='Test unterbrochen. Bitte erneut testen.')

    def save(self, **values):
        with self.lock:
            self.latest.update(values); atomic_write(self.path,json.dumps(self.latest,ensure_ascii=False))
            self.path.chmod(0o600)

    def public(self):
        with self.lock:return {k:v for k,v in self.latest.items() if k != 'fingerprint'}

    def selection(self, body):
        stage=body.get('stage'); provider=body.get('provider')
        if stage not in ('transcription','summary') or provider not in ('local','cdb'):raise ValueError('Verarbeitung und Modelltyp wählen.')
        result={'stage':stage,'provider':provider}
        if provider=='cdb':
            s=self.app.cdb.session()
            result.update(model='company-standard',label='Brain · Unternehmensstandard',binding={'server':s['server'],**{k:s['identity'][k] for k in ('user_id','client_id')}})
            return result,None
        catalog=self.app.models.catalog(); backend='whisper' if stage=='transcription' else 'ollama'
        model=next((m for m in catalog['asr' if stage=='transcription' else 'llm'] if m['id']==body.get('model')),None)
        if not model or not model['installed']:raise ValueError('Modell zuerst herunterladen.')
        if not catalog['whisper_runtime' if stage=='transcription' else 'ollama']:raise ValueError('Lokale Laufzeit fehlt. Unter Gerät & Diagnose prüfen.')
        if model.get('candidate') and not model.get('runtime_compatible'):raise ValueError('Dieses Modell ist mit der lokalen Laufzeit noch nicht bestätigt.')
        result.update(model=model['id'],label=model['label'],fingerprint=model.get('fingerprint'))
        return result,(backend,model)

    def start(self, body):
        selection,entry=self.selection(body)
        if entry:self.app.model_test_preflight()
        with self.lock:
            if self.latest['state']=='running':raise ValueError('Ein Modelltest läuft bereits.')
            self.latest=selection|{'id':uuid.uuid4().hex,'state':'running','message':'Künstliches Beispiel wird geprüft …','started':time.time()}
            self.save()
            self.thread=threading.Thread(target=self.run,args=(dict(self.latest),entry),daemon=True); self.thread.start()
            return self.public()

    def execute(self, selection, entry):
        folder=self.root/selection['id']; folder.mkdir(mode=0o700)
        config=self.app.store.config()|{'threads':2,'process_timeout':300,'summary_timeout':180,'context_size':2048,'prompt':'Fasse den Text knapp auf Deutsch zusammen. Nenne nur ausdrücklich vereinbarte Aufgaben und offene Punkte.','model_test':True}
        local=LocalModels(self.stopping)
        if selection['stage']=='transcription':
            if not shutil.which('espeak-ng'):raise ValueError('Künstliche Teststimme fehlt (espeak-ng).')
            subprocess.run(owned_command(['espeak-ng','-v','de','-s','155','-w',str(folder/'audio.wav'),SAMPLE]),check=True,timeout=20,capture_output=True)
            if entry:return local.transcribe(folder,config|{'whisper_model':entry[1]['path']})
            return CdbBackend(self.app.cdb).remote_transcribe(folder,selection,timeout=300)
        if entry:return local.generate(SAMPLE,config|{'summary_model':entry[1]['id']})
        r=self.app.cdb.call('/api/v1/tqs/agent/structure-text',{'text':SAMPLE,'instructions':config['prompt'],'max_tokens':1000,'temperature':0.0},selection['binding'])
        if r.get('stop_reason') not in ('completed','stop','end_turn'):raise ValueError('Online-Modell hat den Test nicht vollständig abgeschlossen.')
        return r.get('content','')

    def run(self, selection, entry):
        try:
            result=self.execute(selection,entry)
            if not isinstance(result,str) or not result.strip():raise ValueError('Modell hat kein Ergebnis geliefert.')
            if self.stopping.is_set():raise ValueError('Test unterbrochen. Bitte erneut testen.')
            if entry:
                backend,old=entry
                current=self.app.models.catalog()['asr' if backend=='whisper' else 'llm']
                if not any(m['id']==old['id'] and m.get('fingerprint')==old.get('fingerprint') for m in current):raise ValueError('Modell wurde während des Tests geändert. Erneut testen.')
                self.app.models.validate_pair({backend:old})
            else:self.app.cdb.session(selection['binding'])
            self.save(state='completed',message='Test erfolgreich · Auswahl kann aktiviert werden.',result=result[:1200],seconds=round(time.time()-selection['started'],1))
        except Exception as e:
            self.save(state='failed',message=str(e),seconds=round(time.time()-selection['started'],1))

    def use(self, body):
        selection,entry=self.selection(body)
        if entry:
            if not entry[1].get('tested'):raise ValueError('Dieses Modell zuerst erfolgreich testen.')
        else:
            if self.latest.get('state')!='completed' or any(self.latest.get(k)!=selection.get(k) for k in ('stage','provider','model','binding')):raise ValueError('Diesen Brain-Zugang zuerst erfolgreich testen.')
        stage=selection['stage']; old_provider=self.app.cdb.config()[stage]
        self.app.cdb.configure({stage:selection['provider']})
        try:
            if entry:self.app.engine.configure({('whisper_model' if stage=='transcription' else 'summary_model'):entry[1]['path' if stage=='transcription' else 'id']})
        except Exception:
            self.app.cdb.configure({stage:old_provider});raise
        return {'active':selection['label']}
