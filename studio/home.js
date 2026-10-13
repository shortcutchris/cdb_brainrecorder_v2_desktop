/* Home is a destination, not an alternate recorder. Existing routes own their locks. */
(() => {
 const rail=document.createElement('button');rail.id='start-open';rail.className='rail-button';rail.type='button';rail.title='Startseite';rail.setAttribute('aria-label','Startseite');rail.innerHTML='<img src="/assets/house.svg" alt=""><span>Startseite</span>';$('home').before(rail);
 const view=document.createElement('dialog');view.id='start-view';view.className='workspace-view';view.setAttribute('role','region');view.setAttribute('aria-labelledby','start-heading');
 view.innerHTML='<header class="dialog-heading"><h2 id="start-heading">Dein Brain. Ein Ort für alles.</h2><span class="start-heading-label">Startseite</span></header><section class="start-content"><p class="start-intro">Was möchtest du machen?</p><div id="start-tiles" class="start-tiles"></div></section><footer class="start-footer"><div class="start-device-status"><i id="start-led" aria-hidden="true"></i><span id="start-status" role="status">Verbindung wird aufgebaut …</span></div><span id="start-background"></span></footer>';document.body.append(view);
 const destinations=[
  {id:'recorder',target:'home',icon:'waveform',title:'Aufnehmen',copy:'Gedanken und Meetings festhalten',featured:true},
  {id:'live',target:'live-open',icon:'users',title:'Live-Gespräch',copy:'Mit deinem Wissen sprechen',featured:true},
  {id:'library',target:'library-open',icon:'folder',title:'Bibliothek',copy:'Aufnahmen, Notizen und Ergebnisse'},
  {id:'queue',target:'queue-toggle',icon:'list',title:'Warteschlange',copy:'Verarbeitung im Blick behalten'},
  {id:'display',target:'display-open',icon:'monitor',title:'Bildschirm',copy:'Gespräch auf einem zweiten Display'},
  {id:'settings',target:'settings-open',icon:'gear',title:'Einstellungen',copy:'Konto, Modelle und Geräte verwalten'}
 ];
 for(const item of destinations){
  const button=document.createElement('button');button.id='start-'+item.id;button.type='button';button.className='start-tile';button.dataset.featured=String(Boolean(item.featured));button.setAttribute('aria-label',item.title);button.innerHTML='<span class="start-tile-top"><img src="/assets/'+item.icon+'.svg" alt=""><span aria-hidden="true">↗</span></span><strong>'+item.title+'</strong><span class="start-tile-copy">'+item.copy+'</span>';
  button.onclick=run(async()=>{if(button.disabled||rail.disabled)return;$(item.target).click()});$('start-tiles').append(button);
 }
 let initial=true,navigated=false;
 const previousWorkspace=workspaceView;
 workspaceView=function(id=null){previousWorkspace(id);navigated=true;if(id!=='start-view'&&view.open)view.close();const active=id==='start-view';rail.classList.toggle('active',active);rail.setAttribute('aria-current',active?'page':'false')};
 rail.onclick=run(async()=>{if(rail.disabled)return;await leaveDraft();audio.pause();workspaceView('start-view');renderHome()});
 function renderHome(){
  // Recorder's disabled state also includes Live's local connecting/closing transitions.
  const locked=Boolean(state?.recording?.id)||Boolean($('home').disabled);
  rail.disabled=!state||locked;rail.title=locked?'Aufnahme oder Gespräch läuft · zuerst beenden':'Startseite';
  for(const item of destinations)$('start-'+item.id).disabled=!state||locked||Boolean($(item.target).disabled);
  const readiness=typeof currentReadiness==='function'?currentReadiness():{tone:'waiting',label:'Status wird geprüft'};
  $('start-led').dataset.state=readiness.tone;$('start-status').textContent=readiness.label;
  const count=state?(state.jobs||[]).filter(j=>['queued','transcribing','summarizing','importing'].includes(j.state)).length:0;
  $('start-background').textContent=count?count+(count===1?' Auftrag':' Aufträge')+' in der Verarbeitung':'Verarbeitung im Hintergrund';
  if(view.open&&state?.live?.busy)workspaceView('live-view');
  if(initial&&state&&online){initial=false;if(!navigated){if(state.live?.busy)workspaceView('live-view');else if(!locked)workspaceView('start-view')}}
 }
 const previousRender=renderState;renderState=function(){previousRender();renderHome()};renderHome();
})();
