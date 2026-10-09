"""No missing provenance is upgraded to clean history."""
from .features import normalize_problem, near_duplicate, duplicate_keys
from .common import digest
import re


def eligible(trace):
    p = trace.provenance
    return bool(trace.first_pass_correct and p.eligible_for_skill_learning and p.first_pass
                and p.origin_split == 'train-build' and not p.gold_exposed
                and not p.reference_solution_exposed and p.evidence_hash
                and p.source_task_id == trace.problem.task_id
                and not detect_feedback_exposure(trace.prompt_texts)[0]
                and not detect_feedback_exposure(trace.prompt_texts)[1])


def assert_clean_traces(traces, minimum=3):
    if len({t.problem.task_id for t in traces}) < minimum:
        raise ValueError('Insufficient distinct source tasks')
    if len({digest(normalize_problem(t.problem.problem)) for t in traces}) < minimum:
        raise ValueError('Duplicate source question text')
    if not all(eligible(t) for t in traces):
        raise ValueError('Trace lacks first-pass gold-free training evidence')


def assert_independent(sources, targets):
    from collections import defaultdict
    by_id = {s.task_id:s for s in sources}
    by_text = {normalize_problem(s.problem, True):s for s in sources}
    blocks = defaultdict(list)
    for source in sources:
        for key in duplicate_keys(source.problem):
            blocks[key].append(source)
    for target in targets:
        if target.task_id in by_id or normalize_problem(target.problem, True) in by_text:
            raise ValueError(f'Validation overlap or near duplicate: {target.task_id}')
        checked = set()
        for key in duplicate_keys(target.problem):
            for source in blocks[key]:
                if source.task_id not in checked and near_duplicate(source.problem, target.problem):
                    raise ValueError(f'Validation overlap or near duplicate: {target.task_id}')
                checked.add(source.task_id)


def assert_no_canary(texts, canaries):
    for text in texts:
        if any(c and c in text for c in canaries):
            raise ValueError('Gold canary detected in solver-visible data')


def detect_feedback_exposure(texts):
    text='\n'.join(texts)
    gold=bool(re.search(r'gold(?:_answer)?\s*[:=]',text,re.I))
    reference=bool(re.search(r'reference_solution\s*[:=]|ground.truth.solution\s*[:=]',text,re.I))
    return gold,reference
