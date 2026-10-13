/* Readiness is observed, not inferred from a previously completed setup. */
function recorderReadiness(s,connected,snapshot){
 const status=(tone,label,target=null)=>({tone,label,target});
 if(!connected||!s)return status('waiting','Verbindung prüfen');
 if(s.recording.id)return status('ready','Aufnahme läuft');
 if(s.microphone_test?.state==='running')return status('waiting','Mikrofontest läuft');
 if(s.installation?.state==='running')return status('waiting','Download läuft');
 if(s.model_check?.state==='running'||s.capabilities?.configure?.allowed===false)return status('waiting','Gerät beschäftigt');
 if(!snapshot)return status('waiting','Status wird geprüft');
 if(snapshot.error)return status('waiting','Prüfung nicht verfügbar');
 if(!snapshot.devices.some(d=>d.id===s.config.device))return status('error','Mikrofon fehlt','audio-page');
 const cloud=s.cdb?.config||{};
 if([cloud.transcription,cloud.summary].includes('cdb')&&!s.cdb.identity)return status('error','Brain anmelden','connection-page');
 for(const check of snapshot.setup.checks){
  if(check.ok)continue;
  if(check.label==='Mikrofon getestet')return status('error','Mikrofon prüfen','audio-page');
  if(check.label==='CDB-Firmenanmeldung')return status('error','Brain anmelden','connection-page');
  if(['Transkriptionsprogramm vorhanden','Sprachmodell installiert'].includes(check.label))return status('error','Transkription prüfen','asr-page');
  if(['Lokaler Modelldienst bereit','Zusammenfassungsmodell installiert'].includes(check.label))return status('error','Zusammenfassung prüfen','llm-page');
  return status('error','Einrichtung prüfen','models-page');
 }
 if(!s.config.setup_complete)return status('error','Einrichtung abschließen','audio-page');
 if(s.capabilities?.record?.allowed===false)return status('error',/Speicher/.test(s.capabilities.record.reason)?'Speicher knapp':'Einrichtung prüfen',/Speicher/.test(s.capabilities.record.reason)?'library':'audio-page');
 return status('ready','Aufnahmebereit');
}
function readinessKey(s){return JSON.stringify([s?.config,s?.cdb?.config,s?.cdb?.identity?.user_id,s?.microphone_test,s?.installation?.state,s?.model_check?.state])}
let readinessSnapshot=null,readinessSnapshotKey='',readinessChecked=0,readinessPending=false;
function currentReadiness(){return recorderReadiness(state,online,readinessKey(state)===readinessSnapshotKey&&Date.now()-readinessChecked<20000?readinessSnapshot:null)}
function renderRecorderReadiness(){
 if(!online){readinessSnapshot=null;readinessSnapshotKey='';readinessChecked=0}
 const view=currentReadiness(),button=$('mic-settings');
 $('ready-heading').textContent=view.tone==='ready'?'Bereit für eine neue Aufnahme':view.label;
 $('ready-instruction').textContent=view.target?'Tippe links auf die rote Statusanzeige, um den offenen Punkt zu prüfen.':view.tone==='ready'?'Starte links deine Aufnahme. Deine Notizen erscheinen hier.':'Sobald die Prüfung abgeschlossen ist, kannst du hier aufnehmen.';
 button.dataset.status=view.tone;button.disabled=!view.target||Boolean(recordingAction);
 button.title=view.target?'Offenen Punkt prüfen':'';$('mic-name').textContent=view.label;
 button.setAttribute('aria-label',view.label+(view.target?' · '+(view.target==='library'?'Bibliothek öffnen':'Einstellungen öffnen'):''));
 if(view.tone==='error'&&!state?.recording.id)$('capture-hint').textContent='Bitte zuerst den markierten Punkt prüfen.';
 // Keep Stop available; missing prerequisites should never offer a new recording.
 if(!state?.recording.id&&view.tone!=='ready'){$('record').disabled=true;$('record').title=view.label}
}
async function refreshRecorderReadiness(){
 if(readinessPending||!online||!state||state.recording.id||state.capabilities?.configure?.allowed===false)return;
 const key=readinessKey(state);
 if(key===readinessSnapshotKey&&Date.now()-readinessChecked<10000)return;
 readinessPending=true;
 try{
  const [setup,inventory]=await Promise.all([api('/api/setup'),api('/api/devices')]);
  if(key===readinessKey(state)&&online){readinessSnapshot={setup,devices:inventory.devices};readinessSnapshotKey=key;readinessChecked=Date.now()}
 }catch(_){readinessSnapshot={error:true};readinessSnapshotKey=key;readinessChecked=Date.now()}
 finally{readinessPending=false;renderState()}
}
const beforeReadinessState=renderState;
renderState=function(){beforeReadinessState();renderRecorderReadiness();refreshRecorderReadiness()};
$('mic-settings').onclick=run(async()=>{
 const view=currentReadiness();if(!view.target||!online||state?.recording.id||recordingAction)return;
 if(view.target==='library'){await $('library-open').onclick();return}
 await openSettings();if(!state?.recording.id)showSettingsDetail(view.target);
});
