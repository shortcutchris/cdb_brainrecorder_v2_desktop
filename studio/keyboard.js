'use strict';
// Local input only. No OS input injection, downloads or browser permissions.
(()=>{
 let target=null,shift=false,numeric=false;
 const panel=document.createElement('section');panel.className='touch-keyboard';panel.hidden=true;panel.setAttribute('aria-label','Bildschirmtastatur');
 const editable=el=>el instanceof HTMLTextAreaElement||el instanceof HTMLInputElement&&['text','search','url','email','tel'].includes(el.type);
 document.addEventListener('focusin',event=>{if(editable(event.target)){target=event.target;if(!panel.hidden)requestAnimationFrame(()=>target?.scrollIntoView({block:'nearest'}))}});
 function hide(){panel.hidden=true;document.body.classList.remove('keyboard-open');document.querySelectorAll('dialog').forEach(d=>d.classList.remove('with-keyboard'))}
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
  (dialog||document.body).append(panel);panel.hidden=false;document.body.classList.add('keyboard-open');if(dialog)dialog.classList.add('with-keyboard');draw();target?.focus({preventScroll:true});requestAnimationFrame(()=>target?.scrollIntoView({block:'nearest'}));
 }
 document.getElementById('keyboard').onclick=toggle;
 document.addEventListener('click',event=>{if(event.target.closest('#library-open,#settings-open,#more-open'))hide()},true);
 for(const dialog of document.querySelectorAll('dialog')){
  const button=document.createElement('button');button.type='button';button.className='icon-button';button.setAttribute('aria-label','Bildschirmtastatur öffnen');const icon=document.createElement('img');icon.src='/assets/keyboard.svg';icon.alt='';button.append(icon);dialog.querySelector('.dialog-heading').insertBefore(button,dialog.querySelector('[data-close]'));
  button.onclick=toggle;dialog.addEventListener('close',hide);
 }
 document.body.append(panel);
})();
