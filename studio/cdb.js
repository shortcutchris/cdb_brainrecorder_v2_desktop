'use strict';
let cdbArea=null,cdbAreas=[],transferPage=0;
let areaBinding='',areaRequest=0,areaLoading=false,areaLoaded=false,areaError='',areaSaving=false;
let meetingTargetSession=null,meetingTargetOverride=null,transferSending=false;
const transferNames={queued:'Wartet auf Übertragung',sending:'Wird übertragen',accepted:'Im CDB in Verarbeitung',completed:'Im Brain verarbeitet',completed_without_graph:'Gespeichert · ohne Wissensgraph',failed:'CDB-Verarbeitung fehlgeschlagen',uncertain:'Empfang unklar · im CDB prüfen'};
function cdbBinding(c){return c?.identity?JSON.stringify([c.config.server,c.identity.user_id,c.identity.client_id]):''}
function resetAreas(binding){
 areaBinding=binding;areaRequest++;cdbAreas=[];cdbArea=null;areaLoading=false;areaLoaded=false;areaSaving=false;areaError='';meetingTargetOverride=null;
}
async function loadCdbAreas(){
 if(!areaBinding||areaLoading)return;
 const binding=areaBinding,request=++areaRequest;areaLoading=true;areaError='';renderCdb();
 try{
  const rows=await api('/api/cdb/areas');
  if(binding!==areaBinding||request!==areaRequest||binding!==cdbBinding(state?.cdb))return;
  cdbAreas=rows;areaLoaded=true;
 }catch(error){if(binding===areaBinding&&request===areaRequest)areaError=error.message}
 finally{if(binding===areaBinding&&request===areaRequest){areaLoading=false;renderCdb()}}
}
function updateAreaSelect(id,entries,value,placeholder){
 const el=$(id),options=[{id:'',label:placeholder},...entries];
 const signature=JSON.stringify(options.map(a=>[a.id,a.label]));
 if(el.dataset.options!==signature){fillSelect(el,options,value,'id',a=>a.label);el.dataset.options=signature}
 if(el.value!==value)el.value=value;
 el.disabled=!state?.cdb?.identity||areaLoading||areaSaving||!areaLoaded||!entries.length;
}
function renderCdb(){
 const c=state?.cdb;if(!c)return;
 const binding=cdbBinding(c);
 if(binding!==areaBinding){resetAreas(binding);if(binding)queueMicrotask(()=>{if(areaBinding===binding)void loadCdbAreas()})}
 cdbArea=areaLoaded?cdbAreas.find(a=>a.id===c.destination?.id)||null:c.destination||null;
 for(const [id,key] of [['cdb-server','server'],['cdb-transcription','transcription'],['cdb-summary','summary']]){const el=$(id);if(el.value!==c.config[key])el.value=c.config[key];el.disabled=!allowed('configure')}
 $('cdb-account').textContent=c.identity?'Angemeldet: '+c.identity.name+' · '+c.config.server.replace('https://',''):'Nicht angemeldet · lokale Verarbeitung verfügbar';
 $('cdb-connection-heading').textContent=c.identity?'Dein Brain':'Mit deinem Firmenkonto verbinden';$('cdb-connection-intro').hidden=Boolean(c.identity);$('cdb-server').closest('label').hidden=Boolean(c.identity);
 const pending=c.login.state==='pending';$('cdb-login-code').hidden=!pending;
 if(pending){$('cdb-code').textContent=c.login.code;$('cdb-login-url').href=c.login.url;$('cdb-login-url').textContent=c.login.url.replace('https://','');$('cdb-expiry').textContent='Gültig bis '+new Date(c.login.expires*1000).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})}
 $('cdb-login-message').textContent=c.login.message||'';
 $('cdb-login').hidden=Boolean(c.identity);$('cdb-login').disabled=pending||!allowed('configure');$('cdb-logout').disabled=!allowed('configure')||(!pending&&!c.identity);
 $('cdb-connected-area').hidden=!c.identity;$('cdb-connection-refresh').hidden=!c.identity;
 for(const id of ['cdb-areas-refresh','cdb-connection-refresh'])$(id).disabled=!c.identity||areaLoading||areaSaving;
 let message=!c.identity?'Bitte zuerst unter Verbindung mit Microsoft anmelden.':areaLoading?'Knowledge Areas werden geladen …':areaSaving?'Standardbereich wird gespeichert …':areaError?'CDB: '+areaError:c.destination&&areaLoaded&&!cdbArea?'Der bisherige Standardbereich ist nicht mehr verfügbar. Bitte neu wählen.':!cdbAreas.length?'Für dieses Konto sind keine Knowledge Areas verfügbar.':cdbArea?'Standard gespeichert: '+cdbArea.label+'. Schreibrecht wird vor jeder Übertragung geprüft.':'Bitte einen Standardbereich wählen. Es wird nichts automatisch übertragen.';
 for(const id of ['cdb-area-status','cdb-connection-area-status'])$(id).textContent=message;
 const entries=areaLoaded?cdbAreas:cdbArea?[cdbArea]:[];
 for(const id of ['cdb-area','cdb-connection-area'])updateAreaSelect(id,entries,cdbArea?.id||'','Standardbereich wählen');
 if(meetingTargetSession!==selected){meetingTargetSession=selected;meetingTargetOverride=null}
 const target=cdbAreas.find(a=>a.id===(meetingTargetOverride||cdbArea?.id));
 updateAreaSelect('cdb-send-area',entries,target?.id||'','Knowledge Area wählen');
 const jobs=c.publications;transferPage=Math.max(0,Math.min(transferPage,jobs.length-1));drawPageNumbers($('cdb-transfer-pages'),jobs.length,transferPage,i=>{transferPage=i;renderCdb()});
 $('cdb-transfer-page').textContent=jobs.length?(transferPage+1)+' / '+jobs.length:'';
 const job=jobs[transferPage];$('cdb-transfers').replaceChildren();if(job){const h=document.createElement('strong'),p=document.createElement('p');h.textContent=job.title;p.textContent=(transferNames[job.state]||job.state)+(job.error?' · '+job.error:'');$('cdb-transfers').append(h,p)}
 const row=state.sessions.find(r=>r.id===selected);$('cdb-send-area').disabled||=transferSending;$('cdb-send-meeting').textContent=row?.title||'Meeting auswählen';$('cdb-send').disabled=transferSending||!c.identity||!target||areaLoading||areaSaving||!row||busyStates.includes(row.transcription_status);
 $('cdb-send-target').textContent=target?(meetingTargetOverride?'Nur dieses Meeting: ':'Standardbereich: ')+target.label+'. Übertragen werden Zusammenfassung, Transkript und Notizen.':c.identity?'Wähle einen Bereich für dieses Meeting oder lege unter Verbindung deinen Standard fest.':'Bitte zuerst unter Verbindung mit Microsoft anmelden.';
 document.querySelector('.local-note').textContent='Aufnahme lokal · '+(c.config.transcription==='cdb'?'CDB-Transkription':'lokale Transkription');
}
async function saveDefaultArea(id){
 const binding=areaBinding,area=cdbAreas.find(a=>a.id===$(id).value);
 if(!area||areaSaving||areaLoading){renderCdb();return}
 areaSaving=true;areaError='';renderCdb();
 try{await api('/api/cdb/area',{area:area.id});await poll()}
 catch(error){if(binding===areaBinding)areaError=error.message}
 finally{if(binding===areaBinding){areaSaving=false;renderCdb()}}
}
for(const [id,key] of [['cdb-server','server'],['cdb-transcription','transcription'],['cdb-summary','summary']])$(id).onchange=run(async()=>{try{await api('/api/cdb/config',{[key]:$(id).value})}finally{await poll()}});
$('cdb-login').onclick=run(async()=>{await api('/api/cdb/login',{});await poll()});
$('cdb-logout').onclick=run(async()=>{await api('/api/cdb/logout',{});resetAreas('');await poll()});
for(const id of ['cdb-areas-refresh','cdb-connection-refresh'])$(id).onclick=run(loadCdbAreas);
for(const id of ['cdb-area','cdb-connection-area'])$(id).onchange=run(()=>saveDefaultArea(id));
$('cdb-send-area').onchange=()=>{meetingTargetOverride=$('cdb-send-area').value||null;renderCdb()};
$('cdb-send-open').onclick=()=>{$('more').close();$('cdb-transfer').showModal();renderCdb()};
$('cdb-send').onclick=run(async()=>{
 if(transferSending)return;
 const target=cdbAreas.find(a=>a.id===(meetingTargetOverride||cdbArea?.id)),session=selected;
 if(!session||!target)throw new Error('Meeting und Zielbereich auswählen.');
 transferSending=true;renderCdb();
 try{
  await flush();await api('/api/cdb/send',{session,area:target.id});await poll();
  $('cdb-transfer').close();notice('Textübertragung nach '+target.label+' eingereiht. Status unter Knowledge Areas.');
 }finally{transferSending=false;renderCdb()}
});
function drawPageNumbers(nav,count,current,choose){nav.replaceChildren();if(count<2)return;const indices=[...new Set([0,current-1,current,current+1,count-1])].filter(i=>i>=0&&i<count).sort((a,b)=>a-b);let last=-1;for(const i of indices){if(i>last+1){const gap=document.createElement('span');gap.textContent='…';nav.append(gap)}const b=document.createElement('button');b.textContent=String(i+1);b.setAttribute('aria-label','Seite '+(i+1));b.setAttribute('aria-current',i===current?'page':'false');b.onclick=()=>choose(i);nav.append(b);last=i}}
// Augment existing rendering without introducing a second polling loop or store.
const originalRenderState=renderState;renderState=function(){originalRenderState();renderCdb();if((state.cdb?.progress||state.progress)&&state.jobs.some(j=>['transcribing','summarizing'].includes(j.state)))$('phase').textContent=state.cdb.progress||state.progress};

// Theme collections are discrete pages as well; never silently clip custom themes.
const themeList=$('theme-options'),themePages=document.createElement('nav');themePages.className='direct-pages';themePages.setAttribute('aria-label','Themeseiten');themeList.after(themePages);let themePage=0;
function drawThemePages(){const entries=[...themeList.children],size=6,count=Math.ceil(entries.length/size);themePage=Math.min(themePage,Math.max(0,count-1));entries.forEach((el,i)=>el.hidden=Math.floor(i/size)!==themePage);drawPageNumbers(themePages,count,themePage,i=>{themePage=i;drawThemePages()})}
new MutationObserver(drawThemePages).observe(themeList,{childList:true});drawThemePages();
