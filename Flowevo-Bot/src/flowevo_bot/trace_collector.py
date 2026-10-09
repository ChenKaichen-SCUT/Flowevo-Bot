"""Only train-build, sealed, independently evaluated first attempts are learnable."""
from .schemas import Trace, Provenance
from .common import digest
from .provenance import detect_feedback_exposure


def collect_trace(problem, submission, evaluation, calls, prompts=(), strategy_tags=()):
    submission.assert_frozen()
    if evaluation['task_id'] != problem.task_id or submission.task_id != problem.task_id:
        raise ValueError('Trace IDs disagree')
    p = submission.provenance
    detected_gold,detected_reference=detect_feedback_exposure(prompts)
    exposed_gold=p.gold_exposed or detected_gold
    exposed_reference=p.reference_solution_exposed or detected_reference
    clean = (submission.split == 'train-build' and not exposed_gold
             and not exposed_reference and evaluation['first_pass_correct'])
    provenance = Provenance(origin_split=submission.split, source_task_id=problem.task_id,
        first_pass=True, gold_exposed=exposed_gold,
        reference_solution_exposed=exposed_reference,
        external_verifier_used=p.external_verifier_used, eligible_for_skill_learning=clean,
        evidence_hash=digest({'submission': submission.seal, 'evaluation': evaluation}), synthetic=p.synthetic)
    return Trace(problem=problem, first_solution=submission.first_solution,
        first_answer=submission.first_answer, first_pass_correct=evaluation['first_pass_correct'],
        calls=list(calls), provenance=provenance, prompt_texts=list(prompts), strategy_tags=list(strategy_tags))
