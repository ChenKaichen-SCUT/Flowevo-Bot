"""Post-freeze analysis only. No parser, search, selection or runtime mutation."""
import sys,collections,statistics,platform,importlib.metadata
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.compositional_v4.dsl import MANUAL_PROGRAM
from flowevo_bot.features import normalize_problem
from evaluate import verify_freeze

def mdtable(rows,keys):
    return '| '+' | '.join(keys)+' |\n|'+'|'.join(['---']*len(keys))+'|\n'+''.join('| '+' | '.join(str(r.get(k,'')) for k in keys)+' |\n' for r in rows)

def main():
    freeze=verify_freeze();config=read(OUT/'config.json');splits=read(OUT/'dataset_split_manifest.json')
    bank=read(OUT/'automatic_macro_bank.json');audit=read(OUT/'evidence/v3_audit.json');mining=read(OUT/'evidence/mining_summary.json')
    cost=read(OUT/'evidence/local_cost_gate.json');search=read(OUT/'synthesis_search.json');patterns=read(OUT/'pattern_clusters.json')
    allrows=[];summaries=[]
    for split in ('dev-engineering','dev-selection','heldout-confirmation'):
        allrows+=lines(OUT/f'evidence/{split}.scored.jsonl')
        summaries+=read(OUT/f'evidence/{split}.summary.json')
    bytask=collections.defaultdict(dict)
    for r in allrows:bytask[(r['split'],r['task_id'])][r['method']]=r
    pairs=[]
    source_structures={json.dumps(s) for m in bank for s in m['source_structures']}
    for (split,tid),arms in bytask.items():
        b,c=arms['B'],arms['C'];bf=b['result']['full_execution'];cf=c['result']['full_execution']
        pairs.append({'split':split,'task_id':tid,'subject':b['subject'],'B_full':bf,'C_full':cf,
            'B_correct':b['offline_correct'],'C_correct':c['offline_correct'],
            'B_parsed':b['result']['parsed_goal'],'C_parsed':c['result']['parsed_goal'],
            'B_guard':b['result']['guard_pass'],'C_guard':c['result']['guard_pass'],
            'B_module':b['result']['module'],'C_module':c['result']['module'],
            'B_fallback':b['result']['fallback_reason'],'C_fallback':c['result']['fallback_reason'],
            'pair':'both' if bf and cf else 'B_only' if bf else 'C_only' if cf else 'neither',
            'C_source_external_structure':bool(cf and c['result']['module']=='v4_integer_congruence' and json.dumps(c['result']['structure']) not in source_structures)})
    table(OUT/'manual_vs_auto_pairwise.csv',pairs)
    write_lines(OUT/'offline_task_results.jsonl',allrows)
    subject=[]
    for split in ('dev-engineering','dev-selection','heldout-confirmation','ALL_FRESH_POOLS'):
        selected=[r for r in allrows if split=='ALL_FRESH_POOLS' or r['split']==split]
        for sub in sorted({r['subject'] for r in selected}):
            for method in ('B','C'):
                rs=[r for r in selected if r['subject']==sub and r['method']==method]
                full=sum(r['result']['full_execution'] for r in rs)
                subject.append({'split':split,'subject':sub,'method':method,'tasks':len(rs),
                    'parsed':sum(r['result']['parsed_goal'] for r in rs),'guards':sum(r['result']['guard_pass'] for r in rs),
                    'full':full,'independently_correct':sum(r['offline_correct'] is True for r in rs),
                    'C_only':sum(x['pair']=='C_only' and x['subject']==sub and (split=='ALL_FRESH_POOLS' or x['split']==split) for x in pairs) if method=='C' else None,
                    'fallback':len(rs)-full,'coverage':full/len(rs),'V4_full':sum(r['result']['full_execution'] and r['result']['module']=='v4_integer_congruence' for r in rs),
                    'local_seconds_descriptive':sum(r['result']['local_seconds'] for r in rs)})
    table(OUT/'coverage_by_subject.csv',subject)
    table(OUT/'coverage_summary.csv',[{k:v for k,v in x.items() if k!='rejection_reasons'} for x in summaries])
    pairsums={split:dict(collections.Counter(x['pair'] for x in pairs if x['split']==split)) for split in ('dev-engineering','dev-selection','heldout-confirmation')}
    confirmation=[r for r in allrows if r['split']=='heldout-confirmation']
    composite=[r for r in confirmation if r['method']=='C' and r['result']['full_execution'] and r['result']['module']=='v4_integer_congruence']
    types={json.dumps(r['result']['structure']) for r in composite}
    additional=sum(p['pair']=='C_only' for p in pairs if p['split']=='heldout-confirmation')
    false=sum(r['result']['full_execution'] and r['offline_correct'] is not True for r in allrows)
    checks={'certified_composite':len(bank)>=config['gate']['min_certified_composite_macros'],
        'confirmation_eligible':len(composite)>=config['gate']['min_confirmation_eligible'],
        'confirmation_structure_classes':len(types)>=config['gate']['min_confirmation_structural_classes'],
        'new_coverage_or_cost_advantage':additional>=config['gate']['min_C_only_coverage'] or cost['cost_gate_passed'],
        'correctness_tests':freeze['test_count']>0,'no_false_takeovers':false==0}
    gate={'status':'PASS' if all(checks.values()) else 'NOT RUN','checks':checks,'observed':{'certified_composites':len(bank),
        'confirmation_eligible_for_V4':len(composite),'structural_classes':len(types),'C_only':additional,'false_or_unknown_takeovers':false,
        'selection_eligible_for_V4':sum(r['method']=='C' and r['result']['full_execution'] and r['result']['module']=='v4_integer_congruence' and r['split']=='dev-selection' for r in allrows),
        'C_over_B_local_latency':cost['C_over_B']},'preregistered_config_sha256':freeze['config_sha256'],'freeze_hash':freeze['freeze_hash'],
        'new_api_calls':0,'new_input_tokens':0,'new_output_tokens':0,'new_total_tokens':0,
        'A_accuracy':None,'LLM_token_savings':None,'actual_online_LLM_skips':None,
        'explanation':'offline deterministic runs do not constitute A/B/C API performance; unexecuted fallback has unknown accuracy/cost'}
    write(OUT/'paid_gate.json',gate)
    if gate['status']=='PASS':raise RuntimeError('gate passes: execute authorized bounded pilot before producing final NOT RUN report')
    write_lines(OUT/'api_calls.jsonl',[])
    runtime_seconds=sum(read(OUT/f'evidence/{split}.runtime.json')['seconds'] for split in ('dev-engineering','dev-selection','heldout-confirmation'))
    costs=[{'component':'V4_new_model_calls','status':'NOT RUN','calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'local_wall_seconds':None,'money':0,'note':'no API experiment; no observed savings'},
        {'component':'historical_700_source_acquisition','status':'previously_paid_reused','calls':700,'input_tokens':91262,'output_tokens':704173,'total_tokens':795435,'local_wall_seconds':None,'money':None,'note':'includes unsuccessful/unknown traces; not newly billed'},
        {'component':'selected_603_source_subset','status':'subset_do_not_add_again','calls':603,'input_tokens':None,'output_tokens':None,'total_tokens':518212,'local_wall_seconds':None,'money':None,'note':'subset of historical acquisition; new source acquisition = 0'},
        {'component':'V4_extraction_and_synthesis','status':'executed_offline','calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'local_wall_seconds':mining['wall_seconds'],'money':None,'note':'includes synthesis; do not add synthesis again'},
        {'component':'V4_synthesis_and_proof_subset','status':'subset_do_not_add_again','calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'local_wall_seconds':search['wall_seconds'],'money':None,'note':'exact typed search with certificates'},
        {'component':'V4_coverage_and_grading','status':'executed_offline','calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'local_wall_seconds':runtime_seconds,'money':None,'note':'12 processes; monetary CPU cost not instrumented'}]
    table(OUT/'cost_breakdown.csv',costs)
    # Diagnose residual-pool selection bias without inventing a population estimate.
    original=lines(ROOT/'data/manifests/math_grouped/train.problems.jsonl')+lines(ROOT/'data/manifests/math_grouped/dev.problems.jsonl')
    oldscreen={r['task_id'] for r in lines(RMMD/'data/coverage_screen.jsonl')};fresh={p['task_id'] for p in pairs}
    import re
    distribution=[]
    for name,rs in [('original_train_7500',original),('previously_screened_RMMD',[r for r in original if r['task_id'] in oldscreen]),('V4_fresh_residual',[r for r in original if r['task_id'] in fresh])]:
        distribution.append({'population':name,'count':len(rs),'remainder_word':sum(bool(re.search(r'\bremainder\b',r['problem'],re.I)) for r in rs),
            'roots_word':sum(bool(re.search(r'\broots?\b',r['problem'],re.I)) for r in rs),
            'units_or_last_digit':sum(bool(re.search(r'(?:units|last) digit',r['problem'],re.I)) for r in rs)})
    table(OUT/'evidence/residual_pool_bias.csv',distribution)
    fullrecords=[r for r in allrows if r['method']=='C' and r['result']['full_execution']]
    use=[]
    for macro in bank:
        use.append({'macro_id':macro['macro_id'],'training_sources':macro['source_count'],
            **{split:sum(r['result']['selected_macro']==macro['macro_id'] and r['split']==split for r in fullrecords) for split in ('dev-engineering','dev-selection','heldout-confirmation')},
            'actual_online_uses':0})
    table(OUT/'macro_usage.csv',use)
    main=[r for r in summaries if r['module']=='ALL'];confirmationmain=[r for r in main if r['split']=='heldout-confirmation']
    for r in confirmationmain:r['C_new']=0 if r['method']=='C' else '—'
    decision={'decision':'停止该路线','scope':'stop scaling the current automatically executable math macro bank as a MATH token-saving approach; preserve prototype and evidence',
        'reason':['one four-pass composition found within five manually bounded typed alternatives','no heldout use of new macro; only one engineering task outside sources',
            'same chosen program as manual baseline; zero C-only coverage','very low residual-pool coverage, insufficient unbiased fresh data, no measured API benefit'],
        'automatic_next_round':False,'bank_production_admission':False,'paid_experiment':'NOT RUN'}
    write(OUT/'decision.json',decision)

    reports={}
    reports['00_EXECUTIVE_SUMMARY.md']=f'''# V4 结果与科研判断

**停止该路线**：停止把当前自动可执行数学宏库作为 MATH 规模化 token 节省路线继续扩展。本轮确实合成了一个四步组合，但未超过同先验人工工具，确认集中没有新宏的使用证据。不删除既有代码或历史结果。

V3 603→9 的最大损失在完整目标文法入口。594 条被拒绝，其中259条包含旧提取器已验证的数学操作；不能称为无复用价值。完整漏斗及逐轨迹原因见01与JSONL。

V4 解耦目标与步骤提取，在603条中识别703条整数等式/同余操作，涉及291条来源；这不等于291条完整任务策略。整体目标解析仅5条，4条提供可匹配的非最终中间表达式。5个类型合法组合中，选择4来源共同支持的四步程序。原语、文法、守卫与同余规则均为人工设计。

新数据划分：工程1184、选择1229、确认2383；程序发现仍只用603条既有训练首次成功轨迹。旧1549及1115完全排除。确认之前冻结38个文件，hash `{freeze['freeze_hash']}`。

确认集（2383题，V4与冻结V3联合路由）：

{mdtable(confirmationmain,['method','parsed','guards','full','correct','C_new','fallback'])}

其中V4新宏 B/C均完整执行0题；C的1题来自旧V3根和，B的额外1题来自旧V3人工对称工具。工程集中V4两者均正确完成1题，选择集均0题。所有新池4796题合计B3题、C2题正确完整提交；未提交的回退不是错误答题。

付费实验 **NOT RUN**；新增API0、tokens0。A未执行，准确率和token节省均不可测；没有运行MATH-500。193项测试通过。所有4075个参考历史文件按SHA256保护。

限制：剩余未使用题池已被历史筛查和近重复剔除改变分布，不能用这里的覆盖率估计原始MATH总体收益。人工编程工时未计量，不能声称减少人工建库成本。
'''
    reports['02_REASONING_STRUCTURE_MINING.md']=f'''# 02 — 真实轨迹中的操作和组合证据

提取器先扫描每条轨迹的数学片段，不再要求完整题意先解析。字段包含operation_type、input/output_type、input/output_structure、preconditions、transformation、source_task_id、source_step_ids、verification_rule、confidence、provenance。603条均保留自然语言未理解标记。6029条记录中703条数学关系独立验证通过，5326条保留unknown；没有把unknown当作数学错误。

{mdtable([{'kind':k,'count':v} for k,v in mining['operation_types'].items()],['kind','count'])}

每个数值同余使用独立二进制模幂检查，精确等式使用有界整数计算；只验证显式局部关系，不声称解释整个自然语言推理链。未知变量、多项式、分式、集合推理均不勉强解析。

方向选择依据：训练中反复出现先将操作数/幂归约，再合并和/积，再取规范余数。来源210是三项幂和；537是六个连续整数之和；809是三个整数乘积；prealgebra992是乘法与幂的混合表达式。它们有实际中间表达式，不只是最终答案。

归一化保持整数常量的精确值、加法/乘法扁平化与交换排序。变量类型不在本轮范围内，故没有把变量重命名称为已学习能力。受限anti-unification保存不同数值/结构的typed holes并复用重复分歧；这里{sum(p['informative_root'] for p in patterns['anti_unification_pairs'])}/{len(patterns['anti_unification_pairs'])}个来源对保留非空共同根结构。根层IntegerExpressionHole属于弱信息，不能冒充共享数学解法。真正支持组合的是不同来源的已验证中间状态被同一执行序列复现。

这也暴露限制：程序组合在人工提供的通用树遍历原语中搜索；没有从异质自然语言自动推导新的高层数学算法。48片段消融有701操作/290来源，96片段有703/291；提升不能全部归因于去除入口过滤，也不能直接和旧RMMD不同算子集合的267来源作因果比较。

数论以外候选未新增实现。余式仅2源且结构差异大；倒数和/e2等只有1源；一般有理式与有限候选筛选需要额外语义守卫，当前没有足够来源支持新增完整流程。见source_extractions、pattern_clusters和逐条操作JSONL。
'''
    reports['03_TYPED_DSL_AND_SYNTHESIS.md']=f'''# 03 — 类型化 DSL、搜索与证明

实现IntegerExpression、Scalar、ResidueScalar。Polynomial/RationalExpression/Equation/ConstraintSet/FiniteCandidateSet在本轮暂缓；旧V3作为冻结对照保留，不借增加这些类型数量冒充进展。

人工原语：

| 原语 | 类型 | 数学含义 |
|---|---|---|
| reduce_literals | IntegerExpression→IntegerExpression | 整数叶节点对m归约；绝不对指数取m余数 |
| reduce_powers | IntegerExpression→IntegerExpression | 自底向上将正整数幂替换为其同余值 |
| evaluate | IntegerExpression→Scalar | 有界精确整数加乘幂计算 |
| canonical_residue | Scalar→ResidueScalar | 取[0,m)中的唯一代表 |

没有提供“整个余式题求解器”作为单个原语。但树遍历和幂模计算是明显人工先验，四步流程的合成难度有限。枚举类型合法、无重复幂等归约的程序，至多6个节点，实际5个组合；运行中以(op,state,m)去重。先比较真实训练最终值和非最终中间表达式，再要求≥2来源和≥2结构，最后独立验证。按来源支持数优先、长度次之、字典序最终决胜选择一条。来源与候选失败检查完整保存，不按确认结果选择。

数学证明与样本拟合分开：加/乘的同余保持恒等式、正整数幂归纳步骤的符号余项均为0；结合整数除法唯一代表和AST结构归纳说明允许原语的合法组合保持同余。此为人工指定归纳规则与符号检验，不冒称定理证明器形式化证明。每次真实执行仍由独立二进制模幂和模环遍历检查所有中间状态及最终值；不调用DSL的pow实现核验自身。

有反例测试：2^5 mod5=2，错误地把指数5模5得到0会输出1，验证拒绝；同余但不规范的答案7也拒绝。非法操作/类型、幂塔、除法、变量、模数0/1/负数、负指数及任何指数0、额外任务文本均回退。

资源限制：AST≤96节点/深度12，程序≤6节点，指数≤10^6、模数2..10000，精确中间整数≤8192bit；工作进程3秒墙钟时限、512MiB地址空间上限，最多12个本地worker。只执行白名单DSL，不执行eval、生成Python或不受限符号代码。时间/内存限制有真实子进程测试。

搜索耗时{search['wall_seconds']:.6f}秒（含候选证明）；提取加搜索{mining['wall_seconds']:.6f}秒。193项新旧测试通过，详见all_tests.xml。程序最终恰好等于人工基线，这是对照发现，不能隐藏。
'''
    macro=bank[0] if bank else None
    reports['04_AUTOMATIC_MACRO_BANK.md']='# 04 — 自动宏库\n\n'
    if macro:
        reports['04_AUTOMATIC_MACRO_BANK.md']+=f'''唯一新入研究库宏：`{macro['macro_id']}`。

任务：有显式整数表达式的余数或十进制个位问题。适用表达式为整数、加法、乘法、字面正整数幂；不支持含变量、除法、求和省略号、阶乘、递推、约束推断等任务。

来源4题：`{', '.join(macro['source_task_ids'])}`。原题、完整模型解答、source_hash、逐步位置保存在source_extractions与macro_candidates。使用每题真实的非最终算式作为额外样本约束，不能仅从最终数字回归公式。

顺序：`{' → '.join(macro['program'])}`，4个执行步骤，属于受限多步程序；Guard是完整目标语义、整数表达式类型、正整数指数、合法模数及资源上限。Guard来自人工文法/类型与原语合法性传播，并非自动发现新数论条件。符号义务全部通过；每次执行还要独立验证。独立确认使用次数0，工程使用1，生产admission=False。

候选记录：仅evaluate→canonical_residue虽然拟合最终值，没有所需非最终状态，来源支持0；reduce_literals的3步版本支持537/809；reduce_powers的3步版本支持210/992；两种4步顺序均支持4题，最终按冻结规则选字典序较小者。不是从五种候选中发现全新数学定理。

与人工工具的程序完全相同。5个组合的搜索空间、原语、语义、正确性规则都人工设计；自动所得为组合选择和多来源准入证据。旧V3根和/根积宏保持原文件，未算作本轮新宏。
'''
    reports['05_INDEPENDENT_GENERALIZATION.md']=f'''# 05 — 划分与独立泛化

从原始MATH train共7500题审计历史使用：2463题已经实际使用或被目标筛查；近重复连通分量再剔除241道未用但相近的题，剩4796。训练发现只读取603条干净成功模型轨迹。无MATH test参与建库、选择或验证。

全量两两digit-masked字符LCS相似度≥0.9建立连通分量（RapidFuzz3.14.1，12进程、只保存上三角高分边），避免只做前后缀阻塞漏检。相较旧SequenceMatcher门槛更保守；仍不能保证排除所有语义改写或相同高层数学族。连通分量按固定SHA256分配：engineering1184、selection1229、confirmation2383。所有题ID、问题文件hash、历史排除记录与边均保存。

旧1549开发题和其子集1115保留池已经曝光，不作为fresh。确认题在冻结之前仅用于数据集ID/近重复分组，不进入Goal Parser、宏筛选或调试；冻结后才按问题运行，所有输出完成并封存后评分。评估脚本读取标签文件用于已封存提交的离线评分；标签不传入solver，不做gold反思/重试。

泛化结果：V4宏工程集1题正确、选择集0、确认集0。工程题`math_train_number_theory_686`问13×41的个位，来源外，且是两因子积（来源809为三因子积）；不是靠改来源题数字生成。它提供有限的乘积项数/措辞迁移证据，不能支持幂或混合结构的独立泛化主张。

确认集中C唯一完整结果`math_train_algebra_688`根和21/8，来自冻结V3。不要把它计到V4宏。B另外解决一题旧V3范围，具体见配对CSV。

{mdtable(distribution,['population','count','remainder_word','roots_word','units_or_last_digit'])}

新池是历史筛查后剩余分布，尤其目标关键词已经被系统性抽走；这里不是原始MATH的随机代表性抽样。因此0个V4确认命中同时反映独立资源不足与严格作用域，不能推断所有数学程序学习永远无效。现在这个池完成本轮检查后也必须标记已看过，不可下轮重复宣称fresh。
'''
    reports['06_COVERAGE_AND_BASELINES.md']=f'''# 06 — 同先验人工与自动对照

A Bot-NoBank未运行。B和C共享V4完整目标文法、可用原语、预算、Guard及独立验证器，并继续保留冻结V3路由。B的模运算顺序是人工固定；C真正执行合成bank内的DSL序列，搜索不读取MANUAL_PROGRAM（测试中破坏人工常量仍合成同一结果）。二者最后恰好选择同一序列。

{mdtable(main,['split','method','denominator','parsed','guards','full','correct','fallback','local_seconds'])}

{mdtable([{'split':s,**v} for s,v in pairsums.items()],['split','both','B_only','C_only','neither'])}

完整执行正确只是已提交子集正确，不是全池准确率；所有其他题未调用LLM，结果保持null。确认B2/2383=0.0839%覆盖，C1/2383=0.0420%，C新增0。V4新宏工程B/C各1、选择各0、确认各0；B独有来自旧V3库差异。整个新池B3/4796、C2/4796，其中V4额外工具仅1/4796（描述性0.02085%），不是原始MATH总体估计。

数学误接管0；没有证据给出未触发题的准确率。回退细分见summary JSON：主要semantic_unsupported_whole_question/旧V3无完整文法；确认C有1题no_certified_automatic_macro（DSL/库覆盖缺失），没有实际Guard失败或验证失败。无中间结果注入LLM。

表中总local_seconds仅描述运行开销：导入、缓存、路由顺序会偏移B/C，不能用它宣称算法加速。预热且100次交替配对的唯一V4独立开发命中，B中位{cost['B_median_ns']/1000:.4f}µs，C{cost['C_median_ns']/1000:.4f}µs，C/B={cost['C_over_B']:.4f}；未达≤0.8的成本门槛，样本亦极少。CPU计时不是推理token收益。
'''
    reports['07_PILOT_RESULTS.md']=f'''# 07 — 条件式模型实验

**NOT RUN**。冻结config的sha256 `{freeze['config_sha256']}`；冻结后没有改门槛。

{mdtable([{'condition':k,'passed':v} for k,v in checks.items()],['condition','passed'])}

观察：认证组合宏1条；确认V4 eligible0（门槛12）；确认结构0（门槛3）；C-only0；本地成本优势False；193测试通过、未见错误接管。选择集V4 eligible也为0。付费实验不启动，不强行凑题，不跑MATH-500。

| 方法 | 正确率 | 输入tokens | 输出tokens | 总tokens | API调用 |
|---|---|---|---|---|---|
| A Bot-NoBank | NOT RUN | N/A | N/A | N/A | N/A |
| B Manual Tools | NOT RUN | N/A | N/A | N/A | N/A |
| C Automatic Macros | NOT RUN | N/A | N/A | N/A | N/A |

本轮实际新增调用账本为空，新增调用0、实际tokens0、新增API费用0；这只是未调用的账目，不是三种已运行模型方法的零成本优势。离线完整提交为真实计算，但“实际跳过在线LLM调用数”N/A，因为没有启动配对在线协议。Token节省N/A。

如果曾满足门槛，配置限DeepSeek Flash、temperature0、max_tokens4096、同system/base prompt、API并发≤64、本地≤12、最多120调用/200000tokens，gold反思和gold正确性重试关闭。本轮实验代码没有密钥访问或网络模型调用。发布安全扫描会在本地读取密钥文件用于检查泄漏，不上传密钥。
'''
    reports['08_MECHANISM_AND_COST.md']=f'''# 08 — 机制归因与成本

**RQ1**：在很小的人工DSL内自动组合成功。4来源的真实中间表达式约束选出了四步序列，优于仅拟合最终数字；但只有5个可选组合，算法/类型/守卫基本由人工限定，未学会新的高层数学策略。所有anti-unification来源对根结构不匹配，不能把typed hole当作强结构归纳成果。

**RQ2**：仅工程集一题验证了两因子乘积向既有三因子来源的项数和措辞迁移；选择、确认无V4任务命中，其他结构未独立验证。根和确认成功属于V3。

**RQ3**：未优于人工工具。匹配相同基础原语/语义时，新程序与B完全相同，C新增覆盖0，也无本地成本优势。没有测量人工工时，不主张工程建库成本减少。

**RQ4**：没有MATH全分布摊销证据。历史700训练调用实际795435tokens（其中603成功子集518212，不能重复相加）；本轮复用，新增建库API0。基于已测“C相对B新增接管率=0”，无法通过额外免LLM调用回收任何新增成本。B/C相对A的实际平均节省S未测，p也受历史筛查影响，不能把N≥T_build/(p×S)代入猜测数字当作实测。大规模学习和算子维护的人工/本地费用也未定价。

**RQ5**：停止当前路线的规模化token收益主张，保留负结果与原型。继续盲目增加目标文法和手工算子会增加人工能力，无法检验原问题中的自动结构学习贡献。

{mdtable(costs,['component','status','calls','total_tokens','local_wall_seconds','note'])}

本轮API实际费用为0；历史美元/人民币费用没有价格账单，不补写推算。代码搜索/验证的本地秒数是实际计时，不能直接转换为API tokens。完整source、config、bank与代码hash见run_manifest与freeze记录。
'''
    reports['09_NEXT_ITERATION.md']='''# 09 — 下一阶段科研判断

**选择：停止该路线。** 具体停止：把“从当前MATH轨迹自动合成可执行宏”继续作为规模化推理token节省方案来扩容，不启动下一轮500题或追加手工算子。本轮完成后停止；没有安排自动后续任务。

理由：唯一新程序是四种手工树操作的5选1组合，重现人工基线；跨题完整任务只在工程池有1次，选择和确认都0；C-only0、无额外成本优势；剩余独立数据分布又受历史筛查明显影响。程序正确与工程实现可复现，并不构成有效token收益证据。

保留所有程序、候选、失败、原始轨迹、封存输出、历史结果与测试。研究库状态保持certified_research，不加入生产Skill Bank。若未来用户另行决定换研究问题，应先取得足量全新结构来源和预注册确认集，并将“自动学习语义/组合”与人工工具配置区分。那将是另一个获授权实验，不是本轮自动继续。

不能再把本轮4796道工程/选择/确认题称为未见数据；不能把本轮离线零调用当作实测A/B/C性能；不能用简单改数字或选择已见eligible题补足独立验证。
'''
    for name,content in reports.items():(OUT/name).write_text(content)
    write(OUT/'run_manifest.json',{'stage':'completed_offline_pilot_NOT_RUN','created_at':now(),
        'reference_commit':'ebe50279392e8a6d0ad717ef0cd33922115552ca','publication_repository':'https://github.com/ChenKaichen-SCUT/Flowevo-Bot',
        'publication_commit':'recorded by git commit containing this manifest; embedding own commit hash would be self-referential',
        'freeze_hash':freeze['freeze_hash'],'config_sha256':sha(OUT/'config.json'),'bank_sha256':sha(OUT/'automatic_macro_bank.json'),
        'split_manifest_sha256':sha(OUT/'dataset_split_manifest.json'),'source_trace_sha256':sha(RMMD/'data/clean_success_traces.jsonl'),
        'runtime_code_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src/flowevo_bot/compositional_v4').glob('*.py')},
        'source_data_hashes':{n:sha(ROOT/f'data/manifests/math_grouped/{n}.jsonl') for n in ['train.problems','dev.problems','train.labels','dev.labels']},
        'python':platform.python_version(),'packages':{n:importlib.metadata.version(n) for n in ['sympy','rapidfuzz','pytest','math-verify','latex2sympy2_extended']},
        'new_api_calls':0,'new_input_tokens':0,'new_output_tokens':0,'new_total_tokens':0,'new_API_monetary_cost':0,
        'source_acquisition_tokens_historical':795435,'source_acquisition_tokens_incremental':0,
        'test_count':freeze['test_count'],'local_workers':12,'api_concurrency_limit_if_run':64,
        'full_MATH500_run':False,'gate':gate,'decision':decision,'pairwise':pairsums,'scope_notes':['all math train','all previous artifacts preserved','same parser/primitives B/C','post-freeze analysis only']})
    (OUT/'README.md').write_text('''# Flowevo-Bot V4

从00_EXECUTIVE_SUMMARY.md开始，按01–09阅读。机器可读结果均在本目录；逐split的sealed/scored输出及冻结证据在evidence/，原始来源链接在source_extractions.json。

代码：src/flowevo_bot/compositional_v4。使用现有.venv，额外依赖rapidfuzz==3.14.1。运行记录：audit.py → split.py → discover.py → evaluate.py dev-engineering → evaluate.py dev-selection → diagnostics.py → pytest → freeze.py → evaluate.py heldout-confirmation → report.py → verify.py。

split/freeze拒绝覆盖已经冻结的文件；历史结果为只读。重现实验请使用单独工作副本，不重写本目录已发布的原始证据。正式自检命令：`.venv/bin/python experiments/compositional_macro_v4/code/verify.py`。API实验NOT RUN；无需密钥即可重放全部离线结果。
''')
    print(json.dumps({'gate':gate,'pairwise':pairsums,'decision':decision},ensure_ascii=False))
if __name__=='__main__':main()
