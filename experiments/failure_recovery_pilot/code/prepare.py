"""Historical evidence first; no paid calls. Predeclare small, question-only pools."""
import collections,re,shutil,time
from common import *
from flowevo_recovery.public import Task,State

def main():
 cap();old=BOT/'experiments/math500_goldfree_20261009';native=EXTERNAL/'experiments/flowevo_native_mbpp500_20261008'
 if (OUT/'dataset_split_manifest.json').exists():raise RuntimeError('already prepared')
 manifest=read(ROOT/'UPLOAD_MANIFEST.json');protected=[x for x in manifest['files'] if x['path']!='指引.txt']
 assert all(sha(ROOT/x['path'])==x['sha256'] for x in protected)
 write(OUT/'snapshots/protected_history.json',protected);shutil.copy2(ROOT/'指引.txt',OUT/'snapshots/指引.txt')
 historical=read(BOT/'experiments/flowevo_bot_v2_math500/data/historical_rechecked.json')
 problems={r['task_id']:r for n in ('train','dev','test') for r in lines(old/f'manifests/{n}.problems.jsonl')}
 cases=[]
 reviewed={
 'math_test_algebra_673':'40/0.02=2000; candidate merely includes calories.',
 'math_test_algebra_884':'(3491-60)(3491+60)-3491^2=-3600; magnitude of decrease is3600.',
 'math_test_counting_probability_411':'4*12/C(52,3)=12/5525; reference includes LaTex thousands separator.',
 'math_test_geometry_165':'Circumcenter at BC midpoint implies angleA=90, so angleC=40.',
 'math_test_geometry_48':'Shaded triangles have areas1 and2 in area4, giving75%; label is75.',
 'math_test_intermediate_algebra_796':'Oddness implies f(3)=-f(-3)=-5; (3,-5) is valid even though reference chooses(0,0).',
 'math_test_prealgebra_334':'(5*13+7)/6=12 grams; reference uses gm.',
 'math_test_prealgebra_435':'10/4=2.50 dollars; currency wrapper mismatch.',
 'math_test_prealgebra_498':'360-3*108=36 degrees; unicode vs LaTex degree unit.'}
 originals={r['task_id']:r for r in read(old/'flowevo_bot/rows.json')}
 for r in historical:
  if r['method']!='flowevo_bot' or originals[r['task_id']]['final_correct']:continue
  tid=r['task_id'];tr=r['truncation_status'];p=problems[tid]
  cases.append({'task_id':tid,'domain':'math','subject':p['subject'],'level':p['level'],'problem':r['question'],
   'original_solution':r['solution'],'original_final_answer':r['answer'],'original_offline_correct':False,
   'frozen_v2_correct':r['rechecked_correct'],'truncated':tr,'primary':'Truncation Failure' if tr else 'Evaluator/Environment Issue',
   'secondary':[],'failure_location':'response tail/output cap' if tr else 'final answer comparison',
   'evidence':'provider output token cap; final result incomplete' if tr else reviewed[tid],
   'reviewed_correct':False if tr else True,'local_error_verified':False,
   'unknowns':'Underlying reasoning could still be faulty; a single truncation cannot establish inability.' if tr else 'Does not indicate a recovery need.',
   'use':'retrospective_only_not_memory_or_holdout','gold_free_first_pass':True})
 physical=lines(native/'physical_requests.jsonl');first={r['task_id']:r for r in physical if r['call']==1}
 observations=lines(native/'observations.jsonl');obs={r['task_id']:r for r in observations if r['call']==1}
 receipts={r['task_id']:r['receipt'] for r in lines(native/'verifier_receipts.jsonl') if r['call']==1}
 tasks={r['task_id']:r for r in read(native/'tasks.json')};summary=read(native/'summary.json')
 final={r['task_id']:r for r in summary['task_results']};codefirst=[]
 for tid,r in sorted(first.items()):
  response=json.loads(r['raw_response']);text=response['choices'][0]['message']['content'];tr=response['choices'][0]['finish_reason']=='length'
  codefirst.append({'task_id':tid,'request':r['raw_payload'],'response':response,'observation':obs[tid],'receipt':receipts[tid],'source_sha256':sha(native/'physical_requests.jsonl')})
  if obs[tid]['passed']:continue
  receipt=receipts[tid];stderr=receipt.get('stderr','');failed=receipt.get('failed_tests',[])
  primary='Truncation Failure' if tr else 'Answer/Format Failure' if 'SyntaxError' in stderr or 'IndentationError' in stderr else 'Verification Failure'
  cases.append({'task_id':tid,'domain':'code','subject':'MBPP','level':'unspecified','problem':tasks[tid]['text'],
   'original_solution':text,'original_final_answer':obs[tid]['candidate'],'original_offline_correct':False,'truncated':tr,
   'primary':primary,'secondary':['Unknown'] if primary=='Verification Failure' else [],'failure_location':failed or stderr[-1200:] or 'public test harness',
   'evidence':receipt,'local_error_verified':False,'reviewed_correct':False,'unknowns':'Public test failure alone does not distinguish a local implementation bug from an incorrect strategy.',
   'final_native_failed':not final[tid]['native_passed'],'use':'retrospective_only_not_memory_or_holdout',
   'gold_free_first_pass':True,'all_tests_visible':True,'settings':r['raw_payload']})
 jl(OUT/'failure_cases.jsonl',cases);csvwrite(OUT/'failure_labels.csv',[{k:v for k,v in r.items() if k in ['task_id','domain','primary','secondary','truncated','reviewed_correct','failure_location','unknowns']} for r in cases])
 jl(OUT/'snapshots/native_code_first_passes.jsonl',codefirst)
 write(OUT/'evidence/historical_audit.json',{'reference_commit':'eba3d76c8418ea28173004b2f46e51c3856b0643',
  'math_original_correct':464,'math_original_failures':36,'math_truncated':27,'math_reviewed_false_negatives':9,
  'math_review_adjusted_exploratory_correct':473,'math_warning':'464 originals not all re-adjudicated; nine explicit false negatives audited; never overwrite published464.',
  'code_tasks':500,'code_first_correct':434,'code_first_failed':66,'code_final_failed':28,'code_all_tests_visible':True,
  'code_settings':summary['generation_settings'],'code_native_recovery':summary['stage_successes'],
  'code_source':str(native),'code_source_hashes':{n:sha(native/n) for n in ['logical_requests.jsonl','physical_requests.jsonl','observations.jsonl','verifier_receipts.jsonl','tasks.json']},
  'math_source_hashes':{n:sha(old/n) for n in ['flowevo_bot/rows.json','flowevo_bot/calls.json','train/rows.json','train/calls.json']},
  'cases':len(cases),'taxonomy_counts':{d:dict(collections.Counter(r['primary'] for r in cases if r['domain']==d)) for d in ['math','code']},
  'protected_files':len(protected),'new_API_calls':0})
 # Training source failures: one truncation per available subject (six) plus the audited dime interpretation error.
 train=[r for r in historical if r['method']=='train'];selected=[]
 for subject in sorted({problems[r['task_id']]['subject'] for r in train}):
  rs=[r for r in train if r['truncation_status'] and problems[r['task_id']]['subject']==subject]
  if rs:selected.append(min(rs,key=lambda r:digest(['recovery-train',r['task_id']])))
 selected.append(next(r for r in train if r['task_id']=='math_train_prealgebra_76'))
 calls=read(old/'train/calls.json');byid={c['task_id']:c for c in calls['calls']};states=[]
 for r in selected:
  c=byid[r['task_id']];p=problems[r['task_id']]
  task=Task(task_id=r['task_id'],domain='math',problem=p['problem'],subject=p['subject'],level=p['level'])
  states.append(State(task=task,solution=r['solution'],truncated=r['truncation_status'],call_id=c['call_id'],input_tokens=c['prompt_tokens'],output_tokens=c['completion_tokens']).model_dump())
 jl(OUT/'data/train_math_states.jsonl',states)
 # Code training pool from the official non-test portion (IDs601..974); no synthetic problems.
 mbpp=lines(EXTERNAL/'data/raw/mbpp/mbpp.jsonl');candidates=[r for r in mbpp if r['task_id']>=601 and len(r['test_list'])>=3]
 # Group digit-masked problem text, keep recovery train/confirmation distinct.
 def norm(t):return re.sub(r'\d+','#',' '.join(t.lower().split()))
 groups=collections.defaultdict(list)
 for r in candidates:groups[norm(r['text'])].append(r)
 ordered=sorted(groups,key=lambda k:digest(['recovery-code',k]));traincode=[];confirmcode=[]
 for k in ordered:
  row=groups[k][0]
  if len(traincode)<32:traincode.append(row)
  elif len(confirmcode)<24:confirmcode.append(row)
  if len(confirmcode)==24:break
 allmath=lines(BOT/'data/manifests/math_grouped/train.problems.jsonl')+lines(BOT/'data/manifests/math_grouped/dev.problems.jsonl')
 used={r['task_id'] for r in historical}
 for path in [BOT/'experiments/flowevo_bot_v2_math500/data/dev_tasks.json',BOT/'experiments/macro_discovery_pilot/data/dev_tasks.json']:
  used|={r['problem']['task_id'] for r in read(path)}
 pool=[r for r in allmath if r['task_id'] not in used and r['level'] in ('Level 4','Level 5')]
 confirmmath=[]
 for subject in sorted({r['subject'] for r in pool}):
  n=4 if subject in ('algebra','intermediate_algebra','number_theory') else 3
  confirmmath+=sorted([r for r in pool if r['subject']==subject],key=lambda r:digest(['recovery-confirm',r['task_id']]))[:n]
 assert len(confirmmath)==24
 code_task=lambda r:Task(task_id='mbpp_train_'+str(r['task_id']),domain='code',problem=r['text'],public_tests=r['test_list'][:1],setup=r.get('test_setup_code','')).model_dump()
 public_train=[code_task(r) for r in traincode]
 public_confirm=[Task(task_id=r['task_id'],domain='math',problem=r['problem'],subject=r['subject'],level=r['level']).model_dump() for r in confirmmath]+[code_task(r) for r in confirmcode]
 jl(OUT/'data/train_code_tasks.jsonl',public_train);jl(OUT/'data/confirmation_tasks.jsonl',public_confirm)
 mathlabels={r['task_id']:r for n in ('train','dev') for r in lines(BOT/f'data/manifests/math_grouped/{n}.labels.jsonl')}
 labels={t['task_id']:{'gold_answer':mathlabels[t['task_id']]['gold_answer']} for t in [s['task'] for s in states]+public_confirm if t['domain']=='math'}
 for r in traincode+confirmcode:labels['mbpp_train_'+str(r['task_id'])]={'hidden_tests':r['test_list'][1:],'reference':r['code']}
 write(OUT/'data/offline_labels.json',labels)
 write(OUT/'dataset_split_manifest.json',{'created_at':now(),'train_math_source_ids':[s['task']['task_id'] for s in states],
  'train_code_ids':[r['task_id'] for r in public_train],'confirmation_ids':[r['task_id'] for r in public_confirm],
  'confirmation_selection':'24 MATH train Level4/5 stratified hash +24 MBPP non-test hash; no selection by new response correctness',
  'math_prior_exposure':'V1-V4 may have inspected question text/labels; no historical model first-pass in available in-repo ledgers; independent of Recovery source/Memory, not globally pristine',
  'code_prior_exposure':'different IDs from native500 and Recovery training; earlier sibling studies may have used MBPP training tasks; no global pristine claim',
  'deduplication':'disjoint task IDs and digit-masked exact code text groups; inspect structural similarity before freeze; no claim of universal semantic disjointness',
  'historical_test_ids_excluded':True,'code_test_protocol':'first official test public; remaining2 offline only; hidden/reference never passed to Task schema',
  'files':{n:sha(OUT/'data'/n) for n in ['train_math_states.jsonl','train_code_tasks.jsonl','confirmation_tasks.jsonl','offline_labels.json']}})
 write(OUT/'config.json',{'reference_commit':'eba3d76c8418ea28173004b2f46e51c3856b0643','model':'deepseek-flash',
  'temperature':0,'math_max_tokens':4096,'code_max_tokens':2048,'code_thinking':'disabled','math_thinking':'omitted_matching_old_baseline',
  'max_calls':240,'max_tokens':300000,'api_workers':8,'api_max_concurrency':64,'local_workers':12,
  'max_extra_calls_per_method':1,'gold_reflection':False,'infrastructure_retries':0,'correctness_retries':0,
  'source_train_math':len(states),'source_train_code_first':32,'train_code_failure_cap':8,'confirmation_math':24,'confirmation_code':24,
  'training_token_soft_cap':155000,'training_policy':'four actions per selected failure; cumulative training token cap155000; incomplete source blocks excluded from memory',
  'memory_min_sources':2,'memory_utility':'mean(correct)-mean(additional_tokens)/100000; need>=0.05 advantage vs A or lower tokens at equal success',
  'confirmation_policy':'freeze decisions before offline labels; share the same sampled output for identical task/action across methods; charge each method its logical calls',
  'priority':'confirmation fixed-retry and A/C actions before shuffled; do not select best branch by gold',
  'context_char_cap':6000,'final_commit':'always use chosen branch output if a recovery is chosen; no oracle rollback'})
 print('audit',len(cases),'trainingmath',len(states),'trainingcode',len(public_train),'confirmation',len(public_confirm))
if __name__=='__main__':main()
