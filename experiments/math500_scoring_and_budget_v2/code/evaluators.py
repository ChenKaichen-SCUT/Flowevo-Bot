"""Offline adapters to the unchanged, previously published evaluators."""
import time
from common import ROOT,OUT,read,save,sha
from flowevo_bot.evaluator import extract_answer
from flowevo_bot.experiment_grader import grade_one
from flowevo_recovery.math_scoring_v2 import grade

class LegacyEvaluator:
 @staticmethod
 def score(item):
  start=time.perf_counter();answer=extract_answer(item['solution'])
  r=grade_one((item['task_id'],answer,item['gold_answer'],item.get('truncated',False)))
  return {'task_id':item['task_id'],'answer':answer,'correct':r['final_correct'],'status':r['feedback'],'detail':r,'local_seconds':time.perf_counter()-start}
class FixedEvaluator:
 @staticmethod
 def score(item):
  start=time.perf_counter();r=grade(item)
  return {**r,'local_seconds':time.perf_counter()-start}
def both(item):return {'task_id':item['task_id'],'legacy':LegacyEvaluator.score(item),'fixed':FixedEvaluator.score(item)}

def regression():
 import concurrent.futures as cf
 rows=read(ROOT/'experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json');start=time.perf_counter()
 with cf.ProcessPoolExecutor(max_workers=12) as p:rs=list(p.map(both,rows))
 nine={r['task_id'] for r in rows if not r['original_correct'] and not r['truncated']}
 counts={'legacy_correct':sum(r['legacy']['correct'] is True for r in rs),'fixed_correct':sum(r['fixed']['correct'] is True for r in rs),'nine_fixed':sum(r['fixed']['correct'] is True for r in rs if r['task_id'] in nine),'original_true_lost':sum(b['original_correct'] and r['fixed']['correct'] is not True for b,r in zip(rows,rs))}
 assert counts=={'legacy_correct':464,'fixed_correct':473,'nine_fixed':9,'original_true_lost':0},counts
 save('evaluator_regression.json',{'counts':counts,'elapsed_seconds':time.perf_counter()-start,'workers':12,'new_api_calls':0,'rows':rs})
 files=['Flowevo-Bot/src/flowevo_bot/evaluator.py','Flowevo-Bot/src/flowevo_bot/experiment_grader.py','Flowevo-Bot/src/flowevo_bot/v2/evaluator.py','FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py']
 save('evidence/evaluators_frozen.json',{'files':[{'path':f,'sha256':sha(ROOT/f)} for f in files],'policy':'No modifications on new test correctness; uncertain results remain unknown and disagreements audited separately.'})
 print(counts,flush=True)
if __name__=='__main__':regression()
