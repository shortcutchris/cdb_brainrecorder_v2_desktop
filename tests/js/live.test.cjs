const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={},events={},calls=[];
 const element=id=>nodes[id]??=({get id(){return id},set id(value){nodes[value]=this},hidden:false,disabled:false,open:false,value:'',dataset:{},style:{},children:[],classList:{toggle(){}},setAttribute(k,v){this[k]=v},append(...a){this.children.push(...a)},before(){},replaceChildren(...a){this.children=a},show(){this.open=true},close(){this.open=false},get innerHTML(){return''},set innerHTML(html){for(const m of html.matchAll(/id="([^"]+)"/g))element(m[1])}});
 const c={document:{createElement:t=>element('new'+Math.random()),body:{append(){},dataset:{}}},window:{addEventListener:(n,f)=>events[n]=f},$:element,state:{recording:{id:null},live:{state:'idle',busy:false,history:[]},cdb:{identity:{name:'Test'}}},online:true,csrf:'csrf',renderState(){},workspaceView(id){c.document.body.dataset.workspace=id;element(id).show()},leaveDraft:async()=>{},audio:{pause(){}},drawPageNumbers(){},run:fn=>fn,setInterval:()=>1,clearInterval(){},fetch:async()=>{},poll:async()=>{},openSettings:async()=>{},showSettingsDetail(){},api:async(path,body)=>{
  calls.push([path,body]);
  if(path==='/api/live/setup')return {enabled:true,max_areas:8,areas:[{id:'area',label:'Staging'}],default_area:{id:'area'},audio:{available:true,microphone_label:'ReSpeaker',speaker_label:'Pi Lautsprecher'}};
  if(path==='/api/live/reserve'){c.state.live={state:'connecting',busy:true,history:[]};return{lease:'owner-lease'}};
  if(path==='/api/live/start-native')return{starting:true};
  if(path==='/api/live/mute'){c.state.live.muted=body.muted;return {muted:body.muted}};
  if(path==='/api/live/end'){c.state.live={state:'ended',busy:false,history:[]};return{closed:true}};
  return {};
 }};
 vm.createContext(c);vm.runInContext(fs.readFileSync('studio/live.js','utf8'),c);return{c,element,events,calls};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('native start uses Pi settings and needs no browser audio APIs',async()=>{
 const h=harness();await h.element('live-open').onclick();assert.equal(h.element('live-input-name').textContent,'ReSpeaker');assert.equal(h.element('live-start').disabled,false);await h.element('live-start').onclick();assert.deepEqual(h.calls.slice(-2).map(c=>c[0]),['/api/live/reserve','/api/live/start-native']);assert.equal(h.c.state.live.busy,true);assert.throws(()=>h.c.workspaceView('settings'),/Gespräch läuft/);
 assert.doesNotMatch(fs.readFileSync('studio/live.js','utf8'),/getUserMedia|RTCPeerConnection|enumerateDevices|navigator/);
});
test('muting is acknowledged by Python and stopping unlocks recorder',async()=>{
 const h=harness();await h.element('live-open').onclick();await h.element('live-start').onclick();assert.equal(h.element('home').disabled,true);await h.element('live-mute').onclick();assert.equal(h.c.state.live.muted,true);assert.equal(h.calls.at(-1)[0],'/api/live/mute');await h.element('live-end').onclick();assert.equal(h.c.state.live.busy,false);assert.equal(h.element('home').disabled,false);assert.equal(h.element('live-notice').textContent,'');
});
test('cancellation while reserve response is delayed cannot start native capture',async()=>{
 const h=harness();await h.element('live-open').onclick();const api=h.c.api;let resolve;h.c.api=async(path,body)=>path.endsWith('/reserve')?await new Promise(r=>resolve=r):api(path,body);const pending=h.element('live-start').onclick();await tick();await h.element('live-end').onclick();resolve({lease:'late-lease'});await pending;assert.equal(h.calls.some(([p])=>p.endsWith('/start-native')),false);assert.equal(h.calls.at(-1)[1].lease,'late-lease');
});
test('native start failure releases reservation and leaves an actionable error',async()=>{
 const h=harness();await h.element('live-open').onclick();const api=h.c.api;h.c.api=async(path,body)=>{if(path.endsWith('/start-native'))throw new Error('Pi-Mikrofon fehlt');return api(path,body)};await assert.rejects(h.element('live-start').onclick(),/Pi-Mikrofon fehlt/);assert.equal(h.c.state.live.busy,false);assert.match(h.element('live-notice').textContent,/Pi-Mikrofon fehlt/);
});
test('unavailable Pi audio blocks start and offers settings',async()=>{
 const h=harness(),api=h.c.api;h.c.api=async(path,body)=>{const r=await api(path,body);if(path.endsWith('/setup'))r.audio={available:false,message:'Pi-Lautsprecher fehlt'};return r};await h.element('live-open').onclick();assert.equal(h.element('live-start').disabled,true);assert.match(h.element('live-audio-status').textContent,/Pi-Lautsprecher fehlt/);let destination;h.c.showSettingsDetail=p=>destination=p;await h.element('live-audio-settings').onclick();assert.equal(destination,'audio-home');
});
test('recording prevents entry to live',async()=>{
 const h=harness();h.c.state.recording.id='record';h.c.renderState();assert.equal(h.element('live-open').disabled,true);await assert.rejects(h.element('live-open').onclick(),/Aufnahme läuft/);
});
test('chat pages preserve long and multiline content without oversize bubbles',()=>{
 const source=fs.readFileSync('studio/live.js','utf8');const fn=source.slice(source.indexOf('function historyPages('),source.indexOf('function drawHistory('));const c={};vm.createContext(c);vm.runInContext(fn,c);
 for(const text of ['Langer Testtext '.repeat(200),Array.from({length:30},(_,i)=>'Zeile '+i).join('\n'),'\n\n\n\n','W'.repeat(999)]){const pages=c.historyPages([{role:'user',text}]);assert.equal(pages.flat().map(x=>x.text).join(''),text);assert.ok(pages.every(p=>p.length<=2&&p.every(b=>b.text.length<=273&&b.lines<=3)));}
});
test('feedback uses measured audio and confirmed search, mute zeros input',()=>{
 const h=harness();h.c.state.live={state:'listening',busy:true,history:[],feedback:{active:true,state:'thinking',search:{web:1},input:{bars:Array(16).fill(.5)},output:{active:false},search_sound:false}};h.c.renderState();assert.equal(h.element('live-feedback-title').textContent,'Sucht im Web …');assert.equal(h.element('live-sound').textContent,'Suchton aus');assert.match(h.element('live-bar-0').style.transform,/0.52/);
 h.c.state.live.feedback={active:true,muted:true,output:{active:false},input:{bars:Array(16).fill(1)}};h.c.renderState();assert.equal(h.element('live-feedback-title').textContent,'Mikrofon stumm');assert.equal(h.element('live-bar-0').style.transform,'scaleY(0.04)');
 h.c.state.live.feedback.output={active:true,bars:Array(16).fill(.8)};h.c.renderState();assert.equal(h.element('live-feedback-title').textContent,'Voice One spricht');
});
