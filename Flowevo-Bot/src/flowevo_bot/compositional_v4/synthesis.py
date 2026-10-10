"""Enumerate typed compositions, match actual source intermediate states, verify.

The whole pipeline is not inserted into the bank. Five nonredundant type-safe
programs are searched in this deliberately small grammar. Negative or unsupported
trace observations remain in the candidate ledger. Numeric target fit alone is
insufficient for multi-step admission.
"""
import json,hashlib,time
from .expression import canonical,ScopeError
from .dsl import enumerate_programs,execute
from .verify import verify_execution,universal_certificate

def synthesize(examples):
    t=time.perf_counter();rows=[x for x in examples if x['io_verified'] and x['observations']]
    candidates=[]
    for program in enumerate_programs():
        item={'program':list(program),'source_checks':[],'source_ids':[],'structural_classes':[]}
        for row in rows:
            goal=row['goal'];check={'task_id':row['task_id']}
            try:
                value,steps=execute(program,goal['expression'],goal['modulus'])
                proof=verify_execution(goal['expression'],goal['modulus'],value,steps)
                states=[canonical(x['output']) for x in steps if x['output_type']=='IntegerExpression']
                observations=[o for o in row['observations'] if canonical(o['expression']) in states]
                check.update(final_fit=value==row['target'],intermediate_step_fit=bool(observations),independently_verified=proof['passed'],
                    matched_source_step_ids=sorted({o['step_id'] for o in observations}),execution_steps=steps,certificate=proof)
                if check['final_fit'] and observations and proof['passed']:
                    item['source_ids'].append(row['task_id']);item['structural_classes'].append(row['structure'])
            except (ScopeError,TimeoutError) as exc:check['reason']=str(exc)
            item['source_checks'].append(check)
        item['structural_class_count']=len({json.dumps(s,sort_keys=True) for s in item['structural_classes']})
        item['universal_certificate']=universal_certificate(program)
        item['eligible']=len(item['source_ids'])>=2 and item['structural_class_count']>=2 and len(program)>=3 and item['universal_certificate']['passed']
        candidates.append(item)
    admitted=[x for x in candidates if x['eligible']]
    admitted.sort(key=lambda x:(-len(x['source_ids']),len(x['program']),x['program']))
    bank=[]
    if admitted:
        best=admitted[0];ident=hashlib.sha256(json.dumps(best['program']).encode()).hexdigest()[:12]
        bank=[{'macro_id':'auto_integer_congruence_'+ident,'status':'certified_research','goal_kind':'integer_remainder',
            'program':best['program'],'source_task_ids':best['source_ids'],'source_structures':best['structural_classes'],
            'source_step_ids':{x['task_id']:x['matched_source_step_ids'] for x in best['source_checks'] if x.get('intermediate_step_fit')},
            'guards':['whole question consumed by shared semantic grammar','int/add/mul/positive literal pow only',
                '2<=modulus<=10000','AST<=96 nodes/depth<=12','exact intermediates<=8192 bits','exponents<=1000000',
                '3 second worker deadline and 512 MiB address space','independent verification of every rewrite and final residue'],
            'certificate':best['universal_certificate'],'selection':'largest actual trace intermediate support, then shortest program, then lexicographic',
            'multi_step':True,'learned':['primitive subset and ordering selected by bounded enumeration','routing admission from independent source states'],
            'manual':['integer goal grammar','four primitive operators','type rules','generic tree traversal','scope/budget guards','independent congruence verifier'],
            'guard_learning_limit':'semantic/validity guards are manual and propagated by types; no claim of learning a new number-theoretic precondition',
            'not_learned':['Euler theorem','new semantics parser','full natural-language reasoning','new primitive mathematics'],
            'source_count':len(best['source_ids']),'new_api_calls':0}]
    return {'bank':bank,'candidates':candidates,'statistics':{'enumerated_type_safe_programs':len(candidates),
        'admissible_programs':len(admitted),'trace_candidates':len(rows),'selected_macros':len(bank),
        'bounded_search':'four primitive names without repeated idempotent passes; <=6 nodes; normalized AST memo in interpreter',
        'wall_seconds':time.perf_counter()-t}}
