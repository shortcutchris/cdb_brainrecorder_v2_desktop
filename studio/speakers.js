/* Device changes and tones are executed by Python on the Pi, not Web Audio. */
let speakerData=null,speakerBusy=false,speakerLoading=false,speakerLoadedAt=0,speakerError='',speakerRevision=0;
function speakerControls(data,s,connected,busy){
 const running=s?.speaker_test?.state==='running';
 const locked=!connected||busy||Boolean(s?.recording.id)||s?.capabilities?.configure?.allowed===false;
 const usable=Boolean(data?.available);
 return {running,locked,usable,select:!locked&&Boolean(data?.devices?.length),volume:!locked&&usable,
  test:running?!busy&&connected&&!s?.recording.id:!locked&&usable&&!data.muted&&data.volume>0};
}
function announcementControls(s,connected,busy){
 const a=s?.announcements||{};
 const locked=!connected||busy||Boolean(s?.recording?.id)||s?.capabilities?.configure?.allowed===false;
 return {reload:!locked,offline:!locked&&Boolean(a.ready||a.offline),timers:!locked&&Boolean(a.ready||a.timers),connecting:!locked&&Boolean(a.connecting_ready||a.connecting),countdown:!locked&&Boolean(a.countdown_ready||a.countdown),
  stop:connected&&!busy&&!s?.recording?.id&&s?.speaker_test?.state==='running'};
}
function renderAnnouncements(){
 const a=state?.announcements||{},c=announcementControls(state,online,speakerBusy);
 for(const key of ['offline','timers','connecting','countdown']){
  const button=$('announcements-'+key);button.disabled=!c[key];
  button.textContent=a[key]?'Ein':'Aus';
  button.setAttribute('aria-label',({offline:'Gesprächshinweis',timers:'Timer-Ansagen',connecting:'Verbindungsansage',countdown:'Timer-Countdown'}[key])+(a[key]?' ausschalten':' einschalten'));button.setAttribute('aria-pressed',String(Boolean(a[key])));
 }
 $('announcements-status').textContent=!online?'Verbindung zum Pi unterbrochen.':a.message||'Sprachpaket wird geprüft.';
 $('announcements-stop').disabled=!c.stop;
 $('announcements-reload').disabled=!c.reload;
}
function deviceSoundControls(s,output,connected,busy){
 const locked=!connected||busy||Boolean(s?.recording?.id)||s?.capabilities?.configure?.allowed!==true;
 return {toggle:!locked,preview:!locked&&Boolean(output?.available)&&!output.muted&&output.volume>0,
  stop:connected&&!busy&&!s?.recording?.id&&s?.speaker_test?.state==='running'};
}
function renderDeviceSounds(){
 const controls=deviceSoundControls(state,speakerData,online,speakerBusy);
 for(const kind of ['startup','shutdown']){
  const button=$('device-sound-'+kind),enabled=state?.device_sounds?.[kind]===true;
  button.disabled=!controls.toggle;button.setAttribute('aria-pressed',String(enabled));button.textContent=enabled?'Eingeschaltet · ausschalten':'Ausgeschaltet · einschalten';
  $('device-sound-preview-'+kind).disabled=!controls.preview;
 }
 $('device-sound-stop').disabled=!controls.stop;
 $('device-sound-status').textContent=speakerError||(!online?'Verbindung zum Pi unterbrochen.':state?.speaker_test?.state==='running'?state.speaker_test.message:!speakerData?.available?'Zum Vorhören einen Lautsprecher anschließen und auswählen.':speakerData.muted||speakerData.volume===0?'Dein Pi ist stumm. Lautstärke unter „Lautsprecher & Lautstärke“ ändern.':'Vorhören schaltet den Pi nicht aus. Der Startklang gilt ab dem nächsten Einschalten.');
}
let deviceReadyToken='',deviceReadyPending=false,deviceReadyRetryAt=0;
function signalDeviceReady(){
 const token=state?.csrf;
 if(!online||!token||token===deviceReadyToken||deviceReadyPending||Date.now()<deviceReadyRetryAt)return;
 deviceReadyPending=true;
 api('/api/device/ready',{}).then(()=>{deviceReadyToken=token}).catch(()=>{deviceReadyRetryAt=Date.now()+5000}).finally(()=>{deviceReadyPending=false});
}
function renderSpeakers(){
 renderAnnouncements();renderDeviceSounds();
 const d=speakerData,c=speakerControls(d,state,online,speakerBusy),test=state?.speaker_test||d?.test||{};
 const selected=d?.selected||'',entries=d?.devices||[];
 const options=entries.map(x=>[x.id,x.label]);
 if(!entries.some(x=>x.id===selected))options.unshift([selected,d?.devices?.length?'Gewählter Ausgang nicht verbunden':'Kein Lautsprecher erkannt']);
 const select=$('speaker-select'),signature=JSON.stringify(options);
 if(select.dataset.options!==signature){fillSelect(select,options.map(([id,label])=>({id,label})),selected,'id',x=>x.label);select.dataset.options=signature}
 select.value=selected;select.disabled=!c.select;
 $('speaker-volume').textContent=c.usable?d.volume+' %':'—';
 $('speaker-volume-state').textContent=c.usable?(d.muted?'Stumm':'Aktiv'):'Kein Ausgang';
 $('speaker-quieter').disabled=!c.volume||d.volume<=0;$('speaker-louder').disabled=!c.volume||d.volume>=100;
 $('speaker-mute').disabled=!c.volume;$('speaker-mute').textContent=d?.muted?'Ton einschalten':'Stummschalten';$('speaker-mute').setAttribute('aria-pressed',String(Boolean(d?.muted)));
 $('speaker-test').disabled=!c.test;$('speaker-test').textContent=c.running?'Audioausgabe stoppen':'Testton am Pi';
 $('speaker-refresh').disabled=speakerBusy||speakerLoading||!online||Boolean(state?.recording.id);
 $('speaker-state').textContent=!online?'Verbindung unterbrochen':c.usable?'Lautsprecher verbunden':d?'Kein nutzbarer Ausgang':'Wird geprüft';
 $('speaker-led').dataset.ready=String(online&&c.usable);
 $('speaker-description').textContent=speakerError||d?.message||'Audioausgänge werden geladen.';
 const matching=test.device===selected||!test.device;
 $('speaker-test-label').textContent=!c.usable?'Kein Ausgang':c.running?'Wird abgespielt …':matching&&test.state==='completed'?'Audioausgabe beendet':matching&&test.state==='failed'?'Fehlgeschlagen':'Bereit zum Prüfen';
 $('speaker-test-label').dataset.running=String(c.running);
 $('speaker-test-status').textContent=!online?'Verbindung zum Pi prüfen.':state?.recording.id?'Während der Aufnahme gesperrt.':c.running?test.message:!c.usable?'Zuerst einen Lautsprecher anschließen und auswählen.':d?.muted?'Vor dem Testton den Ton einschalten.':c.usable&&d.volume===0?'Vor dem Testton die Lautstärke erhöhen.':matching&&['completed','failed','cancelled'].includes(test.state)?test.message:'Zwei kurze Töne: erst links, dann rechts.';
}
async function loadSpeakers(force=false){
 if(speakerLoading||speakerBusy||!online||state?.recording.id)return;
 if(!force&&Date.now()-speakerLoadedAt<5000)return;
 const revision=speakerRevision;
 speakerLoading=true;renderSpeakers();
 try{const data=await api('/api/speakers');if(revision===speakerRevision){speakerData=data;speakerError=''}}catch(e){if(revision===speakerRevision){speakerData=null;speakerError=e.message}}
 finally{speakerLoading=false;speakerLoadedAt=Date.now();renderSpeakers()}
}
async function speakerAction(path,body){
 if(speakerBusy||!online||state?.recording.id)return;
 speakerBusy=true;speakerRevision++;speakerError='';renderSpeakers();
 try{const result=await api(path,body);if(path==='/api/speakers')speakerData=result;await poll()}
 catch(e){speakerError=e.message;notice(e.message)}
 finally{speakerBusy=false;speakerLoadedAt=0;renderSpeakers();await loadSpeakers(true)}
}
$('audio-microphone').onclick=()=>showSettingsDetail('audio-page');
$('audio-speakers').onclick=()=>showSettingsDetail('speaker-page');
$('speaker-select').onchange=()=>speakerAction('/api/speakers',{device:$('speaker-select').value});
$('speaker-quieter').onclick=()=>speakerAction('/api/speakers',{volume:Math.max(0,speakerData.volume-5)});
$('speaker-louder').onclick=()=>speakerAction('/api/speakers',{volume:Math.min(100,speakerData.volume+5)});
$('speaker-mute').onclick=()=>speakerAction('/api/speakers',{muted:!speakerData.muted});
$('speaker-test').onclick=()=>speakerAction(state?.speaker_test?.state==='running'?'/api/speakers/stop':'/api/speakers/test',{});
$('speaker-refresh').onclick=()=>loadSpeakers(true);
const beforeSpeakerDetail=showSettingsDetail;
showSettingsDetail=function(page){beforeSpeakerDetail(page);if(['speaker-page','device-sounds-page'].includes(page))loadSpeakers(true)};
const beforeSpeakerState=renderState;
renderState=function(){beforeSpeakerState();renderSpeakers();signalDeviceReady();if((!$('speaker-page').hidden||!$('device-sounds-page').hidden)&&$('settings').open&&$('settings').dataset.overview!=='true')loadSpeakers()};

$('audio-announcements').onclick=()=>showSettingsDetail('announcements-page');
$('speaker-announcements').onclick=()=>showSettingsDetail('announcements-page');
for(const key of ['offline','timers','connecting','countdown'])$('announcements-'+key).onclick=()=>speakerAction('/api/announcements',{[key]:!state?.announcements?.[key]});
$('announcements-stop').onclick=()=>speakerAction('/api/speakers/stop',{});
$('announcements-reload').onclick=()=>speakerAction('/api/announcements/reload',{});

$('speaker-device-sounds').onclick=()=>showSettingsDetail('device-sounds-page');
$('device-sound-output').onclick=()=>showSettingsDetail('speaker-page');
$('device-sound-stop').onclick=()=>speakerAction('/api/speakers/stop',{});
for(const kind of ['startup','shutdown']){
 $('device-sound-'+kind).onclick=()=>speakerAction('/api/device/sounds',{[kind]:!state?.device_sounds?.[kind]});
 $('device-sound-preview-'+kind).onclick=()=>speakerAction('/api/device/sounds/test',{kind});
}
