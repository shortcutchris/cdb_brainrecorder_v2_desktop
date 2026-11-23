const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={},calls=[],origin={isConnected:true,focus(){this.focused=true}};
 function element(){return {dataset:{},open:false,textContent:'',hidden:false,disabled:false,setAttribute(){},focus(){},showModal(){this.open=true;this.shows=(this.shows||0)+1},close(){this.open=false}}}
 const el=id=>nodes[id]??=element();
 const c={$:el,window:{hideStudioKeyboard(){c.keyboardHidden=true}},document:{activeElement:origin,body:{append(){}},createElement(){const e=element();Object.defineProperty(e,'id',{set:id=>nodes[id]=e});return e},querySelectorAll(){return c.other?[c.other]:[]}},state:{timers:{items:[]},live:{busy:false},recording:{}},online:true,renderState(){},api:async(path,body)=>{calls.push({path,...body});const item=c.state.timers.items.find(i=>i.id===body.id);item.state=body.action==='snooze'?'scheduled':body.action==='cancel'?'cancelled':'done';item.revision++},poll:async()=>c.renderState()};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/timer-focus.js','utf8'),c);
 const timer=(id='a',state='scheduled',revision=1)=>({id,state,revision,label:'Tee',remaining:65,kind:'timer',sound:'pending'});
 return {c,el,calls,origin,timer};
}
test('large running timer minimizes without cancelling and can be reopened from history',async()=>{
 const {c,el,calls,timer,origin}=harness();c.state.timers.items=[timer()];c.state.recording.id='ongoing';
 c.window.openTimerFocus('a');assert.equal(el('timer-focus').open,true);assert.equal(c.keyboardHidden,true);
 assert.equal(el('timer-focus-time').textContent,'01:05');assert.match(el('timer-focus-context').textContent,/Aufnahme läuft weiter/);
 await el('timer-focus-secondary').onclick();assert.equal(el('timer-focus').open,false);assert.equal(calls.length,0);assert.equal(origin.focused,true);
 c.state.timers.items[0].state='done';c.window.openTimerFocus('a');assert.equal(el('timer-focus-primary').hidden,true);
 assert.equal(el('timer-focus-secondary-label').textContent,'Schließen');
});
test('expiration opens automatically once, minimizing keeps alarm available and snooze re-arms',async()=>{
 const {c,el,timer,calls}=harness();c.state.timers.items=[timer('a','due')];c.state.live.busy=true;c.renderState();
 assert.equal(el('timer-focus').open,true);assert.match(el('timer-focus-context').textContent,/verbunden/);
 el('timer-focus-close').onclick();for(let i=0;i<5;i++)c.renderState();assert.equal(el('timer-focus').open,false);
 c.window.openTimerFocus('a');await el('timer-focus-secondary').onclick();assert.equal(calls[0].action,'snooze');assert.equal(el('timer-focus').open,false);
 c.state.timers.items[0]={...timer('a','due',3)};c.renderState();assert.equal(el('timer-focus').open,true);
});
test('confirming multiple expired timers advances one at a time without changing target',async()=>{
 const {c,el,timer,calls}=harness();c.state.timers.items=[timer('a','due'),timer('b','due')];c.renderState();
 await el('timer-focus-primary').onclick();assert.equal(calls[0].id,'a');assert.equal(calls[0].action,'ack');assert.equal(el('timer-focus').open,true);
 await el('timer-focus-primary').onclick();assert.equal(calls[1].id,'b');assert.equal(el('timer-focus').open,false);
});
test('another dialog is not covered; loss of visible ownership closes private timer detail',()=>{
 const {c,el,timer}=harness();c.state.timers.items=[timer('a','due')];c.other={open:true};c.renderState();assert.equal(el('timer-focus').open,false);
 c.other=null;c.renderState();assert.equal(el('timer-focus').open,true);
 c.state.timers.items=[];c.renderState();assert.equal(el('timer-focus').open,false);
});
test('in-flight stop blocks repeated taps and cannot stop a different newly due timer',async()=>{
 const {c,el,timer}=harness();const calls=[];let release;
 c.state.timers.items=[timer()];c.window.openTimerFocus('a');c.api=(path,body)=>{calls.push(body);return new Promise(r=>release=r)};
 const first=el('timer-focus-primary').onclick();await el('timer-focus-primary').onclick();
 c.state.timers.items.push(timer('b','due'));c.renderState();assert.equal(el('timer-focus-primary').disabled,true);
 c.window.openTimerFocus('b');assert.equal(calls.length,1);assert.equal(calls[0].id,'a');assert.equal(calls[0].action,'cancel');assert.equal(calls[0].revision,1);
 c.state.timers.items[0].state='cancelled';release();await first;assert.equal(el('timer-focus').open,true);
});
test('offline and failed or stale requests never claim a timer was stopped',async()=>{
 const {c,el,timer}=harness();c.state.timers.items=[timer()];c.window.openTimerFocus('a');c.online=false;c.renderState();
 assert.equal(el('timer-focus-primary').disabled,true);assert.match(el('timer-focus-error').textContent,/unterbrochen/);
 c.online=true;c.api=async()=>{throw Error('Eintrag wurde geändert. Bitte aktualisieren.')};await el('timer-focus-primary').onclick();
 assert.equal(el('timer-focus').open,true);assert.match(el('timer-focus-error').textContent,/aktualisieren/);assert.equal(el('timer-focus-primary').disabled,false);
});
test('silent alarm never promises sound after a recording',()=>{
 const {c,el,timer}=harness();c.state.timers.items=[{...timer('a','due'),tone:'silent'}];c.state.recording.id='ongoing';c.renderState();
 assert.match(el('timer-focus-detail').textContent,/lautlos/);assert.doesNotMatch(el('timer-focus-detail').textContent,/wartet/);
});
