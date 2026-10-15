"""Compare completed local diagnostic windows, never production acceptance."""
import hashlib,json,statistics
from pathlib import Path

base=Path(__file__).resolve().parent
experiments=[
('normal-ui',base.parent/'natural-idle-mac',1800),
('render-frozen',base/'render-frozen',1800),
('static-page',base/'static-page',480),
('render-frozen-timeouts-disabled',base/'timeouts-disabled',600),
]
report={'scope':'Local Mac Chrome diagnostic comparisons; not Pi acceptance or production changes','os_warmup_excluded_before_seconds':120,'overall_goal_complete':False,'runs':[],
'limits':['Windows have different durations and start times; do not compare absolute RSS as a controlled effect size. OS comparisons exclude the first two minutes for every run because old page objects are still present in an early sample.',
'The static page had explicit GC before its window; the app windows did not.',
'The static and timeout controls overlap part of the render-frozen window on the same Mac.',
'Playwright and routing can influence results; driver RSS is excluded from browser RSS.',
'RSS sums may count shared pages more than once; short samples cannot exclude all leaks.',
'No rendering and no timeouts are diagnostic controls, not usable product fixes.',
'Local Chrome 155 and synthetic preview are different from the Pi Chromium 142 and real profile.']}
for mode,root,planned in experiments:
    init=json.loads((root/'init.json').read_text());start=init['startedAt']/1000
    samples=[json.loads(x) for x in (root/'samples.jsonl').read_text().splitlines()]
    os_rows=[json.loads(x) for x in (root/'process-memory.jsonl').read_text().splitlines()]
    assert samples[-1]['at']/1000-start>=planned, 'Observation not complete: '+mode
    assert (root/'cleanup.json').exists(), 'Browser cleanup not recorded: '+mode
    assert all(b['at']>a['at'] for a,b in zip(samples,samples[1:]))
    assert max((b['at']-a['at'])/1000 for a,b in zip(samples,samples[1:]))<90
    observed_os_rows=[row for row in os_rows if row['at_epoch']-start>=120]
    assert len(observed_os_rows)>=2
    a,b=observed_os_rows[0],observed_os_rows[-1]
    old={p['pid']:p for p in a['processes']}
    assert set(old)=={p['pid'] for p in b['processes']}
    deltas=[{'pid':p['pid'],'role':p['name'],'driver_excluded':p['pid']==b['driver_pid'],'first_rss_mib':round(old[p['pid']]['rss_kib']/1024,3),'last_rss_mib':round(p['rss_kib']/1024,3),'delta_mib':round((p['rss_kib']-old[p['pid']]['rss_kib'])/1024,3)} for p in b['processes']]
    run={'mode':mode,'declared_scope':init['scope'],'planned_seconds':planned,'sampled_seconds_from_ready':round(samples[-1]['at']/1000-start,3),'sample_count':len(samples),'browser_versions':sorted({s['browser']['product'] for s in samples}),
'js_heap_used_mib':{'min':round(min(s['heap']['usedSize'] for s in samples)/1024**2,3),'max':round(max(s['heap']['usedSize'] for s in samples)/1024**2,3),'first':round(samples[0]['heap']['usedSize']/1024**2,3),'last':round(samples[-1]['heap']['usedSize']/1024**2,3)},
'dom_ranges':{key:[min(s['dom'][key] for s in samples),max(s['dom'][key] for s in samples)] for key in ('documents','nodes','jsEventListeners')},
'attached_elements_range':[min(s['page']['attachedNodes'] for s in samples),max(s['page']['attachedNodes'] for s in samples)],
'os_interval_seconds_from_ready':[round(a['at_epoch']-start,3),round(b['at_epoch']-start,3)],'browser_rss_mib':[round(a['browser_rss_kib']/1024,3),round(b['browser_rss_kib']/1024,3)],'processes':deltas,
'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('init.json','samples.jsonl','process-memory.jsonl','cleanup.json')}}
    for key in ('frozenRenderCalls','disabledTimeoutCalls'):
        if key in samples[0]['page']:run[key]=[samples[0]['page'][key],samples[-1]['page'][key]]
    report['runs'].append(run)
print(json.dumps(report,indent=2))
