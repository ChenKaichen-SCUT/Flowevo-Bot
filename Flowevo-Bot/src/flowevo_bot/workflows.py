"""Train-build -> paired train-dev admission -> frozen test; labels read last."""
from pathlib import Path
from runtime.llm_client import LLMClient
from .common import digest,read_json,write_json
from .token_accounting import TokenLedger
from .strategy_bank import StrategyBank
from .math_solver import MathSolver
from .checkpoint import Checkpoint
from .evaluator import Evaluator
from .trace_collector import collect_trace
from .thought_distiller import ThoughtDistiller,cluster_traces
from .skill_validator import SkillValidator
from .reporting import make_rows,summarize,write_run
from .mock import mock_response
from .provenance import assert_independent
from code_math.loader import load_manifest


def evaluate_manifest(config,manifest_path,bank,mode,output_dir,*,split='test',dry_run=False,allow_paid=False,resume=False):
    manifest,problems,labels=load_manifest(manifest_path,split)
    if not dry_run and bank.synthetic:raise ValueError('Synthetic bank forbidden for real evaluation')
    if not dry_run:
        if manifest.get('synthetic'):raise ValueError('Fixture manifest cannot be a real experiment')
        if not (allow_paid or config.llm.allow_paid_api):raise PermissionError('Pass --allow-paid-api explicitly for real inference')
    if split=='test':
        # Guard source/test overlap even in admission-free ablations.
        assert_independent([t.problem for t in bank.history],problems)
    checkpoint=Checkpoint(output_dir,config=config,bank_hash=bank.bank_hash,split=split,mode=mode,
        manifest_hash=digest(manifest),simulated=dry_run,resume=resume)
    ledger=TokenLedger(Path(output_dir)/'calls.json')
    client=LLMClient(config.llm,ledger,allow_paid=allow_paid,mock_handler=mock_response if dry_run else None)
    solver=MathSolver(client,config,bank,mode)
    for task in problems:
        if task.task_id in checkpoint.records:continue
        submission=solver.solve(task,split=split,purpose='trace_generation' if split=='train-build' else None)
        checkpoint.commit(submission)
    submissions=[checkpoint.records[p.task_id] for p in problems]
    # Frozen answers persisted BEFORE labels are loaded.
    evaluator=Evaluator(labels,manifest['labels_hash'])
    scores=evaluator.score(submissions)
    rows=make_rows(problems,submissions,scores,ledger,mode,bank)
    summary=summarize(rows,bank,ledger)
    summary.update({'mode':mode,'model':config.llm.model,'temperature':config.llm.temperature,
                    'max_output_tokens':config.llm.max_output_tokens,'manifest_hash':digest(manifest),
                    'split':split,'bank_hash':bank.bank_hash,'config_hash':digest(config.model_dump())})
    write_run(output_dir,rows,summary)
    traces=[]
    if split=='train-build':
        for p,s,score in zip(problems,submissions,scores):
            calls=[c for c in ledger.calls if c.call_id in s.call_ids]
            traces.append(collect_trace(p,s,score,calls,prompts=[ledger.prompts[c.call_id] for c in calls if c.call_id in ledger.prompts]))
        write_json(Path(output_dir)/'traces.json',[t.model_dump(mode='json') for t in traces])
    return summary,traces


def build_bank(config,train_manifest,dev_manifest,output,*,dry_run=False,allow_paid=False,resume=False):
    if not config.distillation.enabled:raise ValueError('Distillation disabled in config')
    train_info,train,_=load_manifest(train_manifest,'train-build')
    dev_info,dev,dev_labels=load_manifest(dev_manifest,'train-dev')
    assert_independent(train,dev)
    output=Path(output)
    if output.exists() and not resume:raise FileExistsError('Bank exists; choose a new destination')
    work=output.with_suffix('.work')
    identity={'config_hash':digest(config.model_dump()),'train_manifest_hash':digest(train_info),
              'dev_manifest_hash':digest(dev_info),'simulated':dry_run}
    identity_path=work/'build_identity.json'
    if identity_path.exists():
        if read_json(identity_path)!=identity:
            raise ValueError('Build checkpoint config/manifest/simulation mismatch')
    else:
        if output.exists():raise ValueError('Existing bank has no matching build identity')
        write_json(identity_path,identity)
    if output.exists() and resume:
        return StrategyBank.load(output,frozen=False,allow_synthetic=dry_run)
    # Per-task checkpoints make source generation resumable without resubmitting completed work.
    empty=StrategyBank(synthetic=dry_run,frozen=True)
    _,traces=evaluate_manifest(config,train_manifest,empty,'base_onepass',work/'train',
        split='train-build',dry_run=dry_run,allow_paid=allow_paid,resume=resume)
    bank=StrategyBank(synthetic=dry_run)
    from .provenance import eligible
    bank.history=[t for t in traces if eligible(t)]
    source_calls=TokenLedger(work/'train'/'calls.json').calls
    remaining_calls=config.llm.max_calls-len(source_calls)
    remaining_tokens=config.llm.max_total_tokens-sum(c.total_tokens for c in source_calls)
    if remaining_calls<1 or remaining_tokens<1:
        raise RuntimeError('Build budget exhausted by source generation; source checkpoints are preserved')
    build_llm=config.llm.model_copy(update={'max_calls':remaining_calls,'max_total_tokens':remaining_tokens})
    client=LLMClient(build_llm,TokenLedger(work/'build_calls.json'),allow_paid=allow_paid,
                     mock_handler=mock_response if dry_run else None)
    distiller=ThoughtDistiller(client,config)
    validator=SkillValidator(config)
    candidates=[]
    for cluster in cluster_traces(bank.history,config.distillation.min_source_traces):
        skill=distiller.distill(cluster,bank.skills.values())
        if skill is None:continue
        candidates.append(skill.model_dump(mode='json'))
        duplicate=bank.duplicate(skill) if config.distillation.merge_duplicates else None
        if duplicate:
            original=bank.skills[duplicate]
            # Re-distill union of sources; no concatenation or truncation of strategies.
            source_ids=set(original.source_task_ids+skill.source_task_ids)
            cluster=[t for t in bank.history if t.problem.task_id in source_ids]
            combined=distiller.distill(cluster,bank.skills.values(),purpose='skill_revision',revision_note='Merge the common strategy; preserve exceptions.')
            if combined is None:continue
            skill=bank.merge([duplicate],combined)
        if config.admission.enabled:
            skill=validator.validate(skill,cluster,dev,Evaluator(dev_labels,dev_info['labels_hash']),client)
        bank.add(skill)
    write_json(work/'candidates.json',candidates)
    train_calls=TokenLedger(work/'train'/'calls.json').calls
    bank.cost_calls=train_calls+client.ledger.calls
    bank.build_costs={
        'trace_generation':sum(c.total_tokens for c in train_calls),
        'distillation':sum(c.total_tokens for c in client.ledger.calls if c.purpose=='distillation'),
        'validation':sum(c.total_tokens for c in client.ledger.calls if c.purpose in ('skill_validation','retry')),
        'maintenance':sum(c.total_tokens for c in client.ledger.calls if c.purpose=='skill_revision'),
    }
    bank.save(output)
    write_json(work/'build_summary.json',{'synthetic':dry_run,'source_traces':len(bank.history),
        'clusters':len(cluster_traces(bank.history,config.distillation.min_source_traces)),
        'skills':len(bank.skills),'statuses':{s.skill_id:s.status for s in bank.skills.values()},
        'build_call_costs':client.ledger.by_purpose(),'real_api_calls':sum(not c.simulated for c in client.ledger.calls),
        'note':'Mock bank never enables real inference. Candidate/shadow is not validated research evidence.'})
    return bank
