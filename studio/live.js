/* CDB Voice One uses Python audio on the Pi; the browser only controls the session. */
(() => {
 const rail=document.createElement('button');rail.id='live-open';rail.className='rail-button';rail.setAttribute('aria-label','Live-Gespräch');rail.title='Live-Gespräch';rail.innerHTML='<img src="/assets/users.svg" alt=""><span>Live-Gespräch</span>';$('settings-open').before(rail);
 const view=document.createElement('dialog');view.id='live-view';view.className='workspace-view';view.setAttribute('aria-labelledby','live-heading');view.setAttribute('role','region');
 view.innerHTML=`<div class="dialog-heading"><h2 id="live-heading">Live-Gespräch</h2><span id="live-status" role="status">Bereiche wählen</span></div>
 <section class="live-content"><div id="live-setup"><h3>Mit deinem Wissen sprechen</h3><p>Wähle deine Knowledge Areas und sprich direkt mit dem Mikrofon am Pi.</p><div class="live-scope-heading"><strong>Knowledge Areas</strong><span id="live-selection-count"></span></div><div id="live-areas"></div><nav id="live-area-pages" class="direct-pages" aria-label="Bereichsseiten"></nav>
 <div class="live-pi-audio"><div class="live-scope-heading"><strong>Audio am Raspberry Pi</strong><span>Aus deinen Einstellungen</span></div><div class="live-device-cards"><div><span>Mikrofon</span><strong id="live-input-name">Wird geprüft …</strong></div><div><span>Lautsprecher</span><strong id="live-output-name">Wird geprüft …</strong></div></div><p id="live-audio-status" role="status">Mikrofon und Lautsprecher werden am Pi geprüft.</p></div></div>
 <div id="live-chat" hidden><div class="live-feedback" id="live-feedback"><div class="live-feedback-copy"><strong id="live-feedback-title" role="status">Bereit</strong><span id="live-feedback-detail">Audio am Pi</span></div><div id="live-wave" class="live-wave" role="img" aria-label="Audiopegel">${Array.from({length:16},(_,i)=>'<i id="live-bar-'+i+'"></i>').join('')}</div><button id="live-sound" aria-pressed="true">Suchton an</button></div><div class="live-scope-summary" id="live-scope-summary"></div><div id="live-messages" role="log" aria-live="polite"></div><nav id="live-chat-pages" class="direct-pages" aria-label="Gesprächsseiten"></nav></div><p id="live-notice" role="status"></p></section>
 <footer class="live-footer"><button id="live-refresh">Aktualisieren</button><button id="live-audio-settings">Audioeinstellungen</button><button id="live-new" hidden>Neues Gespräch</button><button id="live-mute" hidden aria-pressed="false">Mikro stumm</button><button id="live-start" class="primary">Gespräch starten</button><button id="live-end" hidden>Gespräch beenden</button></footer>`;document.body.append(view);
 let setup=null,chosen=new Set(),areaPage=0,chatPage=null,lease=null,heartbeat=null,starting=false,ending=false,loadedOwner=null,generation=0;
 const messages={connecting:'Verbindet am Pi …',listening:'Hört zu',thinking:'Denkt nach …',speaking:'Spricht',reconnecting:'Verbindung wird erneuert …',closing:'Gespräch wird beendet …',ended:'Gespräch beendet',error:'Nicht verbunden',idle:'Bereiche wählen'};
 const busy=()=>Boolean(state?.live?.busy)||starting||ending;
 const post=(path,body={})=>api('/api/live/'+path,body);
 function note(message){$('live-notice').textContent=message||'';}
 function stopHeartbeat(){clearInterval(heartbeat);heartbeat=null;}
 async function finish(){generation++;if(ending)return;ending=true;stopHeartbeat();const old=lease;lease=null;try{if(old)await post('end',{lease:old});else if(state?.live?.busy)await post('end',{});}finally{starting=false;ending=false;await poll();renderLive();}}
 async function load(){note('Bereiche und Pi-Audio werden geprüft …');try{setup=await api('/api/live/setup');const available=new Set(setup.areas.map(a=>a.id));chosen=new Set([...chosen].filter(id=>available.has(id)));if(!chosen.size&&setup.default_area&&available.has(setup.default_area.id))chosen.add(setup.default_area.id);areaPage=0;note(setup.enabled?'':'Voice One ist in dieser Brain-Umgebung nicht freigeschaltet.');}catch(e){setup=null;note(e.message)}renderLive();}
 const baseWorkspace=workspaceView;
 workspaceView=function(id=null){if(busy()&&id!=='live-view')throw new Error('Gespräch läuft. Bitte zuerst beenden.');if(view.open&&id!=='live-view')view.close();baseWorkspace(id);rail.classList.toggle('active',id==='live-view');rail.setAttribute('aria-current',id==='live-view'?'page':'false');};
 rail.onclick=run(async()=>{if(state?.recording.id)throw new Error('Aufnahme läuft. Bitte zuerst stoppen.');await leaveDraft();audio.pause();if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();workspaceView('live-view');renderLive();if(!busy())await load()});
 function drawAreas(){const box=$('live-areas');box.replaceChildren();const areas=setup?.areas||[];areaPage=Math.min(areaPage,Math.max(0,Math.ceil(areas.length/4)-1));for(const area of areas.slice(areaPage*4,areaPage*4+4)){const b=document.createElement('button');b.className='live-area';b.textContent=area.label||area.name;b.setAttribute('aria-pressed',String(chosen.has(area.id)));b.onclick=()=>{if(chosen.has(area.id))chosen.delete(area.id);else if(chosen.size<(setup?.max_areas||8))chosen.add(area.id);else note('Maximal '+setup.max_areas+' Bereiche wählen.');renderLive()};box.append(b)}$('live-selection-count').textContent=chosen.size+' ausgewählt';drawPageNumbers($('live-area-pages'),Math.max(1,Math.ceil(areas.length/4)),areaPage,i=>{areaPage=i;drawAreas()});}
 function historyPages(history){const pages=[];let page=[];for(const row of history||[]){const text=String(row.text||'');for(const chunk of text.match(/(?:[^\n]{1,90}(?:\n|$)?|\n)/g)||[]){if(!page.length||page.at(-1).role!==row.role||page.at(-1).lines>=3)page.push({role:row.role,text:'',lines:0});page.at(-1).text+=chunk;page.at(-1).lines++;if(page.length===2&&page.at(-1).lines===3){pages.push(page);page=[];}}if(page.length===2){pages.push(page);page=[];}}if(page.length)pages.push(page);return pages.length?pages:[[]]}
 function drawHistory(live){const pages=historyPages(live.history);const page=chatPage===null?pages.length-1:Math.min(chatPage,pages.length-1);$('live-messages').replaceChildren();for(const row of pages[page]){const bubble=document.createElement('article');bubble.className='live-message '+row.role;const who=document.createElement('strong');who.textContent=row.role==='user'?'Du':'Voice One';const p=document.createElement('p');p.textContent=row.text;bubble.append(who,p);$('live-messages').append(bubble)}if(!pages[page].length)$('live-messages').textContent=live.busy?(lease?'Das Gespräch verwendet Mikrofon und Lautsprecher am Pi.':'Gespräch am Pi aktiv; in einem anderen Browser gestartet.'):'Noch kein Gesprächsverlauf.';drawPageNumbers($('live-chat-pages'),pages.length,page,i=>{chatPage=i===pages.length-1?null:i;drawHistory(live)});$('live-scope-summary').textContent=(live.areas||[]).map(a=>a.label||a.name).join(' · ');}

 function feedbackPresentation(f){
  if(f?.unavailable)return{title:'Verbindung unterbrochen',detail:'Audiozustand wird neu geprüft',bars:Array(16).fill(0),mode:'idle'};
  if(!f?.active)return{title:f?.state==='closing'?'Gespräch wird beendet …':'Gespräch beendet',detail:'Keine Audioübertragung',bars:Array(16).fill(0),mode:'idle'};
  const search=f.search||{},output=f.output||{},input=f.input||{};
  const title=search.web?'Sucht im Web …':search.brain?'Sucht im Brain …':output.active?'Voice One spricht':f.muted?'Mikrofon stumm':f.state==='thinking'?'Denkt nach …':f.state==='speaking'?'Antwort wird vorbereitet …':f.state==='connecting'?'Verbindet …':f.state==='reconnecting'?'Verbindung wird erneuert …':'Hört zu';
  return{title,detail:search.failed?'Suche fehlgeschlagen':f.muted?(output.active?'Mikrofon stumm · Antwort über Lautsprecher':'Dein Mikrofon ist ausgeschaltet'):output.active?'Antwort über den Pi-Lautsprecher':search.web||search.brain?'Recherche läuft · du kannst weiter zuhören':'Dein Mikrofon am Pi',bars:output.active?output.bars:!f.muted?input.bars:[],mode:search.web||search.brain?'search':output.active?'speaking':f.muted?'muted':'listening'};
 }
 function feedbackText(id,value){if($(id).textContent!==value)$(id).textContent=value}
 function drawFeedback(f){
  const p=feedbackPresentation(online?f:{unavailable:true});feedbackText('live-feedback-title',p.title);feedbackText('live-feedback-detail',p.detail);$('live-feedback').dataset.mode=p.mode;
  $('live-wave').setAttribute('aria-label',p.mode==='speaking'?'Pegel der Antwort':'Mikrofonpegel');
  for(let i=0;i<16;i++){const v=Number(p.bars?.[i]);$('live-bar-'+i).style.transform='scaleY('+(.04+.96*(Number.isFinite(v)?Math.min(1,Math.max(0,v)):0))+')'}
  feedbackText('live-sound',f?.search_sound===false?'Suchton aus':'Suchton an');$('live-sound').setAttribute('aria-pressed',String(f?.search_sound!==false));$('live-sound').disabled=!online||soundSaving||Boolean(f?.active&&!lease);
 }
 let feedbackLoading=false,soundSaving=false;
 async function refreshFeedback(){
  if(feedbackLoading||!online||!view.open||document.hidden||!busy())return;
  feedbackLoading=true;const runId=generation;
  try{const f=await api('/api/live/activity');if(runId===generation&&busy()){state.live.feedback=f;drawFeedback(f)}}catch(_){drawFeedback({unavailable:true,search_sound:state?.live?.feedback?.search_sound})}finally{feedbackLoading=false}
 }
 setInterval(refreshFeedback,100);
 $('live-sound').onclick=run(async()=>{if(soundSaving)return;soundSaving=true;try{const f=await post('preferences',{lease,search_sound:state?.live?.feedback?.search_sound===false});state.live.feedback=f;drawFeedback(f)}finally{soundSaving=false;drawFeedback(state?.live?.feedback)}});
 function renderLive(){
  const live=state?.live||{state:'idle',history:[]},active=busy(),history=Boolean(live.history?.length),recording=Boolean(state?.recording.id);rail.disabled=recording;
  const owner=JSON.stringify(state?.cdb?.identity||null);if(owner!==loadedOwner&&!active){loadedOwner=owner;setup=null;chosen.clear();}
  $('live-status').textContent='CDB Voice One';$('live-setup').hidden=active||history;$('live-chat').hidden=!active&&!history;
  $('live-start').hidden=active||history;$('live-end').hidden=!active;$('live-end').disabled=ending||live.state==='closing';
  $('live-mute').hidden=!active;$('live-mute').disabled=!lease||ending||live.state==='closing';$('live-mute').textContent=live.muted?'Mikro einschalten':'Mikro stumm';$('live-mute').setAttribute('aria-pressed',String(Boolean(live.muted)));
  $('live-refresh').hidden=active||history;$('live-audio-settings').hidden=active||history;$('live-new').hidden=active||!history;
  $('live-start').disabled=!online||recording||!setup?.enabled||!chosen.size||!setup?.audio?.available;
  $('live-audio-settings').disabled=active||recording||!online;
  $('live-input-name').textContent=setup?.audio?.microphone_label||'Mikrofon prüfen';$('live-output-name').textContent=setup?.audio?.speaker_label||'Lautsprecher prüfen';
  $('live-audio-status').textContent=setup?.audio?.message||(setup?.audio?.available?'Bereit. Keine zusätzliche Browserfreigabe nötig.':'Unter Audioeinstellungen prüfen und anschließend aktualisieren.');
  drawFeedback(live.feedback||{active:live.busy,state:live.state,muted:live.muted});drawAreas();drawHistory(live);if(!active&&$('live-notice').textContent==='Sprich am Pi. Der Recorder bleibt während des Gesprächs gesperrt.')note('');if(live.error)note(live.error);$('home').disabled=active;for(const id of ['library-open','settings-open','queue-toggle'])if(active)$(id).disabled=true;if(active)$('record').disabled=true;
  if(lease&&!live.busy&&!starting&&!ending){stopHeartbeat();lease=null;}
 }
 const previousRender=renderState;renderState=function(){previousRender();renderLive()};
 $('live-refresh').onclick=run(load);
 $('live-audio-settings').onclick=run(async()=>{if(busy())return;await openSettings();showSettingsDetail('audio-home')});
 $('live-new').onclick=run(async()=>{await post('clear');chatPage=null;await poll();await load()});
 $('live-start').onclick=run(async()=>{
  if(starting||busy()||!setup?.audio?.available)return;const runId=++generation;starting=true;chatPage=null;audio.pause();if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();note('Mikrofon und Lautsprecher werden am Pi verbunden …');renderLive();
  try{
   const reserved=await post('reserve',{area_ids:[...chosen]});if(runId!==generation){await post('end',{lease:reserved.lease});return;}lease=reserved.lease;
   heartbeat=setInterval(()=>{if(runId===generation&&lease)post('pulse',{lease}).catch(()=>{if(runId===generation)finish().catch(()=>{})})},5000);
   await post('start-native',{lease});if(runId!==generation)return;starting=false;note('Sprich am Pi. Der Recorder bleibt während des Gesprächs gesperrt.');await poll();renderLive();
  }catch(e){if(runId===generation){await finish().catch(()=>{});note(e.message);}throw e;}
 });
 $('live-end').onclick=run(finish);
 $('live-mute').onclick=run(async()=>{if(!lease)return;await post('mute',{lease,muted:!state?.live?.muted});await poll()});
 window.addEventListener('pagehide',()=>{stopHeartbeat();if(lease)fetch('/api/live/end',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({lease}),keepalive:true}).catch(()=>{})});
 window.addEventListener('offline',()=>{if(lease)finish().catch(()=>{})});
 renderLive();
})();
