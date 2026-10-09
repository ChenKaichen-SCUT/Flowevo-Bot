"""Versioned boundaries. Gold fields never belong to a ProblemView."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from .common import now, digest
from .taxonomy import SUBJECTS, normalize_subject

Split = Literal['train-build', 'train-dev', 'test']
Status = Literal['candidate', 'shadow', 'active', 'quarantine', 'retired']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class ProblemView(StrictModel):
    task_id: str
    problem: str
    subject: str | None = None
    level: str = ''
    public_metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator('subject')
    @classmethod
    def subject_valid(cls, v):
        if v is not None and v not in SUBJECTS:
            raise ValueError('Unknown standardized subject')
        return v

    @field_validator('public_metadata')
    @classmethod
    def public_only(cls, value):
        if set(value) - {'type', 'benchmark', 'subject_source'}:
            raise ValueError('Public metadata accepts only type/benchmark/subject_source')
        if 'type' in value and normalize_subject(value['type']) is None:
            raise ValueError('Invalid public subject metadata')
        if value.get('subject_source', 'metadata') not in {'metadata','rule','unknown'}:
            raise ValueError('Invalid subject provenance')
        if value.get('benchmark','math') not in {'math','gsm8k','humaneval','mbpp'}:
            raise ValueError('Invalid benchmark metadata')
        return value


class EvaluationRecord(StrictModel):
    task_id: str
    gold_answer: str
    reference_solution: str = ''


class Provenance(StrictModel):
    origin_split: Split
    source_task_id: str
    first_pass: bool
    gold_exposed: bool
    reference_solution_exposed: bool
    external_verifier_used: bool
    eligible_for_skill_learning: bool
    evidence_hash: str
    synthetic: bool = False

    @model_validator(mode='after')
    def valid_eligibility(self):
        if self.eligible_for_skill_learning and (
            self.origin_split != 'train-build' or not self.first_pass or self.gold_exposed
            or self.reference_solution_exposed or not self.evidence_hash
        ):
            raise ValueError('Ineligible provenance cannot authorize skill learning')
        return self


class TokenCall(StrictModel):
    call_id: str
    task_id: str
    purpose: Literal['base_solve', 'skill_solve', 'distillation', 'skill_validation', 'retry', 'skill_revision', 'trace_generation']
    model: str
    route: str
    skill_ids: list[str] = Field(default_factory=list)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    latency: float = Field(ge=0)
    estimated: bool = False
    estimation_method: str | None = None
    simulated: bool = False
    prompt_hash: str
    response_hash: str

    @model_validator(mode='after')
    def usage_consistent(self):
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError('Token totals do not reconcile')
        if self.estimated and not self.estimation_method:
            raise ValueError('Missing estimation method')
        return self


class ValidationStats(StrictModel):
    eligible_cases: int = 0
    total_cases: int = 0
    both_correct: int = 0
    base_only_correct: int = 0
    skill_only_correct: int = 0
    both_wrong: int = 0
    base_total_tokens: int = 0
    skill_total_tokens: int = 0
    fallback_tokens: int = 0
    independent: bool = False
    synthetic: bool = False
    evidence_hash: str = ''
    confidence: float = 0
    accuracy_delta: float = 0
    accuracy_delta_lower_bound: float = -1
    saving_lower_bound: float = 0
    structurally_distinct_cases: int = 0
    pairwise: list[dict] = Field(default_factory=list)


class SkillRecord(StrictModel):
    schema_version: Literal['1.0'] = '1.0'
    skill_id: str
    version: int = Field(default=1, ge=1)
    subject: str
    strategy_pattern: str
    name: str
    trigger_features: list[str] = Field(min_length=1)
    preconditions: list[str] = Field(default_factory=list)
    negative_triggers: list[str] = Field(default_factory=list)
    strategy_steps: list[str] = Field(min_length=2, max_length=5)
    verification_rules: list[str] = Field(min_length=1)
    composition_tags: list[str] = Field(default_factory=list)
    compact_prompt: str = Field(min_length=1)
    optional_executor: str | None = None
    source_task_ids: list[str] = Field(default_factory=list)
    source_trace_hashes: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    validation_stats: ValidationStats = Field(default_factory=ValidationStats)
    token_stats: dict[str, float] = Field(default_factory=dict)
    estimated_coverage: float = 0
    estimated_net_saving: float | None = None
    status: Status = 'candidate'
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    admission_certificate: str = ''

    @field_validator('subject')
    @classmethod
    def valid_subject(cls, v):
        if v not in SUBJECTS:
            raise ValueError('Invalid subject')
        return v

    @model_validator(mode='after')
    def activation_proof(self):
        if self.status == 'active':
            if not self.provenance or any(not p.eligible_for_skill_learning for p in self.provenance):
                raise ValueError('Active skill lacks clean source provenance')
            if set(self.source_task_ids) != {p.source_task_id for p in self.provenance}:
                raise ValueError('Source provenance mismatch')
            if len(self.source_trace_hashes) != len(self.source_task_ids):
                raise ValueError('Missing trace evidence')
            if not self.validation_stats.independent or not self.validation_stats.evidence_hash:
                raise ValueError('Active skill lacks independent validation')
            if self.admission_certificate != self.certificate():
                raise ValueError('Admission certificate is absent or stale')
        return self

    def certificate(self):
        data = self.model_dump(mode='json')
        for key in ['status', 'updated_at', 'admission_certificate']:
            data.pop(key)
        return digest(data)


class Trace(StrictModel):
    problem: ProblemView
    first_solution: str
    first_answer: str | None
    first_pass_correct: bool
    calls: list[TokenCall]
    provenance: Provenance
    prompt_texts: list[str] = Field(default_factory=list)
    strategy_tags: list[str] = Field(default_factory=list)

    @property
    def trace_hash(self):
        return digest(self)


class RouteDecision(StrictModel):
    route: Literal['base', 'strategy', 'execution', 'history', 'template']
    subject: str | None = None
    subject_source: str = 'unknown'
    skill_ids: list[str] = Field(default_factory=list)
    retrieved_skill_ids: list[str] = Field(default_factory=list)
    reason: str
    estimates: dict = Field(default_factory=dict)


class Submission(StrictModel):
    task_id: str
    first_solution: str
    solution: str
    first_answer: str | None
    final_answer: str | None
    retry_count: int
    decision: RouteDecision
    call_ids: list[str]
    skill_prompt_tokens: int
    bank_hash: str
    split: Split
    provenance: Provenance
    seal: str = ''

    def seal_value(self):
        return digest(self.model_dump(exclude={'seal'}, mode='json'))

    def frozen_submission(self):
        return self.model_copy(update={'seal': self.seal_value()})

    def assert_frozen(self):
        if self.seal != self.seal_value():
            raise ValueError('Submission must be frozen before evaluation')
