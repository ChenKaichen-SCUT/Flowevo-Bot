"""Shared routing and guards. Unexecuted fallback is never a wrong answer or zero-cost LLM run."""
import time
from .goals import parse_goal
from .dsl import execute,MANUAL_PROGRAM
from .verify import verify_execution
from .expression import structure,ScopeError

def solve(question,method,bank,legacy_bank=None):
    if method not in ('B','C'):raise ValueError('offline runtime supports only B/C')
    start=time.perf_counter();goal=parse_goal(question)
    out={'method':method,'module':'v4_integer_congruence','parsed_goal':goal.parsed,'guard_pass':False,
        'full_execution':False,'answer':None,'fallback_reason':goal.reason,'goal':goal.to_dict(),
        'structure':structure(goal.expression) if goal.parsed else None,'selected_macro':None,
        'execution_seconds':0.,'verification_seconds':0.,'retrieval_seconds':0.,'partial_available':False}
    try:
        if not goal.parsed:
            # Frozen V3 remains available to both arms under its original common grammar.
            from flowevo_bot.goal_v3.engine import solve as old_solve
            old=old_solve(question,'manual' if method=='B' else 'automatic',legacy_bank or [])
            out['legacy_result']=old
            if old['trigger'] or old['partial_result']:
                out.update(module='frozen_v3',parsed_goal=old['trigger'],guard_pass=old['guard_pass'],
                    full_execution=old['full_task_verified'],answer=old['answer'],fallback_reason=old['fallback_reason'],
                    selected_macro=old['selected_macro'],partial_available=old['partial_result'],
                    execution_seconds=old['execution_seconds'],verification_seconds=old['verification_seconds'],
                    retrieval_seconds=old['retrieval_seconds'])
            return out
        out['guard_pass']=True;t=time.perf_counter()
        if method=='B':program=MANUAL_PROGRAM;out['selected_macro']='manual_integer_congruence'
        else:
            candidates=[m for m in bank if m['status']=='certified_research' and m['goal_kind']==goal.kind and m['certificate']['passed']]
            if not candidates:out['fallback_reason']='DSL_no_certified_program';return out
            program=candidates[0]['program'];out['selected_macro']=candidates[0]['macro_id']
        out['retrieval_seconds']=time.perf_counter()-t;t=time.perf_counter()
        value,steps=execute(program,goal.expression,goal.modulus);out['execution_seconds']=time.perf_counter()-t
        t=time.perf_counter();proof=verify_execution(goal.expression,goal.modulus,value,steps)
        out['verification_seconds']=time.perf_counter()-t;out['steps']=steps;out['certificate']=proof
        if not proof['passed']:out['fallback_reason']='verification_failed';return out
        out.update(full_execution=True,answer=str(value),fallback_reason=None)
    except (ScopeError,TimeoutError,MemoryError) as exc:out['fallback_reason']='guard_or_resource_'+str(exc)
    finally:out['local_seconds']=time.perf_counter()-start
    return out
