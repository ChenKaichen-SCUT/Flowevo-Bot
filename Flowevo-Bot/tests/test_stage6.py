import json
from pathlib import Path
import pytest
from runtime.llm_client import LLMClient
from runtime.config import MODES,load_config
from flowevo_bot.cli import main
from flowevo_bot.common import read_json
from flowevo_bot.data import prepare_math
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.token_accounting import TokenLedger
from flowevo_bot.reporting import analyze
from flowevo_bot.schemas import ProblemView
from flowevo_bot.math_solver import MathSolver
from conftest import make_skill

ROOT=Path(__file__).resolve().parents[1]


def test_cli_offline_end_to_end(tmp_path):
    config=str(ROOT/'configs/default.yaml')
    output=tmp_path/'bank.json'
    main(['build-bank','--config',config,'--train-manifest',str(ROOT/'data/manifests/train.json'),
          '--dev-manifest',str(ROOT/'data/manifests/dev.json'),'--output',str(output),'--dry-run'])
    bank=StrategyBank.load(output,allow_synthetic=True)
    assert len(bank.skills)==2 and all(s.status=='shadow' for s in bank.skills.values())
    assert sum(bank.build_costs.values())==sum(c.total_tokens for c in bank.cost_calls)
    for mode in MODES:
        main(['evaluate','--config',config,'--manifest',str(ROOT/'data/manifests/test.json'),
              '--mode',mode,'--bank',str(output),'--output-dir',str(tmp_path/'runs'/mode),'--dry-run'])
        summary=read_json(tmp_path/'runs'/mode/'summary.json')
        assert summary['n']==3 and summary['real_api_calls']==0 and summary['simulated']
    main(['analyze','--runs-dir',str(tmp_path/'runs'),'--output',str(tmp_path/'report.md')])
    assert len(read_json(tmp_path/'report.pairwise.json'))==18
    amortized=read_json(tmp_path/'report.amortized.json')
    assert amortized['subject_strategy_costaware']['net_tokens_saved']<0


def test_dry_run_ignores_paid_config_and_key(tmp_path,monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','DO_NOT_SEND_THIS_KEY')
    config=ROOT/'configs/default.yaml'
    main(['evaluate','--config',str(config),'--manifest',str(ROOT/'data/manifests/test.json'),
          '--mode','base_onepass','--bank',str(ROOT/'data/skill_banks/empty_mock_bank.json'),
          '--output-dir',str(tmp_path/'run'),'--dry-run','--allow-paid-api'])
    assert read_json(tmp_path/'run/summary.json')['real_api_calls']==0
    assert 'DO_NOT_SEND_THIS_KEY' not in (tmp_path/'run/calls.json').read_text()


def test_public_prompt_budget_and_fair_format(config):
    from code_math.baseline import base_prompt,OUTPUT_INSTRUCTION
    from flowevo_bot.prompt_builder import compact_prompt
    task=ProblemView(task_id='t',subject='algebra',problem='Find the degree of the polynomial x^2.')
    skill=make_skill()
    assert base_prompt(task).endswith(OUTPUT_INSTRUCTION)
    assert compact_prompt(task,[skill]).endswith(OUTPUT_INSTRUCTION)
    over=make_skill(compact_prompt='word '*1000)
    client=LLMClient(config.llm,mock_handler=lambda p,k:'The answer is 2.')
    s=MathSolver(client,config,StrategyBank([over],synthetic=True),'subject_strategy').solve(task)
    assert s.decision.route=='base' and 'Relevant strategy:' not in client.prompts[0]


def test_truncated_call_cannot_be_reused_as_success(config,tmp_path):
    llm=LLMClient(config.llm,TokenLedger(tmp_path/'calls.json'),mock_handler=lambda p,k:{'text':'The answer is 4.','finish_reason':'length'})
    for _ in range(2):
        with pytest.raises(RuntimeError,match='truncated'):llm.complete('p',task_id='x',purpose='base_solve')
    assert len(llm.ledger.calls)==1


def test_data_split_reproducible_and_not_math500(tmp_path):
    source=tmp_path/'source';source.mkdir()
    rows=[]
    for i in range(8):
        rows.append({'problem':f'Polynomial structure {chr(97+i)} has degree {i+2}.', 'solution':r'\boxed{2}', 'level':'Level 1','type':'Algebra'})
    for split in ['train','test']:
        with (source/(split+'.jsonl')).open('w') as f:
            for row in rows:f.write(json.dumps(row)+'\n')
    a=prepare_math(source,tmp_path/'a',seed=8,excluded_algebra=2)
    b=prepare_math(source,tmp_path/'b',seed=8,excluded_algebra=2)
    assert a==b and a['excluded']==2
    assert read_json(tmp_path/'a/train.json')['problems_hash']==read_json(tmp_path/'b/train.json')['problems_hash']
    assert read_json(tmp_path/'a/excluded_test_ids.json')['not_math500']


def test_stage0_audit_and_missing_repo(tmp_path):
    from flowevo_bot.audit import audit_sources
    with pytest.raises(FileNotFoundError):audit_sources(tmp_path/'missing',tmp_path/'also_missing')


def test_all_seven_schema_examples():
    from flowevo_bot.taxonomy import SUBJECTS
    bank=StrategyBank.load(ROOT/'data/skill_banks/schema_examples.json',allow_synthetic=True)
    assert {s.subject for s in bank.skills.values()}==set(SUBJECTS)
    assert all(s.status=='candidate' for s in bank.skills.values())


def test_native_humaneval_mbpp_preserved(tmp_path):
    import subprocess,sys
    script='''
import sys
sys.path.insert(0, 'vendor/flowevo/src')
from core.schemas import CodeTaskInstance
from code_math.runner import verify,build_prompt
from env.sandbox import Sandbox
sandbox=Sandbox(python_executable=sys.executable)
h=CodeTaskInstance(task_id='h',benchmark='humaneval',prompt='def twice(x):\\n    """Double x."""\\n',entry_point='twice',test='def check(candidate):\\n    assert candidate(3)==6\\n')
assert verify(h,'def twice(x):\\n    return x*2',sandbox)[0]
m=CodeTaskInstance(task_id='m',benchmark='mbpp',text='Double x',test_list=['assert twice(4)==8'])
assert verify(m,'def twice(x):\\n    return x*2',sandbox)[0]
assert 'Think step by step' in build_prompt(h,True)
print('native code tests passed without LLM calls')
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,text=True,capture_output=True)
    assert result.returncode==0,result.stderr


def test_feedback_exposure_detector():
    from flowevo_bot.provenance import detect_feedback_exposure,eligible
    from conftest import make_trace
    assert detect_feedback_exposure(['wrong: predicted=2, gold=8'])==(True,False)
    assert detect_feedback_exposure(['reference_solution: private answer'])==(False,True)
    trace=make_trace().model_copy(update={'prompt_texts':['Feedback: gold_answer=8']})
    assert not eligible(trace)


def test_near_duplicate_different_subjects_stay_together(tmp_path):
    source=tmp_path/'raw';source.mkdir()
    rows=[{'problem':'Find degree of polynomial 3x^2.', 'solution':r'\boxed 2','type':'Algebra','level':'Level 1'},
          {'problem':'Find degree of polynomial 5x^2.', 'solution':r'\boxed{2}','type':'Intermediate Algebra','level':'Level 2'},
          {'problem':'A genuinely different geometry exercise.', 'solution':r'\boxed{1}','type':'Geometry','level':'Level 1'}]
    for split in ['train','test']:
        (source/(split+'.jsonl')).write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    prepare_math(source,tmp_path/'split',excluded_algebra=0)
    from code_math.loader import load_manifest
    from flowevo_bot.provenance import assert_independent
    _,build,_=load_manifest(tmp_path/'split/train.json');_,dev,_=load_manifest(tmp_path/'split/dev.json')
    assert_independent(build,dev)


def test_build_bank_resume_is_content_stable(tmp_path):
    from flowevo_bot.workflows import build_bank
    config=load_config(ROOT/'configs/default.yaml')
    args=(config,ROOT/'data/manifests/train.json',ROOT/'data/manifests/dev.json',tmp_path/'bank.json')
    bank=build_bank(*args,dry_run=True)
    resumed=build_bank(*args,dry_run=True,resume=True)
    assert resumed.bank_hash==bank.bank_hash
    changed=config.model_copy(deep=True);changed.seed=9
    with pytest.raises(ValueError):build_bank(changed,*args[1:],dry_run=True,resume=True)
