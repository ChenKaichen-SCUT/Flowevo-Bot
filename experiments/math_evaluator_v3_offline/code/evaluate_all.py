from common import *
import time,collections,argparse
from math_evaluation import MathEvaluatorV3,EvaluatorConfig
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default='evaluator_v3_results.jsonl');a=p.parse_args()
 records=jl(OUT/'evidence/input_records.jsonl');start=time.monotonic()
 cfg=EvaluatorConfig(workers=12);ev=MathEvaluatorV3(cfg);rs=ev.evaluate_batch(records)
 lines(a.output,rs)
 result={'wall_seconds':time.monotonic()-start,'worker_seconds':sum(r['elapsed_seconds'] for r in rs),'workers':12,'records':len(rs),'config':cfg.to_dict(),'config_hash':cfg.hash(),'counts':{b:dict(collections.Counter(r['status'] for r in rs if r['branch']==b)) for b in ['base','adaptive']},'new_llm_calls':0}
 save('evidence/'+Path(a.output).stem+'_timing.json',result);print(json.dumps(result,indent=2))
