"""Reuse extracted events; reconcile saved grades and explicitly reviewed evidence."""
from common import *
from build_atlas import export
import re

def main():
 if (OUT/'evidence/atlas_reconciliation.json').exists():print('Reconciled atlas reused');return
 results=jl(OUT/'historical_records.jsonl');proofs=read(ROOT/'experiments/math_truncation_and_scoring_audit/evidence/manual_math_review.json')
 grades={a['response_id']:a['grade'] for r in jl(ROOT/'experiments/math_truncation_and_scoring_audit/truncation_task_results.jsonl') for a in r['all_attempts']}
 manual=[]
 for r in results:
  if r['response_id'] in grades:
   g=grades[r['response_id']];r['offline_status']='correct' if g['correct'] else 'incomplete' if r['completion']['retry_required'] else 'unconfirmed';r['offline_grade_source']='historical_truncation_all_attempts_grade_reused'
  if 'F2' in r['labels'] and r['budget']!=16384:r['labels'].remove('F2');r['label_basis'].pop('F2',None)
  if r['task_id'] in {'math_test_counting_probability_42','math_test_intermediate_algebra_364'} and r['repeat_proxy'] and r['finish_reason']=='length':
   r['labels'].append('F2');r['label_basis']['F2']='New assistant review of exposed repeated derivation and verification, unchanged candidate, end-of-budget without final content; not just automatic check-word counts.'
   manual.append({'record_id':r['record_id'],'type':'F2','evidence':r['reasoning'][-2000:],'offset':max(0,len(r['reasoning'])-2000)})
  if r['task_id']=='math_test_intermediate_algebra_494' and r['budget']==16384:
   m=re.search(r'4[ ,]?022[ ,]?030|4022030',r['reasoning'])
   if m:
    r['labels'].append('F1');r['label_basis']['F1']='Reused exact audit proves 4022030; candidate visible before truncated final request. New text-position lookup, not a model generation or score rerun.'
    ev={'start':m.start(),'end':m.end(),'text':m[0],'context':r['reasoning'][max(0,m.start()-150):m.end()+220],'source':'prior_mathematical_audit_candidate','offline_reference_match':'prior_exact_proof','observability':'exposed_reasoning_text'}
    r['offline_matching_candidates'].append(ev);manual.append({'record_id':r['record_id'],'type':'F1','evidence':ev})
  if r['goal_check'].get('high_confidence_mismatch') and r['task_id'] in {'math_test_geometry_340','math_test_prealgebra_573'}:
   r['goal_check']['development_false_positive']=True;r['goal_check']['review']='Unit requirement absent in public spec: valid optional unit suffix must not cause intervention. Fixed before pilot freeze.'
   manual.append({'record_id':r['record_id'],'type':'A2_development_false_positive','evidence':r['final_text'][-250:]})
  if r['offline_status']=='correct' and 'F8' in r['labels']:r['labels'].remove('F8');r['label_basis'].pop('F8',None)
  if not r['labels'] and r['completion']['retry_required']:r['labels']=['F8'];r['label_basis']['F8']='Insufficient directly reviewed mechanism evidence.'
  r['primary']=next((x for x in ['F5','F3','F4','F6','F7','F1','F2','F8'] if x in r['labels']),None);r['secondary']=[x for x in r['labels'] if x!=r['primary']]
 previous=read(OUT/'evidence/stage1_sealed.json');save('evidence/stage1_extraction_seal.json',previous)
 export(results)
 save('evidence/atlas_reconciliation.json',{'at':now(),'paid_calls':0,'reextracted_candidates':False,'old_grades_rerun':False,'reused_37_retry_grades':len(grades),'reviewer':'Codex assistant, no independent human','manual_reviews':manual,'F6_convention':'Goal drift remains F3, not counted again as arithmetic/derivation error. Zero F6 is confirmed lower bound, not proof all unreviewed historical answers are correct.'})
if __name__=='__main__':main()
