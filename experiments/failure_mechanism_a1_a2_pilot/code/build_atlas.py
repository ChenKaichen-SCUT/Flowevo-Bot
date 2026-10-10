"""New retrospective mechanism extraction; reuse all historical answer grades."""
from common import *
import csv,re,collections,signal
from concurrent.futures import ProcessPoolExecutor
from math_control import candidate_events,check_goal
from math_control.parser_bridge import boxes,parse_public
sys.path.insert(0,str(ROOT/'experiments/math500_scoring_and_budget_v2/code'))
from completion import detect
E=ROOT/'experiments'
TAX={'F1':'Answer Found but Not Finalized','F2':'Repeated Reasoning / Verification Loop','F3':'Goal Drift','F4':'Constraint Drift','F5':'Ambiguous Problem Semantics','F6':'True Mathematical Error','F7':'Evaluator / Interface Failure','F8':'Unknown'}
class Timeout(BaseException):pass

def sources():
 tasks={}
 for split in ('train','test'):
  counts=collections.Counter()
  for r in jl(ROOT/f'FlowEvo/data/datasets/math/{split}.jsonl'):
   sub=r['type'].lower().replace(' & ','_').replace(' and ','_').replace(' ','_');sub=sub.replace('counting_and_probability','counting_probability')
   i=counts[sub];counts[sub]+=1;tid=f'math_{split}_{sub}_{i}'
   tasks[tid]={'task_id':tid,'question':r['problem'],'subject':sub,'level':r['level'],'reference':r['solution']}
 v3={r['response_hash']:r for r in jl(E/'math_evaluator_v3_offline/evaluator_v3_results.jsonl')}
 fixed={r['response_hash']:r['grade'] for r in jl(E/'math500_scoring_and_budget_v2/fixed_scoring_results.jsonl')}
 oldcsv={r['task_id']:r for r in csv.DictReader((E/'math_truncation_and_scoring_audit/math500_rescored.csv').open())}
 recovered={}
 for r in jl(E/'failure_recovery_pilot/task_results.jsonl'):
  if r['domain']!='math':continue
  for field,score in [('initial_call_id','initial_correct'),('recovery_call_id','final_correct')]:
   if r.get(field):recovered[r[field]]=r[score]
 records=[]
 def add(tid,response,budget,source,cohort,grade,grade_source,reasoning_observable=True,job=None,legacy=None):
  t=tasks[tid];msg=response['choices'][0]['message'];comp=detect(tid,response,budget)
  records.append(dict(t,record_id=cohort+':'+str(job or response.get('id') or len(records)),response_id=response.get('id'),response_hash=digest(response),budget=budget,source=source,cohort=cohort,final_text=msg.get('content') or '',reasoning=msg.get('reasoning_content') or '',reasoning_observable=reasoning_observable,finish_reason=response['choices'][0].get('finish_reason'),completion=comp,offline_status=grade,offline_grade_source=grade_source,legacy_correct=legacy,usage=response.get('usage',{})))
 first=E/'math_truncation_and_scoring_audit/evidence/baseline_500.json'
 for r in read(first):
  p=r['provider'];response={'id':p.get('response_id'),'choices':[{'message':{'content':r['solution']},'finish_reason':p['finish_reason']}],'usage':p['usage']}
  grade=oldcsv[r['task_id']]['B_rescored_correct'].lower()=='true'
  add(r['task_id'],response,4096,str(first.relative_to(ROOT)),'batch1_base','correct' if grade else 'incomplete' if r['truncated'] else 'unconfirmed', 'historical_fixed_csv',False,legacy=r['original_correct'])
 for exp,cohort in [('math500_scoring_and_budget_v2','batch2'),('math_truncation_and_scoring_audit','batch1_retries'),('failure_recovery_pilot','earlier_recovery')]:
  path=E/exp/'api_calls.jsonl'
  for r in jl(path):
   if cohort=='earlier_recovery' and r['domain']!='math':continue
   if cohort=='earlier_recovery':raw=read(E/exp/r['raw_path']);response=raw['response'];request=raw['request'];grade='correct' if recovered.get(r['call_id']) is True else 'unconfirmed';gs='historical_recovery_grade' if r['call_id'] in recovered else 'no_saved_grade'
   else:
    response=r['response'];request=r['request'];v=v3.get(r.get('response_hash'));f=fixed.get(r.get('response_hash'))
    if v:grade=v['status'];gs='frozen_V3_reused'
    elif f:grade='correct' if f['correct'] else 'incomplete' if response['choices'][0]['finish_reason']=='length' else 'unconfirmed';gs='historical_fixed_reused'
    elif cohort=='batch1_retries':grade='correct' if r.get('correct') is True else 'incomplete' if response['choices'][0]['finish_reason']=='length' else 'unconfirmed';gs='historical_retry_metadata'
    else:grade='unconfirmed';gs='no_saved_grade'
   add(r['task_id'],response,request['max_tokens'],str(path.relative_to(ROOT)),cohort,grade,gs,True,r.get('job_id',r.get('call_id',str(r.get('budget')))))
 # Actual IDs take priority for deduplication. No history file is modified.
 unique={}
 for r in records:unique.setdefault(r['response_id'] or r['response_hash'],r)
 return list(unique.values())

def analyze(r):
 def timeout(*a):raise Timeout()
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,10)
 events=[];notes=[];goal={};matches=[]
 try:
  events=candidate_events(r['question'],r['reasoning'])
  goal=check_goal(r['question'],r['final_text'])
  bs=boxes(r['reference'])
  if bs:
   ref=parse_public(bs[-1].text,r['question']).to_dict()
   for e in events:
    if e.get('typed') and e['normalized']['kind']==ref['kind'] and e['normalized']['structure']==ref['structure']:
     e['offline_reference_match']='exact_typed_structure';matches.append(e)
 except Timeout:notes.append('local_analysis_timeout; partial events retained')
 except Exception as e:notes.append(type(e).__name__+':'+str(e)[:100])
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 reasoning=r['reasoning'];paras=[p.strip() for p in re.split(r'\n\s*\n',reasoning) if len(p.strip())>=60]
 repeated=[{'text':p,'count':n,'first_offset':reasoning.find(p)} for p,n in collections.Counter(paras).items() if n>=2]
 checks=list(re.finditer(r'\b(?:wait|let me (?:check|verify|reconsider)|double.check|recheck|however|but wait)\b',reasoning,re.I))
 repeat_proxy=bool(repeated or (len(checks)>=4 and max([e.get('same_candidate_occurrences',0) for e in events] or [0])>=3))
 labels=[];basis={};incomplete=r['completion']['retry_required'];tid=r['task_id']
 if incomplete and matches:labels.append('F1');basis['F1']='Explicit exposed candidate exactly matches typed reference, yet response is incomplete; post-hoc reference verification, not online proof.'
 # Prior manually reviewed loops, with exposed repeated verification. Other heuristic matches remain provisional.
 known_loops={'math_test_geometry_66','math_test_intermediate_algebra_253','math_test_algebra_1161','math_test_geometry_56','math_test_intermediate_algebra_494'}
 if incomplete and tid in known_loops and reasoning:labels.append('F2');basis['F2']='Prior mathematical/manual audit documents repeated verification/ambiguity; reused evidence, visible reasoning retained.'
 if tid=='math_test_number_theory_491' and r['offline_status']=='incorrect':labels+=['F3'];basis['F3']='Prior exact audit: sum of starting values 6+11+16+21=54 submitted instead of 6+7+8+9=30; arithmetic itself is valid.'
 if incomplete and tid in {'math_test_intermediate_algebra_253','math_test_algebra_1161'}:labels.append('F5');basis['F5']='Reused independent algebra/graph reasoning in previous assistant audit; no independent human adjudication.'
 # Goal drift is not mislabeled as arithmetic error; F6 requires a demonstrated mathematical error.
 if (r['legacy_correct'] is False and r['offline_status']=='correct') or tid=='math_test_precalculus_187' and r['offline_status']=='unknown':labels.append('F7');basis['F7']='Frozen score correction or proven-correct exponent rejected by frozen V3 resource limit.'
 if r['cohort']=='batch2':
  # Fixed->V3 discrepancies are known interface defects, not new solver events.
  pass
 if (incomplete or r['offline_status'] in ('incorrect','unknown','unconfirmed')) and not labels:labels=['F8'];basis['F8']='Insufficient evidence for a mechanism; incompleteness/legacy false is not itself a mathematical error.'
 primary=next((x for x in ['F5','F3','F4','F6','F7','F1','F2','F8'] if x in labels),None)
 r.update(labels=labels,primary=primary,secondary=[x for x in labels if x!=primary],label_basis=basis,candidate_events=events,first_candidate_offset=min([e['start'] for e in events] or [-1]),offline_matching_candidates=matches,repeat_proxy=repeat_proxy,repeated_paragraphs=repeated,check_marker_count=len(checks),check_marker_spans=[{'start':m.start(),'end':m.end(),'text':m[0]} for m in checks[:30]],goal_check=goal,analysis_notes=notes)
 return r

def export(results):
 # Reuse fixed->V3 evaluator corrections by response hash association.
 corrections={r['response_hash'] for r in jl(E/'math500_scoring_and_budget_v2/fixed_scoring_results.jsonl') if r['grade']['correct'] is not True}
 vcorrect={r['response_hash'] for r in jl(E/'math_evaluator_v3_offline/evaluator_v3_results.jsonl') if r['status']=='correct'}
 provider_corrections={r['response']['id'] for r in jl(E/'math500_scoring_and_budget_v2/api_calls.jsonl') if r['response_hash'] in corrections & vcorrect}
 for r in results:
  if r['response_id'] in provider_corrections:
   r['labels']=[x for x in r['labels'] if x!='F8']+['F7'];r['label_basis']['F7']='Reused fixed false -> V3 correct result for identical frozen response';r['primary']='F7'
  if 'reference' in r:r['reference_raw_sha256']=digest(r.pop('reference'))
 lines('historical_records.jsonl',results)
 lines('failure_cases.jsonl',[r for r in results if r['labels']])
 lines('repeated_reasoning_cases.jsonl',[r for r in results if r['repeat_proxy'] or 'F2' in r['labels']])
 lines('goal_drift_cases.jsonl',[r for r in results if 'F3' in r['labels'] or r['goal_check'].get('high_confidence_mismatch')])
 lines('historical_candidate_events.jsonl',[dict(e,record_id=r['record_id'],task_id=r['task_id'],budget=r['budget']) for r in results for e in r['candidate_events']])
 tids={r['task_id'] for r in results};bytask=collections.defaultdict(list)
 for r in results:bytask[r['task_id']].append(r)
 taxonomy=[]
 for code,title in TAX.items():
  rows=[r for r in results if code in r['labels']];ids={r['task_id'] for r in rows};success=sum(any(r['offline_status']=='correct' for r in bytask[t]) for t in ids)
  taxonomy.append({'code':code,'name':title,'records':len(rows),'tasks':len(ids),'all_audited_tasks':len(tids),'task_fraction':len(ids)/len(tids),'ever_historical_correct_tasks':success,'no_confirmed_correct_tasks':len(ids)-success,'subjects':dict(collections.Counter(next(r['subject'] for r in rows if r['task_id']==t) for t in ids)),'mean_output_tokens':sum(r['usage'].get('completion_tokens',0) for r in rows)/max(1,len(rows))})
 with (OUT/'failure_taxonomy.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(taxonomy[0]));w.writeheader();w.writerows(taxonomy)
 features=[{'record_id':r['record_id'],'task_id':r['task_id'],'reasoning_available':r['reasoning_observable'],'candidate_count':len(r['candidate_events']),'typed_candidates':sum(e['typed'] for e in r['candidate_events']),'repeat_proxy':r['repeat_proxy'],'goal_mismatch_proxy':r['goal_check'].get('high_confidence_mismatch',False),'truncated':r['finish_reason']=='length','final_answer_present':r['completion']['final_answer_present'],'offline_reference_used_online':False} for r in results]
 with (OUT/'online_observable_features.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(features[0]));w.writeheader();w.writerows(features)
 summary={'records':len(results),'tasks':len(tids),'cohorts':dict(collections.Counter(r['cohort'] for r in results)),'reasoning_observable_records':sum(r['reasoning_observable'] for r in results),'reasoning_observable_tasks':len({r['task_id'] for r in results if r['reasoning_observable']}),'taxonomy':taxonomy,'repeat_proxy_records':sum(r['repeat_proxy'] for r in results),'repeat_proxy_tasks':len({r['task_id'] for r in results if r['repeat_proxy']}),'candidate_records':sum(bool(r['candidate_events']) for r in results),'candidate_tasks':len({r['task_id'] for r in results if r['candidate_events']}),'local_analysis_notes':dict(collections.Counter(n for r in results for n in r['analysis_notes'])),'paid_calls':0,'old_grades_rerun':False,'limits':'F1 exact-reference candidate evidence does not establish a complete solution. F2 reviewed lower bound; proxies are not confirmed loops. F3 goal error excluded from F6 arithmetic-error count. Earlier recovery uses different prompts. All success controls retained.'}
 save('evidence/atlas_summary.json',summary)
 save('evidence/stage1_sealed.json',{'sealed_at':now(),'new_model_calls':0,'files':{str(p.relative_to(OUT)):sha(p) for p in [OUT/'historical_records.jsonl',OUT/'failure_cases.jsonl',OUT/'evidence/atlas_summary.json']}})
 print(json.dumps(summary,ensure_ascii=False,indent=2))

def main():
 if (OUT/'evidence/stage1_sealed.json').exists():print('stage1 already sealed: reused');return
 records=sources()
 with ProcessPoolExecutor(max_workers=12) as pool:results=list(pool.map(analyze,records,chunksize=1))
 export(results)
if __name__=='__main__':main()
