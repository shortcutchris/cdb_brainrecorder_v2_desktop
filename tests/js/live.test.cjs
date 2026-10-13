const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const nodes={},events={},calls=[];
 const element=id=>nodes[id]??=({get id(){return id},set id(value){nodes[value]=this},hidden:false,disabled:false,open:false,value:'',dataset:{},style:{},children:[],classList:{toggle(){}},setAttribute(k,v){this[k]=v},append(...a){this.children.push(...a)},before(){},replaceChildren(...a){this.children=a},show(){this.open=true},close(){this.open=false},get innerHTML(){return''},set innerHTML(html){for(const m of html.matchAll(/id="([^"]+)"/g))element(m[1])}});
 const c={document:{createElement:t=>element('new'+Math.random()),body:{append(){},dataset:{},classList:{contains(){return false}}}},window:{addEventListener:(n,f)=>events[n]=f},$:element,state:{recording:{id:null},live:{state:'idle',busy:false,history:[]},cdb:{identity:{name:'Test'}}},online:true,csrf:'csrf',renderState(){},workspaceView(id){c.document.body.dataset.workspace=id;element(id).show()},leaveDraft:async()=>{},audio:{pause(){}},drawPageNumbers(){},run:fn=>fn,setInterval:()=>1,clearInterval(){},fetch:async()=>{},poll:async()=>{},openSettings:async()=>{},showSettingsDetail(){},api:async(path,body)=>{
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
test('measured pages preserve every character, separate turns and fit the viewport',()=>{
 const source=fs.readFileSync('studio/live.js','utf8');const fn=source.slice(source.indexOf('function historyPages('),source.indexOf('const bubbleNodes='));const c={};vm.createContext(c);vm.runInContext(fn,c);
 const measure=text=>46+Math.max(1,text.split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(line.length/40)),0))*27;
 for(const text of ['Langer Testtext '.repeat(200),Array.from({length:30},(_,i)=>'Zeile '+i).join('\n'),'\n\n\n\n','W'.repeat(999),'👋 '.repeat(900)]){
  const pages=c.historyPages([{role:'user',text}],measure,280);assert.equal(pages.flat().map(x=>x.text).join(''),text);
  assert.ok(pages.every(p=>p.reduce((n,b)=>n+measure(b.text),0)+(p.length-1)*12<=280));
  assert.ok(pages.flat().every(b=>!/[\uD800-\uDBFF]$/.test(b.text)));
 }
 const pages=c.historyPages([{role:'user',text:'Eins'},{role:'user',text:'Zwei'}],measure,280);assert.equal(pages[0].length,2);assert.notEqual(pages[0][0].key,pages[0][1].key);
});
test('streaming appends into the same bubble and explicit history selection survives updates',()=>{
 const h=harness();h.c.state.live={state:'speaking',busy:true,history:[{role:'assistant',text:'Hallo'}]};h.c.renderState();const bubble=h.element('live-messages').children[0];
 h.c.state.live.history[0].text+=' Welt';h.c.renderState();assert.equal(h.element('live-messages').children[0],bubble);assert.equal(bubble._tail.textContent,' Welt');assert.equal(bubble._stable.textContent,'Hallo');
 let choose;h.c.drawPageNumbers=(nav,count,current,fn)=>{choose=fn};h.c.state.live.history[0].text='Langer Text '.repeat(200);h.c.renderState();choose(0);const old=h.element('live-messages').children[0]._text;
 h.c.state.live.history[0].text+=' Weitere Wörter';h.c.renderState();assert.equal(h.element('live-messages').children[0]._text,old);assert.equal(h.element('live-follow').textContent,'Zum Live-Gespräch');h.element('live-follow').onclick();assert.equal(h.element('live-follow').disabled,true);
});
test('feedback uses measured audio and confirmed search, mute zeros input',()=>{
 const h=harness();h.c.state.live={state:'listening',busy:true,history:[],feedback:{active:true,state:'thinking',search:{web:1},input:{bars:Array(16).fill(.5)},output:{active:false},search_sound:false}};h.c.renderState();assert.equal(h.element('live-feedback-title').textContent,'Sucht im Web …');assert.equal(h.element('live-sound').textContent,'Suchton aus');assert.match(h.element('live-bar-0').style.transform,/0.52/);
 h.c.state.live.feedback={active:true,muted:true,output:{active:false},input:{bars:Array(16).fill(1)}};h.c.renderState();assert.equal(h.element('live-feedback-title').textContent,'Mikrofon stumm');assert.equal(h.element('live-bar-0').style.transform,'scaleY(0.04)');
 h.c.state.live.feedback.output={active:true,bars:Array(16).fill(.8)};h.c.renderState();assert.equal(h.element('live-feedback-title').textContent,'Voice One spricht');
});

test('opening a completed transcript does not request cloud setup again',async()=>{
 const h=harness();h.c.state.live={state:'ended',busy:false,history:[{role:'assistant',text:'Fertig.'}]};await h.element('live-open').onclick();assert.equal(h.calls.some(([p])=>p==='/api/live/setup'),false);assert.equal(h.element('live-new').hidden,false);
});

test('cue indicator follows actual playback, search pauses and terminal states',()=>{
 const h=harness(),f={active:true,search:{web:1},search_sound:true,search_audio:{playing:false}};
 h.c.state.live={state:'listening',busy:true,history:[],feedback:f};h.c.renderState();
 assert.equal(h.element('live-cue').dataset.mode,'searching');assert.equal(h.element('live-cue-label').textContent,'Suche · Ton pausiert');
 f.search_audio.playing=true;h.c.renderState();assert.equal(h.element('live-cue').dataset.mode,'playing');assert.equal(h.element('live-cue-label').textContent,'Suchton läuft');
 f.search.web=0;h.c.renderState();assert.equal(h.element('live-cue-label').textContent,'Suchton klingt aus');
 f.search.web=1;f.search_sound=false;h.c.renderState();assert.equal(h.element('live-cue').dataset.mode,'searching');assert.equal(h.element('live-cue-label').textContent,'Suche · Ton aus');
 f.search.web=0;h.c.renderState();assert.equal(h.element('live-cue').dataset.mode,'idle');
 f.search_sound=true;f.active=false;h.c.renderState();assert.equal(h.element('live-cue').dataset.mode,'idle');
 f.active=true;f.unavailable=true;h.c.renderState();assert.equal(h.element('live-cue').dataset.mode,'idle');
 f.unavailable=false;h.c.online=false;h.c.renderState();assert.equal(h.element('live-cue').dataset.mode,'idle');
});

async function areaHarness(max=8){
 const h=harness(),api=h.c.api;const areas=Array.from({length:12},(_,i)=>({id:'area-'+i,label:['Projekt Atlas','Teamwissen','Kundenservice','Workshop-Notizen'][i%4]+' '+i}));
 h.c.api=async(path,body)=>path==='/api/live/setup'?{enabled:true,max_areas:max,areas,default_area:areas[0],audio:{available:true}}:api(path,body);
 await h.element('live-open').onclick();return {...h,areas};
}
test('area search and direct pages preserve multi-selection and send all selected IDs',async()=>{
 const h=await areaHarness();h.element('live-areas').children[1].onclick();
 h.element('live-area-pages').children[1].onclick();h.element('live-areas').children[2].onclick();
 h.element('live-area-search').value='PROJEKT';h.element('live-area-search').oninput();
 assert.equal(h.element('live-areas').children.length,3);assert.equal(h.element('live-area-position').textContent,'1 / 1');
 assert.equal(h.element('live-selection-count').textContent,'3 von maximal 8 ausgewählt');
 h.element('live-area-search').value='kein Treffer';h.element('live-area-search').oninput();assert.match(h.element('live-areas').children[0].textContent,/Keine passenden/);
 await h.element('live-start').onclick();assert.deepEqual(Array.from(h.calls.find(([p])=>p.endsWith('/reserve'))[1].area_ids),['area-0','area-1','area-6']);
});
test('selection limits block additional checks and zero selection blocks start, including refresh',async()=>{
 const h=await areaHarness(2);h.element('live-areas').children[1].onclick();assert.equal(h.element('live-areas').children[2].disabled,true);
 h.element('live-areas').children[2].onclick();assert.equal(h.element('live-selection-count').textContent,'2 von maximal 2 ausgewählt');
 h.element('live-areas').children[0].onclick();h.element('live-areas').children[1].onclick();assert.equal(h.element('live-start').disabled,true);
 await h.element('live-refresh').onclick();assert.equal(h.element('live-selection-count').textContent,'0 von maximal 2 ausgewählt');
 await h.element('live-start').onclick();assert.equal(h.calls.some(([p])=>p.endsWith('/reserve')),false);
});
test('connecting and running areas are read-only, stale click handlers cannot change selection',async()=>{
 const h=await areaHarness(),old=h.element('live-areas').children[1];await h.element('live-start').onclick();old.onclick();
 assert.equal(h.element('live-area-search').disabled,true);assert.equal(h.element('live-areas').children.length,1);assert.equal(h.element('live-areas').children[0].onclick,undefined);
 h.c.state.live.areas=h.areas.slice(0,8);h.c.renderState();h.element('live-area-pages').children[1].onclick();assert.equal(h.element('live-area-position').textContent,'2 / 2');
 assert.equal(h.element('live-areas').children.every(row=>row.onclick===undefined),true);
 h.c.state.live={busy:false,state:'ended',areas:h.areas.slice(0,8),history:[{role:'assistant',text:'Fertig'}]};h.c.renderState();assert.equal(h.element('live-area-search').disabled,true);
});
test('account changes discard pending area requests rather than showing another account selection',async()=>{
 const h=await areaHarness();let resolve;h.c.api=()=>new Promise(r=>resolve=r);const loading=h.element('live-refresh').onclick();
 assert.equal(h.element('live-start').disabled,true);h.c.state.cdb.identity={name:'Other'};h.c.renderState();resolve({enabled:true,max_areas:8,areas:h.areas,default_area:h.areas[0],audio:{available:true}});await loading;
 assert.equal(h.element('live-selection-count').textContent,'0 von maximal 8 ausgewählt');assert.equal(h.element('live-start').disabled,true);assert.match(h.element('live-areas').children[0].textContent,/Keine Wissensbereiche/);
});

test('selected filter collects choices from all pages and clears search without losing choices',async()=>{
 const h=await areaHarness();h.element('live-areas').children[1].onclick();h.element('live-area-pages').children[1].onclick();h.element('live-areas').children[2].onclick();
 h.element('live-area-search').value='nothing';h.element('live-area-search').oninput();h.element('live-selected-filter').onclick();
 assert.equal(h.element('live-area-search').value,'');assert.equal(h.element('live-selected-filter').textContent,'Ausgewählt (3)');
 assert.deepEqual(h.element('live-areas').children.map(r=>r['aria-label']),['Projekt Atlas 0','Teamwissen 1','Kundenservice 6']);
 h.element('live-areas').children[1].onclick();assert.equal(h.element('live-areas').children.length,2);assert.equal(h.element('live-selected-filter').textContent,'Ausgewählt (2)');
 h.element('live-selected-filter').onclick();assert.equal(h.element('live-areas').children.length,4);
 await h.element('live-start').onclick();assert.deepEqual(Array.from(h.calls.find(([p])=>p.endsWith('/reserve'))[1].area_ids),['area-0','area-6']);
});
test('empty selected filter is recoverable and stale filter cannot change a running session',async()=>{
 const h=await areaHarness();h.element('live-selected-filter').onclick();h.element('live-areas').children[0].onclick();
 assert.match(h.element('live-areas').children[0].textContent,/Noch nichts ausgewählt/);assert.equal(h.element('live-selected-filter').disabled,false);assert.equal(h.element('live-start').disabled,true);
 h.element('live-selected-filter').onclick();h.element('live-areas').children[0].onclick();await h.element('live-start').onclick();
 assert.equal(h.element('live-selected-filter').hidden,true);h.element('live-selected-filter').onclick();assert.equal(h.element('live-areas').children[0].onclick,undefined);
});
