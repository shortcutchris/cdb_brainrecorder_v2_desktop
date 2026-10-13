/* The external display can read chat only; Studio retains all control. */
(() => {
 const rail=document.createElement('button');rail.id='display-open';rail.className='rail-button';rail.type='button';rail.title='Bildschirm';rail.setAttribute('aria-label','Bildschirm');rail.innerHTML='<img src="/assets/monitor.svg" alt=""><span>Bildschirm</span>';$('settings-open').before(rail);
 const view=document.createElement('dialog');view.id='display-view';view.className='workspace-view';view.setAttribute('role','region');view.setAttribute('aria-labelledby','display-heading');view.innerHTML='<header class="dialog-heading"><h2 id="display-heading">Bildschirm</h2><span>Gespräch teilen</span></header>';
 const page=$('display-page');view.append(...page.children);page.remove();document.body.append(view);
 const previousWorkspace=workspaceView;
 workspaceView=function(id=null){previousWorkspace(id);if(id!=='display-view'&&view.open)view.close();rail.classList.toggle('active',id==='display-view');rail.setAttribute('aria-current',id==='display-view'?'page':'false')};
 rail.onclick=run(async()=>{if(rail.disabled)return;await leaveDraft();audio.pause();workspaceView('display-view');renderDisplay()});
 let request=false;
 function renderDisplay(){
  if(view.open&&state?.live?.busy)workspaceView('live-view');
  rail.disabled=!online||Boolean(state?.recording?.id)||Boolean($('home').disabled);
  const d=state?.display||{},locked=!online||!state?.capabilities?.configure?.allowed||request;
  $('display-url').textContent=d.url||'Adresse wird geladen …';
  $('display-status').textContent=!d.enabled?'Freigabe ausgeschaltet':d.connected?'Bildschirm verbunden':d.paired?'Verbindung unterbrochen':d.pending?'Wartet auf den Kopplungscode':'Bereit zum Koppeln';
  $('display-status').dataset.connected=String(Boolean(d.connected));
  $('display-name').textContent=d.name||'Noch kein Bildschirm gekoppelt.';
  $('display-enable').textContent=d.enabled?'Freigabe ausschalten':'Freigabe einschalten';$('display-enable').disabled=locked;
  $('display-code').disabled=locked||!d.enabled||!state?.cdb?.identity;
  $('display-pair').disabled=locked||!d.enabled||!state?.cdb?.identity||!/^\d{6}$/.test($('display-code').value);
  $('display-revoke').disabled=!online||request||!d.paired;
 }
 async function act(action){if(request)return;request=true;$('display-message').textContent='';renderDisplay();try{await api(action==='revoke'?'/api/display/revoke':'/api/display/control',{action,code:$('display-code').value});if(action==='pair'){$('display-code').value='';if(document.body.classList.contains('keyboard-open'))$('keyboard').click();$('display-message').textContent='Gekoppelt. Dein Gespräch erscheint jetzt auf dem Bildschirm.'}await poll()}catch(e){$('display-message').textContent=e.message}finally{request=false;renderDisplay()}}
 $('display-enable').onclick=()=>act(state?.display?.enabled?'disable':'enable');$('display-pair').onclick=()=>act('pair');$('display-revoke').onclick=()=>act('revoke');$('display-code').oninput=renderDisplay;
 const before=renderState;renderState=function(){before();renderDisplay()};renderDisplay();
})();
