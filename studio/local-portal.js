/* Local portal setup; all personal control grants are approved on the Pi. */
(()=>{
 let busy=false;
 function render(){const p=state?.portal;if(!p)return;
  $('portal-url').textContent=p.url;$('portal-ip').textContent=p.ip_urls?.length?'Alternativ: '+p.ip_urls.join(' · '):'';
  $('portal-state').textContent=p.error||(!p.available?'Hilfezugang noch nicht gestartet.':p.enabled?'Hilfe verfügbar · verschlüsselte Fernbedienung eingeschaltet.':'Hilfe verfügbar · Fernbedienung ausgeschaltet.');
  $('portal-controllers').textContent=p.controllers.length?'Freigegeben: '+p.controllers.join(', '):'Noch kein Browser freigegeben.';
  $('portal-fingerprint').textContent=p.fingerprint||'Wird beim Einschalten der Fernbedienung auf diesem Pi erstellt.';
  $('portal-toggle').textContent=p.enabled?'Fernbedienung ausschalten':'Fernbedienung einschalten';
  $('portal-toggle').disabled=busy||!online||!allowed('configure')||state.room?.operator===false;
  $('portal-approve').disabled=busy||!online||!p.enabled||!state.room?.signed_in||!allowed('configure');
  $('portal-revoke').disabled=busy||!online||!p.enabled;
  $('portal-read').disabled=busy||!online||!allowed('configure');
 }
 async function change(path,body={}){if(busy)return;busy=true;render();try{await api('/api/portal/'+path,body);$('portal-message').textContent=path==='approve'?'Browser freigegeben. Du kannst ihn jetzt bedienen.':path==='revoke'?'Alle Browser entkoppelt. Laufende Vorgänge bleiben bestehen.':'Zugang aktualisiert.';if(path==='approve')$('portal-code').value='';await poll()}catch(e){$('portal-message').textContent=e.message}finally{busy=false;render()}}
 $('portal-toggle').onclick=()=>change(state.portal.enabled?'disable':'enable');$('portal-revoke').onclick=()=>change('revoke');$('portal-approve').onclick=()=>change('approve',{code:$('portal-code').value.trim()});
 $('portal-read').onclick=run(async()=>{if(!allowed('configure'))return;await flushAllDrafts();if(!allowed('configure'))return;location.href='/help/index.html'});
 const previous=renderState;renderState=function(){previous();render()};render();
})();
