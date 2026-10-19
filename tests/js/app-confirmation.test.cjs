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
