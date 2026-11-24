const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={};vm.createContext(ctx);vm.runInContext(fs.readFileSync('studio/speakers.js','utf8').split('function renderSpeakers')[0],ctx);
const s=()=>({recording:{id:null},capabilities:{configure:{allowed:true}},speaker_test:{state:'idle'}}),d=()=>({available:true,devices:[{id:'usb'}],volume:50,muted:false});
test('USB recovery needs an installed eligible helper and remains blocked during other work',()=>{
 const data={...d(),recovery:{available:true,running:false}},state=s();
 assert.equal(ctx.recoveryControls(data,state,true,false).allowed,true);
 for(const value of [undefined,{}, {available:false}, {available:true,running:true}])
  assert.equal(ctx.recoveryControls({...data,recovery:value},state,true,false).allowed,false);
 for(const [connected,busy] of [[false,false],[true,true]])
  assert.equal(ctx.recoveryControls(data,state,connected,busy).allowed,false);
 for(const override of [{recording:{id:'active'}},{recording:{id:'active',paused:true}},
  {capabilities:{configure:{allowed:false}}},{live:{busy:true}},
  {timers:{items:[{state:'scheduled'}]}},{timers:{items:[{state:'due'}]}},
  {jobs:[{state:'transcribing'}]},{cdb:{publications:[{state:'sending'}]}}])
  assert.equal(ctx.recoveryControls(data,{...state,...override},true,false).allowed,false);
});
test('recording blocks every speaker mutation, including tone stop',()=>{const state=s();state.recording.id='active';for(const key of ['select','volume','test'])assert.equal(ctx.speakerControls(d(),state,true,false)[key],false)});
test('missing output and offline cannot play a test tone',()=>{assert.equal(ctx.speakerControls({...d(),available:false},s(),true,false).test,false);assert.equal(ctx.speakerControls(d(),s(),false,false).test,false)});
test('muted or silent speakers keep volume available but block tests',()=>{for(const data of [{...d(),muted:true},{...d(),volume:0}]){const c=ctx.speakerControls(data,s(),true,false);assert.equal(c.volume,true);assert.equal(c.test,false)}});
test('running tone can be stopped while other settings are locked',()=>{const state=s();state.speaker_test.state='running';state.capabilities.configure.allowed=false;const c=ctx.speakerControls(d(),state,true,false);assert.equal(c.test,true);assert.equal(c.select,false);assert.equal(c.volume,false)});
test('speech opt-in requires a pack, but disabling remains possible without one',()=>{
 const state=s();state.announcements={ready:false,offline:false,timers:true};
 const c=ctx.announcementControls(state,true,false);assert.equal(c.offline,false);assert.equal(c.timers,true);
 state.announcements.ready=true;assert.equal(ctx.announcementControls(state,true,false).offline,true);
});
test('speech controls obey recording, pause, disconnected and occupied guards',()=>{
 const state=s();state.announcements={ready:true,offline:true,timers:true};
 for(const [connected,busy] of [[false,false],[true,true]])for(const key of ['offline','timers'])assert.equal(ctx.announcementControls(state,connected,busy)[key],false);
 state.recording={id:'active',paused:true};state.speaker_test.state='running';
 for(const key of ['offline','timers','stop'])assert.equal(ctx.announcementControls(state,true,false)[key],false);
 state.recording.id=null;state.capabilities.configure.allowed=false;
 assert.equal(ctx.announcementControls(state,true,false).offline,false);assert.equal(ctx.announcementControls(state,true,false).stop,true);
});

test('connecting voice requires its optional clip and follows activity lock',()=>{const state=s();state.announcements={ready:true,connecting_ready:false,connecting:false};assert.equal(ctx.announcementControls(state,true,false).connecting,false);state.announcements.connecting_ready=true;assert.equal(ctx.announcementControls(state,true,false).connecting,true);state.capabilities.configure.allowed=false;assert.equal(ctx.announcementControls(state,true,false).connecting,false)});
test('countdown has its own pack gate and can be disabled after pack loss',()=>{
 const state=s();state.announcements={ready:true,countdown_ready:false,countdown:false};
 assert.equal(ctx.announcementControls(state,true,false).countdown,false);
 state.announcements.countdown_ready=true;assert.equal(ctx.announcementControls(state,true,false).countdown,true);
 state.announcements.countdown_ready=false;state.announcements.countdown=true;
 assert.equal(ctx.announcementControls(state,true,false).countdown,true);
 for(const [connected,busy] of [[false,false],[true,true]])assert.equal(ctx.announcementControls(state,connected,busy).countdown,false);
 state.recording={id:'recording',paused:true};assert.equal(ctx.announcementControls(state,true,false).countdown,false);
 state.recording.id=null;state.capabilities.configure.allowed=false;assert.equal(ctx.announcementControls(state,true,false).countdown,false);
});

test('device sounds keep preferences separate from audible previews and obey all activity locks',()=>{
 const state=s(),output=d();
 assert.equal(ctx.deviceSoundControls(state,output,true,false).toggle,true);
 for(const data of [null,{...output,available:false},{...output,muted:true},{...output,volume:0}]){
  const c=ctx.deviceSoundControls(state,data,true,false);assert.equal(c.toggle,true);assert.equal(c.preview,false);
 }
 for(const [online,busy] of [[false,false],[true,true]]){const c=ctx.deviceSoundControls(state,output,online,busy);assert.equal(c.toggle,false);assert.equal(c.preview,false)}
 state.recording={id:'active',paused:true};state.speaker_test.state='running';
 for(const value of Object.values(ctx.deviceSoundControls(state,output,true,false)))assert.equal(value,false);
 state.recording.id=null;state.capabilities.configure.allowed=false;
 const c=ctx.deviceSoundControls(state,output,true,false);assert.equal(c.toggle,false);assert.equal(c.preview,false);assert.equal(c.stop,true);
});
