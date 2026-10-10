"""Step extraction independent of whole-question parsing; trace-linked observations.

Only explicit integer equalities/congruences receive verified operation labels.
Unknown algebra/natural language is retained as unknown, never treated as a proof.
"""
import re,collections,itertools,json,hashlib
from flowevo_bot.rmmd.macros import fragments
from flowevo_bot.v2.evaluator import extract,presentation
from .expression import *
from .goals import parse_goal
from .verify import reference_residue

def anti_unify(a,b,holes=None,depth=0):
    """Bounded least general generalization; mismatched roots become typed holes.

    Repeated pair disagreements reuse one hole; numeric values are never learned
    as constants. A root-only hole is explicitly low-information, not a pattern.
    """
    holes={} if holes is None else holes
    if depth>MAX_DEPTH:raise ScopeError('anti_unification_depth')
    if a==b:return a
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)) and a[0]==b[0] and len(a)==len(b) and a[0]!='int':
        if a[0]=='pow':return ('pow',anti_unify(a[1],b[1],holes,depth+1),('ExponentHole',))
        return (a[0],*(anti_unify(x,y,holes,depth+1) for x,y in zip(a[1:],b[1:])))
    key=(repr(a),repr(b))
    if key not in holes:holes[key]=len(holes)
    typ='Integer' if a[0]==b[0]=='int' else 'IntegerExpression'
    return (typ+'Hole',holes[key])

def record(row,kind,inp,out,stepid,rule,status,raw,modulus=None):
    return {'operation_type':kind,'input_type':'IntegerExpression' if inp else 'Unknown','output_type':'IntegerExpression' if out else 'Unknown',
        'input_structure':inp,'output_structure':out,'preconditions':['exact integers','positive literal exponents']+([f'modulus={modulus}'] if modulus else []),
        'transformation':raw,'source_task_id':row['task_id'],'source_step_ids':[stepid] if stepid is not None else [],
        'verification_rule':rule,'verification_status':status,'extraction_confidence':'verified_explicit_step' if status=='verified' else 'unknown',
        'provenance':{'source_hash':row['source_hash'],'source_run_id':row['source_run_id'],
            'recognizer':'human-written finite integer/congruence syntax; automatic matching','raw_text':'copied source span',
            'complete_natural_language_chain_understood':False},'modulus':modulus}

def extract_trace(row,max_spans=96):
    goal=parse_goal(row['problem']);ops=[];observations=[];fs=fragments(row['model_solution'])
    for f in fs[:max_spans]:
        raw=f['text']
        if not ('=' in raw or '\\equiv' in raw):continue
        modmatch=re.search(r'\\pmod\s*(?:\{(\d+)\}|(\d+))\s*[.,]?$',raw)
        mod=int(modmatch[1] or modmatch[2]) if modmatch else goal.modulus
        cleaned=raw[:modmatch.start()].strip() if modmatch else raw.strip()
        parts=re.split(r'\\equiv|=',cleaned)
        nodes=[]
        for part in parts:
            try:nodes.append(parse_expression(part))
            except (ScopeError,ValueError):nodes.append(None)
        for i,(a,b) in enumerate(zip(nodes,nodes[1:])):
            congruence='\\equiv' in raw
            if a is None or b is None or congruence and (mod is None or not 2<=mod<=MAX_MODULUS):
                ops.append(record(row,'uninterpreted_mathematical_relation',a,b,f['step_id'],'not_proven','unknown',raw,mod));continue
            try:
                passed=reference_residue(a,mod)==reference_residue(b,mod) if congruence else exact_eval(a)==exact_eval(b)
            except ScopeError:
                ops.append(record(row,'resource_limited_relation',a,b,f['step_id'],'not_proven','unknown',raw,mod));continue
            kind='integer_congruence' if congruence else 'exact_integer_evaluation'
            ops.append(record(row,kind,a,b,f['step_id'],'independent_binary_modular_check' if congruence else 'exact_integer_equality',
                              'verified' if passed else 'rejected',raw,mod))
            # A whole-task intermediate must be verified from the source relation,
            # non-scalar, congruent to the requested object, and materially changed.
            if passed and goal.parsed and (not congruence or mod==goal.modulus):
                for node in (a,b):
                    if node[0]!='int' and node!=goal.expression and reference_residue(node,goal.modulus)==reference_residue(goal.expression,goal.modulus):
                        observations.append({'expression':node,'step_id':f['step_id'],'raw':raw,'modulus_inherited_from_question':modmatch is None})
    ops.append(record(row,'uninterpreted_natural_language',None,None,None,'not_analyzed','unknown',row['model_solution'][:600]))
    answer,status=extract(row['model_solution']);answer=presentation(answer) if answer else ''
    target=int(answer) if re.fullmatch(r'-?\d+',answer or '') else None
    eligible=goal.parsed and target is not None and target==reference_residue(goal.expression,goal.modulus)
    return ops,{'task_id':row['task_id'],'problem':row['problem'],'goal':goal.to_dict(),'target':target,
      'observations':observations,'io_verified':eligible,'source_hash':row['source_hash'],'source_solution':row['model_solution'],
      'structure':structure(goal.expression) if goal.parsed else None}

def cluster(examples):
    eligible=[r for r in examples if r['io_verified'] and r['observations']]
    pairs=[]
    for a,b in itertools.combinations(eligible,2):
        holes={};general=anti_unify(a['goal']['expression'],b['goal']['expression'],holes)
        pairs.append({'source_ids':[a['task_id'],b['task_id']],'anti_unification':general,'hole_count':len(holes),
                      'informative_root':not general[0].endswith('Hole')})
    return {'candidate_family':'integer_expression_modular_rewrite','eligible_source_ids':[r['task_id'] for r in eligible],
      'structural_classes':{r['task_id']:r['structure'] for r in eligible},'anti_unification_pairs':pairs,
      'normalization':'commutative add/mul flatten/sort; typed literal holes; no variables admitted',
      'limit':'cross add/mul root disagreement is only an IntegerExpression hole; common traversal/composition is supported by trace states, not asserted from this vacuous LGG'}
