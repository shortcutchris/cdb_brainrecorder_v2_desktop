/* Explicit model drafts: browsing never changes a provider or active model. */
let providerDraft=null,brainReturn=null,lastDirectCheck='';
const checkPages={asr:0,llm:0};let resultCheckId='';
function modelStage(prefix){return prefix==='asr'?'transcription':'summary'}
function draftProvider(stage){return providerDraft?.[stage]||state?.cdb?.config[stage]||'local'}
function activeModelLabel(prefix){
 const stage=modelStage(prefix);if(state?.cdb?.config[stage]==='cdb')return 'Brain · Unternehmensstandard';
 const value=state?.config[prefix==='asr'?'whisper_model':'summary_model'];
 const model=catalog?.[prefix==='asr'?'asr':'llm']?.find(m=>(prefix==='asr'?m.path:m.id)===value);
 return 'Auf dem Pi · '+(model?.label||String(value||'Nicht eingerichtet').split('/').pop());
}
function modelSelection(prefix){const backend=prefix==='asr'?'whisper':'ollama';return {stage:modelStage(prefix),provider:draftProvider(modelStage(prefix)),model:chosenModel(backend)?.id}}
function checkMatches(prefix){const t=state?.model_check,s=modelSelection(prefix);return t&&t.stage===s.stage&&t.provider===s.provider&&(s.provider==='cdb'?Boolean(state.cdb.identity&&t.binding&&t.binding.server===state.cdb.config.server&&t.binding.user_id===state.cdb.identity.user_id&&t.binding.client_id===state.cdb.identity.client_id):t.model===s.model)}
function renderModelChoices(){
 if(!state?.cdb)return;
 $('brain-tile-status').textContent=state.cdb.identity?'Angemeldet · '+(state.cdb.destination?.label||'Standardbereich wählen'):'Mit Microsoft anmelden';
 $('ai-tile-status').textContent='Transkription: '+(state.cdb.config.transcription==='cdb'?'Brain':'Pi')+' · Zusammenfassung: '+(state.cdb.config.summary==='cdb'?'Brain':'Pi');
 $('ai-asr-active').textContent=activeModelLabel('asr');$('ai-llm-active').textContent=activeModelLabel('llm');
 $('cdb-logout').textContent=state.cdb.login.state==='pending'?'Anmeldung abbrechen':'Abmelden';$('cdb-logout').hidden=!state.cdb.identity&&state.cdb.login.state!=='pending';
 $('brain-transfers').hidden=!state.cdb.identity;$('brain-models').textContent=brainReturn?'Zur Modellwahl zurück':'KI-Verarbeitung einrichten';
 const t=state.model_check;
 if(t?.state==='running'){document.body.classList.add('working');$('phase').textContent='Modelltest · '+t.label;$('activity-icon').hidden=false;$('activity-icon').src='/assets/circle-notch.svg';$('queue-toggle').title='Modelltest läuft · '+t.label}
 if(t&&t.state!==lastDirectCheck){lastDirectCheck=t.state;if(['completed','failed'].includes(t.state)&&$('settings').open)loadSetup().catch(e=>notice(e.message))}
 for(const prefix of ['asr','llm']){
  const stage=modelStage(prefix),cloud=draftProvider(stage)==='cdb',backend=prefix==='asr'?'whisper':'ollama',m=chosenModel(backend),match=checkMatches(prefix),busy=t?.state==='running';
  $(prefix==='asr'?'cdb-transcription':'cdb-summary').value=draftProvider(stage);
  $(prefix+'-active').textContent=activeModelLabel(prefix);
  $(prefix==='asr'?'local-asr-settings':'local-summary-settings').hidden=cloud;
  $(prefix==='asr'?'local-asr-actions':'local-summary-actions').hidden=cloud;
  $(prefix==='asr'?'cdb-asr-info':'azure-summary-info').hidden=!cloud;
  $(prefix==='asr'?'cdb-asr-status':'azure-summary-status').textContent=state.cdb.identity?'Brain-Konto verbunden.':'Bitte mit Microsoft beim Brain anmelden.';
  const current=state.cdb.config[stage]===draftProvider(stage)&&(cloud||Boolean(m&&(prefix==='asr'?m.path===state.config.whisper_model:m.id===state.config.summary_model)));
  const tested=cloud?match&&t.state==='completed':m?.tested;
  const box=$(prefix+'-info');box.hidden=cloud;box.replaceChildren();
  if(m&&!cloud){const p=document.createElement('p');p.textContent=(m.installed?'Installiert':'Download: '+(m.bytes/1e9).toFixed(2)+' GB')+' · '+(m.tested?'Gerätetest bestanden':'Noch kein bestandener Gerätetest')+' · '+(current?'Bereits aktiv':'Nur ausgewählt');box.append(p);if(m.source){const a=document.createElement('a');a.href=m.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent=(m.license||'Lizenz')+' · Modellquelle ansehen';box.append(a)}}
  const reason=!allowed('model_test')?(state.capabilities.model_test.reason||'Verbindung unterbrochen. Bitte warten.'):!cloud&&catalog?.test_block_reason?catalog.test_block_reason:!cloud&&!m?.installed?'Zuerst herunterladen.':!cloud&&!(prefix==='asr'?catalog?.whisper_runtime:catalog?.ollama)?'Lokale Laufzeit unter Gerät & Diagnose prüfen.':!cloud&&m?.candidate&&!m.runtime_compatible?'Laufzeit dieses Modells noch nicht bestätigt.':cloud&&!state.cdb.identity?'Zuerst beim Brain anmelden.':'';
  $(prefix+'-install').hidden=Boolean(m?.installed);$(prefix+'-install').disabled=!allowed('install')||!m||m.installed||m.id==='custom';
  $(prefix+'-test').disabled=Boolean(reason)||busy;$(prefix+'-test').textContent=match&&busy?'Test läuft …':'Modell testen';
  $(prefix+'-login').hidden=!cloud||Boolean(state.cdb.identity);
  $(prefix+'-activate').disabled=!allowed('configure')||!tested||current;
  $(prefix+'-activate').textContent=current?'Bereits aktiv':'Für neue Aufnahmen verwenden';
  $(prefix+'-check-status').textContent=match?(current&&t.state==='completed'?'Test erfolgreich · Bereits aktiv.':t.message)+(t.seconds!==undefined?' · '+t.seconds+' s':''):reason||'Ein Beispieltest prüft diese Auswahl, ohne deine aktiven Modelle zu ändern.';
  $(prefix+'-check-status').classList.toggle('is-working',Boolean(match&&busy));
  $(prefix+'-result-box').hidden=!match||!t.result;const result=match?t.result||'':'';if(t?.id!==resultCheckId){resultCheckId=t?.id;checkPages.asr=checkPages.llm=0}
  const count=Math.max(1,Math.ceil(result.length/360));checkPages[prefix]=Math.min(checkPages[prefix],count-1);$(prefix+'-result').textContent=result.slice(checkPages[prefix]*360,(checkPages[prefix]+1)*360);drawPageNumbers($(prefix+'-result-pages'),count,checkPages[prefix],i=>{checkPages[prefix]=i;renderModelChoices()});
 }
}
// Keep the candidate selection on this page; provider changes need explicit use().
for(const [id,prefix] of [['cdb-transcription','asr'],['cdb-summary','llm']])$(id).onchange=()=>{providerDraft||={...state.cdb.config};providerDraft[modelStage(prefix)]=$(id).value;renderModelChoices()};
for(const prefix of ['asr','llm']){
 $(prefix+'-test').onclick=run(async()=>{await api('/api/models/check',modelSelection(prefix));await poll()});
 $(prefix+'-activate').onclick=run(async()=>{await api('/api/models/use',modelSelection(prefix));await poll();await loadSetup()});
 $(prefix+'-login').onclick=()=>{brainReturn=prefix==='asr'?'asr-page':'llm-page';showSettingsDetail('connection-page')};
}
$('brain-models').onclick=()=>{const page=brainReturn||'ai-page';brainReturn=null;showSettingsDetail(page)};
$('brain-transfers').onclick=()=>showSettingsDetail('brain-page');
document.querySelectorAll('[data-ai-page]').forEach(b=>b.onclick=()=>showSettingsDetail(b.dataset.aiPage));
const originalShowSettingsDetail=showSettingsDetail;
showSettingsDetail=function(page){originalShowSettingsDetail(page);$('settings').dataset.detail=page;$('settings-overview-back').textContent=['asr-page','llm-page'].includes(page)?'KI & Modelle':page==='brain-page'?'Brain-Konto':'Alle Einstellungen';renderModelChoices()};
$('settings-overview-back').onclick=()=>{const page=$('settings').dataset.detail;if(['asr-page','llm-page'].includes(page))showSettingsDetail('ai-page');else if(page==='brain-page')showSettingsDetail('connection-page');else showSettingsOverview()};
const originalModelInfo=renderModelInfo;
renderModelInfo=function(){renderModelChoices()};
const beforeModelState=renderState;renderState=function(){beforeModelState();renderModelChoices()};
const originalOpenSettings=openSettings;
openSettings=async function(){providerDraft=null;brainReturn=null;$('asr-select').value='';$('llm-select').value='';await originalOpenSettings();renderModelChoices()};
$('settings-open').onclick=run(openSettings);
renderModelChoices();
