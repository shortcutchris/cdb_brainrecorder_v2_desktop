"""Describe five-minute Pi app probes without claiming long-term stability."""
from pathlib import Path
import json,sys,subprocess,hashlib
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]))
from scripts.validate_icon_probe import validate
CANDIDATE=hashlib.sha256(subprocess.check_output(['git','show','d80f558:studio/microphone.js'],cwd=ROOT.parents[2])).hexdigest()

def describe(mode):
 p=ROOT/mode
 s=json.loads((p/'profile.json').read_text());c=json.loads((p/'cleanup.json').read_text())
 validation=validate(s,c,CANDIDATE,mode)
 roles=json.loads((p/'process-types.json').read_text())['processes']
 assert c['closed'] and not c['remaining'] and c['server_stopped'] and c['guard_stopped']
 assert s['mode']==mode and s['planned_seconds']==300
 assert s['browser']['product']=='Chrome/142.0.7444.59'
 assert not s['errors'] and all(g['idle'] for g in s['guard_samples'])
 rows=s['runs'];assert len(rows)==11
 elapsed=rows[-1]['at_epoch']-rows[0]['at_epoch'];assert 299<=elapsed<=305
 for r in rows:
  assert r['ui']['workspace']=='start-view' and not r['ui']['hidden'] and r['ui']['online'] and r['ui']['version']=='0.5.55'
 for a,b in zip(rows,rows[1:]):
  assert 29<=b['at_epoch']-a['at_epoch']<=31
  for path in ('/api/state','/api/wake/status'):
   assert b['requests'][path]>a['requests'][path]
 continuous={pid:row for pid,row in rows[0]['processes'].items() if all(pid in r['processes'] and r['processes'][pid]['start']==row['start'] for r in rows)}
 assert continuous
 process_rows=[]
 for pid,initial in continuous.items():
  role=roles.get(pid);assert role and role['start']==initial['start']
  b,a=rows[2]['processes'][pid],rows[-1]['processes'][pid]
  seconds=rows[-1]['at_epoch']-rows[2]['at_epoch']
  cpu=(a['user_ticks']+a['system_ticks']-b['user_ticks']-b['system_ticks'])/s['clock_ticks']
  assert cpu>=0
  process_rows.append({'pid':int(pid),'start':initial['start'],'type':role['type'],
   'rss_60s_mib':b['rss_kib']/1024,'rss_300s_mib':a['rss_kib']/1024,'rss_delta_mib':(a['rss_kib']-b['rss_kib'])/1024,
   'cpu_percent_one_core_60_to_300':round(cpu/seconds*100,3)})
 snapshots=[]
 for r in rows:
  snapshots.append({'elapsed_seconds':round(r['at_epoch']-rows[0]['at_epoch'],3),'dom':r['dom'],'heap':r['heap'],
    'rss_continuous_mib':sum(r['processes'][pid]['rss_kib'] for pid in continuous)/1024,
    'polls':{path:r['requests'].get(path,0) for path in ('/api/state','/api/wake/status','/assets/play.svg')}})
 sets=[set((pid, v['start']) for pid,v in r['processes'].items()) for r in rows]
 return {'mode':mode,'browser':s['browser']['product'],'start_epoch':s['started_at_epoch'],'end_epoch':c['at_epoch'],
   'source_hashes':s['source_hashes'],'fixture_counts':s['fixture_counts'],'startup_flags':s['startup_flags'],
   'seconds':elapsed,'snapshots':snapshots,'continuous_processes':process_rows,
   'process_group_unchanged':all(group==sets[0] for group in sets),
   'requests':s['requests'],'validation':validation,'auxiliary_statuses':s['auxiliary_statuses'],'closed':True,'overall_goal_complete':False}

if __name__=='__main__':
 rows=[describe(mode) for mode in ('original','guarded')]
 for key in ['app.js','device-status.js','touch.js','microphone.js']:
  assert rows[0]['source_hashes'][key]==rows[1]['source_hashes'][key]
 assert rows[0]['source_hashes']['served_microphone.js']!=rows[1]['source_hashes']['served_microphone.js']
 assert rows[0]['startup_flags']==rows[1]['startup_flags']
 print(json.dumps(rows,indent=2))
