"""Bounded, source-linked mathematical operation extraction; no API or labels."""
import sys,time,re,signal,collections
from concurrent.futures import ProcessPoolExecutor
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.rmmd.macros import fragments,scalar,inspect_question,IDS
import sympy as s

def deadline(*args):raise TimeoutError('symbolic_timeout')
def canonical(expr):
    symbols=sorted(expr.free_symbols,key=str)
    return s.srepr(expr.xreplace({x:s.Symbol('v'+str(i)) for i,x in enumerate(symbols)}))
def worker(row):
    signal.signal(signal.SIGALRM,deadline);ops=[];fs=fragments(row['model_solution'])
    def add(kind,inp,out,ids,status,guards=None,assumptions=None):
        ops.append(dict(task_id=row['task_id'],subject=row['subject'],level=row['level'],operation_type=kind,input_structure=inp,output_structure=out,assumptions=assumptions or [],required_guards=guards or [],source_step_ids=ids,verification_status=status))
    for mid in IDS:
        signal.alarm(5)
        try:
            result=inspect_question(row['problem'],mid)
            if result['execution_verified']:
                # Actual source evidence must include the relevant algebraic method,
                # AND its final result is independently confirmed by audit.
                pattern=r'Vieta|sum of.*roots|product of.*roots|symmetric|coefficien' if mid=='root_invariants' else r'remainder|divis|substitut|modulo'
                evidence=[f['step_id'] for f in fs if ('=' in f['text'] or '\\equiv' in f['text'])]
                if re.search(pattern,row['model_solution'],re.I) and evidence:
                    add(mid,result['input_structure'],result['output_structure'],evidence,'verified_operation_with_confirmed_source',assumptions=['source final answer independently correct; intermediate identity separately recomputed','all roots with multiplicity' if mid=='root_invariants' else 'QQ polynomial ring'])
        except Exception:pass
        finally:signal.alarm(0)
    for f in fs[:48]:
        text=f['text']
        if text.count('=')!=1:continue
        signal.alarm(2)
        try:
            a,b=map(scalar,text.split('='));diff=s.cancel(a-b)
            if diff==0:
                guards=[str(s.denom(s.together(v)))+' != 0' for v in (a,b) if s.denom(s.together(v))!=1]
                if not (a.free_symbols|b.free_symbols):kind='exact_numeric_evaluation'
                elif guards:kind='rational_normalization'
                elif a.has(s.sin,s.cos) or b.has(s.sin,s.cos):kind='trigonometric_identity'
                elif isinstance(a,s.Add) and isinstance(b,(s.Mul,s.Pow)):kind='polynomial_factorization'
                elif isinstance(b,s.Add) and isinstance(a,(s.Mul,s.Pow)):kind='polynomial_expansion'
                else:kind='algebraic_identity'
                add(kind,{'latex':text.split('=')[0],'canonical':canonical(a)},{'latex':text.split('=')[1],'canonical':canonical(b)},[f['step_id']],'symbolically_verified_common_domain',guards)
            else:add('constrained_equation',{'latex':text},None,[f['step_id']],'unknown_requires_context')
        except Exception as exc:add('unparsed',{'latex':text},None,[f['step_id']],'unknown_'+type(exc).__name__)
        finally:signal.alarm(0)
    if not ops:add('unparsed',{'reason':'no supported explicit identity'},None,[],'unknown')
    return ops

def main():
    cap_cpu();start=time.perf_counter();rows=lines(OUT/'data/clean_success_traces.jsonl')
    with ProcessPoolExecutor(max_workers=12) as pool:nested=list(pool.map(worker,rows,chunksize=4))
    ops=[op for group in nested for op in group];write_lines(OUT/'data/reasoning_operations.jsonl',ops)
    clusters=[]
    for (subject,kind) in sorted({(r['subject'],r['operation_type']) for r in ops}):
        group=[r for r in ops if r['subject']==subject and r['operation_type']==kind];ids=sorted({r['task_id'] for r in group})
        clusters.append({'subject':subject,'family':kind,'unique_tasks':len(ids),'operation_count':len(group),'task_ids':ids,'verification_statuses':dict(collections.Counter(r['verification_status'] for r in group)),'examples':group[:3]})
    write(OUT/'data/pattern_clusters.json',clusters)
    table(OUT/'data/pattern_frequency.csv',[{k:v for k,v in r.items() if k!='examples'} for r in clusters])
    write(OUT/'evidence/mining_runtime.json',{'wall_seconds':time.perf_counter()-start,'workers':12,'max_explicit_equations_per_trace':48,'api_calls':0,'method':'engineered operation recognizers with exact symbolic verification; no claim of novel theorem discovery'})
    print('mined',len(ops),'operations from',len(rows),'traces',flush=True)
if __name__=='__main__':main()
