"""Post-freeze analysis. No model calls, parser edits, or candidate revisions."""
import sys,collections,math,statistics,re,time,xml.etree.ElementTree as ET
from common import *
sys.path.insert(0,str(ROOT/'src'))
from artifact_schema import MacroSkill
from flowevo_bot.goal_v3.engine import solve
from flowevo_bot.rmmd.macros import inspect_question
from flowevo_bot.common import digest

def mdtable(rows,keys):
    return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(str(r.get(k,'')) for k in keys)+' |' for r in rows)
def report(name,text):(OUT/name).write_text(text.strip()+'\n')
def wilson(k,n):
    if not n:return None
    z=1.95996398454;p=k/n;center=(p+z*z/(2*n))/(1+z*z/n);half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-half,center+half]

def main():
    cap_cpu();freeze=read(OUT/'evidence/pre_reserved_freeze.json');assert all(sha(ROOT/p)==h for p,h in freeze['files'].items())
    gate=read(OUT/'data/paid_gate.json');status=read(OUT/'evidence/paid_status.json');assert status['status']=='NOT_RUN_GATE_FAILED','This report path explicitly handles an unrun pilot.'
    bank=read(OUT/'data/automatic_macro_bank.json');[MacroSkill.model_validate(r) for r in bank];write(OUT/'data/macro_skill.schema.json',MacroSkill.model_json_schema())
    raw=lines(OUT/'data/engineering_manual_results.jsonl')+lines(OUT/'data/engineering_automatic_results.jsonl')+lines(OUT/'data/reserved_scored_results.jsonl')
    byid={}
    for r in raw:byid.setdefault(r['task_id'],{})[r['method']]=r
    results=[];pairs=[]
    for tid,pair in sorted(byid.items()):
        b=pair['B_Manual'];base={'run_id':'goal_aware_macro_v3','task_id':tid,'subject':b['subject'],'difficulty':b['difficulty'],'question_source':b['source_split'],'question':b['question'],'method':'A_NoBank','phase':'offline_only_paid_gate_failed','status':'NOT_RUN','selected_macro':None,'trigger':False,'goal':None,'guard_checks':[],'execution_attempted':False,'execution_result':None,'verification_certificate':None,'full_task_verified':False,'partial_result':False,'fallback_reason':'paid_pilot_not_authorized_by_preregistered_gate','input_tokens':None,'output_tokens':None,'total_tokens':None,'api_call_count':0,'reasoning_seconds':None,'local_seconds':0.,'retrieval_seconds':0.,'execution_seconds':0.,'verification_seconds':0.,'answer':None,'offline_correct':None,'parse_status':'not_run','truncated':False,'gold_exposed':False,'code_version':freeze['code_hash'],'config_hash':freeze['configuration_hash'],'prompt_hash':None,'real_llm_observation':False}
        results.append(base)
        for method in ['B_Manual','C_Automatic']:
            r=pair[method];x=r['solver_result'];full=x['full_task_verified']
            results.append({**base,'method':method,'status':'DIRECT_SUBMITTED' if full else 'LLM_FALLBACK_REQUIRED_NOT_RUN','selected_macro':x['selected_macro'],'trigger':x['trigger'],'goal':x['goal'],'guard_checks':x['guard_checks'],'execution_attempted':x['execution_attempted'],'execution_result':x['execution_result'],'verification_certificate':x['verification_certificate'],'full_task_verified':full,'partial_result':x['partial_result'],'fallback_reason':x['fallback_reason'],'input_tokens':0,'output_tokens':0,'total_tokens':0,'local_seconds':x['local_seconds'],'retrieval_seconds':x['retrieval_seconds'],'execution_seconds':x['execution_seconds'],'verification_seconds':x['verification_seconds'],'answer':x['answer'],'offline_correct':r['offline_correct'],'parse_status':r['parse_status'],'source_record_sha256':digest(r),'record_scope':'deterministic offline route only; unexecuted fallbacks are not wrong answers'})
            pairs.append({'task_id':tid,'split':b['source_split'],'pair':'A_vs_'+method,'comparison_observed':False,'A_correct':None,'other_correct':r['offline_correct'],'both_correct':None,'both_wrong':None,'benefit':None,'harm':None,'saved_input_tokens':None,'saved_output_tokens':None,'saved_total_tokens':None,'reason':'NoBank was not run; no real token/correctness pair exists','other_direct':full})
        c=pair['C_Automatic'];bf=b['solver_result']['full_task_verified'];cf=c['solver_result']['full_task_verified']
        pairs.append({'task_id':tid,'split':b['source_split'],'pair':'B_vs_C','comparison_observed':bf and cf,'A_correct':b['offline_correct'],'other_correct':c['offline_correct'],'both_correct':b['offline_correct'] is True and c['offline_correct'] is True if bf and cf else None,'both_wrong':b['offline_correct'] is False and c['offline_correct'] is False if bf and cf else None,'benefit':b['offline_correct'] is False and c['offline_correct'] is True if bf and cf else None,'harm':b['offline_correct'] is True and c['offline_correct'] is False if bf and cf else None,'saved_input_tokens':0 if bf and cf else None,'saved_output_tokens':0 if bf and cf else None,'saved_total_tokens':0 if bf and cf else None,'reason':'both exact direct results observed' if bf and cf else 'one or both LLM fallback outcomes unobserved','B_direct':bf,'other_direct':cf})
    write_lines(OUT/'data/task_results.jsonl',results);table(OUT/'data/task_pairwise.csv',pairs)
    coverage=[];usage=[];rejections=[]
    for split in ['ALL','engineering','reserved']:
        for method in ['B_Manual','C_Automatic']:
            group=[r for r in results if r['method']==method and (split=='ALL' or r['question_source']==split)];n=len(group)
            for family in ['ALL','root_symmetric','polynomial_remainder']:
                g=group if family=='ALL' else [r for r in group if r['goal'].get('family')==family];full=[r for r in g if r['full_task_verified']];partial=sum(r['partial_result'] for r in g)
                coverage.append({'split':split,'method':method,'family':family,'denominator':n,'lexical_or_parsed_family_candidates':len(g),'goal_parsed':sum(r['goal'].get('state')=='parsed' for r in g),'guard_pass':sum(all(c['passed'] for c in r['guard_checks']) and bool(r['guard_checks']) for r in g),'full':len(full),'partial_available_not_executed':partial,'other_fallback':len(g)-len(full)-partial,'LLM_needed_total':len(g)-len(full),'coverage_percent':round(100*len(full)/n,6),'direct_correct':sum(r['offline_correct'] is True for r in full),'direct_false':sum(r['offline_correct'] is False for r in full),'direct_unknown':sum(r['offline_correct'] is None for r in full),'direct_precision_wilson95':wilson(sum(r['offline_correct'] is True for r in full),len(full)),'end_to_end_accuracy':None,'new_api_calls':0,'new_LLM_tokens':0})
            for macro in sorted({r['selected_macro'] for r in group if r['selected_macro']}|({m['macro_id'] for m in bank} if method=='C_Automatic' else set())):
                g=[r for r in group if r['selected_macro']==macro];usage.append({'split':split,'method':method,'macro_id':macro,'selected':len(g),'execution_attempted':sum(r['execution_attempted'] for r in g),'direct_submissions':sum(r['full_task_verified'] for r in g),'correct':sum(r['offline_correct'] is True for r in g),'structurally_avoidable_calls_if_deployed':sum(r['full_task_verified'] for r in g),'actually_saved_tokens_vs_new_NoBank':None,'execution_seconds':sum(r['execution_seconds'] for r in g),'verification_seconds':sum(r['verification_seconds'] for r in g),'retrieval_seconds':sum(r['retrieval_seconds'] for r in g),'local_seconds':sum(r['local_seconds'] for r in g)})
            reasons=collections.Counter(r['fallback_reason'] for r in group if not r['full_task_verified'])
            for reason,count in reasons.items():rejections.append({'split':split,'method':method,'reason':reason,'count':count})
    write(OUT/'data/coverage_summary.json',coverage);table(OUT/'data/coverage_summary.csv',coverage);table(OUT/'data/macro_usage.csv',usage);table(OUT/'data/rejection_reasons.csv',rejections)
    root=ROOT/'experiments/math500_goldfree_20261009';costs=[{'item':'new_macro_learning','api_calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'seconds':read(OUT/'evidence/discovery_runtime.json')['wall_seconds'],'scope':'formal local synthesis only; engineering iterations not priced'},
       {'item':'new_paid_pilot','api_calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'seconds':None,'scope':'NOT RUN due to gate failure'},
       {'item':'old_source_acquisition_full','api_calls':700,'input_tokens':91262,'output_tokens':704173,'total_tokens':795435,'seconds':None,'scope':'historical cost, not charged again'},
       {'item':'incremental_source_reuse','api_calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'seconds':None,'scope':'previous603clean traces reused'},
       {'item':'human_and_assistant_engineering','api_calls':None,'input_tokens':None,'output_tokens':None,'total_tokens':None,'seconds':None,'scope':'outside observable DeepSeek experiment ledger, not assumed free'}]
    for label in ['engineering_manual','engineering_automatic','reserved_manual_automatic']:
        costs.append({'item':'local_'+label,'api_calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'seconds':read(OUT/'evidence'/(label+'_runtime.json'))['seconds'],'scope':'final phase wall time with<=12workers, not CPU billing'})
    table(OUT/'data/cost_breakdown.csv',costs)
    scenarios=[]
    for method,complete in [('B_Manual',20),('C_Automatic',2)]:
        for baseline_tokens in [500,1000,2000]:
            assumed=complete/1549*baseline_tokens;scenarios.append({'method':method,'coverage_count':complete,'denominator':1549,'assumed_eligible_NoBank_tokens':baseline_tokens,'assumed_savings_per_all_tasks':assumed,'source_acquisition_break_even_tasks':math.ceil(795435/assumed),'status':'hypothetical deployment vs NoBank; no new baseline observations; mixed development distribution, not MATH-wide estimate'})
    table(OUT/'data/amortization_scenarios.csv',scenarios)
    examples=[]
    for r in results:
        if r['method']=='B_Manual' and (r['full_task_verified'] or r['partial_result']):examples.append({k:r[k] for k in ['task_id','question_source','question','goal','guard_checks','answer','full_task_verified','partial_result','fallback_reason','offline_correct']})
    write(OUT/'data/goal_examples.json',examples)
    admission=[]
    for macro in bank:
        eng=next(r for r in usage if r['method']=='C_Automatic' and r['macro_id']==macro['macro_id'] and r['split']=='engineering');fresh=next(r for r in usage if r['method']=='C_Automatic' and r['macro_id']==macro['macro_id'] and r['split']=='reserved')
        admission.append({'macro_id':macro['macro_id'],'mathematical_certificate':True,'source_replay_tests':True,'random_and_boundary_tests':True,'engineering_dev_full':eng['direct_submissions'],'fresh_dev_full':fresh['direct_submissions'],'production_admitted':False,'status':'mathematically certified research candidate; insufficient independent deployment evidence'})
    write(OUT/'data/macro_admission.json',admission)
    subset=[r for r in coverage if r['family']=='ALL'];byfamily=[r for r in coverage if r['split']=='ALL' and r['family']!='ALL'];tests=(OUT/'tests/offline.log').read_text().strip();ops=lines(OUT/'data/reasoning_operations.jsonl');attempts=lines(OUT/'data/macro_candidates.jsonl');fail=read(OUT/'data/discovery_failures.json');search=read(OUT/'data/synthesis_search.json')
    report('01_IMPLEMENTATION_REPORT.md',f'''# Goal-Aware Executable Skills V3 实现

本地与远端起点均为245ce20d9cc7a70ac8f5119bf29d374039d24a53，仅指引.txt变化。独立目录goal_aware_macro_v3；历史3569个文件SHA被保护，上游、V1、V2和RMMD均不改写。

新增src/flowevo_bot/goal_v3：goals.py定义结构化Goal与闭合题意文法；engine.py实现Goal→Preconditions→Execute→Verify→Commit；learning.py执行受限程序合成；runtime.py实现三组对照及完全相同的无库回退。部分中间量不执行、不注入prompt。所有当前题gold仅进入提交后的独立评分，未进入Goal Parser、Solver、Bank或恢复逻辑。

支持目标：全部根和、根积、两两乘积和、2–6次幂和、合法倒数和、有界对称有理表达式、多项式余式。支持数值多项式/非零右端方程归一化、显式根绑定、完整实根数量与开放区间约束、分数及指定小数格式。目标必须由整个文法消费，未知附加句不能丢弃。仅出现roots/remainder不允许完整执行。

根多项式QQ、次数2–6、首项非零；无显式重数说明的直接请求要求squarefree；显式counting multiplicity或与次数相同的完整命名根绑定允许重根。正根/实根/有理根的子集、变量参数、不明确根数量、未解析条件均拒绝。倒数检查常数项，保留原始分母并用根置换轨道的非零值验证定义域；不能只在约分后检查分母。幂次、表达式大小和分母类型均有上界。

人工计算采用Vieta/Newton、对称多项式化及精确余式。核验分别采用伴随矩阵的迹/行列式/逆矩阵、独立Groebner残差、系数递推与P=QD+R恒等式及次数界。数学证书与语义文法证书分开记录；格式化失败也不能Commit。

Goal与ReasoningOperation有类型定义；自动bank用限定JSON AST执行并由MacroSkill的Pydantic模式复核（data/macro_skill.schema.json）。该类型化归档校验在分析阶段加入，不改变冻结求解器。禁止exec/eval任意模型程序。DSL只有固定系数/奇偶特征、负号和四则运算，最多5节点。

付费与本地并发上限64/12，预算120调用/200000 tokens，DeepSeek Flash、温度0、max_tokens4096。实际付费门槛失败，没有读取密钥执行模型实验。新增调用0。原始独立池运行代码及22个文件hash固定于pre_reserved_freeze.json和runtime_before_reserved.zip，之后没有改动这些文件。
''')
    report('02_GOAL_PARSER_AND_COVERAGE.md',f'''# 目标解析与完整任务覆盖

原开发集1549题分为434道已使用/已筛查工程题、1115道保留题。此前RMMD在278道训练侧问题上运行过根/余式筛查，该集合与原dev的交集连同旧350开发题、V2题及上一轮题一起隔离为工程数据。没有把旧题重新称为独立测试。保留池先固定代码和bank，筛查后不再修订。

{mdtable(subset,['split','method','denominator','goal_parsed','guard_pass','full','partial_available_not_executed','other_fallback','LLM_needed_total','coverage_percent','direct_correct'])}

{mdtable(byfamily,['method','family','denominator','lexical_or_parsed_family_candidates','goal_parsed','full','coverage_percent'])}

原开发分布描述性完整覆盖：人工20/1549=1.2912%，自动2/1549=0.1291%。人工根类8题、余式12题；自动只完成2道根和。仅局部对象可用12题，均未执行/未注入；其余回退人工1517题、自动1535题。所有需要LLM的总数分别1529/1547。覆盖不是端到端准确率，未运行的回退不能计作错误。

独立池唯一命中algebra_285：求(3x+5)(2x-9)=0的解之和，解析为完整平方自由二次方程，B/C均得到17/6并通过独立离线评分。工程题intermediate_algebra_1150：识别三个根均在(0,1)，目标∑1/(1-r)，验证所有分母非零，直接得到12；上一轮只能注入中间量，本轮人工工具可完成整个目标，但自动bank尚不能处理。

工程题999的移位立方和、1137的对称表达式和597的重复因子余式均完整执行；数据中保存题面、Guard及证书。真实完整提交无观察到错误命中：B20/20、C2/2。这里包含工程题，不能作为独立泛化成功率；独立部分各1/1，Wilson95%区间约[20.65%,100%]，不能声称非劣。

拒绝/局部案例：algebra_1381求较大解（不能用全部根和替代）；intermediate_algebra_81仅取四次多项式实根；310包含两个多项式及未知系数；1141涉及f(f(x))；正实根、参数根、未知格式和额外目标均回退。目标文法不支持的自然语言条件未被静默删除。初次工程检查发现1150将问号放在LaTeX内部，已在保留池冻结之前修复；首轮18/434记录和源码保存在evidence/development_attempt_01。

本轮覆盖率与上一轮0.42%的去重后1186题分母不同，不能将两者直接比较并宣称覆盖提升。这里按固定完整原dev分布报告，题目间仍可能相似；拟付费样本另有数字归一化及相似度≥0.9去重，不能靠改数值凑规模。
''')
    report('03_AUTOMATIC_MACRO_DISCOVERY.md',f'''# 从成功轨迹自动构建受限宏

输入仍是603条干净首次成功训练轨迹，SHA保持不变。自动提取{len(ops)}条可绑定目标且有数学步骤的ReasoningOperation，其余保留逐项失败原因。输入对象、目标类型、模型最终值、来源公式片段与位置、前置条件和验证规则完整保存。最终值来自已审计的模型成功轨迹，不是新测试gold。

自动化边界：数学片段、数值对象与模型最终值自动提取；目标类别由人工文法识别；按目标聚合后，程序枚举器在固定系数特征与四则算术DSL内寻找同时吻合多个来源的AST，再用形式根变量证明泛化。不是从自然语言思维链自动学习所有语义步骤；不能把来源公式片段的复制称为整段COT语义解析成功。

实际构建两条程序：

- 根和：`-(top1/lead)`，来源algebra_1366与1507，分别是展开式和非零右端平方方程。二者都是二次源题，跨次数推广来自符号证明，不来自广泛经验样本。
- 根积：`constant/(lead*parity)`，parity=(-1)^degree，来源intermediate_algebra_955（三次）与1151（两个三次因子的六次乘积）。系数奇偶特征为人工预置先验；表达式组合及路由条目由搜索得到。

枚举统计：{json.dumps(search,ensure_ascii=False)}。共2857个程序枚举，14个来源精确拟合候选，其中12个被通用验证排除，2个认证。典型反例：`-top1`在两道首一来源上拟合，但非首一多项式失败；保留反例赋值。除法节点分母也逐节点证明在声明域非零，不能先约分掩盖不合法程序。

每个合格程序在次数2–6，替入L∏(x-r_i)的系数后，对“全部根之和/积”的定义做符号残差=0证明，非随机正确率替代理论验证。源码没有将已知Vieta AST直接写入bank；验证器预置目标定义及数学内核，不能据此宣称无人工先验的新定理发现。

未合格目标：{json.dumps(fail,ensure_ascii=False)}。两两积和、倒数和、一般对称有理式各仅1条来源；余式有2条来源，但当前标量DSL没有多项式程序表示。余式只在B人工基线运行，没有把预写rem算子冒充自动宏。

两条均为数学认证研究候选，未进入production。根和有1道工程题及1道独立题重放；根积没有本轮原dev完整命中，独立开发验证不足。C相对B新增完整覆盖=0；这说明有限程序合成可行，不代表自动Skill Learning已获得性能或摊销收益。
''')
    report('04_OFFLINE_VERIFICATION.md',f'''# 离线检验与隔离

{tests}

132项回归：原90项＋新增42项。参数化负例覆盖部分根、重数歧义、原始分母为零、未知条件/额外目标、不同变量与参数、根绑定别名、数值范围、格式等。性质循环另含40组已知根多重集×4目标、30组余式×4次精确代入、两条学习程序各60组根多重集及有理首项系数。人工例子为测试fixture，不混入真实开发覆盖率。

核对语义证书和计算证书均通过后才能Commit；故意替换错误bank程序时独立验证阻止提交；空自动bank在余式题上回退，不调用人工rem偷补C。三组回退逐字等于Bot-NoBank base_prompt，部分结果不注入。DSL拒绝未知算子/任意代码，候选认证检查分母及所有声明次数。

阶段顺序：工程目标实现及测试→工程覆盖→正式训练轨迹程序合成→来源重放/性质测试/工程验证→代码与bank冻结→独立池目标筛查→预注册门槛→门槛失败后才评分保留池直接输出。早期有一次仅基于训练源的DSL smoke，日志单独保留，正式运行在工程覆盖后重做；未读取保留池结果调算法。

工程和保留池的完整输出均在读对应标签前seal；独立筛查阶段不读标签，gate不读取正确率，gate失败关闭付费路径后才离线评分。保留池2份B/C提交均正确。所有未执行LLM回退的offline_correct=null，不能当错题或免费正确题。

完整数学保证限于QQ多项式和明确解析的闭合题意文法。模式单元测试及有限真题成功不是自然语言任意题的形式证明。后处理MacroSkill schema是归档类型检查，不属于保留池期间的运行逻辑变更。
''')
    report('05_PILOT_RESULTS.md',f'''# 条件付费试验：未达到启动条件

**NOT RUN。新增DeepSeek调用0、输入tokens0、输出tokens0、总tokens0。没有启动MATH500。**

预注册门槛：至少1条认证自动宏、12道独立适用开发题、其中至少3道自动宏题、至少3个结构类别；最多24道适用题加6道不适用对照，120调用/200000 tokens硬预算。门槛是最小可行比较条件，不是统计功效保证。

独立池1115题中，B/C都仅1题完整可解，去重后仍1题、1类；因此门槛失败。未放宽数学guard、未借用工程题冒充新题、未通过数字替换制造样本。A未运行，故不存在本轮真实三组模型正确率或token节省比较。

| 方法 | 原dev离线完整提交 | 直接提交正确率 | 其中独立部分 | 新真实API | 新输入/输出/总tokens | 端到端准确率 |
| --- | --- | --- | --- | --- | --- | --- |
| A Bot-NoBank | 未运行 | N/A | 未运行 | 0 | 0 / 0 / 0（未运行） | N/A |
| B 人工工具 | 20 | 20/20 | 1/1 | 0 | 0 / 0 / 0（仅本地执行） | N/A |
| C 自动宏库 | 2 | 2/2 | 1/1 | 0 | 0 / 0 / 0（仅本地执行） | N/A |

表中的20/20与2/2只衡量实际直接提交，不包含需要模型的剩余题，不是1549题准确率；二者大部分不是独立测试。A输入/输出均未观测，机器逐题结果记null；总体支出账记实际0，明确区分。

task_pairwise.csv为每题保留A-B/A-C/B-C；A相关benefit/harm/both_correct/both_wrong及token差全为null。B/C只有2道共同完整求解能够比较，均正确且同值。B另18道完整求解，C需回退而未执行，不能把这些算作C数学错误。
''')
    report('06_MECHANISM_AND_COST.md',f'''# 机制与完整成本

人工完整任务覆盖20/1549，自动2/1549；C覆盖是B的严格子集，没有新增正确答案、覆盖率或避免调用优势。B的8道根目标和12道余式体现目标感知执行；C只学得根和/积的标量系数程序，本dev中仅根和2次调用其程序。学习根积在独立dev未实际命中。

新NoBank未调用，因此实际节省输入/输出tokens、相对A正确率收益、正确率损伤和模型推理时延都不可估计。离线可确定的是结构上有20/2次完整求解可在部署时跳过LLM，不能把这写成已真实节省20/2次付费请求。部分结果12题均不注入，未花模型token验证辅助效果，也未沿用上一轮根中间量增加token的做法。

直接求解的检索、执行和验证秒数逐条保留并在macro_usage.csv汇总；这是本机测量，未折算为统一费用。C的execution_seconds计时包含retrieval_seconds，二者不可重复相加，总本地耗时以local_seconds为准。正式程序合成耗时{read(OUT/'evidence/discovery_runtime.json')['wall_seconds']:.4f}秒、0模型调用；零新增采集费用不等于零人工研发成本。完整原700题采集795435 tokens（91262输入、704173输出），603条成功只是筛选子集，失败训练也属于原成本。

本轮新增API支出0，原语料复用的增量API支出0；从零采集同样语料的成本仍795435。人工/助手研发会话成本不在DeepSeek实验账本中可观测，记录unknown，未当作免费。没有借用旧34,896 tokens试验冒充本轮费用。

没有新的A观测，不能给出实测盈亏平衡。amortization_scenarios.csv仅做假设每道适用题NoBank需500/1000/2000 tokens的情景：C按2/1549的描述性覆盖，在每适用题1000 tokens的假设下约需616065道总体任务摊销795435采集tokens。工程/保留池混合分布并非MATH总体，实际覆盖和模型成本可能不同。与B比较，C没有新增可避免调用，故没有证据支持额外token摊销收益。

不确定性分两层：有限开发集的路由比例是确切计数，但其总体推广不确定；语义理解证书仅覆盖人工闭合语法。直接提交正确率的Wilson区间记录在coverage_summary，独立1/1不足非劣结论。数学恒等式证明是受条件约束的代数保证，不能代替语言覆盖验证。
''')
    report('07_NEXT_ITERATION.md','''# 下一轮研究决策

**选择：改进自动宏发现，暂不扩大付费实验。**

本轮取得的是受限程序合成的可审计可行性结果：从成功轨迹自动选出两条算术AST并证明其数学范围；目标语法、系数表示、DSL原语与验证规则仍人工预置。没有证明自动宏相对人工工具产生性能、覆盖或摊销上的额外收益，也没有从完整自然语言推理轨迹自动学习中层算法。

对整个MATH分布，第一限制是目标/宏类别狭窄，只覆盖少数根聚合及多项式余式；该范围内，语言条件和完整任务证书进一步限制覆盖。对C相对B的差距，主要是自动DSL仅支持标量表达式，以及多来源支持不足：人工已能解的20题，自动仅2题。已解析任务的精确数值验证没有出现失败，所以当前不应优先堆更多人工SymPy算子。

下一轮应先重新设计训练/开发隔离：本轮1115保留题已被筛查，不再宣称为全新独立池；在查看任何新来源前预留足够的独立题及结构族。研究重点是从多个来源提取可执行的组合步骤（例如多项式变换/递推），明确哪些表示与不变量为人工先验，并用未用于合成的结构变化检验是否超过同算子人工基线。稀少来源不降低准入要求，手写余式程序不能重新贴自动学习标签。

若更丰富的受限程序表示仍只能重现人工基线的少量标量公式，或无法获得足够独立验证任务，应停止自动宏路线的规模化token收益主张，仅保留经过验证的人工工具作为工程功能。

本轮已结束：不补跑、不根据独立结果改解析器、不启动MATH500。代码、数据、失败证据、报告和压缩包发布后停止，等待下一轮研究决策。
''')
    manifest={'run_id':'goal_aware_macro_v3','reference_commit':'245ce20d9cc7a70ac8f5119bf29d374039d24a53','phase':'complete_offline_research_paid_gate_failed','frozen_code_hash':freeze['code_hash'],'configuration_hash':freeze['configuration_hash'],'new_api_calls':0,'new_input_tokens':0,'new_output_tokens':0,'new_total_tokens':0,'math500_run':False,'source_clean_traces':603,'original_dev':1549,'engineering_dev':434,'reserved_dev':1115,'manual_direct_total':20,'automatic_direct_total':2,'fresh_direct_each':1,'learned_scalar_programs':2,'production_macros':0,'history_protected_files':3569,'automatic_advantage_over_manual_observed':False,'test_count':132,'declared_next_action':'improve_automatic_discovery_and_independent_data_design; no further execution','post_freeze_analysis_only_files':['code/analyze.py','code/artifact_schema.py'],'runtime_snapshot':'snapshots/runtime_before_reserved.zip'}
    write(OUT/'run_manifest.json',manifest);write(OUT/'data/decision.json',{'choice':'改进自动宏发现，暂不扩大付费实验','paid_pilot':'NOT_RUN','automatic_learning_claim':'two bounded scalar arithmetic programs synthesized; no automatic language-goal learning, no novel theorem discovery, no demonstrated advantage over manual tools','stop_now':True})
    print(json.dumps({'coverage':[r for r in coverage if r['family']=='ALL'],'manifest':manifest},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
