"""Post-submission evaluator, isolated from generation and gold feedback."""
import json,time,signal,contextlib,socket,resource,os
from dataclasses import replace
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from .models import EvaluatorConfig,AnswerSpec,Unsupported,Invalid,DeadlineExceeded
from .spec import infer_spec
from .reference import build_reference
from .extraction import extract_model
from .normalization import normalize
from .equivalence import compare

PINNED={'math-verify':'0.8.0','latex2sympy2_extended':'1.10.2','sympy':'1.14.0','antlr4-python3-runtime':'4.13.2','mpmath':'1.3.0'}

def check_versions():
    from importlib.metadata import version
    actual={name:version(name) for name in PINNED}
    if actual!=PINNED:raise RuntimeError(f'Evaluator dependency mismatch: {actual}; required {PINNED}')
    return actual

@contextlib.contextmanager
def deadline(seconds):
    # Batch work always executes in a worker main thread. API use from another
    # thread is rejected rather than silently losing the timeout guarantee.
    import threading
    if threading.current_thread() is not threading.main_thread():raise RuntimeError('Use evaluate_batch from threaded applications')
    def expire(*_):raise DeadlineExceeded('evaluation_timeout')
    old=signal.signal(signal.SIGALRM,expire)
    previous=signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,*previous);signal.signal(signal.SIGALRM,old)

class MathEvaluatorV3:
    def __init__(self,config=None):
        self.config=config or EvaluatorConfig();check_versions()
    def evaluate(self,record,answer_spec=None):
        """Accept a sealed visible response and full canonical solution only.

        `reasoning_content` is intentionally not an input to the extractor.
        The result is a standalone record; no callback/controller hook exists.
        """
        start=time.monotonic();cfg=self.config
        r={k:record.get(k) for k in ('record_id','task_id','branch','subject','level','question','prediction_raw','reference_raw','finish_reason','source_job_id','source_path','request_hash','response_hash')}
        r.update(evaluator='MathEvaluatorV3',version=cfg.version,config_hash=cfg.hash(),status='unknown',reason='',answer_spec=None,prediction_extracted=None,reference_candidates=[],reference_complete=False,prediction_normalized=None,reference_normalized=None,equivalence_method=None,equivalence_evidence={})
        stage='input'
        try:
            if cfg.require_sealed_submission and record.get('submission_sealed') is not True:raise Unsupported('submission_not_sealed')
            if any(len(record.get(k) or '')>cfg.max_text_chars for k in ('question','prediction_raw','reference_raw')):raise Unsupported('raw_text_length_limit')
            with deadline(cfg.timeout_seconds):
                spec=answer_spec or infer_spec(record['question']);r['answer_spec']=spec.to_dict()
                ex=extract_model(record.get('prediction_raw') or '',record.get('finish_reason'),spec);r['prediction_extraction']=ex.to_dict();r['prediction_extracted']=ex.selected
                ref=build_reference(record['question'],record.get('reference_raw') or '',spec)
                r.update(reference_builder=ref,reference_candidates=ref['candidates'],reference_complete=ref['complete'],reference_extracted=ref['selected'])
                if ex.status!='ok':r.update(status=ex.status,reason=ex.reason);return r
                if spec.uncertain or spec.kind=='unknown':raise Unsupported('answer_specification_uncertain')
                if ref['status']!='ok':r.update(status=ref['status'],reason=ref['reason']);return r
                stage='reference';gold=normalize(ref['selected'],spec,cfg);r['reference_normalized']=gold.to_dict()
                for alternative in ref.get('alternative_candidates',[]):
                    alt=normalize(alternative,spec,cfg)
                    if compare(alt,gold,spec)[0] is not True:
                        r.update(status='reference_ambiguous',reason='boxed candidates not proven equivalent; intermediate status unresolved',reference_complete=False);return r
                stage='prediction';pred=normalize(ex.selected,spec,cfg);r['prediction_normalized']=pred.to_dict()
                stage='comparison'
                directions=[n.removeprefix('direction=') for n in pred.notes if n.startswith('direction=') and n!='direction=unspecified']
                if directions:
                    from .certificates import area_direction
                    cert=area_direction(record['question'])
                    if cert is None:raise Unsupported('direction_not_verified_from_public_question')
                    r['public_constraint_certificate']=cert
                    if directions[0]!=cert['direction']:
                        r.update(status='incorrect',reason='wrong_direction_of_change');return r
                v,method,ev=compare(pred,gold,spec)
                r.update(status='correct' if v is True else 'incorrect' if v is False else 'unknown',reason=method,equivalence_method=method,equivalence_evidence=ev)
                # Math-Verify receives parsed objects only, and is diagnostic. Its
                # tolerance/unit/extraction defaults never decide V3's verdict.
                if pred.kind==gold.kind=='expression' and not (pred.value.free_symbols or gold.value.free_symbols):
                    from math_verify import verify
                    r['math_verify_diagnostic']={'equivalent':bool(verify(gold.value,pred.value,timeout_seconds=1)),'decisive':False,'input':'already parsed exact objects'}
        except Invalid as e:r.update(status='reference_invalid' if stage=='reference' else 'incorrect',reason=str(e),error_stage=stage)
        except (Unsupported,DeadlineExceeded,MemoryError) as e:r.update(status='unknown',reason=str(e) or type(e).__name__,error_stage=stage)
        except Exception as e:r.update(status='unknown',reason='parser_or_symbolic_error',error_stage=stage,error_type=type(e).__name__,error_detail=str(e)[:500])
        finally:r['elapsed_seconds']=time.monotonic()-start
        return r
    def evaluate_batch(self,records):
        cfg=self.config
        with ProcessPoolExecutor(max_workers=min(12,cfg.workers),initializer=_worker_init,initargs=(cfg,)) as pool:return list(pool.map(_work,records,chunksize=1))
    @staticmethod
    def export_unknown(results,path):
        Path(path).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results if r['status'] in ('unknown','reference_ambiguous','reference_invalid')))

_WORKER=None

def _worker_init(config):
    global _WORKER
    # Resource guard applies to the isolated child, never the caller's process.
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    cap=config.memory_limit_mb*1024**2
    resource.setrlimit(resource.RLIMIT_AS,(min(cap,hard) if hard!=-1 else cap,hard))
    def no_network(*args,**kwargs):raise RuntimeError('offline evaluator network disabled')
    socket.socket=no_network;socket.create_connection=no_network
    _WORKER=MathEvaluatorV3(config)

def _work(record):return _WORKER.evaluate(record)
