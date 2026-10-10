"""Development-only evidence: extraction-cap ablation and warm interleaved timings.

No confirmation questions are loaded here. Coverage process timings are sensitive
to imports/caches; only repeated warmed paired timings can test a cost gate.
"""
import sys,time,statistics,collections
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.compositional_v4.mining import extract_trace
from flowevo_bot.compositional_v4.runtime import solve
from flowevo_bot.compositional_v4.dsl import MANUAL_PROGRAM

def main():
    cap_cpu();source=lines(RMMD/'data/clean_success_traces.jsonl')
    metrics=[]
    for cap in (48,96):
        start=time.perf_counter();ops=[]
        for row in source:ops.extend(extract_trace(row,max_spans=cap)[0])
        verified=[o for o in ops if o['verification_status']=='verified']
        metrics.append({'max_math_spans':cap,'verified_operations':len(verified),
            'verified_source_traces':len({o['source_task_id'] for o in verified}),'seconds':time.perf_counter()-start})
    write(OUT/'evidence/extraction_cap_ablation.json',metrics)
    bank=read(OUT/'automatic_macro_bank.json');legacy=read(V3/'data/automatic_macro_bank.json')
    candidates=[]
    for split in ('dev-engineering','dev-selection'):
        for r in lines(OUT/f'evidence/{split}.scored.jsonl'):
            if r['method']=='C' and r['result']['full_execution'] and r['result']['module']=='v4_integer_congruence':candidates.append(r)
    times=[]
    for row in candidates:
        for _ in range(10):
            for method in ('B','C'):solve(row['question'],method,bank,legacy)
        for i in range(100):
            values={}
            for method in (('B','C') if i%2 else ('C','B')):
                start=time.perf_counter_ns();r=solve(row['question'],method,bank,legacy)
                values[method]=time.perf_counter_ns()-start
                assert r['full_execution'] and r['answer']==row['result']['answer']
            times.append({'task_id':row['task_id'],'repetition':i,'B_nanoseconds':values['B'],'C_nanoseconds':values['C']})
    table(OUT/'evidence/interleaved_local_cost.csv',times,fields=['task_id','repetition','B_nanoseconds','C_nanoseconds'])
    mb=statistics.median(x['B_nanoseconds'] for x in times) if times else None
    mc=statistics.median(x['C_nanoseconds'] for x in times) if times else None
    write(OUT/'evidence/local_cost_gate.json',{'source':'engineering+selection only; no heldout access','independent_tasks':len(candidates),
        'repeats_per_task':100,'B_median_ns':mb,'C_median_ns':mc,'C_over_B':mc/mb if mb else None,
        'cost_gate_passed':bool(mb and mc<=.8*mb),'programs_identical':bool(bank and tuple(bank[0]['program'])==MANUAL_PROGRAM),
        'meaning':'local CPU/wall latency only, cannot establish token savings; identical programs imply no algorithmic cost gain',
        'coverage_timing_caveat':'initial engineering dispatch B-first in each pair; later split dispatch balanced; total process times include cold imports and cross-method caches, not causal evidence'})
    print(metrics,'paired_tasks',len(candidates),'B_ns',mb,'C_ns',mc)
if __name__=='__main__':main()
