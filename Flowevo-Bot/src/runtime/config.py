"""Validated configurations. Importing this module cannot contact an API."""
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

MODES = ('base_onepass', 'flowevo_goldfree', 'flowevo_context_goldfree', 'bot_template',
         'subject_strategy', 'subject_strategy_admission', 'subject_strategy_costaware')


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class LLMConfig(Model):
    model: str = 'deepseek-flash'
    base_url: str = 'https://api.deepseek.com'
    api_key_env: str = 'DEEPSEEK_API_KEY'
    temperature: float = 0
    max_output_tokens: int = Field(default=2048, ge=1)
    timeout: float = 120
    max_calls: int = Field(default=100, ge=1)
    max_total_tokens: int = Field(default=200000, ge=1)
    allow_paid_api: bool = False


class StrategyConfig(Model):
    enabled: bool = True
    subject_routing: bool = True
    cross_subject_retrieval: bool = False
    top_k: int = Field(default=3, ge=1)
    max_injected_skills: int = Field(default=1, ge=1, le=2)
    max_skill_prompt_tokens: int = Field(default=100, ge=1)


class DistillationConfig(Model):
    enabled: bool = True
    min_source_traces: int = Field(default=3, ge=2)
    merge_duplicates: bool = True
    supervised_distillation: bool = False


class AdmissionConfig(Model):
    enabled: bool = True
    min_source_traces: int = Field(default=3, ge=2)
    min_dev_eligible_cases: int = Field(default=10, ge=2)
    require_independent_validation: bool = True
    require_positive_net_saving: bool = True
    reject_observed_harmful_patterns: bool = True
    allow_shadow_candidates: bool = True
    expected_future_uses: int = Field(default=100, ge=1)


class RouterConfig(Model):
    cost_aware: bool = True
    allow_skip_skill: bool = True
    max_allowed_accuracy_drop: float = Field(default=.01, ge=0, le=1)
    min_confidence: float = Field(default=.8, ge=0, le=1)
    enable_verified_execution: bool = False


class EvaluationConfig(Model):
    allow_test_gold_feedback: bool = False
    freeze_bank: bool = True
    save_pairwise_results: bool = True
    max_format_retries: int = Field(default=1, ge=0, le=3)


class Config(Model):
    seed: int = 42
    manifest: str = 'data/manifests/test.json'
    llm: LLMConfig = Field(default_factory=LLMConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    distillation: DistillationConfig = Field(default_factory=DistillationConfig)
    admission: AdmissionConfig = Field(default_factory=AdmissionConfig)
    router: RouterConfig = Field(default_factory=RouterConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    modes: list[str] = Field(default_factory=lambda: list(MODES))

    @model_validator(mode='after')
    def safe_protocol(self):
        if self.evaluation.allow_test_gold_feedback or not self.evaluation.freeze_bank:
            raise ValueError('This release requires gold-blind evaluation with a frozen bank')
        if self.distillation.supervised_distillation:
            raise ValueError('Supervised reference-solution distillation is not enabled in this release')
        if set(self.modes) - set(MODES):
            raise ValueError('Unknown experiment mode')
        return self


def load_config(path):
    return Config.model_validate(yaml.safe_load(Path(path).read_text()) or {})
