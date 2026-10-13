/* Read-only, bounded polling; never retains credentials or chat in browser storage. */
(() => {
 const $=id=>document.getElementById(id);
 let connected=false,history=[],session='',revision='',pages=[],page=0,follow=true,loading=false,paired=false,expires=0;
 const labels={idle:'Bereit',connecting:'Verbindet …',listening:'Hört zu',thinking:'Denkt nach …',speaking:'Spricht',reconnecting:'Verbindet erneut …',closing:'Wird beendet …',ended:'Gespräch beendet',error:'Gespräch beendet'};
 async function request(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Display-Request':'1'}:{},body:body?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(6000)});const data=await r.json();if(!r.ok){const e=new Error(data.error||'Verbindung fehlgeschlagen');e.status=r.status;throw e}return data}
 function connection(ok,label){connected=ok;$('connection').dataset.connected=String(ok);$('connection').textContent=label}
 function reset(message){expires=0;paired=false;history=[];pages=[];revision='';session='';$('messages').replaceChildren();$('areas').textContent='';$('pages').replaceChildren();$('conversation').hidden=true;$('pairing').hidden=false;$('leave').hidden=true;$('follow').hidden=true;$('begin').disabled=false;$('begin').textContent='Code anfordern';$('code-label').textContent='Bereit zum Koppeln';$('expiry').textContent='Der Code gilt zwei Minuten.';$('name').disabled=false;$('pair-message').textContent=message||'Nur im vertrauten lokalen Netzwerk verwenden.';$('code').textContent='— — —';$('footer-status').textContent='Textanzeige · kein Mikrofonzugriff';connection(false,'Nicht gekoppelt')}
 function pending(data){paired=false;$('conversation').hidden=true;$('pairing').hidden=false;$('code').textContent=data.code;$('code-label').textContent='Diesen Code am Pi eingeben';expires=Date.now()+data.expires_in*1000;$('begin').textContent='Neuen Code anfordern';$('pair-message').textContent='Am Pi den Code bestätigen. Erst danach wird der Verlauf freigegeben.';connection(false,'Wartet auf den Pi')}
 function article(row,text){const el=document.createElement('article');el.dataset.role=row.role;const name=document.createElement('strong'),p=document.createElement('p');name.textContent=row.role==='user'?'Du':'Brain';p.textContent=text;el.append(name,p);return el}
 function paginate(){
  if(!paired)return;const height=$('messages').clientHeight-18,measure=$('measure');if(height<80)return;
  pages=[];let rows=[],used=0;
  const finish=()=>{if(rows.length)pages.push(rows);rows=[];used=0};
  for(const row of history){let rest=String(row.text||'');while(rest){let room=height-used-(rows.length?18:0);if(room<90&&rows.length){finish();continue}
    const fits=text=>{measure.replaceChildren(article(row,text));return measure.firstChild.getBoundingClientRect().height<=room};
    let take=rest.length;if(!fits(rest)){let lo=1,hi=rest.length;while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(fits(rest.slice(0,mid)))lo=mid;else hi=mid-1}take=lo;const word=rest.lastIndexOf(' ',take);if(word>take*.65)take=word+1}
    const text=rest.slice(0,take);measure.replaceChildren(article(row,text));used+=measure.firstChild.getBoundingClientRect().height+(rows.length?18:0);rows.push({...row,text});rest=rest.slice(take);if(rest)finish();
  }}finish();measure.replaceChildren();page=follow?Math.max(0,pages.length-1):Math.min(page,Math.max(0,pages.length-1));draw();
 }
 function draw(){const box=$('messages');box.replaceChildren();for(const row of pages[page]||[])box.append(article(row,row.text));if(!pages.length){const p=document.createElement('p');p.className='empty';p.textContent='Dein nächstes Gespräch erscheint hier.';box.append(p)}
  const count=Math.max(1,pages.length),nav=$('pages');nav.replaceChildren();const add=(label,target,aria)=>{const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-label',aria);b.disabled=target<0||target>=count;if(label!== '‹'&&label!== '›')b.setAttribute('aria-current',target===page?'page':'false');b.onclick=()=>{page=target;follow=false;draw()};nav.append(b)};
  add('‹',page-1,'Vorherige Gesprächsseite');const start=Math.max(0,Math.min(page-1,count-3));const visible=new Set([0,count-1]);for(let i=start;i<Math.min(count,start+3);i++)visible.add(i);for(const i of [...visible].sort((a,b)=>a-b))add(String(i+1),i,'Gesprächsseite '+(i+1));add('›',page+1,'Nächste Gesprächsseite');$('footer-status').textContent=history.length+' Beiträge · Seite '+(page+1)+' / '+count;$('follow').disabled=follow;$('follow').textContent=follow?'Beim neuesten Beitrag':'Zum neuesten Beitrag';
 }
 async function refresh(){if(loading)return;loading=true;try{
  let data=await request('/api/display?revision='+encodeURIComponent(revision));
  if(!data.paired){pending(data);return}
  const needsRender=!data.unchanged||!paired;
  if(!data.unchanged){const first=data;let all=data.history||[];while(data.more){data=await request('/api/display?offset='+all.length);if(!data.paired||data.revision!==first.revision){return}all=all.concat(data.history)}
   if(session!==first.session){history=[];follow=true;page=0}session=first.session;history=all;revision=first.revision;data=first;
  }
  paired=true;$('pairing').hidden=true;$('conversation').hidden=false;$('leave').hidden=false;$('follow').hidden=false;connection(true,'Mit dem Pi verbunden');$('phase').textContent=labels[data.state]||'Bereit';$('areas').textContent=data.areas.length?'Gesprächswissen · '+data.areas.join(' · '):'Warte auf das nächste Gespräch am Pi';if(needsRender)paginate();
 }catch(e){if(e.status===401){reset(paired||expires?e.message:'Fordere einen Code an und bestätige ihn am Pi.')}else{history=[];pages=[];revision='';$('messages').replaceChildren();$('areas').textContent='';$('pages').replaceChildren();$('pair-message').textContent=e.message;connection(false,'Verbindung unterbrochen');$('phase').textContent='Warte auf den Pi …'}}finally{loading=false}}
 $('begin').onclick=async()=>{if(loading)return;loading=true;$('begin').disabled=true;try{await request('/api/leave',{});const data=await request('/api/begin',{name:$('name').value});pending(data)}catch(e){$('pair-message').textContent=e.message}finally{loading=false;$('begin').disabled=false}};
 $('leave').onclick=async()=>{try{await request('/api/leave',{});reset('Verbindung getrennt. Du kannst jederzeit einen neuen Code anfordern.')}catch(e){connection(false,'Trennen fehlgeschlagen');$('phase').textContent='Bitte am Pi entkoppeln.'}};
 $('follow').onclick=()=>{follow=true;page=Math.max(0,pages.length-1);draw()};
 new ResizeObserver(()=>{if(paired)paginate()}).observe($('messages'));
 setInterval(()=>{if(!paired&&expires)$('expiry').textContent='Noch '+Math.max(0,Math.ceil((expires-Date.now())/1000))+' Sekunden gültig.'},1000);
 setInterval(refresh,3000);refresh();
})();
