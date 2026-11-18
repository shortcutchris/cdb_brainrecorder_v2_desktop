/* Optional physical mode controls share the recorder's existing state/actions. */
(() => {
 let pending=false,error='';
 function render(){
  const n=state?.nfc||{},busy=Boolean(state?.recording?.id||state?.live?.busy),locked=pending||!online||busy;
  $('nfc-banner').hidden=!n.enabled;
  $('nfc-banner').textContent=n.enabled?'NFC · '+(n.message||'Bereitschaft prüfen.') : '';
  $('nfc-state').textContent=error||n.message||'NFC ausgeschaltet.';
  $('nfc-next').textContent=busy?'Einrichtung nach der Aufnahme oder dem Gespräch möglich.':n.enabled?'Aufsteller bereit. Zum Ändern zuerst NFC ausschalten.':!n.can_enroll?'Lege einen Aufsteller auf und tippe auf „Leser prüfen“.':'Aufsteller erkannt. Ordne ihm Gespräch oder Meeting zu.';
  $('nfc-assigned').textContent=['talk','meeting'].map(k=>k.toUpperCase()+': '+(n.assigned?.[k]?'zugeordnet':'noch offen')).join(' · ');
  $('nfc-toggle').textContent=n.enabled?'NFC ausschalten':'NFC einschalten';
  $('nfc-toggle').setAttribute('aria-pressed',String(Boolean(n.enabled)));
  $('nfc-toggle').disabled=locked||(!n.enabled&&(!n.assigned?.talk||!n.assigned?.meeting));
  $('nfc-inspect').disabled=locked;
  for(const mode of ['talk','meeting'])$('nfc-'+mode).disabled=locked||n.enabled||!n.can_enroll;
 }
 async function act(action,mode){
  pending=true;error='';render();
  try{await api('/api/nfc',{action,...(mode?{mode}: {})});await poll()}
  catch(e){error=e.message}finally{pending=false;render()}
 }
 $('audio-nfc').onclick=()=>showSettingsDetail('nfc-page');
 $('nfc-inspect').onclick=()=>act('inspect');
 for(const mode of ['talk','meeting'])$('nfc-'+mode).onclick=()=>act('enroll',mode);
 $('nfc-toggle').onclick=()=>act(state?.nfc?.enabled?'off':'on');
 const before=renderState;renderState=function(){before();render()};render();
})();
