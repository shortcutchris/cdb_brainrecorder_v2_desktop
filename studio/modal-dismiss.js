/* Outside taps are cancellation requests, never synthetic clicks on the page below. */
(() => {
 let started=null;
 function outside(event){
  const dialog=event.target;
  if(dialog?.tagName!=='DIALOG'||!dialog.open||dialog.classList.contains('workspace-view')||!dialog.matches(':modal'))return null;
  const r=dialog.getBoundingClientRect();
  return event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom?dialog:null;
 }
 document.addEventListener('pointerdown',event=>{started=event.isPrimary!==false&&event.button===0?outside(event):null},true);
 document.addEventListener('pointercancel',()=>{started=null},true);
 document.addEventListener('click',event=>{
  const dialog=outside(event),same=dialog&&started===dialog;started=null;
  if(!same||event.detail===0)return;
  event.preventDefault();event.stopImmediatePropagation();
  // Existing cancel handlers own cleanup, pending-action guards and timer minimization.
  if(dialog.dispatchEvent(new Event('cancel',{cancelable:true}))&&dialog.open)dialog.close();
 },true);
})();
