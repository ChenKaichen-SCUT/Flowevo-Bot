import sys,time
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.goal_v3.learning import discover

def main():
    cap_cpu();source=PREVIOUS/'data/clean_success_traces.jsonl'
    traces=lines(source);assert len(traces)==603 and all(r['offline_correct'] is True and r['gold_exposed'] is False for r in traces)
    result=discover(traces)
    for key,name in [('operations','reasoning_operations.jsonl'),('excluded_source_extractions','excluded_source_extractions.jsonl'),('candidate_attempts','macro_candidates.jsonl')]:write_lines(OUT/'data'/name,result[key])
    for key,name in [('bank','automatic_macro_bank.json'),('failed_families','discovery_failures.json'),('search_statistics','synthesis_search.json')]:write(OUT/'data'/name,result[key])
    write(OUT/'evidence/discovery_runtime.json',{'wall_seconds':result['wall_seconds'],'source_count':len(traces),'source_sha256':sha(source),'api_calls':0,'learned_macros':len(result['bank']),'kind':'input-output program synthesis from successful model trajectories, not automatic natural-language goal parser learning'})
    print(json.dumps({'bank':result['bank'],'failures':result['failed_families'],'search':result['search_statistics']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
