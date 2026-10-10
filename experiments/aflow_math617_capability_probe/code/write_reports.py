"""Render reports from the completed, audited experiment; no API use."""
from common import *
from analyze import csvfile
import collections

NAMES=['EXECUTIVE_SUMMARY','DATASET_AND_SPLIT_AUDIT','DEEPSEEK_BASELINE','TRUE_FAILURE_ANALYSIS','PASS_AT_K_ANALYSIS','CANDIDATE_SELECTION','GENERATION_SELECTION_GAP','AFLOW_WORKFLOW_COMPARISON','ACCURACY_AND_COST','NEXT_RESEARCH_DIRECTION']
SUB={'counting_probability':'Counting & Probability','number_theory':'Number Theory','prealgebra':'Prealgebra','precalculus':'Precalculus'}
def pct(v):return f'{100*v:.2f}%'
def table(head,rows):return '| '+' | '.join(head)+' |\n|'+'|'.join(['---']*len(head))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n'for r in rows)
def write(i,text):
 (OUT/f'{i:02d}_{NAMES[i]}.md').write_text(text.strip()+'\n')

def main():
 summary=read(OUT/'summary.json');dataset=read(OUT/'dataset_manifest.json');b=summary['baseline'];cost={r['method']:r for r in summary['costs']}
 totals=table(['划分','题数','冻结V3判对','数学复核后确认正确','截断','语义未定','复核后准确率下界–上界'],[[s,b[s]['n'],b[s]['v3_correct'],b[s]['reviewed_math_correct'],b[s]['incomplete'],b[s]['math_unresolved'],pct(b[s]['math_accuracy_lower'])+'–'+pct(b[s]['math_accuracy_upper'])]for s in ['validation','test','all']])
 subjects=table(['学科','题数','V3判对','复核确认正确','截断','未定','复核准确率下界–上界'],[[SUB[s],m['n'],m['v3_correct'],m['reviewed_math_correct'],m['incomplete'],m['math_unresolved'],pct(m['math_accuracy_lower'])+'–'+pct(m['math_accuracy_upper'])]for s,m in summary['baseline_by_subject']['all'].items()])
 ps=[r for r in summary['pass_at_k']if r['subject']=='all'];passtable=table(['验证集指标','V3确认正确','复核确认正确','复核准确率','调用数','tokens'],[[f"Pass@{r['k']}",r['v3_correct'],r['math_correct'],pct(r['math_accuracy'])if isinstance(r['math_accuracy'],float)else '未运行',r['logical_calls'],r['tokens']]for r in ps])
 gaps=[r for r in summary['selection_gap']if r['subject']=='all'];selectiontable=table(['验证集方法','V3判对','复核判对/119','距复核Oracle题数','新增选择调用'],[[r['method'],r['selected_v3_correct'],r['selected_math_correct'],r['gap_tasks'],0]for r in gaps]+[['oracle Pass@4',113,119,0,'仅离线指标']])
 source='[AFlow官方仓库](https://github.com/FoundationAgents/AFlow)、[论文v3](https://arxiv.org/html/2410.10762v3)。'
 write(0,f'''# 实验结论：NO-GO（当前数据上的复杂推理机制研究）

本轮完成全部规定基础阶段，条件阶段按预先门槛停止。实际恢复并运行的是作者当前公开的 **605道题**，不是已验证的论文617道。论文数值与作者档案不一致；不能用本结果声称复现论文同一批617题。

{totals}
冻结V3总分为572/605（94.55%）。复核后597题确认正确、6题截断、2题题意/参考约定未定；**确认的完整数学错误为0**，这不等于对全部推导做了形式化证明。未定题保持None，不按错误或正确强行归类。597/605–599/605是未定标签敏感性区间，不是置信区间。排除两道歧义题的描述性成绩为597/603=99.00%，不能代替完整分母。

{subjects}
{passtable}
{selectiontable}
新增候选仅恢复1道首次截断题，未恢复任何已确认的完整数学错误。不存在四个候选全部答错的已确认数学失败题。Pass@8未达到预先登记的“至少3道、至少2学科”新增恢复门槛，故未运行；不能称8次仍失败或Pass@8等于Pass@4。

基线605份输出共1,068,216 tokens（含7份历史合法复用）；Pass@4额外357次、626,236 tokens。物理新增955次、1,682,920 tokens，全部usage已返回；选择器本地执行，额外API为0。峰值未缓存价格估算本轮约1.9044美元，非实际账单。

官方冻结工作流已恢复、静态检查，未支付运行，不能宣称优于或劣于本轮方法。主要剩余问题是截断、评分语义以及数据的天花板。建议下一轮先修复评测契约，再批准更难且无历史暴露的新验证集；本轮停止，不扩展数据集或启动MCTS。

划分不是全新独立样本：验证21题、测试122题有已知历史求解/分析记录；更严格的无已记录直接/近重复风险子集为83/327。见01、02和逐题manifest。{source}
''')
 splitrows=[]
 for sub in sorted(SUB):
  v=dataset['partition']['validation']['subjects'][sub];t=dataset['partition']['test']['subjects'][sub];splitrows.append([SUB[sub],v,t,v+t])
 write(1,f'''# 官方数据与划分核验

未能唯一恢复论文写的617题。当前官方数据包只有605题，所有题均Level5，原样保留验证119/测试486。它们逐题原文和其他字段均与本地MATH测试集对应，既没有自行补12题，也没有重新抽样。

{table(['学科','官方验证','官方测试','合计'],splitrows)}
{source} 数据下载脚本指向[作者数据档案](https://drive.google.com/uc?export=download&id=1DNoegtZiUhWtvkd2xoIuElmIi4ah7k8e)。当前仓库提交为`3f457218fc716093fe53f6df8a5d5e6379d66346`。旧版作者MetaGPT下载脚本也指向同一个档案。作者公开结果的88份119行验证CSV及2份486行测试CSV，其问题集合均与当前对应划分完全一致。这支持“作者公开档案605”，不能解释或消除论文12题差异。

论文报告seed42及20%/80%划分，并描述以5次初始运行选择高方差验证题。未找到能够唯一重建617或后续保留索引的脚本/清单；当前`AFlow/scripts/evaluator.py`的验证和测试`va_list`均为None。各科验证数等于各科总数乘20%向下取整，但这不是种子算法的重现证据。本轮只使用作者提供的原始119验证行，未做标签驱动筛选。

官方JSONL不带原始任务ID。`dataset_manifest.json`列出全部605个本地规范化ID、官方文件行号、原始字段哈希、问题哈希和划分；ID通过精确文本和全部字段匹配建立，不能当作作者原生编号。内容摘要采用`common.digest`的排序JSON SHA256；文件摘要为字节SHA256。两划分题目ID/规范化文本无交集。

复用此前近重复审计，再对新增500+40历史题做数字遮罩RapidFuzz ratio≥90检查。ID/文本匹配含本地7500训练题、5000测试题；历史索引涵盖训练/开发/Skill Bank和研究记录。训练池或公共题目目录的出现，不等同于实际解题暴露；保守风险与实际记录分字段标注。

{table(['划分','已知历史求解/分析','另有保守登记风险','严格无已记录直接/近重复风险'],[['validation',21,2,83],['test',122,11,327]])}
严格子集是描述性分层，未用它替换官方分母。近重复仅是风险提示，不证明语义相同；不保证不存在预训练污染。完整路径证据、各题匹配见manifest与`evidence/official_csv_partition_checks.jsonl`。
''')
 strat=table(['划分/风险层','确认正确/题数','未定','截断'],[[split+'/'+name,f"{m['reviewed_math_correct']}/{m['n']}",m['math_unresolved'],m['incomplete']]for split,g in summary['exposure_strata'].items()for name,m in g.items()])
 write(2,f'''# DeepSeek Flash 单次16384强基线

请求/返回model均为`deepseek-flash`；实际每次返回的`system_fingerprint`保留在raw与api账本，服务端权重版本不能锁定。沿用FlowEvo的原生数学CoT消息：system为“You are an expert programmer and mathematician.”，user为公开题目加分步求解和终答标记。Gold feedback、gold reflection、Skill检索/注入均关闭。

每题一次16384上限，默认thinking开启、reasoning effort high；参数省略，实际响应有reasoning字段和reasoning_tokens。请求temperature=0，但[官方思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/)说明该模式下此参数不生效；无可用seed。候选是独立HTTP调用，不宣称固定种子可重现服务端采样。API峰值64、本地12。

{totals}
{subjects}
验证先求解和审计；选择器输出在新增候选评分前封存；`METHOD_FROZEN_FOR_TEST.json`随后冻结方法，再正式请求测试集479个新输出。另7个测试输出复用上一轮无条件direct16384：请求体完全相同，逐份响应哈希可核实。没有复用按失败条件触发的高预算重试，也没有根据本轮正确性补采样。

{strat}
MathEvaluator-V3源码树哈希`ddf574ce8adacc73a91e59370cf0310daf82bd192bba66adcadfff563a9007e6`，配置哈希`6ac932c2464edb410709e5e30e373f354d3c38b8b15321c31a0914701211fab6`，版本3.0.0、4秒/题、12workers。本轮没有修改评分器。V3非正确项逐份补充数学复核证据；完整输出、thinking、finish_reason、tokens、Unknown原因、复核分轨见baseline_results/raw/grading。

本轮未给测试集运行Pass@4选择器，因此候选选择的提高只能称验证集探索结果，不能称独立测试集算法提升。已知历史暴露同样限制泛化主张。
''')
 write(3,'''# 真正数学失败审计

605题基线中，V3非正确33题：25题评分/提取问题B、6题未完成A、2题参考或题意歧义H。未检出已确认的完整数学错误C/D/E/F/G，未知原因I为0；两题H保留数学标签None。仅审计非正确候选和代表性推导，不宣称全体正确响应已获形式化证明。

验证基线为6B+1A。完整验证候选池476份中，30份B、4份A，没有确认完整数学错误；4个截断候选分布在2道题。测试基线为19B+5A+2H。逐学科/类型/题数与响应数分别保留于failure_taxonomy.csv，避免将同一道题的多个候选当多个独立失败样本。

代表性评分缺陷包括：三进制与二进制小数、MAKE/Friday文字答案、角度集合、区间目标误识别、元组/列向量的同一空间点、明确单位以及矩阵行距。`precalculus_277`、`211`等的`\\[2pt]`或`\\[2mm]`是LaTeX排版，冻结解析器却引入额外符号，从而产生假incorrect。这些缺陷没有在本轮测试后回改V3或候选选择规则。

`precalculus_442`：模型明确使用arccot值域(0,π)，得到四个根±(3±2√2)；参考采用与atan一致的另一分支，仅保留正根。题目未给值域，不能直接把额外负根认定为约束遗漏。分类H、未定。

`precalculus_469`：按参考意图n≥0，角度三倍映射给出3^2007，模型推导正确；V3另有指数上限。但原题明确只说递推对正整数n成立，未约束a0→a1。按字面，任意实数a0都可由某个a1经2006次奇次多项式迭代到达，答案不是有限的3^2007。保持H，分别保存两种解释，未擅自修题。

6个基线截断ID：counting_probability_327、number_theory_242、number_theory_262、prealgebra_145、precalculus_426、precalculus_485（均带math_test_前缀）。其中precalculus_426有223字可见半成品，其余5份无可见终答。hidden reasoning里的候选答案不计为完成。不能由“未提交”推断模型数学不会。

唯一验证恢复例：precalculus_485的前三份候选耗满16384且无终答，第四份完成半球内最大立方体问题。对任意朝向、中心C、半边长r、正交矩阵U，有C_z≥r，最远顶点距离平方为||C||²+3r²+2r||UᵀC||₁≥6r²；因此边长≤10/√6，底面在z=0的正放立方体达到等号。这个全朝向证明支持第四份答案，不靠参考解预先假定朝向。详见evidence/cube_recovery_review.json。
''')
 per=table(['学科','Pass@1复核','Pass@4复核','新增恢复'],[[SUB[sub],next(f"{r['math_correct']}/{r['n']}"for r in summary['pass_at_k']if r['subject']==sub and r['k']==1),next(f"{r['math_correct']}/{r['n']}"for r in summary['pass_at_k']if r['subject']==sub and r['k']==4),next(r['new_recoveries_over_first']for r in summary['pass_at_k']if r['subject']==sub and r['k']==4)]for sub in sorted(SUB)])
 write(4,f'''# 完整验证集的Pass@k

{passtable}
{per}
119道验证题均有4份真实独立调用，第一份就是基线，没有只采样失败题。所有候选使用相同公开题目、CoT消息、默认思考配置和16384上限。请求体相同；HTTP完成ID独立。Pass@4是观察到的四候选存在正确解比例，不是选出正确解的自动能力，也不是无限采样概率估计。

首次未确认正确的7个V3任务中，1题新增候选被V3判对；其余6题本来就是数学正确的格式问题。按数学复核，首次失败仅1题，4候选恢复1/1；原始V3口径恢复1/7。这两个分母不能混用。

预先门槛为至少3题、至少2学科的新增数学正确恢复。本轮仅1题、1学科，且是截断恢复；Pass@8不运行，其结果为NA。没有测量“8次仍失败”。验证中不存在四份全部无正确解的数学失败题；V3口径有6个全不判对的任务，均属于同一评分支持缺口。

候选变化不等同于不同数学结构。逐题保存词法方法标签和数学等价分组；标签只能作为探索性描述。人工复核显示半球题反复探讨朝向最优性，第四份完成范数界证明；precalculus_44前三份用互余角恒等式或平方后恒等式得到相同正确结果，第四份反而截断。不存在可用于归纳“重复相同错误策略”的已确认完整错误样本。
''')
 write(5,f'''# 无Gold候选选择

{selectiontable}
选择程序只接收公开题目、候选文本、完成状态和响应哈希，拒绝额外gold/score/reference字段。使用V3公共解析/等价纯函数，不导入reference构建器或评分engine。选择结果在候选2–4首次离线评分之前封存，全部候选生成也在评分前完成。

First直接选第一份。Majority先做有类型的数学等价证明，再按最大等价组投票；并列取最早候选。截断不能成为有效票，无法解析的答案不伪装为数学相等；无可解析候选时回退最早完整答案。最终有451份成功解析、21份不支持、4份截断。公共解析仍继承矩阵行距等缺陷，所以本轮成绩不能证明归一化已经全面可靠。

Verification仅对完整匹配的单表达式求值题或单变量低次多项式全实根题产生精确公开证书；其他题记为证据不足。先选有证书的候选，再在未被公开证伪的候选中使用数学等价多数。没有足够证据时就是多数回退，不声称验证了复杂证明。

本轮仅2题/8个候选获得公共证书；其余468个候选没有完整验证证据。没有额外模型调用。半球题被选中是因为只有第四份完整可解析，并非该窄验证器证明了立方体最优性；后者是独立离线人工审计。多数和验证的119/119不能被宣传成“119题均通过数学证明验证”。

没有完整但确认错误的候选，故无法估计该验证器排除强错误解的能力。未根据测试标签调整排序，也未在测试集新增多候选实验。
''')
 write(6,f'''# 生成上界与实际选择的差距

{selectiontable}
复核Oracle119/119；First118/119，差1题/0.84百分点；Majority和Verification均119/119，差0题。冻结V3的Oracle113/119、First112/119、两种选择113/119。V3与复核的差别是评分支持，不是新增候选生成能力。

没有“池中已有正确解但多数/验证选错”的数学案例，也没有四候选全错的已确认任务。`generation_selection_gap.csv`按学科/方法保留差距，`task_pairwise.csv`列每题增益、成本和分组。统计上只有一次截断恢复，不能据此证明复杂选择算法收益；该单次配对改变也不构成有力显著性证据。

当前结果既不支持GO-SELECTION，也不支持GO-GENERATION：欠缺完整且可靠判定的数学错误样本。所谓零差距只适用于本119题、k=4、当前候选池，不外推到k=8或更困难问题。
''')
 write(7,'''# AFlow公开冻结工作流检查

已恢复作者结果档案中的`MATH/graphs_test/round_5/graph.py`、prompt以及template operator，逐文件哈希见evidence/official_workflow_audit.json。两份历史测试CSV各486行、验证CSV119行与当前数据集合一致。已进行Python语法解析；没有实际执行/计分/付费调用。

该流程包括：Programmer生成并运行Python（带执行错误反馈重试）、Custom整理代码结果、独立详细解答、另外两份解答、ScEnsemble通过模型选择四份文本之一。它依赖历史MetaGPT ActionNode/provider接口，模板还引用Gsm8K路径；当前独立AFlow库使用不同接口。不能把当前算子直接替换后称为原封不动的官方运行。

本轮验证基线已118/119，多候选只恢复一次截断，尚无完整数学错误或选择能力缺口。按指引的可选条件，本轮不追加迁移后的付费对照，也不启动完整MCTS。不是宣称工作流永远不可运行，而是本轮没有足够研究信号且未经验证的接口替换会影响归因。

因此官方工作流相对DeepSeek基线的优劣为“未测”，调用数与tokens均0。原论文优化/执行模型与本实验不同，不引用原文正确率当作同条件比较。原始源文件和档案已随交付保存。
''')
 costtable=table(['方法/阶段','输出数','本轮新调用','复用','输入tokens','输出tokens','reasoning tokens','总tokens','峰值美元估算'],[[r['method'],r['logical_completed_calls'],r['new_completed_calls'],r['reused_calls'],r['input_tokens'],r['output_tokens'],r['reasoning_tokens'],r['total_tokens'],r['peak_uncached_usd_estimate']]for r in summary['costs'][:6]])
 write(8,f'''# 正确率和成本

{costtable}
这些行有重叠，不可相加：Pass@4池已含验证基线；all605基线已含验证和测试。物理新增总计955次HTTP成功、1,682,920 tokens；0次usage未知、0次网络重试。另复用7次、11,532 tokens，旧费用不计入本轮新支出。605基线逻辑总耗1,068,216，新增Pass@4耗626,236；合计逻辑962次、1,694,452 tokens。

Pass@4相对验证基线增加357调用、626,236 tokens，获得1道截断恢复；池总耗为基线{837738/211502:.2f}倍。每次复核恢复的额外成本为626,236 tokens，不能叫“每修复一个完整数学错误”的成本，因为完整错误恢复数为0。两种本地选择器额外API/tokens均0，但仍需整个候选池的生成成本。

正式调用前预算文件估算955新调用、4,106,500 tokens、4.66995美元；实际tokens更低。1000万token/1500请求为固定安全上限，失败未知usage会按保守上界占用；本轮未触发。API最大实际并发64、本地评分/选择最多12。

费用采用[DeepSeek公开价格](https://api-docs.deepseek.com/quick_start/pricing/)中峰值未缓存输入0.30美元/百万、输出1.20美元/百万估算。本轮物理新增估算1.904413美元；并非账单，未断言缓存/非高峰折扣实际结算。reasoning tokens属于completion子集，未再次相加。原始usage保留缓存命中和实际reasoning计数。

{totals}
不得只展示复核后高分而隐藏V3错误，也不得把两道语义未定按模型错误统计。独立性限制和严格风险层成绩见02。
''')
 write(9,'''# 下一阶段研究决策：NO-GO

当前605题不支持继续投入复杂生成搜索、候选排序或新Skill/Memory机制。理由是：确认完整数学错误0、验证基线118/119、Pass@4只有一次截断恢复、简单多数已经达到本候选池的复核Oracle。两道测试题语义未定不能充当新算法训练目标。

优先级建议：先在独立开发用例上修复数学评测契约，包括矩阵排版、角度/进制/单位、区间/向量表示，以及逆函数分支和递推起点的歧义标注。修复后建立新评分版本并单独回归，不能覆盖本轮冻结V3结果。随后由下一轮授权选择更难、历史暴露更少且参考可靠的数学集，先测完整错误密度，再决定生成或选择研究。

本轮不能从“多次截断”推断“不会数学”，不能从“零完整错误”宣称普遍数学能力完备，也不能从“多数零差距”宣称选择问题已经解决。条件结论仅针对当前模型、提示词、预算和可恢复官方数据。

若未来验证集确有多个正确/错误候选竞争，再评估GO-SELECTION；若多候选仍无正确解，再评估GO-GENERATION及分解/工具方法。当前两种现象均未得到足够证据，不预先设计复杂控制器。

本轮研究、数据/日志/代码及压缩包完成后上传现有仓库即停止。没有自动运行其他数据集、Pass@8、AFlow付费对照或MCTS。
''')
 (OUT/'README.md').write_text('''# AFlow数学能力边界实验

实际官方数据605题（119验证/486测试），目录按用户指引保留617名称；不能称精确617复现。

阅读顺序：00摘要 → 01数据审计 → 02–08结果 → 09决策。所有机器可读指标由summary.json和逐题文件支持。冻结V3与响应哈希绑定的数学复核分别保存；两题H保持null。研究决策NO-GO，条件实验未满足门槛不是未完成交付。

已完成输出全部保留。不要为复现统计再次付费：在工作区使用`Flowevo-Bot/.venv/bin/python experiments/aflow_math617_capability_probe/code/analyze.py`和`code/write_reports.py`即可从现有证据重建报告（第二条使用相同目录前缀）。原始生成入口为`code/generate.py`，阶段参数依次validation1、validation4、test1；已有seal时只校验并退出，不重发。不得重新运行preflight来覆盖原始事前预算时间戳。

实际流程：数据审计/预算冻结 → 9项生成测试 → validation1生成封存/评分/人工复核及12项选择测试 → 完整validation4生成 → 公共选择封存 → 候选2–4评分/人工复核 → Pass8门槛决策/方法冻结 → test1单次生成（复用7份）→ 冻结V3评分（复用7份旧评分）→ 数学审计 → 汇总及交付验证。选例依赖公开数据元信息；gold只用于离线评分/审计/Oracle，未反馈给求解器。

原始作者档案、605题和官方行序位于data/official及evidence；source/data SHA见manifest和freeze。raw保存逐调用请求和完整响应，`.sse.gz`保留新调用原始流；attempts记录物理调用，api_calls含7份历史复用行。candidate_generations只有完整119验证集的476个候选，baseline_results包括605个第一候选。不要将逻辑方法费用重复加到物理API总账。

所有候选均无Skills/Gold反思；API64、本地12；冻结V3源代码不变。手工审计脚本的ID映射仅用于重现人工证据，不会被生成或选择程序读取。具体case证明可在*_adjudications.jsonl、failure_cases.jsonl和evidence/ambiguous_reference_cases.json中查阅。
''')
 save('run_manifest.json',{'created_at':now(),'reference_commit':REF,'status':'completed','decision':'NO-GO','directory_label_n':617,'paper_exact617_recovered':False,'actual_official_n':605,'validation_n':119,'test_n':486,'baseline_metrics':b,'actual_new_http_attempts':955,'actual_new_tokens':1682920,'reused_outputs':7,'reused_historical_tokens':11532,'all_logical_outputs':962,'pass4_validation_completed':True,'pass8_status':'not_run_gate_not_met','aflow_comparison_status':'source_restored_not_executed_optional','gold_feedback':False,'gold_reflection':False,'skill_injection':False,'api_peak_concurrency':64,'local_workers':12,'evaluator_source_sha256':read(OUT/'evidence/pre_api_freeze.json')['evaluator_source_sha256'],'evaluator_unchanged':True,'existing_experiments_not_rerun':True,'historical_tests_reused':498,'new_tests_initial':21,'noncorrect_responses_reviewed':len(jl(OUT/'failure_cases.jsonl')),'source_and_labels':{'dataset_manifest_sha256':sha(OUT/'dataset_manifest.json'),'generation_freeze_sha256':sha(OUT/'evidence/pre_api_freeze.json'),'test_method_freeze_sha256':sha(OUT/'checkpoints/METHOD_FROZEN_FOR_TEST.json'),'selection_seal_sha256':sha(OUT/'checkpoints/selection_k4_SEALED.json')},'new_paid_calls_closed':True,'next_action':'Validate delivery, package, publish, stop.','limitations':['605 differs from paper617','Historical exposure and possible pretraining contamination','Two semantically ambiguous test questions remain unresolved','No verified complete mathematical error sample','Selection measured on validation only','Alias/backend stochasticity not reproducibly seedable']})
 print({'reports':10,'decision':'NO-GO','math_correct':b['all']['reviewed_math_correct'],'unknown':b['all']['math_unresolved']})
if __name__=='__main__':main()
