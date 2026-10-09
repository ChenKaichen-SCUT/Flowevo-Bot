import pytest
from pydantic import ValidationError
from flowevo_bot.schemas import ProblemView
from flowevo_bot.taxonomy import normalize_subject, SUBJECTS
from code_math.baseline import base_prompt
from runtime.llm_client import LLMClient
from runtime.config import Config

@pytest.mark.parametrize('raw,expected', list(zip(['Prealgebra','Algebra','Intermediate Algebra','Geometry','Number Theory','Counting & Probability','Precalculus'], SUBJECTS)))
def test_taxonomy(raw, expected):
    assert normalize_subject(raw) == expected


def test_base_and_no_network():
    p = ProblemView(task_id='1', problem='Compute 2+2.')
    assert base_prompt(p) == 'Problem: Compute 2+2.\n\nSolve step by step. End with: The answer is [your answer].'
    llm = LLMClient(Config().llm, mock_handler=lambda prompt, purpose:'The answer is 4.')
    r = llm.complete(base_prompt(p), task_id='1', purpose='base_solve')
    assert r.text.endswith('4.') and r.call.estimated and r.call.simulated
    assert r.call.total_tokens > 0
    with pytest.raises(PermissionError):
        LLMClient(Config().llm).complete('test', task_id='1', purpose='base_solve')


def test_problem_rejects_gold():
    with pytest.raises(ValidationError):
        ProblemView(task_id='1',problem='?',public_metadata={'gold_answer':'CANARY'})
    with pytest.raises(ValidationError):
        ProblemView(task_id='1',problem='?',gold_answer='CANARY')
