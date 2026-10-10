from common import *
from build_regression_fixtures import COVERAGE,LABELS,FIRST
import csv,collections

def table(headers,rows):
 return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in row)+' |' for row in rows])+'\n'
def write(name,text):(OUT/name).write_text(text.strip()+'\n')

def main():
 audit=read(OUT/'evidence/audit_summary.json');tests=read(OUT/'regression_test_results.json');freeze=read(OUT/'evidence/evaluator_freeze.json');protection=read(OUT/'evidence/protection_audit.json');timing=read(OUT/'evidence/evaluator_v3_results_timing.json');rs=jl(OUT/'evaluator_v3_results.jsonl');by={(r['branch'],r['task_id']):r for r in rs};proof=read(OUT/'evidence/independent_proof_checks.json')
 score=table(['输出','Legacy','Fixed','V3 自动确认正确','V3 Unknown','V3 未完成','V3 Incorrect'],[['固定4096','456/500 (91.2%)','449/500 (89.8%)','466/500 (93.2%)',1,33,0],['自适应最终','485/500 (97.0%)','476/500 (95.2%)','495/500 (99.0%)',1,3,1]])
 cases=[]
 for key in COVERAGE+LABELS:
  tid='math_test_'+key;a=by['adaptive',tid];b=by['base',tid]
  cases.append([tid,'参考漏解' if key in LABELS else '类型/格式覆盖',b['status'],a['status'],proof[tid]['proof']])
 case_table=table(['task_id','历史问题','首轮 V3','自适应 V3','题目数学证明'],cases)
 write('00_EXECUTIVE_SUMMARY.md',f'''# MathEvaluator-V3 离线研究结论

基于提交 `{REF}` 的同一批本地MATH测试集分层抽取的500道题（非官方MATH-500名单）、两套封存输出（共1000份记录）完成回顾性工程改进。本轮新增 LLM 调用 **0**、新增 LLM token **0**。不重新求解，不改变 Solver/Skill/Prompt/预算控制器。旧四项成绩按记录完全复现。

{score}

V3 修复了已确认的17道覆盖问题和3道参考末盒漏解问题；在自适应分支，相比 Fixed 新确认20道正确，同时将两旧评分器均判对的 `precalculus_187` 保留为 Unknown，净增19。该题答案为2^2005，因预设指数上限1000被拒绝解析；独立问题证明确认其正确，但没有把审计结果写回正式分数。首轮对应净增17。

首批9道历史误判、第二批22份旧新分歧均纳入回归。全部项目测试 **{tests['total_tests']} 通过**；V3 和历史案例测试153项，另见本轮证据完整性测试。原生MATH loader的6道真实任务已通过新离线CLI接入，Legacy/Fixed/V3配置可选，默认仍为Legacy。

数学审计覆盖123份记录、75个不同题ID：87份有问题级数学证明，36份核验为截断未交付；其中固定种子20261010按7学科×3难度段抽样21个一致判对题，复核两分支。已核验V3假阳性0、严格假阴性0，正确但弃权2份（同1道题的两份输出）。剩余877份记录未作独立问题证明，不能把99.0%称为整套数学真实性认证。

结论：在已审查类型和案例上，V3比Legacy/Fixed更可靠，且通过严格反例拒绝测试。仍不建议立即替换默认评分器；先在独立题集做盲审，验证自然语言答案类型推断、域约束和复杂表达式资源边界。497份完整自适应回答中495份自动确认、1份错误、1份弃权；审计敏感性为496/500，**不是正式V3分数，也不是新的独立泛化成绩**。

代码冻结树：`{freeze['source_tree_sha256']}`。详细证据在`evaluator_v3_results.jsonl`、`adjudicated_cases.jsonl`、`run_manifest.json`。归档：仓库根目录`math_evaluator_v3_offline.zip`。
''')
 write('01_EVALUATOR_ARCHITECTURE.md',f'''# 实现与依赖审查

代码位于`FlowEvo/src/math_evaluation/`。六个职责单独实现：`spec.py`从公开题目推断AnswerSpec；`reference.py`从完整canonical solution构建参考；`extraction.py`只提取可见最终提交；`normalization.py`构造带类型对象；`equivalence.py`给出确定性等价证据；`engine.py`统一状态、超时、批处理和错误追踪。`certificates.py`提供两个可泛化的公开题目证明模板（函数奇偶对称点、矩形面积变化方向），不含任何task ID。

结构字段包括目标变量、实数/整数/复数域、是否要求全部解、无序性、单位、是否允许换单位、小数位数、百分数语义、选项和不确定性。自然语言识别仍是保守的规则层，不能把它宣传成通用题意理解。识别不可靠时输出Unknown。

解析复用Math-Verify依赖的ANTLR语法转换器，最终判定采用SymPy精确运算和自有类型/域约束。独立调用Math-Verify只对已解析的纯数值对象产生**非决定性诊断**；没有把它另列为独立基线，也不对原始答案调用其默认Expr解析或字符串fallback。[Math-Verify官方说明](https://github.com/huggingface/Math-Verify)、[LaTeX转换器](https://github.com/huggingface/latex2sympy2_extended)。

依赖固定：math-verify0.8.0 (Apache-2.0)、latex2sympy2_extended1.10.2 (MIT)、SymPy1.14.0 (BSD)、ANTLR runtime4.13.2 (BSD-3-Clause)、mpmath1.3.0 (BSD)。使用现有环境实际版本；包元数据、许可证全文/上游来源归档在`evidence/dependency_audit.json`及license文件。ANTLR安装元数据未带许可证，额外保存[4.13.2上游许可证](https://github.com/antlr/antlr4/blob/4.13.2/LICENSE.txt)。

未直接采用Math-Verify默认的单位删除、近似容差和字符串回退。SymPy文档提示`parse_expr`使用eval，因此V3的原始字符串不走该接口；ANTLR转换器的`variable_values`保持None，并检查整条token流消费完毕。[SymPy解析文档](https://docs.sympy.org/latest/modules/parsing.html)。私有ANTLR转换器接口的风险通过精确版本检查和回归测试控制。

数值使用精确有理数；符号比较通过恒等变换，不以有限随机代入相同作为证明。捕获分母非零、偶次根非负、对数正值等约束，再作符号替换。无法证明域等价时弃权。

资源限制：每条4秒、答案4096字符、原文100000字符、表达式600节点、嵌套40层、指数绝对值1000；独立批处理进程地址空间上限1536MiB；最多12进程。批处理worker禁止网络。直接单条evaluate采用字符/复杂度/信号超时保护，进程内存限额仅由batch worker施加；不应将单条接口当作通用不可信代码沙箱。

冻结版本3.0.0，config hash `{freeze['config_hash']}`。正式结果发生在三次开发试跑和历史回归之后；开发结果保留在evidence，明确属于同数据回顾性修复。
''')
 multi=table(['task_id','冻结旧gold','V3完整参考'],[[tid, next(o['frozen_gold_answer'] for o in jl(OUT/'evidence/input_records.jsonl') if o['task_id']==tid),by['adaptive',tid]['reference_extracted']] for tid in ['math_test_'+k for k in LABELS]])
 write('02_REFERENCE_EXTRACTION.md',f'''# 完整参考答案

V3使用完整原始解答，而非最后一个盒子或原生loader浅层正则产出的metadata.gold_answer。先记录所有平衡盒子候选和上下文，再结合公开题目是否要求全部解、目标变量、候选相邻关系选择。明确标为中间计算的盒子不参加最终答案集合；跨段且归属不明时reference_ambiguous。单值题多个候选需要证明等价；多解题只有终结解列表/目标变量赋值支持时才合并。

{multi}

409需两根-3/2,-3/4；516需b=±10879；563需x=3,2/5。两分支均正确恢复，历史gold文件保持不变。`reference_candidates`、`reference_builder`、`reference_complete`和`reference_normalized`保留全过程。

首批796中，奇函数图像经过(-3,5)，另一必过点(3,-5)由公开条件严格推出；参考另列(0,0)附带定义域假设。通用奇偶性证明模块选择可证明的对称点，记录附加假设问题，未根据模型值挑选gold。

本轮完整性队列含5个第二批题ID：上述3个历史漏解、`algebra_1161`逆函数非单射歧义、`precalculus_415`标准推导三角恒等式排印错误。1161的自动提交状态仍是prediction_incomplete，题意歧义单独记录；415的最终2/3经独立推导正确，自动评分不因参考中间笔误改成错。该队列是审计发现，不伪称V3已自动证明每条参考解答。

参考格式完整不等同于参考数学真值完整。V3并未构建通用自然语言证明核验器；无参考、候选冲突或解析失败均不能自动给模型正确。
''')
 write('03_ANSWER_TYPES_AND_EQUIVALENCE.md','''# 数学类型与判定规则

| 类型 | 规范化及验证 | 必须拒绝/弃权的近似情况 |
| --- | --- | --- |
| 数值、分数、根式 | ANTLR→精确SymPy对象；小数转有理数 | 未声明容差时不以近似相等通过 |
| 表达式/多项式 | 有理恒等式、符号化简，并比较定义域 | x/x与1在全实数域不无条件相同；sqrt(x²)不等于x |
| 有限集合/全部解 | 展开单个±，扁平有限集合、逐元素精确匹配 | 缺根、只提交±一支、额外根 |
| 区间/不等式 | 相同目标变量及域下转解集 | [-4,0)和[-4,0]不同 |
| 方程 | 非零常数倍残差，或可解的单变量零点集 | 无法证明多变量零点集相同时Unknown |
| 元组/向量/矩阵 | 顺序、维度、逐元素比较 | (1,2)不等于(2,1)，行列维度不混同 |
| 单位 | 完整后缀、量纲、精确转换系数 | 45mph不等于45km/h；题目限定单位时不擅自换单位 |
| 百分数 | 问百分数时裸20代表20%；问普通数值时20%为1/5 | 不无条件把20、20%、0.2混同 |
| 选项/文本 | 公开词汇集合，精确类别匹配 | 不将odd、CD当成自由代数变量 |
| 进位数 | 题目指定进制并验证数字合法性 | 错下标、该进制非法数字 |

固定的单位注册表覆盖长度、时间、速度、面积、体积、质量、角度、美元/美分等。换单位必须由AnswerSpec显式允许；自动推断尊重题目指定输出单位，不泛化到任意量纲系统。数量方向（more/less）需公开题目证明，不能删除。

小数舍入只在题目明确位数时使用；当前精确有理数路径采用half-away-from-zero，单位值转SI后存在精度表达限制，未宣称覆盖所有计量舍入规范。此限制会保守拒绝某些答案，未来应单独验证原单位中的精度。

矩阵和分式使用相同域检查，但不是通用符号函数/矩阵域证明系统。复杂多变量约束、分段函数、带条件集合、隐式特殊函数、关联多个±、复杂逻辑谓词仍可能Unknown。表达式字符白名单和宏检查属于安全/格式边界；数学相等并非继续堆字符串正则得到。
''')
 groups=table(['测试组','通过数','结果'],[[r['group'],r['counts']['tests'],'PASS' if r['exit_code']==0 else '0个可收集测试（常量文件）'] for r in tests['groups']])
 write('04_REGRESSION_TESTS.md',f'''# 测试与历史案例覆盖

全部相关项目测试结果：**{tests['total_tests']}通过，0失败，0跳过**。BoT两个`test_templates.py`是字符串模板常量，不含可收集测试，pytest返回5；已单独列出，不虚报为已执行测试。

{groups}

V3基础正反例64项，历史真实记录89项。后者包括首批9个确认误判、第二批全部22份旧新评分分歧（包括非主表的E控制响应）、17覆盖问题和3漏解题的两套输出、完整错误/截断和普通样本。

负例覆盖缺一个根、±只取正支、区间错误端点、百分数语义混淆、量纲错误、more/less方向错误、变量域丢失、矩阵维度/元组顺序、任意Python表达式、资源限制、隐藏reasoning、仅示例的boxed、最后答案推翻中间结果、未封存回答。task ID改名后结果不变。新评测模块中不存在task ID特例。

原FlowEvo gold隔离、Recovery、BoT所有历史策略和实验数据完整性测试仍通过。测试进程强制禁止网络；历史测试中的LLM均为FakeLLM/模拟transport。

第一次全套测试使用pytest importlib模式，导致原BoT中直接`from conftest import ...`的5个模块收集失败；恢复其原有prepend模式后仅重跑该组，134项全过。保留首次日志和重跑日志，未修改旧项目测试以迁就新接口。

实际集成另执行原生MATH loader读取本地数据，导出6道封存回答，通过Legacy默认、Fixed、V3三种CLI配置；V3六道全部正确。输入/输出路径相同或已存在时拒绝覆盖。
''')
 allcounts=[]
 for branch,info in audit['branches'].items():
  for name,c in info['counts'].items():allcounts.append([branch,name]+[c.get(status,0) for status in ['correct','incorrect','unknown','reference_ambiguous','reference_invalid','prediction_incomplete']])
 write('05_MATH500_COMPARISON.md',f'''# 两套500输出的配对比较

{score}

{table(['分支','评分器','Correct','Incorrect','Unknown','Ref ambiguous','Ref invalid','Incomplete'],allcounts)}

Legacy/Fixed没有独立reference和incomplete结果类别，表中保留其实际历史状态；旧评分器的incorrect包含截断，不能解释成纯数学错误。V3将未完成独立列出。

首轮相对Legacy新增11、退出确认1，净增10；相对Fixed新增18、退出确认1，净增17。自适应相对Legacy新增11、退出确认1，净增10；相对Fixed新增20、退出确认1，净增19。两分支各有9份V3新增正确且两个旧评分器都未确认。唯一退出确认的是precalculus_187，状态为Unknown而非Incorrect。

Fixed Unknown由首轮16降到V3总Unknown1，自适应18降到1；但这不是原Unknown集合的简单包含关系：原34份Fixed Unknown都获数学证明且V3确认，新增2份Unknown来自指数限额。见逐题`evaluator_comparison_500.csv`和三维`scoring_transitions.csv`。

V3全1000份批量离线评分墙钟 {timing['wall_seconds']:.3f} 秒，12进程；逐记录耗时累计{timing['worker_seconds']:.3f}秒。历史复现（Legacy+Fixed合并调度）墙钟4.433秒。逐分支/评分器的累计、均值、中位数见`evaluation_timing.csv`；累计并行耗时不等于墙钟，冷启动导入及缓存不对称，因此不能由这些数值推出公平吞吐倍数。

本轮新增模型token=0。过去生成token及预算分配保留在旧实验；没有重生成、预算加码、token节省宣称或新显著性泛化检验。
''')
 write('06_SCORING_DISAGREEMENTS.md',f'''# 分歧逐题说明

共有首轮54份、自适应26份三状态分歧，其中36份是V3把旧incorrect拆为prediction_incomplete。所有分歧记录均纳入`adjudicated_cases.jsonl`，保留题目全文、原始最终文本、完整参考解答、所有候选、规范化对象、请求/响应hash、代码版本和独立问题证明。

之前20道确认问题逐题如下。ID均保留原始值；首轮仍截断的记录不因同题自适应答案正确而获得分数。

{case_table}

另外两道旧修复得分项：geometry_191的48°和prealgebra_385的20%继续判对。唯一V3新增弃权题precalculus_187在两分支均为2^2005，数学证明正确，解析限额不改变正式结果。

自适应仍未完成：algebra_1161、geometry_56、intermediate_algebra_494。完整但数学错误：number_theory_491提交54，正确30。这四道均未计为V3正确。
''')
 write('07_FALSE_POSITIVE_FALSE_NEGATIVE.md',f'''# 评分可靠性审计

审计独立于V3分数决策：`independent_proofs.py`只用公开问题中的条件建立54个确定性数学证书，不导入V3。证书包含两个历史批次和固定种子抽样题；后者在写证明前已按学科×难度段选定。题目特定的ID证书只属于离线审计，不被运行时评分代码使用。

第二批复核123份记录/75题ID：87份完整提交有问题级证明；36份核验为未完成。包括全部三评分器分歧、全部V3 Unknown、新增正确且两旧均非真的记录、全部参考问题、21道分层一致正确题的两分支，以及一致incorrect的完整错误题。必审集合无遗漏。

| 在已复核记录中 | Legacy | Fixed | V3 |
| --- | --- | --- | --- |
| 已证假阳性 | 0 | 0 | 0 |
| 将正确答案明确判incorrect | 22 | 4 | 0 |
| 正确答案但Unknown弃权 | 0 | 34 | 2 |

False negative文件明确区分incorrect假阴性与弃权，不能把Unknown直接叫数学错误。V3的两个弃权是同一道题的两套输出；题目级计数为1。

独立问题证明包括有理式解域/代回、对称多项式恒等式、完整根集、勾股/几何面积、离散穷举、组合计数、矩阵方程和三角恒等式。随机采样数值相等没有作为一般恒等证明。

代码大模型完成了阅读和证明编码，没有第二个独立审查者，也没有人类双盲裁决；这些证据不等价于独立人工金标准。877份自动评分记录未逐题进行问题级审查，无法排除共同假阳性。0个已知假阳性不是总体误判率0。

审计敏感性：仅把两份已证明正确的指数限额弃权加回时，首轮467/500、自适应496/500；此数不写回V3，不算独立新基准。V3自动确认覆盖率为93.2%/99.0%，Unknown均0.2%；参考审计共5题，其中3题末盒漏解、1题逆函数歧义、1题参考中间推导排印错误。各类型状态分布见`answer_type_statistics.csv`。
''')
 write('08_FLOWEVO_INTEGRATION.md',r'''# FlowEvo实际接入与重现

新组件`FlowEvo/src/math_evaluation`与新入口`FlowEvo/src/code_math/evaluate_offline.py`只做已提交答案的离线评分。已有solver、router、prompt、skill库、预算controller和旧评分代码均未改动。`OfflineScoringConfig`可选legacy/fixed/v3，默认legacy。

从仓库根目录运行（已有环境依赖已固定）：

```bash
Flowevo-Bot/.venv/bin/python experiments/math_evaluator_v3_offline/code/reproduce_history.py
Flowevo-Bot/.venv/bin/python experiments/math_evaluator_v3_offline/code/build_regression_fixtures.py
Flowevo-Bot/.venv/bin/python experiments/math_evaluator_v3_offline/code/run_all_tests.py
PYTHONPATH=FlowEvo/src:Flowevo-Bot/src:FlowEvo-Recovery/src Flowevo-Bot/.venv/bin/python -m code_math.evaluate_offline --input experiments/math_evaluator_v3_offline/evidence/input_records.jsonl --output /tmp/math_v3_replay.jsonl --evaluator v3 --workers 12 --unknown-output /tmp/math_v3_unknown.jsonl
```

输出必须是新文件，已有文件不会被覆盖；重复运行请换输出名。只比较status/typed evidence和hash，elapsed_seconds自然会变化。安装到新环境时使用`FlowEvo/requirements-math-evaluator-v3.txt`；原有FlowEvo基础依赖不变。

原生任务适配：`from_flowevo_task(CodeTaskInstance, runner_record, submission_sealed=True)`使用`task.canonical_solution`；不把loader截断的`metadata.gold_answer`给V3。原生runner记录键`solution`映射为可见模型回答；没有finish_reason时保留None并标识不可用，不伪造stop。legacy/fixed仍可重放其传入的冻结历史gold。

本轮实际用原生`load_math()`从本地Parquet读取6道题，按问题全文关联之前已封存的回答，导出`evidence/native_loader_tasks.jsonl`及`native_runner_records.jsonl`，三种CLI均运行。它不是新的solver运行。命令与结果在`evidence/integration_smoke.json`。

Gold隔离是接口契约：必须有submission_sealed标记；没有任何结果回调、反思或重试入口；ModelExtractor签名没有gold参数；批处理worker禁止socket连接。调用者拥有输入数据时仍需遵守进程阶段隔离，这不是阻止恶意调用者读本地gold文件的访问控制系统。

历史实验配置中的skill_injection/history_retrieval/gold_answer_feedback/gold_driven_reflection/correctness_retries均为false，本轮没有生成阶段。此前项目仍保留显式指定旧训练策略库的通用能力；本轮未调用或开启它。哈希证明旧执行代码、请求响应和Prompt全部不变。
''')
 write('09_REMAINING_LIMITATIONS.md','''# 剩余限制

1. 唯一500题内的自动Unknown是precalculus_187；两套输出相同。2^2005超过固定指数上限1000。审计已证明正确，正式结果仍弃权。将来可在独立复杂度测试中按计算成本放宽，但本轮未以目标分数反推限额。
2. AnswerSpec的语言层仍是规则推断；未识别问题会弃权，错误推断也可能造成错误类型/单位。这次开发曾发现ABC误当选项、计数有序对误当元组，已形成反例，但不宣称穷尽全部自然语言歧义。
3. 单位注册表有限；转换需显式允许。复杂复合单位、上下文约定和舍入仍不完整。单位值转SI后的精度路径可能保守拒绝，未来需补原单位舍入语义。
4. 多变量分母域、复杂对数分支、分段函数、关联多个±、隐式集合/参数区间、特殊函数可能Unknown。有限数值抽样不能代替证明。
5. 完整参考Builder只能作结构性完整判断；未证明所有500个参考解答的真值。推导笔误、非单射逆函数和附加条件问题需独立审计。
6. 解析器使用固定版ANTLR内部接口。字符/宏限制、复杂度和进程超时降低风险，不是通用安全沙箱。单条evaluate不设置调用进程的地址空间限额；处理不可信批量输入应使用evaluate_batch。
7. 多段候选结论、只有自然语言回答、没有finish_reason的旧日志存在不可消除的提取不确定性。Unknown必须保留，不能用gold寻找“更合适”的候选。
8. 500道题用于既有错误发现和本轮工程回归，存在回顾性适配；21题抽样也不是新的留出集。123条已审查记录不能代表全1000条。没有独立人类双审。
9. V3更慢：严格ANTLR和域检查增加本地耗时；本轮1000条12进程约8.64秒，可用于离线科研。未作跨机器公平性能基准。
''')
 write('10_NEXT_STEP.md','''# 下一轮科研决策建议

已审查的格式、解集、单位、域约束和完整参考问题中，V3比两旧评分器更可靠：覆盖问题减少，明确错误与未完成仍被拒绝，已核验假阳性为0。该结论只适用于现有审计范围，不证明全局真实正确率。

建议保留V3为可选的正式离线组件，暂不替换默认Legacy。下一轮先冻结题目类型规则和参考规范，在未参与开发的独立题目/人工构造反例上做盲测；优先复核共同判对题，安排两位独立审查者评估False Positive，再决定是否切换默认。

将复杂度预算与表达式计算成本对应，完善单位原值舍入与全解完整性断言，扩展域约束/引用答案完整性审查。所有调整先做独立回归，不能以达到496/500为优化目标。

本轮工作止于代码、零LLM离线比较、证明和复核材料、测试、ZIP与GitHub发布。没有启动新的模型实验；发布成功后等待下一轮研究指引。
''')
 print('11 research reports written')
if __name__=='__main__':main()
