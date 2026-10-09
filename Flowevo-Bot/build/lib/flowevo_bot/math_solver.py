"""Gold-blind orchestration: only ProblemView can cross the solving boundary."""
from runtime.config import MODES
from code_math.baseline import base_prompt, HistoryLibrary
from .common import digest
from .schemas import ProblemView, RouteDecision, Submission, Provenance
from .taxonomy import detect_subject
from .skill_retriever import MathSubjectRetriever
from .cost_router import MathCostAwareRouter
from .prompt_builder import compact_prompt, repair_prompt, history_prompt
from .evaluator import extract_answer
from .math_executor import MathExecutor
from .token_accounting import estimate_tokens


class MathSolver:
    def __init__(self, client, config, bank, mode):
        if mode not in MODES:
            raise ValueError('Unknown mode')
        self.client, self.config, self.bank, self.mode = client, config, bank, mode
        self.history = HistoryLibrary(bank.history)
        self.router_inputs = []

    def solve(self, task: ProblemView, *, split='test', purpose=None):
        if type(task) is not ProblemView:
            raise TypeError('Solver accepts only ProblemView, never an evaluation record')
        self.router_inputs.append(task.model_dump())
        bank_hash = self.bank.bank_hash
        subject, origin = detect_subject(task)
        decision = RouteDecision(route='base',subject=subject,subject_source=origin,reason='base mode')
        prompt=base_prompt(task);context='';strategy_tokens=0
        if self.mode=='flowevo_context_goldfree' and self.config.strategy.enabled:
            context=self.history.retrieve(task)
            if context:
                decision=decision.model_copy(update={'route':'history','reason':'frozen clean historical solution'})
                prompt=history_prompt(task,context)
                strategy_tokens=estimate_tokens(context)
        elif self.mode not in ('base_onepass','flowevo_goldfree') and self.config.strategy.enabled:
            if self.mode=='subject_strategy_costaware' and self.config.router.cost_aware and self.config.router.allow_skip_skill:
                decision=MathCostAwareRouter(self.config).route(task,self.bank)
            else:
                settings=self.config.strategy.model_copy()
                if self.mode=='bot_template':
                    settings=settings.model_copy(update={'cross_subject_retrieval':True})
                active_only=self.mode in ('subject_strategy_admission','subject_strategy_costaware')
                candidates=MathSubjectRetriever(settings).retrieve(task,self.bank,active_only=active_only)
                selected=candidates[:1]
                if selected and self.config.strategy.max_injected_skills==2:
                    for candidate in candidates[1:]:
                        if (candidate.strategy_pattern in selected[0].composition_tags
                            and selected[0].strategy_pattern in candidate.composition_tags):
                            selected.append(candidate)
                            break
                decision=RouteDecision(route=('template' if self.mode=='bot_template' else 'strategy') if selected else 'base',
                    subject=subject,subject_source=origin,skill_ids=[s.skill_id for s in selected],
                    retrieved_skill_ids=[s.skill_id for s in candidates],reason='fixed retrieval ablation' if selected else 'no eligible strategy')
            if decision.skill_ids:
                skills=[self.bank.skills[sid] for sid in decision.skill_ids]
                if self.mode=='bot_template':
                    context='\n\n'.join('Thought template: '+s.name+'\n'+'\n'.join(s.strategy_steps)+'\nChecks: '+'; '.join(s.verification_rules) for s in skills)
                    prompt=history_prompt(task,context)
                else:
                    prompt=compact_prompt(task,skills,self.config.strategy.max_skill_prompt_tokens)
                    context='\n\n'.join(s.compact_prompt for s in skills)
                strategy_tokens=estimate_tokens(context)
        execution=None
        if self.config.router.enable_verified_execution and self.mode=='subject_strategy_costaware':
            execution=MathExecutor().execute(task)
        call_ids=[];retry_count=0
        if execution and execution.full_task_verified:
            decision=RouteDecision(route='execution',subject=subject,subject_source=origin,reason=execution.method)
            solution=f'The answer is {execution.answer}.';first=solution;strategy_tokens=0
        else:
            kind=purpose or ('skill_solve' if decision.route!='base' else 'base_solve')
            reply=self.client.complete(prompt,task_id=task.task_id,purpose=kind,route=decision.route,skill_ids=decision.skill_ids)
            solution=first=reply.text;call_ids.append(reply.call.call_id)
            # Format-only repair: no mathematical pass/fail signal exists here.
            budget=0 if self.mode=='base_onepass' else self.config.evaluation.max_format_retries
            while extract_answer(solution) is None and retry_count<budget:
                reply=self.client.complete(repair_prompt(task,solution,context),task_id=task.task_id,
                    purpose='retry',route=decision.route,skill_ids=decision.skill_ids)
                solution=reply.text;call_ids.append(reply.call.call_id);retry_count+=1
        provenance=Provenance(origin_split=split,source_task_id=task.task_id,first_pass=retry_count==0,
            gold_exposed=False,reference_solution_exposed=False,external_verifier_used=execution is not None,
            eligible_for_skill_learning=False,evidence_hash=digest({'task':task.model_dump(),'calls':call_ids}),
            synthetic=self.client.simulated)
        if self.bank.bank_hash!=bank_hash:
            raise RuntimeError('Solver mutated frozen bank')
        return Submission(task_id=task.task_id,first_solution=first,solution=solution,
            first_answer=extract_answer(first),final_answer=extract_answer(solution),retry_count=retry_count,
            decision=decision,call_ids=list(dict.fromkeys(call_ids)),skill_prompt_tokens=strategy_tokens,
            bank_hash=bank_hash,split=split,provenance=provenance).frozen_submission()
