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
  message:!connected?'Kein Mikrofon verbunden. Anschließen und Geräte aktualisieren.':!online?'Verbindung unterbrochen. Pegel wird erneut geprüft.':running?'Sprich jetzt fünf Sekunden in das Mikrofon.':completed&&!sameDevice?'Testaufnahme gehört zu einem anderen Mikrofon. Bitte neu testen.':completed?(probe.message||'Test beendet. Höre dir die Aufnahme an.'):probe.message||'Starte einen kurzen Test und prüfe den Klang.',
  sampleLabel:completed?(!connected||!sameDevice?'Frühere Aufnahme':'Bereit'):running?'Test läuft …':probe.state==='failed'?'Test fehlgeschlagen':'Noch kein Test'};
}
function renderMicrophone(probe){
 const connected=microphoneDevices.some(d=>d.id===$('mic-select').value);
 const view=microphoneView(probe,connected,$('mic-select').value);
 $('probe-level').value=view.level;$('probe-level-label').textContent=view.label;$('probe-state').textContent=view.message;
 if(view.running||state?.recording.id||!online)pauseMicrophoneAudio();
 if(view.running&&probeAudio.hasAttribute('src')){probeAudio.removeAttribute('src');probeAudio.load();probePlaybackError=false}
 const labels={'Mikrofon getestet':'Mikrofontest','Transkriptionsprogramm vorhanden':'Whisper-Laufzeit','Sprachmodell installiert':'Transkriptionsmodell','Lokaler Modelldienst bereit':'Lokaler Modelldienst','Zusammenfassungsmodell installiert':'Zusammenfassungsmodell','CDB-Firmenanmeldung':'Brain-Konto'};
 const checks=microphoneChecks.map((check,i)=>({...check,label:labels[check.label]||check.label,ok:check.ok&&(i!==0||(connected&&probe.state==='completed'&&probe.device===$('mic-select').value)),status:i===0?(!connected?'Nicht verbunden':view.running?'Läuft …':probe.state==='failed'?'Fehlgeschlagen':check.ok&&probe.device===$('mic-select').value?'Bereit':'Offen'):check.ok?'Bereit':'Offen'}));
 const signature=JSON.stringify(checks);if(signature!==microphoneCheckSignature){microphoneCheckSignature=signature;$('checks').replaceChildren();for(const check of checks){const row=document.createElement('div');row.className='audio-check';row.dataset.ready=String(check.ok);row.setAttribute('role','listitem');const label=document.createElement('span');label.className='audio-check-label';label.textContent=check.label;const status=document.createElement('span');status.className='audio-check-state';status.textContent=check.status;row.append(icon(check.ok?'check-circle':'circle'),label,status);$('checks').append(row)}}
 renderProbePlayer(view);
}
function renderProbePlayer(view){
 view=view||microphoneView(state?.microphone_test||{},microphoneDevices.some(d=>d.id===$('mic-select').value),$('mic-select').value);
 const available=state?.microphone_test?.state==='completed'&&probeAudio.hasAttribute('src')&&online&&!state?.recording.id;
 $('probe-play').disabled=!available;$('probe-mute').disabled=!available;$('probe-seek').disabled=!available||!Number.isFinite(probeAudio.duration)||probeAudio.duration<=0;
 $('probe-play-icon').src='/assets/'+(probeAudio.paused?'play':'pause')+'.svg';$('probe-play').setAttribute('aria-label',probeAudio.paused?'Testaufnahme abspielen':'Testaufnahme pausieren');
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
