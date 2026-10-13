/* Bluetooth control remains on the Pi, with one bounded pairing reservation. */
let btData=null,btPage=0,btSelected=null,btLoading=false,btRequest=false,btLoadedAt=0,btSignature='',btPromptId='';
function btControls(data,s,connected,request){const exclusive=Boolean(s?.recording.id||s?.live?.busy||(!s?.capabilities.configure.allowed&&!data?.busy));return{locked:!connected||exclusive||request,busy:Boolean(data?.busy),ready:Boolean(data?.supported&&data?.powered)}}
function btAudio(device){const p=device?.connected?device.profile:null;return{outputs:p?.sinks||[],inputs:p?.sources||[]}}
function btDeviceStatus(device){const a=btAudio(device);return device?.connected?(a.outputs.length||a.inputs.length?'Audio bereit':'Verbunden · Audio fehlt'):device?.paired?'Gekoppelt · nicht verbunden':'Nicht gekoppelt'}
function renderBluetooth(){
 const d=btData||state?.bluetooth||{},c=btControls(d,state,online,btRequest),rows=d.devices||[],prompt=d.prompt;if(prompt)btSelected=prompt.device;const selected=rows.find(r=>r.id===btSelected);
 $('bt-adapter').textContent=d.supported?(d.adapter+' · '+(d.powered?'Eingeschaltet':'Ausgeschaltet')):'Bluetooth-Dienst am Pi prüfen.';
 $('bt-state').textContent=d.busy?(d.operation==='scan'?'Sucht …':'Wird eingerichtet …'):d.powered?'Bluetooth bereit':'Bluetooth aus';$('bt-state').dataset.busy=String(Boolean(d.busy));
 $('bt-message').textContent=!online?'Verbindung zum Pi unterbrochen.':c.locked&&!btRequest?state?.capabilities.configure.reason||'Bitte warten.':(!d.busy&&selected&&d.message==='Gerät in den Kopplungsmodus versetzen und suchen.'?btDeviceStatus(selected):d.message)||'';
 $('bt-count').textContent=rows.length+(rows.length===1?' Gerät':' Geräte');btPage=Math.min(btPage,Math.max(0,Math.ceil(rows.length/3)-1));
 const signature=JSON.stringify([rows,btPage,btSelected,c.locked,d.busy,d.operation]);
 if(signature!==btSignature){btSignature=signature;$('bt-devices').replaceChildren();for(const row of rows.slice(btPage*3,btPage*3+3)){const button=document.createElement('button');button.className='bt-device';button.setAttribute('aria-pressed',String(row.id===btSelected));const name=document.createElement('strong'),info=document.createElement('span');name.textContent=row.name;info.textContent=btDeviceStatus(row)+' · '+(row.audio?'Audio-Gerät':row.address);button.append(name,info);button.disabled=c.locked||d.busy&&d.operation!=='scan';button.onclick=()=>{btSelected=row.id;$('bt-forget-confirm').hidden=true;renderBluetooth()};$('bt-devices').append(button)}if(!rows.length)$('bt-devices').textContent=d.operation==='scan'?'Suche nach Geräten in deiner Nähe …':'Noch keine Geräte. Schalte dein Bluetooth-Gerät in den Kopplungsmodus.';drawPageNumbers($('bt-pages'),Math.max(1,Math.ceil(rows.length/3)),btPage,i=>{btPage=i;renderBluetooth()});}
 $('bt-device-name').textContent=selected?.name||'Gerät auswählen';$('bt-device-state').textContent=selected?(selected.connected?(btAudio(selected).outputs.length||btAudio(selected).inputs.length?'Audio bereit. Wähle unten, wofür du dieses Gerät verwenden möchtest.':'Bluetooth verbunden, aber der Pi hat noch keinen Audioausgang oder Eingang erkannt.'):selected.paired?'Nur gekoppelt, noch nicht verbunden. Erst verbinden; danach wird die Audioauswahl verfügbar.':'Gerät in den Kopplungsmodus versetzen und koppeln.'):'Wähle links ein Gerät aus der Liste.';
 $('bt-pairing').hidden=!prompt;$('bt-device-controls').hidden=!selected||Boolean(prompt);
 if(prompt){$('bt-prompt-label').textContent=prompt.kind==='confirm'?'Stimmt dieser Code auf beiden Geräten überein?':prompt.kind==='display'?'Diesen Code am Bluetooth-Gerät eingeben:':['pin','passkey'].includes(prompt.kind)?'Code des Bluetooth-Geräts eingeben:':'Dieses Gerät koppeln?';$('bt-code').textContent=prompt.code||'';$('bt-pin').hidden=!['pin','passkey'].includes(prompt.kind);$('bt-confirm').hidden=prompt.kind==='display';$('bt-reject').hidden=prompt.kind==='display';if(btPromptId!==prompt.id){btPromptId=prompt.id;$('bt-pin').value=''}$('bt-confirm').disabled=c.locked;$('bt-reject').disabled=c.locked;}
 const profile=selected?.profile,options=profile?.profiles||[],select=$('bt-profile');if(select.dataset.signature!==JSON.stringify(options)){select.dataset.signature=JSON.stringify(options);select.replaceChildren(...options.map(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=p.label;return o}))}select.value=profile?.active||'';
 $('bt-profile-block').hidden=!options.length;select.disabled=c.locked||c.busy;
 $('bt-profile-hint').textContent=options.length?(options.some(p=>p.id.startsWith('headset-head-unit'))?'Musik: hochwertige Wiedergabe. Gespräch: Mikrofon + Lautsprecher, gegebenenfalls geringere Klangqualität.':'Dieses Gerät bietet Lautsprecherwiedergabe. Ein Bluetooth-Mikrofon ist hier nicht verfügbar.'):'Audioauswahl wird nach dem Verbinden verfügbar. Nicht jedes Gerät unterstützt ein Mikrofon.';
 $('bt-connect').textContent=selected?.connected?'Trennen':selected?.paired?'Verbinden':'Koppeln';$('bt-connect').disabled=c.locked||!c.ready||c.busy&&d.operation!=='scan';$('bt-forget').hidden=!selected?.paired;$('bt-forget').disabled=c.locked||c.busy;
 $('bt-power').textContent=d.powered?'Bluetooth ausschalten':'Bluetooth einschalten';$('bt-power').disabled=c.locked||!d.supported||c.busy;
 $('bt-scan').hidden=c.busy;$('bt-scan').disabled=c.locked||!c.ready;$('bt-cancel').hidden=!c.busy;$('bt-cancel').disabled=c.locked;
 for(const id of ['bt-forget-no','bt-forget-yes'])$(id).disabled=c.locked||c.busy;
 const audio=btAudio(selected);$('bt-to-mic').disabled=c.locked||c.busy||!audio.inputs.length;$('bt-to-speaker').disabled=c.locked||c.busy||!audio.outputs.length;
}
async function loadBluetooth(force=false){if(btLoading||!online||!force&&Date.now()-btLoadedAt<2500)return;btLoading=true;try{btData=await api('/api/bluetooth')}catch(e){notice(e.message)}finally{btLoading=false;btLoadedAt=Date.now();renderBluetooth()}}
async function btAction(action,extra={}){if(btRequest)return;btRequest=true;renderBluetooth();try{btData=await api('/api/bluetooth',{action,device:btSelected,...extra});await poll()}catch(e){notice(e.message)}finally{btRequest=false;btLoadedAt=0;renderBluetooth();await loadBluetooth(true)}}
$('audio-bluetooth').onclick=()=>showSettingsDetail('bluetooth-page');
$('bt-power').onclick=()=>btAction('power',{powered:!btData?.powered});$('bt-scan').onclick=()=>btAction('scan');$('bt-cancel').onclick=()=>btAction('cancel');
$('bt-connect').onclick=()=>{const d=btData?.devices.find(d=>d.id===btSelected);if(d)btAction(d.connected?'disconnect':d.paired?'connect':'pair')};
$('bt-profile').onchange=()=>btAction('profile',{profile:$('bt-profile').value});
$('bt-forget').onclick=()=>{$('bt-forget-confirm').hidden=false};$('bt-forget-no').onclick=()=>{$('bt-forget-confirm').hidden=true};$('bt-forget-yes').onclick=()=>{$('bt-forget-confirm').hidden=true;btAction('forget',{confirmed:true})};
$('bt-confirm').onclick=()=>btAction('reply',{id:btData.prompt.id,accept:true,value:$('bt-pin').value});$('bt-reject').onclick=()=>btAction('reply',{id:btData.prompt.id,accept:false});
$('bt-to-mic').onclick=async()=>{await loadSetup();showSettingsDetail('audio-page')};$('bt-to-speaker').onclick=async()=>{
 const selected=btData?.devices.find(d=>d.id===btSelected),output=btAudio(selected).outputs[0];
 if(!output||btRequest)return;btRequest=true;renderBluetooth();
 try{const result=await api('/api/speakers',{device:output.id});speakerRevision++;speakerData=result;speakerError='';speakerLoadedAt=Date.now();showSettingsDetail('speaker-page');await poll()}
 catch(e){notice(e.message)}finally{btRequest=false;renderBluetooth()}
};
const beforeBluetoothDetail=showSettingsDetail;showSettingsDetail=function(page){beforeBluetoothDetail(page);if(page==='bluetooth-page')loadBluetooth(true)};
const beforeBluetoothState=renderState;renderState=function(){beforeBluetoothState();if(state?.bluetooth)btData=state.bluetooth;if(!$('bluetooth-page').hidden&&$('settings').open){renderBluetooth();loadBluetooth()}};
