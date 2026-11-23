'use strict';
const el=id=>document.getElementById(id);
let articles=[], info=null, session=null, working=false, connected=false, pending=null, timer=null, sessionChecked=false, connectionError=false;
const labels={ 'record.start':['Meeting aufzeichnen','Aufnahme am Pi starten'], 'record.stop':['Aufnahme stoppen','Speichern und verarbeiten'], 'record.pause':['Pause','Aufnahme unterbrechen'], 'record.resume':['Weiter aufnehmen','Aufnahme fortsetzen'], 'record.mute':['Mikrofon stumm','Aufnahme ohne Raumton'], 'record.unmute':['Mikrofon freigeben','Raumton wieder aufnehmen'], 'talk.start':['Mit dem Brain sprechen','Gespeichertes Gesprächswissen nutzen'], 'talk.stop':['Gespräch beenden','Audioverbindung schließen'], 'talk.mute':['Mikrofon stumm','Im Gespräch stummschalten'], 'talk.unmute':['Mikrofon freigeben','Im Gespräch wieder sprechen']};
async function request(path, body){
 const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),10000);
 try{const response=await fetch(path,{cache:'no-store',signal:controller.signal,headers:body?{'Content-Type':'application/json','X-Portal-Request':'1','X-Portal-CSRF':session?.csrf||''}:{},method:body?'POST':'GET',body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok){const e=Error(result.error||'Anfrage fehlgeschlagen.');e.status=response.status;throw e}return result}finally{clearTimeout(timeout)}
}
function text(tag,value,className){const node=document.createElement(tag);node.textContent=value;if(className)node.className=className;return node}
function searchText(value){return value.toLocaleLowerCase('de').normalize('NFD').replace(/[\u0300-\u036f]/g,'')}
function showArticles(){
 const query=searchText(el('search').value.trim()),hash=decodeURIComponent(location.hash.slice(1)),selected=articles.find(a=>a.id===hash);
 document.body.classList.toggle('reading',Boolean(query||selected));
 el('articles').replaceChildren();el('topics').replaceChildren();
 const matches=articles.filter(a=>!query||searchText(JSON.stringify(a)).includes(query));
 el('search-count').textContent=query?`${matches.length} passende Anleitungen`:'';
 for(const a of articles){const link=text('a',a.title);link.href='#'+a.id;link.setAttribute('aria-current',String(selected===a));el('topics').append(link)}
 for(const a of (query?matches:selected?[selected]:articles)){
  const article=document.createElement('article');article.id='article-'+a.id;article.append(text('p',a.category,'eyebrow'),text('h2',a.title));
  if(a.intro)article.append(text('p',a.intro));
  for(const item of (a.links||[]).filter(x=>x.url.endsWith('.pdf'))){const link=text('a',item.label,'button primary');link.href=item.url;article.append(link)}
  if(a.image){const image=document.createElement('img');image.src=a.image;image.alt=a.alt||a.title;image.loading='lazy';article.append(image)}
  if(a.note)article.append(text('p',a.note,'note'));
  if(a.steps){const list=document.createElement('ol');for(const step of a.steps)list.append(text('li',step));article.append(list)}
  for(const p of a.paragraphs||[])article.append(text('p',p));
  for(const item of (a.links||[]).filter(x=>!x.url.endsWith('.pdf'))){const link=text('a',item.label,'article-link');link.href=item.url;if(item.url.startsWith('https:')){link.rel='noreferrer';link.target='_blank'}article.append(link)}
  if(a.source)article.append(text('p',a.source,'source'));
  el('articles').append(article);
 }
 if(!matches.length)el('articles').append(text('p','Kein Treffer. Versuche zum Beispiel „Aufnahme“, „Kabel“ oder „Anmelden“.','card'));
}
function route(){el('search').value='';const remote=location.hash==='#remote';el('help').hidden=remote;el('remote').hidden=!remote;el('help-tab').setAttribute('aria-current',remote?'false':'page');el('remote-tab').setAttribute('aria-current',remote?'page':'false');if(!remote)showArticles();else refresh();window.scrollTo(0,0)}
function renderRemote(){
 const secure=Boolean(info?.secure),paired=Boolean(session?.paired),waiting=Boolean(session&&!paired);
 document.body.classList.toggle('paired',paired);
 el('secure-entry').hidden=secure;el('pair-entry').hidden=!secure||waiting||paired;el('pair-wait').hidden=!waiting;el('controls').hidden=!paired;
 el('pair').disabled=working||!info?.enabled;el('secure-link').href=info?.control_url||'#';
 if(waiting){el('pair-code').textContent=session.code;el('pair-time').textContent=`Noch ${session.expires_in} Sekunden gültig.`}
 if(paired){
  const s=session.snapshot;el('controller-name').textContent=session.name;el('controller-time').textContent=`Freigabe noch etwa ${Math.ceil(session.expires_in/60)} Minuten. Bei Abmeldung endet sie sofort.`;
  el('device-state').textContent=s.recording?(s.paused?'Aufnahme pausiert':'Aufnahme läuft'):!['idle','ended','error'].includes(s.talk)?'Gespräch · '+({connecting:'Verbindung wird aufgebaut',closing:'wird beendet',listening:'bereit',thinking:'Brain arbeitet',speaking:'Brain antwortet',reconnecting:'verbindet erneut'}[s.talk]||s.talk):s.mode==='idle'?'Bereit':'Gerät beschäftigt';
  el('device-detail').textContent=s.recording?`${Math.floor(s.seconds/60)} min ${Math.floor(s.seconds%60)} s · ${s.muted?'Mikrofon stumm':'Mikrofon aktiv'}`:s.reason||'Wähle Talk oder Meeting.';
  const actions=el('control-actions'), key=s.allowed.join('|');
  if(actions.dataset.actions!==key){actions.dataset.actions=key;actions.replaceChildren();
  for(const action of s.allowed){const [label,detail]=labels[action]||[action,''];const button=document.createElement('button');button.append(text('strong',label),text('small',detail));if(action.endsWith('.start'))button.className='primary';button.disabled=working||!connected||Boolean(pending);button.onclick=()=>act(action);el('control-actions').append(button)}
  }
  for(const button of actions.children)button.disabled=working||!connected||Boolean(pending);
 }
 el('stop-confirm').hidden=!pending;el('stop-yes').disabled=working||!connected;el('stop-cancel').disabled=working;
 el('leave').disabled=working;el('cancel-pair').disabled=working;
}
async function refresh(){
 if(working)return;
 try{
  info=await request(location.pathname.startsWith('/help/')?'/api/portal/info':'/api/info');el('version').textContent='cdbPiOS '+info.version+' · Hilfe 23.11.2026';
  if(info.secure&&(session||!sessionChecked)){try{const wasPaired=session?.paired;session=await request('/api/session');sessionChecked=true;connected=true;if(connectionError||(!wasPaired&&session.paired))el('remote-message').textContent=session.paired?'Browser am Pi freigegeben.':'';connectionError=false;el('last-seen').textContent='Vom Pi bestätigt: '+new Date().toLocaleTimeString('de-DE');el('retry').hidden=true}catch(e){if(e.status!==403)throw e;if(session)el('remote-message').textContent='Freigabe beendet. Zum Bedienen bitte erneut am Pi koppeln.';sessionChecked=true;session=null;connected=false;pending=null}}
  renderRemote();
 }catch(e){connectionError=true;connected=false;renderRemote();el('remote-message').textContent='Pi nicht erreichbar. Eine laufende Aufnahme bleibt am Pi aktiv. Vor weiterer Bedienung Verbindung erneut prüfen.';el('retry').hidden=false}
}
async function act(action){
 if(working||!connected||!session?.paired)return;
 const command={id:crypto.randomUUID(),action,ticket:session.ticket};
 if(action.endsWith('.stop')){pending=command;el('stop-heading').textContent=action==='record.stop'?'Aufnahme am Pi stoppen?':'Gespräch am Pi beenden?';renderRemote();el('stop-cancel').focus({preventScroll:true});el('stop-confirm').scrollIntoView({block:'center',behavior:'smooth'});return}
 await send(command);
}
async function send(command){const wasStop=Boolean(pending);working=true;renderRemote();el('remote-message').textContent='Wird am Pi ausgeführt …';try{const result=await request('/api/command',command);el('remote-message').textContent=result.message}catch(e){el('remote-message').textContent=e.name==='AbortError'?'Antwort fehlt. Bitte den tatsächlichen Status am Pi prüfen; der Auftrag wird nicht automatisch wiederholt.':e.message}finally{pending=null;working=false;await refresh();if(wasStop)el('device-state').scrollIntoView({block:'center',behavior:'smooth'})}}
el('stop-yes').onclick=()=>{if(pending)send(pending)};el('stop-cancel').onclick=()=>{pending=null;renderRemote()};
el('pair').onclick=async()=>{if(working)return;working=true;renderRemote();try{session=await request('/api/pair',{name:el('browser-name').value.trim()});el('remote-message').textContent='Bitte jetzt am Pi bestätigen.'}catch(e){el('remote-message').textContent=e.message}finally{working=false;renderRemote()}};
async function leave(){if(working)return;working=true;renderRemote();try{await request('/api/leave',{});session=null;pending=null;connected=false;el('remote-message').textContent='Dieser Browser ist entkoppelt. Ein laufender Vorgang am Pi bleibt bestehen.'}catch(e){el('remote-message').textContent=e.message}finally{working=false;renderRemote()}}
el('leave').onclick=el('cancel-pair').onclick=leave;el('retry').onclick=refresh;
el('search').addEventListener('input',showArticles);window.addEventListener('hashchange',route);
if(location.pathname.startsWith('/help/')){el('return-studio').hidden=false;el('remote-tab').hidden=true;el('keyboard').hidden=false;document.body.classList.add('on-pi');const script=document.createElement('script');script.src='/keyboard.js';document.head.append(script)}
fetch('./articles.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{articles=data;route()}).catch(()=>{el('articles').append(text('p','Hilfe konnte nicht geladen werden. Seite erneut öffnen.','card'))});
refresh();timer=setInterval(()=>{if(location.hash==='#remote'&&!document.hidden)refresh()},2000);
