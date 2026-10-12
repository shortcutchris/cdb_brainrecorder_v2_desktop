'use strict';
let cdbArea=null,cdbAreas=[],transferPage=0;
const transferNames={queued:'Wartet auf Übertragung',sending:'Wird übertragen',accepted:'Im CDB in Verarbeitung',completed:'Im Brain verarbeitet',completed_without_graph:'Gespeichert · ohne Wissensgraph',failed:'CDB-Verarbeitung fehlgeschlagen',uncertain:'Empfang unklar · im CDB prüfen'};
function renderCdb(){
 const c=state?.cdb;if(!c)return;
 cdbArea=c.destination||null;
 if(cdbArea&&!cdbAreas.length)fillSelect($('cdb-area'),[cdbArea],cdbArea.id,'id',a=>a.label);
 for(const [id,key] of [['cdb-server','server'],['cdb-transcription','transcription'],['cdb-summary','summary']]){const el=$(id);if(el.value!==c.config[key])el.value=c.config[key];el.disabled=!allowed('configure')}
 $('cdb-account').textContent=c.identity?'Angemeldet: '+c.identity.name:'Nicht angemeldet · lokale Verarbeitung verfügbar';
 const pending=c.login.state==='pending';$('cdb-login-code').hidden=!pending;
 if(pending){$('cdb-code').textContent=c.login.code;$('cdb-login-url').href=c.login.url;$('cdb-login-url').textContent=c.login.url.replace('https://','');$('cdb-expiry').textContent='Gültig bis '+new Date(c.login.expires*1000).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})}
 $('cdb-login-message').textContent=c.login.message||'';$('cdb-login').disabled=pending||!allowed('configure');$('cdb-logout').disabled=!allowed('configure')||(!pending&&!c.identity);
 $('cdb-areas-refresh').disabled=!c.identity;$('cdb-area').disabled=!c.identity||(!cdbAreas.length&&!cdbArea);if(!c.identity)$('cdb-area-status').textContent='Bitte zuerst unter Verbindung mit Microsoft anmelden.';
 const jobs=c.publications;transferPage=Math.max(0,Math.min(transferPage,jobs.length-1));drawPageNumbers($('cdb-transfer-pages'),jobs.length,transferPage,i=>{transferPage=i;renderCdb()});
 $('cdb-transfer-page').textContent=jobs.length?(transferPage+1)+' / '+jobs.length:'';
 const job=jobs[transferPage];$('cdb-transfers').replaceChildren();if(job){const h=document.createElement('strong'),p=document.createElement('p');h.textContent=job.title;p.textContent=(transferNames[job.state]||job.state)+(job.error?' · '+job.error:'');$('cdb-transfers').append(h,p)}
 const row=state.sessions.find(r=>r.id===selected);$('cdb-send').disabled=!c.identity||!cdbArea||!row||busyStates.includes(row.transcription_status);$('cdb-send-target').textContent=cdbArea?'Ziel: '+cdbArea.label:'Zuerst in Einstellungen → Knowledge Areas einen Zielbereich wählen.';
 if(!c.identity){cdbArea=null;cdbAreas=[];$('cdb-area').replaceChildren()}
 document.querySelector('.local-note').textContent='Aufnahme lokal · '+(c.config.transcription==='cdb'?'CDB-Transkription':'lokale Transkription');
}
for(const [id,key] of [['cdb-server','server'],['cdb-transcription','transcription'],['cdb-summary','summary']])$(id).onchange=run(async()=>{try{await api('/api/cdb/config',{[key]:$(id).value})}finally{await poll()}});
$('cdb-login').onclick=run(async()=>{await api('/api/cdb/login',{});await poll()});
$('cdb-logout').onclick=run(async()=>{await api('/api/cdb/logout',{});cdbArea=null;cdbAreas=[];await poll()});
$('cdb-areas-refresh').onclick=run(async()=>{cdbAreas=await api('/api/cdb/areas');fillSelect($('cdb-area'),[{id:'',label:'Zielbereich auswählen'},...cdbAreas],cdbArea?.id||'','id',a=>a.label);cdbArea=cdbAreas.find(a=>a.id===$('cdb-area').value)||null;$('cdb-area-status').textContent=cdbAreas.length+' Bereiche verfügbar. Schreibrecht wird beim Übertragen geprüft.';renderCdb()});
$('cdb-area').onchange=run(async()=>{const area=cdbAreas.find(a=>a.id===$('cdb-area').value);if(area){await api('/api/cdb/area',{area:area.id});await poll()}});
$('cdb-send').onclick=run(async()=>{await flush();if(!selected||!cdbArea)throw new Error('Meeting und Zielbereich auswählen.');await api('/api/cdb/send',{session:selected,area:cdbArea.id});notice('Textübertragung eingereiht. Status unter Knowledge Areas.');await poll()});
function drawPageNumbers(nav,count,current,choose){nav.replaceChildren();if(count<2)return;const indices=[...new Set([0,current-1,current,current+1,count-1])].filter(i=>i>=0&&i<count).sort((a,b)=>a-b);let last=-1;for(const i of indices){if(i>last+1){const gap=document.createElement('span');gap.textContent='…';nav.append(gap)}const b=document.createElement('button');b.textContent=String(i+1);b.setAttribute('aria-label','Seite '+(i+1));b.setAttribute('aria-current',i===current?'page':'false');b.onclick=()=>choose(i);nav.append(b);last=i}}
// Augment existing rendering without introducing a second polling loop or store.
const originalRenderState=renderState;renderState=function(){originalRenderState();renderCdb();if((state.cdb?.progress||state.progress)&&state.jobs.some(j=>['transcribing','summarizing'].includes(j.state)))$('phase').textContent=state.cdb.progress||state.progress};

// Theme collections are discrete pages as well; never silently clip custom themes.
const themeList=$('theme-options'),themePages=document.createElement('nav');themePages.className='direct-pages';themePages.setAttribute('aria-label','Themeseiten');themeList.after(themePages);let themePage=0;
function drawThemePages(){const entries=[...themeList.children],size=6,count=Math.ceil(entries.length/size);themePage=Math.min(themePage,Math.max(0,count-1));entries.forEach((el,i)=>el.hidden=Math.floor(i/size)!==themePage);drawPageNumbers(themePages,count,themePage,i=>{themePage=i;drawThemePages()})}
new MutationObserver(drawThemePages).observe(themeList,{childList:true});drawThemePages();
