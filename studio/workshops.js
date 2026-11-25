/* Guided conversations and editable results; personal data stays account-bound. */
(() => {
 const labels={goal:'Ziel',questions:'Fragen',findings:'Erkenntnisse',ideas:'Ideen',decisions:'Entscheidungen',next_steps:'Nächste Schritte'};
 const phases={opening:'Ankommen',exploring:'Sammeln',grouping:'Ordnen',prioritizing:'Priorisieren',closing:'Abschließen'};
 const dialog=document.createElement('dialog');dialog.id='workshop-dialog';dialog.setAttribute('aria-labelledby','workshop-heading');
 dialog.innerHTML=`<header><div><h2 id="workshop-heading">Gesprächsformat</h2><p id="workshop-meta"></p></div><button id="workshop-keyboard" aria-label="Bildschirmtastatur öffnen">Tastatur</button></header><section id="workshop-body"></section><p id="workshop-message" role="status"></p><footer><button id="workshop-back">Schließen</button><button id="workshop-primary" class="primary" hidden></button></footer>`;
 document.body.append(dialog);$('workshop-keyboard').onclick=()=>$('keyboard').click();
 const open=document.createElement('button');open.id='workshop-open';open.textContent='Interview & Ideen';$('live-knowledge-open').after(open);
 let selected=null,row=null,section='goal',dirty=false,fetching=false,mode='choose',page=0,ownerKey='',savedKey='',sending=false,format='interview';
 const body=$('workshop-body'),primary=$('workshop-primary'),back=$('workshop-back');
 const send=payload=>api('/api/workshops',payload);
 const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n};
 function button(label,fn,cls=''){const b=text('button',label);b.className=cls;b.onclick=run(fn);return b}
 function message(value){$('workshop-message').textContent=value||''}
 function close(){window.hideStudioKeyboard?.();dialog.close()}
 function draft(){return (state?.workshops||[]).find(r=>r.id===selected)}
 async function read(){if(!selected||fetching)return;fetching=true;try{row=await send({action:'read',id:selected});savedKey=JSON.stringify([row.id,row.revision,row.composer]);if(dialog.open&&mode==='result'&&!dirty)drawResult()}finally{fetching=false}}
 async function openResult(id){selected=id;mode='result';dirty=false;row=null;message('Ergebnis wird geladen …');if(!dialog.open)dialog.showModal();await read()}
 function setupHeader(title,meta=''){ $('workshop-heading').textContent=title;$('workshop-meta').textContent=meta;body.replaceChildren();primary.hidden=true;back.textContent='Schließen';back.onclick=close;message('');dialog.dataset.mode=mode;$('workshop-keyboard').hidden=mode==='choose';}
 function choose(){
  mode='choose';setupHeader('Wie möchtest du arbeiten?','Ergebnisse bleiben für dein Brain-Konto gespeichert.');primary.hidden=false;primary.textContent='Freies Gespräch';primary.disabled=Boolean(state?.live?.busy);primary.onclick=()=>{selected=null;row=null;close()};
  const tiles=document.createElement('div');tiles.className='workshop-tiles';
  for(const [kind,title,detail] of [['interview','Interview','KAI fragt nach und hält Antworten fest.'],['brainstorming','Brainstorming','Ideen sammeln, ordnen und nächste Schritte klären.']]){
   const b=button('',()=>{format=kind;form()});b.append(text('strong',title),text('small',detail));b.disabled=Boolean(state?.live?.busy||state?.recording?.id);tiles.append(b)
  }body.append(tiles);
  const rows=state?.workshops||[],size=window.innerHeight<650?1:2;page=Math.min(page,Math.max(0,Math.ceil(rows.length/size)-1));if(rows.length){body.append(text('h3','Deine Ergebnisse'));const list=document.createElement('div');list.className='workshop-recent';for(const r of rows.slice(page*size,page*size+size))list.append(button(r.title+' · '+(r.format==='interview'?'Interview':'Brainstorming'),()=>openResult(r.id)));body.append(list);if(rows.length>size){const pages=document.createElement('div');pages.className='workshop-pages';const prev=button('Zurück',()=>{page--;choose()});prev.disabled=page===0;const next=button('Weiter',()=>{page++;choose()});next.disabled=(page+1)*size>=rows.length;pages.append(prev,text('span',`${page+1} / ${Math.ceil(rows.length/size)}`),next);body.append(pages)}}
 }
 function field(label,id,tag,value){const wrap=document.createElement('label');wrap.append(text('span',label));const input=document.createElement(tag);input.id=id;input.value=value;wrap.append(input);body.append(wrap);return input}
 function form(){
  mode='form';setupHeader(format==='interview'?'Interview vorbereiten':'Brainstorming vorbereiten','Wähle anschließend das Gesprächswissen und starte am Pi.');
  field('Titel','workshop-title','input',format==='interview'?'Mein Interview':'Unser Brainstorming').maxLength=120;
  field('Was soll am Ende klar sein?','workshop-goal','textarea','').maxLength=2000;
  const times=document.createElement('div');times.className='workshop-times';let minutes=10;for(const n of [5,10,15,20]){const b=button(n+' Minuten',()=>{minutes=n;for(const other of times.children)other.setAttribute('aria-pressed',String(other===b))});b.setAttribute('aria-pressed',String(n===minutes));times.append(b)}body.append(times);
  back.textContent='Zurück';back.onclick=choose;primary.hidden=false;primary.textContent='Format vorbereiten';primary.onclick=run(async()=>{
   if(sending)return;sending=true;primary.disabled=true;try{row=await send({action:'create',format,title:$('workshop-title').value,goal:$('workshop-goal').value,minutes});selected=row.id;await poll();window.hideStudioKeyboard?.();mode='result';drawResult()}catch(e){message(e.message)}finally{sending=false;primary.disabled=false}
  });
 }
 async function saveEdit(){if(!dirty||!row)return;const value=$('workshop-text').value;row=await send({action:'edit',id:row.id,revision:row.revision,section,text:value});dirty=false;window.hideStudioKeyboard?.();await poll();drawResult()}
 function drawResult(){
  if(!row)return;setupHeader(row.title,`${row.format==='interview'?'Interview':'Brainstorming'} · ${row.minutes} Minuten · ${phases[row.phase]} · Stand ${row.revision}`);
  const grid=document.createElement('div');grid.className='workshop-result';const nav=document.createElement('nav');nav.setAttribute('aria-label','Ergebnisbereiche');
  for(const [key,label] of Object.entries(labels)){const b=button(label,async()=>{if(dirty){message('Bitte deine Änderung zuerst übernehmen oder verwerfen.');return}section=key;drawResult()});b.setAttribute('aria-pressed',String(key===section));nav.append(b)}
  const pane=document.createElement('div');pane.className='workshop-editor';const label=text('label',labels[section]);label.htmlFor='workshop-text';const input=document.createElement('textarea');input.id='workshop-text';input.maxLength=6000;input.value=row.sections[section];input.placeholder='Hier erscheinen die Ergebnisse. Du kannst sie auch selbst ergänzen.';
  input.oninput=()=>{dirty=true;primary.textContent='Änderung übernehmen';primary.disabled=false;message('Noch nicht gespeichert. Andere Beiträge werden nicht überschrieben.');};
  pane.append(label,input);const transfer=text('p',row.composer.message);pane.append(transfer);
  if(row.composer.url){const a=text('a','Board im Composer öffnen ↗');a.href=row.composer.url;a.target='_blank';a.rel='noopener noreferrer';pane.append(a)}
  const actions=document.createElement('div');actions.className='workshop-actions';const publish=button('In Composer speichern',async()=>{if(dirty){message('Bitte Textänderung zuerst übernehmen.');return}publish.disabled=true;try{await send({action:'save',id:row.id,revision:row.revision});await poll();await read()}catch(e){message(e.message)}});publish.disabled=['saving','uncertain'].includes(row.composer.state);actions.append(publish);
  const active=Boolean(state?.live?.busy&&state.live.workshop_id===row.id);
  const control=button(active?'Gespräch pausieren':'Gespräch fortsetzen',async()=>{
   if(dirty){message('Bitte Textänderung zuerst übernehmen.');return}
   if(active){await window.studioWorkshopLive.pause();await poll();await read();if(!state?.live?.busy){row=await send({action:'pause',id:row.id,revision:row.revision});drawResult()}else message('Gespräch wird beendet. Dein Ergebnis bleibt erhalten.');}
   else{await window.studioWorkshopLive.prepare();close();workspaceView('live-view');notice('Gesprächswissen wählen und „Gespräch starten“ antippen. Dein bisheriges Ergebnis steht KAI für die Fortsetzung bereit.');}
  });control.disabled=Boolean(state?.recording?.id||(state?.live?.busy&&!active));actions.append(control);pane.append(actions);grid.append(nav,pane);body.append(grid);
  primary.hidden=false;primary.textContent='Änderung übernehmen';primary.disabled=!dirty;primary.onclick=run(async()=>{try{await saveEdit()}catch(e){message(e.message+' Dein Text bleibt im Feld.')}});
  back.textContent='Zurück zum Gespräch';back.onclick=()=>{if(dirty){message('Ungespeicherte Änderung: „Verwerfen“ oder „Übernehmen“ wählen.');back.textContent='Änderung verwerfen';back.onclick=()=>{dirty=false;close()};return}close()};
 }
 open.onclick=run(async()=>{if(!state?.cdb?.identity){notice('Bitte zuerst am Brain anmelden.');return}if(state?.live?.workshop_id&&state.live.busy)await openResult(state.live.workshop_id);else{choose();dialog.showModal()}});
 dialog.addEventListener('cancel',e=>{if(dirty){e.preventDefault();message('Bitte deine Änderung zuerst übernehmen oder verwerfen.');back.textContent='Änderung verwerfen';back.onclick=()=>{dirty=false;close()}}});
 window.studioWorkshop={selected:()=>selected,clear:()=>{selected=null},open:()=>open.click()};
 const baseRender=renderState;renderState=function(){baseRender();const key=JSON.stringify([state?.cdb?.identity,state?.cdb?.config?.server]);if(ownerKey&&key!==ownerKey){selected=null;row=null;dirty=false;savedKey='';page=0;dialog.close()}ownerKey=key;
  if(state?.live?.busy&&state.live.workshop_id)selected=state.live.workshop_id;
  open.textContent=selected?'Ergebnis & Format':'Interview & Ideen';open.disabled=Boolean(state?.recording?.id);
  const welcome=document.querySelector('.live-welcome h3');if(welcome)welcome.textContent=draft()?draft().title:'Worüber möchtest du sprechen?';
  const current=draft();const nextKey=current&&JSON.stringify([current.id,current.revision,current.composer]);if(dialog.open&&mode==='result'&&!dirty&&!fetching&&nextKey!==savedKey)read().catch(e=>message(e.message));
 };
})();
