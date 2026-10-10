"""Question-only decontamination and deterministic grouped allocation, before mining V4.

Global LCS normalized similarity >= .9 is a conservative superset of the old
SequenceMatcher >= .9 rule (the latter cannot exceed an optimal common sequence).
No labels, candidate parser or macro coverage is consulted during allocation.
"""
import sys, collections, time
from concurrent.futures import ProcessPoolExecutor
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.features import normalize_problem
from rapidfuzz import process, fuzz

TEXTS=[]
def similarity_worker(i):
    return [(i,i+1+j,score) for _,score,j in process.extract_iter(TEXTS[i],TEXTS[i+1:],scorer=fuzz.ratio,score_cutoff=90)]

def main():
    global TEXTS
    cap_cpu(); start=time.perf_counter()
    if (OUT/'dataset_split_manifest.json').exists(): raise RuntimeError('split already frozen')
    pool=lines(ROOT/'data/manifests/math_grouped/train.problems.jsonl')+lines(ROOT/'data/manifests/math_grouped/dev.problems.jsonl')
    lookup={x['task_id']:x for x in pool}; assert len(lookup)==7500
    used={x['task_id'] for x in lines(ROOT/'data/manifests/math_grouped/dev.problems.jsonl')}
    audit=[]
    for path in [ROOT/'experiments/math500_goldfree_20261009/manifests/train.problems.jsonl',
                 ROOT/'experiments/math500_goldfree_20261009/manifests/dev.problems.jsonl',
                 RMMD/'data/coverage_screen.jsonl']:
        rows=lines(path); ids={x['task_id'] for x in rows}; used|=ids
        audit.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path),'task_count':len(ids),'use':'historically exposed'})
    for path in [ROOT/'experiments/flowevo_bot_v2_math500/data/dev_tasks.json', RMMD/'data/dev_tasks.json']:
        ids={x['problem']['task_id'] for x in read(path)}; used|=ids
        audit.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path),'task_count':len(ids),'use':'historically exposed'})
    used &= lookup.keys()
    ids=sorted(lookup); texts=[normalize_problem(lookup[i]['problem'],True) for i in ids]
    parent=list(range(len(ids)))
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    # Stream only high-score upper-triangle pairs; no dense similarity matrix.
    TEXTS=texts
    edges=[]
    with ProcessPoolExecutor(max_workers=12) as pool:
        for matches in pool.map(similarity_worker,range(len(ids)),chunksize=16):
            for i,j,score in matches:
                union(i,j);edges.append({'a':ids[i],'b':ids[j],'score':score})
    groups=collections.defaultdict(list)
    for i,tid in enumerate(ids):groups[find(i)].append(tid)
    splits={'train-build':sorted(x['task_id'] for x in lines(RMMD/'data/clean_success_traces.jsonl')),
            'dev-engineering':[],'dev-selection':[],'heldout-confirmation':[]}
    excluded=[]; assignments=[]
    for members in groups.values():
        gh=digest(sorted(normalize_problem(lookup[t]['problem'],True) for t in members))
        if set(members)&used:
            excluded.extend(t for t in members if t not in used)
            assigned='historical_exposure_component'
        else:
            n=int(digest(['V4-20261010',gh])[:8],16)%4
            assigned='dev-engineering' if n==0 else 'dev-selection' if n==1 else 'heldout-confirmation'
            splits[assigned].extend(members)
        assignments.append({'component_hash':gh,'task_ids':members,'split':assigned})
    write(OUT/'evidence/duplicate_components.json',assignments)
    write_lines(OUT/'evidence/near_duplicate_edges.jsonl',edges)
    for name, members in splits.items():
        if name!='train-build':write_lines(OUT/f'snapshots/{name}.problems.jsonl',[lookup[t] for t in sorted(members)])
    write(OUT/'dataset_split_manifest.json',{'created_at':now(),'source':'local MATH original train only; no test access',
        'historically_exposed_count':len(used),'historically_exposed_ids':sorted(used),'additional_near_duplicate_exclusions':sorted(excluded),
        'old_1115_status':'seen in V3, entirely excluded from fresh pools','splits':{k:{'count':len(v),'ids':sorted(v)} for k,v in splits.items()},
        'allocation':'SHA256 of digit-masked near-duplicate connected components; 1/4 engineering, 1/4 selection, 1/2 confirmation',
        'similarity':'all-pairs digit-masked character LCS (RapidFuzz ratio) >=0.9; no length/prefix blocking',
        'near_duplicate_edges':len(edges),'structural_independence_limit':'excludes numeric clones and near-duplicate wording; broad mathematical family overlap is expected and is reported after freeze; not a proof against all semantic duplicates',
        'historical_sources':audit,'public_source_hashes':{n:sha(ROOT/f'data/manifests/math_grouped/{n}.problems.jsonl') for n in ['train','dev']},
        'public_split_hashes':{n:sha(OUT/f'snapshots/{n}.problems.jsonl') for n in splits if n!='train-build'},
        'source_trace_sha256':sha(RMMD/'data/clean_success_traces.jsonl'),'labels_read':False,'macro_screening_before_allocation':False,
        'wall_seconds':time.perf_counter()-start})
    # Frozen before dev selection and, more importantly, before confirmation access.
    write(OUT/'config.json',{'created_at':now(),'model':'deepseek-flash','temperature':0,'max_tokens':4096,
        'system':'You are an expert programmer and mathematician.','gold_reflection':False,'correctness_retries':False,
        'api_concurrency':64,'local_workers':12,'new_api_calls_cap':120,'new_tokens_cap':200000,
        'gate':{'min_certified_composite_macros':1,'min_confirmation_eligible':12,'min_confirmation_structural_classes':3,
            'min_C_only_coverage':1,'alternative_cost_advantage':'measured same-coverage C total local median latency <=0.8*B over 100 interleaved repeats with no higher fallback; no inferred token benefit',
            'required_tests_pass':True,'max_false_takeovers':0},
        'pilot':'if gate passes, 12 eligible plus 3 negatives, at most 120 calls/200000 total actual tokens; otherwise NOT RUN',
        'interpreter':{'max_ast_nodes':96,'max_ast_depth':12,'max_program_nodes':6,'max_integer_bits':8192,'max_modulus':10000,'max_exponent':1000000,'timeout_seconds':3,'memory_bytes':536870912},
        'selection':'minimum trace-consistent instruction count, then lexicographic program order; no heldout tuning',
        'manual_baseline':'same parser, primitives and independent verifier; independently fixed general modular computation plan',
        'A_usage_if_no_pilot':None})
    print({k:len(v) for k,v in splits.items()},'old',len(used),'duplicate_excluded',len(excluded),flush=True)
if __name__=='__main__':main()
