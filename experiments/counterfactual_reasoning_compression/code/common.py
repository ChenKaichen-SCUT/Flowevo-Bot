from pathlib import Path
import sys,json,hashlib,datetime,csv
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
HIGH=ROOT/'experiments/aflow_math617_capability_probe'
LOW=ROOT/'experiments/flowevo_original_math605'
sys.path.insert(0,str(ROOT/'FlowEvo/src'))
def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def save(p,x):
 p=Path(p);p=p if p.is_absolute() else OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
 q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');q.replace(p)
def lines(p,rows):
 p=Path(p);p=p if p.is_absolute() else OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
def csvfile(p,rows,fields=None):
 p=Path(p);p=p if p.is_absolute() else OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def frozen_evaluator():
 from math_evaluation.engine import MathEvaluatorV3
 from math_evaluation.models import EvaluatorConfig
 freeze=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json')
 for p,h in freeze['source_files'].items():assert sha(ROOT/p)==h,p
 config=EvaluatorConfig(**freeze['config']);assert config.hash()==freeze['config_hash']
 return MathEvaluatorV3(config)
