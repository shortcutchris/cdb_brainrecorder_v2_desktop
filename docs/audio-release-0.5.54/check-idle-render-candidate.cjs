// Isolated equivalence check for the HTTP-route candidate. No browser, audio or Pi access.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
async function candidateSources(){
 const routes=new Map(),stop=new Error('stop before browser reload');
 const script=fs.readFileSync('docs/audio-release-0.5.54/idle-render-comparison.js','utf8').replace('const candidate=false;','const candidate=true;');
 const run=vm.runInNewContext('('+script+')');
 try{await run({unrouteAll:async()=>{},route:async(pattern,handler)=>routes.set(pattern,handler),reload:async()=>{throw stop}})}catch(e){if(e!==stop)throw e}
 const out={};
 for(const name of ['device-status','touch']){
  const original=require('node:child_process').execFileSync('git',['show','14f9dc571b5d7f712bd12f4ba139009f893cb8d5:studio/'+name+'.js'],{encoding:'utf8'});let body;
  await routes.get('**/'+name+'.js')({fetch:async()=>({text:async()=>original}),fulfill:async value=>{body=value.body}});
  assert.equal(typeof body,'string');assert.equal(fs.readFileSync('studio/'+name+'.js','utf8'),body,'Runtime patch must match measured candidate');out[name]={original,candidate:body};
 }
 return out;
}
function deviceHarness(source){
 const nodes={};let writes=0,serial=0,now=1000;
 function element(id){
  if(nodes[id])return nodes[id];
  const values={hidden:false,textContent:''};
  const e={dataset:new Proxy({}, {set(o,k,v){writes++;o[k]=v;return true}}),setAttribute(k,v){writes++;this[k]=v},append(){}};
  for(const key of ['hidden','textContent'])Object.defineProperty(e,key,{get:()=>values[key],set:v=>{writes++;values[key]=v}});
  nodes[id]=e;return e;
 }
 const c={$:element,Date:{now:()=>now},document:{hidden:false,body:{append(){},classList:{toggle(){}}},createElement(){const e=element('new'+serial++);Object.defineProperty(e,'id',{set:id=>nodes[id]=e});return e}},online:true,renderState(){},setInterval(fn){c.tick=fn}};
 c.state={recording:null,live:{busy:false,state:'idle'},timers:{items:[]},wake:{enabled:true,state:'listening',word:'Okay KAI',phrase:'okay-kai',detections:0,recognized_for:0,instance:'initial'}};
 c.api=async()=>c.reply;vm.createContext(c);vm.runInContext(source,c);
 const snapshot=()=>JSON.parse(JSON.stringify({hidden:element('wake-feedback').hidden,title:element('wake-feedback-title').textContent,detail:element('wake-feedback-detail').textContent,led:element('wake-rail-led').dataset.state,timer:element('timer-countdown').textContent}));
 return {c,element,snapshot,writes:()=>writes,advance:ms=>now+=ms};
}
async function checkDevices(pair){
 const a=deviceHarness(pair.original),b=deviceHarness(pair.candidate);let steps=0;
 const step=async(action,expect)=>{for(const h of [a,b])await action(h);assert.deepEqual(b.snapshot(),a.snapshot());if(expect)expect(b);steps++};
 for(let round=0;round<100;round++){
  const base={enabled:true,state:'listening',word:round%2?'Hey Brain':'Okay KAI',detections:0,recognized_for:0,instance:'instance-'+round};
  await step(h=>{h.c.state.live={busy:false,state:'idle'};h.c.state.recording=null;h.c.state.wake={...base};h.c.renderState()});
  const detected={...base,state:'waiting',detections:1,recognized_for:7};
  await step(async h=>{h.c.reply={...detected};await h.c.tick()},h=>assert.equal(h.element('wake-feedback').hidden,false));
  await step(h=>{h.c.state.wake={...base};h.c.renderState()},h=>assert.equal(h.element('wake-feedback').hidden,false));
  await step(h=>{h.c.state.wake={...detected};h.c.state.live={busy:true,state:'connecting'};h.c.renderState()});
  for(const state of ['listening','thinking','speaking','closing'])await step(async h=>{h.c.state.live={busy:true,state};h.c.renderState();await h.c.tick()},h=>assert.equal(h.element('wake-feedback').hidden,true));
  await step(h=>{h.c.state.live={busy:false,state:'ended'};h.c.state.wake={...detected,recognized_for:0,state:'loading'};h.c.renderState()});
  await step(h=>{h.c.state.recording={id:'synthetic'};h.c.state.wake={...detected,detections:2};h.c.renderState()},h=>assert.equal(h.element('wake-feedback').hidden,true));
  await step(h=>{h.c.state.recording=null;h.c.state.live={busy:false,state:'idle'};h.c.state.wake={...base,detections:2};h.c.renderState()});
  await step(async h=>{h.c.reply={...detected,detections:3,testing:true,state:'testing'};await h.c.tick()},h=>assert.equal(h.element('wake-feedback').hidden,false));
  await step(async h=>{h.advance(10000);await h.c.tick()},h=>assert.equal(h.element('wake-feedback').hidden,true));
  await step(h=>{h.c.state.wake={...base,enabled:false,detections:3};h.c.renderState()});
 }
 assert.ok(b.writes()<a.writes());
 return {rounds:100,transition_checks:steps,equal_presentation:true,original_writes:a.writes(),candidate_writes:b.writes()};
}
function checkPager(pair){
 const counts=[];
 for(const variant of ['original','candidate']){
  const s=pair[variant],body=s.slice(s.indexOf(' function refresh(){'),s.indexOf(' const selectButtons='));let label='Audio',writes=0,stored='';
  const bar={hidden:false,getAttribute:()=>stored,setAttribute:(k,v)=>{writes++;stored=v}},element={getAttribute:()=>label};
  const c={pagers:new Map([[element,{bar,name:'fallback'}]]),isVisible:()=>false,refreshSelects(){}};
  vm.createContext(c);vm.runInContext(body,c);
  for(let i=0;i<100;i++)c.refresh();assert.equal(stored,'Audio Seiten');assert.equal(bar.hidden,true);
  const repeated=writes;label='Bibliothek';c.refresh();assert.equal(stored,'Bibliothek Seiten');
  counts.push({variant,repeated_writes:repeated,total_writes:writes});
 }
 assert.equal(counts[1].repeated_writes,1);assert.equal(counts[1].total_writes,2);
 return counts;
}
(async()=>{const sources=await candidateSources();console.log(JSON.stringify({scope:'Synthetic VM equivalence only; no Pi, real browser or acoustic acceptance',device:await checkDevices(sources['device-status']),pager:checkPager(sources.touch)},null,2))})().catch(e=>{console.error(e);process.exitCode=1});
