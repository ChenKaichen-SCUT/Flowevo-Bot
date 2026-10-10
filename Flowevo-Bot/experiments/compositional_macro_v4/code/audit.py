"""Reproduce the V3 funnel, preserving the distinction between spans and semantics."""
import sys, collections, shutil, time
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.goal_v3.learning import extract_operations
from flowevo_bot.goal_v3.goals import parse_goal
from flowevo_bot.rmmd.macros import fragments

def main():
    cap_cpu(); start=time.perf_counter()
    manifest=read(ROOT.parent/'UPLOAD_MANIFEST.json')
    # Entire published baseline is protected, not only selected experimental files.
    protected=[x for x in manifest['files'] if x['path']!='指引.txt']
    changed=[x['path'] for x in protected if not (ROOT.parent/x['path']).is_file() or sha(ROOT.parent/x['path'])!=x['sha256']]
    if changed: raise RuntimeError(('baseline_changed',changed))
    write(OUT/'snapshots/protected_history.json',protected)
    shutil.copy2(ROOT.parent/'指引.txt',OUT/'snapshots/指引.txt')
    traces=lines(RMMD/'data/clean_success_traces.jsonl'); ops, excluded=extract_operations(traces)
    assert len(traces)==603 and len(ops)==9
    old=lines(RMMD/'data/reasoning_operations.jsonl')
    byid=collections.defaultdict(list)
    for x in old:byid[x['task_id']].append(x)
    opby={x['task_id']:x for x in ops}; exby={x['task_id']:x for x in excluded}
    groups=collections.defaultdict(list)
    for x in ops:groups[x['output_goal']['kind']].append(x)
    repeated={k for k,v in groups.items() if len(v)>=2}
    supported={'root_sum','root_product'}
    records=[]
    for row in traces:
        tid=row['task_id']; g=parse_goal(row['problem']); op=opby.get(tid)
        verified=[x for x in byid[tid] if x['verification_status'].startswith(('symbolically_verified','verified_operation'))]
        kind=op['output_goal']['kind'] if op else None
        reason='B' if not op else 'C' if kind not in repeated else 'D' if kind not in supported else None
        records.append({'task_id':tid,'problem':row['problem'],'source_hash':row['source_hash'],
            'goal_state':g.state,'goal_kind':g.kind,'v3_first_rejection':exby.get(tid),
            'stages':{'clean':True,'goal_parsed':g.state=='parsed','math_objects':g.state=='parsed',
              'transformation_spans':op is not None,'io_relation':op is not None,
              'repeated_family':kind in repeated,'independent_sources':kind in repeated,
              'dsl_expressible_and_prover_supported':kind in supported,'certified_family':kind in supported},
            'primary_failure_category':reason,'secondary_failure_categories':['E'] if kind=='polynomial_remainder' else [],
            'reuse_value':'not_determined' if reason=='B' else 'supported_in_scope',
            'verified_old_operation_count':len(verified),'verified_old_operations':verified,
            'uninterpreted_steps':fragments(row['model_solution'])[:6],
            'source_solution_excerpt':row['model_solution'][:2400],
            'warning':'V3 transformation evidence means copied equality/congruence spans, not a semantically understood chain.'})
    write_lines(OUT/'extraction_failures.jsonl',records)
    keys=['clean','goal_parsed','math_objects','transformation_spans','io_relation','repeated_family','independent_sources','dsl_expressible_and_prover_supported','certified_family']
    funnel=[]; previous=len(traces)
    for key in keys:
        n=sum(x['stages'][key] for x in records)
        funnel.append({'stage':key,'unit':'source_traces','accepted':n,'rejected_from_previous':previous-n,
            'caveat':'copied spans only; semantic chain not established' if key=='transformation_spans' else ''});previous=n
    funnel.append({'stage':'automatic_macros','unit':'programs','accepted':2,'rejected_from_previous':'NA_unit_change','caveat':'4 source traces support 2 scalar ASTs'})
    table(OUT/'extraction_funnel.csv',funnel)
    stats={'clean':603,'operations':len(ops),'categories':dict(collections.Counter(x['primary_failure_category'] or 'admitted' for x in records)),
        'any_verified_operation_sources':len({x['task_id'] for x in records if x['verified_old_operation_count']}),
        'parser_rejected_with_verified_operation':sum(x['primary_failure_category']=='B' and x['verified_old_operation_count']>0 for x in records),
        'A_proven_no_reuse':0,'old_operation_counts':dict(collections.Counter(x['operation_type'] for x in old)),
        'source_sha256':sha(RMMD/'data/clean_success_traces.jsonl'),'protected_files':len(protected),'baseline_changes':changed,
        'wall_seconds':time.perf_counter()-start,'completed_at':now(),'source_of_semantics':'manual grammar, not inferred from LaTex copying'}
    write(OUT/'evidence/v3_audit.json',stats)
    examples=[]
    for cat,tid in [('B','math_train_number_theory_210'),('C','math_train_algebra_558'),('D/E','math_train_intermediate_algebra_891')]:
        x=next(x for x in records if x['task_id']==tid)
        examples.append(f"### {cat}: {tid}\n\n{x['problem']}\n\nSource solution excerpt (model-generated training trace):\n\n```text\n{x['source_solution_excerpt']}\n```\n\nFailure: {x['v3_first_rejection'] or ('family='+x['goal_kind'])}.\n")
    text='# 01 — 603 条轨迹的提取瓶颈\n\n'
    text+=' → '.join(str(x['accepted'])+(' programs' if x['unit']=='programs' else ' traces') for x in funnel)+'。\n\n'
    text+=f"最大损失是完整目标文法：603→9，丢失594（98.51%）。learning.extract_operations 在检查任何解题步骤前即以 parse_goal.state 过滤。9条的 transformation_spans 只是复制等式/同余片段；不能称为9条完整语义链。\n\n历史逐步提取在267条轨迹中找到至少一项已验证操作；其中{stats['parser_rejected_with_verified_operation']}条被V3目标文法拒绝。这是 parser 与过程提取耦合过早的直接证据；不证明这些操作均可构成完整任务宏。\n\n"
    text+='A：没有任何轨迹被证明绝无复用价值，计0；未理解步骤保持unknown。B：594条目标入口损失，不等于594条已证明有复用结构。C：3条分别为e2、倒数和、对称有理式，来源不足。D：2条余式来源有结构差异，但标量DSL不支持多项式过程。E：这2条同时缺少余式目标证明规则（共因，不重复计入主类别）；V3的12个拟合候选被反例否决属于验证成功拒错，不是验证器失效。\n\n'
    text+='重复结构按输出目标族统计：root_sum、root_product、remainder共6条；两来源/结构门槛后仍6条；DSL与prover联合门槛后4条；4条支持2条已认证标量程序。完整逐轨迹状态、失败点和真实来源步骤见JSONL。\n\n'
    text+='\n'.join(examples)
    text+='\n本轮选择：从完整目标入口解耦步骤提取，优先研究训练数据反复出现的整数同余计算。多项式/有理式/约束集类型暂缓；不先堆砌算子。\n'
    (OUT/'01_EXTRACTION_BOTTLENECK.md').write_text(text)
    print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':main()
