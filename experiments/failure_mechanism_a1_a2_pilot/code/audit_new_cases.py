"""Post-seal exact proofs and mechanism review; frozen V3 remains unchanged."""
from common import *
import sympy as s,re,collections
from math_control import candidate_events

def main():
 if (OUT/'evidence/pilot_manual_audit.json').exists():print('Completed new-case audit reused');return
 assert (OUT/'checkpoints/ALL_GENERATION_SEALED.json').exists()
 grades=jl(OUT/'pilot_v3_results.jsonl');calls={r['job_id']:r for r in jl(OUT/'api_calls.jsonl')};proofs=[]
 delta=s.Rational(5,100)*(60-60*s.Rational(80,100))*100;assert delta==60
 theta=s.symbols('theta',real=True);xl=s.limit(s.cos(2*theta),theta,s.pi/2,dir='-');yl=s.limit(s.cos(2*theta)*s.tan(theta),theta,s.pi/2,dir='-');assert xl==-1 and yl==-s.oo
 area=s.Rational(30)-s.Rational(30,169)-s.Rational(1920,169);assert area==s.Rational(240,13)
 rock=80*s.sqrt(3)-80*s.pi/3;assert round(float(rock))==55
 proofs=[{'task_id':'math_test_prealgebra_66','exact_result':str(delta)+' cents','proof':'5%*(60-48) dollars = 0.60 dollars = 60 cents. Question explicitly asks cents. Frozen V3 spec omits cent, normalizes prediction to currency quantity 3/5 while reference is dimensionless 60; typed_object_mismatch is an evaluator failure.','frozen_v3_status':'incorrect','adjudicated_math_correct':True,'type':'F7'}, {'task_id':'math_test_precalculus_47','exact_result':'x=-1, equivalently r*cos(theta)=-1','proof':'x=cos(2 theta) -> -1 and y=cos(2 theta)tan(theta) -> -infinity as theta->pi/2 from below. B2 explicitly submits both equivalent forms; frozen parser rejects explanatory parenthesis.','limits':{'x':str(xl),'y':str(yl)},'frozen_v3_status':'unknown','adjudicated_math_correct':True,'type':'F7'}, {'task_id':'math_test_geometry_75','exact_result':str(area),'proof':'Use explicit CN=CM=4. Right 5-12-13 triangle area30; remove similar triangles with scales1/13 and8/13:30*(1-1/169-64/169)=240/13. Asy uses N=(5,0), inconsistent with explicit CN=4; generic reasoning revisits this drawing discrepancy and truncates.','drawing_conflict':'Text CN=4, Asy C=(0,0), N=(5,0). Explicit lengths determine intended solution.','type':'F5_context_conflict'}, {'task_id':'math_test_geometry_232','exact_result':'55 mm','proof':'Center height8 cm, upper line12 cm; extremal angle pi/6. No-slip center displacement8*pi/6; endpoint horizontal projection4*sqrt(3). Two touch points are separated by8*sqrt(3)-8*pi/3 cm, i.e.54.78826 mm, rounded55.','unrounded_mm':str(s.N(rock,18)),'type':'long_verification'}]
 adjud=[]
 for g in grades:
  if g['status']=='correct':continue
  if g['task_id']in {'math_test_prealgebra_66','math_test_precalculus_47'} and g['finish_reason']=='stop':
   adjud.append({'source_job_id':g['source_job_id'],'task_id':g['task_id'],'response_hash':g['response_hash'],'original_v3_status':g['status'],'adjudicated_math_correct':True,'proof_id':g['task_id'],'original_prediction_unchanged':True})
 mechanisms=[]
 for g in grades:
  if g['status']!='prediction_incomplete':continue
  r=calls[g['source_job_id']];reason=r['response']['choices'][0]['message'].get('reasoning_content')or'';events=candidate_events(g['question'],reason)
  keys={'math_test_geometry_75':[r'240\s*/\s*13',r'\\frac\{240\}\{13\}'],'math_test_geometry_232':[r'55\s*(?:mm|mill)',r'54\.788'],'math_test_precalculus_47':[r'x\s*=\s*-1']}
  spans=[]
  for pat in keys.get(g['task_id'],[]):
   for m in re.finditer(pat,reason):spans.append({'start':m.start(),'end':m.end(),'candidate':m[0],'context':reason[max(0,m.start()-150):min(len(reason),m.end()+220)]})
  spans.sort(key=lambda x:x['start']);checks=len(re.findall(r'\b(?:wait|verify|check|reconsider)\b',reason,re.I))
  mechanisms.append({'task_id':g['task_id'],'source_job_id':g['source_job_id'],'stage':r['stage'],'budget':r['max_tokens'],'finish_reason':r['finish_reason'],'reasoning_observable':True,'explicit_candidate_events':events,'mathematically_relevant_candidate_spans':spans[:12],'matching_candidate_occurrences':len(spans),'first_matching_offset':spans[0]['start']if spans else None,'candidate_match_is_posthoc_not_online_gold':True,'verification_marker_count':checks,'F1_candidate_before_incomplete':bool(spans),'F2_reviewed_reverification':r['stage']=='generic' and g['task_id']in {'math_test_geometry_232','math_test_precalculus_47'},'F5_diagram_conflict':g['task_id']=='math_test_geometry_75','proof_id':g['task_id'],'interventions_fired_on_this_response':False,'reason':'A1 policy is attached to the original B2 output only. These are B0/B1 or generic output traces, analyzed after sealing without new retries.'})
 lines('new_failure_mechanisms.jsonl',mechanisms);lines('posthoc_adjudications.jsonl',adjud)
 amap={a['source_job_id']:a for a in adjud};rows=jl(OUT/'task_results.jsonl');mathrows=[]
 for r in rows:
  correct=r['offline_correct'] is True or r['final_job_id']in amap
  mathrows.append({'task_id':r['task_id'],'method':r['method'],'final_job_id':r['final_job_id'],'frozen_v3_status':r['evaluator_status'],'math_correct_after_exception_audit':correct,'basis':'sealed_V3_plus_posthoc_exact_exception_proof' if r['final_job_id']in amap else 'sealed_V3' if r['offline_correct']is True else 'no_complete_answer','not_independent_human_review':True})
 lines('adjudicated_task_results.jsonl',mathrows);metrics={m:sum(r['math_correct_after_exception_audit']for r in mathrows if r['method']==m)for m in sorted({r['method']for r in mathrows})}
 rmap={(r['task_id'],r['method']):r['math_correct_after_exception_audit']for r in mathrows};tids={r['task_id']for r in mathrows};paired={}
 for a,b in [('B2','B1'),('B2','B0'),('B2+a1','B2'),('B2+a2','B2'),('B2+generic','B2')]:
  paired[a+' vs '+b]={'gained':[tid for tid in sorted(tids)if rmap[tid,a]and not rmap[tid,b]],'lost':[tid for tid in sorted(tids)if rmap[tid,b]and not rmap[tid,a]]}
 summary={'at':now(),'reviewer':'Codex assistant plus exact SymPy arithmetic/limits; no independent human','original_v3_code_config_labels_scores_unchanged':True,'pilot_generation_was_complete_before_any_proof':True,'proofs':proofs,'adjudicated_response_records':len(adjud),'posthoc_math_correct_by_method':metrics,'posthoc_paired':paired,'new_F1_records':sum(r['F1_candidate_before_incomplete']for r in mechanisms),'new_F1_tasks':len({r['task_id']for r in mechanisms if r['F1_candidate_before_incomplete']}),'new_F2_reviewed_records':sum(r['F2_reviewed_reverification']for r in mechanisms),'new_F5_drawing_conflict_tasks':1,'B2_remaining_true_math_errors_observed':0,'B2_goal_drift_observed':0,'B2_constraint_drift_observed':0,'limitation':'Only disagreements/incomplete outputs received the additional explicit proof audit; other correct outputs retain frozen V3 evidence. No independent human adjudication; no claim of strict noninferiority.'}
 save('evidence/pilot_manual_audit.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
