async page => {
 if(page.url()!=='http://127.0.0.1:8099/')throw new Error('Synthetic local preview required');
 const preflight=await (await page.request.get('http://127.0.0.1:8099/api/state')).json();
 if(preflight.preview!==true)throw new Error('Not a preview');
 const wake={instance:'synthetic-long-idle',enabled:true,available:true,word:'Okay KAI',phrase:'okay-kai',state:'listening',message:'Bereit',detections:0,recognized_for:0,testing:false};
 await page.route('**/api/state',async route=>{const response=await route.fetch();const value=await response.json();if(value.preview!==true)throw new Error('Not a preview');value.wake=wake;await route.fulfill({response,json:value})});
 await page.route('**/api/wake/status',route=>route.fulfill({json:wake}));
 await page.addInitScript(()=>{window.__diagnosticTimeoutCalls=0;AbortSignal.timeout=()=>{window.__diagnosticTimeoutCalls++;return undefined}});
 await page.reload();await page.waitForFunction(()=>document.querySelector('#wake-rail-led')?.dataset.state==='listening');
 await page.evaluate(()=>{window.__frozenRenderCalls=0;renderState=function(){window.__frozenRenderCalls++}});
 return {scope:'Local synthetic diagnostic control: renderState disabled and AbortSignal.timeout disabled; diagnostic only, not a safe production app',backendVersion:preflight.version,sessions:preflight.sessions.length,startedAt:Date.now(),viewport:page.viewportSize()};
}
