const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={};vm.createContext(ctx);vm.runInContext(fs.readFileSync('studio/speakers.js','utf8').split('function renderSpeakers')[0],ctx);
const s=()=>({recording:{id:null},capabilities:{configure:{allowed:true}},speaker_test:{state:'idle'}}),d=()=>({available:true,devices:[{id:'usb'}],volume:50,muted:false});
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
