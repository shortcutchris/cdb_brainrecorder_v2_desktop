const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('studio/room.js','utf8');
function harness(recording=false){
 const calls=[];
 const c={window:{},busy:false,recordingAction:false,online:true,allowed:()=>true,renderState(){},state:{recording:{id:recording?'active':null},live:{busy:false}},confirmAction:async()=>{calls.push('confirm');return true},flushAllDrafts:async()=>calls.push('save'),audio:{pause:()=>calls.push('pause')},api:async(path,body)=>{calls.push({path,...body});return {}},clearRoomDrafts:()=>calls.push('clear'),location:{reload:()=>calls.push('reload')}};
 vm.createContext(c);vm.runInContext(source.slice(source.indexOf(' function logoutBlocked('),source.indexOf(' end.onclick=run(')),c);return {c,calls};
}
test('explicit idle logout tile needs no second dialog and never authorizes stopping capture',async()=>{
 const {c,calls}=harness();await c.finish(true);assert.equal(calls.includes('confirm'),false);assert.equal(calls.find(v=>v.path)?.confirm,undefined);assert.equal(calls.at(-1),'reload');
});
test('recording, pause, Live, start transition and offline cannot initiate logout',async()=>{
 for(const patch of [{state:{recording:{id:'paused',paused:true},live:{busy:false}}},{state:{recording:{},live:{busy:true}}},{recordingAction:true},{online:false},{allowed:()=>false}]){
  const {c,calls}=harness();Object.assign(c,patch);await c.finish(true);await c.finish();assert.equal(calls.length,0);
 }
});
test('capture starting during confirmation or draft save leaves account and drafts intact',async()=>{
 for(const stage of ['confirm','save']){
  const {c,calls}=harness();let done;
  c[stage==='confirm'?'confirmAction':'flushAllDrafts']=()=>new Promise(r=>done=r);
  const pending=c.finish();await new Promise(setImmediate);c.state.recording.id='new';done(true);
  await assert.rejects(pending,/zuerst beenden/);assert.equal(calls.some(v=>v.path),false);assert.equal(calls.includes('clear'),false);assert.equal(c.busy,false);
 }
});
test('server rejection or failed draft save keeps account and local text without reload',async()=>{
 for(const stage of ['api','flushAllDrafts']){const {c,calls}=harness();c[stage]=async()=>{throw Error('not saved')};await assert.rejects(c.finish(),/not saved/);assert.equal(calls.includes('clear'),false);assert.equal(calls.includes('reload'),false);assert.equal(c.busy,false)}
});
test('two different logout entry points share one pending operation',async()=>{
 const {c,calls}=harness();let accept;c.confirmAction=()=>new Promise(r=>accept=r);
 const pending=c.finish();await c.window.finishRoomSession();await c.finish(true);assert.equal(calls.length,0);accept(true);await pending;assert.equal(calls.filter(v=>v.path).length,1);
});
