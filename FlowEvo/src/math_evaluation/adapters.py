"""Adapters for sealed experiment records and native CodeTaskInstance objects."""
from dataclasses import dataclass,asdict,is_dataclass
from pathlib import Path
import hashlib,json,time,sys
from .engine import MathEvaluatorV3
from .models import EvaluatorConfig

@dataclass(frozen=True)
class OfflineScoringConfig:
    evaluator:str='legacy'
    workers:int=12
    def __post_init__(self):
        if self.evaluator not in ('legacy','fixed','v3'):raise ValueError('evaluator must be legacy, fixed or v3')
        if not 1<=self.workers<=12:raise ValueError('local workers must be in [1,12]')
    def hash(self):return hashlib.sha256(json.dumps(asdict(self),sort_keys=True).encode()).hexdigest()

def from_flowevo_task(task,runner_record,*,submission_sealed=False):
    """Native loader's shallow metadata.gold_answer is intentionally not V3 gold.

    Existing runner logs may omit finish_reason; preserve its absence. A caller
    must affirm the run has ended before passing a frozen record for scoring.
    """
    if getattr(task,'benchmark',None)!='math':raise ValueError('V3 adapter currently supports native MATH tasks only')
    if runner_record.get('task_id')!=task.task_id:raise ValueError('task/response ID mismatch')
    return {'record_id':task.task_id,'task_id':task.task_id,'question':task.prompt or task.text,'reference_raw':task.canonical_solution,'prediction_raw':runner_record.get('solution') or '',
            'frozen_gold_answer':task.metadata.get('gold_answer',''),'finish_reason':runner_record.get('finish_reason'),'submission_sealed':submission_sealed,
            'source_path':runner_record.get('source_path'),'request_hash':runner_record.get('request_hash'),'response_hash':runner_record.get('response_hash'),
            'source_metadata':{'finish_reason_available':'finish_reason' in runner_record,'native_loader_gold_is_historical_only':True}}

def _old_worker(args):
    name,r=args
    start=time.monotonic()
    # These pinned historical implementations reside in sibling projects.
    root=Path(__file__).resolve().parents[3]
    for path in (root/'Flowevo-Bot/src',root/'FlowEvo-Recovery/src'):
        if str(path) not in sys.path:sys.path.insert(0,str(path))
    if not r.get('submission_sealed'):return {'task_id':r.get('task_id'),'status':'unknown','reason':'submission_not_sealed','evaluator':name}
    if 'frozen_gold_answer' not in r:raise ValueError('Historical evaluators require the historical frozen gold, not a V3 rebuilt label')
    if name=='legacy':
        from flowevo_bot.evaluator import extract_answer
        from flowevo_bot.experiment_grader import grade_one
        raw=grade_one((r['task_id'],extract_answer(r['prediction_raw']),r['frozen_gold_answer'],r.get('finish_reason')=='length'))
        status='correct' if raw['final_correct'] else 'incorrect'
    else:
        from flowevo_recovery.math_scoring_v2 import grade
        raw=grade({'task_id':r['task_id'],'question':r['question'],'solution':r['prediction_raw'],'gold_answer':r['frozen_gold_answer'],'truncated':r.get('finish_reason')=='length'})
        status='correct' if raw['correct'] is True else 'incorrect' if raw['correct'] is False else 'unknown'
    return {'record_id':r.get('record_id'),'task_id':r['task_id'],'evaluator':name,'status':status,'historical_grade':raw,'elapsed_seconds':time.monotonic()-start}

class OfflineMathEvaluator:
    def __init__(self,config=None):self.config=config or OfflineScoringConfig()
    def evaluate_batch(self,records):
        if self.config.evaluator=='v3':return MathEvaluatorV3(EvaluatorConfig(workers=self.config.workers)).evaluate_batch(records)
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=self.config.workers) as pool:return list(pool.map(_old_worker,((self.config.evaluator,r) for r in records)))
