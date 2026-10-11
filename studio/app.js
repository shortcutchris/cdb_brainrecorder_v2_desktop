'use strict';
const $=id=>document.getElementById(id), fields=['title','notes','transcript_text','summary_text'];
let online=false, setupReady=false, lastStateAt=0;
let state=null, selected=null, field='notes', csrf='', namespace='', models=new Map(), prompts=[], catalog=null;
let pollRunning=false, saveTimer=null, recordingAction=false, nextRecordAction=0, queueSignature='', recentSignature='', setupBusy=false;
const names={recording:'Aufnahme läuft',importing:'Audio vorbereiten',queued:'Wartet',transcribing:'Transkription läuft',summarizing:'Zusammenfassung läuft',completed:'Fertig',failed:'Fehler'};
const busyStates=['recording','importing','queued','transcribing','summarizing'];
const audio=$('audio');audio.volume=.8;
function duration(n){n=Math.max(0,Math.floor(Number(n)||0));return n>=3600?[Math.floor(n/3600),Math.floor(n/60)%60,n%60].map(x=>String(x).padStart(2,'0')).join(':'):[Math.floor(n/60),n%60].map(x=>String(x).padStart(2,'0')).join(':')}
function icon(name){const img=document.createElement('img');img.src='/assets/'+name+'.svg';img.alt='';return img}
function notice(text){$('notice-text').textContent=text;$('notice').hidden=!text}
$('notice-close').onclick=()=>notice('');
async function api(path,body,keepalive=false){
 const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store',keepalive,signal:keepalive?undefined:AbortSignal.timeout(body===undefined?8000:25000)});
 const result=await response.json();if(!response.ok){const error=new Error(result.error||'Verbindung fehlgeschlagen.');error.status=response.status;throw error}return result;
}
function allowed(key){return online&&Boolean(state?.capabilities?.[key]?.allowed)}
function bindRule(id,key,extra=false){const el=$(id);el.disabled=!allowed(key)||extra;el.title=!online?'Verbindung unterbrochen':state?.capabilities?.[key]?.reason||''}
async function leaveDraft(){try{await flush()}catch(_){notice('Entwurf bleibt auf diesem Gerät erhalten. Du kannst weiter navigieren und ihn lokal sichern.')}}
function run(fn){return async(...args)=>{try{await fn(...args)}catch(error){notice(error.message)}}}
function draftKey(id,key){return 'recorder:'+namespace+':'+id+':'+key}
function storeDraft(model,key){try{localStorage.setItem(draftKey(model.id,key),JSON.stringify({value:model.values[key],base:model.base[key]}))}catch(_){notice('Lokaler Entwurfsspeicher nicht verfügbar. Bitte Änderungen zeitnah speichern.')}}
function clearDraft(id,key){try{localStorage.removeItem(draftKey(id,key))}catch(_){} }
function makeModel(row){const model={id:row.id,row,base:{},values:{},dirty:new Set(),saving:null,failed:false,savedAt:null};for(const key of fields){model.base[key]=row[key]||'';model.values[key]=row[key]||'';try{const draft=JSON.parse(localStorage.getItem(draftKey(row.id,key))||'null');if(draft&&typeof draft.value==='string'&&draft.value!==model.values[key]){model.values[key]=draft.value;model.base[key]=draft.base;model.dirty.add(key);notice('Ein ungespeicherter Entwurf wurde wiederhergestellt. Er bleibt bis zum erfolgreichen Speichern erhalten.')}}catch(_){}}models.set(row.id,model);return model}
async function flush(model=models.get(selected)){
 if(!model)return true;
 if(!online&&model.dirty.size)throw new Error('Offline · Entwurf bleibt lokal erhalten.');
 if(model.saving)await model.saving;
 while(model.dirty.size){
  const changes={},base={};for(const key of model.dirty){changes[key]=model.values[key];base[key]=model.base[key]}
  $('save-state').textContent='Wird gespeichert …';
  model.saving=api('/api/sessions/'+model.id+'/save',{changes,base}).then(row=>{
   model.row=row;for(const key of Object.keys(changes)){model.base[key]=changes[key];if(model.values[key]===changes[key]){model.dirty.delete(key);clearDraft(model.id,key)}else storeDraft(model,key)}model.failed=false;model.savedAt=new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});notice('');
  }).catch(error=>{model.failed=true;$('save-state').textContent='Nicht gespeichert · Entwurf bleibt erhalten';$('draft-actions').hidden=false;notice(error.message);throw error}).finally(()=>{model.saving=null});
  await model.saving;
 }
 if(model.id===selected){$('draft-actions').hidden=!model.dirty.size;}
 if(model.id===selected&&model.savedAt)$('save-state').textContent='Zuletzt gespeichert: '+model.savedAt;
 return true;
}
function changed(key,value){const model=models.get(selected);if(!model)return;model.values[key]=value;model.dirty.add(key);model.failed=false;$('draft-actions').hidden=false;storeDraft(model,key);clearTimeout(saveTimer);if(!online){model.failed=true;$('save-state').textContent='Offline · Entwurf bleibt lokal erhalten';return}$('save-state').textContent='Wird gespeichert …';saveTimer=setTimeout(()=>flush(model).catch(()=>{}),450)}
$('editor').oninput=()=>changed(field,$('editor').value);
window.addEventListener('beforeunload',event=>{if([...models.values()].some(m=>m.dirty.size)){event.preventDefault();event.returnValue=''}});
window.addEventListener('pagehide',()=>{for(const m of models.values()){if(!m.dirty.size||m.saving)continue;const changes={},base={};for(const key of m.dirty){changes[key]=m.values[key];base[key]=m.base[key];storeDraft(m,key)}api('/api/sessions/'+m.id+'/save',{changes,base},true).catch(()=>{})}});
function setEditor(value){const el=$('editor');if(el.value===value)return;const start=el.selectionStart,end=el.selectionEnd,scroll=el.scrollTop;el.value=value;el.setSelectionRange(Math.min(start,value.length),Math.min(end,value.length));el.scrollTop=scroll}
function renderSelected(){
 const model=models.get(selected);if(!model)return;const row=model.row;
 $('meeting-title').textContent=model.values.title;$('meeting-title').title=model.values.title;
 const date=new Date(row.recorded_at);$('meeting-date').textContent=Number.isNaN(+date)?row.recorded_at:date.toLocaleDateString('de-DE',{weekday:'long',day:'numeric',month:'long',year:'numeric'})+' · '+date.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
 setEditor(model.values[field]);$('editor').disabled=false;$('editor').readOnly=field!=='notes'&&busyStates.includes(row.transcription_status);
 $('editor').setAttribute('aria-label',{notes:'Notizen',transcript_text:'Transkript',summary_text:'Zusammenfassung'}[field]);
 $('editor-tools').hidden=field==='notes';bindRule('process','process',busyStates.includes(row.transcription_status));bindRule('retranscribe','process',busyStates.includes(row.transcription_status));$('delete').disabled=!online||busyStates.includes(row.transcription_status);$('meeting-constraint').textContent=busyStates.includes(row.transcription_status)?'Aufnahme oder Verarbeitung zuerst abschließen. Notizen und Titel bleiben editierbar.':'';$('delete').title=busyStates.includes(row.transcription_status)?'Aufnahme oder Verarbeitung zuerst abschließen.':'';$('draft-actions').hidden=!model.dirty.size;
 if(row.local_error&&row.transcription_status==='failed')$('save-state').textContent='Fehler: '+row.local_error;
 else if(!model.dirty.size&&!model.saving)$('save-state').textContent=$('editor').readOnly?'KI-Verarbeitung läuft · Notizen bleiben editierbar':model.savedAt?'Zuletzt gespeichert: '+model.savedAt:'Änderungen werden automatisch gespeichert';
 document.querySelectorAll('[data-field]').forEach(b=>{const active=b.dataset.field===field;b.classList.toggle('active',active);b.setAttribute('aria-selected',String(active))});
 const hasAudio=state?.sessions.find(r=>r.id===selected)?.has_audio;
 if(hasAudio&&audio.dataset.session!==String(selected)){audio.src='/api/sessions/'+selected+'/audio';audio.dataset.session=String(selected);$('seek').value=0;$('play-time').textContent='00:00'}
 $('play').disabled=!hasAudio||!online;
}
async function selectMeeting(id){
 if(selected===id)return;
 await leaveDraft();const row=await api('/api/sessions/'+id);audio.pause();selected=id;
 let model=models.get(id);if(!model)model=makeModel(row);else mergeRow(model,row);
 $('editor').value='';$('editor').scrollTop=0;renderSelected();renderRecent();
 const peaks=await api('/api/sessions/'+id+'/peaks');if(selected===id){selectedPeaks=peaks;drawWave(state.recording.id?state.waveform:peaks)}
 if(model.dirty.size&&!model.failed)flush(model).catch(()=>{});
}
function mergeRow(model,row){model.row=row;for(const key of fields){if(!model.dirty.has(key)&&!model.saving){model.base[key]=row[key]||'';model.values[key]=row[key]||''}}}
document.querySelectorAll('[data-field]').forEach(button=>button.onclick=run(async()=>{await leaveDraft();field=button.dataset.field;renderSelected()}));
function renderRecent(){
 const rows=state?.sessions.slice(0,3)||[];const signature=JSON.stringify([rows,selected]);if(signature===recentSignature)return;recentSignature=signature;
 $('recent').replaceChildren();for(const [i,row] of rows.entries()){const button=document.createElement('button');button.className='recent-card'+(row.id===selected?' selected':'');button.append(icon(['users','chart-bar','user'][i]));const text=document.createElement('span');text.className='card-text';const strong=document.createElement('strong');strong.textContent=row.title;const date=document.createElement('small');const d=new Date(row.recorded_at);date.textContent=Number.isNaN(+d)?row.recorded_at:d.toLocaleDateString('de-DE')+' · '+d.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});text.append(strong,date);button.append(text);button.title=row.title;button.onclick=run(()=>selectMeeting(row.id));$('recent').append(button)}
 const next=document.createElement('button');next.className='recent-next';next.setAttribute('aria-label','Alle Aufnahmen öffnen');next.append(icon('caret-right'));next.onclick=run(openLibrary);$('recent').append(next);
}
function drawWave(peaks){const canvas=$('waveform'),context=canvas.getContext('2d');context.clearRect(0,0,canvas.width,canvas.height);context.strokeStyle=state?.recording.id?'#4b85bc':'#bdcbd8';context.lineWidth=3;context.lineCap='round';for(let i=0;i<peaks.length;i++){const h=Math.max(1,Math.min(30,peaks[i]*85));const x=5+i*(canvas.width-10)/peaks.length;context.beginPath();context.moveTo(x,36-h);context.lineTo(x,36+h);context.stroke()}}
let selectedPeaks=[0];
function renderState(){
 const active=Boolean(state.recording.id);$('record').classList.toggle('recording',active);$('record').setAttribute('aria-label',active?'Aufnahme stoppen':'Aufnahme starten');$('record-icon').src='/assets/'+(active?'stop':'circle')+'.svg';$('record-label').textContent=active?'Aufnahme stoppen':'Aufnahme starten';$('duration').textContent=duration(state.recording.seconds);$('record').disabled=recordingAction||!online||(!active&&state.config.setup_complete&&!allowed('record'));$('record').title=active?'':state.capabilities?.record.reason||'';for(const b of document.querySelectorAll('.dialog-stop')){b.hidden=!active;b.disabled=recordingAction||!online}
 const c=state.config;$('mic-name').textContent=c.setup_complete?'Mikrofon · eingerichtet':'Mikrofon einrichten';
 $('capture-hint').textContent=state.preview?'Lokale Testbibliothek · künstliche Audioquelle. Keine Verbindung zu persönlichen Pi-Meetings.':active?'Aufnahme läuft. Tippe auf den Button, um sie sicher zu beenden.':c.setup_complete?'Bereit für eine neue Aufnahme. Tippe auf den Button, um zu starten.':'Kein getestetes Mikrofon. Bitte Audio in den Einstellungen einrichten.';
 if(!online)$('capture-hint').textContent='Verbindung unterbrochen. Der letzte Aufnahmestand wird erneut geprüft.';else if(!active&&state.config.setup_complete&&!allowed('record'))$('capture-hint').textContent=state.capabilities.record.reason;drawWave(active?state.waveform:selectedPeaks);renderRecent();renderQueue();renderSettingsStatus();if(!online)$('phase').textContent='Verbindung unterbrochen · Entwürfe bleiben lokal';
}
function queueJobs(){const rows=new Map(state.sessions.filter(r=>r.local_job_id).map(r=>[r.local_job_id,r]));const jobs=state.jobs.filter(j=>rows.has(j.id)&&j.state!=='completed').map(j=>({...j,session:rows.get(j.id)}));for(const r of state.sessions)if(r.transcription_status==='failed'&&!r.local_job_id)jobs.push({id:'legacy-'+r.id,state:'failed',created:0,error:r.local_error,session:r});const order={recording:0,transcribing:1,summarizing:1,importing:2,queued:3,failed:4};return jobs.sort((a,b)=>(order[a.state]-order[b.state])||((a.queued_at||a.created)-(b.queued_at||b.created)))}
function renderQueue(){
 const jobs=queueJobs(),active=jobs.find(j=>['transcribing','summarizing','importing'].includes(j.state)),waiting=jobs.filter(j=>j.state==='queued'),failed=jobs.filter(j=>j.state==='failed');
 const test=state.model_test&&busyStates.includes(state.model_test.state)?state.model_test:null;const processing=active||test;
 $('phase').textContent=processing?(test&&!active?'Modelltest · ':'')+(names[processing.state]||processing.state)+' · '+duration(Date.now()/1000-processing.updated):state.recording.id?'Aufnahme läuft':waiting.length?'Wartet auf Verarbeitung':state.installation.state==='running'?'Modelldownload läuft':state.free_mb<state.config.min_free_mb?'Zu wenig freier Speicher':!state.config.setup_complete?'Mikrofon einrichten':'Lokal bereit';
 $('waiting').textContent=waiting.length+' warten';$('errors').textContent=failed.length?failed.length+' Fehler':'';document.body.classList.toggle('working',Boolean(processing));$('activity-icon').src='/assets/'+(processing?'circle-notch':state.recording.id?'microphone':failed.length?'arrow-clockwise':'check-circle')+'.svg';
 const signature=String(allowed('process'))+JSON.stringify(jobs.map(j=>[j.id,j.state,j.session.title,j.error]));if(signature===queueSignature)return;queueSignature=signature;const scroll=$('queue-panel').scrollTop;$('queue-panel').replaceChildren();let position=0;
 for(const job of jobs){const row=document.createElement('div');row.className='queue-row';const title=document.createElement('strong');if(job.state==='queued')position++;title.textContent=(job.state==='queued'?position+'. ':'')+job.session.title;const status=document.createElement('span');status.textContent=job.state==='failed'?job.error||'Fehler':names[job.state];status.title=job.error||'';const action=document.createElement('button');action.textContent=job.state==='failed'?'Wiederholen':'Öffnen';action.disabled=job.state==='failed'&&!allowed('process');action.onclick=run(async()=>{await flush();if(job.state==='failed'){await api('/api/sessions/'+job.session.id+'/retry',{});await poll()}else await selectMeeting(job.session.id)});row.append(title,status,action);$('queue-panel').append(row)}
 if(!jobs.length){const empty=document.createElement('p');empty.textContent='Keine offenen Aufträge.';$('queue-panel').append(empty)}$('queue-panel').scrollTop=scroll;
}
async function poll(){
 if(pollRunning)return;pollRunning=true;
 try{const s=await api('/api/state');state=s;online=true;lastStateAt=Date.now();csrf=s.csrf;namespace=s.namespace;renderState();if(selected===null&&s.sessions.length){await selectMeeting(s.sessions[0].id)}else if(selected!==null){const id=selected,row=await api('/api/sessions/'+id);if(id===selected){const model=models.get(id);mergeRow(model,row);renderSelected()}}}
 catch(error){online=false;queueSignature='';if(state){renderState();renderSelected()}$('phase').textContent='Verbindung unterbrochen · Entwürfe bleiben lokal';$('record').disabled=true;for(const id of ['delete','retranscribe','process','finish-setup','probe-start','asr-install','llm-install','model-test','binary-save'])$(id).disabled=true;for(const b of document.querySelectorAll('.dialog-stop'))b.disabled=true;if(!state)notice(error.message)}finally{pollRunning=false}
}
$('record').onclick=run(async()=>{if(recordingAction||performance.now()<nextRecordAction)return;recordingAction=true;nextRecordAction=performance.now()+700;$('record').disabled=true;try{if(!state)throw new Error('Noch keine Verbindung.');if(!state.recording.id&&!state.config.setup_complete){await openSettings();throw new Error('Bitte zuerst Mikrofon testen und Einrichtung abschließen.')}if(!state.recording.id)audio.pause();await api('/api/record/'+(state.recording.id?'stop':'start'),{});await poll()}finally{recordingAction=false;if(state)renderState()}});
$('queue-toggle').onclick=()=>{const opened=$('queue-panel').hidden;$('queue-panel').hidden=!opened;document.body.classList.toggle('queue-open',opened);$('queue-toggle').setAttribute('aria-expanded',String(opened));$('queue-arrow').src='/assets/'+(opened?'caret-down':'caret-up')+'.svg'};
$('errors').onclick=()=>{if($('queue-panel').hidden)$('queue-toggle').click()};
$('play').onclick=run(async()=>{if(audio.paused){if(state?.recording.id&&!confirm('Die Wiedergabe kann mit aufgenommen werden. Nur mit Kopfhörern fortsetzen?'))return;await audio.play();}else audio.pause()});
audio.onplay=()=>{$('play-icon').src='/assets/pause.svg';$('play').setAttribute('aria-label','Wiedergabe pausieren')};audio.onpause=()=>{$('play-icon').src='/assets/play.svg';$('play').setAttribute('aria-label','Wiedergabe starten')};audio.onerror=()=>{if(audio.src)notice('Audio konnte nicht wiedergegeben werden. Datei und Audioausgabe prüfen.')};
let seeking=false;$('seek').onpointerdown=()=>{seeking=true};$('seek').onchange=()=>{if(Number.isFinite(audio.duration))audio.currentTime=audio.duration*Number($('seek').value)/1000;seeking=false};$('seek').onpointerup=()=>{seeking=false};
audio.ontimeupdate=()=>{$('play-time').textContent=duration(audio.currentTime);if(!seeking)$('seek').value=Number.isFinite(audio.duration)?audio.currentTime/audio.duration*1000:0};audio.ondurationchange=()=>{$('play-total').textContent=duration(audio.duration)};$('volume').oninput=()=>{audio.volume=Number($('volume').value);$('volume').style.setProperty('--volume',(audio.volume*100)+'%')};
async function openLibrary(){await leaveDraft();$('library').showModal();await searchLibrary()}
let searchNumber=0;async function searchLibrary(){const number=++searchNumber;const rows=await api('/api/search?q='+encodeURIComponent($('search').value));if(number!==searchNumber)return;$('library-list').replaceChildren();for(const row of rows){const wrap=document.createElement('div');wrap.className='library-item';const b=document.createElement('button');const title=document.createElement('span');title.textContent=row.title;const date=document.createElement('small');date.textContent=row.recorded_at.slice(0,10);b.append(title,date);b.onclick=run(async()=>{await selectMeeting(row.id);$('library').close()});wrap.append(b);$('library-list').append(wrap)}if(!rows.length)$('library-list').textContent='Keine passenden Meetings.'}
$('search').oninput=run(searchLibrary);$('library-open').onclick=run(openLibrary);$('home').onclick=()=>{for(const d of document.querySelectorAll('dialog[open]'))d.close()};
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
$('more-open').onclick=run(async()=>{if(!selected)return;await leaveDraft();const m=models.get(selected);$('title-edit').value=m.values.title;$('metadata').textContent=m.row.recorded_at+' · '+duration(m.row.duration_sec)+' · '+m.row.samplerate+' Hz · '+m.row.channels+' Kanal/Kanäle';$('more').showModal()});
$('rename').onclick=run(async()=>{changed('title',$('title-edit').value);await flush();renderSelected();await poll();$('more').close()});
async function exportMeeting(){const m=models.get(selected);if(!m)return;const text='# '+m.values.title+'\n\n'+[['Notizen','notes'],['Transkript','transcript_text'],['Zusammenfassung','summary_text']].map(([label,key])=>'## '+label+'\n\n'+m.values[key]).join('\n\n');$('export-text').value=text;$('local-export').showModal();$('export-file').onclick=()=>{const url=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='meeting-'+selected+(m.dirty.size?'-entwurf':'')+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};}
$('draft-export').onclick=run(exportMeeting);
$('draft-retry').onclick=run(()=>flush());
$('draft-compare').onclick=run(async()=>{const m=models.get(selected);if(!m)return;const current=await api('/api/sessions/'+selected);$('conflict-local').value=m.values[field];$('conflict-server').value=current[field]||'';$('conflict').showModal();$('conflict-keep').onclick=run(async()=>{const key=field,value=m.values[key];await api('/api/sessions/'+m.id+'/save',{changes:{[key]:value},base:{[key]:current[key]||''}});m.base[key]=value;m.dirty.delete(key);clearDraft(m.id,key);notice('');$('conflict').close();renderSelected()});$('conflict-use-server').onclick=()=>{m.base[field]=current[field]||'';m.values[field]=current[field]||'';m.dirty.delete(field);clearDraft(m.id,field);$('conflict').close();renderSelected()}});
for(const heading of document.querySelectorAll('.dialog-heading')){const b=document.createElement('button');b.className='dialog-stop danger';b.textContent='Aufnahme stoppen';b.hidden=true;b.onclick=()=>$('record').click();heading.insertBefore(b,heading.lastElementChild)}
$('export').onclick=run(exportMeeting);$('download').onclick=run(exportMeeting);
async function processMeeting(transcribeAgain=false){await flush();if(!selected)return;await api('/api/sessions/'+selected+'/process',{prompt:$('prompt').value,transcribe_again:transcribeAgain});$('more').close();await poll()}
$('process').onclick=run(()=>processMeeting(false));$('retranscribe').onclick=run(()=>processMeeting(true));
$('delete').onclick=run(async()=>{await flush();if(!selected||!confirm('Dieses Meeting und seine Audiodatei endgültig löschen?'))return;const id=selected;await api('/api/sessions/'+id+'/delete',{});models.delete(id);selected=null;audio.pause();audio.removeAttribute('src');delete audio.dataset.session;$('editor').value='';$('editor').disabled=true;$('meeting-title').textContent='Meeting auswählen';$('more').close();await poll()});
function fillSelect(element,entries,selectedValue,valueKey,label){element.replaceChildren();for(const entry of entries){const option=document.createElement('option');option.value=entry[valueKey];option.textContent=label(entry);element.append(option)}if(selectedValue!==undefined)element.value=selectedValue}
async function loadPrompts(){prompts=await api('/api/prompts');for(const id of ['prompt','prompt-select']){const before=$(id).value;fillSelect($(id),prompts,before||prompts[0]?.id,'id',p=>p.name)}renderPrompt()}
function renderPrompt(){const p=prompts.find(p=>p.id===$('prompt-select').value);$('prompt-name').value=p?.name||'';$('prompt-text').value=p?.prompt_text||'';$('prompt-name').readOnly=Boolean(p?.is_default);$('prompt-text').readOnly=Boolean(p?.is_default);$('prompt-save').disabled=Boolean(p?.is_default);$('prompt-delete').disabled=!p||p.is_default}
$('prompt-select').onchange=renderPrompt;$('prompt-new').onclick=()=>{$('prompt-select').value='';$('prompt-name').value='';$('prompt-text').value='';$('prompt-name').readOnly=false;$('prompt-text').readOnly=false;$('prompt-save').disabled=false;$('prompt-delete').disabled=true;$('prompt-name').focus()};
$('prompt-save').onclick=run(async()=>{const id=$('prompt-select').value,known=new Set(prompts.map(p=>p.id));const saved=await api('/api/prompts',{action:id?'update':'add',id,name:$('prompt-name').value,text:$('prompt-text').value});await loadPrompts();$('prompt-select').value=id||saved.find(p=>!known.has(p.id))?.id||prompts[0]?.id;renderPrompt();notice('Prompt gespeichert.')});
$('prompt-delete').onclick=run(async()=>{if(!confirm('Eigenen Prompt löschen?'))return;await api('/api/prompts',{action:'delete',id:$('prompt-select').value});await loadPrompts()});
async function loadSetup(){
 if(setupBusy)return;setupBusy=true;
 try{const [setup,audioDevices]=await Promise.all([api('/api/setup'),api('/api/devices')]);catalog=setup.catalog;const c=state.config;
  fillSelect($('mic-select'),audioDevices.devices,c.device,'id',d=>d.label);if(!audioDevices.devices.length){fillSelect($('mic-select'),[{id:'',label:'Kein Mikrofon gefunden'}],'','id',d=>d.label)}
  fillSelect($('asr-select'),catalog.asr,c.whisper_model,'path',m=>m.label+' · '+(m.installed?'installiert':'fehlt'));
  fillSelect($('llm-select'),catalog.llm,c.summary_model,'id',m=>m.label+' · '+(m.installed?'installiert':'fehlt'));
  $('binary').value=c.whisper_binary;$('checks').replaceChildren();for(const check of setup.checks){const p=document.createElement('p');p.textContent=check.label+' · '+(check.ok?'bereit':'offen');$('checks').append(p)}setupReady=setup.ready;bindRule('finish-setup','finish_setup',!setupReady);renderModelInfo();renderSettingsStatus();
 }finally{setupBusy=false}
}
async function openSettings(){await leaveDraft();$('settings').showModal();await loadPrompts();await loadSetup()}
$('settings-open').onclick=run(openSettings);$('mic-settings').onclick=run(openSettings);$('refresh-devices').onclick=run(loadSetup);
document.querySelectorAll('[data-settings]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-settings]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.settings-page').forEach(p=>p.hidden=p.id!==b.dataset.settings)});
async function configure(changes){await api('/api/settings',changes);await poll();await loadSetup()}
$('mic-select').onchange=run(async()=>{if($('mic-select').value)await configure({device:$('mic-select').value})});
for(const id of ['asr-select','llm-select'])$(id).onchange=run(()=>configure({whisper_model:$('asr-select').value,summary_model:$('llm-select').value}));
$('binary-save').onclick=run(()=>configure({whisper_binary:$('binary').value}));
$('probe-start').onclick=run(async()=>{await api('/api/microphone/test',{});await poll()});
$('finish-setup').onclick=run(async()=>{await api('/api/setup/complete',{});await poll();await loadSetup();notice('Einrichtung gespeichert.')});
function renderModelInfo(){if(!catalog)return;for(const [select,key,entries,info,install] of [['asr-select','path',catalog.asr,'asr-info','asr-install'],['llm-select','id',catalog.llm,'llm-info','llm-install']]){const m=entries.find(m=>m[key]===$(select).value);$(info).textContent=m?m.description+' · '+m.license+' · '+(m.bytes/1e9).toFixed(1)+' GB':'';$(install).disabled=!m||m.installed||m.id==='custom'||!allowed('install')}}
async function installModel(backend){const entries=backend==='whisper'?catalog.asr:catalog.llm,key=backend==='whisper'?'path':'id',select=backend==='whisper'?'asr-select':'llm-select';const m=entries.find(m=>m[key]===$(select).value);if(!m||!confirm(m.label+' bewusst herunterladen? Ungefähr '+(m.bytes/1e9).toFixed(1)+' GB plus Reserve. '+m.license+'. Keine Meetings werden übertragen.'))return;await api('/api/models/install',{backend,model:m.id});await poll()}
$('asr-install').onclick=run(()=>installModel('whisper'));$('llm-install').onclick=run(()=>installModel('ollama'));
$('model-test').onclick=run(async()=>{await api('/api/models/test',{});await poll()});
let previousDownload='',previousProbe='';function renderSettingsStatus(){
 if(!state)return;$('settings-constraint').textContent=!online?'Verbindung unterbrochen. Einstellungen warten auf eine neue Verbindung.':state.capabilities.configure.reason||(!state.capabilities.install.allowed?'Aufnahme und Notizen bleiben verfügbar. Modelle herunterladen oder testen erst nach Abschluss offener Aufträge.':'');const p=state.microphone_test,d=state.installation;const busy=!allowed('configure');
 for(const id of ['mic-select','asr-select','llm-select','binary-save','probe-start'])$(id).disabled=busy||id==='mic-select'&&!$('mic-select').value;
 bindRule('probe-start','probe',!$('mic-select').value);bindRule('finish-setup','finish_setup',!setupReady);
 $('probe-level').value=p.level||0;$('probe-state').textContent=p.message||names[p.state]||p.state;
 if(p.state==='completed'&&previousProbe!=='completed'){$('probe-audio').src='/api/microphone/audio?completed='+Date.now();if($('settings').open)loadSetup().catch(e=>notice(e.message))}previousProbe=p.state;
 if(d.total)$('download-progress').value=100*d.completed/d.total;else if(d.state==='running')$('download-progress').removeAttribute('value');else $('download-progress').value=0;$('download-state').textContent=(d.message||'')+(d.total?' · '+Math.round(d.completed/1e6)+' / '+Math.round(d.total/1e6)+' MB':'');
 if(d.state==='completed'&&previousDownload!=='completed'&&$('settings').open)loadSetup().catch(e=>notice(e.message));previousDownload=d.state;
 $('model-test').disabled=!allowed('model_test')||!catalog?.asr.some(m=>m.installed&&m.path===state.config.whisper_model)||!catalog?.llm.some(m=>m.installed&&m.id===state.config.summary_model)||!catalog?.whisper_runtime||!catalog?.ollama||Boolean(state.model_test&&busyStates.includes(state.model_test.state));if(state.model_test){const t=state.model_test;$('model-test-state').textContent=(names[t.state]||t.state)+(t.error?' · '+t.error:'')+(t.summary?'\n'+t.summary:'')}
 if(catalog)renderModelInfo();
}
poll().then(()=>loadPrompts()).catch(e=>notice(e.message));setInterval(poll,1000);setInterval(()=>{if(online&&Date.now()-lastStateAt>5000){online=false;renderState();renderSelected();$('phase').textContent='Verbindung wird geprüft · Aktionen warten';}},1000);
