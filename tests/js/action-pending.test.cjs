const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function harness(){const errors=[],c={notice:message=>errors.push(message)};vm.createContext(c);const s=fs.readFileSync('studio/app.js','utf8');vm.runInContext(s.slice(s.indexOf('function run('),s.indexOf('function draftKey(')),c);return {c,errors}}
test('a repeated touch cannot submit an in-flight action twice and failure releases it',async()=>{
 const {c,errors}=harness();let fail,calls=0;const button={tagName:'BUTTON',setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]}};
 const action=c.run(()=>{calls++;return new Promise((_,reject)=>fail=reject)});
 const pending=action({currentTarget:button});await action({currentTarget:button});assert.equal(calls,1);assert.equal(button['aria-busy'],'true');
 fail(Error('Speichern fehlgeschlagen'));await pending;assert.equal(button['aria-busy'],undefined);assert.deepEqual(errors,['Speichern fehlgeschlagen']);
 const retry=action();assert.equal(calls,2);fail(Error('retry'));await retry;
});
test('search input retains its latest event while an older search is pending',async()=>{
 const {c}=harness(),resolvers=[],values=[];const action=c.run(event=>{values.push(event.currentTarget.value);return new Promise(resolve=>resolvers.push(resolve))});
 const a=action({currentTarget:{tagName:'INPUT',value:'a'}}),b=action({currentTarget:{tagName:'INPUT',value:'ab'}});
 assert.deepEqual(values,['a','ab']);resolvers.forEach(r=>r());await Promise.all([a,b]);
});

test('processing keeps its original meeting and prompt while draft saving is pending',async()=>{
 const s=fs.readFileSync('studio/app.js','utf8');let done;const calls=[],c={selected:7,models:new Map([[7,{id:7}]]),$:id=>({value:'original',close(){}}),flush:()=>new Promise(r=>done=r),api:async(path,body)=>calls.push({path,...body}),poll:async()=>{}};
 vm.createContext(c);vm.runInContext(s.slice(s.indexOf('async function processMeeting('),s.indexOf("$('process').onclick=")),c);
 const pending=c.processMeeting();c.selected=9;c.$=()=>({value:'other',close(){}});done();await pending;
 assert.equal(calls[0].path,'/api/sessions/7/process');assert.equal(calls[0].prompt,'original');
});

test('final saving includes an earlier meeting and fails rather than discarding it',async()=>{
 const s=fs.readFileSync('studio/app.js','utf8'),seen=[],c={models:new Map([[1,{id:1}],[2,{id:2}]]),flush:async m=>{seen.push(m.id);if(m.id===2)throw Error('earlier draft cannot be saved')}};
 vm.createContext(c);vm.runInContext(s.slice(s.indexOf('async function flushAllDrafts('),s.indexOf('function changed(')),c);
 await assert.rejects(c.flushAllDrafts(),/earlier draft/);assert.deepEqual(seen,[1,2]);
});
