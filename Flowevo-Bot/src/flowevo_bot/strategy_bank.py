"""Content-addressed, split-bound, versioned strategy bank with explicit lifecycle."""
from difflib import SequenceMatcher
from .common import digest, now, read_json, write_json
from .schemas import SkillRecord, ValidationStats, Trace, TokenCall


class StrategyBank:
    def __init__(self, skills=(), *, version=1, origin_split='train-build', synthetic=False, frozen=False):
        if origin_split != 'train-build':
            raise ValueError('Bank origin must be train-build')
        self.skills = {s.skill_id: SkillRecord.model_validate(s.model_dump()) for s in skills}
        if len(self.skills) != len(list(skills)):
            raise ValueError('Duplicate skill ID')
        self.version, self.origin_split = version, origin_split
        self.synthetic, self.frozen = synthetic, frozen
        self.history = []
        self.cost_calls = []
        self.build_costs = {}

    def payload(self):
        return {'schema_version': '1.0', 'version': self.version, 'origin_split': self.origin_split,
                'synthetic': self.synthetic, 'skills': [s.model_dump(mode='json') for s in sorted(self.skills.values(), key=lambda s:s.skill_id)],
                'history': [t.model_dump(mode='json') for t in self.history],
                'cost_calls': [c.model_dump(mode='json') for c in self.cost_calls], 'build_costs':self.build_costs}

    @property
    def bank_hash(self):
        return digest(self.payload())

    def save(self, path):
        payload = self.payload()
        write_json(path, {**payload, 'bank_hash': digest(payload)})

    @classmethod
    def load(cls, path, *, frozen=True, allow_synthetic=False):
        data = read_json(path)
        recorded = data.pop('bank_hash')
        if digest(data) != recorded:
            raise ValueError('Bank hash mismatch')
        if data['schema_version'] != '1.0':
            raise ValueError('Unsupported bank schema')
        if data['synthetic'] and not allow_synthetic:
            raise ValueError('Mock bank cannot be used for real inference')
        bank = cls([SkillRecord.model_validate(s) for s in data['skills']], version=data['version'],
                   origin_split=data['origin_split'], synthetic=data['synthetic'], frozen=frozen)
        bank.history = [Trace.model_validate(t) for t in data.get('history', [])]
        bank.cost_calls = [TokenCall.model_validate(c) for c in data.get('cost_calls', [])]
        bank.build_costs = data.get('build_costs', {})
        if len({c.call_id for c in bank.cost_calls}) != len(bank.cost_calls):
            raise ValueError('Duplicate build cost call')
        from .provenance import eligible
        if any(not eligible(t) for t in bank.history):
            raise ValueError('Untrusted history in bank')
        return bank

    def add(self, skill):
        if self.frozen:
            raise RuntimeError('Bank is frozen')
        skill = SkillRecord.model_validate(skill.model_dump())
        if not self.synthetic and (skill.validation_stats.synthetic or any(p.synthetic for p in skill.provenance)):
            raise ValueError('Synthetic evidence cannot enter a real bank')
        self.skills[skill.skill_id] = skill
        self.version += 1

    def duplicate(self, skill):
        for old in self.skills.values():
            if old.subject != skill.subject or old.status == 'retired':
                continue
            a, b = set(old.trigger_features), set(skill.trigger_features)
            overlap = len(a & b) / max(1, len(a | b))
            similarity = SequenceMatcher(None, ' '.join(old.strategy_steps), ' '.join(skill.strategy_steps)).ratio()
            if overlap >= .6 and similarity >= .75:
                return old.skill_id
        return None

    def merge(self, ids, proposed):
        if self.frozen:
            raise RuntimeError('Bank is frozen')
        originals = [self.skills[i] for i in ids]
        if any(s.subject != proposed.subject for s in originals):
            raise ValueError('Cross-subject merge requires manual review')
        provenances = {p.source_task_id:p for s in originals for p in s.provenance}
        hashes = {tid:h for s in originals for tid,h in zip(s.source_task_ids,s.source_trace_hashes)}
        data = proposed.model_dump()
        data.update(status='candidate', version=max(s.version for s in originals)+1,
                    validation_stats=ValidationStats().model_dump(), admission_certificate='',
                    source_task_ids=list(hashes), source_trace_hashes=list(hashes.values()),
                    provenance=[p.model_dump() for p in provenances.values()], updated_at=now(),
                    estimated_coverage=0, estimated_net_saving=None)
        merged = SkillRecord.model_validate(data)
        self.add(merged)
        for old in originals:
            if old.skill_id != merged.skill_id:
                self.transition(old.skill_id, 'retired')
        return merged

    def split(self, skill_id, proposals):
        original = self.skills[skill_id]
        children = []
        for proposal in proposals:
            if not set(proposal.trigger_features) <= set(original.trigger_features):
                raise ValueError('Split must narrow the original trigger range')
            child = proposal.model_copy(update={'status':'candidate','admission_certificate':'',
                'validation_stats':ValidationStats(), 'version':original.version+1,
                'source_task_ids':original.source_task_ids, 'source_trace_hashes':original.source_trace_hashes,
                'provenance':original.provenance, 'estimated_net_saving':None, 'estimated_coverage':0})
            self.add(child)
            children.append(child)
        self.transition(skill_id, 'quarantine')
        return children

    def transition(self, skill_id, status):
        if status == 'active':
            raise ValueError('Activation requires validator admission, not a manual transition')
        old = self.skills[skill_id]
        self.add(old.model_copy(update={'status':status, 'updated_at':now(), 'admission_certificate':''}))

    def maintain(self, skill_id, *, harmful_cases, observed_net_saving, minimum_observations_met):
        # Only training/dev maintenance; evaluation never calls this on frozen banks.
        if harmful_cases:
            self.transition(skill_id, 'quarantine')
            return 'quarantine'
        if minimum_observations_met and observed_net_saving <= 0:
            self.transition(skill_id, 'retired')
            return 'retire'
        return 'retain'
