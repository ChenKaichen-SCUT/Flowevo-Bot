import json
import pytest
from pathlib import Path
from conftest import make_skill
from flowevo_bot.schemas import ProblemView,Submission,EvaluationRecord
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.math_solver import MathSolver
from flowevo_bot.evaluator import Evaluator,verify,extract_answer,normalize
from flowevo_bot.token_accounting import TokenLedger,amortized_cost
from flowevo_bot.checkpoint import Checkpoint
from flowevo_bot.data import write_manifest
from flowevo_bot.workflows import evaluate_manifest
from runtime.llm_client import LLMClient
from runtime.config import MODES
from flowevo_bot.common import digest


def test_gold_canary_through_router_retry_bank_and_evaluator(config,tmp_path):
    canary='SECRET_GOLD_CANARY_9bc88'
    labels=tmp_path/'labels.jsonl'
    labels.write_text(json.dumps({'task_id':'test','gold_answer':canary,'reference_solution':canary})+'\n')
    evaluator=Evaluator(labels)
    answers=iter(['Missing final answer line.','The answer is 6.'])
    client=LLMClient(config.llm,mock_handler=lambda p,k:next(answers))
    bank=StrategyBank([make_skill()],synthetic=True,frozen=True)
    solver=MathSolver(client,config,bank,'subject_strategy')
    task=ProblemView(task_id='test',problem='Find the degree of the polynomial 4x^6 + 2x^2.',subject='algebra')
    s=solver.solve(task)
    assert s.retry_count==1 and evaluator.read_count==0
    visible=json.dumps([client.prompts,solver.router_inputs,bank.payload(),s.model_dump()])
    assert canary not in visible
    assert not s.provenance.gold_exposed
    cp=Checkpoint(tmp_path/'sealed',config=config,bank_hash=bank.bank_hash,split='test',
                  mode='subject_strategy',manifest_hash='canary-fixture',simulated=True)
    cp.commit(s)
    assert canary not in cp.path.read_text()
    score=evaluator.score([s])[0]
    assert not score['final_correct'] and canary not in json.dumps(score)
    assert len(client.ledger.calls)==2  # evaluation did not induce another call
    assert verify('6',EvaluationRecord(task_id='test',gold_answer=canary))==(False,'incorrect')
    with pytest.raises(ValueError):evaluator.score([s.model_copy(update={'seal':''})])


def test_wrong_but_formatted_answer_never_triggers_gold_retry(config):
    client=LLMClient(config.llm,mock_handler=lambda p,k:'The answer is 999.')
    solver=MathSolver(client,config,StrategyBank(synthetic=True),'flowevo_goldfree')
    s=solver.solve(ProblemView(task_id='x',problem='Compute 2+2.'))
    assert s.retry_count==0 and len(client.ledger.calls)==1


def test_usage_missing_counted_and_cached(config,tmp_path):
    ledger=TokenLedger(tmp_path/'calls.json')
    client=LLMClient(config.llm,ledger,mock_handler=lambda p,k:'The answer is 4.')
    r=client.complete('Compute 2+2.',task_id='a',purpose='base_solve')
    assert r.call.estimated and r.call.total_tokens>0
    client.complete('Compute 2+2.',task_id='a',purpose='base_solve')
    assert len(ledger.calls)==1
    client.complete('Compute 2+2.',task_id='b',purpose='base_solve')
    assert len(ledger.calls)==2
    assert ledger.totals()['total_tokens']==sum(c.total_tokens for c in ledger.calls)
    assert len(TokenLedger(tmp_path/'calls.json').calls)==2


def test_real_usage_preferred(config):
    client=LLMClient(config.llm,mock_handler=lambda p,k:{'text':'ok','usage':{'prompt_tokens':19,'completion_tokens':7}})
    c=client.complete('hello',task_id='a',purpose='base_solve').call
    assert (c.prompt_tokens,c.completion_tokens,c.total_tokens,c.estimated)==(19,7,26,False)


def test_checkpoint_binding_and_idempotency(config,tmp_path):
    bank=StrategyBank(synthetic=True)
    solver=MathSolver(LLMClient(config.llm,mock_handler=lambda p,k:'The answer is 4.'),config,bank,'base_onepass')
    s=solver.solve(ProblemView(task_id='a',problem='Compute 2+2.'))
    kwargs=dict(config=config,bank_hash=bank.bank_hash,split='test',mode='base_onepass',manifest_hash='manifest',simulated=True)
    path=tmp_path/'run';cp=Checkpoint(path,**kwargs);cp.commit(s);cp.commit(s)
    assert len(Checkpoint(path,**kwargs,resume=True).records)==1
    for changes in [{'bank_hash':'bad'},{'split':'train-dev'},{'manifest_hash':'bad'},{'mode':'subject_strategy'}]:
        with pytest.raises(ValueError):Checkpoint(path,**{**kwargs,**changes},resume=True)
    new=config.model_copy(deep=True);new.seed+=1
    with pytest.raises(ValueError):Checkpoint(path,**{**kwargs,'config':new},resume=True)
    with pytest.raises(FileExistsError):Checkpoint(path,**kwargs)


def test_interrupted_resume_does_not_repeat_finished_tasks(config,tmp_path,monkeypatch):
    tasks=[ProblemView(task_id=str(i),problem=f'Compute {i}+2.') for i in range(2)]
    labels=[EvaluationRecord(task_id=str(i),gold_answer=str(i+2)) for i in range(2)]
    manifest=write_manifest(tmp_path/'data','test','test',tasks,labels,synthetic=True)
    calls=[]
    def interrupted(prompt,purpose):
        calls.append(prompt)
        if 'Compute 1+2.' in prompt:raise RuntimeError('simulated process interruption')
        return 'The answer is 2.'
    monkeypatch.setattr('flowevo_bot.workflows.mock_response',interrupted)
    bank=StrategyBank(synthetic=True)
    with pytest.raises(RuntimeError):evaluate_manifest(config,manifest,bank,'base_onepass',tmp_path/'run',dry_run=True)
    assert len(json.loads((tmp_path/'run/checkpoint.json').read_text())['submissions'])==1
    before=len(calls)
    def resumed(prompt,purpose):calls.append(prompt);return 'The answer is 3.'
    monkeypatch.setattr('flowevo_bot.workflows.mock_response',resumed)
    summary,_=evaluate_manifest(config,manifest,bank,'base_onepass',tmp_path/'run',dry_run=True,resume=True)
    assert summary['accuracy']==1 and len(calls)==before+1
    evaluate_manifest(config,manifest,bank,'base_onepass',tmp_path/'run',dry_run=True,resume=True)
    assert len(calls)==before+1


@pytest.mark.parametrize('mode',MODES)
def test_all_modes_offline(config,mode):
    from flowevo_bot.mock import mock_response
    solver=MathSolver(LLMClient(config.llm,mock_handler=mock_response),config,StrategyBank(synthetic=True),mode)
    s=solver.solve(ProblemView(task_id='x',problem='Compute 3+4.'))
    assert s.final_answer=='7' and not s.provenance.gold_exposed


def test_answer_extraction_nested_fraction_and_decimal():
    assert extract_answer(r'Answer: \boxed{\frac{1}{2}}')==r'\frac{1}{2}'
    assert normalize(r'\frac{1}{2}')==normalize('0.5')
    assert extract_answer('The answer is 1.25.')=='1.25'
    assert normalize('(1,2)')!=normalize('(12)')


def test_verified_execution_has_narrow_scope(config):
    config.router.enable_verified_execution=True
    client=LLMClient(config.llm,mock_handler=lambda p,k:'The answer is 0.')
    solver=MathSolver(client,config,StrategyBank(synthetic=True),'subject_strategy_costaware')
    s=solver.solve(ProblemView(task_id='x',problem='Compute (3+5)/2.'))
    assert s.decision.route=='execution' and s.final_answer=='4' and not client.ledger.calls
    s=solver.solve(ProblemView(task_id='y',problem='Compute 3+5 and explain whether a triangle exists.'))
    assert s.decision.route=='base' and len(client.ledger.calls)==1


def test_budget_fails_before_transport(config):
    config.llm.max_calls=1
    client=LLMClient(config.llm,mock_handler=lambda p,k:'The answer is 4.')
    client.complete('a',task_id='a',purpose='base_solve')
    with pytest.raises(RuntimeError,match='budget'):client.complete('b',task_id='b',purpose='base_solve')
