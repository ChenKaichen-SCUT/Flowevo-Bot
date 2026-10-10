from pathlib import Path
import json,hashlib,sys,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
REF='c2586290a0086b0b9da3705e9799c2d04e060b32'
sys.path[:0]=[str(ROOT/'Flowevo-Bot/src'),str(ROOT/'FlowEvo-Recovery/src')]
from flowevo_bot.common import digest,write_json

def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def save(p,x):write_json(OUT/p,x)
def lines(p,rows):(OUT/p).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
