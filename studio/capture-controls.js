let captureControlBusy=false;
function renderCaptureControls(){
 const r=state?.recording,active=Boolean(r?.id),busy=captureControlBusy||recordingAction||!online;
 $('capture-controls').hidden=!active;
 document.querySelector('.capture').classList.toggle('is-active',active);
 $('capture-mute').textContent=r?.muted?'Mikro einschalten':'Mikro stumm';$('capture-mute').setAttribute('aria-pressed',String(Boolean(r?.muted)));
 $('capture-pause').textContent=r?.paused?'Fortsetzen':'Pause';$('capture-pause').setAttribute('aria-pressed',String(Boolean(r?.paused)));
 $('capture-mute').disabled=!active||busy;$('capture-pause').disabled=!active||busy;
 if(active){
  const label=r.paused?(r.muted?'Pausiert · Mikro stumm':'Aufnahme pausiert'):r.muted?'Mikrofon stumm':'Aufnahme läuft';
  $('mic-name').textContent=label;$('mic-settings').setAttribute('aria-label',label);$('mic-settings').dataset.status=r.paused||r.muted?'waiting':'ready';
  $('recording-lock').textContent=r.paused?'Pausiert · Keine Audiodaten werden gespeichert.':r.muted?'Mikro stumm · Die Aufnahme speichert Stille.':'Aufnahme läuft · Einstellungen bleiben gesperrt.';
  if(captureControlBusy)$('record').disabled=true;
 }
}
async function setCaptureControl(key){
 if(captureControlBusy||recordingAction||!online||!state?.recording.id)return;
 captureControlBusy=true;renderCaptureControls();
 try{const updated=await api('/api/record/control',{[key]:!state.recording[key]});if(state?.recording.id===updated.id)state.recording=updated;await poll()}
 catch(e){notice(e.message)}finally{captureControlBusy=false;renderState()}
}
$('capture-mute').onclick=()=>setCaptureControl('muted');$('capture-pause').onclick=()=>setCaptureControl('paused');
const beforeCaptureControls=renderState;
renderState=function(){beforeCaptureControls();renderCaptureControls()};
