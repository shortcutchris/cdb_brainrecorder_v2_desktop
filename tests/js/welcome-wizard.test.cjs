const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');

async function wizard(saved={},query=''){
 const nodes=new Map(),posts=[];
 const status={required:true,step:'welcome',allowed:true,csrf:'test',busy:false,management:{state:'unconfigured'},operation:{state:'idle'},installation:{state:'idle'},brain:{signed_in:false,server:'https://staging.cdbos.de',login:{state:'idle'}},...saved};
 function el(id){
  if(!nodes.has(id))nodes.set(id,{hidden:false,value:'',dataset:{},children:[],append(...kids){this.children.push(...kids)},replaceChildren(){this.children=[]},getAttribute(k){return this[k]},removeAttribute(k){delete this[k]}});
  return nodes.get(id)
 }
 let tick;const location={search:query};
 const c={document:{getElementById:el,querySelectorAll:()=>[],createElement:()=>el(Symbol())},setInterval(fn){tick=fn},URLSearchParams,AbortSignal,location,
  async fetch(path,opt){
   const body=opt.body&&JSON.parse(opt.body);if(body)posts.push([path,body]);
   if(path==='/api/onboarding/step')Object.assign(status,body);
   if(path==='/api/cdb/config')status.brain.server=body.server;
   if(path==='/api/models/install')status.installation={...body,state:'running',message:'Whisper-Modell wird heruntergeladen',completed:250,total:1000};
   const result=path==='/api/onboarding'?status:path==='/api/setup'?{catalog:{asr:[{id:'medium',installed:false,bytes:1000}],llm:[],whisper_runtime:true}}:{};
   return {ok:true,json:()=>structuredClone(result)}
  }};
 vm.createContext(c);
 for(const file of ['model-download','welcome'])vm.runInContext(fs.readFileSync('studio/'+file+'.js','utf8'),c);
 await new Promise(setImmediate);
 return {el,status,tick,posts,location}
}
test('resume network checks LAN first; Wi-Fi discovery runs once if disconnected',async()=>{
 for(const lan of [true,false]){
  const h=await wizard({step:'network'});
  assert.deepEqual(h.posts.map(x=>x[1].action),['status']);
  h.status.operation={id:'status-1',action:'status',state:'done',network:{devices:lan?[{type:'ethernet',state:'connected'}]:[],connectivity:'unknown'}};
  await h.tick();await h.tick();
  assert.deepEqual(h.posts.map(x=>x[1].action),lan?['status']:['status','scan']);
  assert.match(h.el('link-state').textContent,lan?/LAN verbunden/:/Kein Netzwerk/);
 }
});
test('a Pi without the Wi-Fi helper can recheck a newly plugged Ethernet cable',async()=>{
 const h=await wizard({step:'network'});
 h.status.operation={id:'status-1',action:'status',state:'done',network:{wifi_setup:false,devices:[]}};
 await h.tick();assert.equal(h.el('other-network').disabled,true);await h.el('scan').onclick();
 assert.deepEqual(h.posts.map(x=>x[1].action),['status','status']);
 h.status.operation={...h.status.operation,id:'status-2',network:{wifi_setup:false,devices:[{type:'ethernet',state:'connected (externally)'}]}};
 await h.tick();assert.match(h.el('link-state').textContent,/LAN verbunden/);
});
test('manual network entry returns to Studio without persisting a factory step',async()=>{
 const h=await wizard({step:'brain'},'?network=1');
 assert.match(h.el('heading').textContent,/Netzwerk/);await h.el('back').onclick();assert.equal(h.location.href,'/');
 assert.ok(h.posts.every(x=>x[0]!=='/api/onboarding/step'));
});
test('model download starts explicitly and renders measured bytes; the pending Brain code can be cancelled',async()=>{
 const h=await wizard({step:'models'});assert.equal(h.posts.length,0);
 await h.el('whisper-install').onclick();assert.equal(h.el('model-progress').value,25);
 assert.deepEqual(h.posts[0],['/api/models/install',{backend:'whisper',model:'medium'}]);
 h.status.installation.state='completed';await h.tick();await h.el('next').onclick();
 assert.equal(h.status.step,'brain');
 h.el('brain-server').value='https://cdbos.de';await h.el('brain-server').onchange({target:h.el('brain-server')});
 assert.equal(h.status.brain.server,'https://cdbos.de');
 h.status.brain.login={state:'pending',code:'TEST',url:'https://login.microsoft.com/device'};await h.tick();
 assert.equal(h.el('brain-code').textContent,'TEST');assert.equal(h.el('next').disabled,true);
 await h.el('brain-cancel').onclick();assert.equal(h.posts.at(-1)[0],'/api/cdb/login/cancel');
 h.status.brain.login={state:'idle'};await h.tick();assert.equal(h.el('brain-code').textContent,'');
 await h.el('next').onclick();assert.equal(h.status.step,'audio');await h.el('next').onclick();assert.equal(h.location.href,'/?setup=recorder');
});
