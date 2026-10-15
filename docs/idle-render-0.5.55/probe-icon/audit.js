async page => {
 const response=await page.request.get('http://127.0.0.1:8099/api/state');let preflight;
 try{preflight=await response.json()}finally{await response.dispose()}
 if(preflight.preview!==true)throw new Error('Synthetic preview required');
 const old="$('probe-play-icon').src='/assets/'+(probeAudio.paused?'play':'pause')+'.svg';";
 const fixed="setIcon($('probe-play-icon'),'/assets/'+(probeAudio.paused?'play':'pause')+'.svg');";
 let phase='',requests=0;
 page.on('request',r=>{if(phase&&new URL(r.url()).pathname==='/assets/play.svg')requests++});
 const output={scope:'Local preview, same running browser, no audio; source interception only',runs:[]};
 for(const mode of ['original','guarded']){
  if(mode==='guarded')await page.route('**/microphone.js',async route=>{const r=await route.fetch();try{const text=await r.text();if(!text.includes(old))throw new Error('Original assignment absent');await route.fulfill({response:r,body:text.replace(old,fixed)})}finally{await r.dispose()}});
  await page.reload();await page.waitForFunction(()=>online&&state!==null);await page.waitForTimeout(1500);
  await page.evaluate(()=>{window.iconAudit={mutations:0,loads:0};const icon=document.querySelector('#probe-play-icon');window.iconAuditObserver=new MutationObserver(rows=>{window.iconAudit.mutations+=rows.filter(r=>r.attributeName==='src').length});window.iconAuditObserver.observe(icon,{attributes:true,attributeFilter:['src']});icon.addEventListener('load',()=>window.iconAudit.loads++)});
  phase=mode;requests=0;const start=Date.now();await page.waitForTimeout(12000);
  output.runs.push({mode,start,end:Date.now(),requests,...await page.evaluate(()=>{window.iconAuditObserver.disconnect();return window.iconAudit})});phase='';
 }
 return output;
}
