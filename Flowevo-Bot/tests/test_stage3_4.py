import pytest
from conftest import make_skill,make_trace
from flowevo_bot.schemas import ProblemView,SkillRecord
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.skill_validator import SkillValidator
from flowevo_bot.skill_retriever import MathSubjectRetriever
from flowevo_bot.cost_router import MathCostAwareRouter
from flowevo_bot.provenance import assert_independent
from runtime.llm_client import LLMClient
from flowevo_bot.evaluator import Evaluator


def evidence(n=400,base=1000,skill=400,harm=0):
    return [{'task_id':f'dev_{i}','problem_hash':str(i),'problem_tokens':25,
             'base_correct':True,'skill_correct':i>=harm,'base_tokens':base,'skill_tokens':skill,
             'fallback_tokens':0,'structurally_distinct':True} for i in range(n)]


def validated(config,id='B',**kwargs):
    validator=SkillValidator(config)
    stats=validator.summarize(evidence(**kwargs),kwargs.get('n',400),synthetic=True)
    return validator.admit(make_skill(id,validation_stats=stats))


def test_admission_insufficient_and_harm(config):
    assert validated(config,n=2).status=='shadow'
    assert validated(config,harm=1).status=='quarantine'
    assert validated(config,base=400,skill=600).status=='shadow'
    assert validated(config).status=='active'


def test_build_cost_cannot_be_free(config):
    good=validated(config)
    data=good.model_dump();data.update(status='candidate',admission_certificate='',token_stats={'distillation':1000000})
    assert SkillValidator(config).admit(SkillRecord.model_validate(data)).status=='shadow'


def test_old_unproven_bank_rejected(config):
    old=make_skill(provenance=[],source_task_ids=[],source_trace_hashes=[])
    assert SkillValidator(config).admit(old).status!='active'
    with pytest.raises(ValueError):SkillRecord.model_validate({**old.model_dump(),'status':'active'})


def test_overlap_id_text_and_nearduplicate():
    source=make_trace().problem
    for target in [source,source.model_copy(update={'task_id':'other'}),
                   source.model_copy(update={'task_id':'different','problem':source.problem.replace('2x','9x')})]:
        with pytest.raises(ValueError):assert_independent([source],[target])


def test_paired_validator_actual_flow(config,tmp_path):
    import json
    sources=[make_trace(i) for i in range(3)];skill=make_skill()
    task=ProblemView(task_id='independent',subject='algebra',problem='A student studies a polynomial with exponents 2 and 9. Explain which degree governs eventual growth.')
    labels=tmp_path/'labels.jsonl';labels.write_text(json.dumps({'task_id':'independent','gold_answer':'9','reference_solution':'PRIVATE'})+'\n')
    def reply(prompt,purpose):
        return {'text':'The answer is 9.','usage':{'prompt_tokens':20,'completion_tokens':20 if 'Relevant strategy:' in prompt else 200}}
    llm=LLMClient(config.llm,mock_handler=reply)
    result=SkillValidator(config).validate(skill,sources,[task],Evaluator(labels),llm)
    assert result.status=='shadow'
    assert result.validation_stats.both_correct==1
    assert len(llm.ledger.calls)==2
    assert all(c.purpose=='skill_validation' for c in llm.ledger.calls)
    assert all('PRIVATE' not in p for p in llm.prompts)
    assert result.validation_stats.base_total_tokens>result.validation_stats.skill_total_tokens


def test_subject_filter_and_unknown(config):
    number=make_skill(subject='number_theory',trigger_features=['prime'])
    bank=StrategyBank([number],synthetic=True)
    retriever=MathSubjectRetriever(config.strategy)
    task=ProblemView(task_id='t',subject='geometry',problem='A triangle has a prime number of points.')
    assert retriever.retrieve(task,bank,active_only=False)==[]
    assert retriever.retrieve(ProblemView(task_id='u',problem='What happens next?'),bank,active_only=False)==[]
    cross=config.strategy.model_copy(update={'cross_subject_retrieval':True})
    assert MathSubjectRetriever(cross).retrieve(task,bank,active_only=False)==[number]


def test_router_selects_cheap_reliable_not_similarity(config):
    b=validated(config,'B')
    # A is active with historical positive costs, but pessimistic current predictor sees greater cost.
    a=validated(config,'A',base=800,skill=700)
    c=validated(config,'C')
    cd=c.model_dump();cd.update(status='candidate',admission_certificate='',preconditions=['nonzero'])
    c=SkillValidator(config).admit(SkillRecord.model_validate(cd))
    bank=StrategyBank([a,b,c],synthetic=True)
    router=MathCostAwareRouter(config)
    original=router.predictor.estimate
    router.predictor.estimate=lambda task,skill:({**original(task,skill),'expected_saving':-50} if skill.skill_id=='A' else original(task,skill))
    task=ProblemView(task_id='new',subject='algebra',problem='What is the degree of the polynomial 3x^9 + 2x^2 + 7 with positive coefficients?')
    decision=router.route(task,bank)
    assert decision.skill_ids==['B'] and 'C' not in decision.retrieved_skill_ids
    router.predictor.estimate=lambda task,skill:{'uncertain':True}
    assert router.route(task,bank).route=='base'


def test_default_router_rejects_small_sample_uncertainty(config):
    b=validated(config,n=10)
    assert b.status=='active'  # admission != confidence sufficient for cost-aware routing
    task=ProblemView(task_id='new',subject='algebra',problem='Find the degree of the polynomial 3x^9 + 2x^2 + 7.')
    assert MathCostAwareRouter(config).route(task,StrategyBank([b],synthetic=True)).route=='base'


def test_freeze_and_lifecycle(config):
    bank=StrategyBank([validated(config)],synthetic=True,frozen=True)
    with pytest.raises(RuntimeError):bank.transition('B','retired')
    bank.frozen=False
    assert bank.maintain('B',harmful_cases=1,observed_net_saving=20,minimum_observations_met=True)=='quarantine'
    assert bank.skills['B'].status=='quarantine'
