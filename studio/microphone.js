/* The test sample is independent from live input: an old peak is never a live meter. */
let microphoneDevices=[],microphoneChecks=[],microphoneCheckSignature='',probePlaybackError=false;
const probeAudio=$('probe-audio');
function pauseMicrophoneAudio(){probeAudio.pause()}
function setMicrophoneSetup(checks,devices){microphoneChecks=checks;microphoneDevices=devices;renderMicrophone(state.microphone_test)}
function microphoneView(probe,connected,selectedDevice){
 const running=probe.state==='running',completed=probe.state==='completed';
 const sameDevice=completed&&probe.device===selectedDevice;
 return {running,level:running&&connected&&online?Math.max(0,Math.min(100,Number(probe.level)||0)):0,
  label:running&&online?'Live':!online?'Offline':'Inaktiv',
  message:!online?'Verbindung unterbrochen. Pegel wird erneut geprüft.':!connected?'Mikrofon anschließen oder einen verfügbaren Eingang wählen.':running?'Sprich jetzt in das ausgewählte Mikrofon.':completed&&!sameDevice?'Testaufnahme gehört zu einem anderen Mikrofon. Bitte neu testen.':completed?(probe.message||'Test beendet. Höre dir die Aufnahme an.'):probe.state==='failed'?probe.message:'Starte den Test, um den Eingangspegel zu sehen.',
  ready:online&&connected&&sameDevice,
  checkStatus:!online?'Offline':!connected?'Nicht verbunden':running?'Läuft …':probe.state==='failed'?'Fehlgeschlagen':sameDevice?'Bereit':'Offen',
  sampleLabel:!online?'Offline':completed?(!connected||!sameDevice?'Frühere Aufnahme':'Bereit'):running?'Test läuft …':probe.state==='failed'?'Test fehlgeschlagen':'Noch kein Test'};
}
function renderMicrophone(probe){
 const connected=microphoneDevices.some(d=>d.id===$('mic-select').value);
 const view=microphoneView(probe,connected,$('mic-select').value);
 const remaining=probe.seconds_left??5;
 $('probe-start').dataset.counting=String(view.running&&online);
 const lock=state?.capabilities?.probe;
 const idleLabel=view.ready?'Erneut testen · 5 Sekunden':'Mikrofon testen · 5 Sekunden';
 $('probe-start').textContent=view.running&&online?(remaining>0?'Noch '+remaining+' s':'Aufnahme wird abgeschlossen …'):idleLabel;
 $('probe-level').value=view.level;$('probe-level-label').textContent=view.label;$('probe-state').textContent=!view.running&&online&&connected&&lock?.allowed===false&&lock.reason?view.message+' Neuer Test gesperrt: '+lock.reason:view.message;
 if(view.running||state?.recording.id||!online)pauseMicrophoneAudio();
 if(probe.state!=='completed'&&probeAudio.hasAttribute('src')){probeAudio.removeAttribute('src');probeAudio.load();probePlaybackError=false}
 const checks=microphoneChecks.map(check=>{
  const mic=check.label==='Mikrofon getestet';
  return {label:check.label,ok:mic?view.ready:online&&check.ok,
   status:mic?view.checkStatus:!online?'Offline':check.ok?'Bereit':'Offen'};
 });
 renderSetupChecklist(checks);
 renderProbePlayer(view);
}
const setupDestinations={
 'Mikrofon getestet':['Mikrofontest','audio-page'],
 'Transkriptionsprogramm vorhanden':['Whisper-Laufzeit','asr-page'],
 'Sprachmodell installiert':['Transkriptionsmodell','asr-page'],
 'Lokaler Modelldienst bereit':['Lokaler Modelldienst','llm-page'],
 'Zusammenfassungsmodell installiert':['Zusammenfassungsmodell','llm-page'],
 'CDB-Firmenanmeldung':['Brain-Konto','connection-page']
};
function renderSetupChecklist(checks){
 const open=checks.filter(check=>!check.ok).length;
 $('setup-progress').textContent=!online?'Verbindung unterbrochen.':!checks.length?'Status wird geprüft …':
  open?(open===1?'Ein Schritt ist offen.':open+' Schritte sind offen.')+' Tippe auf einen Eintrag, um ihn zu prüfen.':
  state.config?.setup_complete?'Einrichtung abgeschlossen.': 'Alle Voraussetzungen sind erfüllt. Du kannst die Einrichtung abschließen.';
 const signature=JSON.stringify(checks);
 if(signature===microphoneCheckSignature)return;
 microphoneCheckSignature=signature;
 $('checks').replaceChildren();
 for(const check of checks){
  const [title,page]=setupDestinations[check.label]||[check.label,null];
  const row=document.createElement(page?'button':'div');
  row.className='audio-check';row.dataset.ready=String(check.ok);
  if(page)row.onclick=()=>showSettingsDetail(page);
  const label=document.createElement('span');label.className='audio-check-label';label.textContent=title;
  const status=document.createElement('span');status.className='audio-check-state';status.textContent=check.status;
  row.append(icon(check.ok?'check-circle':'circle'),label,status);
  if(page)row.append(icon('caret-right'));
  $('checks').append(row);
 }
}
function renderProbePlayer(view){
 view=view||microphoneView(state?.microphone_test||{},microphoneDevices.some(d=>d.id===$('mic-select').value),$('mic-select').value);
 const available=state?.microphone_test?.state==='completed'&&probeAudio.hasAttribute('src')&&online&&!state?.recording.id;
 $('probe-play').disabled=!available;$('probe-mute').disabled=!available;$('probe-seek').disabled=!available||!Number.isFinite(probeAudio.duration)||probeAudio.duration<=0;
 $('probe-play-text').textContent=probeAudio.paused?'Anhören':'Pause';
 setIcon($('probe-play-icon'),'/assets/'+(probeAudio.paused?'play':'pause')+'.svg');$('probe-play').setAttribute('aria-label',probeAudio.paused?'Testaufnahme abspielen':'Testaufnahme pausieren');
 $('probe-player-state').textContent=probePlaybackError?'Wiedergabe fehlgeschlagen':!probeAudio.paused?'Wird abgespielt':view.sampleLabel;
 $('probe-time').textContent=duration(probeAudio.currentTime);$('probe-total').textContent=duration(probeAudio.duration);
 const position=Number.isFinite(probeAudio.duration)&&probeAudio.duration>0?probeAudio.currentTime/probeAudio.duration*1000:0;
 $('probe-seek').value=position;$('probe-seek').style.setProperty('--played',(position/10)+'%');
}
$('probe-play').onclick=run(async()=>{if($('probe-play').disabled)return;if(probeAudio.paused){audio.pause();if(probePlaybackError){probePlaybackError=false;probeAudio.load()}try{await probeAudio.play()}catch(error){probePlaybackError=true;renderProbePlayer();throw error}}else pauseMicrophoneAudio()});
$('probe-seek').oninput=()=>{if(!$('probe-seek').disabled&&Number.isFinite(probeAudio.duration)){probeAudio.currentTime=probeAudio.duration*Number($('probe-seek').value)/1000;renderProbePlayer()}};
$('probe-mute').onclick=()=>{probeAudio.muted=!probeAudio.muted;$('probe-mute').setAttribute('aria-pressed',String(probeAudio.muted));$('probe-mute').setAttribute('aria-label',probeAudio.muted?'Ton der Testaufnahme einschalten':'Testaufnahme stummschalten')};
for(const event of ['play','pause','ended','timeupdate','durationchange','loadedmetadata','emptied'])probeAudio.addEventListener(event,()=>renderProbePlayer());
probeAudio.addEventListener('loadstart',()=>{probePlaybackError=false;renderProbePlayer()});
probeAudio.addEventListener('error',()=>{if(probeAudio.hasAttribute('src')){probePlaybackError=true;renderProbePlayer()}});
// Stop sample playback whenever the user leaves Audio, including its settings overview.
new MutationObserver(()=>{if($('audio-page').hidden||$('settings').dataset.overview==='true'||!$('settings').open)pauseMicrophoneAudio()}).observe($('settings'),{attributes:true,subtree:true,attributeFilter:['hidden','data-overview','open']});
