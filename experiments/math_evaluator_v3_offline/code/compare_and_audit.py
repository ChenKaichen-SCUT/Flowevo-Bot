from common import *
from independent_proofs import proofs
from select_audit_sample import select
import csv,collections,statistics

def csvfile(name,rows):
 with (OUT/name).open('w',newline='') as f:
  if not rows:return
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def old_status(r,name):
 value=r['legacy']['final_correct'] if name=='legacy' else r['fixed']['correct']
 return 'correct' if value is True else 'incorrect' if value is False else 'unknown'

def main():
 rs=jl(OUT/'evaluator_v3_results.jsonl');old={r['record_id']:r for r in jl(OUT/'evidence/legacy_fixed_reproduced.jsonl')};freeze=read(OUT/'evidence/evaluator_freeze.json')
 for r in rs:r['code_sha256']=freeze['source_tree_sha256'];r['reference_commit']=REF
 lines('evaluator_v3_results.jsonl',rs)
 rows=[]
 for r in rs:
  o=old[r['record_id']]
  rows.append({'record_id':r['record_id'],'task_id':r['task_id'],'branch':r['branch'],'subject':r['subject'],'level':r['level'],'legacy_status':old_status(o,'legacy'),'fixed_status':old_status(o,'fixed'),'v3_status':r['status'],'v3_reason':r['reason'],'answer_type':r['answer_spec']['kind'],'request_hash':r['request_hash'],'response_hash':r['response_hash'],'prediction_raw':r['prediction_raw'],'reference_raw':r['reference_raw'],'v3_evidence_file':'evaluator_v3_results.jsonl','source_path':r['source_path'],'code_sha256':r['code_sha256']})
 csvfile('evaluator_comparison_500.csv',rows)
 transitions=collections.Counter((r['branch'],r['legacy_status'],r['fixed_status'],r['v3_status']) for r in rows)
 csvfile('scoring_transitions.csv',[{'branch':k[0],'legacy':k[1],'fixed':k[2],'v3':k[3],'records':v} for k,v in sorted(transitions.items())])
 types=collections.Counter((r['branch'],r['answer_type'],r['v3_status']) for r in rows)
 csvfile('answer_type_statistics.csv',[{'branch':k[0],'answer_type':k[1],'v3_status':k[2],'records':v} for k,v in sorted(types.items())])
 timing=[]
 for branch in ('base','adaptive'):
  for name in ('legacy','fixed','v3'):
   values=[r['elapsed_seconds'] for r in rs if r['branch']==branch] if name=='v3' else [r[name+'_seconds'] for r in old.values() if r['branch']==branch]
   timing.append({'branch':branch,'evaluator':name,'records':len(values),'sum_record_elapsed_seconds':sum(values),'median_record_seconds':statistics.median(values),'mean_record_seconds':statistics.mean(values),'workers':12,'timing_definition':'sum of per-record elapsed times, not wall/CPU time; cold imports included'})
 csvfile('evaluation_timing.csv',timing)
 math=proofs();save('evidence/independent_proof_checks.json',math)
 sample=select(rs);sample_ids={x['record']['task_id'] for x in sample};lines('evidence/stratified_unanimous_sample.jsonl',sample)
 reviews=[];issues=[]
 for r,row in zip(rs,rows):
  reasons=[]
  if len({row['legacy_status'],row['fixed_status'],r['status']})>1:reasons.append('three_evaluator_disagreement')
  if r['status'] in ('unknown','reference_ambiguous','reference_invalid'):reasons.append('v3_abstention_or_reference_issue')
  if r['status']=='correct' and row['legacy_status']!='correct' and row['fixed_status']!='correct':reasons.append('new_correct_both_old_nontrue')
  if r['task_id'] in sample_ids:reasons.append('fixed_seed_stratified_unanimous_sample_task')
  if all(v=='incorrect' for v in (row['legacy_status'],row['fixed_status'],r['status'])):reasons.append('all_unanimous_incorrect_included')
  issue=None
  if r['reference_builder'].get('multiple_boxes_reconstructed'):
   issue='historical_last_box_incomplete'
  if r['task_id']=='math_test_algebra_1161':issue='inverse_function_ambiguous_noninjective_graph'
  if r['task_id']=='math_test_precalculus_415':issue='reference_derivation_typographical_error_final_answer_valid'
  if issue:
   issues.append(dict(r,integrity_issue=issue,integrity_source='assistant full-reference/public-problem review; metadata, not a changed automatic grade'))
   reasons.append('reference_integrity_issue')
  if not reasons:continue
  review={'record_id':r['record_id'],'task_id':r['task_id'],'branch':r['branch'],'selection_reasons':reasons,'raw_record':r,'legacy_status':row['legacy_status'],'fixed_status':row['fixed_status'],'v3_status':r['status'],'reviewer':'Codex assistant + deterministic exact proof checks; no second reviewer or independent human','code_sha256':r['code_sha256'],'reference_source':r['source_path'],'request_hash':r['request_hash'],'response_hash':r['response_hash']}
  if r['finish_reason']=='length':
   review.update(review_status='verified_submission_incomplete',mathematically_correct_final_answer=None,delivered_complete_answer=False,proof='封存provider finish_reason=length；不从隐藏reasoning或中途候选计分。这里只核验交付状态，不声称已证明该题数学错误。',evidence_source='sealed raw provider response + frozen online completion policy')
  elif r['task_id'] in math:
   review.update(math[r['task_id']],review_status='verified_by_exact_problem_proof',evidence_source='code/independent_proofs.py',delivered_complete_answer=True)
  else:
   review.update(review_status='pending_independent_problem_proof',mathematically_correct_final_answer=None,proof='完整复核材料已生成；不能以评分器一致性代替独立数学证明。',evidence_source='evaluator comparison only')
  reviews.append(review)
 lines('adjudicated_cases.jsonl',reviews)
 unknown=[dict(r,review=next(x for x in reviews if x['record_id']==r['record_id'])) for r in rs if r['status'] in ('unknown','reference_ambiguous','reference_invalid')]
 lines('unknown_review_queue.jsonl',unknown);lines('reference_integrity_issues.jsonl',issues)
 fp=[];fn=[]
 for r in reviews:
  truth=r['mathematically_correct_final_answer']
  for scorer,status in [('legacy',r['legacy_status']),('fixed',r['fixed_status']),('v3',r['v3_status'])]:
   if status=='correct' and truth is False:fp.append(dict(r,scorer=scorer,error_type='verified_false_positive'))
   if truth is True and status!='correct':fn.append(dict(r,scorer=scorer,error_type='verified_incorrect_false_negative' if status=='incorrect' else 'verified_correct_but_abstained',strict_false_negative=status=='incorrect'))
 lines('false_positive_cases.jsonl',fp);lines('false_negative_cases.jsonl',fn)
 stats={}
 for b in ('base','adaptive'):
  br=[r for r in rows if r['branch']==b]
  stats[b]={'counts':{name:dict(collections.Counter(r[name+'_status'] for r in br)) for name in ['legacy','fixed','v3']},'new_vs':{name:{'new_correct':sum(r['v3_status']=='correct' and r[name+'_status']!='correct' for r in br),'new_nontrue':sum(r['v3_status']!='correct' and r[name+'_status']=='correct' for r in br),'net_correct':sum(r['v3_status']=='correct' for r in br)-sum(r[name+'_status']=='correct' for r in br)} for name in ['legacy','fixed']},'new_correct_vs_both':sum(r['v3_status']=='correct' and r['legacy_status']!='correct' and r['fixed_status']!='correct' for r in br),'disagreements':sum(len({r[n+'_status'] for n in ['legacy','fixed','v3']})>1 for r in br)}
 summary={'branches':stats,'reviewed_records':len(reviews),'reviewed_unique_tasks':len({r['task_id'] for r in reviews}),'review_status_counts':dict(collections.Counter(r['review_status'] for r in reviews)),'sample_seed':20261010,'sample_strata':'subject × levels 1-2 / 3 / 4-5','unanimous_correct_sample_unique_tasks':len(sample_ids),'sample_both_branches_reviewed':True,'false_positives':dict(collections.Counter(r['scorer'] for r in fp)),'strict_false_negatives':dict(collections.Counter(r['scorer'] for r in fn if r['strict_false_negative'])),'verified_correct_abstentions':dict(collections.Counter(r['scorer'] for r in fn if not r['strict_false_negative'])),'reference_integrity_unique_tasks':len({r['task_id'] for r in issues}),'automatically_unreviewed_records':len(rs)-len(reviews),'independent_human_reviewers':0,'complete_500_truth_certification':False,'limitations':'Retrospective same-data development; exact certificates cover selected tasks, not all automatic true answers.'}
 save('evidence/audit_summary.json',summary)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
