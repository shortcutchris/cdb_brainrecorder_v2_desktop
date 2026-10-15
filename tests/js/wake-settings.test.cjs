const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={},calls=[],events=[];let response={enabled:true,max_areas:8,areas:Array.from({length:10},(_,i)=>({id:'a'+i,label:'Bereich '+i})),remembered_area_ids:[],selection_account_key:'bound-account',audio:{available:true,microphone_label:'Array',speaker_label:'Marshall'}};
 const el=id=>nodes[id]??=({textContent:'',value:'',hidden:false,disabled:false,dataset:{},children:[],setAttribute(k,v){this[k]=v},replaceChildren(){this.children=[]},append(e){this.children.push(e)}});
 const c={$:el,document:{body:{classList:{contains:()=>false}},createElement:()=>el('new'+Math.random())},window:{innerHeight:900,dispatchEvent:e=>events.push(e.type)},Event:class{constructor(type){this.type=type}},online:true,state:{cdb:{identity:{name:'Test'},config:{server:'https://staging.cdbos.de'}},wake:{available:true,enabled:false},recording:{id:null},live:{busy:false}},showSettingsDetail(){},renderState(){},drawPageNumbers:(e,count,page,choose)=>Object.assign(e,{count,page,choose}),poll:async()=>{},api:async(path,body)=>{calls.push([path,body]);if(path==='/api/live/setup')return response;if(path==='/api/wake')c.state.wake.enabled=body.action==='on';return{}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/wake-settings.js','utf8'),c);
 return {c,el,calls,events,setResponse:r=>response=r,load:()=>el('wake-refresh').onclick()};
}
test('empty selection explains prerequisite inline, no premature activation; search and pages retain choices',async()=>{
 const h=harness();await h.load();assert.equal(h.el('wake-toggle').disabled,true);assert.match(h.el('wake-hint').textContent,/mindestens/);
 h.el('wake-areas').children[0].onclick();h.el('wake-area-pages').choose(2);h.el('wake-areas').children[1].onclick();assert.equal(h.el('wake-selected').textContent,'Ausgewählt (2)');
 h.el('wake-selected').onclick();assert.equal(h.el('wake-areas').children.length,2);h.el('wake-area-search').value='7';h.el('wake-area-search').oninput();assert.equal(h.el('wake-areas').children.length,1);
 assert.equal(h.el('wake-toggle').disabled,false);await h.el('wake-toggle').onclick();assert.deepEqual(h.calls.slice(-2).map(x=>x[0]),['/api/live/areas','/api/wake']);assert.equal(h.calls.at(-2)[1].account_key,'bound-account');assert.deepEqual(Array.from(h.calls.at(-2)[1].area_ids),['a0','a7']);assert.deepEqual(h.events,['brain-areas-changed']);assert.equal(h.el('wake-areas').children[0].disabled,true);assert.equal(h.el('wake-toggle').disabled,false);
 await h.el('wake-toggle').onclick();assert.equal(h.c.state.wake.enabled,false);
});
test('signed-out, missing audio, busy, and unavailable runtime cannot enable; saved selection reloads',async()=>{
 const h=harness();await h.load();h.el('wake-areas').children[0].onclick();
 for(const mutate of [()=>h.c.state.recording.id='recording',()=>{h.c.state.recording.id=null;h.c.state.live.busy=true},()=>{h.c.state.live.busy=false;h.c.state.wake.available=false},()=>{h.c.state.wake.available=true;h.c.state.cdb.identity=null}]){mutate();h.c.renderState();assert.equal(h.el('wake-toggle').disabled,true)}
 assert.equal(h.el('wake-selected').textContent,'Ausgewählt (0)');
 h.c.state.cdb.identity={name:'Another'};h.setResponse({enabled:true,areas:[{id:'b',label:'Saved'}],remembered_area_ids:['b','removed'],selection_account_key:'another',audio:{available:false,message:'Lautsprecher fehlt'}});await h.load();assert.equal(h.el('wake-selected').textContent,'Ausgewählt (1)');assert.equal(h.el('wake-toggle').disabled,true);assert.match(h.el('wake-audio').textContent,/fehlt/);
});
test('failed save stays inline and never activates; stale account responses never install areas',async()=>{
 const h=harness();await h.load();h.el('wake-areas').children[0].onclick();const api=h.c.api;h.c.api=async(p,b)=>{if(p==='/api/live/areas')throw Error('Speichern fehlgeschlagen');return api(p,b)};
 await h.el('wake-toggle').onclick();assert.equal(h.calls.some(x=>x[0]==='/api/wake'),false);assert.match(h.el('wake-hint').textContent,/fehlgeschlagen/);
 let finish;h.c.api=()=>new Promise(resolve=>finish=resolve);const pending=h.load();h.c.state.cdb.identity={name:'Other account'};h.c.renderState();finish({areas:[{id:'wrong',label:'Wrong'}],remembered_area_ids:['wrong']});await pending;assert.equal(h.el('wake-selected').textContent,'Ausgewählt (0)');assert.equal(h.el('wake-toggle').disabled,true);
});
test('account change during save prevents activation; a refresh error clears obsolete readiness',async()=>{
 const h=harness();await h.load();h.el('wake-areas').children[0].onclick();let finish;h.c.api=()=>new Promise(resolve=>finish=resolve);const pending=h.el('wake-toggle').onclick();h.c.state.cdb.identity={name:'Other'};finish({});await pending;assert.equal(h.c.state.wake.enabled,false);assert.equal(h.el('wake-toggle').disabled,true);
 h.c.api=async()=>{throw Error('Nicht erreichbar')};await h.load();assert.match(h.el('wake-hint').textContent,/Nicht erreichbar/);assert.equal(h.el('wake-toggle').disabled,true);
});
test('phrase selector follows saved word and is locked during listening, test, recording and conversation',async()=>{
 const h=harness();await h.load();h.c.state.wake.phrase='okay-kai';h.c.state.wake.word='Okay KAI';h.c.renderState();
 assert.equal(h.el('wake-phrase').value,'okay-kai');assert.equal(h.el('wake-word').textContent,'Okay KAI');
 h.el('wake-phrase').value='hey-kai';await h.el('wake-phrase').onchange();
 assert.equal(h.calls.at(-1)[1].action,'phrase');assert.equal(h.calls.at(-1)[1].phrase,'hey-kai');
 for(const field of ['enabled','testing']){h.c.state.wake[field]=true;h.c.renderState();assert.equal(h.el('wake-phrase').disabled,true);const count=h.calls.length;await h.el('wake-phrase').onchange();assert.equal(h.calls.length,count);h.c.state.wake[field]=false}
 h.c.state.recording.id='active';h.c.renderState();assert.equal(h.el('wake-phrase').disabled,true);
 h.c.state.recording.id=null;h.c.state.live.busy=true;h.c.renderState();assert.equal(h.el('wake-phrase').disabled,true);
});
