/* Optional physical mode controls share the recorder's existing state/actions. */
(() => {
 let pending=false,error='';
 function render(){
  const n=state?.nfc||{},busy=Boolean(state?.recording?.id||state?.live?.busy),locked=pending||!allowed('configure')||busy;
  for(const [mode,id] of [['meeting','nfc-banner'],['talk','live-nfc-hint']]){
   const hint=$(id),active=n.active_mode===mode&&(mode==='meeting'?Boolean(state?.recording?.id):Boolean(state?.live?.busy));
   hint.hidden=!active;
   hint.textContent=n.state==='error'?'NFC · Leser prüfen, am Bildschirm beenden':n.stop_on_remove?.[mode]===false?'NFC · Am Bildschirm beenden':'NFC · Abnehmen beendet '+(mode==='meeting'?'Aufnahme':'Gespräch');
   hint.title=n.message||'';
  }
  $('nfc-state').textContent=error||n.message||'NFC ausgeschaltet.';
  $('nfc-next').textContent=busy?'Einrichtung nach der Aufnahme oder dem Gespräch möglich.':n.enabled?'Aufsteller bereit. Zum Neuzuordnen zuerst NFC ausschalten.':!n.can_enroll?'Lege einen Aufsteller auf und tippe auf „Leser prüfen“.':'Aufsteller erkannt. Ordne ihm Gespräch oder Meeting zu.';
  $('nfc-assigned').textContent=['talk','meeting'].map(k=>k.toUpperCase()+': '+(n.assigned?.[k]?'zugeordnet':'noch offen')).join(' · ');
  $('nfc-toggle').textContent=n.enabled?'NFC ausschalten':'NFC einschalten';
  $('nfc-toggle').setAttribute('aria-pressed',String(Boolean(n.enabled)));
  $('nfc-toggle').disabled=locked||(!n.enabled&&(!n.assigned?.talk||!n.assigned?.meeting));
  $('nfc-inspect').disabled=locked;
  for(const mode of ['talk','meeting'])$('nfc-'+mode).disabled=locked||n.enabled||!n.can_enroll;
  for(const mode of ['talk','meeting']){
   const button=$('nfc-direct-'+mode),direct=Boolean(n.direct_start?.[mode]);
   button.disabled=locked||!online;
   button.setAttribute('aria-pressed',String(direct));
   button.textContent=direct?'Direktstart ein':'Direktstart aus';
   const stop=$('nfc-stop-'+mode),automatic=n.stop_on_remove?.[mode]!==false;
   stop.disabled=locked||!online;
   stop.setAttribute('aria-pressed',String(automatic));
   stop.textContent=automatic?'Beenden beim Abnehmen ein':'Beenden beim Abnehmen aus';
  }
 }
 async function act(action,mode,enabled){
  if(pending||!allowed('configure'))return;
  pending=true;error='';render();
  try{await api('/api/nfc',{action,...(mode?{mode}: {}),...(typeof enabled==='boolean'?{enabled}:{})});await poll()}
  catch(e){error=e.message}finally{pending=false;render()}
 }
 $('audio-nfc').onclick=()=>showSettingsDetail('nfc-page');
 $('nfc-inspect').onclick=()=>act('inspect');
 for(const mode of ['talk','meeting'])$('nfc-'+mode).onclick=()=>act('enroll',mode);
 for(const mode of ['talk','meeting'])$('nfc-direct-'+mode).onclick=()=>act('direct-start',mode,!state?.nfc?.direct_start?.[mode]);
 for(const mode of ['talk','meeting'])$('nfc-stop-'+mode).onclick=()=>act('stop-on-remove',mode,state?.nfc?.stop_on_remove?.[mode]===false);
 $('nfc-toggle').onclick=()=>act(state?.nfc?.enabled?'off':'on');
 const before=renderState;renderState=function(){before();render()};render();
})();
