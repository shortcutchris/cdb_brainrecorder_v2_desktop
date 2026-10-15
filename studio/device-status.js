/* Lightweight device feedback, independent of slow model/account setup. */
(() => {
 const feedback=document.createElement('section');feedback.id='wake-feedback';feedback.hidden=true;feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');feedback.innerHTML='<i aria-hidden="true"></i><div><strong>Hey Brain erkannt</strong><span id="wake-feedback-detail"></span></div>';document.body.append(feedback);
 const running=document.createElement('button');running.id='timer-running';running.hidden=true;running.type='button';running.innerHTML='<span id="running-timer-label"></span><strong id="running-timer-time"></strong>';running.onclick=()=>{if(!$('timers-open').disabled)$('timers-open').click()};document.body.append(running);
 const led=document.createElement('i');led.id='wake-rail-led';led.setAttribute('aria-hidden','true');$('live-open').append(led);
 const timerLabel=document.createElement('small');timerLabel.id='timer-countdown';$('timers-open').append(timerLabel);
 let fetching=false,lastWake=null,lastDetection=null,lastInstance=null,recognizedUntil=0;
 function renderWake(w){
  w=w||{};
  if(w.instance!==lastInstance){lastInstance=w.instance;lastDetection=null;recognizedUntil=0}
  const detection=w.detections;
  if(lastDetection!==null&&detection<lastDetection)return; // Older full-state poll after a fast detection.
  lastWake=w;
  if(detection!==lastDetection){lastDetection=detection;recognizedUntil=Date.now()+Math.min(8,Math.max(0,lastWake.recognized_for||0))*1000}
  if(!(lastWake.recognized_for>0))recognizedUntil=0;
  const recognized=Date.now()<recognizedUntil;
  const busy=Boolean(state?.recording?.id)||Boolean(state?.live?.busy);
  const connected=['listening','thinking','speaking','reconnecting','closing','ended','error'].includes(state?.live?.state);
  led.dataset.state=recognized&&!connected?'recognized':lastWake.enabled?(busy?'waiting':lastWake.state):'off';
  feedback.hidden=!recognized||Boolean(state?.recording?.id)||(!lastWake.testing&&connected);
  $('wake-feedback-detail').textContent=lastWake.testing?'Lokaler Test · kein Gespräch':state?.live?.state==='error'?'Start fehlgeschlagen · bitte im Gespräch prüfen':state?.live?.busy&&['listening','thinking','speaking'].includes(state.live.state)?'Du kannst sprechen': 'Gespräch wird verbunden …';
 }
 function renderDeviceStatus(){
  renderWake(state?.wake||lastWake);
  const items=state?.timers?.items||[],active=items.filter(i=>i.state==='scheduled').sort((a,b)=>a.remaining-b.remaining),due=items.filter(i=>i.state==='due'||i.state==='missed');
  const next=active[0],rail=$('timers-open');
  rail.dataset.timerState=due.length?'due':next?'running':'idle';
  const seconds=Math.max(0,next?.remaining||0),hours=Math.floor(seconds/3600),mins=Math.floor(seconds%3600/60),secs=seconds%60;
  const countdown=(hours?hours+':'+String(mins).padStart(2,'0'):String(mins).padStart(2,'0'))+':'+String(secs).padStart(2,'0');
  timerLabel.textContent=due.length?'Fällig':next?countdown:'';
  const title=due.length?due.length+' Alarm'+(due.length===1?'':'e')+' fällig':next?next.label+' · '+countdown+(active.length>1?' · +'+(active.length-1)+' weitere':''):'Timer & Erinnerungen';
  running.hidden=!next||Boolean(due.length);running.disabled=Boolean(rail.disabled);
  $('running-timer-label').textContent=next?(active.length>1?next.label+' · +'+(active.length-1):next.label):'';
  $('running-timer-time').textContent=countdown;running.setAttribute('aria-label','Timer läuft · '+title);
  document.body.classList.toggle('has-active-timer',!running.hidden);
  rail.title=title;rail.setAttribute('aria-label',title);
 }
 const previous=renderState;renderState=function(){previous();renderDeviceStatus()};renderDeviceStatus();
 setInterval(async()=>{
  if(Date.now()>=recognizedUntil)feedback.hidden=true;
  // Tiny memory-only endpoint. No file access, audio processing or model load.
  if(fetching||!online||document.hidden||!state?.wake?.enabled||state?.recording?.id)return;
  if(state?.live?.busy&&state.live.state!=='connecting')return;
  fetching=true;
  try{renderWake(await api('/api/wake/status'))}catch(_){feedback.hidden=true}finally{fetching=false}
 },300);
})();
