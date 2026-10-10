"""Cross-file scientific and integration invariants, independent of parser tests."""
from pathlib import Path
import json,hashlib,collections
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def read(p):return json.loads(p.read_text())
RS=jl(OUT/'evaluator_v3_results.jsonl')

def test_same_500_two_complete_branches():
 assert len(RS)==1000 and len({r['task_id'] for r in RS})==500
 assert len({r['record_id'] for r in RS})==1000
 assert collections.Counter(r['branch'] for r in RS)=={'base':500,'adaptive':500}
 assert all(r['request_hash'] and r['response_hash'] and r['code_sha256'] for r in RS)

def test_frozen_historical_scores_reproduced():
 r=read(OUT/'evidence/history_reproduction.json')
 assert r['matches_frozen_per_record'] and r['counts']=={'base':{'legacy':456,'fixed':449},'adaptive':{'legacy':485,'fixed':476}}

def test_review_selection_complete():
 old={r['record_id']:r for r in jl(OUT/'evidence/legacy_fixed_reproduced.jsonl')};reviews={r['record_id']:r for r in jl(OUT/'adjudicated_cases.jsonl')}
 for r in RS:
  o=old[r['record_id']];a='correct' if o['legacy']['final_correct'] else 'incorrect';b='correct' if o['fixed']['correct'] is True else 'incorrect' if o['fixed']['correct'] is False else 'unknown'
  if len({a,b,r['status']})>1 or r['status'].startswith('reference') or r['status']=='unknown':assert r['record_id'] in reviews
 assert all(not r['review_status'].startswith('pending') for r in reviews.values())
 assert read(OUT/'evidence/audit_summary.json')['independent_human_reviewers']==0

def test_length_never_scored_correct():
 for r in RS:
  if r['finish_reason']=='length':assert r['status']=='prediction_incomplete'
 assert sum(r['branch']=='adaptive' and r['status']=='prediction_incomplete' for r in RS)==3
 wrong=next(r for r in RS if r['record_id']=='adaptive:math_test_number_theory_491');assert wrong['status']=='incorrect'

def test_all_twenty_confirmed_cases():
 fixtures=jl(OUT/'evidence/regression_fixtures.jsonl')
 ids={x['record']['task_id'] for x in fixtures if x['category'] in ['coverage17','label3']}
 assert len(ids)==20
 assert all(r['status']=='correct' for r in RS if r['branch']=='adaptive' and r['task_id'] in ids)

def test_runtime_source_frozen_and_id_free():
 freeze=read(OUT/'evidence/evaluator_freeze.json')
 for p,h in freeze['source_files'].items():
  data=(ROOT/p).read_bytes();assert hashlib.sha256(data).hexdigest()==h
  if p.endswith('.py'):assert b'math_test_' not in data
 assert read(OUT/'evidence/protection_audit.json')['status']=='PASS'

def test_zero_model_calls_and_policy_isolation():
 p=read(OUT/'evidence/protection_audit.json');assert p['new_llm_api_calls']==0 and p['new_llm_tokens']==0
 assert not any(p['generation_policy'].values())
 assert not p['modified_protected_files'] and not p['forbidden_runtime_imports']

def test_real_loader_cli_integration():
 p=read(OUT/'evidence/integration_smoke.json');assert p['status']=='PASS' and p['overwrite_rejected']
 assert p['default_evaluator']=='legacy' and p['model_calls']==0
 assert next(r for r in p['native_cli'] if r['evaluator']=='v3')['correct']==6
