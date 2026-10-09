import json
import pytest
from pydantic import ValidationError
from conftest import make_trace,make_skill
from flowevo_bot.schemas import SkillRecord
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.thought_distiller import cluster_traces,ThoughtDistiller
from flowevo_bot.mock import mock_response
from runtime.llm_client import LLMClient


def test_schema_roundtrip_and_unknown_status(skill):
    assert SkillRecord.model_validate_json(skill.model_dump_json())==skill
    with pytest.raises(ValidationError):SkillRecord.model_validate({**skill.model_dump(),'status':'published'})
    with pytest.raises(ValidationError):SkillRecord.model_validate({**skill.model_dump(),'status':'active'})


def test_multi_trace_distillation(config):
    traces=[make_trace(i) for i in range(3)]
    groups=cluster_traces(traces)
    assert len(groups)==1
    client=LLMClient(config.llm,mock_handler=mock_response)
    skill=ThoughtDistiller(client,config).distill(groups[0])
    assert skill.status=='candidate' and len(skill.source_task_ids)==3
    assert len(client.ledger.calls)==1
    assert 'gold_answer' not in client.prompts[0]
    assert 'reference_solution' not in client.prompts[0]
    assert 'first_pass_correct' not in client.prompts[0]


def test_unrelated_and_too_few(config):
    assert cluster_traces([make_trace(0),make_trace(1)])==[]
    unrelated=[make_trace(0),make_trace(1,subject='geometry',problem='A triangle has area 4.'),
               make_trace(2,subject='number_theory',problem='Find a prime divisor.')]
    assert cluster_traces(unrelated)==[]
    client=LLMClient(config.llm,mock_handler=mock_response)
    assert ThoughtDistiller(client,config).distill(unrelated) is None
    assert not client.ledger.calls


def test_no_generalization_response(config):
    client=LLMClient(config.llm,mock_handler=lambda p,k:'{"no_generalizable_skill":true}')
    assert ThoughtDistiller(client,config).distill([make_trace(i) for i in range(3)]) is None


def test_duplicate_merge_needs_revalidation(skill,tmp_path):
    bank=StrategyBank([skill],synthetic=True)
    duplicate=make_skill('degree-copy')
    assert bank.duplicate(duplicate)==skill.skill_id
    merged=bank.merge([skill.skill_id],duplicate)
    assert merged.status=='candidate' and not merged.validation_stats.independent
    assert bank.skills[skill.skill_id].status=='retired'
    path=tmp_path/'bank.json';bank.save(path)
    assert StrategyBank.load(path,allow_synthetic=True).bank_hash==bank.bank_hash
    with pytest.raises(ValueError):StrategyBank.load(path)
    data=json.loads(path.read_text());data['skills'][0]['compact_prompt']='tampered';path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='hash'):StrategyBank.load(path,allow_synthetic=True)


def test_contaminated_trace_excluded(config):
    t=make_trace(0)
    tainted=t.model_copy(update={'provenance':t.provenance.model_copy(update={'gold_exposed':True,'eligible_for_skill_learning':False})})
    assert cluster_traces([tainted,make_trace(1),make_trace(2)])==[]
    with pytest.raises(ValueError):ThoughtDistiller(LLMClient(config.llm,mock_handler=mock_response),config).distill([tainted,make_trace(1),make_trace(2)])


def test_oversize_not_truncated(config):
    def oversized(prompt,purpose):
        data=json.loads(mock_response(prompt,purpose));data['compact_prompt']='polynomial '*200
        return json.dumps(data)
    with pytest.raises(ValueError,match='budget'):
        ThoughtDistiller(LLMClient(config.llm,mock_handler=oversized),config).distill([make_trace(i) for i in range(3)])
