import socket
import pytest
from flowevo_bot.schemas import ProblemView,Provenance,Trace,SkillRecord
from flowevo_bot.common import digest
from flowevo_bot.strategy_bank import StrategyBank
from runtime.config import Config


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*a,**kw):raise AssertionError('Tests must never access the network')
    monkeypatch.setattr(socket.socket,'connect',fail)


@pytest.fixture
def config():return Config()


def make_trace(index=0,subject='algebra',problem=None):
    prompt=problem or f'Find the degree of the polynomial {index+2}x^{index+3} + 2x^2 + 5.'
    p=ProblemView(task_id=f'source_{index}',problem=prompt,subject=subject)
    provenance=Provenance(origin_split='train-build',source_task_id=p.task_id,first_pass=True,
        gold_exposed=False,reference_solution_exposed=False,external_verifier_used=False,
        eligible_for_skill_learning=True,evidence_hash=digest(prompt),synthetic=True)
    return Trace(problem=p,first_solution=f'Collect powers. The answer is {index+3}.',first_answer=str(index+3),
                 first_pass_correct=True,calls=[],provenance=provenance)


def make_skill(skill_id='degree',**updates):
    traces=[make_trace(i) for i in range(3)]
    data=dict(skill_id=skill_id,subject='algebra',strategy_pattern='polynomial_degree',name='Polynomial degree',
        trigger_features=['polynomial'],preconditions=[],negative_triggers=[],
        strategy_steps=['Collect like powers.','Select the greatest nonzero exponent.'],
        verification_rules=['Check leading-term cancellation.'],
        compact_prompt='For a polynomial, collect like powers and check cancellation before choosing the largest exponent.',
        source_task_ids=[t.problem.task_id for t in traces],source_trace_hashes=[t.trace_hash for t in traces],
        provenance=[t.provenance for t in traces])
    data.update(updates)
    return SkillRecord(**data)


@pytest.fixture
def skill():return make_skill()
