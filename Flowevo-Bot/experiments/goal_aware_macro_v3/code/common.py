from pathlib import Path
import csv,json,hashlib,os
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments/goal_aware_macro_v3'
PREVIOUS=ROOT/'experiments/macro_discovery_pilot'
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def write(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def write_lines(p,rows):Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table(p,rows,fields=None):
    fields=fields or sorted({k for r in rows for k in r})
    with Path(p).open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def cap_cpu():
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
