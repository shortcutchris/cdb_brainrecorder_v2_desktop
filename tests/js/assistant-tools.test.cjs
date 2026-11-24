const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(small=false){
 const nodes={};
 function element(){return {children:[],hidden:false,dataset:{},textContent:'',value:'bell',open:false,classList:{toggle(){}},setAttribute(){},before(){},append(...items){this.children.push(...items)},replaceChildren(){this.children=[]},close(){this.open=false}}}
 const el=id=>nodes[id]??=element();
 let lastPage;const c={window:{},matchMedia:()=>({matches:small,addEventListener(){}}),$:el,document:{body:{append(){},classList:{toggle(){},contains(){return false}}},createElement:element,querySelectorAll(){return []},addEventListener(){}},state:{wake:{},timers:{items:[]},live:{busy:false}},online:true,
 workspaceView(){},renderState(){},run:fn=>fn,setInterval(){},drawPageNumbers(nav,count,page,choose){lastPage={count,page,choose}},crypto:{randomUUID:()=> 'test-browser'},audio:{pause(){}},HTMLAudioElement:class{}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/assistant-tools.js','utf8'),c);return{c,el,get paging(){return lastPage}};
}
test('ringing alarm stays actionable during live and never claims it must wait for the conversation',()=>{
 const {c,el}=harness();c.state.live={busy:true};c.state.timers={items:[{id:'test',label:'Tee',state:'due',sound:'attempted'}],ringing_id:'test'};
 c.renderState();assert.match(el('alarm-detail').textContent,/Alarm läuft/);let opened;c.window={openTimerFocus:id=>opened=id};el('alarm-open').onclick();assert.equal(opened,'test');
 c.state.timers.ringing_id=null;c.state.timers.items[0].sound='failed';c.renderState();assert.match(el('alarm-detail').textContent,/Alarmton fehlgeschlagen/);
});
test('only a pending alarm waits for recording; a previously played alarm is not promised again',()=>{
 const {c,el}=harness();c.state.recording={id:'record'};c.state.timers={items:[{id:'test',label:'Tee',state:'due',sound:'pending'}]};
 c.renderState();assert.equal(el('alarm-detail').textContent,'Ton nach der Aufnahme');
 c.state.timers.items[0].sound='played';c.renderState();assert.equal(el('alarm-detail').textContent,'Zeit ist um');
});

test('setup page switches preserve duration, title and tone; kind changes return to time',()=>{
 const {el}=harness();el('timer-label').value='Workshop';el('timer-number').value='20';el('timer-unit').value='60';el('timer-tone').value='silent';
 el('timer-details-page').onclick();assert.equal(el('timer-time-panel').hidden,true);assert.equal(el('timer-details-panel').hidden,false);
 el('timer-time-page').onclick();assert.equal(el('timer-label').value,'Workshop');assert.equal(el('timer-number').value,'20');assert.equal(el('timer-tone').value,'silent');
 el('reminder-kind').onclick();assert.equal(el('timer-time-panel').hidden,false);assert.equal(el('reminder-date').hidden,false);assert.equal(el('timer-duration').hidden,true);assert.equal(el('timer-create').textContent,'Erinnerung speichern');
});
test('two entries per small Pi page, three on larger Pi; history and shrinking lists clamp page',()=>{
 for(const small of [true,false]){
  const h=harness(small);h.c.state.timers.items=Array.from({length:5},(_,i)=>({id:String(i),label:'Timer '+i,state:'scheduled',remaining:60,tone:'bell'}));h.c.renderState();
  assert.equal(h.el('timer-list').children.length,small?2:3);assert.equal(h.paging.count,small?3:2);
  h.paging.choose(h.paging.count-1);assert.equal(h.el('timer-list').children.length,small?1:2);
  h.c.state.timers.items.pop();h.c.renderState();assert.equal(h.paging.page,small?1:1);
  h.el('timer-history').onclick();assert.equal(h.paging.page,0);assert.equal(h.paging.count,1);assert.match(h.el('timer-list').children[0].textContent,/erledigten/);
 }
});
test('create uses selected setup on either page and shows new entry on correct small-screen page',async()=>{
 const h=harness(true);h.el('timer-label').value='Workshop';h.el('timer-number').value='12';h.el('timer-unit').value='60';h.el('timer-tone').value='silent';
 h.c.state.timers.items=Array.from({length:4},(_,i)=>({id:String(i),label:'Timer '+i,state:'scheduled',remaining:60,tone:'bell'}));
 let sent;h.c.api=async(path,body)=>{sent=body;h.c.state.timers.items.push({id:'new',label:body.label,state:'scheduled',remaining:720,tone:body.tone});return {id:'new'}};h.c.poll=async()=>{};
 h.el('timer-details-page').onclick();await h.el('timer-create').onclick();assert.equal(sent.seconds,720);assert.equal(sent.tone,'silent');assert.equal(sent.label,'Workshop');assert.equal(h.paging.page,2);assert.equal(h.el('timer-create').disabled,false);
});
