from pathlib import Path
import sys,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1];OLD=ROOT/'experiments/math500_scoring_and_budget_v2'
REF='cf1b32bbd7d0fc3ff98fcb8ba4bdd63bbd2367f3'
sys.path[:0]=[str(ROOT/'FlowEvo/src'),str(ROOT/'Flowevo-Bot/src'),str(ROOT/'FlowEvo-Recovery/src')]
def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):(OUT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def lines(p,rs):(OUT/p).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rs))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
