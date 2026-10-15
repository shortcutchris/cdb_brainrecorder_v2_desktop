import json, subprocess, time
from pathlib import Path

root=Path('/tmp/cdb-static-control-055-20261015')
started=json.loads((root/'init.json').read_text())['startedAt']/1000
cli='/Users/chris/.codex/skills/playwright/scripts/playwright_cli.sh'
driver_pid=40051

def process_memory():
    raw=subprocess.check_output(['ps','-axo','pid=,ppid=,rss=,comm='],text=True)
    processes={}
    for line in raw.splitlines():
        parts=line.split(None,3)
        if len(parts)==4:
            pid,parent,rss=map(int,parts[:3]);processes[pid]={'pid':pid,'parent':parent,'rss_kib':rss,'name':Path(parts[3]).name}
    assert driver_pid in processes and processes[driver_pid]['name']=='node'
    included={driver_pid}
    while True:
        before=len(included);included.update(pid for pid,p in processes.items() if p['parent'] in included)
        if len(included)==before:break
    rows=[processes[pid] for pid in sorted(included)]
    return {'at_epoch':time.time(),'driver_pid':driver_pid,'processes':rows,'browser_rss_kib':sum(p['rss_kib'] for p in rows if p['pid']!=driver_pid)}

while True:
    os_row=process_memory()
    result=subprocess.run([cli,'-s=cdb-static-control-055','run-code','--filename','/tmp/cdb-idle-long-sample.js'],capture_output=True,text=True,timeout=45)
    try:
        assert result.returncode==0
        sample=json.loads(result.stdout.split('### Result\n',1)[1].split('\n###',1)[0])
        assert sample['page']['url']=='http://127.0.0.1:8099/'
    except Exception:
        (root/'sample-error.txt').write_text(result.stdout+'\n'+result.stderr)
        raise
    for name,row in [('samples.jsonl',sample),('process-memory.jsonl',os_row)]:
        with (root/name).open('a') as f:f.write(json.dumps(row)+'\n')
    elapsed=sample['at']/1000-started
    print(json.dumps({'elapsed_seconds':round(elapsed),'heap_used_mib':round(sample['heap']['usedSize']/1024**2,3),'dom':sample['dom']}),flush=True)
    if elapsed>=480:break
    time.sleep(min(60,max(0,started+480-time.time())))
(root/'sampler-complete.json').write_text(json.dumps({'at_epoch':time.time(),'actual_elapsed_seconds':elapsed,'completed':True},indent=2)+'\n')
