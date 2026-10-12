'use strict';
// Local input only. No OS input injection, downloads or browser permissions.
(()=>{
 let target=null,shift=false,numeric=false;
 const panel=document.createElement('section');panel.className='touch-keyboard';panel.hidden=true;panel.setAttribute('aria-label','Bildschirmtastatur');
 function focusSettings(el){document.querySelectorAll('.keyboard-muted').forEach(x=>x.classList.remove('keyboard-muted'));const settings=el?.closest('#settings.with-keyboard');if(!settings)return;let node=el.closest('label')||el;while(node&&node.parentElement&&!node.parentElement.classList.contains('settings-page')){for(const sibling of node.parentElement.children)if(sibling!==node)sibling.classList.add('keyboard-muted');if(node.parentElement.classList.contains('settings-content'))break;node=node.parentElement}}
 const editable=el=>el instanceof HTMLTextAreaElement||el instanceof HTMLInputElement&&['text','search','url','email','tel'].includes(el.type);
 document.addEventListener('focusin',event=>{if(editable(event.target)){target=event.target;focusSettings(target);if(!panel.hidden)requestAnimationFrame(()=>target?.scrollIntoView({block:'nearest'}))}});
 function hide(){document.querySelectorAll('.keyboard-muted').forEach(x=>x.classList.remove('keyboard-muted'));panel.hidden=true;document.body.classList.remove('keyboard-open');document.querySelectorAll('dialog').forEach(d=>d.classList.remove('with-keyboard'))}
 function draw(){
  panel.replaceChildren();
  const rows=numeric?[['1','2','3','4','5','6','7','8','9','0'],['@','#','€','%','&','(',')','/',';',':','?'],['⇧','+','-','*','=','!','"',"'",'_','\\','§','⌫']]:[['q','w','e','r','t','z','u','i','o','p','ü'],['a','s','d','f','g','h','j','k','l','ö','ä'],['⇧','y','x','c','v','b','n','m',',','.','ß','⌫']];
  rows.push(['123','←','→','Leertaste','Enter','Tastatur schließen']);
  for(const keys of rows){
   const row=document.createElement('div');row.className='key-row';panel.append(row);
   for(const key of keys){const button=document.createElement('button');button.type='button';button.textContent=key==='123'?(numeric?'ABC':'123'):key.length===1&&shift?key.toUpperCase():key;button.setAttribute('aria-label',key.length===1?'Taste '+button.textContent:key==='123'?'Zahlen und Buchstaben wechseln':key);if(key==='Leertaste')button.className='space';
    button.onpointerdown=e=>e.preventDefault();button.onclick=()=>press(key);row.append(button)}
  }
 }
 function press(key){
  if(key==='Tastatur schließen'){hide();return}
  if(key==='123'){numeric=!numeric;draw();return}
  if(key==='⇧'){shift=!shift;draw();return}
  if(!target||!target.isConnected||target.disabled||target.readOnly||!target.getClientRects().length)return;
  target.focus({preventScroll:true});let a=target.selectionStart??target.value.length,b=target.selectionEnd??a;
  if(key==='←'||key==='→'){const position=Math.max(0,Math.min(target.value.length,a+(key==='←'?-1:1)));target.setSelectionRange(position,position);return}
  if(key==='Enter'&&!(target instanceof HTMLTextAreaElement)){hide();return}
  if(key==='⌫'){if(a===b)a=Math.max(0,a-1);target.setRangeText('',a,b,'end')}
  else target.setRangeText(key==='Enter'?'\n':key==='Leertaste'?' ':shift?key.toUpperCase():key,a,b,'end');
  target.dispatchEvent(new Event('input',{bubbles:true}));
 }
 function toggle(){
  if(!panel.hidden){hide();return}
  const dialog=document.querySelector('dialog[open]');
  if(!target||!target.isConnected||target.disabled||target.readOnly||!target.getClientRects().length||(dialog&&!dialog.contains(target)))target=[...(dialog||document).querySelectorAll('textarea:not([disabled]):not([readonly]),input:not([disabled]):not([readonly])')].find(el=>editable(el)&&el.getClientRects().length);
  if(!target)return;
  (dialog||document.body).append(panel);panel.hidden=false;document.body.classList.add('keyboard-open');if(dialog)dialog.classList.add('with-keyboard');draw();target?.focus({preventScroll:true});focusSettings(target);requestAnimationFrame(()=>target?.scrollIntoView({block:'nearest'}));
 }
 document.getElementById('keyboard').onclick=toggle;
 document.addEventListener('click',event=>{if(event.target.closest('#library-open,#settings-open,#queue-toggle,#queue-close,#settings-overview-back,[data-settings-tile],#more-open,#theme-save,#theme-cancel,[data-settings]'))hide()},true);
 for(const dialog of document.querySelectorAll('dialog')){
  dialog.addEventListener('close',hide);const heading=dialog.querySelector('.dialog-heading');if(!heading||dialog.classList.contains('workspace-view')||!dialog.querySelector('textarea:not([readonly]),input:not([readonly])'))continue;
  const button=document.createElement('button');button.type='button';button.className='icon-button';button.setAttribute('aria-label','Bildschirmtastatur öffnen');const icon=document.createElement('img');icon.src='/assets/keyboard.svg';icon.alt='';button.append(icon);heading.insertBefore(button,dialog.querySelector('[data-close]'));
  button.onclick=toggle;
 }
 document.body.append(panel);
 function refreshAvailability(){
  const canEdit=[...document.querySelectorAll('textarea:not([disabled]):not([readonly]),input:not([disabled]):not([readonly])')].some(el=>editable(el)&&el.getClientRects().length);
  const button=document.getElementById('keyboard'),disabled=panel.hidden&&!canEdit;if(button.disabled!==disabled)button.disabled=disabled;
 }
 new MutationObserver(refreshAvailability).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','disabled','readonly','open','class']});refreshAvailability();
})();
