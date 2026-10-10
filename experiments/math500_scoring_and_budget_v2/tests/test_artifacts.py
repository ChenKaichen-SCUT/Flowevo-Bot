import sys,json
from pathlib import Path
import pytest
OUT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(OUT/'code'))
import run_experiment as runtime
from audit_artifacts import audit
from manual_audit import exact_checks

def test_sealed_execution_and_policy_integrity():assert audit()['status']=='PASS'
def test_case_specific_mathematical_audit_evidence():assert len(exact_checks())==26

def test_resume_existing_response_does_not_call_transport():
 def fail(req):raise AssertionError('duplicate paid call')
 runner=runtime.Runner(transport=fail)
 entry=json.loads((OUT/'data/native_prompts.json').read_text())['prompts'][0]
 before=runner.normal_calls
 result=runner.call(entry,'base4096',4096)
 assert runner.normal_calls==before and result['task_id']==entry['task_id']

def test_budget_stop_never_expands_cap():
 runner=runtime.Runner(transport=lambda _:None)
 cap=runner.config['max_total_token_reservation']
 with pytest.raises(runtime.BudgetStop):runner.reserve(cap+1)
 assert runner.config['max_total_token_reservation']==cap and runner.active==0

def test_ambiguous_pending_blocks_automatic_resend(tmp_path,monkeypatch):
 (tmp_path/'raw').mkdir();(tmp_path/'raw'/'job.pending.json').write_text('{}')
 monkeypatch.setattr(runtime,'OUT',tmp_path)
 with pytest.raises(RuntimeError,match='pending requests'):runtime.Runner(config=json.loads((OUT/'config.json').read_text()),transport=lambda _:None)
