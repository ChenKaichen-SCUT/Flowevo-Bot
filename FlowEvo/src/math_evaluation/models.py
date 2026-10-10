from dataclasses import dataclass,field,asdict
import hashlib,json

@dataclass(frozen=True)
class AnswerSpec:
    kind:str='unknown'
    target:str|None=None
    domain:str='real'
    all_solutions:bool=False
    unordered:bool=False
    unit:str|None=None
    allow_unit_conversion:bool=False
    decimal_places:int|None=None
    percent_mode:str|None=None
    choices:tuple[str,...]=()
    base:int|None=None
    assumptions:tuple[str,...]=()
    evidence:tuple[str,...]=()
    uncertain:bool=False
    def to_dict(self):return asdict(self)

@dataclass(frozen=True)
class EvaluatorConfig:
    version:str='3.0.0'
    timeout_seconds:float=4.0
    max_answer_chars:int=4096
    max_text_chars:int=100000
    max_nodes:int=600
    max_nesting:int=40
    memory_limit_mb:int=1536
    workers:int=12
    require_sealed_submission:bool=True
    def to_dict(self):return asdict(self)
    def hash(self):return hashlib.sha256(json.dumps(asdict(self),sort_keys=True).encode()).hexdigest()

@dataclass
class Candidate:
    text:str
    start:int
    end:int
    source:str
    context:str=''
    def to_dict(self):return asdict(self)

@dataclass
class Extraction:
    selected:str|None
    candidates:list[Candidate]=field(default_factory=list)
    status:str='ok'
    reason:str=''
    def to_dict(self):return {'selected':self.selected,'candidates':[x.to_dict() for x in self.candidates],'status':self.status,'reason':self.reason}

@dataclass
class Normalized:
    kind:str
    value:object
    domain:object=None
    unit:str|None=None
    dimension:tuple=()
    notes:list=field(default_factory=list)
    def to_dict(self):
        import sympy as s
        return {'kind':self.kind,'value':str(self.value),'structure':s.srepr(self.value) if isinstance(self.value,(s.Basic,s.MatrixBase)) else repr(self.value),'domain':str(self.domain) if self.domain is not None else None,'unit':self.unit,'dimension':self.dimension,'notes':self.notes}

class Unsupported(ValueError):pass
class Invalid(ValueError):pass
class DeadlineExceeded(TimeoutError):pass
