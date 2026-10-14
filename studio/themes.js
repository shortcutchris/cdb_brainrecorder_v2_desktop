'use strict';
// Preferences stay in this kiosk profile and never change audio/model settings.
(()=>{
 const root=document.documentElement,key='cdb-studio-theme',customKey='cdb-studio-custom-themes-v1';
 const labels={blue:'Blau · Hell',petrol:'Petrol · Hell',midnight:'Mitternacht',graphite:'Graphit',cdb:'Corporate Digital Brain'};
 const fields={surface:'Hintergrund',panel:'Flächen',capture:'Aufnahmebereich',ink:'Text',accent:'Akzentfarbe'};
 const tokens=['ink','muted','surface','panel','capture','line','accent','on-accent','soft','accent-text','ring','keyboard','scroll','player','wave','icon-filter','active-filter','on-icon'];
 const hex=value=>typeof value==='string'&&/^#[0-9a-f]{6}$/i.test(value);
 const valid=t=>t&&/^custom-[a-z0-9-]+$/.test(t.id)&&typeof t.name==='string'&&t.name.trim().length>0&&t.name.length<=40&&Object.keys(fields).every(k=>hex(t.colors?.[k]));
 let themes=[],current='blue',persistent=true,draft=null,editingId=null;
 function read(){try{const parsed=JSON.parse(localStorage.getItem(customKey)||'[]');themes=Array.isArray(parsed)?parsed.filter(valid).slice(0,100):[];const saved=localStorage.getItem(key);current=Object.hasOwn(labels,saved)||themes.some(t=>t.id===saved)?saved:'blue'}catch(_){themes=[];current='blue';persistent=false}}
 const luminance=c=>{const v=c.slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return v[0]*.2126+v[1]*.7152+v[2]*.0722};
 const contrast=(a,b)=>(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
 function apply(id,colors){tokens.forEach(k=>root.style.removeProperty('--'+k));root.style.removeProperty('color-scheme');root.dataset.theme=id;
  const c=colors||themes.find(t=>t.id===id)?.colors;if(!c)return;
  const dark=luminance(c.surface)<.2,on=contrast(c.accent,'#ffffff')>=contrast(c.accent,'#000000')?'#ffffff':'#000000';
  const values={...c,muted:c.ink,line:c.ink+'40','on-accent':on,soft:c.panel,'accent-text':contrast(c.accent,c.surface)>=4.5?c.accent:c.ink,ring:c.accent+'55',keyboard:c.panel,scroll:c.ink+'80',player:c.accent,wave:c.ink+'80','icon-filter':luminance(c.ink)>.4?'brightness(0) invert(.9)':'brightness(0) invert(.2)','on-icon':on==='#ffffff'?'1':'0','active-filter':luminance(c.ink)>.4?'brightness(0) invert(.9)':'brightness(0) invert(.2)'};
  Object.entries(values).forEach(([k,v])=>root.style.setProperty('--'+k,v));root.style.setProperty('color-scheme',dark?'dark':'light');
 }
 read();apply(current);
 const $=id=>document.getElementById(id);
 function persist(){try{localStorage.setItem(customKey,JSON.stringify(themes));localStorage.setItem(key,current);persistent=true}catch(_){persistent=false}}
 function render(){
  const list=$('theme-options');list.replaceChildren();
  for(const t of [...Object.entries(labels).map(([id,name])=>({id,name})),...themes]){
   const b=document.createElement('button');b.dataset.themeChoice=t.id;b.setAttribute('aria-pressed',String(t.id===current));
   const swatch=document.createElement('span');swatch.className='theme-swatch'+(t.colors?'':' swatch-'+t.id);swatch.setAttribute('aria-hidden','true');
   if(t.colors)swatch.style.background=`linear-gradient(90deg,${t.colors.accent} 0 33%,${t.colors.capture} 33% 66%,${t.colors.surface} 66%)`;
   const name=document.createElement('strong');name.textContent=t.name;const sub=document.createElement('small');sub.textContent=t.colors?'Eigenes Theme':'Standardtheme';b.append(swatch,name,sub);
   b.onclick=()=>{current=t.id;apply(current);persist();render()};list.append(b);
  }
  $('theme-delete-confirm').hidden=true;const own=themes.some(t=>t.id===current);$('theme-edit').disabled=!own;$('theme-delete').disabled=!own;$('theme-new').disabled=themes.length>=100;$('theme-copy').disabled=themes.length>=100;
  $('theme-status').textContent=(labels[current]||themes.find(t=>t.id===current)?.name||'Blau · Hell')+(persistent?' · Auf diesem Gerät gespeichert.':' · Nur für diese Sitzung. Browserspeicher nicht verfügbar.');
 }
 function snapshot(){const c=getComputedStyle(root);return Object.fromEntries(Object.keys(fields).map(k=>[k,c.getPropertyValue('--'+k).trim().replace(/^#([a-f0-9])([a-f0-9])([a-f0-9])$/i,'#$1$1$2$2$3$3')]))}
 function validate(){const okay=Object.values(draft.colors).every(hex)&&['surface','panel','capture'].every(k=>contrast(draft.colors.ink,draft.colors[k])>=4.5);const named=$('theme-name').value.trim().length>0;$('theme-save').disabled=!okay||!named;$('theme-validation').textContent=!named?'Bitte gib deinem Theme einen Namen.':!okay?'Text und Hintergrund brauchen mehr Kontrast. Wähle helleren Text oder dunklere Flächen – oder umgekehrt.':'Guter Textkontrast. Dein Theme kann gespeichert werden.';return okay&&named}
 function start(edit=false){editingId=edit?current:null;const own=themes.find(t=>t.id===current);draft={name:edit?own.name:((labels[current]||own?.name||'Theme')+' Kopie').slice(0,40),colors:snapshot()};$('theme-name').value=draft.name;
  const colors=$('theme-color-fields');colors.replaceChildren();for(const [k,label] of Object.entries(fields)){const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.type='color';input.value=draft.colors[k];input.setAttribute('aria-label',label+' wählen');input.oninput=()=>{draft.colors[k]=input.value;apply(current,draft.colors);validate()};wrap.append(input);colors.append(wrap)}
  $('theme-library').hidden=true;$('theme-editor').hidden=false;$('theme-editor-actions').hidden=false;$('theme-status').hidden=true;validate();$('theme-editor').closest('.settings-content').scrollTop=0;
 }
 function cancel(){if(!draft)return;draft=null;editingId=null;apply(current);$('theme-library').hidden=false;$('theme-editor').hidden=true;$('theme-editor-actions').hidden=true;$('theme-status').hidden=false;render()}
 document.addEventListener('DOMContentLoaded',()=>{
  // The first-start page shares colors, but has no theme editor.
  if(!$('theme-options'))return;
  render();$('theme-new').onclick=()=>{start();$('theme-name').value='Mein Theme';validate()};$('theme-copy').onclick=()=>start();$('theme-edit').onclick=()=>start(true);$('theme-name').oninput=()=>validate();$('theme-cancel').onclick=cancel;
  $('theme-save').onclick=()=>{if(!draft||!validate())return;const id=editingId||'custom-'+crypto.randomUUID();const entry={id,name:$('theme-name').value.trim(),colors:{...draft.colors}};themes=themes.filter(t=>t.id!==id);themes.push(entry);current=id;persist();cancel()};
  $('theme-delete').onclick=()=>{$('theme-delete-confirm').hidden=false};$('theme-delete-no').onclick=()=>{$('theme-delete-confirm').hidden=true};$('theme-delete-yes').onclick=()=>{themes=themes.filter(t=>t.id!==current);current='blue';apply(current);persist();render()};
  $('settings').addEventListener('close',cancel);$('settings').addEventListener('cancel',cancel);
  document.addEventListener('click',e=>{if(e.target.closest('[data-close="settings"],[data-settings],[data-settings-tile],#settings-overview-back'))cancel()},true);
 });
 window.addEventListener('storage',event=>{if(event.key===key||event.key===customKey){cancel();read();apply(current);if($('theme-options'))render()}});
})();
