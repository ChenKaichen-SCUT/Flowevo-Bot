"""Paired train-dev validation after complete gold-blind submissions are sealed."""
import math
import statistics
from .common import digest, now
from .schemas import ValidationStats, SkillRecord
from .features import matches, extract_features, normalize_problem
from .provenance import assert_clean_traces, assert_independent
from .token_accounting import estimate_tokens


def wilson(successes, n, z=1.96):
    if not n: return (0.,1.)
    p=successes/n; d=1+z*z/n
    mid=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,mid-half),min(1,mid+half)


class SkillValidator:
    def __init__(self, config):
        self.config = config

    def validate(self, skill, sources, dev_problems, evaluator, client):
        from .math_solver import MathSolver
        from .strategy_bank import StrategyBank
        assert_clean_traces(sources,self.config.admission.min_source_traces)
        if {t.problem.task_id for t in sources} != set(skill.source_task_ids):
            raise ValueError('Validation must carry original source traces')
        if {t.trace_hash for t in sources} != set(skill.source_trace_hashes):
            raise ValueError('Source trace hash mismatch')
        assert_independent([t.problem for t in sources], dev_problems)
        eligible = [p for p in dev_problems if p.subject==skill.subject and matches(skill,extract_features(p))]
        # Do not inflate validation confidence using numeric-only copies of a dev question.
        unique = {}
        for problem in eligible:
            unique.setdefault(normalize_problem(problem.problem, True), problem)
        eligible = list(unique.values())
        bank = StrategyBank([skill], synthetic=client.simulated, frozen=True)
        base_solver = MathSolver(client,self.config,bank,'base_onepass')
        skill_solver = MathSolver(client,self.config,bank,'subject_strategy')
        pairs=[]; submissions=[]
        for task in eligible:
            base = base_solver.solve(task,split='train-dev',purpose='skill_validation')
            augmented = skill_solver.solve(task,split='train-dev',purpose='skill_validation')
            submissions.extend([base,augmented]);pairs.append((task,base,augmented))
        scores=evaluator.score(submissions)
        rows=[]
        for idx,(task,base,aug) in enumerate(pairs):
            bc=[c for c in client.ledger.calls if c.call_id in base.call_ids]
            sc=[c for c in client.ledger.calls if c.call_id in aug.call_ids]
            rows.append({'task_id':task.task_id,'problem_hash':digest(normalize_problem(task.problem)),
                'problem_tokens':estimate_tokens(task.problem),
                'base_correct':scores[2*idx]['final_correct'],'skill_correct':scores[2*idx+1]['final_correct'],
                'base_tokens':sum(c.total_tokens for c in bc),'skill_tokens':sum(c.total_tokens for c in sc),
                'base_input_tokens':sum(c.prompt_tokens for c in bc),'base_output_tokens':sum(c.completion_tokens for c in bc),
                'skill_input_tokens':sum(c.prompt_tokens for c in sc),'skill_output_tokens':sum(c.completion_tokens for c in sc),
                'fallback_tokens':sum(c.total_tokens for c in sc if c.purpose=='retry'),
                'calls':len(bc)+len(sc),'base_seal':base.seal,'skill_seal':aug.seal,
                'structurally_distinct':all(normalize_problem(task.problem,True)!=normalize_problem(t.problem.problem,True) for t in sources)})
        stats=self.summarize(rows,len(dev_problems),client.simulated)
        validation_cost=sum(r['base_tokens']+r['skill_tokens'] for r in rows)
        data=skill.model_dump()
        data.update(validation_stats=stats.model_dump(), token_stats={**skill.token_stats,'validation':validation_cost},
                    estimated_coverage=len(eligible)/max(1,len(dev_problems)), status='shadow', admission_certificate='')
        return self.admit(SkillRecord.model_validate(data))

    def summarize(self, rows, total, synthetic=False):
        n=len(rows)
        harm=sum(r['base_correct'] and not r['skill_correct'] for r in rows)
        benefit=sum(not r['base_correct'] and r['skill_correct'] for r in rows)
        savings=[r['base_tokens']-r['skill_tokens'] for r in rows]
        mean=statistics.mean(savings) if n else 0
        lower=mean-1.96*statistics.stdev(savings)/math.sqrt(n) if n>1 else 0
        return ValidationStats(eligible_cases=n,total_cases=total,
            both_correct=sum(r['base_correct'] and r['skill_correct'] for r in rows),
            base_only_correct=harm,skill_only_correct=benefit,
            both_wrong=sum(not r['base_correct'] and not r['skill_correct'] for r in rows),
            base_total_tokens=sum(r['base_tokens'] for r in rows),skill_total_tokens=sum(r['skill_tokens'] for r in rows),
            fallback_tokens=sum(r['fallback_tokens'] for r in rows), independent=True,synthetic=synthetic,
            evidence_hash=digest(rows), confidence=n/(n+10), accuracy_delta=(benefit-harm)/max(1,n),
            accuracy_delta_lower_bound=wilson(benefit,n)[0]-wilson(harm,n)[1],
            saving_lower_bound=lower, structurally_distinct_cases=sum(r['structurally_distinct'] for r in rows),pairwise=rows)

    def admit(self, skill):
        a=self.config.admission;s=skill.validation_stats
        clean=(len(set(skill.source_task_ids))>=a.min_source_traces and len(skill.provenance)==len(skill.source_task_ids)
               and all(p.eligible_for_skill_learning for p in skill.provenance)
               and len(skill.source_trace_hashes)==len(skill.source_task_ids))
        independent=s.independent and s.evidence_hash==digest(s.pairwise) and bool(s.pairwise)
        if a.require_independent_validation and not independent:
            state='quarantine'
        elif a.reject_observed_harmful_patterns and s.base_only_correct:
            state='quarantine'
        elif not clean or s.eligible_cases<a.min_dev_eligible_cases or s.structurally_distinct_cases==0:
            state='shadow' if a.allow_shadow_candidates else 'candidate'
        else:
            saving=(s.base_total_tokens-s.skill_total_tokens)/max(1,s.eligible_cases)
            overhead=sum(skill.token_stats.values())
            positive=(s.saving_lower_bound>0 and saving*a.expected_future_uses>overhead)
            state='active' if (positive or not a.require_positive_net_saving) else 'shadow'
        per_use=(s.base_total_tokens-s.skill_total_tokens)/max(1,s.eligible_cases)
        data=skill.model_dump()
        data.update(status='shadow',admission_certificate='',updated_at=now(),
            estimated_net_saving=per_use*a.expected_future_uses-sum(skill.token_stats.values()))
        prepared=SkillRecord.model_validate(data)
        data.update(status=state,admission_certificate=prepared.certificate() if state=='active' else '')
        return SkillRecord.model_validate(data)
