/* CDB Voice One uses Python audio on the Pi; the browser only controls the session. */
(() => {
 const rail=document.createElement('button');rail.id='live-open';rail.className='rail-button';rail.setAttribute('aria-label','Live-Gespräch');rail.title='Live-Gespräch';rail.innerHTML='<img src="/assets/users.svg" alt=""><span>Live-Gespräch</span>';$('settings-open').before(rail);
 const view=document.createElement('dialog');view.id='live-view';view.className='workspace-view';view.setAttribute('aria-labelledby','live-heading');view.setAttribute('role','region');
 view.innerHTML=`<div class="dialog-heading"><h2 id="live-heading">Live-Gespräch</h2><span id="live-status" role="status">Bereiche wählen</span></div>
 <section class="live-content"><div class="live-feedback" id="live-feedback"><div class="live-feedback-copy"><strong id="live-feedback-title" role="status">Bereit für dein Gespräch</strong><span id="live-feedback-detail">Wähle rechts dein Gesprächswissen.</span></div><div id="live-wave" class="live-wave" role="img" aria-label="Audiopegel">${Array.from({length:16},(_,i)=>'<i id="live-bar-'+i+'"></i>').join('')}</div><button id="live-sound" aria-pressed="true">Suchton an</button></div>
 <div class="live-layout"><div class="live-main"><div id="live-setup"><div class="live-welcome"><h3>Worüber möchtest du sprechen?</h3><p>Wähle einen oder mehrere Wissensbereiche<br>und starte dein Gespräch.</p></div><div class="live-pi-audio"><div class="live-device-cards"><div><span>Mikrofon</span><strong id="live-input-name">Wird geprüft …</strong></div><div><span>Lautsprecher</span><strong id="live-output-name">Wird geprüft …</strong></div></div><p id="live-audio-status" role="status">Mikrofon und Lautsprecher werden am Pi geprüft.</p></div></div>
 <div id="live-chat" hidden><div id="live-messages" role="log" aria-live="polite"></div><div class="live-history-controls"><nav id="live-chat-pages" class="direct-pages" aria-label="Gesprächsseiten"></nav><div class="live-history-trailing"><div id="live-cue" data-mode="idle"><span class="live-cue-icon" aria-hidden="true"><i></i><i></i><i></i><i></i></span><span id="live-cue-label" role="status"></span></div><button id="live-follow" aria-pressed="true">Am aktuellen Gespräch</button></div></div></div></div>
 <aside class="live-knowledge" aria-labelledby="live-knowledge-heading"><div class="live-knowledge-heading"><img src="/assets/book-open.svg" alt=""><div><h3 id="live-knowledge-heading">Gesprächswissen</h3><span id="live-selection-count" role="status"></span></div></div><div class="live-area-tools"><label id="live-search-label"><img src="/assets/magnifying-glass.svg" alt=""><input id="live-area-search" type="search" aria-label="Wissensbereiche suchen" placeholder="Suchen …" autocomplete="off"></label><button id="live-selected-filter" aria-pressed="false">Ausgewählt (0)</button><p id="live-area-lock" hidden><img src="/assets/lock-simple.svg" alt=""><span id="live-area-lock-text">Auswahl im Gespräch gesperrt</span></p></div><div id="live-areas" role="group" aria-label="Wissensbereiche"></div><div class="live-area-footer"><nav id="live-area-pages" class="direct-pages" aria-label="Bereichsseiten"></nav><span id="live-area-position"></span></div></aside></div><p id="live-notice" role="status"></p></section>
 <footer class="live-footer"><button id="live-audio-settings">Audioeinstellungen</button><button id="live-refresh" aria-label="Bereiche und Geräte aktualisieren" title="Bereiche und Geräte aktualisieren"><img src="/assets/arrow-clockwise.svg" alt=""></button><button id="live-new" hidden>Neues Gespräch</button><button id="live-mute" hidden aria-pressed="false">Mikro stumm</button><button id="live-start" class="primary">Gespräch starten</button><button id="live-end" hidden>Gespräch beenden</button></footer>`;document.body.append(view);
 let setup=null,chosen=new Set(),areaPage=0,chatPage=null,lease=null,heartbeat=null,starting=false,ending=false,loadedOwner=null,generation=0;
 let selectedOnly=false,selectionSave=Promise.resolve();
 let areaQuery='',areaPageSize=4,areaSignature='',areaNavSignature='',setupLoading=false,setupError='',selectionInitialized=false,loadSerial=0,requestedAreas=[];
 window.addEventListener('brain-areas-changed',()=>{selectionInitialized=false;setup=null});
 const ownerKey=()=>JSON.stringify([state?.cdb?.identity||null,state?.cdb?.config?.server||null]);
 const areaName=a=>a.label||a.name||'Unbenannter Bereich';
 const areaLocked=()=>busy()||Boolean(state?.live?.history?.length);
 const maxAreas=()=>Math.min(8,Math.max(1,Number(setup?.max_areas)||8));
 const messages={connecting:'Verbindet am Pi …',listening:'Hört zu',thinking:'Denkt nach …',speaking:'Spricht',reconnecting:'Verbindung wird erneuert …',closing:'Gespräch wird beendet …',ended:'Gespräch beendet',error:'Nicht verbunden',idle:'Bereiche wählen'};
 const busy=()=>Boolean(state?.live?.busy)||starting||ending;
 const post=(path,body={})=>api('/api/live/'+path,body);
 function note(message){$('live-notice').textContent=message||'';}
 function stopHeartbeat(){clearInterval(heartbeat);heartbeat=null;}
 async function finish(){generation++;if(ending)return;ending=true;stopHeartbeat();const old=lease;lease=null;try{if(old)await post('end',{lease:old});else if(state?.live?.busy)await post('end',{});}finally{starting=false;ending=false;await poll();renderLive();}}
 async function load(){
  if(areaLocked())return;
  const serial=++loadSerial,owner=ownerKey();setupLoading=true;setupError='';renderLive();
  try{
   await selectionSave;if(serial!==loadSerial||owner!==ownerKey())return;
   const result=await api('/api/live/setup');if(serial!==loadSerial||owner!==ownerKey())return;
   setup=result;const available=new Set(setup.areas.map(a=>a.id));chosen=new Set([...chosen].filter(id=>available.has(id)));
   if(Array.isArray(setup.remembered_area_ids))chosen=new Set(setup.remembered_area_ids.filter(id=>available.has(id)));
   else if(!selectionInitialized&&setup.default_area&&available.has(setup.default_area.id))chosen.add(setup.default_area.id);
   selectionInitialized=true;areaPage=0;note(setup.enabled?'':'Voice One ist in dieser Brain-Umgebung nicht freigeschaltet.');
  }catch(e){if(serial===loadSerial){setup=null;setupError=e.message;note(e.message)}}
  finally{if(serial===loadSerial){setupLoading=false;renderLive()}}
 }
 function rememberSelection(){
  const owner=ownerKey(),key=setup?.selection_account_key,ids=[...chosen];if(!key)return;
  selectionSave=selectionSave.catch(()=>{}).then(async()=>{
   if(owner!==ownerKey())return;
   try{await post('areas',{account_key:key,area_ids:ids})}
   catch(e){if(owner===ownerKey())note('Auswahl konnte nicht gemerkt werden: '+e.message)}
  });
 }
 const baseWorkspace=workspaceView;
 workspaceView=function(id=null){if(busy()&&id!=='live-view')throw new Error('Gespräch läuft. Bitte zuerst beenden.');if(view.open&&id!=='live-view')view.close();baseWorkspace(id);rail.classList.toggle('active',id==='live-view');rail.setAttribute('aria-current',id==='live-view'?'page':'false');};
 rail.onclick=run(async()=>{if(state?.recording.id)throw new Error('Aufnahme läuft. Bitte zuerst stoppen.');await leaveDraft();audio.pause();if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();workspaceView('live-view');renderLive();if(!busy()&&!state?.live?.history?.length)await load()});
 function drawAreas(){
  const locked=areaLocked(),live=liveState(),confirmed=live.areas||[];
  const source=locked?(confirmed.length?confirmed:busy()?requestedAreas:[]):setup?.areas||[];
  const normalize=text=>text.toLocaleLowerCase('de').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const query=locked?'':normalize(areaQuery.trim()),areas=source.filter(a=>(locked||!selectedOnly||chosen.has(a.id))&&(!query||normalize(areaName(a)).includes(query)));
  const count=Math.max(1,Math.ceil(areas.length/areaPageSize));areaPage=Math.max(0,Math.min(areaPage,count-1));
  $('live-area-search').disabled=locked||setupLoading||!online||!setup;$('live-search-label').hidden=locked;$('live-area-lock').hidden=!locked;
  $('live-selected-filter').hidden=locked;$('live-selected-filter').disabled=locked||setupLoading||!online||!setup;$('live-selected-filter').textContent='Ausgewählt ('+chosen.size+')';$('live-selected-filter').setAttribute('aria-pressed',String(selectedOnly));$('live-selected-filter').setAttribute('aria-label',selectedOnly?'Alle Wissensbereiche anzeigen':'Nur ausgewählte Wissensbereiche anzeigen ('+chosen.size+')');
  $('live-area-lock-text').textContent=busy()?'Auswahl im Gespräch gesperrt':'Für dieses Gespräch festgelegt';
  $('live-selection-count').textContent=locked?(source.length+(source.length===1?' Bereich ':' Bereiche ')+(busy()?'im Gespräch':'verwendet')):setupLoading?'Bereiche werden geladen …':chosen.size+' von maximal '+maxAreas()+' ausgewählt';
  const rows=areas.slice(areaPage*areaPageSize,(areaPage+1)*areaPageSize);
  const signature=JSON.stringify([rows,locked,[...chosen],areaPageSize,online,setupLoading,setupError,maxAreas(),selectedOnly]);
  if(signature!==areaSignature){
   areaSignature=signature;const box=$('live-areas');box.style.setProperty?.('--area-rows',areaPageSize);box.replaceChildren();
   for(const area of rows){
    const selected=locked||chosen.has(area.id),row=document.createElement(locked?'div':'button');row.className='live-area';row.title=areaName(area);row.dataset.selected=String(selected);
    const icon=document.createElement('img');icon.src='/assets/'+(locked?'check-circle':selected?'check-square':'square')+'.svg';icon.alt='';
    const label=document.createElement('span');label.textContent=areaName(area);row.append(icon,label);
    if(!locked){row.type='button';row.setAttribute('role','checkbox');row.setAttribute('aria-checked',String(selected));row.setAttribute('aria-label',areaName(area));row.disabled=!online||setupLoading||(!selected&&chosen.size>=maxAreas());
     row.onclick=()=>{if(areaLocked()||!online||setupLoading||!setup?.areas.some(a=>a.id===area.id))return;if(chosen.has(area.id))chosen.delete(area.id);else if(chosen.size<maxAreas())chosen.add(area.id);else return;selectionInitialized=true;note('');rememberSelection();renderLive()};
    }box.append(row);
   }
   if(!rows.length){const empty=document.createElement('p');empty.className='live-area-empty';empty.textContent=locked?'Bereiche werden bestätigt …':setupLoading?'Bereiche werden geladen …':setupError?'Bereiche konnten nicht geladen werden. Bitte aktualisieren.':query?'Keine passenden Bereiche. Suche ändern.':selectedOnly?'Noch nichts ausgewählt. Filter ausschalten, um Bereiche zu wählen.':'Keine Wissensbereiche verfügbar.';box.append(empty)}
  }
  const navKey=count+':'+areaPage;
  if(navKey!==areaNavSignature){areaNavSignature=navKey;const nav=$('live-area-pages');nav.replaceChildren();const first=Math.max(0,Math.min(areaPage-1,count-3));for(let i=first;i<Math.min(count,first+3);i++){const button=document.createElement('button');button.textContent=String(i+1);button.setAttribute('aria-label','Bereichsseite '+(i+1));button.setAttribute('aria-current',i===areaPage?'page':'false');button.onclick=()=>{areaPage=i;drawAreas()};nav.append(button)}}
  $('live-area-position').textContent=(areaPage+1)+' / '+count;
 }
 $('live-selected-filter').onclick=()=>{if(areaLocked()||setupLoading||!online||!setup)return;selectedOnly=!selectedOnly;areaQuery='';$('live-area-search').value='';areaPage=0;drawAreas()};
 $('live-area-search').oninput=()=>{if(areaLocked())return;areaQuery=$('live-area-search').value;areaPage=0;drawAreas()};
 if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>{const size=Math.max(1,Math.min(4,Math.floor((($('live-areas').clientHeight||210)+6)/54)));if(size!==areaPageSize){const first=areaPage*areaPageSize;areaPageSize=size;areaPage=Math.floor(first/size);drawAreas()}}).observe($('live-areas'));
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
  const p=ready?{title:setupLoading?'Bereiche werden geladen …':'Bereit für dein Gespräch',detail:setupError?'Verbindung prüfen und aktualisieren.':'Wähle rechts dein Gesprächswissen.',mode:'idle',bars:[]}:feedbackPresentation(online?f:{unavailable:true});
  $('live-wave').style.visibility=ready?'hidden':'visible';$('live-sound').style.visibility=ready?'hidden':'visible';feedbackText('live-feedback-title',p.title);feedbackText('live-feedback-detail',p.detail);$('live-feedback').dataset.mode=p.mode;
  $('live-wave').setAttribute('aria-label',p.mode==='speaking'?'Pegel der Antwort':'Mikrofonpegel');
  for(let i=0;i<16;i++){const v=Number(p.bars?.[i]);$('live-bar-'+i).style.transform='scaleY('+(.04+.96*(Number.isFinite(v)?Math.min(1,Math.max(0,v)):0))+')'}
  feedbackText('live-sound',f?.search_sound===false?'Suchton aus':'Suchton an');$('live-sound').setAttribute('aria-pressed',String(f?.search_sound!==false));$('live-sound').disabled=!online||soundSaving||Boolean(f?.active&&!lease&&state?.live?.owner_kind!=='device');
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
  const owner=ownerKey();if(owner!==loadedOwner&&!active){loadedOwner=owner;setup=null;chosen.clear();requestedAreas=[];selectedOnly=false;selectionInitialized=false;setupLoading=false;setupError='';loadSerial++;areaQuery='';$('live-area-search').value='';areaPage=0;}
  $('live-status').textContent='CDB Voice One';$('live-setup').hidden=active||history;$('live-chat').hidden=!active&&!history;
  $('live-start').hidden=active||history;$('live-end').hidden=!active;$('live-end').disabled=ending||live.state==='closing';
  $('live-mute').hidden=!active;$('live-mute').disabled=(!lease&&live.owner_kind!=='device')||ending||live.state==='closing';$('live-mute').textContent=live.muted?'Mikro einschalten':'Mikro stumm';$('live-mute').setAttribute('aria-pressed',String(Boolean(live.muted)));
  $('live-refresh').hidden=active||history;$('live-audio-settings').hidden=active||history;$('live-new').hidden=active||!history;
  $('live-start').disabled=!online||recording||!setup?.enabled||setupLoading||!chosen.size||chosen.size>maxAreas()||!setup?.audio?.available;
  $('live-refresh').disabled=setupLoading||!online;$('live-audio-settings').disabled=active||recording||!online;
  $('live-input-name').textContent=setup?.audio?.microphone_label||'Mikrofon prüfen';$('live-output-name').textContent=setup?.audio?.speaker_label||'Lautsprecher prüfen';
  $('live-audio-status').textContent=setup?.audio?.message||(setup?.audio?.available?'Bereit. Keine zusätzliche Browserfreigabe nötig.':'Unter Audioeinstellungen prüfen und anschließend aktualisieren.');
  drawFeedback(live.feedback||{active:live.busy,state:live.state,muted:live.muted});drawAreas();drawHistory(live);if(!active&&$('live-notice').textContent==='Sprich am Pi. Der Recorder bleibt während des Gesprächs gesperrt.')note('');if(live.error)note(live.error);$('home').disabled=active;for(const id of ['library-open','settings-open','queue-toggle'])if(active)$(id).disabled=true;if(active)$('record').disabled=true;
  if(lease&&!live.busy&&!starting&&!ending){stopHeartbeat();lease=null;}
 }
 const previousRender=renderState;renderState=function(){previousRender();renderLive()};
 $('live-refresh').onclick=run(load);
 $('live-audio-settings').onclick=run(async()=>{if(busy())return;await openSettings();showSettingsDetail('audio-home')});
 $('live-new').onclick=run(async()=>{await post('clear');chatPage=null;areaPage=0;selectedOnly=false;areaQuery='';$('live-area-search').value='';requestedAreas=[];await poll();await load()});
 $('live-start').onclick=run(async()=>{
  if(starting||busy()||!online||setupLoading||!setup?.enabled||!chosen.size||chosen.size>maxAreas()||!setup?.audio?.available)return;const runId=++generation;requestedAreas=setup.areas.filter(a=>chosen.has(a.id));starting=true;areaPage=0;chatPage=null;if(document.body.classList.contains('keyboard-open'))$('keyboard').click();audio.pause();if(typeof pauseMicrophoneAudio==='function')pauseMicrophoneAudio();note('Mikrofon und Lautsprecher werden am Pi verbunden …');renderLive();
  try{
   await selectionSave;if(runId!==generation)return;
   const reserved=await post('reserve',{area_ids:[...chosen]});if(runId!==generation){await post('end',{lease:reserved.lease});return;}lease=reserved.lease;
   heartbeat=setInterval(()=>{if(runId===generation&&lease)post('pulse',{lease}).catch(()=>{if(runId===generation)finish().catch(()=>{})})},5000);
   await post('start-native',{lease});if(runId!==generation)return;starting=false;note('Sprich am Pi. Der Recorder bleibt während des Gesprächs gesperrt.');await poll();renderLive();
  }catch(e){if(runId===generation){await finish().catch(()=>{});note(e.message);}throw e;}
 });
 $('live-end').onclick=run(finish);
 $('live-mute').onclick=run(async()=>{if(!lease&&state?.live?.owner_kind!=='device')return;await post('mute',{lease,muted:!state?.live?.muted});await poll()});
 window.addEventListener('pagehide',()=>{stopHeartbeat();if(lease)fetch('/api/live/end',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({lease}),keepalive:true}).catch(()=>{})});
 window.addEventListener('offline',()=>{if(lease)finish().catch(()=>{})});
 renderLive();
})();
