"""BoT-inspired multi-trace abstraction; never feeds reference answers to a model."""
import json
import re
from .common import digest, now
from .features import extract_features, PATTERNS
from .schemas import SkillRecord, ValidationStats
from .provenance import assert_clean_traces, eligible
from .token_accounting import estimate_tokens

GENERIC = {'check the answer', 'think step by step', 'read carefully', '仔细审题', '逐步分析', '检查答案'}


def cluster_traces(traces, minimum=3):
    groups = {}
    for t in traces:
        if not eligible(t):
            continue
        features = extract_features(t.problem)
        if not t.problem.subject or not features:
            continue
        # Shared structural signature, with optional preliminary strategy tags.
        transformations = tuple(term for term in ('factor', 'collect', 'substitut', 'congruen', 'reduce', 'partition', 'similar')
                                if re.search(term, t.first_solution, re.I))
        key = (t.problem.subject, tuple(sorted(features)), tuple(sorted(t.strategy_tags)), transformations)
        groups.setdefault(key, []).append(t)
    clusters = []
    for group in groups.values():
        unique = {t.problem.task_id:t for t in group}
        if len(unique) >= minimum:
            candidate = list(unique.values())
            assert_clean_traces(candidate, minimum)
            clusters.append(candidate)
    return clusters


class ThoughtDistiller:
    def __init__(self, client, config):
        self.client, self.config = client, config

    def distill(self, traces, existing=(), *, purpose='distillation', revision_note=''):
        assert_clean_traces(traces, self.config.distillation.min_source_traces)
        subjects = {t.problem.subject for t in traces}
        common = set.intersection(*(set(extract_features(t.problem)) for t in traces))
        if len(subjects) != 1 or None in subjects or not common:
            return None
        # No correctness feedback, reference_solution, or EvaluationRecord is serialized here.
        visible = [{'task_id': t.problem.task_id, 'problem':t.problem.problem,
                    'model_first_solution':t.first_solution} for t in traces]
        instructions = {
            'task':'Abstract one medium-grained reusable mathematical strategy from these clean first-pass model solutions.',
            'constraints': [
                'Separate general transformations from source-specific numbers. Do not quote source answers.',
                'Return {"no_generalizable_skill":true} when no substantive common strategy exists.',
                'Use 2-5 concrete strategy_steps, observable triggers, necessary preconditions, negative_triggers, verification_rules.',
                'compact_prompt must preserve ALL preconditions and exceptions; do not truncate; limit approximately 100 tokens.',
                'Generic advice like think step by step is not a mathematical strategy.',
                'A bracketed problem operator is an unconfirmed name, never assume a factorization algorithm.'
            ],
            'subject':traces[0].problem.subject, 'observable_common_features':sorted(common),
            'feature_vocabulary': sorted(PATTERNS), 'existing_strategy_names':[s.name for s in existing],
            'required_fields':['skill_id','version','subject','strategy_pattern','name','trigger_features','preconditions',
                               'negative_triggers','strategy_steps','verification_rules','composition_tags','compact_prompt','optional_executor'],
            'revision_note':revision_note, 'examples':visible,
        }
        response = self.client.complete(json.dumps(instructions, ensure_ascii=False),
            task_id='cluster_' + digest([t.trace_hash for t in traces])[:16], purpose=purpose, route='distill')
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('\n',1)[1].rsplit('```',1)[0]
        payload = json.loads(text)
        if payload.get('no_generalizable_skill') is True:
            return None
        payload.update(source_task_ids=[t.problem.task_id for t in traces],
            source_trace_hashes=[t.trace_hash for t in traces], provenance=[t.provenance.model_dump() for t in traces],
            status='candidate', admission_certificate='', validation_stats={},
            token_stats={'trace_generation': sum(c.total_tokens for t in traces for c in t.calls),
                         'distillation':response.call.total_tokens}, estimated_coverage=0, estimated_net_saving=None)
        skill = SkillRecord.model_validate(payload)
        if skill.subject != traces[0].problem.subject:
            raise ValueError('Distiller changed source subject')
        if not set(skill.trigger_features) <= common or not set(skill.preconditions + skill.negative_triggers) <= set(PATTERNS):
            raise ValueError('Distiller proposed an unobservable or unsupported feature')
        if all(step.strip().lower().rstrip('.') in GENERIC for step in skill.strategy_steps):
            raise ValueError('No substantive mathematical strategy')
        if estimate_tokens(skill.compact_prompt) > self.config.strategy.max_skill_prompt_tokens:
            raise ValueError('Compact strategy exceeds budget; revise and validate, never truncate')
        # All machine-readable required conditions must survive compression.
        for feature in skill.preconditions + skill.negative_triggers:
            if feature.replace('_', ' ') not in skill.compact_prompt.lower():
                raise ValueError('Compact prompt omitted a declared precondition or exception')
        return skill

    def revise(self, skill, traces, note):
        candidate = self.distill(traces, purpose='skill_revision', revision_note=note)
        if candidate is None:
            return None
        return candidate.model_copy(update={'skill_id':skill.skill_id,'version':skill.version+1,
            'updated_at':now(), 'validation_stats':ValidationStats(), 'status':'candidate',
            'admission_certificate':'', 'token_stats':{
                **skill.token_stats, 'skill_revision':candidate.token_stats['distillation']}})
