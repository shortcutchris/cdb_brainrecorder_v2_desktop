/* Voice One: browser WebRTC audio, authenticated Python broker, one audio owner. */
(() => {
 const rail = document.createElement('button'); rail.id='live-open';rail.className='rail-button';rail.setAttribute('aria-label','Live-Gespräch');rail.title='Live-Gespräch';
 rail.innerHTML='<img src="/assets/users.svg" alt=""><span>Live-Gespräch</span>';
 $('settings-open').before(rail);
 const view=document.createElement('dialog');view.id='live-view';view.className='workspace-view';view.setAttribute('aria-labelledby','live-heading');view.setAttribute('role','region');
 view.innerHTML=`<div class="dialog-heading"><h2 id="live-heading">Live-Gespräch</h2><span id="live-status" role="status">Bereiche wählen</span></div>
 <section class="live-content"><div id="live-setup"><h3>Mit deinem Wissen sprechen</h3><p>Wähle eine oder mehrere Knowledge Areas. Voice One nutzt die ausgewählten Bereiche als Wissensgrundlage.</p><div class="live-scope-heading"><strong>Knowledge Areas</strong><span id="live-selection-count"></span></div><div id="live-areas"></div><nav id="live-area-pages" class="direct-pages" aria-label="Bereichsseiten"></nav><div class="live-audio-choice"><label for="live-microphone">Gespräch über Mikrofon und Lautsprecher dieses Geräts</label><div><select id="live-microphone" aria-label="Mikrofon für Live-Gespräch"><option value="">Mikrofon zuerst freigeben</option></select><button id="live-devices">Mikrofon wählen</button></div></div></div>
 <div id="live-chat" hidden><div class="live-scope-summary" id="live-scope-summary"></div><div id="live-messages" role="log" aria-live="polite"></div><nav id="live-chat-pages" class="direct-pages" aria-label="Gesprächsseiten"></nav></div><p id="live-notice" role="status"></p></section>
 <footer class="live-footer"><button id="live-refresh">Bereiche laden</button><button id="live-new" hidden>Neues Gespräch</button><button id="live-mute" hidden aria-pressed="false">Mikro stumm</button><button id="live-start" class="primary">Gespräch starten</button><button id="live-end" hidden>Gespräch beenden</button></footer>`;
 document.body.append(view);
 const remoteAudio=document.createElement('audio');remoteAudio.autoplay=true;remoteAudio.id='live-remote-audio';view.append(remoteAudio);
 let setup=null,chosen=new Set(),areaPage=0,chatPage=null,lease=null,peer=null,microphone=null,heartbeat=null,statusTimer=null,starting=false,ending=false,deviceGranted=false,loadedOwner=null,generation=0;
 const messages={connecting:'Verbindet …',listening:'Hört zu',thinking:'Denkt nach …',speaking:'Spricht',reconnecting:'Verbindung wird erneuert …',closing:'Gespräch wird beendet …',ended:'Gespräch beendet',error:'Nicht verbunden',idle:'Bereiche wählen'};
 const busy=()=>Boolean(state?.live?.busy)||starting||ending;
 const post=(path,body={})=>api('/api/live/'+path,body);
 function note(message){$('live-notice').textContent=message||'';}
 function stopAudio(){clearInterval(heartbeat);heartbeat=null;clearInterval(statusTimer);statusTimer=null;microphone?.getTracks().forEach(t=>t.stop());microphone=null;peer?.close();peer=null;remoteAudio.pause();remoteAudio.srcObject=null;}
 async function finish(){generation++;if(ending)return;ending=true;stopAudio();const old=lease;lease=null;try{if(old)await post('end',{lease:old});else if(state?.live?.busy)await post('end',{});}finally{starting=false;ending=false;await poll();renderLive();}}
 async function load(){note('Bereiche werden geladen …');try{setup=await api('/api/live/setup');const available=new Set(setup.areas.map(a=>a.id));chosen=new Set([...chosen].filter(id=>available.has(id)));if(!chosen.size&&setup.default_area&&available.has(setup.default_area.id))chosen.add(setup.default_area.id);areaPage=0;note(setup.enabled?'':'Voice One ist in dieser Brain-Umgebung nicht freigeschaltet.');}catch(e){setup=null;note(e.message)}renderLive();}
 const baseWorkspace=workspaceView;
 workspaceView=function(id=null){
  if(busy()&&id!=='live-view')throw new Error('Gespräch läuft. Bitte zuerst beenden.');
  if(view.open&&id!=='live-view')view.close();baseWorkspace(id);
  rail.classList.toggle('active',id==='live-view');rail.setAttribute('aria-current',id==='live-view'?'page':'false');
 };
 rail.onclick=run(async()=>{if(state?.recording.id)throw new Error('Aufnahme läuft. Bitte zuerst stoppen.');await leaveDraft();audio.pause();workspaceView('live-view');renderLive();if(!busy())await load()});
 function drawAreas(){const box=$('live-areas');box.replaceChildren();const areas=setup?.areas||[];areaPage=Math.min(areaPage,Math.max(0,Math.ceil(areas.length/4)-1));for(const area of areas.slice(areaPage*4,areaPage*4+4)){const b=document.createElement('button');b.className='live-area';b.textContent=area.label||area.name;b.setAttribute('aria-pressed',String(chosen.has(area.id)));b.onclick=()=>{if(chosen.has(area.id))chosen.delete(area.id);else if(chosen.size<(setup?.max_areas||8))chosen.add(area.id);else note('Maximal '+setup.max_areas+' Bereiche wählen.');renderLive()};box.append(b)}$('live-selection-count').textContent=chosen.size+' ausgewählt';drawPageNumbers($('live-area-pages'),Math.max(1,Math.ceil(areas.length/4)),areaPage,i=>{areaPage=i;drawAreas()});}
 function historyPages(history){const pages=[];let page=[];for(const row of history||[]){const text=String(row.text||'');for(const chunk of text.match(/(?:[^\n]{1,90}(?:\n|$)?|\n)/g)||[]){if(!page.length||page.at(-1).role!==row.role||page.at(-1).lines>=3)page.push({role:row.role,text:'',lines:0});page.at(-1).text+=chunk;page.at(-1).lines++;if(page.length===2&&page.at(-1).lines===3){pages.push(page);page=[];}}if(page.length===2){pages.push(page);page=[];}}if(page.length)pages.push(page);return pages.length?pages:[[]]}
 function drawHistory(live){const pages=historyPages(live.history);const page=chatPage===null?pages.length-1:Math.min(chatPage,pages.length-1);$('live-messages').replaceChildren();for(const row of pages[page]){const bubble=document.createElement('article');bubble.className='live-message '+row.role;const who=document.createElement('strong');who.textContent=row.role==='user'?'Du':'Voice One';const p=document.createElement('p');p.textContent=row.text;bubble.append(who,p);$('live-messages').append(bubble)}if(!pages[page].length)$('live-messages').textContent=live.busy?(lease?'Du kannst gleich mit Voice One sprechen.':'Gespräch auf einem anderen Gerät aktiv.'):'Noch kein Gesprächsverlauf.';drawPageNumbers($('live-chat-pages'),pages.length,page,i=>{chatPage=i===pages.length-1?null:i;drawHistory(live)});$('live-scope-summary').textContent=(live.areas||[]).map(a=>a.label||a.name).join(' · ');}
 function renderLive(){const live=state?.live||{state:'idle',history:[]};const active=busy(),history=Boolean(live.history?.length),recording=Boolean(state?.recording.id);rail.disabled=recording;const owner=JSON.stringify(state?.cdb?.identity||null);if(owner!==loadedOwner&&!active){loadedOwner=owner;setup=null;chosen.clear();} $('live-status').textContent=messages[live.state]||'Bereiche wählen';$('live-setup').hidden=active||history;$('live-chat').hidden=!active&&!history;$('live-start').hidden=active||history;$('live-end').hidden=!active;$('live-end').disabled=ending||live.state==='closing';$('live-mute').hidden=!active;$('live-mute').disabled=!lease||!microphone||ending;$('live-mute').textContent=live.muted?'Mikro einschalten':'Mikro stumm';$('live-mute').setAttribute('aria-pressed',String(Boolean(live.muted)));$('live-refresh').hidden=active||history;$('live-new').hidden=active||!history;$('live-start').disabled=!online||recording||!setup?.enabled||!chosen.size||!deviceGranted||!$('live-microphone').value;$('live-devices').disabled=active||recording||!online;drawAreas();drawHistory(live);if(live.error)note(live.error);$('home').disabled=active;for(const id of ['library-open','settings-open','queue-toggle'])if(active)$(id).disabled=true;if(active){$('record').disabled=true;}if(lease&&!live.busy&&!starting&&!ending){stopAudio();lease=null;}}
 const previousRender=renderState;renderState=function(){previousRender();renderLive()};
 $('live-refresh').onclick=run(load);
 $('live-new').onclick=run(async()=>{await post('clear');chatPage=null;await poll();await load()});
 $('live-devices').onclick=run(async()=>{
  if(!navigator.mediaDevices?.getUserMedia)throw new Error('Für Live ist ein sicherer Browser am Pi oder über localhost nötig.');
  if(!chosen.size)throw new Error('Bitte zuerst mindestens eine Knowledge Area wählen.');
  const runId=++generation;starting=true;renderLive();let stream=null;
  try{
   const reserved=await post('reserve',{area_ids:[...chosen]});
   if(runId!==generation){await post('end',{lease:reserved.lease});return;}
   lease=reserved.lease;heartbeat=setInterval(()=>{if(runId===generation&&lease)post('pulse',{lease}).catch(()=>{if(runId===generation)finish().catch(()=>{})})},5000);
   stream=await navigator.mediaDevices.getUserMedia({audio:true});
   if(runId!==generation){stream.getTracks().forEach(t=>t.stop());return;}
   const devices=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='audioinput');
   if(runId!==generation)return;
   $('live-microphone').replaceChildren();const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Mikrofon auswählen';$('live-microphone').append(placeholder);
   for(const d of devices){const o=document.createElement('option');o.value=d.deviceId;o.textContent=d.label||'Mikrofon';$('live-microphone').append(o)}
   const preferred=devices.find(d=>/respeaker|xvf3800/i.test(d.label));if(preferred)$('live-microphone').value=preferred.deviceId;
   deviceGranted=true;note(preferred?'ReSpeaker für dieses Gespräch ausgewählt.':'Bitte das Mikrofon dieses Browsers ausdrücklich auswählen.');
  }finally{stream?.getTracks().forEach(t=>t.stop());if(runId===generation)await finish();}renderLive();
 });
 $('live-microphone').onchange=renderLive;
 $('live-start').onclick=run(async()=>{
  if(starting||busy())return;const runId=++generation;starting=true;chatPage=null;note('Audioverbindung wird vorbereitet …');renderLive();
  try{
   const reserved=await post('reserve',{area_ids:[...chosen]});if(runId!==generation){await post('end',{lease:reserved.lease});return;}lease=reserved.lease;
   heartbeat=setInterval(()=>{if(runId===generation&&lease)post('pulse',{lease}).catch(()=>{if(runId===generation)finish().catch(()=>{})})},5000);
   const stream=await navigator.mediaDevices.getUserMedia({audio:{deviceId:{exact:$('live-microphone').value},echoCancellation:true,noiseSuppression:true},video:false});
   if(runId!==generation){stream.getTracks().forEach(t=>t.stop());return;}microphone=stream;
   peer=new RTCPeerConnection();peer.addTransceiver(microphone.getAudioTracks()[0],{direction:'sendrecv'});peer.createDataChannel('oai-events');
   peer.ontrack=e=>{remoteAudio.srcObject=e.streams[0]||new MediaStream([e.track]);remoteAudio.play().catch(()=>note('Audioausgabe blockiert. Gespräch beenden und erneut starten.'));};
   peer.onconnectionstatechange=()=>{if(peer&&['failed','closed'].includes(peer.connectionState))finish().catch(()=>{});};
   const offer=await peer.createOffer();if(runId!==generation||!peer)return;await peer.setLocalDescription(offer);await new Promise(resolve=>setTimeout(resolve,1500));
   if(runId!==generation||!peer||!lease)return;
   await post('start',{lease,sdp:peer.localDescription.sdp});if(runId!==generation)return;
   statusTimer=setInterval(async()=>{if(runId!==generation||!lease||!peer)return;try{const r=await post('status',{lease});if(runId!==generation||!peer)return;if(r.sdp_answer){clearInterval(statusTimer);statusTimer=null;await peer.setRemoteDescription({type:'answer',sdp:r.sdp_answer});if(runId!==generation)return;starting=false;note('Sprich jetzt. Der Recorder bleibt während des Gesprächs gesperrt.');await poll();}}catch(e){if(runId===generation){note(e.message);await finish().catch(()=>{});}}},800);
  }catch(e){if(runId===generation)await finish().catch(()=>{});throw e;}
 });
 $('live-end').onclick=run(finish);
 $('live-mute').onclick=run(async()=>{if(!microphone||!lease)return;const muted=!state?.live?.muted;if(muted)microphone.getAudioTracks().forEach(t=>t.enabled=false);await post('mute',{lease,muted});if(microphone)microphone.getAudioTracks().forEach(t=>t.enabled=!muted);await poll()});
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&lease)finish().catch(()=>{})});
 window.addEventListener('pagehide',()=>{stopAudio();if(lease)fetch('/api/live/end',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({lease}),keepalive:true}).catch(()=>{})});
 window.addEventListener('offline',()=>{if(lease)finish().catch(()=>{})});
 renderLive();
})();
