/* A timer stays device-owned; this dialog only views and explicitly changes it. */
(() => {
 const dialog=document.createElement('dialog');dialog.id='timer-focus';
 dialog.setAttribute('aria-labelledby','timer-focus-title');
 dialog.innerHTML=`<header class="timer-focus-heading"><div><span id="timer-focus-status"></span><h2 id="timer-focus-title"></h2></div><button id="timer-focus-close" aria-label="Timer minimieren"><img src="/assets/x.svg" alt=""></button></header>
 <section class="timer-focus-body"><div id="timer-focus-time" aria-label="Verbleibende Zeit"></div><p id="timer-focus-detail"></p><p id="timer-focus-context"></p><p id="timer-focus-error" role="status"></p></section>
 <footer class="timer-focus-actions"><button id="timer-focus-secondary"><img id="timer-focus-secondary-icon" src="/assets/timer.svg" alt=""><strong id="timer-focus-secondary-label"></strong><small id="timer-focus-secondary-detail"></small></button><button id="timer-focus-primary"><img src="/assets/stop.svg" alt=""><strong id="timer-focus-primary-label"></strong><small id="timer-focus-primary-detail"></small></button></footer>`;
 document.body.append(dialog);
 let selected=null,displayed=null,pending=false,error='',origin=null;
 const dismissed=new Set(),isDue=item=>['due','missed'].includes(item?.state),key=item=>item.id+':'+item.revision;
 const items=()=>state?.timers?.items||[];
 const otherModal=()=>[...document.querySelectorAll('dialog[open]:not(.workspace-view)')].some(d=>d!==dialog);
 function close(){selected=null;displayed=null;error='';dialog.close();if(origin?.isConnected)origin.focus();origin=null}
 function minimize(){
  if(pending)return;
  // A minimized alarm stays reachable but does not reopen on every state poll.
  for(const item of items().filter(isDue))dismissed.add(key(item));
  close();
 }
 function open(id){
  const item=items().find(i=>i.id===id);if(!item||pending)return;
  if(!dialog.open)origin=document.activeElement;
  selected=id;error='';window.hideStudioKeyboard?.();
  if(!dialog.open)dialog.showModal();
  draw(item);$('timer-focus-close').focus();
 }
 window.openTimerFocus=open;
 $('timer-focus-close').onclick=minimize;
 dialog.oncancel=event=>{event.preventDefault();minimize()};
 function countdown(seconds){
  const n=Math.max(0,Math.ceil(Number(seconds)||0)),h=Math.floor(n/3600);
  return (h?String(h).padStart(2,'0')+':':'')+String(Math.floor(n%3600/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
 }
 function draw(item){
  displayed={...item};const due=isDue(item),running=item.state==='scheduled',finished=!due&&!running;
  dialog.dataset.state=due?'due':running?'running':'finished';
  $('timer-focus-title').textContent=item.label;
  $('timer-focus-status').textContent=due?(item.state==='missed'?'Timer verpasst':'Zeit ist um'):running?(item.kind==='reminder'?'Erinnerung':'Timer läuft'):item.state==='done'?'Timer erledigt':'Timer beendet';
  $('timer-focus-time').textContent=running?countdown(item.remaining):'00:00';
  $('timer-focus-detail').textContent=due?(item.tone==='silent'?'Dieser Timer ist lautlos. Bestätige ihn oder verlängere ihn um fünf Minuten.':state?.recording?.id&&item.sound==='pending'?'Der Ton wartet bis nach der Aufnahme.':item.sound==='failed'?'Der Alarmton konnte nicht abgespielt werden. Bitte hier bestätigen.':'Bestätige den Timer oder verlängere ihn um fünf Minuten.'):running?(item.kind==='reminder'?new Date(item.due*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin',dateStyle:'medium',timeStyle:'short'}):'Dein Timer läuft auf dem Pi weiter, auch in der kleinen Ansicht.'):'Diesen Eintrag findest du weiterhin im Verlauf.';
  $('timer-focus-context').textContent=state?.recording?.id?'Deine Aufnahme läuft weiter.':state?.live?.busy?'Dein Gespräch bleibt verbunden.':'';
  $('timer-focus-error').textContent=error||(!online?'Verbindung zum Pi unterbrochen. Beenden ist nach Wiederverbindung möglich.':'');
  $('timer-focus-secondary-label').textContent=due?'+5 Minuten':finished?'Schließen':'Minimieren';
  $('timer-focus-secondary-detail').textContent=due?'Erneut in fünf Minuten erinnern.':finished?'Zur vorherigen Ansicht.':'Klein anzeigen und weiterlaufen lassen.';
  $('timer-focus-secondary-icon').src='/assets/'+(due?'timer':'x')+'.svg';
  $('timer-focus-primary-label').textContent=pending?'Wird gespeichert …':due?'Alarm stoppen':item.kind==='reminder'?'Erinnerung löschen':'Timer beenden';
  $('timer-focus-primary-detail').textContent=due?'Bestätigen und Alarm ausschalten.':'Diesen Timer vorzeitig stoppen.';
  $('timer-focus-primary').hidden=finished;
  $('timer-focus-primary').disabled=pending||!online;
  $('timer-focus-secondary').disabled=pending||(due&&!online);
  $('timer-focus-close').disabled=pending;
 }
 async function act(secondary){
  if(pending||!displayed)return;
  const target={...displayed},due=isDue(target);
  if((secondary&&!due)||!['scheduled','due','missed'].includes(target.state)){minimize();return}
  if(!online)return;
  const action=secondary?'snooze':due?'ack':'cancel';pending=true;error='';draw(target);
  try{
   await api('/api/timers',{action,id:target.id,revision:target.revision});
   if(selected===target.id)close();
   await poll();
  }catch(e){error=e.message;await poll()}
  finally{pending=false;renderFocus()}
 }
 $('timer-focus-secondary').onclick=()=>act(true);
 $('timer-focus-primary').onclick=()=>act(false);
 function renderFocus(){
  const rows=items(),due=rows.filter(isDue);
  for(const old of dismissed)if(!due.some(i=>key(i)===old))dismissed.delete(old);
  if(selected&&!rows.some(i=>i.id===selected))close();
  // Do not cover an in-flight confirmation or login. Reconsider on the next poll.
  const next=due.find(i=>!dismissed.has(key(i)));
  if(!pending&&next&&!otherModal()&&(!dialog.open||!isDue(rows.find(i=>i.id===selected))))open(next.id);
  const item=rows.find(i=>i.id===selected);
  if(dialog.open&&item)draw(item);
 }
 const previous=renderState;renderState=function(){previous();renderFocus()};renderFocus();
})();
