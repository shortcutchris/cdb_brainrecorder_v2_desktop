'use strict';
// Load before rendering to avoid a bright flash in the kiosk. This preference
// belongs to this browser profile; it never changes audio or model settings.
(()=>{
 const key='cdb-studio-theme', labels={blue:'Blau · Hell',petrol:'Petrol · Hell',midnight:'Mitternacht',graphite:'Graphit'};
 let current='blue',persistent=true;
 try{const saved=localStorage.getItem(key);if(Object.hasOwn(labels,saved))current=saved}catch(_){persistent=false}
 document.documentElement.dataset.theme=current;
 function render(){
  document.querySelectorAll('[data-theme-choice]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.themeChoice===current)));
  const status=document.getElementById('theme-status');
  if(status)status.textContent=labels[current]+(persistent?' · Auf diesem Gerät gespeichert.':' · Nur für diese Sitzung. Browserspeicher nicht verfügbar.');
 }
 document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('[data-theme-choice]').forEach(button=>button.addEventListener('click',()=>{
   current=button.dataset.themeChoice;document.documentElement.dataset.theme=current;
   try{localStorage.setItem(key,current);persistent=true}catch(_){persistent=false}
   render();
  }));render();
 });
 window.addEventListener('storage',event=>{if(event.key===key){current=Object.hasOwn(labels,event.newValue)?event.newValue:'blue';document.documentElement.dataset.theme=current;render()}});
})();
