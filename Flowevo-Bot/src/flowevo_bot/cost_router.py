"""No LLM call and no gold input. Conservative estimates from paired dev evidence."""
from .schemas import RouteDecision
from .taxonomy import detect_subject
from .skill_retriever import MathSubjectRetriever
from .token_accounting import estimate_tokens


class CostPredictor:
    def __init__(self, config):
        self.config = config

    def estimate(self, task, skill):
        s = skill.validation_stats
        n = s.eligible_cases
        if n < self.config.admission.min_dev_eligible_cases or not s.independent:
            return {'uncertain':True, 'reason':'insufficient independent dev evidence'}
        if not s.pairwise:
            return {'uncertain':True, 'reason':'missing per-task evidence'}
        lengths = [row['problem_tokens'] for row in s.pairwise]
        length = estimate_tokens(task.problem)
        if length < min(lengths)*.5 or length > max(lengths)*2:
            return {'uncertain':True, 'reason':'query length outside calibrated range'}
        base = s.base_total_tokens/n
        skilled = s.skill_total_tokens/n  # already includes strategy and fallback
        return {'uncertain':s.confidence < self.config.router.min_confidence,
                'predicted_base_total_tokens':base, 'predicted_skill_total_tokens':skilled,
                'predicted_accuracy_change':s.accuracy_delta,
                'predicted_accuracy_drop_upper':max(0,-s.accuracy_delta_lower_bound),
                'predicted_fallback_cost':s.fallback_tokens/n,
                'expected_saving':base-skilled, 'saving_lower_bound':s.saving_lower_bound,
                'confidence':s.confidence, 'method':'paired_dev_means_with_conservative_bounds'}


class MathCostAwareRouter:
    def __init__(self, config):
        self.config = config
        self.retriever = MathSubjectRetriever(config.strategy)
        self.predictor = CostPredictor(config)

    def route(self, task, bank):
        subject, origin = detect_subject(task)
        if not self.config.strategy.enabled:
            return RouteDecision(route='base',subject=subject,subject_source=origin,reason='strategy disabled')
        candidates = self.retriever.retrieve(task, bank, active_only=True)
        estimates = {s.skill_id:self.predictor.estimate(task,s) for s in candidates}
        viable = []
        for skill in candidates:
            e = estimates[skill.skill_id]
            if e.get('uncertain',True) or e.get('expected_saving',0) <= 0 or e.get('saving_lower_bound',0) <= 0:
                continue
            if e['predicted_accuracy_drop_upper'] > self.config.router.max_allowed_accuracy_drop:
                continue
            viable.append((e['expected_saving'],skill.skill_id))
        if not viable:
            return RouteDecision(route='base',subject=subject,subject_source=origin,
                retrieved_skill_ids=[s.skill_id for s in candidates], estimates=estimates,
                reason='no reliable positive saving within correctness risk budget')
        selected = sorted(viable, key=lambda x:(-x[0],x[1]))[0][1]
        # Pairwise costs support one skill. Joint combinations require joint validation.
        return RouteDecision(route='strategy',subject=subject,subject_source=origin,
            skill_ids=[selected], retrieved_skill_ids=[s.skill_id for s in candidates], estimates=estimates,
            reason='largest validated positive saving within risk budget')
