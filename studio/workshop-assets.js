/* Reviewed text assets: chat card, large selection tiles and explicit Brain filing. */
(() => {
 const labels={goal:'Ziel',questions:'Fragen',findings:'Erkenntnisse',ideas:'Ideen',decisions:'Entscheidungen',next_steps:'Nächste Schritte'};
 const states={queued:'Wartet auf Übertragung',sending:'Wird übertragen',accepted:'Im Brain empfangen · wird verarbeitet',completed:'Im Brain gespeichert',completed_without_graph:'Im Brain gespeichert · ohne Wissensgraph',uncertain:'Empfang unklar · bitte im Brain prüfen',failed:'Verarbeitung fehlgeschlagen'};
 const dialog=document.createElement('dialog');dialog.id='workshop-assets';dialog.setAttribute('aria-labelledby','asset-heading');
 dialog.innerHTML='<header><div><h2 id="asset-heading"></h2><p id="asset-meta"></p></div><button id="asset-keyboard" hidden>Tastatur</button></header><section id="asset-body"></section><p id="asset-message" role="status"></p><div id="asset-pagination" hidden></div><footer><button id="asset-back">Schließen</button><button id="asset-next" class="primary"></button></footer>';
 document.body.append(dialog);
 const card=document.createElement('aside');card.id='workshop-chat-card';card.hidden=true;card.setAttribute('aria-label','Erzeugte Gesprächsergebnisse');
 card.innerHTML='<div><strong id="asset-chat-title"></strong><p id="asset-chat-detail"></p></div><button id="asset-chat-open">Ergebnisse ansehen</button>';
 $('live-messages').after(card);
 let row=null,mode='select',selected=new Set(),page=0,areas=[],areaId=null,query='',areaPage=0,reading=null,jobs=[],loading=false,sending=false,generation=0,ownerKey='',activeId=null,receiptKey='';
 const body=$('asset-body'),back=$('asset-back'),next=$('asset-next');
 const node=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n};
 const message=value=>$('asset-message').textContent=value||'';
 const send=payload=>api('/api/workshops',payload);
 const available=()=>Object.keys(labels).filter(k=>row?.sections[k]?.trim());
 function button(label,fn){const b=node('button',label);b.onclick=run(fn);return b}
 function close(){window.hideStudioKeyboard?.();dialog.close();generation++;}
 function header(title,meta){$('asset-heading').textContent=title;$('asset-meta').textContent=meta;body.replaceChildren();$('asset-pagination').replaceChildren();$('asset-pagination').hidden=true;message('');dialog.dataset.mode=mode;next.hidden=false;next.disabled=false;back.textContent='Schließen';back.onclick=close;$('asset-keyboard').hidden=mode!=='target';}
 function pages(count,current,change){const container=$('asset-pagination');container.replaceChildren();container.hidden=count<=1;if(count<=1)return;const nav=document.createElement('nav');nav.className='asset-pages';nav.setAttribute('aria-label',mode==='target'?'Wissensbereichseiten':'Ergebnisseiten');const previous=button('Zurück',()=>change(current-1)),following=button('Weiter',()=>change(current+1));previous.disabled=current===0;following.disabled=current===count-1;nav.append(previous,node('span',`Seite ${current+1} von ${count}`),following);container.append(nav)}
 async function open(id){
  if(sending)return;const token=++generation;loading=true;mode='select';row=null;header('Ergebnisse werden geladen …','');next.hidden=true;if(!dialog.open)dialog.showModal();
  try{const fresh=await send({action:'read',id});if(token!==generation)return;row=fresh;selected=new Set(available());page=0;areaId=null;jobs=[];drawSelection()}
  catch(e){if(token===generation)message(e.message)}finally{if(token===generation)loading=false}
 }
 function drawSelection(){
  mode='select';header('Was soll ins Brain?',`${row.title} · Stand ${row.revision} · ${selected.size} ausgewählt`);
  if(row.brain?.length){$('asset-keyboard').hidden=false;$('asset-keyboard').textContent='Brain-Status';$('asset-keyboard').onclick=()=>{jobs=row.brain.map(r=>({id:r.id,section:r.section}));drawStatus()}}
  const items=available(),grid=document.createElement('div');grid.className='asset-grid';page=Math.min(page,Math.max(0,Math.ceil(items.length/4)-1));
  for(const key of items.slice(page*4,page*4+4)){
   const tile=document.createElement('article');tile.className='asset-tile';
   const choose=button('',()=>{selected.has(key)?selected.delete(key):selected.add(key);drawSelection()});choose.className='asset-select';choose.setAttribute('aria-pressed',String(selected.has(key)));choose.setAttribute('aria-label',labels[key]+(selected.has(key)?' ausgewählt':' auswählen'));
   choose.append(node('strong',(selected.has(key)?'✓ ':'')+labels[key]),node('span',row.sections[key]));
   const read=button('Lesen',()=>{reading=key;drawReader()});read.setAttribute('aria-label',labels[key]+' lesen');tile.append(choose,read);grid.append(tile);
  }
  body.append(grid);pages(Math.ceil(items.length/4),page,p=>{page=p;drawSelection()});
  if(!items.length)body.append(node('p','Noch keine Texte vorhanden. Du kannst im Ergebnisdialog Inhalte ergänzen.'));
  message('Nur ausgewählte Texte werden als eigene Dokumente gespeichert. Chat und Audio bleiben außen vor.');
  next.textContent='Ziel wählen';next.disabled=!selected.size||Boolean(state?.live?.busy||state?.recording?.id);next.onclick=run(loadTargets);
  if(state?.live?.busy||state?.recording?.id)message('Zum Speichern zuerst das Gespräch oder die Aufnahme beenden. Du kannst die Ergebnisse bereits lesen.');
 }
 function drawReader(){
  mode='read';header(labels[reading],`${row.title} · Stand ${row.revision}`);
  const content=node('div',row.sections[reading]);content.className='asset-reader';body.append(content);
  back.textContent='Zur Auswahl';back.onclick=drawSelection;next.textContent='Text bearbeiten';next.onclick=run(async()=>{const id=row.id,key=reading;close();await window.studioWorkshop.inspect(id,key)});
 }
 async function loadTargets(){
  window.hideStudioKeyboard?.();const token=++generation;loading=true;mode='loading-target';header('Wissensbereich wählen','Deine Auswahl wird erst nach dem Speichern übertragen.');next.disabled=true;next.textContent='Bereiche werden geladen …';back.onclick=()=>{generation++;loading=false;drawSelection()};
  try{const list=await api('/api/cdb/areas');if(token!==generation)return;areas=list;query='';areaPage=0;
   const prior=(state?.live?.workshop_id===row.id?state.live.areas||[]:[]).filter(a=>areas.some(b=>b.id===a.id));
   const fallback=state?.cdb?.destination?.id;
   areaId=prior.length===1?prior[0].id:prior.length>1?null:areas.some(a=>a.id===fallback)?fallback:null;drawTargets();
  }catch(e){if(token===generation){mode='target-error';next.textContent='Erneut laden';next.disabled=false;next.onclick=run(loadTargets);message(e.message)}}finally{if(token===generation)loading=false}
 }
 function drawTargets(){
  mode='target';header('In welchem Wissensbereich?',`${selected.size} Textdokumente · ${row.title}`);
  const label=node('label','Bereich suchen'),search=document.createElement('input');search.type='search';search.id='asset-area-query';search.value=query;search.placeholder='Name des Wissensbereichs';label.htmlFor=search.id;body.append(label,search);
  const results=document.createElement('div');results.id='asset-area-results';body.append(results);
  search.oninput=()=>{query=search.value;areaPage=0;drawAreas()};$('asset-keyboard').textContent='Tastatur';$('asset-keyboard').onclick=()=>$('keyboard').click();
  back.textContent='Zur Auswahl';back.onclick=()=>{window.hideStudioKeyboard?.();drawSelection()};next.textContent=`${selected.size} Ergebnisse speichern`;next.onclick=run(publish);drawAreas();
 }
 function drawAreas(){
  const box=$('asset-area-results');box.replaceChildren();const filtered=areas.filter(a=>(a.label+' '+a.name).toLowerCase().includes(query.toLowerCase())),size=window.innerHeight<650?2:3;
  areaPage=Math.min(areaPage,Math.max(0,Math.ceil(filtered.length/size)-1));
  for(const a of filtered.slice(areaPage*size,areaPage*size+size)){const b=button((a.id===areaId?'✓ ':'')+(a.label||a.name),()=>{areaId=a.id;drawAreas()});b.setAttribute('aria-pressed',String(a.id===areaId));box.append(b)}
  if(!filtered.length)box.append(node('p','Kein passender Wissensbereich verfügbar.'));
  pages(Math.ceil(filtered.length/size),areaPage,p=>{areaPage=p;drawAreas()});
  next.disabled=!areaId||sending||Boolean(state?.live?.busy||state?.recording?.id);
  const a=areas.find(a=>a.id===areaId);message(a?'Ziel: '+(a.label||a.name)+' · KI-generierte Inhalte bleiben prüfpflichtig.':'Bitte genau einen Zielbereich auswählen. Gesprächswissen ist keine automatische Schreibfreigabe.');
 }
 async function publish(){
  if(sending)return;const token=++generation;sending=true;next.disabled=true;back.disabled=true;window.hideStudioKeyboard?.();message('Auswahl wird zur Übertragung vorgemerkt …');
  try{const result=await send({action:'brain-save',id:row.id,revision:row.revision,sections:[...selected],area_id:areaId});if(token!==generation)return;jobs=result.jobs;row=await send({action:'read',id:row.id});if(token!==generation)return;mode='status';drawStatus();await poll()}
  catch(e){if(token===generation){message(e.message+' Die Texte bleiben am Pi erhalten.');next.textContent='Auswahl neu prüfen';next.disabled=false;next.onclick=run(()=>open(row.id))}}
  finally{sending=false;back.disabled=false}
 }
 function drawStatus(){
  mode='status';header('Ergebnisse im Brain',row.title+' · Übertragungsbelege');
  const list=document.createElement('div');list.className='asset-status-list';
  for(const job of jobs){const receipt=(row.brain||[]).find(r=>r.id===job.id);const item=document.createElement('article');item.append(node('strong',labels[job.section]),node('span',receipt?states[receipt.state]||'Status unbekannt':'Status wird geladen …'));if(receipt)item.append(node('small',(receipt.area.label||receipt.area.name)+' · Stand '+receipt.revision+(receipt.error?' · '+receipt.error:'')));list.append(item)}
  body.append(list);next.textContent='Zur Ergebnisauswahl';next.onclick=drawSelection;
  const done=jobs.length&&jobs.every(j=>['completed','completed_without_graph'].includes(row.brain?.find(r=>r.id===j.id)?.state));
  message(done?'Alle ausgewählten Dokumente sind verarbeitet.':'Du kannst diesen Dialog schließen. Den aktuellen Status findest du später wieder bei den Ergebnissen.');
 }
 dialog.addEventListener('cancel',e=>{if(sending){e.preventDefault();message('Bitte die Bestätigung der Vormerkung abwarten.')}else{window.hideStudioKeyboard?.();generation++}});
 window.studioWorkshopAssets={open};
 $('asset-chat-open').onclick=run(()=>open(window.studioWorkshop.selected()||state.live.workshop_id));
 const baseRender=renderState;renderState=function(){baseRender();
  const key=JSON.stringify([state?.cdb?.identity,state?.cdb?.config?.server]);if(ownerKey&&key!==ownerKey){generation++;row=null;jobs=[];activeId=null;dialog.close();card.hidden=true}ownerKey=key;
  const id=window.studioWorkshop.selected(),draft=(state?.workshops||[]).find(r=>r.id===id),items=draft?.artifacts||[];
  card.hidden=!items.length;if(!card.hidden){$('asset-chat-title').textContent=`${items.length} Ergebnis${items.length===1?'':'se'} · Stand ${draft.revision}`;$('asset-chat-detail').textContent=items.map(a=>a.title).join(' · ')}
  if(state?.live?.busy)activeId=state.live.workshop_id;
  else if(activeId){const endedId=activeId;activeId=null;if(state.live.state==='ended'&&!document.querySelector('dialog[open]:not(.workspace-view)')&&$('live-view').open)open(endedId).catch(e=>notice(e.message))}
  if(dialog.open&&mode==='status'&&!loading&&!sending){const updated=JSON.stringify(state?.cdb?.publications);if(updated!==receiptKey){receiptKey=updated;loading=true;const token=generation;send({action:'read',id:row.id}).then(fresh=>{if(token===generation){row=fresh;drawStatus()}}).catch(e=>message(e.message)).finally(()=>{loading=false})}}
  if(dialog.open&&['select','target'].includes(mode)&&!sending&&!loading)next.disabled=!(mode==='select'?selected.size:areaId)||Boolean(state?.live?.busy||state?.recording?.id);
 };
})();
