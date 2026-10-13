const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={},events={},calls=[];let resolveMedia,rejectMedia,stopped=0;
 const element=id=>nodes[id]??=( {get id(){return id},set id(value){nodes[value]=this},hidden:false,disabled:false,open:false,value:'',dataset:{},children:[],classList:{toggle(){}},setAttribute(k,v){this[k]=v},append(...a){this.children.push(...a)},before(){},replaceChildren(...a){this.children=a},show(){this.open=true},close(){this.open=false},pause(){},play:async()=>{},get innerHTML(){return''},set innerHTML(html){for(const m of html.matchAll(/id="([^"]+)"/g))element(m[1])}} );
 const media=new Promise((r,j)=>{resolveMedia=r;rejectMedia=j});const track={stop(){stopped++},enabled:true};
 const c={document:{createElement:t=>element('new'+Math.random()),body:{append(){},dataset:{}},addEventListener:(n,f)=>events[n]=f,hidden:false},window:{addEventListener:(n,f)=>events[n]=f},navigator:{mediaDevices:{getUserMedia:()=>media,enumerateDevices:async()=>[{kind:'audioinput',deviceId:'respeaker',label:'ReSpeaker XVF3800'}]}},$:element,state:{recording:{id:null},live:{state:'idle',busy:false,history:[]},cdb:{identity:{name:'Test'}}},online:true,csrf:'csrf',starting:false,renderState(){},workspaceView(id){c.document.body.dataset.workspace=id;element(id).show()},leaveDraft:async()=>{},audio:{pause(){}},notice:()=>{},drawPageNumbers(){},run:fn=>fn,setInterval:()=>1,clearInterval(){},setTimeout,fetch:async()=>{},MediaStream:class{},poll:async()=>{},api:async(path,body)=>{
  calls.push([path,body]);
  if(path==='/api/live/setup')return {enabled:true,max_areas:8,areas:[{id:'area',label:'Staging'}],default_area:{id:'area'}};
  if(path==='/api/live/reserve'){c.state.live={state:'connecting',busy:true,history:[]};return{lease:'owner-lease'}};
  if(path==='/api/live/end'){c.state.live={state:'ended',busy:false,history:[]};return{closed:true}};
  return {};
 }};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/live.js','utf8'),c);
 return{c,element,events,calls,resolveMedia:()=>resolveMedia({getTracks:()=>[track],getAudioTracks:()=>[track]}),rejectMedia,stopped:()=>stopped};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('microphone permission reserves backend audio first and cancelled late stream is stopped',async()=>{
 const h=harness();await h.element('live-open').onclick();const pending=h.element('live-devices').onclick();await tick();
 assert.equal(h.calls.at(-1)[0],'/api/live/reserve');assert.equal(h.c.state.live.busy,true);
 assert.throws(()=>h.c.workspaceView('settings'),/Gespräch läuft/);
 await h.element('live-end').onclick();h.resolveMedia();await pending;
 assert.equal(h.stopped()>0,true);assert.equal(h.c.state.live.busy,false);
 assert.equal(h.calls.some(([path])=>path==='/api/live/start'),false);
});
test('permission denial releases the lease; successful probe explicitly picks ReSpeaker',async()=>{
 const failed=harness();await failed.element('live-open').onclick();const pending=failed.element('live-devices').onclick();await tick();failed.rejectMedia(new Error('denied'));await assert.rejects(pending,/denied/);assert.equal(failed.c.state.live.busy,false);
 const good=harness();await good.element('live-open').onclick();const probing=good.element('live-devices').onclick();await tick();good.resolveMedia();await probing;
 assert.equal(good.element('live-microphone').value,'respeaker');assert.equal(good.stopped(),1);assert.equal(good.c.state.live.busy,false);
});
test('recording prevents entry to live',async()=>{
 const h=harness();h.c.state.recording.id='record';h.c.renderState();assert.equal(h.element('live-open').disabled,true);await assert.rejects(h.element('live-open').onclick(),/Aufnahme läuft/);
});
test('chat pages preserve long and multiline content without oversize bubbles',()=>{
 const source=fs.readFileSync('studio/live.js','utf8');const fn=source.slice(source.indexOf('function historyPages('),source.indexOf('function drawHistory('));const c={};vm.createContext(c);vm.runInContext(fn,c);
 for(const text of ['Langer Testtext '.repeat(200),Array.from({length:30},(_,i)=>'Zeile '+i).join('\n'),'\n\n\n\n','W'.repeat(999)]){
  const pages=c.historyPages([{role:'user',text}]);assert.equal(pages.flat().map(x=>x.text).join(''),text);assert.ok(pages.every(p=>p.length<=2&&p.every(b=>b.text.length<=273&&b.lines<=3)));
 }
});
test('recorder navigation unlocks after live ends',()=>{
 const h=harness();h.c.state.live={state:'listening',busy:true,history:[]};h.c.renderState();assert.equal(h.element('home').disabled,true);h.c.state.live={state:'ended',busy:false,history:[]};h.c.renderState();assert.equal(h.element('home').disabled,false);
});
