const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const A={id:'area-a',label:'Bereich A'},B={id:'area-b',label:'Bereich B'};
function harness(){
 const elements=new Map(),calls=[],microtasks=[];
 function element(id){if(!elements.has(id))elements.set(id,{value:'',dataset:{},children:[],hidden:false,disabled:false,textContent:'',replaceChildren(...children){this.children=children},append(...children){this.children.push(...children)},after(){},close(){},showModal(){},setAttribute(){},closest(){return element(id+'-label')}});return elements.get(id)}
 const c={identity:{user_id:'one',client_id:'company',name:'Test'},config:{server:'https://staging.cdbos.de',transcription:'local',summary:'local'},destination:null,login:{state:'completed'},publications:[]};
 const context={state:{cdb:c,sessions:[{id:1,transcription_status:'completed'},{id:2,transcription_status:'completed'}],jobs:[]},selected:1,busyStates:['recording'],document:{querySelector:()=>element('local-note'),createElement:()=>element(Symbol())},$:element,allowed:()=>true,queueMicrotask:fn=>microtasks.push(fn),MutationObserver:class{observe(){}},renderState(){},run:fn=>fn,notice(){},flush:async()=>{},poll:async()=>context.renderCdb(),fillSelect(el,entries,value){el.entries=entries;el.value=value},api:async(p,b)=>{calls.push([p,b]);if(p==='/api/cdb/areas')return [A,B];if(p==='/api/cdb/area'){c.destination=[A,B].find(a=>a.id===b.area);return c}return {}}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../studio/cdb.js'),'utf8'),context);
 return {context,c,element,calls,async settle(){while(microtasks.length)await microtasks.shift()();await new Promise(resolve=>setImmediate(resolve))}};
}
test('successful sign-in automatically loads areas once, with no implicit default or upload',async()=>{
 const h=harness();h.context.renderCdb();await h.settle();h.context.renderCdb();
 assert.equal(h.calls.filter(([p])=>p==='/api/cdb/areas').length,1);
 assert.equal(h.element('cdb-connected-area').hidden,false);
 assert.equal(h.element('cdb-connection-area').disabled,false);
 assert.equal(h.c.destination,null);assert.equal(h.element('cdb-send').disabled,true);
 assert.equal(h.calls.some(([p])=>p==='/api/cdb/send'),false);
});
test('default is shared across settings; per-meeting override does not change it and resets for next meeting',async()=>{
 const h=harness();h.context.renderCdb();await h.settle();
 h.element('cdb-connection-area').value=A.id;await h.element('cdb-connection-area').onchange();
 assert.equal(h.c.destination.id,A.id);assert.equal(h.element('cdb-area').value,A.id);assert.equal(h.element('cdb-send-area').value,A.id);
 h.element('cdb-send-area').value=B.id;h.element('cdb-send-area').onchange();
 await h.element('cdb-send').onclick();assert.equal(h.calls.find(([p])=>p==='/api/cdb/send')[1].area,B.id);assert.equal(h.c.destination.id,A.id);
 h.context.selected=2;h.context.renderCdb();assert.equal(h.element('cdb-send-area').value,A.id);
});
test('area reply from previous account is discarded, including after logout',async()=>{
 const h=harness();let resolveOld;h.context.api=async()=>new Promise(resolve=>{resolveOld=resolve});
 h.context.renderCdb();await h.settle();h.c.identity=null;h.context.renderCdb();resolveOld([A]);await h.settle();
 assert.equal(h.element('cdb-connected-area').hidden,true);assert.equal(h.element('cdb-connection-area').entries.length,1);assert.equal(h.element('cdb-send').disabled,true);
 h.context.api=async()=>[B];h.c.identity={user_id:'two',client_id:'company',name:'Other'};h.context.renderCdb();await h.settle();
 assert.equal(h.element('cdb-connection-area').entries[1].id,B.id);
});
test('failed area loading has explicit retry and cannot enable a stale destination',async()=>{
 const h=harness();h.c.destination=A;h.context.api=async()=>{throw Error('Offline')};h.context.renderCdb();await h.settle();
 assert.match(h.element('cdb-connection-area-status').textContent,/Offline/);assert.equal(h.element('cdb-send').disabled,true);
 h.context.api=async()=>[A];await h.element('cdb-connection-refresh').onclick();assert.equal(h.element('cdb-send').disabled,false);
});
test('removed default is visibly rejected and cannot silently select another area',async()=>{
 const h=harness();h.c.destination={id:'gone',label:'Removed'};h.context.renderCdb();await h.settle();
 assert.match(h.element('cdb-connection-area-status').textContent,/nicht mehr verfügbar/);assert.equal(h.element('cdb-connection-area').value,'');assert.equal(h.element('cdb-send').disabled,true);
});

test('a double tap while sending dispatches one request with its frozen target',async()=>{
 const h=harness();h.c.destination=A;h.context.renderCdb();await h.settle();
 let finish;h.context.api=async(p,b)=>{h.calls.push([p,b]);if(p==='/api/cdb/send')await new Promise(resolve=>{finish=resolve});return {}};
 const first=h.element('cdb-send').onclick();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.element('cdb-send').disabled,true);assert.equal(h.element('cdb-send-area').disabled,true);
 await h.element('cdb-send').onclick();assert.equal(h.calls.filter(([p])=>p==='/api/cdb/send').length,1);
 finish();await first;
});
