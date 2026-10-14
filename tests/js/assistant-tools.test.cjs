const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={};
 function element(){return {hidden:false,dataset:{},textContent:'',value:'bell',open:false,classList:{toggle(){}},setAttribute(){},before(){},append(){},replaceChildren(){},close(){this.open=false}}}
 const el=id=>nodes[id]??=element();
 const c={$:el,document:{body:{append(){},classList:{toggle(){},contains(){return false}}},createElement:element,querySelectorAll(){return []},addEventListener(){}},state:{wake:{},timers:{items:[]},live:{busy:false}},online:true,
 workspaceView(){},renderState(){},run:fn=>fn,setInterval(){},drawPageNumbers(){},crypto:{randomUUID:()=> 'test-browser'},audio:{pause(){}},HTMLAudioElement:class{}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/assistant-tools.js','utf8'),c);return{c,el};
}
test('ringing alarm stays actionable during live and never claims it must wait for the conversation',()=>{
 const {c,el}=harness();c.state.live={busy:true};c.state.timers={items:[{id:'test',label:'Tee',state:'due',sound:'attempted'}],ringing_id:'test'};
 c.renderState();assert.match(el('alarm-detail').textContent,/Alarm läuft/);assert.equal(el('alarm-ack').disabled,false);assert.equal(el('alarm-snooze').disabled,false);
 c.state.timers.ringing_id=null;c.state.timers.items[0].sound='failed';c.renderState();assert.match(el('alarm-detail').textContent,/Lautsprecher nicht erreichbar/);
});
test('only a pending alarm waits for recording; a previously played alarm is not promised again',()=>{
 const {c,el}=harness();c.state.recording={id:'record'};c.state.timers={items:[{id:'test',label:'Tee',state:'due',sound:'pending'}]};
 c.renderState();assert.equal(el('alarm-detail').textContent,'Ton nach der Aufnahme');
 c.state.timers.items[0].sound='played';c.renderState();assert.equal(el('alarm-detail').textContent,'Zeit ist um');
});
