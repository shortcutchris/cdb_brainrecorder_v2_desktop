async page => {
 if(page.url()!=='http://127.0.0.1:8099/')throw new Error('Local synthetic preview required');
 const preflight=await (await page.request.get('http://127.0.0.1:8099/api/state')).json();
 if(preflight.preview!==true)throw new Error('Not a preview');
 await page.route('http://127.0.0.1:8099/',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Static diagnostic control</title></head><body><p id="wake-rail-led" data-state="listening">Static diagnostic control; no application code.</p></body></html>'}));
 await page.reload();
 const cdp=await page.context().newCDPSession(page);
 try{await cdp.send('HeapProfiler.collectGarbage')}finally{await cdp.detach()}
 return {scope:'Static local page; no app scripts or polling; same one-minute CDP sampling; GC before start only',backendVersion:preflight.version,sessions:0,startedAt:Date.now(),viewport:page.viewportSize()};
}
