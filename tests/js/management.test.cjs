const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(storage=new Map()){
 const nodes={},el=id=>nodes[id]??={hidden:false,dataset:{},textContent:'',open:false,querySelector:()=>el(id+'-actions'),showModal(){this.open=true},close(){this.open=false}},calls=[];
 const c={$:el,state:{version:'test',activity:{busy:false},management:{},recording:{},live:{},jobs:[],timers:{items:[]}},online:true,confirmAction:async()=>false,allowed:()=>true,document:{querySelector:()=>({content:'test'})},sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},location:{reload:()=>calls.push('reload'),search:''},URLSearchParams,history:{replaceState(){}},run:f=>f,flushAllDrafts:async()=>calls.push('saved'),api:async(path,body)=>calls.push([path,body]),poll:async()=>{},notice:()=>calls.push('notice'),renderState(){},showSettingsDetail(){}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/management.js','utf8'),c);return {c,el,calls};
}
test('restart needs an explicit dialog confirmation and saves before request',async()=>{
 const h=harness();await h.el('management-restart').onclick();assert.equal(h.calls.length,0);
 h.c.confirmAction=async()=>true;await h.el('management-restart').onclick();assert.equal(h.calls[0],'saved');assert.equal(h.calls[1][0],'/api/device/restart');assert.equal(h.calls[1][1].confirm,true);assert.equal(h.el('management-restart').disabled,true);
});
test('restart cannot race shutdown or work beginning while confirmation is open',async()=>{
 const h=harness();let answer;h.c.confirmAction=()=>new Promise(r=>answer=r);
 const pending=h.el('management-restart').onclick();await h.el('management-shutdown').onclick();await h.el('management-restart').onclick();assert.equal(h.calls.length,0);
 h.c.state.recording={id:'new'};answer(true);await assert.rejects(pending,/beschäftigt/);assert.equal(h.calls.some(Array.isArray),false);
 h.c.renderState();assert.equal(h.el('management-restart').disabled,true);
});
test('version mismatch reloads only once even if next page still has stale HTML',async()=>{const storage=new Map();const a=harness(storage);a.c.state.version='new';a.c.renderState();a.c.renderState();await new Promise(setImmediate);assert.deepEqual(a.calls,['saved','reload']);const b=harness(storage);b.c.state.version='new';b.c.renderState();await new Promise(setImmediate);assert.equal(b.calls.length,0)});
test('recording starting during draft save cancels automatic reload',async()=>{const h=harness();let done;h.c.flushAllDrafts=()=>new Promise(r=>done=r);h.c.state.version='new';h.c.renderState();h.c.state.recording={id:'recording'};done();await new Promise(setImmediate);assert.equal(h.calls.includes('reload'),false)});
test('unavailable storage cannot create a reload loop',async()=>{const h=harness();h.c.sessionStorage.getItem=()=>{throw Error('blocked')};h.c.state.version='new';h.c.renderState();await new Promise(setImmediate);assert.equal(h.calls.includes('reload'),false)});
test('shutdown cancel never sends a command; confirmation saves and locks repeated taps',async()=>{
 const h=harness();await h.el('management-shutdown').onclick();assert.equal(h.calls.length,0);
 let accept;h.c.confirmAction=()=>new Promise(r=>accept=r);
 const pending=h.el('management-shutdown').onclick();assert.equal(h.el('management-shutdown').disabled,true);
 await h.el('management-shutdown').onclick();h.c.api=async(path,body)=>{h.calls.push([path,body]);return {scheduled:true,command:'one'}};
 accept(true);await pending;assert.equal(h.calls[0],'saved');assert.equal(h.calls[1][0],'/api/device/shutdown');assert.equal(h.calls[1][1].confirm,true);
 assert.equal(h.el('shutdown-status').open,true);assert.equal(h.el('management-shutdown').disabled,true);
 await h.el('management-shutdown').onclick();assert.equal(h.calls.length,2);
 h.c.online=false;h.c.renderState();assert.equal(h.el('shutdown-status').open,true);assert.doesNotMatch(h.el('shutdown-heading').textContent,/ausgeschaltet|abziehen/);
});
test('work starting during confirmation or draft save cancels shutdown',async()=>{
 for(const stage of ['confirm','save']){const h=harness();let done;
  h.c.confirmAction=stage==='confirm'?()=>new Promise(r=>done=r):async()=>true;
  if(stage==='save')h.c.flushAllDrafts=()=>new Promise(r=>done=r);
  const pending=h.el('management-shutdown').onclick();await new Promise(setImmediate);h.c.state.recording={id:'active'};done(true);
  await assert.rejects(pending,/beschäftigt/);assert.equal(h.calls.some(c=>Array.isArray(c)&&c[0]==='/api/device/shutdown'),false);
 }
});
test('shutdown disabled for all active work and reported errors restore the button',async()=>{
 for(const state of [{recording:{id:'x'}},{live:{busy:true}},{activity:{busy:true}},{management:{maintenance:true}},{timers:{items:[{state:'scheduled'}]}},{jobs:[{state:'summarizing'}]},{cdb:{publications:[{state:'sending'}]}}]){
  const h=harness();Object.assign(h.c.state,state);h.c.renderState();assert.equal(h.el('management-shutdown').disabled,true);await h.el('management-shutdown').onclick();assert.equal(h.calls.length,0);
 }
 const h=harness();h.c.state.management.power={state:'requested',command:'a'};h.c.renderState();assert.equal(h.el('shutdown-status').open,true);
 h.c.state.management.power={state:'failed',command:'a'};h.c.renderState();assert.equal(h.el('management-shutdown').disabled,false);assert.match(h.el('shutdown-heading').textContent,/nicht abgeschlossen/);
 h.el('shutdown-dismiss').onclick();h.c.renderState();assert.equal(h.el('shutdown-status').open,false);
});
