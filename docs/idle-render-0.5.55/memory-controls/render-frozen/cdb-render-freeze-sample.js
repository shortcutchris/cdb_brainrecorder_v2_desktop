async page => {
 if(page.url()!=='http://127.0.0.1:8099/')throw new Error('Synthetic local preview required');
 const cdp=await page.context().newCDPSession(page);
 try{
  return {at:Date.now(),browser:await cdp.send('Browser.getVersion'),heap:await cdp.send('Runtime.getHeapUsage'),dom:await cdp.send('Memory.getDOMCounters'),page:await page.evaluate(()=>({url:location.href,hidden:document.hidden,visibility:document.visibilityState,attachedNodes:document.querySelectorAll('*').length,wakeState:document.querySelector('#wake-rail-led')?.dataset.state,frozenRenderCalls:window.__frozenRenderCalls}))};
 }finally{await cdp.detach()}
}
