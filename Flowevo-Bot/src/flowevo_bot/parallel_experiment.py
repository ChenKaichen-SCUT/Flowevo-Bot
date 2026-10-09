"""64-way HTTP / 12-process scoring experiment with isolated durable ledgers.
Every model worker receives only public questions and a frozen training bank.
Labels are opened in the coordinator after ALL task submissions are durable.
"""
import concurrent.futures as cf
import json
import multiprocessing
from pathlib import Path
from runtime.llm_client import LLMClient,Reply
from .common import digest,read_json,write_json,jsonl
from .schemas import Submission,Provenance,RouteDecision,EvaluationRecord
from .math_solver import MathSolver
from .evaluator import extract_answer
from .experiment_grader import grade_one
from .token_accounting import TokenLedger
from .checkpoint import Checkpoint
from .trace_collector import collect_trace
from .mock import mock_response
from code_math.loader import load_manifest


class RecordedClient(LLMClient):
    """A truncated paid response is a counted failed attempt, never silently retried."""
    def complete(self,*args,**kwargs):
        try:return super().complete(*args,**kwargs)
        except RuntimeError as exc:
            if str(exc).startswith('Response truncated;') and self.ledger.calls:
                call=self.ledger.calls[-1]
                return Reply(self.ledger.responses[call.call_id],call)
            raise


def exported_submission(task,client,bank,exported,split,purpose):
    entry=exported[task.task_id]
    reply=client.complete(entry['prompt'],task_id=task.task_id,purpose=purpose or 'skill_solve',route=entry['route'])
    p=Provenance(origin_split=split,source_task_id=task.task_id,first_pass=True,
                 gold_exposed=False,reference_solution_exposed=False,external_verifier_used=False,
                 eligible_for_skill_learning=False,evidence_hash=digest({'task':task.model_dump(),'calls':[reply.call.call_id]}),synthetic=client.simulated)
    return Submission(task_id=task.task_id,first_solution=reply.text,solution=reply.text,
        first_answer=extract_answer(reply.text),final_answer=extract_answer(reply.text),retry_count=0,
        decision=RouteDecision(route=entry['route'],subject=task.subject,subject_source='metadata',reason='native FlowEvo frozen CodeSkillLibrary + build_goldfree_math_prompt'),
        call_ids=[reply.call.call_id],skill_prompt_tokens=0,bank_hash=bank.bank_hash,split=split,provenance=p).frozen_submission()


def run_parallel(config,manifest_path,bank,mode,output_dir,*,split='test',api_workers=64,local_workers=12,
                 exported=None,resume=False,dry_run=False):
    if not 1<=api_workers<=64 or not 1<=local_workers<=12:raise ValueError('Concurrency outside declared limits')
    manifest,tasks,labels=load_manifest(manifest_path,split)
    if not dry_run and (manifest.get('synthetic') or bank.synthetic):raise ValueError('Synthetic artifacts forbidden')
    if split=='test':
        from .provenance import assert_independent
        assert_independent([t.problem for t in bank.history],tasks)
    if exported is not None and set(exported)!=set(t.task_id for t in tasks):raise ValueError('Native prompt task IDs mismatch')
    output_dir=Path(output_dir)
    identity_mode=mode if exported is None else 'native_flowevo_goldfree_'+digest(exported)
    checkpoint=Checkpoint(output_dir,config=config,bank_hash=bank.bank_hash,split=split,mode=identity_mode,
        manifest_hash=digest(manifest),simulated=dry_run,resume=resume)
    pending=[p for p in tasks if p.task_id not in checkpoint.records]
    # Each task owns one ledger and one pending journal; coordinator owns checkpoint.
    def worker(task):
        ledger=TokenLedger(output_dir/'task_calls'/(task.task_id+'.json'))
        client=RecordedClient(config.llm,ledger,allow_paid=True,mock_handler=mock_response if dry_run else None)
        purpose='trace_generation' if split=='train-build' else 'skill_validation' if split=='train-dev' else None
        if exported is not None:
            return exported_submission(task,client,bank,exported,split,purpose)
        return MathSolver(client,config,bank,mode).solve(task,split=split,purpose=purpose)
    errors={}
    with cf.ThreadPoolExecutor(max_workers=api_workers) as pool:
        futures={pool.submit(worker,t):t.task_id for t in pending}
        for future in cf.as_completed(futures):
            tid=futures[future]
            try:checkpoint.commit(future.result())
            except Exception as exc:
                errors[tid]=str(exc)[:300]
                write_json(output_dir/'errors.json',errors)
            n=len(checkpoint.records)
            if n%25==0 or n==len(tasks) or tid in errors:
                print(json.dumps({'stage':str(output_dir),'completed':n,'total':len(tasks),'errors':len(errors)}),flush=True)
    if errors:raise RuntimeError(f'{len(errors)} requests failed; completed records preserved in {output_dir}')
    submissions=[checkpoint.records[t.task_id] for t in tasks]
    for s in submissions:s.assert_frozen()
    # Aggregate records only after workers have terminated: no concurrent shared mutation.
    ledger=TokenLedger()
    for t in tasks:
        l=TokenLedger(output_dir/'task_calls'/(t.task_id+'.json'))
        for c in l.calls:ledger.append(c,l.responses[c.call_id],l.prompts.get(c.call_id))
        ledger.failures.update(l.failures)
    ledger.path=output_dir/'calls.json';ledger.save()
    # Labels cannot affect solver prompts, decisions, retries or ordering.
    evaluations=[EvaluationRecord.model_validate(r) for r in jsonl(labels)]
    if digest([r.model_dump(mode='json') for r in evaluations])!=manifest['labels_hash']:raise ValueError('Labels hash mismatch')
    index={e.task_id:e for e in evaluations}
    items=[(s.task_id,s.final_answer,index[s.task_id].gold_answer,any(c in ledger.failures for c in s.call_ids)) for s in submissions]
    ctx=multiprocessing.get_context('spawn')
    with cf.ProcessPoolExecutor(max_workers=local_workers,mp_context=ctx) as pool:scores=list(pool.map(grade_one,items,chunksize=4))
    score_index={s['task_id']:s for s in scores}
    rows=[]
    for t,s in zip(tasks,submissions):
        calls=ledger.for_task(t.task_id)
        rows.append({'task_id':t.task_id,'subject':t.subject,'level':t.level,**score_index[t.task_id],
            'first_answer':s.first_answer,'final_answer':s.final_answer,'route':s.decision.route,
            'skill_ids':s.decision.skill_ids,'retry_count':s.retry_count,'seal':s.seal,
            'truncated':any(c.call_id in ledger.failures for c in calls),**ledger.totals(calls)})
    summary={'mode':mode,'count':len(tasks),'correct':sum(s['final_correct'] for s in scores),
             'accuracy':sum(s['final_correct'] for s in scores)/len(tasks),
             'strict_correct':sum(s['strict_correct'] for s in scores),**ledger.totals(),
             'mean_tokens':ledger.totals()['total_tokens']/len(tasks),
             'routes':{r:sum(s.decision.route==r for s in submissions) for r in sorted({s.decision.route for s in submissions})},
             'truncated':sum(r['truncated'] for r in rows),'model':config.llm.model,
             'temperature':config.llm.temperature,'max_output_tokens':config.llm.max_output_tokens,
             'manifest_hash':digest(manifest),'bank_hash':bank.bank_hash,'api_workers':api_workers,'local_workers':local_workers,
             'grader':'math-verify==0.8.0, conservative exact fallback, 3 second parsing/verification timeouts',
             'config_hash':digest(config.model_dump()),'simulated':dry_run}
    write_json(output_dir/'rows.json',rows);write_json(output_dir/'summary.json',summary)
    traces=[]
    if split=='train-build':
        for t,s in zip(tasks,submissions):
            calls=ledger.for_task(t.task_id)
            traces.append(collect_trace(t,s,score_index[t.task_id],calls,[ledger.prompts[c.call_id] for c in calls]))
        write_json(output_dir/'traces.json',[t.model_dump(mode='json') for t in traces])
    return summary,traces
