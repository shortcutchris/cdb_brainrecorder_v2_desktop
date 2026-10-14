const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('select refresh reaches a fixed point instead of self-triggering its MutationObserver forever',()=>{
 const s=fs.readFileSync('studio/touch.js','utf8'),fn=s.slice(s.indexOf(' function refreshSelects()'),s.indexOf(" document.querySelectorAll('select')"));
 let disabled=false,writes=0,mutations=0;const button={firstChild:{textContent:'Microphone'},get disabled(){return disabled},set disabled(value){disabled=value;writes++;mutations++}};
 const source={disabled:true,selectedOptions:[{textContent:'Microphone'}]},c={selectButtons:new Map([[source,button]])};vm.createContext(c);vm.runInContext(fn,c);
 c.refreshSelects();assert.equal(writes,1);while(mutations&&writes<20){mutations=0;c.refreshSelects()}assert.equal(writes,1,'unchanged reflected attributes must not schedule another frame');
 source.disabled=false;c.refreshSelects();assert.equal(writes,2);c.refreshSelects();assert.equal(writes,2);
});
