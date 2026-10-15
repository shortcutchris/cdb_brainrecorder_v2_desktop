/* Wake setup stays on one touch page. Cloud lookups occur on entry/refresh only. */
(() => {
 let setup=null,chosen=new Set(),owner=null,serial=0,loading=false,saving=false,error='',page=0,selectedOnly=false,signature='';
 const ownerKey=()=>JSON.stringify([state?.cdb?.identity||null,state?.cdb?.config?.server||null]);
 const name=a=>a.label||a.name||'Unbenannter Bereich';
 const audioName=value=>(value||'').replace(/,?\s*(?:USB Audio\s+)?Hardware device.*$/i,'').trim();
 const locked=()=>Boolean(state?.recording?.id||state?.live?.busy);
 const max=()=>Math.min(8,Math.max(1,Number(setup?.max_areas)||8));
 const text=(id,value)=>{if($(id).textContent!==value)$(id).textContent=value};
 const disabled=(id,value)=>{value=Boolean(value);if($(id).disabled!==value)$(id).disabled=value};
 function reset(){setup=null;chosen.clear();owner=ownerKey();serial++;loading=false;error='';page=0;selectedOnly=false;signature='';$('wake-area-search').value=''}
 async function load(){
  if(locked()||saving)return;
  if(owner!==ownerKey())reset();
  const request=++serial,key=ownerKey();loading=true;error='';render();
  try{
   if(!state?.cdb?.identity){setup=null;chosen.clear();return}
   const result=await api('/api/live/setup');if(request!==serial||key!==ownerKey())return;
   setup=result;const available=new Set(result.areas.map(a=>a.id));
   // A default is not consent: only a previously saved selection is preselected.
   chosen=new Set((result.remembered_area_ids||[]).filter(id=>available.has(id)));page=0;
  }catch(e){if(request===serial&&key===ownerKey()){setup=null;chosen.clear();error=e.message}}
  finally{if(request===serial){loading=false;render()}}
 }
 function render(){
  if(owner!==ownerKey())reset();
  const w=state?.wake||{},busy=locked(),frozen=!online||loading||saving||busy||w.enabled||w.testing;
  const identity=state?.cdb?.identity,server=state?.cdb?.config?.server||'';
  text('wake-account',identity?(identity.name||'Firmenkonto')+' · '+(server.includes('staging.')?'Staging':server.replace(/^https?:\/\//,'')):'Noch nicht angemeldet');
  text('wake-audio',loading?'Geräte werden geprüft …':setup?.audio?.available?(audioName(setup.audio.microphone_label)||'Mikrofon')+' → '+(audioName(setup.audio.speaker_label)||'Lautsprecher'):setup?.audio?.message||'Nach Anmeldung prüfen');
  text('wake-word',w.word||'Hey Brain');
  if(!saving)$('wake-phrase').value=w.phrase||'hey-brain';
  disabled('wake-phrase',frozen);
  text('wake-state',!w.enabled&&!w.testing?'Aktivierungswort ausgeschaltet.':w.message||'Bereitschaft wird geprüft.');$('wake-state').dataset.state=w.state||'off';
  text('wake-count',w.testing?'Lokaler Test · '+w.detections+' Erkennungen':'Nur aktiv, wenn Aufnahme, Gespräch und Wiedergabe beendet sind.');
  const hint=error||(saving?'Auswahl wird gespeichert …':loading?'Wissensbereiche werden geladen …':!identity?'Melde dich zuerst bei deinem Brain-Konto an.':!w.available?'Die lokale Aktivierungswort-Erkennung ist noch nicht installiert.':busy?'Aufnahme oder Gespräch läuft. Bitte zuerst beenden.':w.enabled?'Aktiv. Zum Ändern von Rufwort oder Wissen zuerst ausschalten.':w.testing?'Lokaler Erkennungstest läuft. Es wird kein Gespräch gestartet.':!setup?'Bitte Wissensbereiche aktualisieren.':!setup.enabled?'Voice One ist für dieses Brain-Konto nicht freigeschaltet.':!setup.audio?.available?'Bitte Mikrofon und Lautsprecher unter Audio einrichten.':!chosen.size?'Wähle mindestens einen Wissensbereich. Danach kannst du einschalten.':'Bereit. Beim Einschalten wird diese Auswahl für dein Brain-Konto gespeichert.');
  text('wake-hint',hint);text('wake-toggle',w.enabled?'Aktivierungswort ausschalten':'Aktivierungswort einschalten');$('wake-toggle').setAttribute('aria-pressed',String(Boolean(w.enabled)));
  disabled('wake-toggle',!online||saving||(!w.enabled&&(loading||busy||w.testing||!identity||!w.available||!setup?.enabled||!setup?.audio?.available||!chosen.size)));
  disabled('wake-test',!online||saving||busy||!w.available);text('wake-test',w.testing?'Test beenden':'Erkennung testen');
  disabled('wake-refresh',loading||saving||busy||!online||w.enabled||w.testing);
  disabled('wake-account-open',busy||saving||w.enabled||w.testing);disabled('wake-audio-open',busy||saving||w.enabled||w.testing);
  disabled('wake-area-search',frozen);disabled('wake-selected',loading||saving);
  text('wake-selected','Ausgewählt ('+chosen.size+')');$('wake-selected').setAttribute('aria-pressed',String(selectedOnly));
  const query=$('wake-area-search').value.trim().toLocaleLowerCase('de');
  const all=(setup?.areas||[]).filter(a=>(!selectedOnly||chosen.has(a.id))&&name(a).toLocaleLowerCase('de').includes(query));
  const size=document.body?.classList.contains('keyboard-open')?1:window.innerHeight>=820?3:2,count=Math.max(1,Math.ceil(all.length/size));page=Math.min(page,count-1);
  const key=JSON.stringify([all,Array.from(chosen),page,size,frozen,max(),loading]);
  if(key!==signature){signature=key;const list=$('wake-areas');list.replaceChildren();
   for(const area of all.slice(page*size,(page+1)*size)){
    const b=document.createElement('button');b.className='wake-area';b.type='button';b.textContent=name(area);b.setAttribute('aria-pressed',String(chosen.has(area.id)));b.disabled=frozen||(!chosen.has(area.id)&&chosen.size>=max());
    b.onclick=()=>{if(locked()||state?.wake?.enabled||state?.wake?.testing||loading||saving||!online)return;if(chosen.has(area.id))chosen.delete(area.id);else if(chosen.size<max())chosen.add(area.id);error='';render()};list.append(b);
   }
   if(!all.length){const empty=document.createElement('p');empty.className='wake-empty';empty.textContent=loading?'Wird geladen …':selectedOnly?'Noch keine Bereiche ausgewählt.':query?'Keine passenden Bereiche.':'Noch keine Wissensbereiche geladen.';list.append(empty)}
   drawPageNumbers($('wake-area-pages'),count,page,i=>{page=i;render()});
  }
  $('wake-areas').style?.setProperty('--wake-rows',size);
  text('wake-area-count',chosen.size+' / '+max()+' gewählt · Seite '+(page+1)+' / '+count);
 }
 async function action(kind,phrase){
  if(saving||!online)return;const key=ownerKey();saving=true;error='';render();
  try{
   if(kind==='on'){
    if(locked()||!setup?.enabled||!setup.audio?.available||!chosen.size)throw new Error('Bitte zuerst Konto, Audio und Wissensbereiche prüfen.');
    await api('/api/live/areas',{account_key:setup.selection_account_key,area_ids:[...chosen]});
    if(key!==ownerKey())throw new Error('Brain-Konto geändert. Bitte Bereiche erneut laden.');
    window.dispatchEvent(new Event('brain-areas-changed'));
   }
   if(key!==ownerKey())throw new Error('Brain-Konto geändert. Bitte erneut prüfen.');
   if(kind==='phrase'&&(locked()||state?.wake?.enabled||state?.wake?.testing))throw new Error('Zum Wechseln zuerst ausschalten.');
   await api('/api/wake',{action:kind,...(kind==='phrase'?{phrase}: {})});await poll();
  }catch(e){error=e.message}
  finally{saving=false;render()}
 }
 $('wake-phrase').onchange=()=>action('phrase',$('wake-phrase').value);
 $('wake-area-search').oninput=()=>{page=0;render()};$('wake-selected').onclick=()=>{selectedOnly=!selectedOnly;page=0;render()};
 $('wake-toggle').onclick=()=>action(state?.wake?.enabled?'off':'on');$('wake-test').onclick=()=>action(state?.wake?.testing?'test-stop':'test');
 $('wake-refresh').onclick=load;$('wake-account-open').onclick=()=>showSettingsDetail('connection-page');$('wake-audio-open').onclick=()=>showSettingsDetail('audio-home');
 $('audio-wake').onclick=()=>showSettingsDetail('wake-page');
 const beforeDetail=showSettingsDetail;showSettingsDetail=function(id){beforeDetail(id);if(id==='wake-page'&&!$('wake-page').hidden)load()};
 const beforeRender=renderState;renderState=function(){beforeRender();render()};render();
})();
