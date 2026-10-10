from pathlib import Path
import sys,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
REF='96dd474cdcb0116de62775ce31b06bb0ee97e3d0'
sys.path.insert(0,str(ROOT/'FlowEvo/src'))
def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x)for x in Path(p).read_text().splitlines()if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):
 p=Path(p);p=p if p.is_absolute()else OUT/p;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def lines(p,rows):
 p=Path(p);p=p if p.is_absolute()else OUT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n'for x in rows))
def norm(text):
 import re,unicodedata
 return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip()
