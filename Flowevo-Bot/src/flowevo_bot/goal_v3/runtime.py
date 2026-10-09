"""Identical NoBank fallback for A/B/C; partial results never enter prompts."""
import time
from code_math.baseline import base_prompt
from .engine import solve

def solve_task(problem,method,bank,client,code_hash,source='independent_dev'):
    start=time.perf_counter()
    if method not in ('A_NoBank','B_Manual','C_Automatic'):raise ValueError('unknown_comparison_arm')
    execution=solve(problem.problem,'manual' if method=='B_Manual' else 'automatic',bank) if method!='A_NoBank' else None
    direct=bool(execution and execution['full_task_verified'])
    if direct:
        answer=execution['answer'];solution='The answer is \\boxed{'+answer+'}.';call=None;truncated=False
    else:
        # Deliberately identical even when useful-looking partial values exist.
        call=client.complete(base_prompt(problem),method+'__'+problem.task_id,code_hash)
        choice=call['response']['choices'][0];solution=choice['message'].get('content') or '';answer=None;truncated=choice.get('finish_reason')=='length'
    return {'task_id':problem.task_id,'subject':problem.subject,'difficulty':problem.level,'question_source':source,'method':method,'selected_macro':execution['selected_macro'] if execution else None,'trigger':execution['trigger'] if execution else False,'goal':execution['goal'] if execution else None,'guard_checks':execution['guard_checks'] if execution else [],'execution_attempted':execution['execution_attempted'] if execution else False,'execution_result':execution['execution_result'] if execution else None,'verification_certificate':execution['verification_certificate'] if execution else None,'full_task_verified':direct,'partial_result':execution['partial_result'] if execution else False,'fallback_reason':execution['fallback_reason'] if execution else 'NoBank_control','input_tokens':call['input_tokens'] if call else 0,'output_tokens':call['output_tokens'] if call else 0,'total_tokens':call['total_tokens'] if call else 0,'api_call_count':1 if call else 0,'reasoning_seconds':call['latency'] if call else 0,'local_seconds':execution['local_seconds'] if execution else 0,'execution_seconds':execution['execution_seconds'] if execution else 0,'verification_seconds':execution['verification_seconds'] if execution else 0,'retrieval_seconds':execution['retrieval_seconds'] if execution else 0,'answer':answer,'solution':solution,'truncated':truncated,'gold_exposed':False,'code_hash':code_hash,'prompt_hash':call['prompt_hash'] if call else None,'call_id':call['call_id'] if call else None,'total_seconds':time.perf_counter()-start}
