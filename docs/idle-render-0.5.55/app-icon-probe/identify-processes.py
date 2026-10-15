import json,re,time,sys
from pathlib import Path
p=Path(sys.argv[1]);s=json.loads((p/'partial.json').read_text());r=s['runs'][-1];types={}
for pid,row in r['processes'].items():
 try:
  proc=Path('/proc')/pid
  start=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
  if start!=row['start']:continue
  raw=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  match=re.search(r'(?:^|\s)--type=([^\s]+)',raw)
  types[pid]={'start':start,'type':match.group(1) if match else 'browser-or-helper'}
 except OSError:pass
result={'captured_at_epoch':time.time(),'processes':types}
(p/'process-types.json').write_text(json.dumps(result));print(json.dumps(result))
