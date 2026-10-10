import sys,time,collections
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.compositional_v4.mining import extract_trace,cluster
from flowevo_bot.compositional_v4.synthesis import synthesize

def main():
    cap_cpu();t=time.perf_counter()
    assert (OUT/'evidence/v3_audit.json').exists() and (OUT/'dataset_split_manifest.json').exists()
    rows=lines(RMMD/'data/clean_success_traces.jsonl');operations=[];examples=[]
    for row in rows:
        ops,example=extract_trace(row);operations.extend(ops);examples.append(example)
    patterns=cluster(examples);result=synthesize(examples)
    write_lines(OUT/'reasoning_operations.jsonl',operations)
    write(OUT/'pattern_clusters.json',patterns)
    write(OUT/'evidence/source_extractions.json',examples)
    write_lines(OUT/'macro_candidates.jsonl',result['candidates'])
    write(OUT/'automatic_macro_bank.json',result['bank'])
    write(OUT/'synthesis_search.json',result['statistics'])
    write_lines(OUT/'verification_certificates.jsonl',[{'program':x['program'],**x['universal_certificate']} for x in result['candidates']])
    stats={'traces':len(rows),'goal_parsed':sum(x['goal']['parsed'] for x in examples),'verified_io':sum(x['io_verified'] for x in examples),
        'intermediate_candidates':len(patterns['eligible_source_ids']),
        'operation_count':len(operations),'operation_types':dict(collections.Counter(x['operation_type'] for x in operations)),
        'verification_status':dict(collections.Counter(x['verification_status'] for x in operations)),
        'verified_step_sources':len({x['source_task_id'] for x in operations if x['verification_status']=='verified'}),
        'source_ids':[x['source_task_ids'] for x in result['bank']], 'wall_seconds':time.perf_counter()-t,
        'no_question_goal_filter_on_step_extraction':True,'new_api_calls':0}
    write(OUT/'evidence/mining_summary.json',stats)
    print(json.dumps(stats,ensure_ascii=False));print(json.dumps(result['statistics']))
    for b in result['bank']:print(b['macro_id'],b['program'],b['source_task_ids'])
if __name__=='__main__':main()
