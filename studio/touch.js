'use strict';
(()=>{
 const pagers=new Map();let scheduled=false;
 function isVisible(el){return Boolean(el.getClientRects().length)&&!el.closest('[hidden]')}
 function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;refresh()})}
 function install(el){
  if(pagers.has(el)||el.closest('#touch-picker'))return;
  const bar=document.createElement('nav');bar.className='touch-pager';const name=el.getAttribute('aria-label')||({ 'audio-page':'Audio', 'models-page':'Modelle', 'prompts-page':'Prompts', 'appearance-page':'Design' })[el.closest('.settings-page')?.id]||el.closest('dialog')?.querySelector('h2')?.textContent||'Inhalt';bar.setAttribute('aria-label',name+' blättern');
  const info=document.createElement('span');const up=document.createElement('button'),down=document.createElement('button');up.type=down.type='button';up.textContent='↑ Zurück';down.textContent='Weiter ↓';up.setAttribute('aria-label',name+' nach oben');down.setAttribute('aria-label',name+' nach unten');
  // Clicking navigation must preserve the text cursor and on-screen keyboard.
  for(const b of [up,down])b.onpointerdown=e=>e.preventDefault();
  up.onclick=()=>{el.scrollTop=Math.max(0,el.scrollTop-Math.max(48,el.clientHeight*.8));schedule()};down.onclick=()=>{el.scrollTop+=Math.max(48,el.clientHeight*.8);schedule()};
  bar.append(info,up,down);el.after(bar);pagers.set(el,{bar,info,up,down});el.addEventListener('scroll',schedule,{passive:true});el.addEventListener('input',schedule);new ResizeObserver(schedule).observe(el);
 }
 function refresh(){
  for(const [el,p] of pagers){const visible=isVisible(el);const max=Math.max(0,el.scrollHeight-el.clientHeight);const show=visible&&max>2; // Keep the controls while they themselves consume space.
   if(p.bar.hidden===show)p.bar.hidden=!show;
   const up=el.scrollTop<=1,down=el.scrollTop>=max-2;if(p.up.disabled!==up)p.up.disabled=up;if(p.down.disabled!==down)p.down.disabled=down;
   const text=max>0?Math.round(Math.min(100,el.scrollTop/max*100))+' %':'';if(p.info.textContent!==text)p.info.textContent=text;
  }
  refreshSelects();
 }
 const selectButtons=new Map();let source=null,page=0,pageSize=4;
 const picker=document.createElement('dialog');picker.id='touch-picker';picker.setAttribute('aria-labelledby','touch-picker-title');
 picker.innerHTML='<div class="dialog-heading"><h2 id="touch-picker-title">Auswählen</h2><button class="dialog-stop" hidden>Aufnahme stoppen</button><button class="icon-button" aria-label="Auswahl schließen">×</button></div><div class="dialog-body"></div><div class="dialog-actions"><button id="picker-prev">↑ Zurück</button><span id="picker-position"></span><button id="picker-next">Weiter ↓</button></div>';
 document.body.append(picker);
 picker.querySelector('.icon-button').onclick=()=>picker.close();picker.querySelector('.dialog-stop').onclick=()=>document.getElementById('record').click();
 picker.querySelector('#picker-prev').onclick=()=>{page=Math.max(0,page-1);drawPicker()};picker.querySelector('#picker-next').onclick=()=>{page++;drawPicker()};
 function drawPicker(){
  if(!source)return;if(source.disabled||!isVisible(selectButtons.get(source))){picker.close();return}
  const options=[...source.options],pages=Math.max(1,Math.ceil(options.length/pageSize));page=Math.min(page,pages-1);
  const body=picker.querySelector('.dialog-body');body.replaceChildren();
  for(const option of options.slice(page*pageSize,(page+1)*pageSize)){
   const button=document.createElement('button');button.className='picker-option';button.type='button';button.textContent=option.textContent;button.disabled=option.disabled||option.parentElement.disabled;button.setAttribute('aria-pressed',String(option.selected));
   button.onclick=()=>{if(source.disabled||option.disabled)return;if(!source.contains(option)){drawPicker();return}source.value=option.value;source.dispatchEvent(new Event('change',{bubbles:true}));picker.close();refreshSelects()};body.append(button);
  }
  if(!options.length)body.textContent='Keine Einträge vorhanden.';
  picker.querySelector('#picker-prev').disabled=page===0;picker.querySelector('#picker-next').disabled=page>=pages-1;picker.querySelector('#picker-position').textContent=(page+1)+' / '+pages;
 }
 function refreshSelects(){for(const [el,b] of selectButtons){b.disabled=el.disabled;const text=el.selectedOptions[0]?.textContent||'Bitte auswählen';if(b.firstChild.textContent!==text)b.firstChild.textContent=text}}
 document.querySelectorAll('select').forEach(el=>{
  const b=document.createElement('button');b.type='button';b.className='touch-select';b.append(document.createElement('span'));const label=el.getAttribute('aria-label')||el.closest('label')?.firstChild.textContent.trim()||'Auswahl';b.setAttribute('aria-label',label+' auswählen');el.hidden=true;el.after(b);selectButtons.set(el,b);
  b.onclick=()=>{source=el;pageSize=window.innerHeight<=650?3:4;page=Math.floor(Math.max(0,el.selectedIndex)/pageSize);picker.querySelector('h2').textContent=label;picker.showModal();drawPicker()};
 });
 document.querySelectorAll('.dialog-body:not(#settings>.dialog-body),textarea:not(#settings textarea),#queue-panel').forEach(install);
 new MutationObserver(schedule).observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['hidden','disabled','open','class']});
 window.addEventListener('resize',()=>{if(picker.open)drawPicker();schedule()});setInterval(()=>{schedule();if(picker.open&&source?.disabled)picker.close()},500);schedule();
})();
