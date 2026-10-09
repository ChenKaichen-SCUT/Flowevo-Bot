#!/usr/bin/env python3
"""Read-only, network-disabled audit of the completed experiment.
Writes only this diagnostics directory. No core code, bank, or history is modified.
"""
import argparse, csv, hashlib, itertools, json, math, os, re, socket, statistics, subprocess, sys
from collections import Counter,defaultdict
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
AUDIT=Path(__file__).resolve().parents[1]
PROJECT=AUDIT.parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from flowevo_bot.common import digest,read_json,write_json,jsonl
from flowevo_bot.schemas import SkillRecord,Trace,Submission,TokenCall,ProblemView
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.features import extract_features,matches,normalize_problem,near_duplicate,PATTERNS
from flowevo_bot.provenance import assert_independent,eligible,detect_feedback_exposure
from flowevo_bot.token_accounting import estimate_tokens,TokenLedger
from flowevo_bot.skill_validator import SkillValidator,wilson
from flowevo_bot.cost_router import CostPredictor,MathCostAwareRouter
from flowevo_bot.math_solver import MathSolver
from code_math.baseline import base_prompt
from code_math.loader import load_manifest
from runtime.config import Config
from runtime.llm_client import SYSTEM,Reply
EXP=PROJECT/'experiments/math500_goldfree_20261009'

def no_network(*a,**kw):raise AssertionError('This diagnostic must not contact a network or an LLM')
socket.socket.connect=no_network

def csv_write(name,rows):
    if not rows:return
    with (AUDIT/'data'/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(PROJECT))
def git_commit(p):
    r=subprocess.run(['git','-C',str(p),'rev-parse','HEAD'],capture_output=True,text=True)
    return r.stdout.strip() if r.returncode==0 else 'unknown (not a Git checkout at audit start)'

def frozen_files():
    files=list((PROJECT/'src').rglob('*.py'))+list((PROJECT/'configs').glob('*'))
    files+=list(EXP.rglob('*'))
    for root in (PROJECT.parent/'FlowEvo',PROJECT.parent/'buffer-of-thought-llm'):
        files+=list((root/'src').rglob('*.py')) if (root/'src').exists() else list(root.glob('*.py'))
    return {str(p):sha(p) for p in files if p.is_file() and '__pycache__' not in p.parts}

def gate_analysis(skill,cfg,disable=None):
    a=cfg.admission;s=skill.validation_stats;n=s.eligible_cases
    enough_sources=len(set(skill.source_task_ids))>=a.min_source_traces
    clean_prov=(len(skill.provenance)==len(skill.source_task_ids) and all(p.eligible_for_skill_learning for p in skill.provenance)
                and len(skill.source_trace_hashes)==len(skill.source_task_ids))
    independent=s.independent and s.evidence_hash==digest(s.pairwise) and bool(s.pairwise)
    saving=(s.base_total_tokens-s.skill_total_tokens)/n if n else None
    overhead=sum(skill.token_stats.values())
    gates=[
      ('independent_evidence',independent,True,bool(independent),'quarantine'),
      ('observed_harm',s.base_only_correct,0,s.base_only_correct==0,'quarantine'),
      ('source_count',len(set(skill.source_task_ids)),a.min_source_traces,enough_sources,'shadow'),
      ('clean_provenance',clean_prov,True,clean_prov,'shadow'),
      ('dev_count',n,a.min_dev_eligible_cases,n>=a.min_dev_eligible_cases,'shadow'),
      ('structural_evidence',s.structurally_distinct_cases,1,s.structurally_distinct_cases>0,'shadow'),
      ('saving_lower_bound',s.saving_lower_bound if n else None,'> 0',s.saving_lower_bound>0 if n else None,'shadow'),
      ('amortized_saving',saving*a.expected_future_uses if n else None,overhead,(saving*a.expected_future_uses>overhead) if n else None,'shadow')]
    first=None;state='active';detail=[]
    for name,val,threshold,passed,failstate in gates:
        disabled=(disable=='source_count' and name=='source_count') or (disable=='dev_count' and name=='dev_count') or (disable=='positive_cost' and name in ('saving_lower_bound','amortized_saving'))
        effective=True if disabled else passed
        if effective is False and first is None:first=name;state=failstate
        detail.append({'gate_name':name,'observed_value':val,'required_threshold':threshold,'decision':'disabled_offline' if disabled else 'unknown' if passed is None else 'pass' if passed else 'fail',
            'execution_reached':first is None or first==name,'reason':'computed from stored statistics; no model calls','evidence_source':'real_bank.json:validation_stats/token_stats + skill_validator.py:admit'})
    return {'status':state,'first_rejection_gate':first,'all_failed_gates':[x['gate_name'] for x in detail if x['decision']=='fail'],
            'unknown_gates':[x['gate_name'] for x in detail if x['decision']=='unknown'],'gates':detail,'mean_saving':saving,'overhead':overhead,
            'estimated_net_saving':saving*a.expected_future_uses-overhead if n else None}

def main():
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    before=frozen_files()
    write_json(AUDIT/'tests/input_hashes_before.json',before)
    cfg=Config.model_validate(read_json(EXP/'config.json'));bank=StrategyBank.load(EXP/'real_bank.json')
    skills=list(bank.skills.values());assert len(skills)==12
    raw=read_json(EXP/'real_bank.json');write_json(AUDIT/'data/skills_full.json',raw['skills'])
    notes=read_json(AUDIT/'scripts/quality_notes.json')
    manifests={};tasks={};labelpaths={}
    for name in ('train','dev','test'):
        manifests[name],tasks[name],labelpaths[name]=load_manifest(EXP/'manifests'/f'{name}.json')
    history={t.problem.task_id:t for t in bank.history}
    source_ids={tid for s in skills for tid in s.source_task_ids}
    write_json(AUDIT/'data/evidence/source_traces.json',[history[tid].model_dump(mode='json') for tid in sorted(source_ids)])
    diagnostics=[];all_matches=[];admissions=[];examples={};stats={};counterfactuals=[]
    for idx,skill in enumerate(skills,1):
        sid=f'S{idx:02}';note=notes[sid];v=skill.validation_stats
        rows=[]
        for t in tasks['dev']:
            f=extract_features(t);subject=t.subject==skill.subject;trigger=bool(set(skill.trigger_features)&f)
            pre=set(skill.preconditions)<=f;negative=bool(set(skill.negative_triggers)&f)
            effective=subject and trigger and pre and not negative
            rows.append({'skill_id':skill.skill_id,'audit_id':sid,'task_id':t.task_id,'subject':t.subject,'same_subject':subject,
                'trigger_match':trigger,'precondition_pass':pre,'negative_trigger':negative,'eligible':effective,
                'features':sorted(f),'missing_preconditions':sorted(set(skill.preconditions)-f),
                'reason':'eligible' if effective else 'subject' if not subject else 'trigger' if not trigger else 'preconditions' if not pre else 'negative_trigger'})
        all_matches+=rows
        same=[r for r in rows if r['same_subject']];trigger=[r for r in same if r['trigger_match']]
        pre=[r for r in trigger if r['precondition_pass']];neg=[r for r in pre if r['negative_trigger']];elig=[r for r in rows if r['eligible']]
        unique={}
        for r in elig:
            t=next(t for t in tasks['dev'] if t.task_id==r['task_id'])
            unique.setdefault(normalize_problem(t.problem,True),t.task_id)
        assert set(list(unique.values())[:60])=={r['task_id'] for r in v.pairwise}
        original_state=SkillValidator(cfg).admit(skill).status
        gates=gate_analysis(skill,cfg);assert gates['status']==skill.status==original_state
        for g in gates['gates']:
            admissions.append({'skill_id':skill.skill_id,'audit_id':sid,**g,'first_rejection_gate':gates['first_rejection_gate'],
                'all_rejection_reasons':gates['all_failed_gates'],'missing_fields':[],'missing_evidence':gates['unknown_gates']})
        n=v.eligible_cases
        sources=[history[tid] for tid in skill.source_task_ids]
        source_matches=sum(matches(skill,extract_features(t.problem)) for t in sources)
        normalized_unique=len({normalize_problem(t.problem.problem,True) for t in sources})
        near_pairs=[(a.problem.task_id,b.problem.task_id) for a,b in itertools.combinations(sources,2) if near_duplicate(a.problem.problem,b.problem.problem)]
        actual=[]
        for row in v.pairwise:
            path=EXP/'validation_v2'/skill.skill_id/(row['task_id']+'.submission.json')
            sub=Submission.model_validate(read_json(path));sub.assert_frozen()
            assert sub.seal==row['skill_seal']
            actual.append(sub.decision.route=='strategy' and skill.skill_id in sub.decision.skill_ids)
        # The budgeted experiment stamped structurally_distinct=True after a
        # text-overlap check; this is not proof of new mathematical structure.
        stats[sid]={'skill_id':skill.skill_id,'source_matches':source_matches,'source_n':len(sources),'source_normalized_unique':normalized_unique,
            'source_near_duplicate_pairs':near_pairs,'dev_subject':len(same),'dev_trigger':len(trigger),'dev_precondition':len(pre),
            'dev_negative_excluded':len(neg),'dev_eligible':len(elig),'dev_deduplicated':len(unique),'dev_actual_uses':sum(actual),
            'base_correct':v.both_correct+v.base_only_correct if n else None,'skill_correct':v.both_correct+v.skill_only_correct if n else None,
            'harm':v.base_only_correct if n else None,'benefit':v.skill_only_correct if n else None,
            'missing_preconditions':dict(Counter(f for r in trigger for f in r['missing_preconditions'])),
            'missing_evidence':['independent_skill_on_execution','empirical_cost_saving'] if not n else ['replicated_trials','mathematical_structure_generalization'],
            **gates}
        problems={t.task_id:t for t in tasks['dev']}
        def example(candidates):
            if not candidates:return {'status':'missing (no such dev example)'}
            r=candidates[0];return {**r,'problem':problems[r['task_id']].problem,'evidence_path':f'manifests/dev.problems.jsonl task_id={r["task_id"]}'}
        examples[sid]={'eligible':example(elig),'trigger_but_missing_precondition':example([r for r in trigger if not r['precondition_pass']]),
            'nearby_no_trigger':example(sorted([r for r in same if not r['trigger_match']],key=lambda r:-len(set(r['features'])&set(skill.trigger_features+skill.preconditions)))),
            'excluded_by_negative':example(neg)}
        for scenario,disabled in [('keep_all',None),('disable_min_source','source_count'),('disable_min_dev','dev_count'),('disable_positive_cost','positive_cost'),('disable_historical_usage','historical_usage')]:
            cf=gate_analysis(skill,cfg,disabled)
            estimates=[CostPredictor(cfg).estimate(problems[r['task_id']],skill) for r in elig] if cf['status']=='active' else []
            router_pass=[e for e in estimates if not e.get('uncertain',True) and e.get('expected_saving',0)>0 and e.get('saving_lower_bound',0)>0 and e.get('predicted_accuracy_drop_upper',1)<=cfg.router.max_allowed_accuracy_drop]
            counterfactuals.append({'audit_id':sid,'skill_id':skill.skill_id,'scenario':scenario,'original_status':skill.status,'rule_status':cf['status'],
                'first_rejection_gate':cf['first_rejection_gate'],'eligible_dev_router_passes':len(router_pass) if estimates else None,
                'historical_usage_gate_exists':False,'interpretation':'rule-only; not new effectiveness evidence'})
        diagnostics.append({'skill_id':skill.skill_id,'audit_id':sid,'name':skill.name,'subject':skill.subject,'strategy_pattern':skill.strategy_pattern,'status':skill.status,
            'source_task_count':len(sources),'source_gold_exposed':any(t.provenance.gold_exposed for t in sources),
            'compact_prompt_tokens':estimate_tokens(skill.compact_prompt),'token_measurement':'estimate utf8_bytes/3, not model tokenizer',
            'dev_total':len(tasks['dev']),'dev_subject_total':len(same),'dev_trigger_matches':len(trigger),'dev_precondition_passes':len(pre),'dev_actual_uses':sum(actual),
            'dev_skill_correct':stats[sid]['skill_correct'],'dev_base_correct':stats[sid]['base_correct'],
            'estimated_token_saving':gates['estimated_net_saving'],'observed_token_saving':gates['mean_saving'],
            'first_rejection_gate':gates['first_rejection_gate'],'all_rejection_reasons':gates['all_failed_gates'],
            'missing_evidence':stats[sid]['missing_evidence'],'quality_assessment':note['assessment'],'suggested_next_action':note['priority'],
            'evidence_status':'insufficient_evidence' if n<10 else 'single_run_paired_evidence_not_proof'})
    csv_write('skill_diagnostics.csv',diagnostics);csv_write('skill_task_matches.csv',all_matches);csv_write('gate_counterfactuals.csv',counterfactuals)
    write_json(AUDIT/'data/evidence/trigger_examples.json',examples)
    write_json(AUDIT/'data/evidence/skill_statistics.json',stats)
    with (AUDIT/'data/admission_decisions.jsonl').open('w') as f:
        for row in admissions:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    # All 39 paired observations and minimal decisive response excerpts.
    paired=[{'skill_id':s.skill_id,**r} for s in skills for r in s.validation_stats.pairwise]
    csv_write('dev_pairwise.csv',paired)
    decisive=[]
    for s in skills:
        for r in s.validation_stats.pairwise:
            if r['base_correct']!=r['skill_correct']:
                t=next(t for t in tasks['dev'] if t.task_id==r['task_id'])
                entry={'skill_id':s.skill_id,'problem':t.model_dump(mode='json'),'stored_score':r}
                for mode in ('base',s.skill_id):
                    entry[mode]={'submission':read_json(EXP/'validation_v2'/mode/(t.task_id+'.submission.json')),
                                 'calls':read_json(EXP/'validation_v2'/mode/(t.task_id+'.calls.json'))}
                decisive.append(entry)
    write_json(AUDIT/'data/evidence/discordant_dev_cases.json',decisive)
    # Leakage and lineage audit uses stored submissions/prompts/hashes, not just flags.
    for a,b in [('train','dev'),('train','test'),('dev','test')]:assert_independent(tasks[a],tasks[b])
    training_checkpoint={x['task_id']:Submission.model_validate(x) for x in read_json(EXP/'train/checkpoint.json')['submissions']}
    train_ledger=TokenLedger(EXP/'train/calls.json')
    lineage=[]
    for tid in sorted(source_ids):
        t=history[tid];s=training_checkpoint[tid];s.assert_frozen()
        calls=train_ledger.for_task(tid)
        assert eligible(t) and s.retry_count==0 and len(calls)==1 and s.first_solution==t.first_solution
        assert calls[0].purpose=='trace_generation' and not calls[0].simulated
        assert train_ledger.prompts[calls[0].call_id]==base_prompt(t.problem)
        lineage.append({'task_id':tid,'subject':t.problem.subject,'trace_hash':t.trace_hash,'submission_seal':s.seal,
            'origin_split':t.provenance.origin_split,'model_calls':1,'retries':0,'prompt_equals_clean_base':True,
            'gold_exposed':False,'reference_solution_exposed':False,'evidence':'train/checkpoint.json + train/calls.json + real_bank.json'})
    for s in skills:
        assert [history[tid].trace_hash for tid in s.source_task_ids]==s.source_trace_hashes
    distill_proof=[]
    for path in sorted((EXP/'distillation_v2').glob('*.calls.json')):
        ledger=read_json(path)
        for cid,prompt in ledger['prompts'].items():
            payload=json.loads(prompt)
            for e in payload['examples']:
                assert set(e)=={'task_id','problem','model_first_solution'}
                assert e['task_id'] in source_ids and e['model_first_solution']==history[e['task_id']].first_solution
            distill_proof.append({'call_id':cid,'prompt_hash':digest(prompt),'example_ids':[e['task_id'] for e in payload['examples']],
                'schema_keys':sorted(payload),'no_gold_fields_in_examples':True})
    write_json(AUDIT/'data/evidence/source_lineage.json',lineage)
    write_json(AUDIT/'data/evidence/distillation_lineage.json',distill_proof)
    # Costs: preserve separate requests across method conditions even if identical signatures.
    groups=defaultdict(list)
    for c in bank.cost_calls:groups[('build',c.purpose,c.model)].append(c)
    ledgers={};summaries={};records={};checkpoints={}
    for mode in ('flowevo','flowevo_bot'):
        ledgers[mode]=TokenLedger(EXP/mode/'calls.json');summaries[mode]=read_json(EXP/mode/'summary.json')
        records[mode]={r['task_id']:r for r in read_json(EXP/mode/'rows.json')}
        checkpoints[mode]={x['task_id']:Submission.model_validate(x) for x in read_json(EXP/mode/'checkpoint.json')['submissions']}
        for c in ledgers[mode].calls:groups[(mode,c.purpose,c.model)].append(c)
        for field in ('prompt_tokens','completion_tokens','total_tokens'):assert sum(getattr(c,field) for c in ledgers[mode].calls)==summaries[mode][field]
    cost_rows=[{'stage':stage,'purpose':purpose,'model':model,'calls':len(cs),'input_tokens':sum(c.prompt_tokens for c in cs),
        'output_tokens':sum(c.completion_tokens for c in cs),'total_tokens':sum(c.total_tokens for c in cs),'estimated_calls':sum(c.estimated for c in cs)} for (stage,purpose,model),cs in sorted(groups.items())]
    csv_write('cost_breakdown.csv',cost_rows)
    assert sum(r['total_tokens'] for r in cost_rows)==2234706
    test_pairwise=[];config_compare=[];nobank_checks=[];prompt_examples=[];input_savings_by_route=Counter()
    empty=StrategyBank(frozen=True)
    class ReplayClient:
        simulated=False
        def __init__(self,tid):self.tid=tid;self.requests=[]
        def complete(self,prompt,**kwargs):
            self.requests.append({'prompt':prompt,**kwargs});c=ledgers['flowevo_bot'].for_task(self.tid)[0]
            return Reply(ledgers['flowevo_bot'].responses[c.call_id],c)
    for task in tasks['test']:
        tid=task.task_id;a=records['flowevo'][tid];b=records['flowevo_bot'][tid]
        test_pairwise.append({'task_id':tid,'subject':task.subject,'flowevo_correct':a['final_correct'],'bot_correct':b['final_correct'],
            'flowevo_input_tokens':a['prompt_tokens'],'flowevo_output_tokens':a['completion_tokens'],
            'bot_input_tokens':b['prompt_tokens'],'bot_output_tokens':b['completion_tokens'],
            'flowevo_route':a['route'],'bot_route':b['route'],
            'pair_outcome':'both_correct' if a['final_correct'] and b['final_correct'] else 'flowevo_only' if a['final_correct'] else 'bot_only' if b['final_correct'] else 'both_wrong'})
        requests={}
        for method in ('flowevo','flowevo_bot'):
            c=ledgers[method].for_task(tid)[0]
            rawpath=EXP/method/'task_calls'/(tid+'.provider')/(c.call_id+'.json')
            rawcall=read_json(rawpath);requests[method]=rawcall['request']
            assert rawcall['usage']['total_tokens']==c.total_tokens
        ar,br=requests['flowevo'],requests['flowevo_bot']
        assert ar['messages'][0]==br['messages'][0] and ar['messages'][0]['content']==SYSTEM
        assert all(ar[k]==br[k] for k in ('model','temperature','max_tokens'))
        ap=ar['messages'][1]['content'];bp=br['messages'][1]['content']
        assert bp==base_prompt(task)
        assert ap==bp if a['route']=='base' else ap.endswith(bp) and ap.startswith('Here is a similar solved problem for reference:\nExample:\nProblem: ')
        if len(prompt_examples)<2 and (not prompt_examples or prompt_examples[0]['flowevo_route']!=a['route']):
            prompt_examples.append({'task_id':tid,'flowevo_route':a['route'],'flowevo_request':ar,'bot_request':br})
        input_savings_by_route[a['route']]+=a['prompt_tokens']-b['prompt_tokens']
        full_decision=MathCostAwareRouter(cfg).route(task,bank);empty_decision=MathCostAwareRouter(cfg).route(task,empty)
        assert full_decision==empty_decision and full_decision.route=='base'
        replay=ReplayClient(tid);sub=MathSolver(replay,cfg,empty,'subject_strategy_costaware').solve(task)
        assert len(replay.requests)==1 and replay.requests[0]['prompt']==bp and sub.solution==checkpoints['flowevo_bot'][tid].solution
        assert replay.requests[0]['route']=='base' and replay.requests[0]['skill_ids']==[]
        nobank_checks.append({'task_id':tid,'actual_bot_prompt_equals_empty_bank':True,'router_decision_equal':True,'calls':1,'retries':0,
                             'fresh_model_output_equivalence':'unknown stochastic counterfactual; replay does not infer a new sample'})
    csv_write('task_pairwise.csv',test_pairwise);csv_write('nobank_replay.csv',nobank_checks)
    write_json(AUDIT/'data/evidence/prompt_examples.json',prompt_examples)
    comparison_fields=[
      ('model','deepseek-flash','deepseek-flash','alias same; immutable backend checkpoint unknown'),
      ('precise_backend_version','unknown','unknown','provider returns alias only'),
      ('dataset_manifest',summaries['flowevo']['manifest_hash'],summaries['flowevo_bot']['manifest_hash'],'same ordered 500 task list'),
      ('system_prompt',SYSTEM,SYSTEM,'identical in all 1000 requests'),
      ('base_user_prompt','native math base prompt','same base prompt','byte-identical after removal of history prefix'),
      ('history_injection','461 tasks; 39 without','0 tasks','actual input difference'),
      ('strategy_injection',0,0,'Bot active skill count 0; FlowEvo uses historical solution context'),
      ('temperature',0,0,'requested only; provider default thinking enabled makes this ineffective'),
      ('max_tokens',4096,4096,'same thinking/output budget'),
      ('thinking_parameter','omitted','omitted','provider default; exact effective server settings not recorded'),
      ('retry',0,0,'500 paid calls each'),('concurrency',64,64,'configured HTTP workers'),
      ('output_instruction','The answer is [your answer].','The answer is [your answer].','same'),
      ('scorer',summaries['flowevo']['grader'],summaries['flowevo_bot']['grader'],'same; known format false negative remains in historical scores'),
      ('token_source','provider usage','provider usage','no estimated calls'),
      ('cache_hit_input_tokens',22016,128,'token counts include cache hits; RMB cost not inferred'),
      ('execution_order','first 500-task condition','second 500-task condition','not randomized/interleaved; provider load/sampling confound'),
      ('truncated_responses',30,27,'treated as wrong in both; output cost retained'),
      ('subject_metadata','original MATH type carried in manifest; native retriever ignores subject','same metadata; subject-aware retriever','same provenance, different algorithm use')]
    config_compare=[{'field':f,'flowevo':a,'flowevo_bot':b,'interpretation':note} for f,a,b,note in comparison_fields]
    csv_write('prompt_config_comparison.csv',config_compare)
    # Regression counterexamples, completely synthetic and explicitly not model evidence.
    binary=[''.join(x) for x in itertools.product('01',repeat=3)]
    orbits={min(s[i:]+s[:i] for i in range(3)) for s in binary}
    assert len(orbits)==4 and len(binary)/3!=len(orbits)
    semantics={'S02_compact_OR_vs_machine_AND':True,'nonzero_is_lexical_not_proved':True,
               'ratio_in_rational': 'ratio' in extract_features(ProblemView(task_id='synthetic',problem='a rational expression')),
               'quadratic_in_x_power_20':'quadratic' in extract_features(ProblemView(task_id='synthetic',problem=r'x^20')),
               'symmetry_counterexample':{'synthetic':True,'labelled_binary_strings':8,'rotation_orbits':4,'naive_quotient':8/3},
               'composition_compatible_pairs':sum(a.strategy_pattern in b.composition_tags and b.strategy_pattern in a.composition_tags for a,b in itertools.combinations(skills,2)),
               'usage_history_gate_exists':False,'confidence_min_n_for_0_8':40,
               'zero_harm_zero_benefit_min_n_for_1pct_wilson_upper':next(n for n in range(1,1000) if wilson(0,n)[1]<=.01)}
    write_json(AUDIT/'data/evidence/implementation_checks.json',semantics)
    aggregate={'skill_count':12,'source_tasks':len(source_ids),'source_self_match_zero':sum(x['source_matches']==0 for x in stats.values()),
        'dev_zero':sum(x['dev_eligible']==0 for x in stats.values()),'dev_insufficient_10':sum(s.validation_stats.eligible_cases<10 for s in skills),
        'retrieval_coverage_unique':len({r['task_id'] for r in all_matches if r['same_subject'] and r['trigger_match']}),
        'eligible_coverage_unique':len({r['task_id'] for r in all_matches if r['eligible']}),
        'actual_skill_use_unique':len({r['task_id'] for r in paired}),'dev_paired_count':len(paired),
        'observed_mean_cost_increase_skills':sum(s.validation_stats.eligible_cases>0 and s.validation_stats.skill_total_tokens>s.validation_stats.base_total_tokens for s in skills),
        'primary_rejection_counts':dict(Counter(x['first_rejection_gate'] for x in stats.values())),
        'counterfactual_active':{scenario:[x['audit_id'] for x in counterfactuals if x['scenario']==scenario and x['rule_status']=='active'] for scenario in {x['scenario'] for x in counterfactuals}},
        'test_paired_outcomes':dict(Counter(x['pair_outcome'] for x in test_pairwise)),
        'input_savings_by_route':dict(input_savings_by_route),'total_api_calls_previous':sum(x['calls'] for x in cost_rows),
        'total_tokens_previous':sum(x['total_tokens'] for x in cost_rows),'new_llm_calls':0,'new_tokens':0,'new_api_cost':0}
    write_json(AUDIT/'data/audit_summary.json',aggregate)
    subjects=[]
    for subject in sorted({t.subject for t in tasks['train']}):
        ss=[s for s in skills if s.subject==subject]
        subjects.append({'subject':subject,'training_tasks':sum(t.subject==subject for t in tasks['train']),
            'correct_traces':sum(t.problem.subject==subject for t in bank.history),'candidate_skills':len(ss),
            'dev_tasks':sum(t.subject==subject for t in tasks['dev']),
            'trigger_pairs':sum(r['same_subject'] and r['trigger_match'] and r['subject']==subject for r in all_matches),
            'eligible_pairs':sum(r['eligible'] and r['subject']==subject for r in all_matches),
            'actual_pairs':sum(s.validation_stats.eligible_cases for s in ss)})
    csv_write('subject_coverage.csv',subjects)
    manifest={'project_commit':git_commit(PROJECT),'source_repository_commits':{n:git_commit(PROJECT.parent/n) for n in ('FlowEvo','buffer-of-thought-llm')},
      'config_hashes':{'experiment_config':sha(EXP/'config.json'),'model_dump':digest(cfg.model_dump())},
      'dataset_manifest_hashes':{n:sha(EXP/'manifests'/f'{n}.json') for n in manifests},'bank_hashes':{'content':bank.bank_hash,'file':sha(EXP/'real_bank.json')},
      'model_name':'deepseek-flash','immutable_model_version':'unknown','run_ids':['math500_goldfree_20261009'],
      'report_generation_time':datetime.now(timezone(timedelta(hours=8), 'Asia/Shanghai')).isoformat(),
      'new_llm_calls':0,'new_tokens':0,'new_api_cost':0,'currency':'no new billing',
      'original_experiment_path':str(EXP),'audit_script_network_blocked':True,
      'source_records':[{'relative_to_project':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in (EXP/'real_bank.json',EXP/'train/calls.json',EXP/'train/checkpoint.json',EXP/'flowevo/calls.json',EXP/'flowevo_bot/calls.json',EXP/'source_frozen_before_test.json')],
      'unknowns':['complete pre-session test exposure','immutable provider model checkpoint','fresh stochastic Bot-NoBank outcomes','mathematical structural independence beyond text similarity'],
      'scope':'offline diagnostic; historical scores, core algorithms, and thresholds unchanged'}
    write_json(AUDIT/'manifest.json',manifest)
    after=frozen_files();assert before==after,'Protected inputs changed during diagnostics'
    write_json(AUDIT/'tests/read_only_check.json',{'pass':True,'protected_files':len(before),'all_sha256_unchanged':True,'network_disabled':True,'new_llm_calls':0})
    print(json.dumps(aggregate,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
