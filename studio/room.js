/* Shared-room flow uses the same recorder, Brain login and knowledge picker. */
(() => {
 const panel = document.createElement('dialog'); panel.id='room-dialog';
 panel.setAttribute('aria-labelledby','room-title');
 panel.innerHTML=`<header class="dialog-heading"><h2 id="room-title">Meeting vorbereiten</h2><button id="room-close" aria-label="Abbrechen">Schließen</button></header>
  <div class="dialog-body"><p id="room-person"></p><p id="room-message" role="status"></p>
  <p id="room-nfc" hidden>Lass den Aufsteller liegen. Erst deine Bestätigung startet Aufnahme oder Gespräch.</p></div>
  <footer class="dialog-actions"><button id="room-other">Anderes Konto</button><button id="room-knowledge">Gesprächswissen wählen</button><button id="room-login" class="primary">Mit Brain anmelden</button><button id="room-start" class="primary">Aufnahme starten</button></footer>`;
 document.body.append(panel);
 const end=document.createElement('button');end.id='room-finish';end.textContent='Fertig & abmelden';document.body.append(end);
 const settingsButton=document.createElement('button');settingsButton.id='room-settings';settingsButton.textContent='Anmeldung & Geräteschutz';
 $('management-page').querySelector('.dialog-actions').prepend(settingsButton);
 const settings=document.createElement('dialog');settings.id='room-settings-dialog';settings.setAttribute('aria-labelledby','room-settings-title');
 settings.innerHTML=`<header class="dialog-heading"><h2 id="room-settings-title">Anmeldung & Geräteschutz</h2><button id="room-settings-close">Schließen</button></header>
  <div class="dialog-body"><p>Talk und Meeting beginnen mit deiner Brain-Anmeldung. Jede Person sieht nur ihre eigenen Aufnahmen. Während einer Aufnahme, einer Pause oder eines Gesprächs bleibst du angemeldet.</p>
  <div id="room-options"><div class="room-fields"><label id="room-minutes-label">Ruhefrist (Minuten)<input id="room-minutes" type="number" min="2" max="60" value="15"></label><label id="room-pin-label">Betreiber-PIN <input id="room-pin" type="password" inputmode="numeric" autocomplete="off" maxlength="12" placeholder="6 bis 12 Ziffern"></label></div><label class="room-noise-choice" id="room-noise-choice"><input id="room-noise" type="checkbox"> Raumgeräusche berücksichtigen</label><p class="room-noise-note" id="room-noise-note">Mikrofon bleibt bei angemeldeter Sitzung aktiv. Nur lokale Pegelauswertung; kein Ton wird gespeichert oder übertragen. Geräusche können die Abmeldung hinauszögern.</p></div>
  <p id="room-settings-message" role="status"></p></div><footer class="dialog-actions"><button id="room-pin-keys">Tastatur</button><button id="room-unlock" class="primary">Entsperren</button><button id="room-save" class="primary">Speichern</button></footer>`;
 document.body.append(settings);
 const micStatus=document.createElement('span');micStatus.id='room-mic-status';micStatus.setAttribute('role','status');end.after(micStatus);
 const micHint=document.createElement('small');micHint.id='room-mic-hint';$('account-shortcut').querySelector('span').append(micHint);
 const idle=document.createElement('dialog');idle.id='room-idle';idle.setAttribute('aria-labelledby','room-idle-title');
 idle.innerHTML='<h2 id="room-idle-title">Bist du noch da?</h2><p id="room-idle-message"></p><footer class="dialog-actions"><button id="room-idle-finish">Jetzt abmelden</button><button id="room-stay" class="primary" autofocus>Angemeldet bleiben</button></footer>';document.body.append(idle);
 let busy=false,loginAttempt=null,epoch=null,touched=0,message='';
 const room=()=>state?.room;
 const post=async(name,body={})=>{const result=await api('/api/room/'+name,body);await poll();return result};
 window.beginRoom=async mode=>{if(busy)return;message='';await post('begin',{mode})};
 function showSettings(){
  $('room-minutes').value=room()?.idle_minutes||15;$('room-noise').checked=room()?.ambient_activity||false;
  $('room-pin').value='';inputTarget='room-pin';settings.dataset.editing='pin';$('room-settings-message').textContent='';settings.showModal();render();
 }
 settingsButton.onclick=showSettings;
 $('room-settings-close').onclick=()=>{if(document.body.classList.contains('keyboard-open'))$('keyboard').click();$('room-pin').value='';settings.close()};
 let inputTarget='room-pin';
 for(const id of ['room-pin','room-minutes'])$(id).onfocus=()=>{inputTarget=id;settings.dataset.editing=id==='room-minutes'?'minutes':'pin'};
 $('room-pin-keys').onclick=()=>{$(inputTarget).focus();$('keyboard').click()};
 $('room-unlock').onclick=run(async()=>{await post('unlock',{pin:$('room-pin').value});$('room-pin').value='';if(document.body.classList.contains('keyboard-open'))$('keyboard').click();settings.close();await openSettings()});
 $('room-save').onclick=run(async()=>{
  await flush();
  await post('configure',{idle_minutes:Number($('room-minutes').value),ambient_activity:$('room-noise').checked,pin:$('room-pin').value});
  $('room-pin').value='';if(document.body.classList.contains('keyboard-open'))$('keyboard').click();settings.close();notice('Anmeldung & Geräteschutz gespeichert.');
 });
 async function cancel(){await post('cancel');panel.close();message=''}
 $('room-close').onclick=run(cancel);panel.oncancel=event=>{event.preventDefault();void cancel()};
 $('room-login').onclick=()=> $('account-shortcut').click();
 $('room-other').onclick=run(async()=>{await flush();await api('/api/room/finish',{});clearRoomDrafts();location.reload()});
 $('room-knowledge').onclick=run(async()=>{const selection=await window.studioLiveHome.refresh();window.openStudioKnowledge(selection)});
 $('room-start').onclick=run(async()=>{
  if(busy||!room()?.intent)return;
  busy=true;message='Start wird vorbereitet …';render();
  try{
   await flush();audio.pause();
   if(room().intent.mode==='talk'){
    const selection=await window.studioLiveHome.refresh();
    if(!selection.ids.length){window.openStudioKnowledge(selection);message='Wissen wählen, dann Gespräch starten.';return}
   }
   const result=await api('/api/room/start',{id:room().intent.id});
   panel.close();$('account-dialog').close();
   if(result.mode==='meeting'){pendingRecordingId=result.id;workspaceView()}
   else workspaceView('live-view');
   await poll();message='';
  }catch(error){message=error.message;}
  finally{busy=false;render()}
 });
 async function finish(){
  if(busy)return;
  const recording=Boolean(state.recording.id),live=Boolean(state.live.busy);
  const title=recording?'Aufnahme speichern & abschließen?':live?'Gespräch abschließen?':'Sitzung abschließen?';
  const message=recording?'Die Aufnahme wird gestoppt und mit deinen Notizen gespeichert. Die Verarbeitung kann danach weiterlaufen. Anschließend wirst du abgemeldet.':live?'Dein Gespräch wird beendet. Anschließend wirst du abgemeldet und das Gerät ist bereit für die nächste Person.':'Du wirst abgemeldet und das Gerät ist bereit für die nächste Person.';
  if(!await confirmAction({title,message,tone:'primary',accept:recording?'Speichern & abmelden':live?'Beenden & abmelden':'Abmelden',cancel:recording?'Zur Aufnahme':live?'Zum Gespräch':'Angemeldet bleiben',summary:{title:'Deine Aufnahmen bleiben bei dir',detail:'Gespeicherte Aufnahmen und Notizen sind deinem Brain-Konto zugeordnet.'}}))return;
  busy=true;
  try{
   await flush();audio.pause();
   let result=await api('/api/room/finish',{confirm:true});
   for(let count=0;result.finishing&&count<40;count++){
    await new Promise(resolve=>setTimeout(resolve,500));
    result=await api('/api/room/finish',{confirm:true});
   }
   if(result.finishing)throw Error('Das Gespräch wird noch beendet. Dein Konto bleibt angemeldet. Bitte erneut versuchen.');
   clearRoomDrafts();location.reload();
  }finally{busy=false}
 }
 end.onclick=run(finish);$('room-idle-finish').onclick=run(finish);
 $('room-stay').onclick=run(async()=>{await post('touch');idle.close()});
 function clearRoomDrafts(){
  for(const storage of [localStorage,sessionStorage]){
   for(const key of Object.keys(storage))if(key.startsWith('recorder:'+namespace+':'))storage.removeItem(key);
  }
 }
 window.resetRoomView=(next)=>{
  if(epoch&&epoch!==next.room?.epoch){clearRoomDrafts();audio.pause();clearTimeout(saveTimer);models.clear();selected=null;location.reload();return true}
  epoch=next.room?.epoch;return false;
 };
 // Only physical UI activity refreshes idle time, never state polling.
 for(const type of ['pointerdown','keydown'])document.addEventListener(type,()=>{
  if(!room()?.enabled||!room().signed_in||Date.now()-touched<10000)return;
  touched=Date.now();void api('/api/room/touch',{}).catch(()=>{});
 },true);
 document.addEventListener('click',event=>{
  if(!room()?.enabled)return;
  const id=event.target.closest('button')?.id;
  const mode=['start-recorder','record'].includes(id)&&!state.recording.id?'meeting':['start-live','live-start'].includes(id)?'talk':null;
  if(mode){event.preventDefault();event.stopImmediatePropagation();void window.beginRoom(mode).catch(e=>notice(e.message))}
  if(id==='settings-open'&&!room().operator){event.preventDefault();event.stopImmediatePropagation();showSettings()}
 },true);
 function render(){
  const r=room();if(!r){end.hidden=true;return}
  end.hidden=!r.enabled||!r.signed_in;
  micStatus.hidden=!r.signed_in||!r.ambient_activity||state.activity.busy;
  micHint.hidden=micStatus.hidden;micHint.textContent=['listening','testing','monitoring'].includes(r.ambient_state)?'Mikrofon: Geräuschpegel':'Pegelprüfung wartet';micHint.title='Nur lokale Pegelauswertung; kein Ton wird gespeichert oder übertragen.';
  micStatus.textContent=['listening','testing','monitoring'].includes(r.ambient_state)?'Mikrofon aktiv · nur Geräuschpegel':r.ambient_state==='error'?'Geräuscherkennung fehlt · Ruhefrist gilt':'Geräuscherkennung wartet · Ruhefrist gilt';
  const startFooter=$('start-status')?.parentElement;if(startFooter&&micStatus.parentElement!==startFooter)startFooter.append(micStatus);
  end.title=r.idle_suspended?r.idle_reason+' · keine automatische Abmeldung':'Sitzung beenden und Gerät für die nächste Person freigeben';
  // Put this beside the existing account control on every workspace.
  if(!end.hidden&&$('account-shortcut').parentElement!==document.body)$('account-shortcut').after(end);
  if(settings.open){
   for(const id of ['room-minutes-label','room-noise-choice','room-noise-note'])$(id).hidden=!r.operator;$('room-save').hidden=!r.operator;$('room-unlock').hidden=r.operator;
   $('room-settings-message').textContent=r.operator?(r.has_pin?'PIN leer lassen, um sie beizubehalten. Nach dem Beenden beginnt die volle Ruhefrist neu. Eine Minute vor der Abmeldung kannst du verlängern.':'Einmalig eine Betreiber-PIN festlegen. Bis dahin sind die Geräteeinstellungen noch offen. Die Anmeldung ist bereits erforderlich.'):'Zum Ändern der Geräteeinstellungen die Betreiber-PIN eingeben. Sie gibt keinen Zugriff auf Aufnahmen.';
  }
  if(!r.enabled){if(panel.open)panel.close();return}
  if(!state.recording.id&&!state.live.busy){
   $('start-recorder').disabled=!online||busy;$('start-live').disabled=!online||busy;
   $('record').disabled=!online||busy;
   if(!r.signed_in){$('hint-recorder').textContent='Anmelden und Aufnahme vorbereiten';$('hint-live').textContent='Anmelden und Gespräch vorbereiten';$('start-status').textContent='Bereit · Bitte mit Brain anmelden';}
   else $('hint-live').textContent='Gespräch am Pi vorbereiten';
  }
  if(r.intent){
   if(!panel.open)panel.showModal();
   const talk=r.intent.mode==='talk';
   $('room-title').textContent=talk?'Gespräch vorbereiten':'Meeting vorbereiten';
   $('room-person').textContent=r.signed_in?'Weiter als '+state.cdb.identity.name+' · '+brainEnvironment(state.cdb.config.server):'Melde dich mit deinem Brain-Konto an.';
   $('room-message').textContent=message||(r.signed_in?(talk?'Erst „Gespräch starten“ verbindet dein Mikrofon mit dem Brain.':'Erst „Aufnahme starten“ speichert die Meetingaufnahme.')+(r.ambient_activity?' Bis dahin wird nur der Geräuschpegel lokal ausgewertet.':''):'Ohne Internet ist keine neue Anmeldung möglich. Unter Betreiber → Netzwerk kannst du WLAN prüfen.');
   $('room-nfc').hidden=r.intent.source!=='nfc';
   $('room-start').hidden=!r.signed_in;$('room-login').hidden=r.signed_in;
   $('room-other').hidden=!r.signed_in;$('room-knowledge').hidden=!r.signed_in||!talk;
   $('room-start').textContent=talk?'Gespräch starten':'Aufnahme starten';$('room-start').disabled=busy||!online;
   if(!r.signed_in&&loginAttempt!==r.intent.id){loginAttempt=r.intent.id;setTimeout(()=>$('account-shortcut').click(),0)}
   if(r.signed_in&&$('account-dialog').open)$('account-dialog').close();
  }else if(panel.open){panel.close();message='';if(loginAttempt&&$('account-dialog').open)$('account-dialog').close();loginAttempt=null}
  const warning=r.signed_in&&!state.activity.busy&&!r.idle_suspended&&r.idle_remaining<=(r.warning_seconds||60);
  if(warning){$('room-idle-message').textContent='Du hast das Gerät eine Weile nicht verwendet. Abmeldung in '+r.idle_remaining+' Sekunden. Mit „Angemeldet bleiben“ beginnt die Ruhefrist neu. Deine Aufnahmen bleiben gespeichert.';if(!idle.open)idle.showModal()}
  else if(idle.open)idle.close();
 }
 const before=renderState;renderState=function(){before();render()};render();
})();
