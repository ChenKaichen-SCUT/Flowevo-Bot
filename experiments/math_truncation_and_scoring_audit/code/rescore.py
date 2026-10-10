from prepare import ROOT,OUT,read
import sys,json,concurrent.futures as cf,csv
sys.path.insert(0,str(ROOT/'FlowEvo-Recovery/src'))
from flowevo_recovery.math_scoring_v2 import grade
from flowevo_bot.common import write_json
if __name__=='__main__':
 rows=read(OUT/'evidence/baseline_500.json')
 with cf.ProcessPoolExecutor(max_workers=12) as ex:results=list(ex.map(grade,rows))
 write_json(OUT/'evidence/rescored_500_detailed.json',results)
 fields=['task_id','original_correct','correct','status','answer']
 with (OUT/'math500_rescored.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r.get(k) for k in fields} for r in results)
 from collections import Counter
 print(Counter((r['correct'],r['status']) for r in results))
 for b,r in zip(rows,results):
  if r['correct'] is None or (b['original_correct'] and not r['correct']):print(json.dumps({'task_id':b['task_id'],'q':b['question'],'old':b['original_answer'],'gold':b['gold_answer'],'new':r},ensure_ascii=False))
