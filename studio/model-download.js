'use strict';
function queueFileSize(bytes){
 if(!Number.isFinite(bytes)||bytes<0)return '–';
 const units=['B','kB','MB','GB'];let unit=0;
 while(bytes>=1000&&unit<units.length-1){bytes/=1000;unit++}
 return bytes.toLocaleString('de-DE',{maximumFractionDigits:unit?1:0})+' '+units[unit];
}
function modelDownload(d,catalog){
 if(!d||!['running','failed','completed'].includes(d.state))return null;
 const whisper=d.backend==='whisper';
 const entry=catalog?.[whisper?'asr':'llm']?.find(m=>m.id===d.model);
 const view={
  model:entry?.label||(whisper?'Whisper '+d.model:d.model),
  kind:whisper?'Transkriptionsmodell':'Zusammenfassungsmodell',
  phase:'Download wird vorbereitet …',percent:null,amount:''
 };
 if(d.state==='completed'){view.phase='Modell installiert';return view}
 if(d.state==='failed'){view.phase='Download fehlgeschlagen'+(d.message?' · '+d.message:'');return view}
 const message=d.message||'';
 if(/prüfsumme bestätigt|bereits vorhanden|writing manifest|modell installiert|ollama: success/i.test(message)){
  view.phase='Installation wird abgeschlossen …';
 }else if(/verifying/i.test(message)){
  view.phase='Modelldaten werden geprüft …';
 }else if(/pulling manifest/i.test(message)){
  view.phase='Modellinformationen werden geladen …';
 }else if(/heruntergeladen|ollama: pulling |^ollama: download$/i.test(message)){
  view.phase=whisper?'Modelldatei wird geladen':'Modellabschnitt wird geladen';
  if(Number.isFinite(d.completed)&&d.completed>=0){
   if(Number.isFinite(d.total)&&d.total>0){
    view.percent=Math.min(100,Math.floor(100*d.completed/d.total));
    view.amount=queueFileSize(d.completed)+' von '+queueFileSize(d.total);
   }else if(d.completed>0){view.amount=queueFileSize(d.completed)+' geladen'}
  }
 }
 return view;
}
