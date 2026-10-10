from pathlib import Path
import json,hashlib,csv,sys,datetime,os
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments/failure_recovery_pilot'
BOT=ROOT/'Flowevo-Bot'
EXTERNAL=Path('/mnt/Space1/Verify-Then-Commit')
sys.path[:0]=[str(ROOT/'FlowEvo-Recovery/src'),str(BOT/'src')]
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jl(p,xs):Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in xs))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def csvwrite(p,rows):
 keys=list(dict.fromkeys(k for x in rows for k in x))
 with Path(p).open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for x in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in x.items()})
def cap():
 if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
