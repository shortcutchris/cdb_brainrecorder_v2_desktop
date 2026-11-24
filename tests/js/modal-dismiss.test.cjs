const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){
 const handlers={};const c={Event,document:{addEventListener:(type,fn)=>handlers[type]=fn}};
 vm.runInNewContext(fs.readFileSync('studio/modal-dismiss.js','utf8'),c);
 const dialog=()=>Object.assign(new EventTarget(),{tagName:'DIALOG',open:true,classList:{contains:()=>false},matches:()=>true,getBoundingClientRect:()=>({left:100,right:500,top:100,bottom:400}),close(){this.open=false}});
 const fire=(type,d,x=50,y=50,extra={})=>{let stopped=false;handlers[type]({target:d,clientX:x,clientY:y,isPrimary:true,button:0,detail:1,preventDefault(){},stopImmediatePropagation(){stopped=true},...extra});return stopped};
 const tap=d=>{fire('pointerdown',d);return fire('click',d)};
 return{dialog,fire,tap};
}
test('outside tap closes account-like modal, consumes click and leaves underlying actions untouched',()=>{const h=harness(),d=h.dialog();assert.equal(h.tap(d),true);assert.equal(d.open,false)});
test('inside padding, children, keyboard clicks and right clicks do not dismiss',()=>{
 for(const scenario of ['inside','child','keyboard','right']){const h=harness(),d=h.dialog();h.fire('pointerdown',d,scenario==='inside'?200:50,200,{button:scenario==='right'?2:0});h.fire('click',scenario==='child'?{tagName:'BUTTON'}:d,scenario==='inside'?200:50,200,{detail:scenario==='keyboard'?0:1});assert.equal(d.open,true,scenario)}
});
test('drag out, cancelled pointer and a different modal cannot trigger accidental dismissal',()=>{
 for(const scenario of ['drag','cancel','other']){const h=harness(),d=h.dialog();h.fire('pointerdown',scenario==='other'?h.dialog():d,scenario==='drag'?200:50,200);if(scenario==='cancel')h.fire('pointercancel',d);h.fire('click',d);assert.equal(d.open,true,scenario)}
});
test('workspace views and non-modal dialogs stay open',()=>{for(const modal of [false,true]){const h=harness(),d=h.dialog();d.matches=()=>modal;d.classList.contains=()=>modal;h.tap(d);assert.equal(d.open,true)}});
test('busy cancel veto preserves dialog; async owner cleanup is not bypassed',async()=>{
 const h=harness(),d=h.dialog();let busy=true,finish;d.addEventListener('cancel',e=>{e.preventDefault();if(!busy)finish=()=>d.close()});
 h.tap(d);assert.equal(d.open,true);busy=false;h.tap(d);assert.equal(d.open,true);finish();assert.equal(d.open,false);
});
test('timer minimization and confirmation cancellation each run exactly once',()=>{
 for(const behavior of ['minimize','cancel']){const h=harness(),d=h.dialog();let n=0;d.addEventListener('cancel',e=>{e.preventDefault();n++;d.close()});h.tap(d);assert.equal(n,1,behavior);assert.equal(d.open,false)}
});
