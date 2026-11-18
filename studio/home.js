/* Home is a destination, not an alternate recorder. Existing routes own their locks. */
(() => {
 const rail=document.createElement('button');rail.id='start-open';rail.className='rail-button';rail.type='button';rail.title='Startseite';rail.setAttribute('aria-label','Startseite');rail.innerHTML='<img src="/assets/house.svg" alt=""><span>Startseite</span>';$('home').before(rail);
 const view=document.createElement('dialog');view.id='start-view';view.className='workspace-view';view.setAttribute('role','region');view.setAttribute('autofocus','');view.setAttribute('aria-labelledby','start-heading');
 view.innerHTML=`<header class="dialog-heading"><h2 id="start-heading">Recorder Studio</h2>
  <button type="button" id="start-knowledge" aria-haspopup="dialog" aria-controls="knowledge-picker">Gesprächswissen <span id="knowledge-count"></span><img src="/assets/caret-down.svg" alt=""></button></header>
  <section class="start-content"><h3>Was möchtest du machen?</h3><div id="start-tiles" class="start-tiles"></div><p id="start-feedback" role="status"></p></section>
  <footer class="start-footer"><div class="start-device-status"><i id="start-led" aria-hidden="true"></i><span id="start-status" role="status"></span></div><span id="start-background"></span></footer>`;document.body.append(view);
 const actions=[
  ['live','chat','Mit dem Brain sprechen','Gespräch am Pi starten'],
  ['recorder','record','Meeting aufzeichnen','Aufnahme am Pi starten']
 ];
 for(const [id,icon,title,hint] of actions){
  const button=document.createElement('button');button.id='start-'+id;button.type='button';button.className='start-tile';
  button.innerHTML='<img src="/assets/'+icon+'.svg" alt=""><strong>'+title+'</strong><span id="hint-'+id+'">'+hint+'</span>';
  $('start-tiles').append(button);
 }
 const picker=document.createElement('dialog');picker.id='knowledge-picker';picker.setAttribute('aria-labelledby','knowledge-title');
 picker.innerHTML=`<h2 id="knowledge-title">Gesprächswissen wählen</h2>
  <div class="knowledge-tools"><input id="knowledge-search" type="search" aria-label="Wissensbereiche suchen" placeholder="Bereiche suchen …"><button id="knowledge-keys" aria-label="Bildschirmtastatur öffnen">Tastatur</button><button id="knowledge-selected" aria-pressed="false">Ausgewählte</button></div><p id="knowledge-status" role="status"></p><div id="knowledge-grid" role="group" aria-label="Wissensbereiche"></div>
  <nav id="knowledge-pages" aria-label="Bereichsseiten"><button id="knowledge-prev">Zurück</button><span id="knowledge-page"></span><button id="knowledge-next">Weiter</button></nav>
  <footer><button id="knowledge-cancel">Abbrechen</button><button class="primary" id="knowledge-apply">Übernehmen</button></footer>`;document.body.append(picker);
 let pending=false,revision=0,catalog=null,draft=new Set(),page=0,saving=false;
 let selectedOnly=false,readOnly=false;
 const pageSize=6;
 const normalize=value=>value.toLocaleLowerCase('de').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
 function drawPicker(){
  const query=normalize($('knowledge-search').value.trim());
  const areas=catalog.areas.filter(a=>(!selectedOnly||draft.has(a.id))&&normalize(a.name).includes(query));
  const pages=Math.max(1,Math.ceil(areas.length/pageSize));
  page=Math.min(page,pages-1);
  $('knowledge-selected').setAttribute('aria-pressed',String(selectedOnly));
  $('knowledge-selected').textContent='Ausgewählte ('+draft.size+')';
  $('knowledge-grid').dataset.paged=String(pages>1);
  $('knowledge-grid').replaceChildren();
  for(const area of areas.slice(page*pageSize,(page+1)*pageSize)){
   const button=document.createElement('button');
   button.type='button';
   button.textContent=area.name;
   button.title=area.name;
   button.setAttribute('aria-pressed',String(draft.has(area.id)));
   button.disabled=readOnly||saving||(!draft.has(area.id)&&draft.size>=catalog.limit);
   button.onclick=()=>{
    if(saving||readOnly)return;
    if(draft.has(area.id))draft.delete(area.id);else draft.add(area.id);
    const index=areas.indexOf(area)%pageSize;
    drawPicker();
    $('knowledge-grid').children[index]?.focus();
   };
   $('knowledge-grid').append(button);
  }
  $('knowledge-status').textContent=!areas.length&&catalog.areas.length?'Keine passenden Bereiche · '+draft.size+' ausgewählt':catalog.areas.length?draft.size+' von maximal '+catalog.limit+' ausgewählt':'Für dieses Brain-Konto sind keine Wissensbereiche verfügbar.';
  if(readOnly)$('knowledge-status').textContent='Für dieses Gespräch festgelegt · '+draft.size+(draft.size===1?' Bereich':' Bereiche');
  $('knowledge-pages').hidden=pages===1;$('knowledge-page').textContent=(page+1)+' / '+pages;
  $('knowledge-prev').disabled=saving||page===0;$('knowledge-next').disabled=saving||page+1>=pages;
  $('knowledge-apply').disabled=saving||!draft.size||draft.size>catalog.limit;$('knowledge-cancel').disabled=saving;
 }
 function openPicker(selection,review=false){
  if(picker.open||saving)return;
  readOnly=review;catalog=selection;
  selectedOnly=false;$('knowledge-search').value='';
  draft=new Set(catalog.ids);
  $('knowledge-title').textContent=readOnly?'Gesprächswissen in diesem Gespräch':'Gesprächswissen wählen';
  $('knowledge-cancel').textContent=readOnly?'Schließen':'Abbrechen';
  $('knowledge-apply').hidden=readOnly;
  $('knowledge-selected').hidden=readOnly;
  page=0;
  drawPicker();
  picker.showModal();
 }
 window.openStudioKnowledge=openPicker;
 $('knowledge-search').oninput=()=>{page=0;drawPicker()};
 $('knowledge-selected').onclick=()=>{selectedOnly=!selectedOnly;page=0;drawPicker()};
 $('knowledge-keys').onclick=()=>{$('knowledge-search').focus();$('keyboard').click()};
 $('knowledge-prev').onclick=()=>{page--;drawPicker()};$('knowledge-next').onclick=()=>{page++;drawPicker()};
 $('knowledge-cancel').onclick=()=>picker.close();
 picker.oncancel=event=>{if(saving)event.preventDefault()};
 $('knowledge-apply').onclick=async()=>{
  if(saving||readOnly||!catalog)return;
  saving=true;drawPicker();
  try{await window.studioLiveHome.apply(catalog.key,[...draft]);picker.close()}
  catch(error){saving=false;drawPicker();$('knowledge-status').textContent=error.message}
  finally{saving=false;renderHome()}
 };
 function allowsAction(ticket){
  return ticket===revision&&view.open&&online&&state&&!state.recording?.id&&!$('home').disabled;
 }
 async function activate(action){
  if(pending||picker.open||!allowsAction(revision))return;
  const ticket=revision;let failure='';pending=true;
  $('start-feedback').textContent=action==='recorder'?'Aufnahme wird vorbereitet …':'Gesprächswissen wird geladen …';renderHome();
  try{
   await leaveDraft();if(!allowsAction(ticket))return;
   if(action==='recorder'){
    if($('record').disabled)return;
    workspaceView();
    await $('record').onclick();
    return;
   }
   const selection=await window.studioLiveHome.refresh();
   if(!allowsAction(ticket))return;
   if(!selection.enabled)throw new Error('Voice One ist für dieses Brain-Konto nicht freigeschaltet.');
   if(action==='knowledge'||!selection.ids.length||selection.ids.length>selection.limit){openPicker(selection);return}
   if(!selection.audio?.available)throw new Error(selection.audio?.message||'Bitte Mikrofon und Lautsprecher unter Audio einrichten.');
   workspaceView('live-view');
   await window.studioLiveHome.start();
  }catch(error){
   if(allowsAction(ticket))failure=error.message;
   else if(document.body.dataset.workspace==='live-view')notice(error.message);
  }finally{
   pending=false;renderHome();
   $('start-feedback').textContent=failure;
  }
 }
 $('start-live').onclick=()=>activate('live');$('start-recorder').onclick=()=>activate('recorder');$('start-knowledge').onclick=()=>activate('knowledge');
 let initial=true,navigated=false;
 const previousWorkspace=workspaceView;
 workspaceView=function(id=null){const opening=id==='start-view'&&!view.open;previousWorkspace(id);if(opening)document.activeElement?.blur();navigated=true;if(id!=='start-view'&&view.open){revision++;if(picker.open)picker.close();view.close()}const active=id==='start-view';rail.classList.toggle('active',active);rail.setAttribute('aria-current',active?'page':'false')};
 rail.onclick=run(async()=>{if(rail.disabled)return;await leaveDraft();audio.pause();workspaceView('start-view');renderHome()});
 function renderHome(){
  // Recorder's disabled state also includes Live's local connecting/closing transitions.
  const locked=Boolean(state?.recording?.id)||Boolean($('home').disabled);
  rail.disabled=!state||locked;rail.title=locked?'Aufnahme oder Gespräch läuft · zuerst beenden':'Startseite';
  const unavailable=rail.disabled||!online||pending;
  $('start-live').disabled=unavailable;$('start-recorder').disabled=unavailable||$('record').disabled;
  $('start-knowledge').disabled=unavailable;
  const selection=window.studioLiveHome.selection();
  $('knowledge-count').textContent=selection?'('+selection.ids.length+')':'';
  if(picker.open){
   const invalid=readOnly?!$('live-view').open||(!state?.live?.busy&&!state?.live?.history?.length):locked||!selection||selection.key!==catalog.key;
   if(!online||invalid)picker.close();
  }
  const readiness=typeof currentReadiness==='function'?currentReadiness():{tone:'waiting',label:'Status wird geprüft'};
  $('hint-recorder').textContent=$('record').disabled?readiness.label:'Aufnahme am Pi starten';
  $('start-led').dataset.state=readiness.tone;$('start-status').textContent=readiness.label;
  const count=state?(state.jobs||[]).filter(j=>['queued','transcribing','summarizing','importing'].includes(j.state)).length:0;
  $('start-background').textContent=count?count+(count===1?' Auftrag':' Aufträge')+' in der Verarbeitung':'Verarbeitung im Hintergrund';
  if(view.open&&state?.live?.busy)workspaceView('live-view');
  if(initial&&state&&online){initial=false;if(!navigated){if(state.live?.busy)workspaceView('live-view');else if(!locked)workspaceView('start-view')}}
 }
 const previousRender=renderState;renderState=function(){previousRender();renderHome()};renderHome();
})();
