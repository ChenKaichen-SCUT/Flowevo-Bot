from pathlib import Path
import sys,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
REF='f0afc2c8af5be165b36c05a168b2f320d08de3c1'
sys.path[:0]=[str(ROOT/'FlowEvo/src'),str(ROOT/'Flowevo-Bot/src'),str(ROOT/'FlowEvo-Recovery/src')]
def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 p=Path(p);p=p if p.is_absolute() else OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def lines(p,rs):
 p=Path(p);p=p if p.is_absolute() else OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rs))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
