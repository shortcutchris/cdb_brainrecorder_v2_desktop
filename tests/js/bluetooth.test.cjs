const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('studio/bluetooth.js','utf8'),code=source.slice(source.indexOf('function btControls('),source.indexOf('function renderBluetooth(')),c={};vm.createContext(c);vm.runInContext(code,c);
const state={recording:{id:null},live:{busy:false},capabilities:{configure:{allowed:true}}},data={supported:true,powered:true,busy:false};
test('Bluetooth blocks during recording, live, other activity or offline',()=>{for(const s of [{...state,recording:{id:'active'}},{...state,live:{busy:true}},{...state,capabilities:{configure:{allowed:false}}}])assert.equal(c.btControls(data,s,true,false).locked,true);assert.equal(c.btControls(data,state,false,false).locked,true)});
test('Bluetooth own operation allows cancellation while other operations stay blocked',()=>{assert.equal(c.btControls({...data,busy:true},{...state,capabilities:{configure:{allowed:false}}},true,false).locked,false);assert.equal(c.btControls(data,state,true,true).locked,true)});
test('saved pairing and Bluetooth link do not imply audio readiness',()=>{
 assert.equal(c.btDeviceStatus({paired:true,connected:false}),'Gekoppelt · nicht verbunden');
 assert.equal(c.btDeviceStatus({paired:true,connected:true}),'Verbunden · Audio fehlt');
 assert.equal(c.btAudio({connected:false,profile:{sinks:[{id:'old'}]}}).outputs.length,0);
 const device={connected:true,profile:{sinks:[{id:'marshall'}],sources:[]}};
 assert.equal(c.btDeviceStatus(device),'Audio bereit');assert.equal(c.btAudio(device).outputs[0].id,'marshall');assert.equal(c.btAudio(device).inputs.length,0);
});
test('speaker shortcut selects the exact Bluetooth output before navigation; failure stays put',async()=>{
 const nodes={},calls=[],navigated=[];let fail=false;
 const sandbox={$:id=>nodes[id]||(nodes[id]={}),showSettingsDetail:p=>navigated.push(p),renderState:()=>{},notice:()=>{},poll:async()=>{},speakerRevision:0,api:async(path,body)=>{calls.push({path,body});if(fail)throw Error('Disconnected');return{selected:body.device}}};
 vm.createContext(sandbox);vm.runInContext(source,sandbox);
 vm.runInContext("renderBluetooth=()=>{};loadSpeakers=()=>{};loadBluetooth=()=>{};btSelected='box';btData={devices:[{id:'box',connected:true,profile:{sinks:[{id:'exact-marshall-output'}]}}]}",sandbox);
 await nodes['bt-to-speaker'].onclick();assert.equal(calls[0].body.device,'exact-marshall-output');assert.deepEqual(navigated,['speaker-page']);
 fail=true;await nodes['bt-to-speaker'].onclick();assert.equal(navigated.length,1);
 vm.runInContext('btData.devices[0].connected=false',sandbox);await nodes['bt-to-speaker'].onclick();assert.equal(calls.length,2);
});
