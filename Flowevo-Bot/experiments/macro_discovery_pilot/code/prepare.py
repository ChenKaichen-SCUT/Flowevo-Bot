import sys,re,collections,time,signal
from concurrent.futures import ProcessPoolExecutor
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.rmmd.macros import inspect_question,IDS,COMPACT
from flowevo_bot.features import normalize_problem
from difflib import SequenceMatcher
import sympy as s

def near_duplicate(a,b):
    a=normalize_problem(a,True);b=normalize_problem(b,True)
    matcher=SequenceMatcher(None,a,b,autojunk=False)
    return matcher.real_quick_ratio()>=.9 and matcher.quick_ratio()>=.9 and matcher.ratio()>=.9

def structure(result):
    if result.get('macro_id')!='polynomial_remainder' or not result.get('execution_verified'):return None
    values=[]
    for key in ('dividend','divisor'):
        expr=s.sympify(result['input_structure'][key]);x=next(iter(expr.free_symbols));values.append(tuple(m[0][0] for m in s.Poly(expr,x).terms()))
    return tuple(values)

def root_template(question,result):
    if result.get('macro_id')!='root_invariants' or not result.get('execution_verified'):return None
    if re.search(r'product of (?:all )?(?:the )?roots',question,re.I) or re.search(r'Find\s*\$[a-z]{2,6}[.,]?\$',question):
        return ('product_all_roots',result['input_structure']['degree'])
    if re.search(r'sum of (?:all )?(?:the )?roots',question,re.I):
        return ('sum_all_roots',result['input_structure']['degree'],'factored' if ')(' in question or ')(2' in question else 'expanded')
    return None

def check(row):
    return row,{mid:inspect_question(row['problem'],mid) for mid in IDS}
def main():
    cap_cpu();started=time.perf_counter()
    sources=lines(OUT/'data/clean_success_traces.jsonl');ops=lines(OUT/'data/reasoning_operations.jsonl')
    used={r['task_id'] for r in lines(OLD/'manifests/train.problems.jsonl')+lines(OLD/'manifests/dev.problems.jsonl')}
    used.update(r['problem']['task_id'] for r in read(V2/'data/dev_tasks.json'))
    prior_questions=[r['problem'] for r in lines(OLD/'manifests/train.problems.jsonl')+lines(OLD/'manifests/dev.problems.jsonl')]
    prior_questions +=[r['problem']['problem'] for r in read(V2/'data/dev_tasks.json')]
    prior_normal={normalize_problem(q,True) for q in prior_questions}
    dev=lines(ROOT/'data/manifests/math_grouped/dev.problems.jsonl');train=lines(ROOT/'data/manifests/math_grouped/train.problems.jsonl')
    pool=[{**r,'selection_pool':name} for name,rows in [('unused_original_dev',dev),('unused_original_train_reserved_as_dev',train)] for r in rows if r['task_id'] not in used]
    candidates=[r for r in pool if re.search(r'roots|remainder',r['problem'],re.I)]
    with ProcessPoolExecutor(max_workers=12) as ex:checked=list(ex.map(check,candidates))
    routing=[];eligible={mid:[] for mid in IDS}
    source_shapes={structure(inspect_question(r['problem'],'polynomial_remainder')) for r in sources};source_shapes.discard(None)
    source_roots={root_template(r['problem'],inspect_question(r['problem'],'root_invariants')) for r in sources};source_roots.discard(None)
    for row,results in checked:
        for mid,result in results.items():
            reject='previous_digit_normalized_or_near_clone' if result['execution_verified'] and any(near_duplicate(row['problem'],q) for q in prior_questions) else None
            if structure(result) in source_shapes:reject='same_source_polynomial_support_template'
            if root_template(row['problem'],result) in source_roots:reject='same_source_root_target_template'
            routing.append({'task_id':row['task_id'],'macro_id':mid,'selection_pool':row['selection_pool'],'guard_pass':result['guard_pass'],'verified':result['execution_verified'],'exclusion':reject,'reason':result['fallback_reason']})
            if result['execution_verified'] and not reject:eligible[mid].append((row,result))
    chosen=[];bank=[];screen=[]
    for mid in IDS:
        midops=[r for r in ops if r['operation_type']==mid];sourceids=sorted({r['task_id'] for r in midops})
        shapes={};selected=[];seen=set(prior_normal)
        # No label or outcome used. Prefer original unused dev, then public level
        # and hashed ID; stratify structural classes before filling to at most 10.
        rows=sorted(eligible[mid],key=lambda rr:(rr[0]['selection_pool']!='unused_original_dev',rr[0]['level'],rr[0]['task_id']))
        seen_shapes=set(source_shapes);seen_roots=set(source_roots)
        for row,result in rows:
            normalized=normalize_problem(row['problem'],True)
            if normalized in seen:continue
            if any(near_duplicate(row['problem'],c['problem']['problem']) for c in chosen+selected):continue
            st=structure(result)
            if st is not None and st in seen_shapes:continue
            if st is not None:seen_shapes.add(st)
            rt=root_template(row['problem'],result)
            if rt is not None and rt in seen_roots:continue
            if rt is not None:seen_roots.add(rt)
            seen.add(normalized);selected.append({'macro_id':mid,'problem':{k:v for k,v in row.items() if k!='selection_pool'},'selection_pool':row['selection_pool'],'execution':result})
            if len(selected)==10:break
        chosen+=selected
        source_details=[{'task_id':r['task_id'],'input':r['input_structure'],'output':r['output_structure']} for r in midops]
        bank.append({'macro_id':mid,'type':['compact_thought','executable_macro'],'subject':['algebra','intermediate_algebra'],'status':'research_pilot_only','source_task_ids':sourceids,'source_operations':source_details,
          'trigger':{'all_of':[{'feature':'question_grammar_or_unique_roots_polynomial'},{'any_of':[{'feature':'numeric_QQ_polynomial'}]},{'guard':'exact_certificate'}]},
          'guard_implementation':'inspect_question in flowevo_bot.rmmd.macros; exact QQ, bounded degree, no missing parameters',
          'compact_thought':COMPACT[mid],'compact_estimated_tokens':(len(COMPACT[mid].encode())+3)//4,'compact_cap':100,
          'executable_entry':'flowevo_bot.rmmd.macros.inspect_question','certificate_scope':'full_task_only_for_exact_remainder_grammar' if mid=='polynomial_remainder' else 'intermediate_only',
          'claim':'engineered mathematical recognizer substantiated by real source operations, not a newly discovered theorem'})
        screen.append({'macro_id':mid,'source_tasks':len(sourceids),'eligible_original_dev':sum(r['selection_pool']=='unused_original_dev' for r,_ in eligible[mid]),'eligible_supplement_train':sum(r['selection_pool']!='unused_original_dev' for r,_ in eligible[mid]),'pool_denominator':len(pool),'expected_eligible_rate':len(eligible[mid])/len(pool),'selected':len(selected),'prompt_overhead_estimated':(len(COMPACT[mid].encode())+3)//4,
          'replaceable_reasoning':'all remainder computation for exact grammar' if mid=='polynomial_remainder' else 'coefficient normalization and Newton recurrence; final target still LLM',
          'verification_cost':'bounded exact local SymPy and independent coefficient recurrence/companion trace; zero LLM calls','build_cost_tokens':0,
          'recommendation':'pilot' if len(sourceids)>=2 and selected else 'reject_insufficient_evidence','break_even_incremental':'0 token build cost; prompt benefit unknown before A/B/C; CPU+engineering unpriced','break_even_full_cost':'795435 divided by observed unconditional per-task savings; undefined until measured',
          'uncertainty':'question-only scope coverage from training-side pool, not MATH test distribution; source extraction is conservative and incomplete'})
    write(OUT/'data/macro_skill_bank.json',bank);write(OUT/'data/macro_candidates.json',screen);table(OUT/'data/macro_screening.csv',screen)
    write(OUT/'data/dev_tasks.json',chosen);write_lines(OUT/'data/coverage_screen.jsonl',routing)
    write(OUT/'data/selection_manifest.json',{'entire_original_dev':len(dev),'entire_original_train':len(train),'excluded_previous_task_ids':len(used),'eligible_public_pool_denominator':len(pool),'original_dev_unused_denominator':sum(r['selection_pool']=='unused_original_dev' for r in pool),'original_train_unused_denominator':sum(r['selection_pool']!='unused_original_dev' for r in pool),'prefilter_inspected':len(candidates),'selection_rule':'question-only; exclude all 700 old train +350 old dev +20 V2 tasks; reject digit-masked clones; prefer unused dev; lexical ID ordering; at most10 each; no gold read','selection_sha256':sha(OUT/'data/dev_tasks.json'),'selected_count':len(chosen),'local_seconds':time.perf_counter()-started,'api_calls':0})
    print(screen,flush=True)
if __name__=='__main__':main()
