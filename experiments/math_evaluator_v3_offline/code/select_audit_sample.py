from common import *
import random,collections

def select(v3):
 old={r['record_id']:r for r in jl(OUT/'evidence/legacy_fixed_reproduced.jsonl')}
 groups=collections.defaultdict(list)
 for r in v3:
  o=old[r['record_id']]
  if r['branch']=='adaptive' and r['status']=='correct' and o['legacy']['final_correct'] and o['fixed']['correct'] is True:
   lv=int(r['level'][-1]);groups[(r['subject'],'1-2' if lv<=2 else '3' if lv==3 else '4-5')].append(r)
 rng=random.Random(20261010);picked=[]
 for key,rs in sorted(groups.items()):
  picked.append({'stratum':key,'record':rng.choice(sorted(rs,key=lambda x:x['task_id']))})
 return picked
if __name__=='__main__':
 p=OUT/'evaluator_v3_results.jsonl';p=p if p.exists() else OUT/'evidence/development_pass_3.jsonl'
 picked=select(jl(p));lines('evidence/stratified_unanimous_sample.jsonl',picked)
 for x in picked:
  r=x['record'];print('\nID:',r['task_id'],'STRATUM:',x['stratum']);print('Q:',r['question']);print('REF:',r['reference_raw']);print('PRED:',r['prediction_extracted'])
