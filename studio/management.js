(() => {
 const loadedVersion=document.querySelector('meta[name=studio-ui-version]')?.content;
 $('management-diagnostics').onclick=()=>showSettingsDetail('models-page');
 function render(){const m=state?.management||{},connected=m.state==='connected',paired=connected||m.state==='offline'||m.state==='hardware-changed';if(state?.version&&loadedVersion&&state.version!==loadedVersion&&!state.activity?.busy&&!m.maintenance){location.reload();return;}
 $('management-state').textContent=m.maintenance?'Wartung läuft':m.message||'Noch nicht verbunden';$('management-name').textContent=m.name||'';$('management-server').textContent=m.server||'';$('management-code').disabled=paired||m.maintenance;$('management-pair').disabled=!online||paired||Boolean(state?.activity?.busy);}
 $('management-pair').onclick=run(async()=>{await api('/api/management/enroll',{code:$('management-code').value});$('management-code').value='';$('management-message').textContent='Kopplung wird geprüft. Das kann bis zu 30 Sekunden dauern.';await poll()});
 const previous=renderState;renderState=function(){previous();render()};render();
})();
