const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('select refresh reaches a fixed point instead of self-triggering its MutationObserver forever',()=>{
 const s=fs.readFileSync('studio/touch.js','utf8'),fn=s.slice(s.indexOf(' function refreshSelects()'),s.indexOf(" document.querySelectorAll('select')"));
 let disabled=false,writes=0,mutations=0;const button={firstChild:{textContent:'Microphone'},get disabled(){return disabled},set disabled(value){disabled=value;writes++;mutations++}};
 const source={disabled:true,selectedOptions:[{textContent:'Microphone'}]},c={selectButtons:new Map([[source,button]])};vm.createContext(c);vm.runInContext(fn,c);
 c.refreshSelects();assert.equal(writes,1);while(mutations&&writes<20){mutations=0;c.refreshSelects()}assert.equal(writes,1,'unchanged reflected attributes must not schedule another frame');
 source.disabled=false;c.refreshSelects();assert.equal(writes,2);c.refreshSelects();assert.equal(writes,2);
});

test('pager labels update only on changes and retain hidden-page semantics',()=>{
 const s=fs.readFileSync('studio/touch.js','utf8'),fn=s.slice(s.indexOf(' function refresh(){'),s.indexOf(' const selectButtons='));let label='Audio',writes=0,stored='';
 const bar={hidden:false,getAttribute:()=>stored,setAttribute(k,v){writes++;stored=v}},element={getAttribute:()=>label};
 const c={pagers:new Map([[element,{bar,name:'fallback'}]]),isVisible:()=>false,refreshSelects(){}};vm.createContext(c);vm.runInContext(fn,c);
 for(let i=0;i<100;i++)c.refresh();assert.equal(writes,1);assert.equal(stored,'Audio Seiten');assert.equal(bar.hidden,true);
 label='Bibliothek';c.refresh();assert.equal(writes,2);assert.equal(stored,'Bibliothek Seiten');
});

test('queue paging accounts for its header and keeps the selected page while progress text changes',()=>{
 const s=fs.readFileSync('studio/touch.js','utf8'),fn=s.slice(s.indexOf(' function refresh(){'),s.indexOf(' const selectButtons='));
 const rows=Array.from({length:3},(_,i)=>({dataset:{queueKey:'job-'+i},textContent:'Job '+i+' · 00:01',hidden:false,classList:{contains:()=>true},getBoundingClientRect:()=>({height:112})}));
 const el={id:'queue-panel',children:rows,clientHeight:400,scrollTop:0,getAttribute:()=> 'Queue',querySelector:()=>({getBoundingClientRect:()=>({height:30})})};
 const bar={hidden:false,getAttribute:()=> 'Queue Seiten',setAttribute(){}},p={bar,info:{},numbers:{},name:'Queue',signature:''};
 let select;const c={pagers:new Map([[el,p]]),isVisible:()=>true,refreshSelects(){},getComputedStyle:()=>({marginBottom:'12px'}),drawPageNumbers(n,count,page,callback){assert.equal(count,2);select=callback},schedule(){}};
 vm.createContext(c);vm.runInContext(fn,c);c.refresh();assert.equal(p.info.textContent,'Seite 1 von 2');select(1);c.refresh();assert.equal(p.info.textContent,'Seite 2 von 2');
 rows[0].textContent='Job 0 · 00:02';c.refresh();assert.equal(p.page,1);assert.equal(rows[2].hidden,false);assert.equal(rows[0].hidden,true);
});
