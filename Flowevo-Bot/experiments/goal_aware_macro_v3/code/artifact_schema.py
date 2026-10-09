"""Post-run typed audit of the unchanged synthesis bank, not a solver change."""
from typing import Literal,Any
from pydantic import BaseModel,ConfigDict,field_validator,model_validator
from flowevo_bot.goal_v3.learning import validate_program

class MacroSkill(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    macro_id:str
    goal_kind:Literal['root_sum','root_product','pairwise_sum','reciprocal_sum']
    status:Literal['certified']
    program:list[Any]
    program_origin:Literal['enumerated_and_selected_from_trace_targets']
    source_task_ids:list[str]
    structural_classes:list[list[Any]]
    certificate:dict[str,Any]
    manual_components:list[str]
    learned_components:list[str]
    new_llm_calls:Literal[0]
    @field_validator('program')
    @classmethod
    def safe_dsl(cls,value):validate_program(value);return value
    @model_validator(mode='after')
    def qualified_sources(self):
        if len(set(self.source_task_ids))<2:raise ValueError('two_independent_sources_required')
        if len({tuple(c) for c in self.structural_classes})<2:raise ValueError('two_structures_required')
        if self.certificate.get('passed') is not True or self.certificate.get('degrees')!=[2,3,4,5,6]:raise ValueError('incomplete_symbolic_certificate')
        return self
