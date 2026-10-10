import sys,json,csv,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Flowevo-Bot/src'),str(ROOT/'FlowEvo-Recovery/src'),str(OUT/'code')]
from flowevo_bot.common import digest
from run_budgets import eligible

def load(p):return json.loads(p.read_text())
def calls():return [json.loads(x) for x in (OUT/'api_calls.jsonl').read_text().splitlines()]

def test_every_historical_submission_seal_and_counts():
 bs=load(OUT/'evidence/baseline_500.json');assert len(bs)==500
 assert len({b['task_id'] for b in bs})==500
 for b in bs:
  s=b['original_submission']
  assert s['seal']==digest({k:v for k,v in s.items() if k!='seal'})
  assert b['provider']['usage']['total_tokens']==b['original_row']['total_tokens']
 assert sum(x['truncated'] for x in bs)==27
 assert sum(not x['original_correct'] and not x['truncated'] for x in bs)==9

def test_new_requests_exactly_preserve_parameters_and_raw_response():
 bs={x['task_id']:x for x in load(OUT/'evidence/baseline_500.json')};cs=calls()
 assert len(cs)==37 and len({(x['task_id'],x['budget']) for x in cs})==37
 for c in cs:
  assert bs[c['task_id']]['truncated']
  old=bs[c['task_id']]['provider']['request'];new=c['request']
  assert [k for k in old if old[k]!=new[k]]==['max_tokens'] and set(old)==set(new)
  assert new['max_tokens']==c['budget']
  assert json.loads((OUT/'raw'/f"{c['task_id']}_{c['budget']}.http.txt").read_text())==c['response']
  assert digest(c['request'])==c['request_hash'] and digest(c['response'])==c['response_hash']
  assert c['total_tokens']==c['input_tokens']+c['output_tokens']
  assert 0<=c['reasoning_tokens']<=c['output_tokens']<=c['budget']
 assert sum(c['total_tokens'] for c in cs)==288397
 assert not list((OUT/'raw').glob('*.pending.json')) and not list((OUT/'raw').glob('*.error.json'))

def test_observable_selection_and_seal():
 cs=calls();first=[x for x in cs if x['budget']==8192];second=[x for x in cs if x['budget']==16384]
 eligible_ids={x['task_id'] for x in first if eligible(x)}
 assert len(first)==27 and len(second)==10
 assert eligible_ids=={x['task_id'] for x in second}==set(load(OUT/'evidence/escalation_decision.json')['eligible_task_ids'])
 seal=load(OUT/'evidence/generation_complete_seal.json')
 assert seal['api_calls_sha256']==hashlib.sha256((OUT/'api_calls.jsonl').read_bytes()).hexdigest()
 for x in load(OUT/'evidence/frozen_experiment_code.json'):
  assert hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256']

def test_composite_is_last_rung_not_oracle_and_true_failure_empty():
 cs=calls();rows=list(csv.DictReader((OUT/'math500_rescored.csv').open()));assert len(rows)==500
 assert sum(x['C_composite_correct']=='True' for x in rows)==498
 for r in rows:
  attempts=[x for x in cs if x['task_id']==r['task_id']]
  assert int(r['C_budget'])==max((x['budget'] for x in attempts),default=4096)
 assert (OUT/'remaining_true_failures.jsonl').read_text()==''
 reviews=load(OUT/'evidence/manual_math_review.json');assert reviews['reliable_complete_math_errors']==0 and reviews['new_reference_ambiguity_flags']==1
 assert all(not x['scoring_override'] for x in reviews['items'])
