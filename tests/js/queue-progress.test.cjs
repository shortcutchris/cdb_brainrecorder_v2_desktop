const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('studio/app.js','utf8');
function harness(){
 const nodes={};function el(){return {dataset:{},children:[],hidden:false,textContent:'',setAttribute(k,v){this[k]=v},append(...n){this.children.push(...n)},replaceChildren(){this.children=[]}}}
 const c={online:true,state:{recording:{id:null},sessions:[],jobs:[],installation:{state:'idle'},free_mb:1000,config:{min_free_mb:100,setup_complete:true}},names:{transcribing:'Transkription läuft',summarizing:'Zusammenfassung läuft',queued:'Wartet',failed:'Fehler'},busyStates:[],queueSignature:'',duration:n=>Math.floor(n)+' s',allowed:()=>true,setIcon(){},document:{createElement:el,body:{classList:{toggle(){}}}},$:id=>nodes[id]??=(Object.assign(el(),{scrollTop:0})),icon:()=>el(),run:f=>f};
 vm.createContext(c);vm.runInContext(source.slice(source.indexOf('function queueJobs()'),source.indexOf('async function poll(){')),c);return {c,nodes};
}
test('file sizes distinguish unknown, zero and decimal megabytes',()=>{const {c}=harness();assert.equal(c.queueFileSize(null),'–');assert.equal(c.queueFileSize(0),'0 B');assert.equal(c.queueFileSize(1_952_078),'2 MB');assert.equal(c.queueFileSize(-2),'–')});
test('processing reports real phases and section detail without invented percentages',()=>{const {c}=harness();const job={state:'transcribing',updated:Date.now()/1000-10};assert.match(c.queueProgress(job).label,/Schritt 1 von 2/);job.state='summarizing';job.processing_detail='Abschnitt 2/5';assert.equal(c.queueProgress(job).detail,'Abschnitt 2/5');assert.match(c.queueProgress(job).label,/Schritt 2 von 2/);job.state='queued';assert.equal(c.queueProgress(job).active,false);c.online=false;job.state='summarizing';assert.equal(c.queueProgress(job).active,false);assert.match(c.queueProgress(job).label,/nicht aktuell/)});
test('live updates preserve existing row, button focus, pagination key and scroll',()=>{
 const {c,nodes}=harness();c.state.sessions=[{local_job_id:'a',title:'Meeting'}];c.state.jobs=[{id:'a',state:'summarizing',updated:Date.now()/1000,processing_detail:'Abschnitt 1/3',audio_file_bytes:1000}];c.renderQueue();
 const panel=nodes['queue-panel'],row=panel.children[1],button=row.children[4],pageKey=row.dataset.queueKey;panel.scrollTop=70;
 c.state.jobs[0].processing_detail='Abschnitt 2/3';c.state.jobs[0].audio_file_bytes=2000;c.renderQueue();
 assert.equal(panel.children[1],row);assert.equal(row.children[4],button);assert.equal(panel.scrollTop,70);assert.equal(row.dataset.queueKey,pageKey);assert.equal(row.children[1].textContent,'2 kB');assert.equal(row.children[3].children[2].textContent,'Abschnitt 2/3');assert.equal(row.children[3].children[1].value,undefined);
});

test('failed rows expose a named delete action while running jobs do not',()=>{
 const {c,nodes}=harness();c.state.sessions=[{id:7,local_job_id:'a',title:'Leerer Versuch'}];c.state.jobs=[{id:'a',state:'failed',updated:0,audio_file_bytes:0}];c.renderQueue();
 const actions=nodes['queue-panel'].children[1].children[4];assert.equal(actions.children.length,2);assert.match(actions.children[1]['aria-label'],/Leerer Versuch.*löschen/);assert.equal(actions.children[1].disabled,false);
 c.state.recording.id='recording';c.renderQueue();assert.equal(nodes['queue-panel'].children[1].children[4].children[1].disabled,true);
});
test('deleting from queue confirms the target row and preserves a different selected meeting',async()=>{
 const {c}=harness(),calls=[];c.models=new Map([[7,{}],[99,{}]]);c.selected=99;c.flush=async()=>{};c.poll=async()=>calls.push('poll');c.confirmAction=async()=>false;c.api=async(path)=>calls.push(path);
 assert.equal(await c.deleteMeeting(7,'Leerer Versuch'),false);assert.equal(calls.length,0);
 c.confirmAction=async({message})=>{assert.match(message,/Leerer Versuch/);return true};assert.equal(await c.deleteMeeting(7,'Leerer Versuch'),true);
 assert.equal(calls[0],'/api/sessions/7/delete');assert.equal(c.selected,99);assert.equal(c.models.has(99),true);assert.equal(c.models.has(7),false);
});
