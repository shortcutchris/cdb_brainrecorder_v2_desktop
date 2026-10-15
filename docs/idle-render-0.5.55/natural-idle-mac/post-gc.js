async page => {
 if(page.url()!=='http://127.0.0.1:8099/')throw new Error('Synthetic local preview required');
 const cdp=await page.context().newCDPSession(page);
 try{
  const before={at:Date.now(),heap:await cdp.send('Runtime.getHeapUsage'),dom:await cdp.send('Memory.getDOMCounters')};
  await cdp.send('HeapProfiler.collectGarbage');
  return {scope:'Separate post-window forced-GC diagnostic; not part of natural observation',before,after:{at:Date.now(),heap:await cdp.send('Runtime.getHeapUsage'),dom:await cdp.send('Memory.getDOMCounters')}};
 }finally{await cdp.detach()}
}
