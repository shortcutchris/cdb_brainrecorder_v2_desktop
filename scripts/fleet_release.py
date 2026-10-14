#!/usr/bin/env python3
"""Build an operator-reviewed, signed, code-only ARM64 release (never uploads)."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fleet.releases import package,canonical

p=argparse.ArgumentParser();p.add_argument('--key',required=True);p.add_argument('--version',required=True);p.add_argument('--from-version',action='append',required=True);p.add_argument('--sequence',type=int,required=True);p.add_argument('--runtime',required=True);p.add_argument('--out',required=True)
a=p.parse_args()
bundle=package(Path(__file__).resolve().parents[1],a.key,a.version,a.from_version,a.sequence,a.runtime,time.time()+30*86400)
id=hashlib.sha256(canonical(bundle['manifest'])).hexdigest()
folder=Path(a.out);folder.mkdir(parents=True,exist_ok=True);(folder/(id+'.json')).write_text(json.dumps(bundle));print(id)
