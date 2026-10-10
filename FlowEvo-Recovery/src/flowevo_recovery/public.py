"""Public-only solver state. Offline labels cannot enter this schema."""
from pydantic import BaseModel,ConfigDict

class Task(BaseModel):
 model_config=ConfigDict(extra='forbid',frozen=True)
 task_id:str
 domain:str
 problem:str
 subject:str='code'
 level:str='unspecified'
 public_tests:list[str]=[]
 setup:str=''

class State(BaseModel):
 model_config=ConfigDict(extra='forbid',frozen=True)
 task:Task
 solution:str
 truncated:bool
 call_id:str
 input_tokens:int=0
 output_tokens:int=0

ACTIONS=('continue','retry','repair','replan')

def base_prompt(task):
 if task.domain=='math':return f'Problem: {task.problem}\n\nSolve step by step. End with: The answer is [your answer].'
 return ('Write a Python function that solves the following task.\nTask: '+task.problem+
 '\n\nYour function MUST pass these test cases:\n'+''.join('  '+t+'\n' for t in task.public_tests)+
 '\nAnalyze the test cases carefully, think step by step, then write the complete Python function.')

def recovery_prompt(state,action,features):
 if action not in ACTIONS:raise ValueError('unknown_recovery_action')
 task=state.task
 if action=='retry':return base_prompt(task)
 text=state.solution
 # Same state-context cap for all state-conditioned actions; log any omission.
 if len(text)>6000:text=text[:1500]+'\n[Earlier reasoning middle omitted by fixed 6000-character context limit.]\n'+text[-4500:]
 instruction={
 'continue':'Continue the previous reasoning from where it stopped. Preserve justified progress; correct any error you notice. Produce a complete standalone final response.',
 'repair':'Verify the candidate using only the public question and the public evidence below. Locate any concrete inconsistency and repair it. Do not assume the candidate is wrong merely because verification is requested.',
 'replan':'Solve afresh using a different representation, mathematical method, or algorithm from the candidate. Check all stated constraints and provide a complete answer.'}[action]
 evidence=features['evidence'] if action=='repair' else []
 return base_prompt(task)+'\n\nPrevious candidate:\n'+text+'\n\nPublic diagnostic evidence:\n'+str(evidence)+'\n\n'+instruction
