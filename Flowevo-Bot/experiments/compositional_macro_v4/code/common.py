"""V4 artifact helpers; deliberately no network client or secret access."""
from pathlib import Path
import csv, hashlib, json, os, datetime
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'experiments/compositional_macro_v4'
V3 = ROOT / 'experiments/goal_aware_macro_v3'
RMMD = ROOT / 'experiments/macro_discovery_pilot'
def read(p): return json.loads(Path(p).read_text())
def lines(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def write(p, x):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n')
def write_lines(p, xs): Path(p).write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in xs))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def table(p, rows, fields=None):
    fields=fields or list(dict.fromkeys(k for row in rows for k in row))
    with Path(p).open('w') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for row in rows: w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})
def cap_cpu():
    if hasattr(os,'sched_getaffinity'): os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
