from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments/macro_discovery_pilot'
OLD=ROOT/'experiments/math500_goldfree_20261009'
V2=ROOT/'experiments/flowevo_bot_v2_math500'

def read(p):return json.loads(Path(p).read_text())
def write(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def write_lines(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table(p,rows,fields=None):
    fields=fields or sorted({k for r in rows for k in r})
    with Path(p).open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def cap_cpu():
    import os
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
