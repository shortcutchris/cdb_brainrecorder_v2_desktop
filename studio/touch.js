'use strict';
(()=>{
 document.addEventListener('dragstart',event=>{if(!event.target.closest('input,textarea,[contenteditable="true"]'))event.preventDefault()});
 const pagers=new Map();let scheduled=false;
 function isVisible(el){return Boolean(el.getClientRects().length)&&!el.closest('[hidden]')}
 function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;refresh()})}
 function install(el){
  if(pagers.has(el)||el.closest('#touch-picker'))return;
  const bar=document.createElement('nav');bar.className='touch-pager';const name=el.getAttribute('aria-label')||({ 'audio-page':'Audio', 'models-page':'Modelle', 'prompts-page':'Prompts', 'appearance-page':'Design' })[el.closest('.settings-page')?.id]||el.closest('dialog')?.querySelector('h2')?.textContent||'Inhalt';bar.setAttribute('aria-label',name+' blättern');
  const info=document.createElement('span'),numbers=document.createElement('div');numbers.className='direct-pages';
  bar.append(info,numbers);
  const actions=el.classList.contains('dialog-body')?el.parentElement.querySelector(':scope > .dialog-actions'):null;
  if(el.id==='editor')el.closest('.editor-wrap').querySelector('.editor-footer').prepend(bar);else if(el.id==='queue-panel')el.closest('#queue-region').append(bar);else if(actions){actions.prepend(bar);bar.classList.add('inline-pager')}else el.after(bar);
  pagers.set(el,{bar,info,numbers,name,signature:''});el.addEventListener('scroll',schedule,{passive:true});el.addEventListener('input',schedule);new ResizeObserver(schedule).observe(el);
 }
 function refresh(){
  for(const [el,p] of pagers){
   const label=el.getAttribute('aria-label')||p.name,visible=isVisible(el);if(p.bar.hidden===visible)p.bar.hidden=!visible;
   if(p.bar.getAttribute('aria-label')!==label+' Seiten')p.bar.setAttribute('aria-label',label+' Seiten');
   if(!visible||typeof drawPageNumbers!=='function')continue;
   const list=el.id==='queue-panel'?el:el.querySelector('#library-list');
   if(list){
    const items=[...list.children].filter(e=>e.classList.contains(el.id==='queue-panel'?'queue-row':'library-item'));
    const queue=el.id==='queue-panel',visibleRow=items.find(row=>!row.hidden);
    const rowSize=queue&&visibleRow?visibleRow.getBoundingClientRect().height+(parseFloat(getComputedStyle(visibleRow).marginBottom)||0):queue?124:96;
    const headerSize=queue?(el.querySelector('.queue-columns')?.getBoundingClientRect().height||0):0;
    const size=Math.max(1,Math.floor((el.clientHeight-24-headerSize)/Math.max(1,rowSize))),count=Math.max(1,Math.ceil(items.length/size));
    const content=items.map(e=>e.dataset.queueKey||e.textContent).join('|');if(content!==p.content){p.content=content;p.page=0}
    p.page=Math.min(p.page||0,count-1);items.forEach((row,i)=>{const hidden=Math.floor(i/size)!==p.page;if(row.hidden!==hidden)row.hidden=hidden});
    const signature=[count,p.page,size,content].join('|');if(signature===p.signature)continue;p.signature=signature;el.scrollTop=0;
    p.info.textContent='Seite '+(p.page+1)+' von '+count;
    drawPageNumbers(p.numbers,count,p.page,i=>{p.page=i;p.signature='';schedule()});continue;
   }
   const max=Math.max(0,el.scrollHeight-el.clientHeight),line=parseFloat(getComputedStyle(el).lineHeight)||24;
   const step=Math.max(line,Math.floor(el.clientHeight/line)*line),count=max>2?Math.ceil(max/step)+1:1;
   const current=max>2&&el.scrollTop>=max-2?count-1:Math.min(count-1,Math.floor((el.scrollTop+2)/step));
   const signature=[count,current,step,max,label].join('|');if(signature===p.signature)continue;p.signature=signature;
   p.info.textContent='Seite '+(current+1)+' von '+count;
   drawPageNumbers(p.numbers,count,current,i=>{el.scrollTop=Math.min(max,i*step);p.signature='';schedule()});
  }
  refreshSelects();
 }
 const selectButtons=new Map();let source=null,page=0,pageSize=4;
 const picker=document.createElement('dialog');picker.id='touch-picker';picker.setAttribute('aria-labelledby','touch-picker-title');
 picker.innerHTML='<div class="dialog-heading"><h2 id="touch-picker-title">Auswählen</h2><button class="dialog-stop" hidden>Aufnahme stoppen</button><button class="icon-button" id="picker-keyboard" aria-label="Bildschirmtastatur öffnen"><img src="/assets/keyboard.svg" alt=""></button><button class="icon-button" aria-label="Auswahl schließen"><img src="/assets/x.svg" alt=""></button></div><div class="dialog-search"><input id="picker-search" type="search" placeholder="Auswahl durchsuchen …" aria-label="Auswahl durchsuchen"></div><div class="dialog-body"></div><div class="dialog-actions"><span id="picker-position"></span><nav id="picker-pages" class="direct-pages" aria-label="Auswahlseiten"></nav></div>';
 document.body.append(picker);
 picker.querySelector('[aria-label="Auswahl schließen"]').onclick=()=>picker.close();picker.querySelector('#picker-keyboard').onclick=()=>{picker.querySelector('#picker-search').focus();document.getElementById('keyboard').click()};picker.querySelector('.dialog-stop').onclick=()=>document.getElementById('record').click();
 picker.querySelector('#picker-search').oninput=()=>{page=0;drawPicker()};
 function drawPicker(){
  if(!source)return;const height=picker.querySelector('.dialog-body').clientHeight;if(height>0)pageSize=Math.max(1,Math.min(4,Math.floor((height-24)/72)));if(source.disabled||!isVisible(selectButtons.get(source))){picker.close();return}
  const query=picker.querySelector('#picker-search').value.trim().toLocaleLowerCase('de');
  const options=[...source.options].filter(o=>!query||o.textContent.toLocaleLowerCase('de').includes(query)),pages=Math.max(1,Math.ceil(options.length/pageSize));page=Math.min(page,pages-1);
  const body=picker.querySelector('.dialog-body');body.replaceChildren();
  for(const option of options.slice(page*pageSize,(page+1)*pageSize)){
   const button=document.createElement('button');button.className='picker-option';button.type='button';button.textContent=option.textContent;button.disabled=option.disabled||option.parentElement.disabled;button.setAttribute('aria-pressed',String(option.selected));
   button.onclick=()=>{if(source.disabled||option.disabled)return;if(!source.contains(option)){drawPicker();return}source.value=option.value;source.dispatchEvent(new Event('change',{bubbles:true}));picker.close();refreshSelects()};body.append(button);
  }
  if(!options.length)body.textContent='Keine Einträge vorhanden.';
  picker.querySelector('#picker-position').textContent='Seite '+(page+1)+' von '+pages;
  if(typeof drawPageNumbers==='function')drawPageNumbers(picker.querySelector('#picker-pages'),pages,page,i=>{page=i;drawPicker()});
 }
 new ResizeObserver(()=>{if(picker.open)drawPicker()}).observe(picker.querySelector('.dialog-body'));
 function refreshSelects(){for(const [el,b] of selectButtons){if(b.disabled!==el.disabled)b.disabled=el.disabled;const text=el.selectedOptions[0]?.textContent||'Bitte auswählen';if(b.firstChild.textContent!==text)b.firstChild.textContent=text}}
 document.querySelectorAll('select').forEach(el=>{
  const b=document.createElement('button');b.type='button';b.className='touch-select';b.append(document.createElement('span'));const label=el.getAttribute('aria-label')||el.closest('label')?.firstChild.textContent.trim()||'Auswahl';b.setAttribute('aria-label',label+' auswählen');el.hidden=true;el.after(b);selectButtons.set(el,b);
  b.onclick=()=>{source=el;picker.querySelector('#picker-search').value='';pageSize=window.innerHeight<=650?3:4;page=Math.floor(Math.max(0,el.selectedIndex)/pageSize);picker.querySelector('h2').textContent=label;picker.showModal();drawPicker()};
 });
 document.querySelectorAll('.dialog-body:not(#settings>.dialog-body),textarea:not(#settings textarea),#queue-panel').forEach(install);
 new MutationObserver(schedule).observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['hidden','disabled','open','class']});
 window.addEventListener('resize',()=>{if(picker.open)drawPicker();schedule()});setInterval(()=>{schedule();if(picker.open&&source?.disabled)picker.close()},500);schedule();
})();
