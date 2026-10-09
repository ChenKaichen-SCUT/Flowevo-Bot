from pathlib import Path
from flowevo_bot.parallel_experiment import run_parallel
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.experiment_grader import grade_one
from flowevo_bot.common import read_json
from runtime.config import Config


def test_symbolic_grading_and_truncation():
    assert grade_one(('fraction',r'\frac{2}{4}','0.5',False))['final_correct']
    assert grade_one(('radical',r'\sqrt{8}',r'2\sqrt{2}',False))['final_correct']
    assert not grade_one(('wrong','3','2',False))['final_correct']
    assert not grade_one(('truncated','2','2',True))['final_correct']
    assert not grade_one(('absent',None,'2',False))['final_correct']


def test_parallel_isolated_ledgers_and_resume(tmp_path):
    root=Path(__file__).resolve().parents[1]
    cfg=Config();cfg.evaluation.max_format_retries=0
    bank=StrategyBank(synthetic=True,frozen=True)
    manifest=root/'data/manifests/test.json'
    first,_=run_parallel(cfg,manifest,bank,'base_onepass',tmp_path/'run',api_workers=3,local_workers=2,dry_run=True)
    second,_=run_parallel(cfg,manifest,bank,'base_onepass',tmp_path/'run',api_workers=3,local_workers=2,dry_run=True,resume=True)
    assert first==second
    assert first['count']==first['calls']==first['correct']==3
    calls=read_json(tmp_path/'run/calls.json')['calls']
    assert first['total_tokens']==sum(c['prompt_tokens']+c['completion_tokens'] for c in calls)
    assert len(list((tmp_path/'run/task_calls').glob('*.json')))==3
