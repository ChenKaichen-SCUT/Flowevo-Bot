"""Opt-in CLI for scoring sealed outputs. No solver or LLM client imports."""
import argparse,json
from pathlib import Path
from math_evaluation.adapters import OfflineMathEvaluator,OfflineScoringConfig,from_flowevo_task
from math_evaluation.engine import MathEvaluatorV3

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,help='sealed record JSONL; or native runner records with --tasks')
    p.add_argument('--output',required=True)
    p.add_argument('--evaluator',choices=('legacy','fixed','v3'),default='legacy')
    p.add_argument('--workers',type=int,default=12)
    p.add_argument('--unknown-output')
    p.add_argument('--tasks',help='native CodeTaskInstance JSONL, exported from load_math()')
    p.add_argument('--sealed',action='store_true',help='required affirmation for native runner records without seal metadata')
    a=p.parse_args();src=Path(a.input);out=Path(a.output)
    if src.resolve()==out.resolve() or out.exists():p.error('output must be a new file; historical data may not be overwritten')
    records=[json.loads(x) for x in src.read_text().splitlines() if x.strip()]
    if a.tasks:
        if not a.sealed:p.error('native runner records require --sealed')
        from core.schemas import CodeTaskInstance
        tasks={r.task_id:r for r in (CodeTaskInstance(**json.loads(line)) for line in Path(a.tasks).read_text().splitlines() if line.strip())}
        records=[from_flowevo_task(tasks[r['task_id']],dict(r,source_path=str(src)),submission_sealed=True) for r in records]
    if any(r.get('submission_sealed') is not True for r in records):p.error('all inputs must be sealed before offline scoring')
    cfg=OfflineScoringConfig(a.evaluator,a.workers);results=OfflineMathEvaluator(cfg).evaluate_batch(records)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results))
    if a.unknown_output:
        if Path(a.unknown_output).exists():p.error('unknown queue already exists')
        MathEvaluatorV3.export_unknown(results,a.unknown_output)
    print(json.dumps({'records':len(results),'evaluator':a.evaluator,'config_hash':cfg.hash(),'new_llm_calls':0}))
if __name__=='__main__':main()
