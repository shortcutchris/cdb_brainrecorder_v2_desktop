from pathlib import Path
import json,struct,bisect,collections,subprocess
root=Path('/Users/chris/.local/share/cdb-stability-evidence-20261015/055-native-perf');data=(root/'chromium.debug').read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',data);shoff,shsize,shnum=h[6],h[11],h[12];sections=[struct.unpack_from('<IIQQQQIIQQ',data,shoff+i*shsize) for i in range(shnum)];symbols=[]
for s in sections:
 if s[1]!=2:continue
 strings=sections[s[6]];text=data[strings[4]:strings[4]+strings[5]]
 for off in range(s[4],s[4]+s[5],s[9]):
  name,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',data,off)
  if info&15!=2 or not size:continue
  end=text.find(b'\0',name);symbols.append((value,size,text[name:end].decode(errors='replace')))
symbols.sort();keys=[s[0] for s in symbols];maps=[]
for line in (root/'maps-before.txt').read_text().splitlines():
 p=line.split(None,5);a,b=(int(x,16) for x in p[0].split('-'));maps.append((a,b,int(p[2],16),p[5] if len(p)>5 else '[anonymous]'))
def resolve(address):
 for a,b,offset,path in maps:
  if not a<=address<b:continue
  if path!='/usr/lib/chromium/chromium':return path
  fileoffset=address-a+offset
  if not 0x256a000<=fileoffset<0xef97b60:return '[Chromium non-code]'
  vma=fileoffset+0x10000;i=bisect.bisect_right(keys,vma)-1
  if i>=0 and symbols[i][0]<=vma<symbols[i][0]+symbols[i][1]:return symbols[i][2]
  return '[Chromium unresolved '+hex(vma)+']'
 return '[unmapped]'
s=json.loads((root/'sample.json').read_text());leaf=collections.Counter();inclusive=collections.Counter()
for x in s['samples']:
 leaf[resolve(x['ip'])]+=1
 for name in set(resolve(a) for a in x['chain'] if a<0xfffffffffffff000):inclusive[name]+=1
names=list(dict.fromkeys([n for n,c in leaf.most_common(25)]+[n for n,c in inclusive.most_common(25)]));p=subprocess.run(['c++filt'],input='\n'.join(names)+'\n',capture_output=True,text=True,check=True);decoded=dict(zip(names,p.stdout.splitlines()));out={'symbol_count':len(symbols),'build_id':'7914866d038784fc765399fac27c1c34baa6507f','samples':len(s['samples']),'leaf':[{'function':decoded.get(n,n),'samples':c} for n,c in leaf.most_common(25)],'inclusive':[{'function':decoded.get(n,n),'samples':c} for n,c in inclusive.most_common(25)],'method':'Matched GNU build-id; ELF executable LOAD file offset to VMA (+0x10000); function-range lookup in SHT_SYMTAB, per-sample unique inclusive functions'}
(root/'symbolized-summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
