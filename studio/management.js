(() => {
 $('management-network').onclick=()=>{if(allowed('install'))location.href='/welcome.html?network=1'};
 let routed=false,restartConfirm=false,restarting=false;
 $('management-reload').onclick=run(async()=>{await flush();location.reload()});
 $('management-restart').onclick=run(async()=>{
  if(restarting)return;
  if(!restartConfirm){restartConfirm=true;$('management-restart').textContent='Jetzt neu starten';$('management-message').textContent='Der Pi startet neu. Deine Einstellungen und Aufnahmen bleiben erhalten. Zum Bestätigen erneut tippen.';return}
  await flush();await api('/api/device/restart',{confirm:true});restarting=true;
  $('management-message').textContent='Pi startet neu. Bitte etwa eine Minute warten.';render();
 });
 const loadedVersion=document.querySelector('meta[name=studio-ui-version]')?.content;
 $('management-diagnostics').onclick=()=>showSettingsDetail('models-page');
 function render(){if(state&&!routed){routed=true;if(state.first_start?.required){location.replace('/welcome.html');return}if(new URLSearchParams(location.search).get('setup')==='audio'){openSettings().then(()=>showSettingsDetail('audio-page'));history.replaceState(null,'','/')}}$('management-network').disabled=!allowed('install');
 const restartBlocked=!online||Boolean(state?.activity?.busy)||Boolean(state?.jobs?.some(j=>['queued','importing','transcribing','summarizing'].includes(j.state)))||Boolean(state?.timers?.items?.some(i=>['scheduled','due'].includes(i.state)))||Boolean(state?.cdb?.publications?.some(j=>['queued','accepted','sending'].includes(j.state)));
 $('management-restart').disabled=restarting||restartBlocked;
 $('management-reload').disabled=Boolean(state?.recording?.id)||Boolean(state?.live?.busy);
 if(!restarting&&(restartBlocked||$('management-page').hidden)){restartConfirm=false;$('management-restart').textContent='Pi neu starten'}
 const m=state?.management||{},connected=m.state==='connected',paired=connected||m.state==='pairing'||m.state==='offline'||m.state==='hardware-changed';if(state?.version&&loadedVersion&&state.version!==loadedVersion&&!state.activity?.busy&&!m.maintenance){location.reload();return;}
 $('management-state').textContent=m.maintenance?'Wartung läuft':m.message||'Noch nicht verbunden';$('management-name').textContent=m.name||'';$('management-server').textContent=m.server||'';$('management-code').disabled=paired||m.maintenance;$('management-pair').disabled=!online||paired||Boolean(state?.activity?.busy);}
 $('management-pair').onclick=run(async()=>{await api('/api/management/enroll',{code:$('management-code').value});$('management-code').value='';$('management-message').textContent='Kopplung wird geprüft. Das kann bis zu 30 Sekunden dauern.';await poll()});
 const previous=renderState;renderState=function(){previous();render()};render();
})();
