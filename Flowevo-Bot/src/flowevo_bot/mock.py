"""Explicit deterministic fixtures, never represented as real LLM measurements."""
import json
import re
from .math_executor import MathExecutor
from .schemas import ProblemView


def mock_response(prompt,purpose):
    if purpose in ('distillation','skill_revision'):
        data=json.loads(prompt);features=set(data['observable_common_features'])
        if 'polynomial' in features:
            pattern='polynomial_degree';trigger=['polynomial']
            steps=['Collect like powers and identify nonzero coefficients.',
                   'Take the greatest exponent remaining after cancellation.',
                   'Check that leading terms do not cancel.']
            short='For a polynomial, collect like terms before taking the largest nonzero power. Check leading-term cancellation.'
        elif 'modular' in features:
            pattern='modular_reduction';trigger=['modular']
            steps=['Identify the stated modulus and reduce each term.',
                   'Use congruence-preserving operations to simplify.',
                   'Report the least nonnegative residue and check the original expression.']
            short='Reduce terms under the stated modulus using valid congruences. Return the requested residue; check the original expression.'
        else:
            return json.dumps({'no_generalizable_skill':True})
        payload={'skill_id':'mock_'+pattern,'version':1,'subject':data['subject'],
            'strategy_pattern':pattern,'name':pattern,'trigger_features':trigger,'preconditions':[],
            'negative_triggers':[],'strategy_steps':steps,'verification_rules':['Check the original mathematical conditions.'],
            'composition_tags':[],'compact_prompt':short,'optional_executor':None}
        return json.dumps(payload)
    # Recognized synthetic arithmetic only. Unsupported questions remain unanswered.
    matches=list(re.finditer(r'(?:Current problem:|Problem:)\s*(.*?)(?:\n\n|\nYour previous|$)',prompt,re.S))
    question=matches[-1][1] if matches else prompt
    execution=MathExecutor().execute(ProblemView(task_id='mock',problem=question))
    if execution:return 'The answer is '+execution.answer+'.'
    if 'polynomial' in question.lower() and 'degree' in question.lower():
        powers=[int(x) for x in re.findall(r'x\^\{?(\d+)',question)]
        # This fixture grammar excludes cancellation; it is not a general polynomial solver.
        if powers and '-' not in question:
            return 'Collect the displayed nonzero powers. The answer is '+str(max(powers))+'.'
    m=re.search(r'(?:remainder|residue).*?(\d+)\s+(?:modulo|mod)\s+(\d+)',question,re.I)
    if m and int(m[2])>0:
        return 'Reduce under the stated modulus. The answer is '+str(int(m[1])%int(m[2]))+'.'
    return 'Offline mock has no solver for this problem.'
