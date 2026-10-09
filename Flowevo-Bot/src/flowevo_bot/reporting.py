"""Measured cost reports. Pairwise savings stay unknown without a paired baseline."""
import csv
import json
from pathlib import Path
from collections import Counter,defaultdict
from .common import write_json,jsonl,read_json
from .token_accounting import amortized_cost,estimate_tokens,break_even_uses


def make_rows(problems,submissions,scores,ledger,mode,bank):
    tasks={p.task_id:p for p in problems};evaluation={s['task_id']:s for s in scores}
    rows=[]
    for s in submissions:
        p=tasks[s.task_id];totals=ledger.totals([c for c in ledger.calls if c.call_id in s.call_ids])
        rows.append({'task_id':s.task_id,'split':s.split,'subject':s.decision.subject or 'unknown','subject_source':s.decision.subject_source,
            'level':p.level,'condition':mode,'selected_skill_ids':s.decision.skill_ids,'route':s.decision.route,
            'retrieved_skill_ids':s.decision.retrieved_skill_ids,'route_reason':s.decision.reason,
            'skill_prompt_tokens':s.skill_prompt_tokens,'skill_prompt_tokens_estimated':True,
            'llm_input_tokens':totals['prompt_tokens'],'llm_output_tokens':totals['completion_tokens'],
            'total_tokens':totals['total_tokens'],'calls':totals['calls'],'estimated_calls':totals['estimated_calls'],
            'first_pass_correct':evaluation[s.task_id]['first_pass_correct'],
            'final_correct':evaluation[s.task_id]['final_correct'],'retry_count':s.retry_count,
            'gold_exposed':s.provenance.gold_exposed,'bank_version':bank.version,'bank_hash':bank.bank_hash,
            'submission_seal':s.seal,'simulated':s.provenance.synthetic,'problem_tokens_estimated':estimate_tokens(p.problem)})
    return rows


def summarize(rows,bank,ledger):
    n=len(rows);correct=sum(r['final_correct'] for r in rows);tokens=sum(r['total_tokens'] for r in rows)
    subjects={}
    for subject in sorted({r['subject'] for r in rows}):
        subset=[r for r in rows if r['subject']==subject]
        subjects[subject]={'n':len(subset),'accuracy':sum(r['final_correct'] for r in subset)/len(subset)}
    stats=[s.token_stats for s in bank.skills.values()]
    # Shared trace costs are counted once via the retained history, not once per overlapping skill.
    trace_calls={c.call_id:c for t in bank.history for c in t.calls}
    build=sum(c.total_tokens for c in trace_calls.values())+sum(s.get('distillation',0) for s in stats)
    validation=sum(s.get('validation',0) for s in stats)
    maintenance=sum(s.get('skill_revision',0) for s in stats)
    if bank.build_costs:
        build=bank.build_costs.get('trace_generation',0)+bank.build_costs.get('distillation',0)
        validation=bank.build_costs.get('validation',0)
        maintenance=bank.build_costs.get('maintenance',0)
    skill_metrics={}
    for skill in bank.skills.values():
        uses=[r for r in rows if skill.skill_id in r['selected_skill_ids']]
        expected=(skill.validation_stats.base_total_tokens-skill.validation_stats.skill_total_tokens)/max(1,skill.validation_stats.eligible_cases)
        skill_metrics[skill.skill_id]={'eligible_tasks':sum(skill.skill_id in r['retrieved_skill_ids'] for r in rows),
            'actual_uses':len(uses),'successful_uses':sum(r['final_correct'] for r in uses),
            'build_cost':skill.token_stats.get('trace_generation',0)+skill.token_stats.get('distillation',0),
            'validation_cost':skill.token_stats.get('validation',0),'total_solve_tokens_saved':None,
            'net_tokens_saved':None,'estimated_break_even_uses':break_even_uses(sum(skill.token_stats.values()),expected)}
    return {'n':n,'accuracy':correct/n if n else None,
        'first_pass_accuracy':sum(r['first_pass_correct'] for r in rows)/n if n else None,
        'gold_blind_accuracy':correct/n if n and not any(r['gold_exposed'] for r in rows) else None,
        'subjects':subjects,'retrieval_hit_rate':sum(bool(r['retrieved_skill_ids']) for r in rows)/n if n else 0,
        'injection_rate':sum(r['route'] in ('strategy','history','template') for r in rows)/n if n else 0,
        'skip_rate':sum(r['route']=='base' for r in rows)/n if n else 0,
        'input_tokens':sum(r['llm_input_tokens'] for r in rows),'output_tokens':sum(r['llm_output_tokens'] for r in rows),
        'total_tokens':tokens,'tokens_per_correct':tokens/correct if correct else None,
        'costs':amortized_cost(build,validation,maintenance,tokens),
        'bank_size':len(bank.skills),'bank_subjects':dict(Counter(s.subject for s in bank.skills.values())),
        'average_skill_prompt_tokens':sum(estimate_tokens(s.compact_prompt) for s in bank.skills.values())/max(1,len(bank.skills)),
        'skill_metrics':skill_metrics,'call_purposes':ledger.by_purpose(),
        'simulated':all(r['simulated'] for r in rows),'real_api_calls':sum(not c.simulated for c in ledger.calls),
        'retrieval_api_tokens':0,'retrieval_method':'local rules, no model calls',
        'warning':'Offline mock metrics are engineering fixtures, not evidence of model accuracy or savings.' if all(r['simulated'] for r in rows) else ''}


def write_run(output,rows,summary):
    output=Path(output)
    with (output/'episodes.jsonl').open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    if rows:
        with (output/'episodes.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
            for row in rows:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    write_json(output/'summary.json',summary)


def analyze(runs_dir,output):
    runs_dir=Path(runs_dir)
    paths=sorted(runs_dir.rglob('episodes.jsonl'))
    if not paths:raise ValueError('No completed run episodes found')
    all_rows=[r for p in paths for r in jsonl(p)]
    keys=[(r['condition'],r['task_id']) for r in all_rows]
    if len(set(keys))!=len(keys):raise ValueError('Repeated task/condition runs; select one declared replicate')
    by_condition=defaultdict(dict)
    for r in all_rows:by_condition[r['condition']][r['task_id']]=r
    base=by_condition.get('base_onepass',{})
    summaries={read_json(p.parent/'summary.json')['mode']:read_json(p.parent/'summary.json') for p in paths}
    for mode,summary in summaries.items():
        if 'base_onepass' in summaries:
            base_summary=summaries['base_onepass']
            for field in ('model','temperature','max_output_tokens','manifest_hash','split'):
                if summary.get(field)!=base_summary.get(field):
                    raise ValueError(f'Unfair paired comparison: {field} differs')
    pairs=[]
    for condition,rows in by_condition.items():
        if condition=='base_onepass':continue
        for tid,row in rows.items():
            if tid in base:
                b=base[tid]
                if b['simulated']!=row['simulated']:raise ValueError('Cannot pair mock with real results')
                pairs.append({'task_id':tid,'condition':condition,'base_correct':b['final_correct'],
                    'skill_correct':row['final_correct'],'solve_tokens_saved':b['total_tokens']-row['total_tokens'],
                    'selected_skill_ids':row['selected_skill_ids']})
    amortized={}
    for mode,summary in summaries.items():
        matched=[p for p in pairs if p['condition']==mode]
        if not matched:continue
        solve_saved=sum(p['solve_tokens_saved'] for p in matched)
        costs=summary['costs']
        overhead=costs['build_cost']+costs['validation_cost']+costs['maintenance_cost']
        attribution={}
        for pair in matched:
            ids=pair['selected_skill_ids']
            if len(ids)==1:
                sid=ids[0]
                attribution[sid]=attribution.get(sid,0)+pair['solve_tokens_saved']
        amortized[mode]={'paired_tasks':len(matched),'paired_solve_tokens_saved':solve_saved,
            'build_validation_maintenance_tokens':overhead,'net_tokens_saved':solve_saved-overhead,
            'single_skill_solve_tokens_saved':attribution,
            'per_skill_net_tokens_saved':{sid:saved-summary['skill_metrics'][sid]['build_cost']-summary['skill_metrics'][sid]['validation_cost'] for sid,saved in attribution.items()},
            'warning':'Attribution applies only to single-skill decisions; shared trace build costs are attributed conservatively.'}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    write_json(output.with_suffix('.pairwise.json'),pairs)
    write_json(output.with_suffix('.amortized.json'),amortized)
    lines=['# Experiment analysis','', 'Mock results are not research measurements.','',
           '| Mode | N | Accuracy | Input tokens | Output tokens |', '|---|---:|---:|---:|---:|']
    for mode,rows in sorted(by_condition.items()):
        values=list(rows.values());n=len(values)
        lines.append(f"| {mode} | {n} | {sum(r['final_correct'] for r in values)/n:.3f} | {sum(r['llm_input_tokens'] for r in values)} | {sum(r['llm_output_tokens'] for r in values)} |")
    lines += ['',f'Paired comparisons: {len(pairs)}. See `{output.with_suffix(".pairwise.json").name}`.',
              'A missing paired baseline means token savings are unknown, not zero.',
              'No statistical non-inferiority conclusion is claimed by this prototype.']
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return pairs
