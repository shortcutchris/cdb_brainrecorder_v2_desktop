const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={},el=id=>nodes[id]??={hidden:false,dataset:{},textContent:'',setAttribute(k,v){this[k]=v},append(){}};
 const c={$:el,document:{hidden:false,body:{append(){},classList:{toggle(){}}},createElement:()=>el('new'+Math.random())},state:{wake:{enabled:true,state:'listening',detections:0},timers:{items:[]},live:{busy:false}},online:true,renderState(){},setInterval(fn){c.tick=fn},api:async()=>c.reply};
 const old=c.document.createElement;c.document.createElement=()=>{const e=old();Object.defineProperty(e,'id',{set(id){nodes[id]=e}});return e};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/device-status.js','utf8'),c);return{c,el};
}
test('nearest countdown and due status remain available across workspace switches and locks',()=>{
 const {c,el}=harness();c.state.timers.items=[{label:'Tee',state:'scheduled',remaining:65},{label:'Kuchen',state:'scheduled',remaining:500}];c.renderState();assert.equal(el('timer-countdown').textContent,'01:05');assert.match(el('timers-open').title,/Tee.*weitere/);
 c.state.recording={id:'busy'};c.renderState();assert.equal(el('timer-countdown').textContent,'01:05');
 c.state.timers.items[0].state='due';c.renderState();assert.equal(el('timer-countdown').textContent,'Fällig');assert.equal(el('timers-open').dataset.timerState,'due');
 c.state.timers.items=[];c.renderState();assert.equal(el('timer-countdown').textContent,'');assert.equal(el('timers-open').dataset.timerState,'idle');
});
test('fast recognition feedback arrives without waiting for full state; no poll during recording or speech',async()=>{
 const {c,el}=harness();let calls=0;c.reply={enabled:true,state:'waiting',recognized_for:7,detections:1};c.api=async()=>{calls++;return c.reply};
 await c.tick();assert.equal(el('wake-feedback').hidden,false);assert.match(el('wake-feedback-detail').textContent,/verbunden/);
 c.state.live={busy:true,state:'listening'};c.state.wake=c.reply;c.renderState();assert.equal(el('wake-feedback').hidden,true);await c.tick();assert.equal(calls,1);
 c.state.recording={id:'record'};c.renderState();assert.equal(el('wake-feedback').hidden,true);await c.tick();assert.equal(calls,1);
 c.state.recording=null;c.state.live={busy:false};c.state.wake={enabled:true,recognized_for:0};c.renderState();assert.equal(el('wake-feedback').hidden,true);
});

test('recognition expires locally even when requests stall; stale state cannot re-arm it',async()=>{
 const {c,el}=harness();let now=1000;c.Date={now:()=>now};
 c.reply={enabled:true,state:'waiting',recognized_for:7,detections:1};await c.tick();assert.equal(el('wake-feedback').hidden,false);
 now=9000;c.api=()=>new Promise(()=>{});c.tick();assert.equal(el('wake-feedback').hidden,true);
 c.state.wake=c.reply;c.renderState();assert.equal(el('wake-feedback').hidden,true);
});

test('older snapshots never replay a detection; a new backend can reset its counter',async()=>{
 const {c,el}=harness();let now=1000;c.Date={now:()=>now};c.reply={enabled:true,recognized_for:7,detections:4,instance:'a'};
 await c.tick();now=9000;c.state.wake={...c.reply,detections:3};c.renderState();await c.tick();assert.equal(el('wake-feedback').hidden,true);
 c.reply={...c.reply,detections:1,instance:'b'};await c.tick();assert.equal(el('wake-feedback').hidden,false);
});
