/* Direct settings destinations, with a calm tile overview on entry. */
function showSettingsOverview(){
 if(state?.recording.id)return;
 $('settings').dataset.overview='true';$('settings-heading').textContent='Einstellungen';
 $('settings-overview-back').hidden=true;renderSettingsOverview();
}
function showSettingsDetail(page){
 if(state?.recording.id)return;
 const target=document.querySelector('[data-settings="'+page+'"]');
 if(target)target.click();
}
function renderSettingsOverview(){
 if(!state)return;
 const ready=Boolean(state.config.setup_complete);
 $('finish-setup').hidden=ready;
 $('setup-overview-status').textContent=ready?'Dein Recorder ist eingerichtet.':'Beginne mit dem Mikrofon und schließe die Einrichtung ab.';
 $('setup-overview-action').textContent='Audio einrichten';$('setup-overview-action').hidden=ready;
 $('setup-overview-action').disabled=!online||Boolean(state.recording.id);
}
document.querySelectorAll('[data-settings]').forEach(button=>{
 const select=button.onclick;
 button.onclick=()=>{
  if(state?.recording.id)return;
  select();$('settings').dataset.overview='false';
  $('settings-heading').textContent=button.textContent;
  $('settings-overview-back').hidden=false;
 };
});
document.querySelectorAll('[data-settings-tile]').forEach(button=>button.onclick=()=>showSettingsDetail(button.dataset.settingsTile));
$('settings-overview-back').onclick=showSettingsOverview;
$('setup-overview-action').onclick=run(async()=>{if(state?.recording.id)return;if(state?.config.setup_complete)await showRecorder();else showSettingsDetail('audio-page')});
$('mic-settings').onclick=run(async()=>{await openSettings();showSettingsDetail('audio-page')});
for(const button of document.querySelectorAll('.rail-button')){
 const label=button.querySelector('span')?.textContent;
 if(label){button.setAttribute('aria-label',label);button.title=label}
}
renderSettingsOverview();
// Long prompt text has explicit text pages; the surrounding settings page stays put.
const promptPages=document.createElement('nav');promptPages.className='direct-pages prompt-text-pages';promptPages.setAttribute('aria-label','Arbeitsauftrag Textseiten');
$('prompts-page').querySelector('.dialog-actions').prepend(promptPages);
let promptPageSignature='';
function renderPromptPages(){
 const el=$('prompt-text');if(!el.getClientRects().length)return;
 const step=Math.max(48,el.clientHeight*.8),max=Math.max(0,el.scrollHeight-el.clientHeight),count=max>2?Math.ceil(max/step)+1:1,current=Math.min(count-1,Math.round(el.scrollTop/step));
 const signature=[count,current,el.clientHeight,el.value].join('|');if(signature===promptPageSignature)return;promptPageSignature=signature;
 drawPageNumbers(promptPages,count,current,i=>{el.scrollTop=Math.min(max,i*step);promptPageSignature='';renderPromptPages()});
}
$('prompt-text').addEventListener('scroll',renderPromptPages,{passive:true});$('prompt-text').addEventListener('input',renderPromptPages);new ResizeObserver(renderPromptPages).observe($('prompt-text'));setInterval(renderPromptPages,500);

function renderQueueMenu(){
 if(!state)return;
 const jobs=queueJobs(),count=jobs.filter(j=>j.state!=='recording').length;
 $('queue-badge').textContent=count>99?'99+':String(count);$('queue-badge').hidden=count===0;
 $('queue-toggle').title='Warteschlange · '+$('phase').textContent+(count?' · '+count+' Aufträge':'');
 $('queue-toggle').classList.toggle('active',$('queue-region').open);
 $('queue-toggle').disabled=Boolean(state.recording.id);
 $('activity-icon').hidden=!state.recording.id&&!jobs.some(j=>['transcribing','summarizing','importing','failed'].includes(j.state))&&state.installation?.state!=='running'&&!['queued','transcribing','summarizing'].includes(state.model_test?.state);
 $('queue-toggle').classList.toggle('has-errors',jobs.some(j=>j.state==='failed'));
}
const renderBeforeQueueMenu=renderState;renderState=function(){renderBeforeQueueMenu();renderQueueMenu()};

