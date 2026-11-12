'use strict';
(()=>{
 const $=id=>document.getElementById(id);
 const order=['welcome','network','pair','models','brain','audio'];
 const titles={welcome:'Willkommen bei deinem Brain',network:'Netzwerk verbinden',credentials:'WLAN-Schlüssel eingeben',pair:'Geräteverwaltung',models:'Lokale Modelle',brain:'Brain-Anmeldung',audio:'Audio einrichten'};
 const recommended={whisper:{group:'asr',id:'medium'},ollama:{group:'llm',id:'qwen3:4b-instruct'}};
 const networkOnly=new URLSearchParams(location.search).has('network');
 let step='welcome',snapshot=null,networks=[],network=null,page=0,working=false,polling=false,loaded=false;
 let networkListKey='',networkRequest='',handledOperation='',catalog=null,catalogRevision='',catalogError='';
 async function api(path,body){
  const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-CSRF-Token':snapshot.csrf}:{},body:body?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(30000)});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'Verbindung fehlgeschlagen.');
  return data;
 }
 function message(text){$('message').textContent=text}
 function run(fn){return async(event)=>{
  if(working)return;
  const value=event?.target?.value;
  working=true;message('');render();
  try{await fn(value)}catch(e){message(e.message)}finally{try{await poll(true)}finally{working=false;render()}}
 }}
 function connected(){return (network?.devices||[]).filter(d=>d.state==='connected'||d.state==='connected (externally)')}
 function renderNetwork(){
  const links=connected(),lan=links.some(d=>d.type==='ethernet'),canWifi=network?.wifi_setup!==false;
  $('link-state').textContent=network?(lan?'LAN verbunden':links.length?'WLAN verbunden':'Kein Netzwerk verbunden')+' · '+({full:'Internetzugang bestätigt',portal:'Anmeldeseite erforderlich',limited:'Internetzugang eingeschränkt',none:'Kein Internet'}[network.connectivity]||'Internetzugang ungeprüft'):'Verbindung noch nicht geprüft';
  $('network-help').textContent=!canWifi?'Für WLAN-Änderungen fehlt auf diesem Gerät der Einrichtungsdienst.':links.length?'Du kannst mit der vorhandenen Verbindung weitergehen oder ein anderes WLAN wählen.':'Wähle ein WLAN aus der Liste oder gib einen Netzwerknamen ein.';
  const locked=working||!snapshot?.allowed;
  $('other-network').disabled=locked||!canWifi;
  $('scan').disabled=locked;
  $('scan').textContent=network&&canWifi?'WLAN suchen':'Verbindung prüfen';
  const host=$('networks');
  page=Math.max(0,Math.min(page,Math.ceil(networks.length/3)-1));
  const key=JSON.stringify([networks,page,locked,canWifi]);
  if(networkListKey===key)return;
  networkListKey=key;host.replaceChildren();
  for(const item of networks.slice(page*3,page*3+3)){
   const b=document.createElement('button'),name=document.createElement('span'),strength=document.createElement('small');
   name.textContent=item.ssid;strength.textContent=item.supported?item.signal+' %':'Separat einrichten';
   b.append(name,strength);b.disabled=!item.supported||locked||!canWifi;
   b.onclick=()=>credentials(item.ssid,item.security);host.append(b);
  }
  host.hidden=!networks.length;
  $('page-label').textContent='Seite '+(page+1)+' / '+Math.max(1,Math.ceil(networks.length/3));
  for(const id of ['page-prev','page-label','page-next'])$(id).hidden=networks.length<=3;
  $('page-prev').disabled=page===0;$('page-next').disabled=(page+1)*3>=networks.length;
 }
 function model(backend){const {group,id}=recommended[backend];return catalog?.[group]?.find(m=>m.id===id)}
 function renderModels(){
  const d=snapshot?.installation,view=modelDownload(d,catalog);
  for(const backend of Object.keys(recommended)){
   const entry=model(backend),runtime=backend==='ollama'?catalog?.ollama:catalog?.whisper_runtime;
   $(backend+'-status').textContent=entry?(entry.installed?'Installiert':queueFileSize(entry.bytes)+' Download')+(runtime?'':' · Laufzeit fehlt'):catalogError||'Modellkatalog wird geladen …';
   $(backend+'-install').hidden=Boolean(entry?.installed);
   $(backend+'-install').disabled=working||!snapshot?.allowed||!entry||(backend==='ollama'&&!runtime);
  }
  $('transfer').hidden=!view;
  if(view){
   $('model-progress-label').textContent=view.model+' · '+view.phase;
   $('model-progress').hidden=d.state!=='running';
   if(view.percent==null)$('model-progress').removeAttribute('value');else $('model-progress').value=view.percent;
   $('model-amount').textContent=[view.percent==null?'':view.percent+' %',view.amount].filter(Boolean).join(' · ');
  }
 }
 function renderBrain(){
  const brain=snapshot?.brain,pending=brain?.login.state==='pending',signed=brain?.signed_in;
  if(brain)$('brain-server').value=brain.server;
  $('brain-server').disabled=working||!snapshot?.allowed||signed||pending;
  $('brain-status').textContent=signed?'Brain-Konto verbunden.':pending?'QR-Code am Handy scannen und den Gerätecode eingeben.':brain?.login.message||'Noch nicht angemeldet.';
  $('brain-login').hidden=signed||pending;$('brain-login').disabled=working||!snapshot?.allowed;
  $('brain-cancel').hidden=!pending;$('brain-cancel').disabled=working||!snapshot;
  $('brain-device').hidden=!pending;
  $('brain-code').textContent=pending?brain.login.code:'';
  $('brain-url').textContent=pending?brain.login.url:'';
  if(pending){
   const file=brain.login.url==='https://login.microsoft.com/device'?'microsoft-device':'microsoft-devicelogin';
   const url='/assets/'+file+'.png';if($('brain-qr').getAttribute('src')!==url)$('brain-qr').src=url;
  }
 }
 function render(){
  for(const el of document.querySelectorAll('[data-step]'))el.hidden=el.dataset.step!==step;
  const index=order.indexOf(step==='credentials'?'network':step);
  $('heading').textContent=titles[step];
  $('position').textContent=index>0&&!networkOnly?'Einrichtung · Schritt '+index+' von 5':'Recorder Studio';
  const locked=working||!snapshot?.allowed,pair=snapshot?.management||{};
  const pendingLogin=step==='brain'&&snapshot?.brain?.login.state==='pending';
  $('back').hidden=step==='welcome'&&snapshot?.required!==false;
  $('back').disabled=working||snapshot?.busy||pendingLogin||(!networkOnly&&step!=='welcome'&&!snapshot?.allowed);
  $('back').textContent=(networkOnly&&step!=='credentials')||step==='welcome'?'Zur App':'Zurück';
  $('connect').hidden=step!=='credentials';$('connect').disabled=locked;
  $('pair').hidden=step!=='pair'||pair.state==='connected'||$('offline').checked;
  $('pair').disabled=locked||pair.state==='pairing';
  $('next').hidden=step==='credentials'||!$('pair').hidden||(networkOnly&&step==='network');
  $('next').disabled=locked||pendingLogin;
  $('next').textContent=step==='welcome'?'Einrichtung starten':step==='audio'?'Recorder-Einrichtung öffnen':
   step==='models'&&!(model('whisper')?.installed&&model('ollama')?.installed)?'Modelle später ergänzen':
   step==='brain'&&!snapshot?.brain?.signed_in?'Anmeldung überspringen':
   step==='network'&&network&&!connected().length?'Offline weiter':'Weiter';
  $('pair-status').textContent=pair.message||'Noch nicht verbunden';
  $('pair-title').textContent=pair.state==='connected'?'Gerät ist gekoppelt':'Gerät koppeln';
  $('code').disabled=locked||['pairing','connected'].includes(pair.state);
  $('offline').disabled=locked||pair.state==='connected';
  if(pair.state==='connected'){$('pair-name').textContent=pair.name||'Deine Organisation';$('pair-server').textContent=pair.server||''}
  if(!working&&snapshot&&!snapshot.allowed&&snapshot.reason&&!snapshot.busy&&snapshot.installation?.state!=='running')message(snapshot.reason);
  if(step==='network')renderNetwork();
  if(step==='models')renderModels();
  if(step==='brain')renderBrain();
 }
 function credentials(ssid,security){
  $('ssid').value=ssid;$('security').value=security;$('password').value='';
  $('hidden-network').checked=false;$('show-password').checked=false;$('password').type='password';
  step='credentials';message('');render();
 }
 async function poll(afterAction=false){
  if(polling||(working&&!afterAction))return;
  polling=true;
  try{
   snapshot=await api('/api/onboarding');
   if(!loaded){
    loaded=true;step=networkOnly?'network':order.includes(snapshot.step)?snapshot.step:'welcome';
    $('offline').checked=snapshot.offline;
    if(step==='network')networkRequest='status';
   }
   const op=snapshot.operation;
   if(['network','credentials'].includes(step)){
    if(op.state==='done'&&op.id!==handledOperation){
     handledOperation=op.id;network=op.network;
     if(network.scanned)networks=network.networks;
     if(op.action==='connect'&&step==='credentials'){step='network';message('WLAN verbunden.')}
     if(op.action==='status'&&!connected().length&&network.wifi_setup!==false&&!networkRequest)networkRequest='scan';
    }
    if(op.state==='error')message(op.message);
    if(networkRequest&&snapshot.allowed&&!snapshot.busy){
     const action=networkRequest;networkRequest='';await api('/api/onboarding/network',{action});
     snapshot.allowed=false;
    }
   }
   if(step==='models'){
    const d=snapshot.installation,revision=[d.state,d.backend,d.model].join('|');
    if((catalogRevision!==revision&&d.state!=='running')||(!catalog&&!catalogError)){
     try{catalog=(await api('/api/setup')).catalog;catalogError='';catalogRevision=revision}
     catch(e){catalogError='Modellkatalog nicht erreichbar.';catalog=null}
    }
    if(d.state==='running')catalogRevision='running';
   }
   render();
  }catch(e){message('Einrichtung konnte nicht aktualisiert werden. '+e.message);snapshot=null;render()}
  finally{polling=false}
 }
 async function go(next){
  await api('/api/onboarding/step',{step:next,offline:$('offline').checked});
  step=next;message('');
  if(next==='network'){networkRequest='status';network=null;networks=[]}
  if(next==='models'){catalogRevision='';catalogError=''}
  render();
 }
 $('next').onclick=run(async()=>{
  if(step==='audio'){
   await api('/api/onboarding/step',{step:'done',offline:$('offline').checked});
   location.href='/?setup=recorder';return;
  }
  await go(order[order.indexOf(step)+1]);
 });
 $('back').onclick=run(async()=>{
  if(step==='credentials'){$('password').value='';step='network';return}
  if(networkOnly||step==='welcome'){location.href='/';return}
  await go(order[order.indexOf(step)-1]);
 });
 $('other-network').onclick=()=>credentials('','wpa2');
 $('scan').onclick=run(async()=>{networkRequest=network&&network.wifi_setup!==false?'scan':'status'});
 $('connect').onclick=run(async()=>{
  const password=$('password').value;$('password').value='';
  await api('/api/onboarding/network',{action:'connect',ssid:$('ssid').value,password,security:$('security').value,hidden:$('hidden-network').checked});
 });
 $('pair').onclick=run(async()=>{await api('/api/management/enroll',{code:$('code').value});$('code').value='';message('Kopplung wird geprüft.')});
 for(const [backend,entry] of Object.entries(recommended)){
  $(backend+'-install').onclick=run(async()=>{await api('/api/models/install',{backend,model:entry.id});catalogRevision=''});
 }
 $('brain-server').onchange=run(server=>api('/api/cdb/config',{server}));
 $('brain-login').onclick=run(()=>api('/api/cdb/login',{}));
 $('brain-cancel').onclick=run(()=>api('/api/cdb/login/cancel',{}));
 $('offline').onchange=render;$('show-password').onchange=()=>{$('password').type=$('show-password').checked?'text':'password'};
 $('page-prev').onclick=()=>{page--;renderNetwork()};$('page-next').onclick=()=>{page++;renderNetwork()};
 poll();setInterval(poll,2000);
})();
