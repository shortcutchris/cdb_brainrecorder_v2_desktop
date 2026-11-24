/* Composition only: actions retain the existing guarded handlers. */
(() => {
 const setText=(id,text)=>{const el=$(id);if(el&&el.textContent!==text)el.textContent=text};
 // Feedback is actionable text, not supplementary header copy to truncate.
 $('queue-status').after($('queue-feedback'));
 for(const button of document.querySelectorAll('[data-nfc-panel]'))button.onclick=()=>{
  const setup=button.dataset.nfcPanel==='setup';
  $('nfc-setup').hidden=!setup;$('nfc-behavior').hidden=setup;
  $('nfc-talk').hidden=$('nfc-meeting').hidden=!setup;
  document.querySelectorAll('[data-nfc-panel]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
 };
 // Keep output controls and test result together; supporting explanations unfold.
 const columns=$('speaker-page').querySelectorAll('.audio-check-column');
 if(columns.length===2){
  const test=columns[0],status=columns[1];test.prepend(status.querySelector('.speaker-connection'));
  const links=document.createElement('div');links.className='sound-links';
  links.append($('speaker-announcements'),$('speaker-device-sounds'));
  $('speaker-page').querySelector('.audio-input-column').append(links);
  const details=document.createElement('details');details.innerHTML='<summary>Wiedergabe & Aufnahme</summary>';
  for(const card of [...status.querySelectorAll('.settings-card')])if(card.textContent.trim())details.append(card);
  test.append(details);status.remove();
 }
 // Power controls are daily actions; administration has a separate disclosure.
 const content=$('management-page').querySelector('.settings-content'),old=content.firstElementChild;
 const power=document.createElement('div');power.className='device-power-actions';
 for(const [id,title,detail] of [['management-restart','Pi neu starten','Beenden und wieder hochfahren.'],['management-shutdown','Pi ausschalten','Sicher herunterfahren und umstellen.']]){
  const b=$(id);b.replaceChildren();const strong=document.createElement('strong'),small=document.createElement('span');strong.textContent=title;small.textContent=detail;b.append(strong,small);power.append(b);
 }
 const block=document.createElement('p');block.id='management-power-reason';block.setAttribute('role','status');
 const setup=document.createElement('details');setup.className='management-setup';setup.innerHTML='<summary>Einrichten & warten · Gerätekopplung</summary>';
 setup.append(old);old.lastElementChild.append($('management-pair'));content.append(power,block,setup);
 const status=document.createElement('button');status.textContent='Gerätestatus';status.onclick=()=>showSettingsDetail('status-page');$('management-page').querySelector('.dialog-actions').append(status);
 for(const prefix of ['asr','llm']){
  const steps=document.createElement('div');steps.className='model-steps';steps.id=prefix+'-steps';$(prefix+'-page').querySelector('.model-controls').prepend(steps);
 }
 $('connections-display').onclick=()=>{if(!$('display-open').disabled)$('display-open').click()};
 $('lcd-help-open').onclick=run(async()=>{if(!allowed('configure'))return;await flushAllDrafts();if(allowed('configure'))location.href='/help/index.html#timer'});
 function render(){
  if(!state)return;
  if($('settings').open&&!$('status-page').hidden)loadSpeakers();
  setText('management-power-reason',$('management-restart').disabled?($('management-restart').title||'Geräteaktion läuft. Bitte warten.'):'Aufnahmen und Einstellungen bleiben erhalten. Vor dem Ausschalten wird nochmals bestätigt.');
  for(const prefix of ['asr','llm']){
   const next=['login','install','test','activate'].find(a=>$(prefix+'-'+a).dataset.next==='true');
   setText(prefix+'-steps',next==='login'?'1 · Auswählen → Brain anmelden':next==='install'?'1 · Auswählen → Herunterladen':next==='test'?'2 · Prüfen → Modell testen':next==='activate'?'3 · Aktivieren → Für neue Aufnahmen verwenden':'Auswählen → Prüfen → Aktivieren');
  }
  const lcd=state.lcd_status||{},nfc=state.nfc||{},display=state.display||{},portal=state.portal||{};
  setText('accessory-lcd',lcd.message||'USB-Status noch nicht verfügbar');setText('lcd-status-detail',lcd.message||'USB-Status noch nicht verfügbar.');
  setText('accessory-nfc',nfc.message||'Noch nicht eingerichtet');
  setText('accessory-display',display.message||((display.receivers||[]).length?'Browser verbunden':'Browser am Pi koppeln'));
  setText('accessory-portal',portal.enabled?'Fernbedienung eingeschaltet':'Hilfe verfügbar · Fernbedienung ausgeschaltet');
  setText('accessory-mobile',state.remote_control?.message||'Persönliche Verbindung in cdbMOBILE einrichten');
  $('connections-display').disabled=$('display-open').disabled;
  const rows=[['Version','Recorder Studio '+state.version],['Verbindung',online?'Mit diesem Pi verbunden':'Pi nicht erreichbar'],['Netzwerk',portal.ip_urls?.join(' · ')||portal.url||'Keine Netzwerkadresse gemeldet'],['Freier Speicher',Number.isFinite(state.free_mb)?(state.free_mb/1024).toFixed(1)+' GB':'Wird geprüft'],['Mikrofon',state.config?.device_label||state.config?.device||'Unter Audio auswählen und testen'],['Lautsprecher',$('speaker-state').textContent||'Unter Audio prüfen'],['USB-Timerdisplay',lcd.message||'Wird geprüft'],['NFC',nfc.message||'Nicht eingerichtet']];
  const signature=JSON.stringify(rows),health=$('device-health');if(health.dataset.signature!==signature){health.dataset.signature=signature;health.replaceChildren();for(const [label,value] of rows){const item=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);item.append(dt,dd);health.append(item)}}
 }
 const previous=renderState;renderState=function(){previous();render()};render();
})();
