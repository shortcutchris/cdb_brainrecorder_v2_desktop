/* Voice opens views. Audio tests and power still require deliberate touch. */
(() => {
 const dialog=document.createElement('dialog');dialog.id='voice-action';dialog.setAttribute('aria-labelledby','voice-action-title');
 dialog.innerHTML='<header><div><small>GERÄTEBEGLEITER</small><h2 id="voice-action-title"></h2></div></header><section id="voice-action-content"></section><p id="voice-action-error" role="status"></p><footer><button id="voice-action-secondary"><strong></strong><small></small></button><button id="voice-action-primary"><strong></strong><small></small></button></footer>';
 document.body.append(dialog);
 let current=null,busy=false,error='',shown=new Set(),opening=false,drawKey='';
 const content=$('voice-action-content'),primary=$('voice-action-primary'),secondary=$('voice-action-secondary');
 function text(tag,value){const n=document.createElement(tag);n.textContent=value;return n}
 function button(node,title,detail,fn,disabled=false){node.hidden=false;node.querySelector('strong').textContent=title;node.querySelector('small').textContent=detail;node.onclick=fn;node.disabled=disabled||busy||!online}
 async function send(action){if(!current)return;return api('/api/voice-ui/action',{id:current.id,action})}
 async function perform(action){if(busy)return;busy=true;error='';draw();try{await send(action);await poll()}catch(e){error=e.message}finally{busy=false;draw()}}
 async function dismiss(){if(busy)return;try{await send('dismiss')}catch(e){notice(e.message)}finally{current=null;dialog.close()}}
 dialog.oncancel=e=>{e.preventDefault();dismiss()};
 function powerBlocked(){return Boolean(state?.activity?.busy||state?.recording?.id||state?.jobs?.some(j=>busyStates.includes(j.state))||state?.timers?.items?.some(i=>['scheduled','due'].includes(i.state))||state?.cdb?.publications?.some(p=>['queued','accepted','sending'].includes(p.state))||!audio.paused)}
 function draw(){
  if(!current||!dialog.open)return;
  const context=current.name==='show_device_clock'?state?.device_clock:current.name.startsWith('prepare_')?[state?.live?.busy,state?.live?.state,state?.speaker_test,state?.capabilities?.configure,powerBlocked()]:null;
  const nextKey=JSON.stringify([current.id,current.stage,busy,online,error,context]);
  if(nextKey===drawKey)return;drawKey=nextKey;
  const row=current,live=Boolean(state?.live?.busy);content.replaceChildren();dialog.dataset.kind=row.name;
  primary.hidden=true;button(secondary,'Schließen','Zurück zum Gespräch oder zur vorherigen Ansicht.',dismiss);
  $('voice-action-error').textContent=error||(!online?'Verbindung zum Pi unterbrochen. Aktionen sind gesperrt.':'');
  if(row.name==='show_device_clock'){
   $('voice-action-title').textContent='Uhr';const clock=text('div',state.device_clock?.text||'--:--');clock.className='voice-clock';content.append(clock,text('p',state.device_clock?.ready?'Ortszeit des Pi. Timer laufen weiter; fällige Alarme haben Vorrang.':'Die Uhrzeit des Pi ist noch nicht abgeglichen.'));
  }else if(row.name==='open_device_help'){
   const a=row.data.article;$('voice-action-title').textContent=a.title;content.append(text('p',a.intro));
   if(a.note)content.append(text('p',a.note));
   const list=document.createElement('ol');for(const step of a.steps||[])list.append(text('li',step));content.append(list);
   for(const p of a.paragraphs||[])content.append(text('p',p));
  }else if(row.name==='check_meeting_readiness'){
   $('voice-action-title').textContent='Bereit fürs Meeting?';
   for(const check of row.data.checks){const item=text('p',({'ok':'✓ ',attention:'! ',unknown:'? '})[check.state]+check.label+' · '+({ok:'In Ordnung',attention:'Prüfen',unknown:'Unbekannt'})[check.state]);item.className='voice-check';content.append(item)}
   content.append(text('p',row.data.activity_reason||'Bedienstatus zum Zeitpunkt der Abfrage: frei.'),text('p','Momentaufnahme, kein Hör- oder Aufnahmetest. Es wurde keine Aufnahme gestartet.'));
  }else if(row.name==='prepare_speaker_test'){
   $('voice-action-title').textContent='Lautsprecher prüfen';
   if(live){content.append(text('p','Für einen eindeutigen Hörtest zuerst das Gespräch beenden. Danach kannst du den Testton am Display starten.'));button(primary,'Gespräch beenden','Noch keinen Testton abspielen.',()=>perform('end_talk'),state.live.state==='closing');button(secondary,'Im Gespräch bleiben','Hörtest abbrechen.',dismiss)}
   else if(row.stage==='offered'){content.append(text('p','Der Pi spielt einen kurzen Testton: zuerst links, dann rechts. Danach bestätigst du, ob er aus der eingebauten Soundbar hörbar war.'));if(!allowed('configure'))content.append(text('p',state.capabilities?.configure?.reason||'Gerät ist beschäftigt.'));button(primary,'Testton starten','Aktuelle Lautstärke beibehalten.',()=>perform('start_test'),!allowed('configure'))}
   else if(row.stage==='testing'){
    const test=state.speaker_test||{};
    if(test.state==='completed'){content.append(text('p','War der Testton aus dem gewünschten Lautsprecher gut hörbar? Die Software kann das nicht selbst hören.'));button(secondary,'Nein, nicht gehört','Audioanschluss und Lautstärke prüfen.',()=>perform('not_heard'));button(primary,'Ja, gehört','Hörtest ausdrücklich bestätigen.',()=>perform('heard'))}
    else content.append(text('p',test.state==='running'?'Testton läuft …':test.message||'Der Test konnte nicht abgeschlossen werden. Bitte erneut anfordern.'));
   }else content.append(text('p',row.stage==='heard'?'Du hast bestätigt: Testton hörbar.':'Kein hörbarer Testton bestätigt. Bitte unter Einstellungen → Audio den Ausgang, Lautstärke und Anschluss prüfen.'));
  }else if(row.name==='prepare_device_move'){
   $('voice-action-title').textContent='Gerät zum Umstellen vorbereiten';
   content.append(text('p','Aufnahmen, Verarbeitung, Übertragungen und Timer zuerst abschließen. Gespeicherte Inhalte bleiben erhalten. Den Strom erst nach vollständigem Herunterfahren trennen.'));
   if(live){button(primary,'Gespräch beenden','Danach den Gerätestatus prüfen.',()=>perform('end_talk'),state.live.state==='closing');button(secondary,'Weiterarbeiten','Vorbereitung abbrechen.',dismiss)}
   else{
    const blocked=powerBlocked();content.append(text('p',blocked?'Noch beschäftigt: laufende Vorgänge oder offene Timer zuerst abschließen.':'Keine laufenden Vorgänge im angezeigten Status. Vor dem Ausschalten wird erneut geprüft.'));
    button(primary,'Zum Ausschalten','Öffnet die abschließende Bestätigung.',async()=>{
     if(busy||powerBlocked())return;busy=true;
     try{await flushAllDrafts();await send('dismiss');current=null;dialog.close();await $('management-shutdown').onclick()}catch(e){notice(e.message)}finally{busy=false}
    },blocked);
   }
  }
 }
 async function render(){
  const row=state?.voice_ui;
  if(current&&(!row||row.id!==current.id)){current=null;dialog.close()}
  if(current&&!dialog.open){shown.delete(current.id);current=null}
  if(current){current=row;draw();return}
  if(!row||shown.has(row.id)||opening||!online)return;
  // Never cover login, save dialogs, confirmations or an unacknowledged alarm.
  const other=[...document.querySelectorAll('dialog[open]:not(.workspace-view)')].find(d=>d!==dialog&&!(d.id==='timer-focus'&&!['due','missed'].includes(d.dataset.state)));
  if(other)return;
  opening=true;
  try{
   window.minimizeTimerFocus?.();window.hideStudioKeyboard?.();
   if(row.name==='show_device_timer'){
    window.openTimerFocus?.(row.data.timer_id);
    if(!$('timer-focus')?.open)return;
   }else{current=row;error='';drawKey='';dialog.showModal();draw();secondary.focus()}
   await api('/api/voice-ui/action',{id:row.id,action:'shown'});shown.add(row.id);
   if(shown.size>100)shown=new Set([...shown].slice(-50));
  }catch(e){error=e.message;draw()}finally{opening=false}
 }
 const previous=renderState;renderState=function(){previous();render()};render();
})();
