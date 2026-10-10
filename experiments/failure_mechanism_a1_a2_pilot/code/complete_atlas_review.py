from common import *
from build_atlas import export

def main():
 if (OUT/'evidence/atlas_final_review.json').exists():print('Final historical review reused');return
 assert not list((OUT/'raw').glob('*.json'))
 rows=jl(OUT/'historical_records.jsonl');grades={}
 for name in ('train_branches.scored.jsonl','confirmation_all.scored.jsonl'):
  for r in jl(ROOT/'experiments/failure_recovery_pilot/evidence'/name):grades[r['state']['call_id']]=r['score']
 notes=[]
 for r in rows:
  r['labels']=list(dict.fromkeys(r['labels']))
  if r['cohort']=='earlier_recovery':
   cid=r['record_id'].split(':')[-1]
   # Ledger job IDs differ by stage. Map actual response ID using saved raw calls.
   cid=None
   for old in jl(ROOT/'experiments/failure_recovery_pilot/api_calls.jsonl'):
    if old['task_id']!=r['task_id']:continue
    raw=read(ROOT/'experiments/failure_recovery_pilot'/old['raw_path'])
    if raw['response'].get('id')==r['response_id']:cid=old['call_id'];break
   if cid in grades:
    g=grades[cid];r['offline_status']='correct' if g['correct'] is True else 'incomplete' if r['completion']['retry_required'] else 'incorrect' if g['correct'] is False else 'unknown';r['offline_grade_source']='historical_training_or_confirmation_score_reused'
  if r['task_id']=='math_train_prealgebra_76' and not r['completion']['retry_required']:
   r['labels']=['F4'];r['offline_status']='incorrect';r['label_basis']={'F4':'Introduces an exact-payment constraint absent from the usual can-afford interpretation: 3*1000+8*25+8*10=3280 >=3275; 7 dimes insufficient even with all bills/quarters. Ten dimes is only needed to pay exactly with seven quarters. No arithmetic error; interpretation/constraint drift. Wording could invite exact-payment ambiguity.'}
   notes.append({'record_id':r['record_id'],'type':'F4','proof':r['label_basis']['F4'],'visible_evidence':r['final_text'],'ambiguity_sensitivity':'If exact payment is imposed externally, 10 is right. This condition is not stated; reference permits change.'})
  if r['task_id']=='math_test_prealgebra_551' and r['offline_status']=='unconfirmed' and not r['completion']['retry_required']:
   r['labels']=['F7'];r['offline_status']='correct';r['offline_grade_source']='new_posthoc_exact_area_audit';r['label_basis']={'F7':'Union of three side-6 squares: 3*36-2*9=90. Last two only meet at a point; no triple area. Saved fixed scorer could not parse reference multiline square units. No old grading rerun.'}
   notes.append({'record_id':r['record_id'],'type':'F7','proof':r['label_basis']['F7']})
  if r['offline_status']=='correct' and 'F8' in r['labels']:r['labels'].remove('F8');r['label_basis'].pop('F8',None)
  r['primary']=next((c for c in ['F5','F3','F4','F6','F7','F1','F2','F8'] if c in r['labels']),None);r['secondary']=[c for c in r['labels'] if c!=r['primary']]
 # export normalizes known fixed->V3 corrections; deduplicate its existing F7 first.
 for r in rows:
  if 'F7' in r['labels'] and r['cohort']=='batch2' and r['task_id']!='math_test_prealgebra_551':r['labels'].remove('F7')
 export(rows)
 save('evidence/atlas_final_review.json',{'at':now(),'new_api_calls':0,'reused_additional_grade_records':len(grades),'new_manual_reviews':notes,'reviewer':'assistant mathematical audit, no independent human adjudicator','prior_event_extraction_reused':True})
 # Refresh a pre-API draft freeze only; no generated answers exist yet.
 p=OUT/'evidence/pre_api_freeze.json';p.rename(OUT/'evidence/pre_api_freeze_before_atlas_grade_reconciliation.json')
 import subprocess
 subprocess.run([sys.executable,str(OUT/'code/preflight.py')],check=True)
if __name__=='__main__':main()
