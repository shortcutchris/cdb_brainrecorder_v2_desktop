const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync('studio/app.js','utf8');
function harness(){
 const nodes={},origin={isConnected:true,focus(){this.focused=true}};
 const el=id=>nodes[id]??={textContent:'',open:false,showModal(){this.open=true},close(){this.open=false},focus(){this.focused=true}};
 const c={$:el,document:{activeElement:origin}};vm.createContext(c);vm.runInContext(source.slice(source.indexOf('let activeConfirmation='),source.indexOf('async function deleteMeeting(')),c);return {c,el,origin};
}
test('app confirmation presents text safely, focuses cancel and restores caller on cancel',async()=>{
 const {c,el,origin}=harness();const pending=c.confirmAction({title:'Meeting löschen?',message:'<img onerror=unsafe>','accept':'Endgültig löschen'});
 assert.equal(el('app-confirm').open,true);assert.equal(el('app-confirm-message').textContent,'<img onerror=unsafe>');assert.equal(el('app-confirm-cancel').focused,true);
 el('app-confirm-cancel').onclick();assert.equal(await pending,false);assert.equal(el('app-confirm').open,false);assert.equal(origin.focused,true);
});
test('only explicit accept resolves true, Escape and close cancel',async()=>{
 for(const mode of ['accept','escape','close']){
  const {c,el}=harness();const p=c.confirmAction({title:'Vorlage löschen?',message:'Test'});
  if(mode==='accept')el('app-confirm-accept').onclick();else if(mode==='escape'){let prevented=false;el('app-confirm').oncancel({preventDefault(){prevented=true}});assert.equal(prevented,true)}else el('app-confirm-close').onclick();
  assert.equal(await p,mode==='accept');assert.equal(el('app-confirm-accept').onclick,null);
 }
});
test('a second request cannot overwrite an open confirmation target',async()=>{
 const {c,el}=harness();const first=c.confirmAction({title:'First',message:'Meeting A'});assert.equal(await c.confirmAction({title:'Second',message:'Meeting B'}),false);assert.equal(el('app-confirm-message').textContent,'Meeting A');el('app-confirm-cancel').onclick();await first;
});
test('all shipped web screens avoid native JS input dialogs and unload prompts',()=>{
 for(const name of fs.readdirSync('studio').filter(n=>/\.(js|html)$/.test(n))){const s=fs.readFileSync(path.join('studio',name),'utf8');assert.doesNotMatch(s,/\b(?:confirm|alert|prompt)\s*\(/,name);assert.doesNotMatch(s,/beforeunload|onbeforeunload/,name)}
 assert.match(source,/addEventListener\('pagehide'.*storeDraft/);
});

test('pagehide persists dirty text that the existing editor restores after reload',()=>{
 const storage=new Map(),old={id:7,values:{notes:'Lokaler Entwurf',transcript_text:'Text',summary_text:'Kurz'},base:{notes:'Gespeichert',transcript_text:'Text',summary_text:'Kurz'},dirty:new Set(['notes'])};let onHide;
 const c={models:new Map([[7,old]]),namespace:'isolated',fields:['notes','transcript_text','summary_text'],localStorage:{setItem:(k,v)=>storage.set(k,v),getItem:k=>storage.get(k)||null},notice(){},window:{addEventListener:(name,fn)=>{assert.equal(name,'pagehide');onHide=fn}}};vm.createContext(c);
 vm.runInContext(source.slice(source.indexOf('function draftKey('),source.indexOf('async function flush(')),c);
 vm.runInContext(source.slice(source.indexOf("window.addEventListener('pagehide'"),source.indexOf('\n',source.indexOf("window.addEventListener('pagehide'"))),c);
 onHide();c.models=new Map();const restored=c.makeModel({id:7,notes:'Gespeichert',transcript_text:'Text',summary_text:'Kurz'});assert.equal(restored.values.notes,'Lokaler Entwurf');assert.equal(restored.dirty.has('notes'),true);
});
