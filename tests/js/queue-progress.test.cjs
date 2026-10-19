const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('studio/app.js','utf8');
function harness(){
 const nodes={};function el(){return {dataset:{},children:[],hidden:false,textContent:'',setAttribute(k,v){this[k]=v},append(...n){this.children.push(...n)},replaceChildren(){this.children=[]}}}
 const c={online:true,state:{recording:{id:null},sessions:[],jobs:[],installation:{state:'idle'},free_mb:1000,config:{min_free_mb:100,setup_complete:true}},names:{transcribing:'Transkription läuft',summarizing:'Zusammenfassung läuft',queued:'Wartet',failed:'Fehler'},busyStates:[],queueSignature:'',duration:n=>Math.floor(n)+' s',allowed:()=>true,setIcon(){},document:{createElement:el,body:{classList:{toggle(){}}}},$:id=>nodes[id]??=(Object.assign(el(),{scrollTop:0})),run:f=>f};
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
