async page => {
 // Set true for candidate, false for unchanged frontend. Local synthetic preview only.
 const candidate=false;
 await page.unrouteAll({behavior:"wait"});
 if(candidate){
 await page.route('**/touch.js',async route=>{
  const response=await route.fetch();let body=await response.text();
  const from="p.bar.setAttribute('aria-label',label+' Seiten');";
  if(!body.includes(from))throw new Error('touch source mismatch');
  body=body.replace(from,"if(p.bar.getAttribute('aria-label')!==label+' Seiten')p.bar.setAttribute('aria-label',label+' Seiten');");
  await route.fulfill({response,body});
 });
 await page.route('**/device-status.js',async route=>{
  const response=await route.fetch();let body=await response.text();
  const edits=[
   ["$('wake-feedback-title').textContent=(w.word||'Aktivierungswort')+' erkannt';","const title=(w.word||'Aktivierungswort')+' erkannt';if($('wake-feedback-title').textContent!==title)$('wake-feedback-title').textContent=title;"],
   ["led.dataset.state=recognized&&!connected?'recognized':lastWake.enabled?(busy?'waiting':lastWake.state):'off';","const mode=recognized&&!connected?'recognized':lastWake.enabled?(busy?'waiting':lastWake.state):'off';if(led.dataset.state!==mode)led.dataset.state=mode;"],
   ["feedback.hidden=!recognized||Boolean(state?.recording?.id)||(!lastWake.testing&&connected);","const hidden=!recognized||Boolean(state?.recording?.id)||(!lastWake.testing&&connected);if(feedback.hidden!==hidden)feedback.hidden=hidden;"],
   ["$('wake-feedback-detail').textContent=lastWake.testing?'Lokaler Test · kein Gespräch':state?.live?.state==='error'?'Start fehlgeschlagen · bitte im Gespräch prüfen':state?.live?.busy&&['listening','thinking','speaking'].includes(state.live.state)?'Du kannst sprechen': 'Gespräch wird verbunden …';","const detail=lastWake.testing?'Lokaler Test · kein Gespräch':state?.live?.state==='error'?'Start fehlgeschlagen · bitte im Gespräch prüfen':state?.live?.busy&&['listening','thinking','speaking'].includes(state.live.state)?'Du kannst sprechen': 'Gespräch wird verbunden …';if($('wake-feedback-detail').textContent!==detail)$('wake-feedback-detail').textContent=detail;"],
   ["if(Date.now()>=recognizedUntil)feedback.hidden=true;","if(Date.now()>=recognizedUntil&&!feedback.hidden)feedback.hidden=true;"]
  ];
  for(const [from,to] of edits){if(!body.includes(from))throw new Error('device source mismatch');body=body.replace(from,to)}
  await route.fulfill({response,body});
 });

 }
 const wake={instance:'synthetic-perf',enabled:true,available:true,word:'Okay KAI',phrase:'okay-kai',state:'listening',message:'Bereit',detections:0,recognized_for:0,testing:false};
 await page.route('**/api/state',async route=>{const response=await route.fetch();const value=await response.json();value.wake=wake;await route.fulfill({response,json:value})});
 await page.route('**/api/wake/status',route=>route.fulfill({json:wake}));
 await page.reload();await page.waitForTimeout(3000);
 await page.evaluate(()=>{
   window.__mutationCounts={callbacks:0,total:0,targets:{}};
   window.__mutationProbe=new MutationObserver(rows=>{
    const out=window.__mutationCounts;out.callbacks++;out.total+=rows.length;
    for(const r of rows){const n=r.target.nodeType===1?r.target:r.target.parentElement;const id=n?.id||n?.closest('[id]')?.id||n?.nodeName||'unknown';const key=id+':'+r.type+':'+(r.attributeName||'');out.targets[key]=(out.targets[key]||0)+1}
   });
   window.__mutationProbe.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true});
 });
 const cdp=await page.context().newCDPSession(page);await cdp.send('Performance.enable');
 const metrics=async()=>Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x=>[x.name,x.value]));
 await cdp.send("HeapProfiler.collectGarbage");
 const start=await metrics();await page.waitForTimeout(30000);const end=await metrics();
 const mutations=await page.evaluate(()=>{window.__mutationProbe.disconnect();return window.__mutationCounts});
 await cdp.detach();
 return {localSyntheticOnly:true,candidate,seconds:30,mutations,start,end};
}
