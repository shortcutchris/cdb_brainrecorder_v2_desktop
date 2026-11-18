const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../studio/home.js'),'utf8');
function harness({recording=false,live=false,online=true,stateReady=true}={}){
 const nodes={},calls=[];
 const element=id=>nodes[id]??=({get id(){return this._id||id},set id(value){this._id=value;nodes[value]=this},disabled:false,open:false,textContent:'',dataset:{},children:[],classList:{toggle(){}},setAttribute(k,v){this[k]=v},append(...items){this.children.push(...items)},before(node){calls.push(['before',id,node.id])},replaceChildren(){this.children=[]},focus(){c.document.activeElement=this},showModal(){this.open=true},close(){this.open=false},show(){this.open=true;c.document.activeElement=this},blur(){c.document.activeElement=c.document.body},click(){return this.disabled?undefined:this.onclick?.()},set innerHTML(html){for(const m of html.matchAll(/id="([^"]+)"/g))element(m[1])}});
 const ready={config:{setup_complete:true},recording:{id:recording?'capture':null},live:{busy:live},jobs:[]};
 const c={document:{createElement:()=>element('created-'+Math.random()),body:{append(){},dataset:{workspace:'recorder'}}},$:element,state:stateReady?ready:null,online,run:f=>f,audio:{pause:()=>calls.push('pause')},leaveDraft:async()=>calls.push('save'),openSettings:async()=>{c.workspaceView('settings');calls.push('settings')},showSettingsDetail:page=>calls.push(page),renderState(){element('home').disabled=Boolean(c.state?.live.busy)},workspaceView(id=null){if(c.state?.recording.id&&id)throw Error('Aufnahme läuft');if(c.state?.live.busy&&id!=='live-view')throw Error('Gespräch läuft');for(const key of ['library','settings','live-view','queue-region'])if(key!==id)element(key).close();c.document.body.dataset.workspace=id||'recorder';if(id)element(id).show();calls.push(['route',id])}};
 const selection={key:'account',areas:Array.from({length:9},(_,i)=>({id:String(i),name:'Bereich '+i})),ids:['0'],limit:2,enabled:true,audio:{available:true}};
 c.window={studioLiveHome:{selection:()=>selection,refresh:async()=>selection,start:async()=>calls.push('talk'),apply:async(key,ids)=>{calls.push(['apply',key]);selection.ids=ids}}};
 element('record').onclick=async()=>calls.push('capture');
 element('home').disabled=live;
 for(const [target,destination] of [['home',null],['live-open','live-view'],['library-open','library'],['queue-toggle','queue-region'],['settings-open','settings'],['display-open','display-view']])element(target).onclick=()=>{calls.push(['click',target]);c.workspaceView(destination)};
 vm.createContext(c);vm.runInContext(source,c);return {c,element,calls,ready};
}
test('fresh idle connection opens Home and preserves the Recorder button identity',()=>{const h=harness();assert.deepEqual(h.calls[0],['before','home','start-open']);assert.equal(h.c.document.body.dataset.workspace,'start-view');assert.equal(h.element('start-open')['aria-current'],'page');assert.equal(h.element('start-tiles').children.length,2)});
test('active capture is never hidden at startup and Home cannot interrupt it',async()=>{const h=harness({recording:true});assert.equal(h.c.document.body.dataset.workspace,'recorder');assert.equal(h.element('start-open').disabled,true);await h.element('start-open').onclick();assert.equal(h.c.document.body.dataset.workspace,'recorder');assert.ok(h.element('start-tiles').children.every(b=>b.disabled))});
test('active Live session is restored instead of showing Home',()=>{const h=harness({live:true});assert.equal(h.c.document.body.dataset.workspace,'live-view');assert.equal(h.element('start-open').disabled,true);assert.equal(h.element('start-view').open,false)});
test('each direct start runs exactly once and opens the matching workspace',async()=>{
 for(const [tile,action,route] of [['live','talk','live-view'],['recorder','capture','recorder']]){
  const h=harness(),button=h.element('start-'+tile);
  await Promise.all([button.onclick(),button.onclick()]);
  assert.equal(h.calls.filter(x=>x===action).length,1);assert.equal(h.c.document.body.dataset.workspace,route);
 }
});
test('knowledge grid keeps changes local until apply and paginates all available areas',async()=>{
 const h=harness(),button=h.element('start-knowledge'),grid=h.element('knowledge-grid');
 await button.onclick();assert.equal(grid.children.length,6);h.element('knowledge-next').onclick();assert.equal(grid.children.length,3);
 grid.children[0].onclick();assert.equal(grid.children[1].disabled,true);h.element('knowledge-cancel').onclick();assert.equal(h.calls.some(x=>x[0]==='apply'),false);
 await button.onclick();grid.children[1].onclick();await h.element('knowledge-apply').onclick();assert.equal(h.element('knowledge-picker').open,false);
 assert.equal(h.c.window.studioLiveHome.selection().ids.join(','),'0,1');
});
test('missing selection opens grid, and navigating away during setup cancels a pending start',async()=>{
 const h=harness();h.c.window.studioLiveHome.selection().ids=[];await h.element('start-live').onclick();
 assert.equal(h.element('knowledge-picker').open,true);assert.equal(h.element('knowledge-apply').disabled,true);
 h.element('knowledge-cancel').onclick();let release;h.c.window.studioLiveHome.refresh=()=>new Promise(r=>release=r);
 const pending=h.element('start-live').onclick();await new Promise(r=>setImmediate(r));h.c.workspaceView('library');release(h.c.window.studioLiveHome.selection());await pending;
 assert.equal(h.c.document.body.dataset.workspace,'library');assert.equal(h.element('knowledge-picker').open,false);
});
test('render polling never sends the user back Home after navigation',async()=>{const h=harness();await h.element('library-open').onclick();h.c.renderState();h.c.renderState();assert.equal(h.c.document.body.dataset.workspace,'library');assert.equal(h.element('start-open')['aria-current'],'false')});
test('deferred first connection preserves explicit navigation before the state arrives',()=>{const h=harness({stateReady:false,online:false});h.c.workspaceView('settings');h.c.state=h.ready;h.c.online=true;h.c.renderState();assert.equal(h.c.document.body.dataset.workspace,'settings')});
test('new capture locks Home, ending it releases Home; background jobs alone do not lock',async()=>{const h=harness();h.c.state.recording.id='capture';h.c.renderState();assert.equal(h.element('start-open').disabled,true);h.c.state.recording.id=null;h.c.state.jobs=[{state:'summarizing'},{state:'queued'},{state:'completed'}];h.c.renderState();assert.equal(h.element('start-open').disabled,false);assert.equal(h.element('start-background').textContent,'2 Aufträge in der Verarbeitung');await h.element('queue-toggle').onclick();assert.equal(h.c.document.body.dataset.workspace,'queue-region')});
test('guarded routing rejects a Live start race before changing the visible view',()=>{const h=harness();h.c.state.live.busy=true;assert.throws(()=>h.c.workspaceView('settings'),/Gespräch läuft/);assert.equal(h.c.document.body.dataset.workspace,'start-view');assert.equal(h.element('start-view').open,true)});

test('a Live session started by another client replaces the Home view',()=>{const h=harness();h.c.state.live.busy=true;h.c.renderState();assert.equal(h.c.document.body.dataset.workspace,'live-view');assert.equal(h.element('start-view').open,false);assert.equal(h.element('start-open').disabled,true)});

test('Home uses actual recorder readiness, never setup_complete alone',()=>{const h=harness();assert.equal(h.element('start-led').dataset.state,'waiting');h.c.currentReadiness=()=>({tone:'error',label:'Mikrofon prüfen',target:'audio-page'});h.c.renderState();assert.equal(h.c.state.config.setup_complete,true);assert.equal(h.element('start-led').dataset.state,'error');assert.equal(h.element('start-status').textContent,'Mikrofon prüfen');h.c.currentReadiness=()=>({tone:'ready',label:'Aufnahmebereit'});h.c.renderState();assert.equal(h.element('start-led').dataset.state,'ready');assert.equal(h.element('start-status').textContent,'Aufnahmebereit')});

test('opening Home releases automatic dialog focus without stealing later keyboard focus',async()=>{const h=harness();assert.equal(h.c.document.activeElement,h.c.document.body);h.c.document.activeElement=h.element('library-open');h.c.renderState();assert.equal(h.c.document.activeElement,h.element('library-open'));await h.element('library-open').onclick();await h.element('start-open').onclick();assert.equal(h.c.document.activeElement,h.c.document.body)});

test('search, selected filter and cancel leave saved choices intact',async()=>{
 const h=harness();await h.element('start-knowledge').onclick();
 const search=h.element('knowledge-search');search.value='REICH 8';search.oninput();
 assert.equal(h.element('knowledge-grid').children.length,1);h.element('knowledge-grid').children[0].onclick();
 search.value='';search.oninput();h.element('knowledge-selected').onclick();
 assert.deepEqual(h.element('knowledge-grid').children.map(x=>x.textContent),['Bereich 0','Bereich 8']);
 h.element('knowledge-cancel').onclick();assert.deepEqual(h.c.window.studioLiveHome.selection().ids,['0']);
});
