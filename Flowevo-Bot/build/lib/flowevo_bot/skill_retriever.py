from .features import extract_features, matches
from .taxonomy import detect_subject
from .token_accounting import estimate_tokens


class MathSubjectRetriever:
    def __init__(self, config):
        self.config = config

    def retrieve(self, task, bank, *, active_only=True):
        subject, _ = detect_subject(task)
        if subject is None:
            return []
        features = extract_features(task)
        candidates = []
        for skill in bank.skills.values():
            if active_only and skill.status != 'active':
                continue
            if skill.status in ('quarantine', 'retired'):
                continue
            if self.config.subject_routing and not self.config.cross_subject_retrieval and skill.subject != subject:
                continue
            if task.task_id in skill.source_task_ids or not matches(skill, features):
                continue
            if estimate_tokens(skill.compact_prompt) > self.config.max_skill_prompt_tokens:
                continue
            score = len(set(skill.trigger_features) & features) / len(set(skill.trigger_features) | features)
            candidates.append((score, skill.skill_id, skill))
        return [s for _, _, s in sorted(candidates, key=lambda x:(-x[0],x[1]))[:self.config.top_k]]
