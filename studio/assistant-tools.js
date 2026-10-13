/* Device-owned listening and durable timers. No transcript parsing or fake tool calls. */
(() => {
 const rail=document.createElement('button');rail.id='timers-open';rail.className='rail-button';rail.type='button';rail.title='Timer & Erinnerungen';rail.setAttribute('aria-label',rail.title);rail.innerHTML='<img src="/assets/timer.svg" alt=""><span>Timer</span><b id="timer-badge" hidden></b>';$('settings-open').before(rail);
 const view=document.createElement('dialog');view.id='timers-view';view.className='workspace-view';view.setAttribute('role','region');view.setAttribute('aria-labelledby','timers-heading');
 view.innerHTML=`<header class="dialog-heading"><h2 id="timers-heading">Timer & Erinnerungen</h2><span>Lokal auf diesem Pi</span></header>
 <section class="tools-content"><div class="tools-column"><div class="tools-switch"><button id="timer-kind" aria-pressed="true">Timer</button><button id="reminder-kind" aria-pressed="false">Erinnerung</button></div>
 <label>Titel<input id="timer-label" type="text" maxlength="80" value="Mein Timer" autocomplete="off"></label>
 <div id="timer-duration"><label>Dauer</label><div class="duration-choice"><button id="timer-less" aria-label="Dauer verringern">−</button><input id="timer-number" type="text" inputmode="numeric" value="5" maxlength="6" aria-label="Dauer"><button id="timer-more" aria-label="Dauer erhöhen">+</button><select id="timer-unit" aria-label="Zeiteinheit"><option value="60">Minuten</option><option value="1">Sekunden</option><option value="3600">Stunden</option></select></div><div class="timer-presets"><button data-minutes="5">5 Min.</button><button data-minutes="10">10 Min.</button><button data-minutes="30">30 Min.</button></div></div>
 <label id="reminder-date" hidden>Datum und Uhrzeit · Berlin<input id="timer-date" type="datetime-local"></label>
 <label>Alarmton<div class="timer-tone"><select id="timer-tone"><option value="bell">Glocke</option><option value="chime">Klangspiel</option><option value="pulse">Sanfter Puls</option><option value="silent">Lautlos</option></select><button id="timer-tone-test" type="button">Anhören</button></div></label>
 <div class="tools-info"><strong>Bleibt auch ohne Browser aktiv</strong><p>Ton nach Aufnahme / Gespräch. Einträge bleiben gespeichert.</p><p id="timer-clock"></p></div></div>
 <div class="tools-column"><div class="tools-list-heading"><h3>Deine Einträge</h3><button id="timer-history" aria-pressed="false">Verlauf</button></div><div id="timer-list"></div><p id="timer-message" role="status"></p></div></section>
 <footer class="tools-footer"><span>Gerätetimer · für alle am Pi sichtbar<br><span id="timer-voice">Sprachsteuerung wird beim Gesprächsstart geprüft.</span></span><nav id="timer-pages" class="direct-pages" aria-label="Timerseiten"></nav><button class="primary" id="timer-create">Timer starten</button></footer>`;document.body.append(view);
 const alarm=document.createElement('section');alarm.id='timer-alarm';alarm.hidden=true;alarm.setAttribute('aria-label','Fälliger Timer');alarm.innerHTML='<div><strong id="alarm-title" role="alert"></strong><small id="alarm-detail"></small></div><button id="alarm-snooze">+5 Min.</button><button id="alarm-ack">Erledigt</button>';document.body.append(alarm);
 const prevWorkspace=workspaceView;
 workspaceView=function(id=null){prevWorkspace(id);if(id!=='timers-view'&&view.open)view.close();rail.classList.toggle('active',id==='timers-view')};
 rail.onclick=run(async()=>{if(rail.disabled)return;await leaveDraft();audio.pause();workspaceView('timers-view');renderTools()});
 const toneName={bell:'Glocke',chime:'Klangspiel',pulse:'Puls',silent:'Lautlos'};
 let kind='timer',page=0,history=false,creating=false,signature='',alarmItem=null;
 function selectKind(next){kind=next;$('timer-kind').setAttribute('aria-pressed',String(kind==='timer'));$('reminder-kind').setAttribute('aria-pressed',String(kind==='reminder'));$('timer-duration').hidden=kind!=='timer';$('reminder-date').hidden=kind!=='reminder';$('timer-create').textContent=kind==='timer'?'Timer starten':'Erinnerung speichern';renderTools()}
 $('timer-kind').onclick=()=>selectKind('timer');$('reminder-kind').onclick=()=>selectKind('reminder');
 $('timer-less').onclick=()=>{$('timer-number').value=Math.max(1,(Number($('timer-number').value)||1)-1)};
 $('timer-more').onclick=()=>{$('timer-number').value=Math.min(604800,(Number($('timer-number').value)||0)+1)};
 document.querySelectorAll('[data-minutes]').forEach(b=>b.onclick=()=>{$('timer-number').value=b.dataset.minutes;$('timer-unit').value='60'});
 $('timer-history').onclick=()=>{history=!history;page=0;renderTools()};
 function closeKeyboard(){if(document.body.classList.contains('keyboard-open'))$('keyboard').click()}
 async function mutate(body){try{await api('/api/timers',body);$('timer-message').textContent='';await poll()}catch(e){$('timer-message').textContent=e.message;throw e}}
 $('timer-tone').onchange=()=>renderTools();
 $('timer-tone-test').onclick=run(async()=>{await api('/api/timers/tone',{tone:$('timer-tone').value});await poll()});
 $('timer-create').onclick=run(async()=>{if(creating)return;creating=true;renderTools();try{await mutate({action:'create',kind,tone:$('timer-tone').value,label:$('timer-label').value,seconds:Number($('timer-number').value)*Number($('timer-unit').value),local_time:$('timer-date').value,zone:'Europe/Berlin',request_id:crypto.randomUUID()});closeKeyboard();$('timer-message').textContent=kind==='timer'?'Timer läuft.':'Erinnerung gespeichert.';history=false;page=0}finally{creating=false;renderTools()}});
 async function change(item,action){if(item)await mutate({action,id:item.id,revision:item.revision})}
 $('alarm-ack').onclick=run(()=>change(alarmItem,'ack'));$('alarm-snooze').onclick=run(()=>change(alarmItem,'snooze'));
 function duration(seconds){return Math.floor(seconds/3600).toString().padStart(2,'0')+':'+Math.floor(seconds%3600/60).toString().padStart(2,'0')+':'+(seconds%60).toString().padStart(2,'0')}
 function renderTools(){
  const locked=Boolean(state?.recording?.id)||Boolean(state?.live?.busy);rail.disabled=!online||locked;
  if(view.open&&locked)workspaceView(state?.live?.busy?'live-view':null);
  const items=state?.timers?.items||[],due=items.filter(i=>i.state==='due'||i.state==='missed');alarmItem=due[0];
  $('timer-badge').hidden=!due.length;$('timer-badge').textContent=due.length;
  alarm.hidden=!alarmItem;document.body.classList.toggle('has-timer-alarm',Boolean(alarmItem));
  if(alarmItem){$('alarm-title').textContent=alarmItem.label;$('alarm-detail').textContent=(due.length>1?due.length+' fällig · ':'')+(alarmItem.state==='missed'?'Während Abwesenheit fällig':locked?'Ton nach Aufnahme / Gespräch':alarmItem.sound==='failed'?'Lautsprecher nicht erreichbar':'Zeit ist um');$('alarm-ack').disabled=!online;$('alarm-snooze').disabled=!online}
  $('timer-tone-test').disabled=!online||locked||$('timer-tone').value==='silent'||state?.speaker_test?.state==='running';
  $('timer-voice').textContent=state?.timers?.voice_available?'Sprachsteuerung im aktuellen Gespräch verbunden.':'Sprachsteuerung wird beim Gesprächsstart geprüft.';
  $('timer-create').disabled=!online||creating||locked||(kind==='reminder'&&!state?.timers?.clock_ready);
  $('timer-clock').textContent=state?.timers?.clock_ready?'Gerätezeit synchronisiert.':'Uhrzeit wird geprüft. Datierte Erinnerungen warten.';
  $('timer-history').setAttribute('aria-pressed',String(history));
  const rows=items.filter(i=>history?['done','cancelled'].includes(i.state):!['done','cancelled'].includes(i.state));
  const count=Math.max(1,Math.ceil(rows.length/3));page=Math.min(page,count-1);
  const key=JSON.stringify([rows.map(({remaining,...row})=>row),page,online]);
  if(signature!==key){signature=key;const list=$('timer-list');list.replaceChildren();
   for(const item of rows.slice(page*3,page*3+3)){
    const row=document.createElement('article');row.className='timer-row';const copy=document.createElement('div'),title=document.createElement('strong'),detail=document.createElement('span');title.textContent=item.label;
    detail.dataset.timerId=item.id;detail.textContent=item.state==='scheduled'?(item.kind==='timer'?duration(item.remaining):new Date(item.due*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin',dateStyle:'short',timeStyle:'short'})):({due:'Jetzt fällig',missed:'Verpasst',done:'Erledigt',cancelled:'Abgebrochen'}[item.state]);detail.textContent+=' · '+(toneName[item.tone]||'Glocke');copy.append(title,detail);row.append(copy);
    if(!history){const b=document.createElement('button');b.textContent=item.state==='scheduled'?'Abbrechen':'Erledigt';b.disabled=!online;b.onclick=run(()=>change(item,item.state==='scheduled'?'cancel':'ack'));row.append(b)}list.append(row);
   }
   if(!rows.length){const empty=document.createElement('p');empty.className='tools-info';empty.textContent=history?'Noch keine erledigten Einträge.':'Noch keine Timer. Links kannst du einen starten.';list.append(empty)}
   drawPageNumbers($('timer-pages'),count,page,i=>{page=i;signature='';renderTools()});
  }
  for(const el of document.querySelectorAll('[data-timer-id]')){const item=items.find(i=>i.id===el.dataset.timerId);if(item?.state==='scheduled'&&item.kind==='timer')el.textContent=duration(item.remaining)+' · '+(toneName[item.tone]||'Glocke')}
  const w=state?.wake||{};$('wake-state').textContent=w.message||'Status wird geprüft.';$('wake-state').dataset.state=w.state||'off';$('wake-count').textContent=w.testing?'Lokaler Test · '+w.detections+' Erkennungen':'Nur aktiv, wenn Aufnahme, Gespräch und Wiedergabe beendet sind.';
  $('wake-toggle').textContent=w.enabled?'Aktivierungswort ausschalten':'Aktivierungswort einschalten';$('wake-toggle').setAttribute('aria-pressed',String(Boolean(w.enabled)));$('wake-toggle').disabled=!online||(!w.enabled&&(!w.available||locked));$('wake-test').disabled=!online||locked||!w.available;$('wake-test').textContent=w.testing?'Test beenden':'Erkennung testen';
  if(w.enabled||w.testing){$('start-background').textContent=w.state==='listening'?'Bereit für „Okay Nabu“':w.testing?'Aktivierungswort · lokaler Test':'Aktivierungswort · pausiert';$('live-open').title=w.state==='listening'?'Live-Gespräch · bereit für Okay Nabu':'Live-Gespräch · Aktivierungswort pausiert'}else $('live-open').title='Live-Gespräch';
  if(state?.live?.busy&&state.live.owner_kind==='device'&&!$('live-view').open){closeKeyboard();audio.pause();workspaceView('live-view')}
 }
 async function wake(action){await api('/api/wake',{action});await poll()}
 $('wake-toggle').onclick=run(()=>wake(state?.wake?.enabled?'off':'on'));$('wake-test').onclick=run(()=>wake(state?.wake?.testing?'test-stop':'test'));$('audio-wake').onclick=()=>showSettingsDetail('wake-page');
 // Every browser audio path yields the local detector before it emits sound.
 const client=crypto.randomUUID();let playbackBusy=false;
 const playing=()=>[...document.querySelectorAll('audio')].some(el=>!el.paused&&!el.ended);
 async function playbackPulse(){if(playbackBusy||!online)return;playbackBusy=true;try{await api('/api/playback',{client,playing:playing()})}finally{playbackBusy=false}}
 document.addEventListener('play',event=>{const el=event.target;if(!(el instanceof HTMLAudioElement)||el.dataset.wakeGranted==='yes')return;el.pause();api('/api/playback',{client,playing:true}).then(()=>{el.dataset.wakeGranted='yes';return el.play()}).catch(e=>notice(e.message))},true);
 document.addEventListener('pause',event=>{if(event.target instanceof HTMLAudioElement)event.target.dataset.wakeGranted=''},true);
 setInterval(()=>{if(playing())playbackPulse().catch(()=>{document.querySelectorAll('audio').forEach(el=>el.pause())})},2000);
 const previous=renderState;renderState=function(){previous();renderTools()};renderTools();
})();
