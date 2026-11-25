/* CDB Voice One uses Python audio on the Pi; the browser only controls the session. */
(() => {
 const rail=document.createElement('button');rail.id='live-open';rail.className='rail-button';rail.setAttribute('aria-label','Live-Gespräch');rail.title='Live-Gespräch';rail.innerHTML='<img src="/assets/users.svg" alt=""><span>Live-Gespräch</span>';$('settings-open').before(rail);
 const view=document.createElement('dialog');view.id='live-view';view.className='workspace-view';view.setAttribute('aria-labelledby','live-heading');view.setAttribute('role','region');
 view.innerHTML=`<div class="dialog-heading"><h2 id="live-heading">Live-Gespräch</h2><button id="live-knowledge-open" aria-haspopup="dialog" aria-controls="knowledge-picker">Gesprächswissen wählen</button><span id="live-status" role="status"></span></div>
 <section class="live-content"><div class="live-feedback" id="live-feedback"><div class="live-feedback-copy"><strong id="live-feedback-title" role="status">Bereit für dein Gespräch</strong><span id="live-feedback-detail">Wähle oben dein Gesprächswissen.</span></div><div id="live-wave" class="live-wave" role="img" aria-label="Audiopegel">${Array.from({length:16},(_,i)=>'<i id="live-bar-'+i+'"></i>').join('')}</div><button id="live-sound" aria-pressed="true">Suchton an</button></div>
 <div class="live-layout"><div class="live-main"><div id="live-setup"><div class="live-welcome"><h3>Worüber möchtest du sprechen?</h3><p>Wähle oben dein Gesprächswissen und starte das Gespräch.</p></div><div class="live-pi-audio"><div class="live-device-cards"><div><span>Mikrofon</span><strong id="live-input-name">Wird geprüft …</strong></div><div><span>Lautsprecher</span><strong id="live-output-name">Wird geprüft …</strong></div></div><p id="live-audio-status" role="status">Mikrofon und Lautsprecher werden am Pi geprüft.</p></div></div>
 <div id="live-chat" hidden><div id="live-messages" role="log" aria-live="polite"></div><div class="live-history-controls"><nav id="live-chat-pages" class="direct-pages" aria-label="Gesprächsseiten"></nav><div class="live-history-trailing"><div id="live-cue" data-mode="idle"><span class="live-cue-icon" aria-hidden="true"><i></i><i></i><i></i><i></i></span><span id="live-cue-label" role="status"></span></div><button id="live-follow" aria-pressed="true">Am aktuellen Gespräch</button></div></div></div></div>
</div><div class="live-status-line"><p id="live-notice" role="status"></p><span id="live-nfc-hint" class="nfc-inline" role="status" aria-live="polite" hidden></span></div></section>
 <footer class="live-footer"><button id="live-audio-settings">Audioeinstellungen</button><button id="live-refresh" aria-label="Bereiche und Geräte aktualisieren" title="Bereiche und Geräte aktualisieren"><img src="/assets/arrow-clockwise.svg" alt=""></button><button id="live-new" hidden>Neues Gespräch</button><button id="live-mute" hidden aria-pressed="false">Mikro stumm</button><button id="live-start" class="primary">Gespräch starten</button><button id="live-end" hidden>Gespräch beenden</button></footer>`;document.body.append(view);
 let setup=null,chosen=new Set(),chatPage=null,lease=null,heartbeat=null,starting=false,ending=false,loadedOwner=null,generation=0;
 let savingSelection=false,setupLoading=false,setupError='',selectionInitialized=false,loadSerial=0,requestedAreas=[];
 window.addEventListener('brain-areas-changed',()=>{selectionInitialized=false;setup=null;chosen.clear();loadSerial++;setupLoading=false});
 const ownerKey=()=>JSON.stringify([state?.cdb?.identity||null,state?.cdb?.config?.server||null]);
 const areaName=a=>a.label||a.name||'Unbenannter Bereich';
 const areaLocked=()=>busy()||Boolean(state?.live?.history?.length);
 const maxAreas=()=>Math.min(8,Math.max(1,Number(setup?.max_areas)||8));
 const busy=()=>Boolean(state?.live?.busy)||starting||ending;
 window.studioLiveBusy=busy;
 const post=(path,body={})=>api('/api/live/'+path,body);
 function note(message){$('live-notice').textContent=message||'';}
 function stopHeartbeat(){clearInterval(heartbeat);heartbeat=null;}
 async function finish(){generation++;if(ending)return;ending=true;stopHeartbeat();const old=lease;lease=null;try{if(old)await post('end',{lease:old});else if(state?.live?.busy)await post('end',{});}finally{starting=false;ending=false;await poll();renderLive();}}
 async function load(forHome=false){
  if(savingSelection||busy()||(forHome!==true&&areaLocked()))return;
  const serial=++loadSerial,owner=ownerKey();setupLoading=true;setupError='';renderLive();
  try{
   const result=await api('/api/live/setup');if(serial!==loadSerial||owner!==ownerKey())return;
   setup=result;const available=new Set(setup.areas.map(a=>a.id));chosen=new Set([...chosen].filter(id=>available.has(id)));
   if(Array.isArray(setup.remembered_area_ids))chosen=new Set(setup.remembered_area_ids.filter(id=>available.has(id)));
   else if(!selectionInitialized&&setup.default_area&&available.has(setup.default_area.id))chosen.add(setup.default_area.id);
   selectionInitialized=true;note(setup.enabled?'':'Voice One ist in dieser Brain-Umgebung nicht freigeschaltet.');
  }catch(e){if(serial===loadSerial){setup=null;setupError=e.message;note(e.message)}}
  finally{if(serial===loadSerial){setupLoading=false;renderLive()}}
 }
 const baseWorkspace=workspaceView;
 workspaceView=function(id=null){if(busy()&&id!=='live-view')throw new Error('Gespräch läuft. Bitte zuerst beenden.');if(view.open&&id!=='live-view')view.close();baseWorkspace(id);rail.classList.toggle('active',id==='live-view');rail.setAttribute('aria-current',id==='live-view'?'page':'false');};
 rail.onclick=run(async()=>{if(state?.recording.id)throw new Error('Aufnahme läuft. Bitte zuerst stoppen.');await leaveDraft();audio.pause();if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();workspaceView('live-view');renderLive();if(!busy()&&!state?.live?.history?.length)await load()});
 function drawKnowledge(live,locked){
  const areas=locked?(live.areas?.length?live.areas:requestedAreas):(setup?.areas||[]).filter(a=>chosen.has(a.id));
  const names=areas.map(areaName);
  const button=$('live-knowledge-open');
  button.hidden=locked&&!names.length;
  button.disabled=!online||(!locked&&(setupLoading||!setup?.enabled));
  button.textContent=names.length?'Gesprächswissen ('+names.length+')':'Gesprächswissen wählen';
  $('live-status').textContent=names.join(' · ')||(locked?'Bereiche werden bestätigt …':'');
 }
 $('live-knowledge-open').onclick=run(async()=>{
  if(!view.open||!online)return;
  if(areaLocked()){
   const areas=(liveState().areas?.length?liveState().areas:requestedAreas).map(a=>({id:a.id,name:areaName(a)}));
   window.openStudioKnowledge({areas,ids:areas.map(a=>a.id),limit:maxAreas()},true);
   return;
  }
  const selection=await window.studioLiveHome.refresh();
  if(view.open&&!areaLocked()&&online)window.openStudioKnowledge(selection);
 });
 // Fit real rendered text to the fixed viewport, never arbitrary character counts.
 function historyPages(history,measure,height){
  const pages=[];let page=[],used=0;
  const finish=()=>{if(page.length)pages.push(page);page=[];used=0};
  (history||[]).forEach((row,turn)=>{
   const text=String(row.text||'');let start=0;
   while(start<text.length){
    const gap=page.length?12:0,room=height-used-gap;
    if(page.length&&room<100){finish();continue}
    const rest=text.slice(start);let end=text.length;
    if(measure(rest,row.role)>room){
     let lo=0,hi=rest.length;
     while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(measure(rest.slice(0,mid),row.role)<=room)lo=mid;else hi=mid-1}
     if(!lo&&page.length){finish();continue}
     lo=Math.max(1,lo);
     // Prefer paragraph/word boundaries, retaining every character and surrogate pair.
     const head=rest.slice(0,lo),newline=head.lastIndexOf('\n'),space=head.search(/\s+\S*$/);
     const boundary=newline>=lo*.55?newline+1:space>=lo*.65?space+1:lo;
     end=start+boundary;
     if(end<text.length&&/[\uD800-\uDBFF]/.test(text[end-1]))end--;
     if(end<=start)end=start+2;
    }
    const chunk=text.slice(start,end);
    page.push({role:row.role,text:chunk,turn,start,key:turn+':'+start});
    used+=gap+measure(chunk,row.role);start=end;
    if(start<text.length)finish();
   }
  });finish();return pages.length?pages:[[]];
 }
 const bubbleNodes=new Map();let historyCache=null,measureNode=null,lastHistoryLayout='';
 function measureMessage(text,role,width){
  if(!measureNode){measureNode=document.createElement('article');measureNode.innerHTML='<strong>Voice One</strong><p></p>';document.body.append(measureNode)}
  measureNode.className='live-message '+role+' live-measure';measureNode.style.width=Math.floor(width*(role==='user'?.76:.94))+'px';
  const p=measureNode.querySelector?.('p');if(p)p.textContent=text;
  return measureNode.getBoundingClientRect?.().height||48+Math.ceil(text.length/70)*27;
 }
 function drawHistory(live){
  const box=$('live-messages');
  // Hidden views have no usable geometry. Defer pagination until they are visible.
  if(box.getClientRects&&!box.getClientRects().length)return;
  const width=box.clientWidth||800,height=box.clientHeight||280;
  const signature=JSON.stringify([live.history,width,height]);
  if(!historyCache||historyCache.signature!==signature){historyCache={signature,pages:historyPages(live.history,(text,role)=>measureMessage(text,role,width),Math.max(80,height-2))}}
  const pages=historyCache.pages,page=chatPage===null?pages.length-1:Math.min(chatPage,pages.length-1),rows=pages[page];
  const nodes=[];
  for(const row of rows){
   let bubble=bubbleNodes.get(row.key);
   if(!bubble){
    bubble=document.createElement('article');bubble.className='live-message '+row.role;
    bubble._label=document.createElement('strong');bubble._body=document.createElement('p');
    bubble._stable=document.createElement('span');bubble._tail=document.createElement('span');bubble._tail.className='live-text-tail';
    bubble._body.append(bubble._stable,bubble._tail);bubble.append(bubble._label,bubble._body);bubbleNodes.set(row.key,bubble);
   }
   const label=(row.role==='user'?'Du':'Voice One')+(row.start?' · Fortsetzung':'');
   if(bubble._label.textContent!==label)bubble._label.textContent=label;
   if(bubble._text!==row.text){
    const previous=bubble._text||'',append=previous&&row.text.startsWith(previous);
    bubble._stable.textContent=append?previous:row.text;bubble._tail.textContent=append?row.text.slice(previous.length):'';
    if(append&&!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)bubble._tail.animate?.([{opacity:.35},{opacity:1}],{duration:160});
    bubble._text=row.text;bubble._changed=Date.now();
   }
   bubble.className="live-message "+row.role;
   bubble.dataset.streaming=String(Boolean(live.busy&&row.turn===live.history.length-1&&chatPage===null&&Date.now()-bubble._changed<1400));nodes.push(bubble);
  }
  const layout=rows.map(r=>r.key).join('|');
  if(layout!==lastHistoryLayout||!rows.length){
   box.replaceChildren(...nodes);lastHistoryLayout=layout;
   if(!rows.length)box.textContent=live.busy?'Sprich ganz natürlich. Dein Text erscheint hier.':'Noch kein Gesprächsverlauf.';
  }
  // Retain current nodes only; a growing conversation cannot accumulate detached DOM.
  for(const key of bubbleNodes.keys())if(!rows.some(r=>r.key===key))bubbleNodes.delete(key);
  const nav=$('live-chat-pages'),navKey=pages.length+':'+page;
  if(nav.dataset.pages!==navKey){drawPageNumbers(nav,pages.length,page,i=>{chatPage=i;drawHistory(liveState())});nav.dataset.pages=navKey}
  const following=chatPage===null;
  $('live-follow').textContent=following?'Am aktuellen Gespräch':'Zum Live-Gespräch';$('live-follow').disabled=following;$('live-follow').setAttribute('aria-pressed',String(following));
 }
 function liveState(){return state?.live||{history:[]}}
 $('live-follow').onclick=()=>{chatPage=null;drawHistory(liveState())};
 if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>{historyCache=null;if(view.open)drawHistory(liveState())}).observe($('live-messages'));
 document.fonts?.ready.then(()=>{historyCache=null;if(view.open)drawHistory(liveState())});

 function feedbackPresentation(f){
  if(f?.unavailable)return{title:'Verbindung unterbrochen',detail:'Audiozustand wird neu geprüft',bars:Array(16).fill(0),mode:'idle'};
  if(!f?.active)return{title:f?.state==='closing'?'Gespräch wird beendet …':'Gespräch beendet',detail:'Keine Audioübertragung',bars:Array(16).fill(0),mode:'idle'};
  if(f.state==='connecting'&&f.startup)return{title:'Verbindung wird aufgebaut …',detail:f.startup.stage+' · '+Math.max(0,Math.floor(f.startup.seconds||0))+' s · Bitte kurz warten – gleich bereit',bars:Array(16).fill(0),mode:'connecting'};
  const search=f.search||{},output=f.output||{},input=f.input||{};
  const title=search.web?'Sucht im Web …':search.brain?'Sucht im Brain …':output.active?'Voice One spricht':f.muted?'Mikrofon stumm':f.state==='thinking'?'Denkt nach …':f.state==='speaking'?'Antwort wird vorbereitet …':f.state==='connecting'?'Verbindet …':f.state==='reconnecting'?'Verbindung wird erneuert …':'Hört zu';
  return{title,detail:search.failed?'Suche fehlgeschlagen':f.muted?(output.active?'Mikrofon stumm · Antwort über Lautsprecher':'Dein Mikrofon ist ausgeschaltet'):output.active?'Antwort über den Pi-Lautsprecher':search.web||search.brain?'Recherche läuft · du kannst weiter zuhören':'Dein Mikrofon am Pi',bars:output.active?output.bars:!f.muted?input.bars:[],mode:search.web||search.brain?'search':output.active?'speaking':f.muted?'muted':'listening'};
 }
 function feedbackText(id,value){if($(id).textContent!==value)$(id).textContent=value}
 function cuePresentation(f){
  if(!online||!f?.active||f?.unavailable)return{mode:'idle',label:''};
  const searching=Boolean(f.search?.brain||f.search?.web);
  if(f.search_sound!==false&&f.search_audio?.playing)return{mode:'playing',label:searching?'Suchton läuft':'Suchton klingt aus'};
  if(searching)return{mode:'searching',label:f.search_sound===false?'Suche · Ton aus':'Suche · Ton pausiert'};
  return{mode:'idle',label:''};
 }
 function drawFeedback(f){
  const cue=cuePresentation(f);$('live-cue').dataset.mode=cue.mode;feedbackText('live-cue-label',cue.label);
  const ready=!busy()&&!state?.live?.history?.length;
  const p=ready?{title:setupLoading?'Bereiche werden geladen …':!online||setupError||!setup?.enabled||!setup?.audio?.available?'Noch nicht bereit':'Bereit für dein Gespräch',detail:!online?'Verbindung zum Pi wird wiederhergestellt.':setupError?'Verbindung prüfen und aktualisieren.':!setup?.enabled?'Brain-Anmeldung und Verbindung prüfen.':!setup?.audio?.available?'Mikrofon und Lautsprecher unter Audioeinstellungen prüfen.':'Wähle oben dein Gesprächswissen.',mode:'idle',bars:[]}:feedbackPresentation(online?f:{unavailable:true});
  $('live-wave').style.visibility=ready?'hidden':'visible';$('live-sound').style.visibility=ready?'hidden':'visible';feedbackText('live-feedback-title',p.title);feedbackText('live-feedback-detail',p.detail);$('live-feedback').dataset.mode=p.mode;
  $('live-wave').setAttribute('aria-label',p.mode==='speaking'?'Pegel der Antwort':'Mikrofonpegel');
  for(let i=0;i<16;i++){const v=Number(p.bars?.[i]);$('live-bar-'+i).style.transform='scaleY('+(.04+.96*(Number.isFinite(v)?Math.min(1,Math.max(0,v)):0))+')'}
  feedbackText('live-sound',f?.search_sound===false?'Suchton aus':'Suchton an');$('live-sound').setAttribute('aria-pressed',String(f?.search_sound!==false));const soundDisabled=!online||soundSaving||Boolean(f?.active&&!lease&&state?.live?.owner_kind!=='device');if($('live-sound').disabled!==soundDisabled)$('live-sound').disabled=soundDisabled;
 }
 let feedbackLoading=false,soundSaving=false,muteSaving=false;
 async function refreshFeedback(){
  if(feedbackLoading||!online||!view.open||document.hidden||!busy())return;
  feedbackLoading=true;const runId=generation;
  try{const f=await api('/api/live/activity');if(runId===generation&&busy()){state.live.feedback=f;drawFeedback(f)}}catch(_){drawFeedback({unavailable:true,search_sound:state?.live?.feedback?.search_sound})}finally{feedbackLoading=false}
 }
 setInterval(refreshFeedback,100);
 $('live-sound').onclick=run(async()=>{if(soundSaving)return;soundSaving=true;try{const f=await post('preferences',{lease,search_sound:state?.live?.feedback?.search_sound===false});state.live.feedback=f;drawFeedback(f)}finally{soundSaving=false;drawFeedback(state?.live?.feedback)}});
 function renderLive(){
  const live=state?.live||{state:'idle',history:[]},active=busy(),history=Boolean(live.history?.length),recording=Boolean(state?.recording.id);rail.disabled=recording;
  if(active&&document.body.dataset.workspace!=='live-view'){
   window.hideStudioKeyboard?.();audio.pause();
   if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();
   for(const dialog of document.querySelectorAll('dialog:modal'))dialog.close();
   workspaceView('live-view');
  }
  const owner=ownerKey();if(owner!==loadedOwner&&!active){loadedOwner=owner;setup=null;chosen.clear();requestedAreas=[];selectionInitialized=false;setupLoading=false;setupError='';loadSerial++;}
  view.dataset.active=String(active);$('live-setup').hidden=active||history;$('live-chat').hidden=!active&&!history;
  $('live-start').hidden=active||history;$('live-end').hidden=!active;$('live-end').disabled=!online||ending||live.state==='closing';
  $('live-mute').hidden=!active;$('live-mute').disabled=!online||muteSaving||(!lease&&live.owner_kind!=='device')||ending||live.state==='closing';$('live-mute').textContent=live.muted?'Mikro einschalten':'Mikro stumm';$('live-mute').setAttribute('aria-pressed',String(Boolean(live.muted)));
  $('live-refresh').hidden=active||history;$('live-audio-settings').hidden=active||history;$('live-new').hidden=active||!history;
  $('live-start').disabled=!online||recording||!setup?.enabled||savingSelection||setupLoading||!chosen.size||chosen.size>maxAreas()||!setup?.audio?.available;
  $('live-refresh').disabled=setupLoading||!online;$('live-audio-settings').disabled=active||recording||!online;
  $('live-input-name').textContent=setup?.audio?.microphone_label||'Mikrofon prüfen';$('live-output-name').textContent=setup?.audio?.speaker_label||'Lautsprecher prüfen';
  $('live-audio-status').textContent=setup?.audio?.message||(setup?.audio?.available?'Bereit. Keine zusätzliche Browserfreigabe nötig.':'Unter Audioeinstellungen prüfen und anschließend aktualisieren.');
  drawFeedback(live.feedback||{active:live.busy,state:live.state,muted:live.muted});drawKnowledge(live,active||history);drawHistory(live);if(!active&&$('live-notice').textContent==='Sprich am Pi. Der Recorder bleibt während des Gesprächs gesperrt.')note('');if(live.error)note(live.error);$('home').disabled=active;for(const id of ['library-open','settings-open','queue-toggle'])if(active)$(id).disabled=true;if(active)$('record').disabled=true;
  if(lease&&!live.busy&&!starting&&!ending){stopHeartbeat();lease=null;}
 }
 const previousRender=renderState;renderState=function(){previousRender();renderLive()};
 $('live-refresh').onclick=run(load);
 $('live-audio-settings').onclick=run(async()=>{if(busy())return;await openSettings();showSettingsDetail('audio-home')});
 $('live-new').onclick=run(async()=>{await post('clear');chatPage=null;requestedAreas=[];await poll();await load()});
 async function startConversation(){
  if(state?.recording?.id||busy()||!online||savingSelection||setupLoading||!setup?.enabled||!chosen.size||chosen.size>maxAreas()||!setup?.audio?.available)return;const runId=++generation;requestedAreas=setup.areas.filter(a=>chosen.has(a.id));starting=true;chatPage=null;if(document.body.classList.contains('keyboard-open'))$('keyboard').click();audio.pause();if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();note('Mikrofon und Lautsprecher werden am Pi verbunden …');renderLive();
  try{
   const reserved=await post('reserve',{area_ids:[...chosen],workshop_id:window.studioWorkshop?.selected()||null});if(runId!==generation){await post('end',{lease:reserved.lease});return;}lease=reserved.lease;
   heartbeat=setInterval(()=>{if(runId===generation&&lease)post('pulse',{lease}).catch(()=>{if(runId===generation)finish().catch(()=>{})})},5000);
   await post('start-native',{lease});if(runId!==generation)return;starting=false;note('Sprich am Pi. Der Recorder bleibt während des Gesprächs gesperrt.');await poll();renderLive();
  }catch(e){if(runId===generation){await finish().catch(()=>{});note(e.message);}throw e;}
 }
 $('live-start').onclick=run(startConversation);
 // Home edits the selection for the next conversation, even with history on screen.
 // Reserve starts a fresh session without clearing the previous history during selection.
 window.studioLiveHome={
  selection(){
   if(!setup||loadedOwner!==ownerKey())return null;
   return {key:setup.selection_account_key,
    ids:[...chosen],limit:maxAreas(),audio:setup.audio,enabled:setup.enabled};
  },
  async refresh(){
   const owner=ownerKey();
   await load(true);
   if(owner!==ownerKey()||busy()||state?.recording?.id)throw new Error('Gerätestatus hat sich geändert.');
   if(!setup||setupLoading)throw new Error(setupError||'Gesprächswissen bitte erneut laden.');
   return {...this.selection(),areas:setup.areas.map(a=>({id:a.id,name:areaName(a)}))};
  },
  async apply(key,ids){
   const valid=()=>online&&!busy()&&!state?.recording?.id&&key&&key===this.selection()?.key;
   if(savingSelection||!valid()||!ids.length||ids.length>maxAreas()||new Set(ids).size!==ids.length||!ids.every(id=>setup.areas.some(a=>a.id===id)))throw new Error('Gesprächswissen bitte neu öffnen.');
   savingSelection=true;renderLive();
   try{
    await post('areas',{account_key:key,area_ids:ids});
    if(!valid())throw new Error('Gerätestatus hat sich geändert.');
    chosen=new Set(ids);selectionInitialized=true;
   }finally{savingSelection=false;renderLive()}
  },
  start:startConversation
 };
 window.studioWorkshopLive={pause:finish,async prepare(){
  if(busy()||state?.recording?.id)throw new Error('Bitte das laufende Gespräch zuerst beenden.');
  if(state?.live?.history?.length){await post('clear');chatPage=null;await poll()}
  return window.studioLiveHome.refresh();
 }};
 $('live-end').onclick=run(finish);
 $('live-mute').onclick=run(async()=>{
  if($('live-mute').disabled||!busy())return;
  muteSaving=true;renderLive();
  try{await post('mute',{lease,muted:!state?.live?.muted});await poll()}
  finally{muteSaving=false;renderLive()}
 });
 window.addEventListener('pagehide',()=>{stopHeartbeat();if(lease)fetch('/api/live/end',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({lease}),keepalive:true}).catch(()=>{})});
 window.addEventListener('offline',()=>{if(lease)finish().catch(()=>{})});
 renderLive();
})();
