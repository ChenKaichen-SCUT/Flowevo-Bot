"""Cross-artifact integrity checks on new results, not a rerun of old experiments."""
import sys,json,collections,gzip,csv
from pathlib import Path
from datetime import datetime
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from common import ROOT,OUT,read,jl,sha,digest,save,now

@pytest.fixture(scope='module')
def data():
 return {'calls':jl(OUT/'api_calls.jsonl'),'baseline':jl(OUT/'baseline_results.jsonl'),'candidates':jl(OUT/'candidate_generations.jsonl'),'summary':read(OUT/'summary.json'),'dataset':read(OUT/'dataset_manifest.json')}

def test_official_dataset_partition_and_mapping(data):
 tasks=data['dataset']['tasks'];assert len(tasks)==605 and len({t['task_id']for t in tasks})==605
 assert collections.Counter(t['split']for t in tasks)=={'validation':119,'test':486}
 v={t['normalized_problem_sha256']for t in tasks if t['split']=='validation'};t={t['normalized_problem_sha256']for t in tasks if t['split']=='test'}
 assert not(v&t)and data['dataset']['same_617_verified']is False
 assert all(r['equals_current_official_split']for r in jl(OUT/'evidence/official_csv_partition_checks.jsonl'))

def test_full_validation_sampling_and_real_response_ids(data):
 rows=data['candidates'];assert len(rows)==476
 by=collections.defaultdict(list)
 for r in rows:by[r['task_id']].append(r['candidate'])
 assert len(by)==119 and all(sorted(v)==[1,2,3,4]for v in by.values())
 assert len({r['response']['id']for r in data['calls']})==962
 byrequest=collections.defaultdict(set)
 for r in data['calls']:byrequest[r['task_id']].add(r['request_hash'])
 assert all(len(x)==1 for x in byrequest.values())

def test_every_request_has_only_frozen_public_context(data):
 prompts={r['task_id']:r for r in jl(OUT/'data/public_prompts.jsonl')}
 for r in data['calls']:
  req=r['request'];assert set(req)=={'model','messages','temperature','max_tokens','stream','stream_options'}
  assert req['messages']==[{'role':'system','content':'You are an expert programmer and mathematician.'},{'role':'user','content':prompts[r['task_id']]['prompt']}]
  assert req['max_tokens']==16384 and req['model']=='deepseek-flash'
  assert digest(req)==r['request_hash']and digest(r['response'])==r['response_hash']

def test_new_test_requests_after_method_freeze(data):
 frozen=datetime.fromisoformat(read(OUT/'checkpoints/METHOD_FROZEN_FOR_TEST.json')['frozen_at'])
 ids={r['task_id']for r in data['baseline']if r['split']=='test'}
 rs=[r for r in data['calls']if r['task_id']in ids and not r['reused']]
 assert len(rs)==479 and all(datetime.fromisoformat(r['started_at'])>frozen for r in rs)

def test_selection_sealed_before_candidate_grading():
 sel=read(OUT/'checkpoints/selection_k4_SEALED.json');grade=read(OUT/'evidence/validation4_grading_barrier.json')
 assert datetime.fromisoformat(sel['at'])<datetime.fromisoformat(grade['at'])
 assert sel['sha256']==sha(OUT/sel['path'])and sel['new_candidate_grading_not_started']
 assert len(jl(OUT/sel['path']))==119

def test_seals_and_evaluator_source_unchanged():
 for name in ['evidence/pre_api_freeze.json','checkpoints/METHOD_FROZEN_FOR_TEST.json']:
  for p,h in read(OUT/name)['files'].items():assert sha(ROOT/p)==h,p
 for stage in ['validation1','validation4','test1']:
  for p,h in read(OUT/'checkpoints'/f'{stage}_SEALED.json')['files'].items():assert sha(OUT/p)==h

def test_physical_tokens_reconcile_including_reasoning(data):
 attempts=[read(p)for p in (OUT/'attempts').glob('*.json')];assert len(attempts)==955
 assert all(a['usage_known']and a['status']=='completed'for a in attempts)
 assert sum(a['total_tokens']for a in attempts)==1682920
 assert sum(r['total_tokens']for r in data['calls']if not r['reused'])==1682920
 assert sum(r['total_tokens']for r in data['calls']if r['reused'])==11532
 for r in data['calls']:
  assert r['input_tokens']+r['output_tokens']==r['total_tokens']
  assert r['reasoning_tokens']+r['final_content_tokens']==r['output_tokens']
 assert not list((OUT/'attempts').glob('*.pending.json'))

def test_raw_streams_preserve_provider_output(data):
 for r in data['calls']:
  if r['reused']:continue
  chunks=[];reason=[];u=None;finish=None;done=False
  with gzip.open(OUT/r['raw_stream'],'rt')as f:
   for line in f:
    if not line.startswith('data:'):continue
    text=line[5:].strip()
    if text=='[DONE]':done=True;continue
    x=json.loads(text)
    if x.get('usage'):u=x['usage']
    for c in x.get('choices',[]):
     d=c.get('delta',{});chunks.append(d.get('content')or '');reason.append(d.get('reasoning_content')or '')
     if c.get('finish_reason'):finish=c['finish_reason']
  m=r['response']['choices'][0]['message']
  assert done and ''.join(chunks)==m['content']and ''.join(reason)==m['reasoning_content']
  assert u==r['response']['usage']and finish==r['finish_reason']

def test_history_reuse_is_exact_unconditional_arm(data):
 reused=[r for r in data['calls']if r['reused']];assert len(reused)==7
 for r in reused:
  assert sha(ROOT/r['source_path'])==r['source_file_sha256']
  old=read(ROOT/r['source_path']);assert old['stage']=='b2'and old['max_tokens']==16384
  assert r['request']==old['request']and r['response']==old['response']

def test_noncorrect_review_and_ambiguity_preserved(data):
 failures=jl(OUT/'failure_cases.jsonl');assert len(failures)==60
 assert collections.Counter(r['adjudication_category']for r in failures)=={'A':9,'B':49,'H':2}
 assert all(r['audit_proof']for r in failures)
 assert all(r['mathematical_correct']is None for r in failures if r['adjudication_category']=='H')
 base=data['baseline'];assert sum(r['mathematical_correct']is True for r in base)==597
 assert sum(not r['answer_complete']for r in base)==6
 assert sum(r['complete_math_error']for r in base)==0

def test_selection_report_is_actual_frozen_selection(data):
 public={r['task_id']:r for r in jl(OUT/'selection_public_k4.jsonl')};rs=jl(OUT/'selection_results.jsonl');assert len(rs)==357
 for r in rs:
  assert r['selected_candidate']==public[r['task_id']]['selections'][r['method']]
  assert r['gold_used_to_select']is False and r['new_selection_api_calls']==0
 assert sum(r['mathematical_correct']is True for r in rs if r['method']=='majority')==119
 assert sum(r['math_generation_selection_gap']for r in rs if r['method']=='verification')==0

def test_optional_stages_not_fabricated():
 assert read(OUT/'checkpoints/pass8_decision.json')['run_pass8']is False
 assert not (OUT/'checkpoints/validation8_SEALED.json').exists()
 with (OUT/'pass_at_k.csv').open()as f:rs=list(csv.DictReader(f))
 assert all(r['math_correct']=='NA'and r['measured']=='False'for r in rs if r['k']=='8')
 assert read(OUT/'evidence/official_workflow_audit.json')['execution_performed']is False

def test_old_workspace_snapshot_unchanged():
 old=read(OUT/'evidence/protected_previous_snapshot.json');verified=[];bad=[];allowed=[]
 for item in old['files']:
  p=ROOT/item['path']
  if item['path']=='指引.txt':allowed.append({'path':item['path'],'old':item['sha256'],'new':sha(p),'reason':'User supplied the next-stage guide'});continue
  if not p.is_file()or sha(p)!=item['sha256']:bad.append(item['path'])
  else:verified.append(item['path'])
 save('evidence/historical_hash_verification.json',{'at':now(),'previous_snapshot_files':old['file_count'],'protected_verified_count':len(verified),'allowed_guide_change':allowed,'unexpected_changes':bad,'historical_experiments_not_rerun':True})
 assert not bad,bad

def test_all_requested_outputs_exist():
 names=['00_EXECUTIVE_SUMMARY.md','01_DATASET_AND_SPLIT_AUDIT.md','02_DEEPSEEK_BASELINE.md','03_TRUE_FAILURE_ANALYSIS.md','04_PASS_AT_K_ANALYSIS.md','05_CANDIDATE_SELECTION.md','06_GENERATION_SELECTION_GAP.md','07_AFLOW_WORKFLOW_COMPARISON.md','08_ACCURACY_AND_COST.md','09_NEXT_RESEARCH_DIRECTION.md','dataset_manifest.json','baseline_results.jsonl','failure_cases.jsonl','failure_taxonomy.csv','candidate_generations.jsonl','pass_at_k.csv','selection_results.jsonl','generation_selection_gap.csv','task_pairwise.csv','api_calls.jsonl','cost_breakdown.csv','run_manifest.json']
 assert all((OUT/n).is_file()and(OUT/n).stat().st_size for n in names)
