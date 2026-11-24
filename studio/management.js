(() => {
 $('management-network').onclick=()=>{if(allowed('install'))location.href='/welcome.html?network=1'};
 $('setup-wizard').onclick=run(async()=>{if(allowed('install')){await flushAllDrafts();location.href='/welcome.html'}});
 let routed=false,restartPending=false,restarting=false,updateReload=false,shutdownPending=false,shutdownCommand=null,powerErrorSeen=null;
 function powerBlocked(){return !online||Boolean(state?.recording?.id)||Boolean(state?.live?.busy)||Boolean(state?.activity?.busy)||Boolean(state?.management?.maintenance)||Boolean(state?.jobs?.some(j=>['queued','importing','transcribing','summarizing'].includes(j.state)))||Boolean(state?.timers?.items?.some(i=>['scheduled','due'].includes(i.state)))||Boolean(state?.cdb?.publications?.some(j=>['queued','accepted','sending'].includes(j.state)))||(typeof audio!=='undefined'&&!audio.paused)}
 function showShutdown(failed=false){
  const dialog=$('shutdown-status');
  $('shutdown-heading').textContent=failed?'Herunterfahren nicht abgeschlossen':'Pi fährt herunter …';
  $('shutdown-description').textContent=failed?'Der Pi ist weiterhin erreichbar. Bitte den Strom angeschlossen lassen und das Herunterfahren erneut versuchen.':'Bitte den Strom angeschlossen lassen, bis der Pi vollständig heruntergefahren ist.';
  dialog.querySelector('.dialog-actions').hidden=!failed;
  if(!dialog.open)dialog.showModal();
 }
 $('shutdown-status').oncancel=event=>{if(shutdownPending||shutdownCommand)event.preventDefault()};
 $('shutdown-dismiss').onclick=()=> $('shutdown-status').close();
 $('management-shutdown').onclick=run(async()=>{
  if(shutdownPending||shutdownCommand||restartPending||restarting||powerBlocked())return;
  shutdownPending=true;render();
  try{
   if(!await confirmAction({title:'Pi vollständig herunterfahren?',message:'Der gesamte Raspberry Pi wird ausgeschaltet. Deine Aufnahmen und Einstellungen bleiben erhalten. Trenne den Strom erst, wenn der Pi vollständig heruntergefahren ist.',accept:'Jetzt herunterfahren',cancel:'Eingeschaltet lassen',acceptDetail:'Pi sicher ausschalten.',cancelDetail:'Zurück zur Geräteverwaltung.',acceptIcon:'stop',cancelIcon:'monitor'}))return;
   await flushAllDrafts();
   if(powerBlocked())throw Error('Das Gerät ist inzwischen beschäftigt. Bitte den laufenden Vorgang zuerst beenden.');
   const result=await api('/api/device/shutdown',{confirm:true});
   if(!result.scheduled)throw Error('Herunterfahren wurde nicht bestätigt. Bitte erneut versuchen.');
   shutdownCommand=result.command;showShutdown();
  }finally{shutdownPending=false;render()}
 });
 $('management-reload').onclick=run(async()=>{await flushAllDrafts();if(state?.recording?.id||state?.live?.busy)throw Error('Aufnahme oder Gespräch zuerst beenden.');location.reload()});
 $('management-restart').onclick=run(async()=>{
  if(restartPending||restarting||shutdownPending||shutdownCommand||powerBlocked())return;
  restartPending=true;render();
  try{
   if(!await confirmAction({title:'Pi neu starten?',message:'Der gesamte Raspberry Pi startet neu. Deine Aufnahmen und Einstellungen bleiben erhalten.',accept:'Jetzt neu starten',cancel:'Weiterarbeiten',acceptDetail:'Pi beenden und wieder starten.',cancelDetail:'Zurück zur Geräteverwaltung.',acceptIcon:'arrow-clockwise',cancelIcon:'monitor'}))return;
   await flushAllDrafts();
   if(powerBlocked())throw Error('Das Gerät ist inzwischen beschäftigt. Bitte den laufenden Vorgang zuerst beenden.');
   await api('/api/device/restart',{confirm:true});restarting=true;
   $('management-message').textContent='Pi startet neu. Bitte etwa eine Minute warten.';
  }finally{restartPending=false;render()}
 });
 const loadedVersion=document.querySelector('meta[name=studio-ui-version]')?.content;
 function reloadUpdatedVersion(){
  if(updateReload)return;
  const target=state.version,key='cdb-ui-reloaded-version';
  try{if(sessionStorage.getItem(key)===target)return;}catch(_){return;}
  updateReload=true;
  flushAllDrafts().then(()=>{
   if(state?.activity?.busy||state?.recording?.id||state?.live?.busy||state?.management?.maintenance){updateReload=false;return;}
   // Remember across page reloads, not just during this JavaScript instance.
   sessionStorage.setItem(key,target);location.reload();
  }).catch(()=>{updateReload=false;notice('Oberfläche wurde aktualisiert. Entwurf bitte zuerst sichern und danach neu laden.');});
 }
 $('management-diagnostics').onclick=()=>showSettingsDetail('models-page');
 function render(){if(state&&!routed){routed=true;if(state.first_start?.required){location.replace('/welcome.html');return}const setup=new URLSearchParams(location.search).get('setup');if(['audio','recorder'].includes(setup)){openSettings().then(()=>showSettingsDetail(setup==='audio'?'audio-page':'setup-page'));history.replaceState(null,'','/')}}$('management-network').disabled=$('setup-wizard').disabled=!allowed('install');
 const power=state?.management?.power||{};
 if(['scheduled','requested'].includes(power.state)){shutdownCommand=power.command;showShutdown()}
 else if(power.state==='failed'&&power.command!==powerErrorSeen){powerErrorSeen=power.command;shutdownCommand=null;showShutdown(true)}
 const restartBlocked=powerBlocked();
 $('management-restart').disabled=restartPending||restarting||restartBlocked||shutdownPending||Boolean(shutdownCommand);
 $('management-shutdown').disabled=restartPending||restarting||restartBlocked||shutdownPending||Boolean(shutdownCommand);
 $('management-restart').title=$('management-shutdown').title=restartBlocked?'Aufnahme, Gespräch, Wiedergabe, Verarbeitung oder Timer zuerst beenden.':'';
 $('management-reload').disabled=Boolean(state?.recording?.id)||Boolean(state?.live?.busy);
 const m=state?.management||{},connected=m.state==='connected',paired=connected||m.state==='pairing'||m.state==='offline'||m.state==='hardware-changed';if(state?.version&&loadedVersion&&state.version!==loadedVersion&&!state.activity?.busy&&!m.maintenance){reloadUpdatedVersion();}
 $('management-state').textContent=m.maintenance?'Wartung läuft':m.message||'Noch nicht verbunden';$('management-name').textContent=m.name||'';$('management-server').textContent=m.server||'';$('management-code').disabled=paired||m.maintenance;$('management-pair').disabled=!online||paired||Boolean(state?.activity?.busy);}
 $('management-pair').onclick=run(async()=>{await api('/api/management/enroll',{code:$('management-code').value});$('management-code').value='';$('management-message').textContent='Kopplung wird geprüft. Das kann bis zu 30 Sekunden dauern.';await poll()});
 const previous=renderState;renderState=function(){previous();render()};render();
})();
