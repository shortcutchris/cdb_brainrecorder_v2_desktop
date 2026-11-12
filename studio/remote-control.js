(() => {
 let revokeConfirm=false;
 const errors={storage_unavailable:'Gerätespeicher nicht verfügbar. Lokale Bedienung bleibt erhalten.',not_supported:'Diese Brain-Umgebung bietet die Fernbedienung noch nicht an.',sign_in_required:'Bitte beim Brain erneut anmelden.',access_denied:'Keine Freigabe für dieses Konto. Bitte Anmeldung prüfen.',unavailable:'Brain ist gerade nicht erreichbar. Bereits laufende Gespräche bleiben erhalten.',conflict:'Es besteht bereits eine Kopplung oder Anfrage. Bitte zuerst entkoppeln.',expired:'Der Code ist abgelaufen. Bitte einen neuen erzeugen.',rate_limited:'Zu viele Versuche. Bitte etwas warten.',invalid_response:'Die Serverantwort konnte nicht sicher geprüft werden.',stale_response:'Verbindung wird neu abgeglichen.',account_changed:'Das Brain-Konto hat sich geändert.'};
 const labels={unpaired:'Nicht gekoppelt',ready:'Bereit zum Koppeln',connecting:'Verbindung wird geprüft',pairing:'Code bereit',confirm:'Bestätigung erforderlich',paired:'Mit cdbMOBILE gekoppelt',revoking:'Wird entkoppelt',unsupported:'Noch nicht verfügbar',offline:'Verbindung unterbrochen',error:'Verbindung prüfen'};
 const text=(id,value)=>{if($(id).textContent!==value)$(id).textContent=value};
 function render(){
  const r=state?.remote_control||{},pending=r.pending?.[0],blocked=!allowed('configure')||r.busy||r.state==='revoking';
  if($('remote-page').hidden)revokeConfirm=false;
  text('remote-state',labels[r.state]||'Nicht gekoppelt');$('remote-led').dataset.online=String(Boolean(r.online&&r.paired));
  text('remote-environment',r.environment?r.environment.replace('https://',''):'Dasselbe Brain-Konto in cdbMOBILE verwenden.');
  text('remote-message',revokeConfirm?'Verbindung wirklich entfernen? Das Handy verliert seine Steuerrechte. Ein laufendes Gespräch bleibt bestehen.':r.error?(errors[r.error]||'Verbindung konnte nicht geprüft werden.'):!r.account_ready?'Bitte zuerst unter Brain-Konto anmelden.':r.paired?'Start, Ende und Stummschaltung sind freigegeben.':r.busy?'Verbindung wird geprüft …':'Kopplung nur mit deinem angemeldeten Brain-Konto.');
  text('remote-step-title',pending?'Handy bestätigen':r.paired?'Verbindung eingerichtet':'Sicher verbinden');
  text('remote-step-help',pending?'Bestätige nur die gerade von dir angeforderte Verbindung.':r.paired?'Öffne auf dem Handy die Pi-Fernbedienung.':'Code erzeugen und in cdbMOBILE unter Pi-Fernbedienung eingeben.');
  text('remote-code',pending?'Bestätigen':r.paired?'Verbunden':r.code? r.code.slice(0,4)+' '+r.code.slice(4):'— — — —');
  text('remote-code-caption',pending?'Die App wartet auf deine Zustimmung.':r.code?'Einmalcode · fünf Minuten gültig':r.paired?'Dieses Handy darf Gespräche am Pi steuern.':'Anschließend bestätigst du hier am Pi.');
  text('remote-controller',pending?'App-Kennung: '+pending.controller_id.slice(0,8):'');
  text('remote-primary',pending?'Handy freigeben':'Code erzeugen');
  $('remote-primary').disabled=blocked||!r.account_ready||Boolean(r.paired)||Boolean(r.code);
  $('remote-reject').dataset.inactive=String(!pending);$('remote-reject').disabled=blocked||!pending;
  text('remote-revoke',revokeConfirm?'Jetzt entkoppeln':'Entkoppeln');$('remote-revoke').disabled=blocked||!r.device_id;
  $('remote-check').disabled=blocked||!r.account_ready;
 }
 async function send(action,body={}){await api('/api/remote-control/'+action,body);await poll()}
 $('management-remote').onclick=()=>showSettingsDetail('remote-page');
 $('remote-check').onclick=run(()=>send('check'));
 $('remote-primary').onclick=run(()=>{const p=state?.remote_control?.pending?.[0];return p?send('confirm',{pairing_id:p.pairing_id,approved:true}):send('pair')});
 $('remote-reject').onclick=run(()=>{const p=state?.remote_control?.pending?.[0];if(p)return send('confirm',{pairing_id:p.pairing_id,approved:false})});
 $('remote-revoke').onclick=run(async()=>{if(!revokeConfirm){revokeConfirm=true;render();return}revokeConfirm=false;await send('revoke')});
 const previous=renderState;renderState=function(){previous();render()};render();
})();
