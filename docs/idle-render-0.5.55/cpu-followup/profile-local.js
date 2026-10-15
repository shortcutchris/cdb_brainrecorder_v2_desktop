async page => {
 if(page.url()!=='http://127.0.0.1:8099/')throw new Error('Local preview required');
 const response=await page.request.get('http://127.0.0.1:8099/api/state');let preflight;
 try{preflight=await response.json()}finally{await response.dispose()}
 if(preflight.preview!==true)throw new Error('Synthetic preview required');
 const wake={instance:'cpu-test',enabled:true,available:true,word:'Okay KAI',phrase:'okay-kai',state:'listening',message:'Bereit',detections:0,recognized_for:0,testing:false};
 await page.route('**/api/state',async route=>{const r=await route.fetch();try{const value=await r.json();if(value.preview!==true)throw new Error('Preview guard');await route.fulfill({response:r,json:{...value,wake}})}finally{await r.dispose()}});
 await page.route('**/api/wake/status',route=>route.fulfill({json:wake}));
 await page.setViewportSize({width:1280,height:720});await page.reload();
 await page.waitForFunction(()=>document.querySelector('#wake-rail-led')?.dataset.state==='listening');
 await page.waitForTimeout(5000);
 const cdp=await page.context().newCDPSession(page);await cdp.send('Performance.enable');await cdp.send('Profiler.enable');
 const output={scope:'Local synthetic preview; profiler changes instrumentation; no Pi or audio',backendVersion:preflight.version,browser:await cdp.send('Browser.getVersion'),runs:[]};
 for(const mode of ['normal','render-frozen']){
  if(mode==='render-frozen')await page.evaluate(()=>{window.__savedRenderState=renderState;window.__frozen=0;renderState=()=>{window.__frozen++}});
  const started=Date.now(),before=await cdp.send('Performance.getMetrics');await cdp.send('Profiler.start');await page.waitForTimeout(15000);
  const {profile}=await cdp.send('Profiler.stop');const after=await cdp.send('Performance.getMetrics');
  output.runs.push({mode,started,ended:Date.now(),before,after,profile});
 }
 await page.evaluate(()=>{renderState=window.__savedRenderState;delete window.__savedRenderState});
 await cdp.detach();return output;
}
