/* One hierarchy and fixed action slots across settings destinations. */
function renderSettingsTrail(){
 const detail=$('settings').dataset.overview!=='true',page=$('settings').dataset.detail;
 const parent=['asr-page','llm-page'].includes(page)?{page:'ai-page',label:'KI & Modelle'}:page==='brain-page'?{page:'connection-page',label:'Brain-Konto'}:['audio-page','speaker-page','bluetooth-page','wake-page'].includes(page)?{page:'audio-home',label:'Audio'}:null;
 $('settings-overview-back').textContent='Einstellungen';$('settings-overview-back').hidden=!detail;
 $('settings-root-separator').hidden=!detail;
 $('settings-parent-back').hidden=!detail||!parent;$('settings-parent-separator').hidden=!detail||!parent;
 $('settings-parent-back').textContent=parent?.label||'';$('settings-parent-back').onclick=()=>{if(!state?.recording.id&&parent)showSettingsDetail(parent.page)};
}
function renderBrainIdentity(){
 const c=state?.cdb;if(!c)return;
 const signed=Boolean(c.identity),pending=c.login.state==='pending';
 $('brain-signin-state').textContent=signed?'Angemeldet':pending?'Anmeldung läuft':'Nicht angemeldet';
 $('brain-signin-state').dataset.connected=String(signed);
 $('brain-user-name').textContent=signed?(c.identity.name||'Firmenkonto'):'Noch nicht verbunden';
 $('brain-instance').textContent=c.config.server==='https://staging.cdbos.de'?'CDB · Staging':c.config.server==='https://cdbos.de'?'CDB · Produktion':'Brain-Umgebung';
 $('brain-instance-host').textContent=c.config.server.replace(/^https:\/\//,'');
}
const beforeSettingsTrailDetail=showSettingsDetail;
showSettingsDetail=function(page){if(state?.recording.id)return;beforeSettingsTrailDetail(page);renderSettingsTrail()};
const beforeSettingsTrailOverview=showSettingsOverview;
showSettingsOverview=function(){if(state?.recording.id)return;beforeSettingsTrailOverview();renderSettingsTrail()};
$('settings-overview-back').onclick=()=>showSettingsOverview();
const beforeSettingsIdentityState=renderState;
renderState=function(){beforeSettingsIdentityState();renderBrainIdentity();renderSettingsTrail()};
renderBrainIdentity();renderSettingsTrail();
