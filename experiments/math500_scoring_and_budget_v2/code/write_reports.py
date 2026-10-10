"""Render the final research reports from sealed results and separate audit notes."""
from common import *
import csv,collections
from paired_statistics import distribution,paired

def table(headers,rows):
 return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x).replace('|','\\|').replace('\n',' ') for x in row)+' |' for row in rows])
def doc(name,text):(OUT/name).write_text(text.strip()+'\n')
def main():
 s=read(OUT/'summary.json');m=read(OUT/'manual_audit_summary.json');d=read(OUT/'dataset_manifest.json');calls=jl(OUT/'api_calls.jsonl');reviews=jl(OUT/'manual_audit_results.jsonl');fail=jl(OUT/'remaining_failures.jsonl');cfg=read(OUT/'config.json')
 four=table(['方法','正确/500','正确率','unknown','输入 tokens','输出 tokens','总 tokens','调用'],[[x['method'],x['correct'],f"{x['accuracy']:.1%}",x['unknown'],x['input_tokens'],x['output_tokens'],x['total_tokens'],x['api_calls']] for x in s['four_way']])
 contributions=table(['比较','净增正确题','百分点'],[[k,v,f'{v/5:+.1f}'] for k,v in s['contributions'].items()])
 stages=table(['阶段','调用','完整','Fixed正确','unknown','仍截断','输入','输出','总tokens'],[[r[k] for k in ['stage','calls','complete','correct_fixed','unknown_fixed','truncated','input_tokens','output_tokens','total_tokens']] for r in s['stages']])
 note='**口径：**主结果严格使用调用前冻结的评分器；unknown 不计入“确认正确”，但也不代表数学错误。A/B共享首轮输出，C/D共享自适应最终输出；四行调用和token不能相加。逐题人工/符号审计是事后敏感性分析，不替换主成绩。'
 doc('00_EXECUTIVE_SUMMARY.md',f'''# 新独立 MATH 500：评分修复与自适应预算

研究决策：**PARTIAL**。自适应预算在冻结 Fixed 口径下由449提高到476（+27题、+5.4个百分点）；历史评分修复在新格式上的覆盖不足，反而比 Legacy 少计7题。因此不能声称两项技术都已独立复现正收益。

{four}

{note}

{contributions}

B→D：配对变化449均正确、27新增正确、0由正确变未判对、24均未确认正确；双侧精确McNemar p=1.4901161193847656e-08，20,000次配对bootstrap的95%差值区间为+3.4至+7.4个百分点。一次抽样、一次生成，尚不能证明所有数据分布和模型版本都有同样收益。

首轮33/500截断且缺最终答案；8192产生22个完整回答，其中Frozen Fixed确认19正确、2 unknown、1确实错误；16384再产生8个完整且正确回答，最后3个仍截断。完成数增加30，自动确认正确增加27；复核后实际交付正确答案的敏感性增量为29。不能把“完成”与“答对”混为一谈。

同一33题的4096重采样E完成10、Fixed正确9；8192完成22、Fixed正确19。两者配对净差10/33，p=0.00634765625，95%差值区间12.12至48.48个百分点。这支持额外预算具有增量价值，但两次独立采样、小样本和后端随机性仍妨碍完整因果分解。

D未确认正确24题：17评分覆盖缺口、3参考多解提取不完整、3截断、1完整数学错误。参考歧义还有1项次级标记（截断的逆函数题）。逐题审计后敏感性成绩为首轮467/500、自适应496/500，**不是Frozen Fixed成绩**，也不是由独立人工委员会完成的全面500题认证。

唯一明确错误是number_theory_491：8192输出54，把四个连续整数6,7,8,9之和误换成四个合法起点6,11,16,21之和。完整回答未触发16384。

实际577次HTTP/正常调用，输入80,550、输出898,016、总978,566 tokens，按当时官方非高峰与缓存细分费率估计USD0.550121。自适应比基线额外44次、291,912 tokens、USD0.169854，约10,811.56 tokens和USD0.006291/新增自动确认正确题。E的33次、127,727 tokens、USD0.072773单列；费用为估计，非账单。

历史回归464→473、9修复、原正确0损失已复现；源代码、规则与全部响应hash未变。排除7,500训练题及1,190历史/保守排除测试题，再经数字掩码全局近重复过滤后从3,256题中按原学科×难度分层抽500，seed20261010。不是官方标准MATH-500。

报告索引见README；主依据为summary.json、four_way_task_comparison.csv、scoring_disagreements.csv、truncation_recovery.csv、manual_audit_results.jsonl、api_calls.jsonl和原始HTTP正文。后续先修复一般性的标签完整性和评分类型覆盖，在独立开发集验证再换新测试集；同时研究答案完成。单个真实错误不足以支持立即扩大复杂推理算法研究。本轮完成后停止，没有自动启动新实验。
''')
 strata=table(['学科','L1','L2','L3','L4','L5','合计'],[[subject]+[next(x['new_count'] for x in d['strata'] if x['subject']==subject and x['level']==f'Level {i}') for i in range(1,6)]+[sum(x['new_count'] for x in d['strata'] if x['subject']==subject)] for subject in sorted({x['subject'] for x in d['strata']})])
 doc('01_DATASET_AND_CONFIG_AUDIT.md',f'''# 数据与配置审计

参考提交`{REF}`，运行前发布仓库main与远端main都与其一致；本地工作区根目录不是Git仓库，发布checkout在`/mnt/Space1/Flowevo-Bot-upload`。原生FlowEvo上游HEAD记录在evidence/pre_run_version_check.json。历史4,617个发布文件在最终审计中仅根目录指引.txt因本轮用户新指令改变，其余历史源码和实验输出均未覆盖。

## 独立性与固定抽样

本地MATH源是EleutherAI/hendrycks_math，train7,500/test5,000。全部train保守排除，覆盖历次建库、验证、V1–V4开发/确认池；通过历史实验、运行记录、诊断和代码记录排除1,190个test ID，其中含旧500、27截断和9评分修复题。原生math_subject_i别名保守归到test。逐条来源见evidence/exposure_registry.json和exposure_artifact_index.json。

剩余3,810 test候选，与全部8,690排除题做全局比较（没有按学科阻断）：小写、空白规范化、数字掩码后的RapidFuzz Indel/LCS相似度≥90%视为近重复。排除554，剩3,256。固定seed20261010分层洗牌，逐学科×难度匹配旧500数量；选中内部也做全对近重复过滤，另跳过3个候选。选择只依赖题目与元数据，没有按答案、历史正确率或截断表现筛选。

{strata}

500个ID、split、problem hash、seed、exposure状态在dataset_manifest.json；完整公共题干在data/public_tasks.jsonl，标签独立保存。2026-10-10 07:30:42 UTC冻结数据，07:34:03 UTC冻结在线配置/代码，所有API调用均在其后。audit_artifacts.py核对hash、时间及重试集合。

局限：这是对**项目可追踪研究使用记录**的独立性，不能排除模型预训练、未记录的外部使用或语义近重复。原始全量测试目录和静态数据清单以前已存在；其存在不等于已解题或参与调参，不把它们误称为从未可见。所有实际开发/确认池则明确排除。

## 求解环境

- 原生`FlowEvo/src/code_math/runner.py::build_goldfree_math_prompt`，`cot_baseline`、`library=None`；native prompt经导出逐字核验。
- 模型请求名`deepseek-flash`，endpoint `https://api.deepseek.com/chat/completions`，temperature=0；其他参数不随阶段改变，仅max_tokens=4096/8192/16384。
- thinking字段遵循历史方式省略。官方当时默认启用high reasoning；思考模式下temperature不生效，所以请求temperature=0不代表确定性。响应仅提供模型别名，精确后端revision未返回，记unavailable，不能声称已固定不可变模型权重。
- Gold反馈、Gold反思、Skill注入、历史Skill检索、正确性重试、额外修复提示均显式false。在线路径不读取offline_labels；公开prompt字段白名单+精确请求重建检查阻断额外答案字段。
- 64个共享API worker；账本时间区间重建峰值64；本地评分/近重复最多12进程。
- 运行Python3.10，依赖版本见evidence/runtime_packages.json。旧新评分器文件hash见evidence/evaluators_frozen.json。

源代码审计、配置拒绝测试、577条真实请求精确重建均通过：Gold/Skill实际注入0，检索0，正确性重试0。这里“无法读取答案”指实际在线代码/请求数据路径；不是声称有独立OS文件权限隔离，也不排除模型训练记忆。模型为无工具chat请求，不能自行访问本地标签文件。

API模型与thinking语义依据[DeepSeek官方接口说明](https://api-docs.deepseek.com/api/create-chat-completion/)，配置及获取时间证据见preflight与pricing文件。
''')
 gains=[r for r in reviews if r['category']=='confirmed_scoring_fix_gain']
 gt=table(['task_id','修复证据'],[[r['task_id'],r['review_evidence']] for r in gains])
 doc('02_SCORING_FIX_VALIDATION.md',f'''# 评分冻结与泛化检验

LegacyEvaluator与FixedEvaluator均直接适配上一提交源码，未重写判定规则。历史封存500输出复现Legacy464、Fixed473；9个假阴性全部修正，旧464正确没有丢失。详见01_EVALUATOR_AUDIT.md、evaluator_regression.json和scoring_regression_tests.json。

预调用59项测试包括嵌套boxed、数值/符号等价、集合/区间等原测试及8个新增反例：坐标顺序、区间开闭、集合漏项、符号、sqrt(x²)分支、x/x定义域、百分数数量级、错误单位。历史回归成功只说明旧案例保留，**不是新类型全覆盖的证据**。

新500正式固定预算：A456→B449，正改判2，负改判9（8 unknown、1false），净-7。自适应输出：C485→D476，正改判2，负改判11（10 unknown、1false），净-9。主分数不把unknown称为错误。

新题2个正改判均核验成立：

{gt}

27条响应/26题的事后审查覆盖全部22条评分器分歧及D所有24个非true候选。未发现这两个新正改判中的假阳性；这并非对所有500自动判true的全面人工证明。脚本math_scoring_v2.py保持原hash，未根据新结果加ID特判或放宽等价。

评分缺口包含：合法单位与换行单位、text包装数字/字母/odd、选择题字母、displaystyle矩阵、±多解和嵌套集合结构、区间与逻辑不等式、保守定义域拒判、线段标签。特别是intermediate_algebra_700两评分器都false，但CD明确正确；故单看评分器分歧会漏诊。

还有3个**参考答案构建问题**：intermediate_algebra_409、516、563原参考解分别boxed多个解，冻结的last-box提取丢掉其他解。原参考解和所有boxes、数学代入证据在label_integrity_audit.json。它们不是模型错，也不能靠放宽“集合等于单元素”来修。当前标签不回改，主结果保持冻结，完整解集只在事后审计记录。

本轮结论：历史Scoring Fix没有实现独立测试上的正向评分泛化。应在独立开发数据上先改进一般性的答案类型与完整参考集构建，检验错误单位、漏解、域限制等反例，再用新的held-out数据测试。不得用这一轮新增样本调参后继续把这500题当独立验证集。
''')
 doc('03_COMPLETION_CONTROLLER.md',f'''# 完成检测与预算控制

冻结逻辑：finish_reason=length优先触发；其次输出token达到max_tokens、正文空、缺少/不完整的boxed或“The answer is/Final answer”标记、finish_reason非stop均触发。只有明确完成才停止。length即使存在可见boxed也继续；这是保守的完成规则，不比较gold也不导入数学评分器。

首次500共享4096。其33个未完成题各有一次8192和一次E4096，第二阶段预声明按seed20261011随机交错发送；E结果不参与升级或最终选择。8192仍未完成的11题各做一次16384。自适应最终结果取执行的最后预算档，16384后无论对错均停。所有新请求重用相同原始问题和设置，只改max_tokens；不续写隐藏推理，不加入旧推理、诊断、参考答案或hint。

历史离线完成检测27真截断全命中，0漏报；473非截断0误触发。测试还覆盖空正文、推理无最终、合法LaTeX、未闭合boxed、length但可见答案、无显式标记的可能完整回答。对最后一类保守重试是已知局限。新题规则不调整。

{stages}

33个首轮未完成均为length且缺最终正文；8192将22个变为完整，16384另完成8，最终497完整、3截断。D完整回答中Frozen Fixed有476true、18unknown、3false；事后核验3false中2是评分覆盖问题，1是真错。

number_theory_491在8192产生完整错误54，因完成而停止；账本确认无16384，证明不是根据正确性升级。三道16384仍截断题仅隐藏推理中出现候选答案，未当作最终答案计分。

## 持久化与预算

每个task×stage固定job_id；发送前写pending，原始HTTP正文及attempt账本先落盘，完成后写JSON并删除pending。现存相同请求直接复用并检查响应hash；未知pending阻止盲目重发。仅明确429允许最多两次有限重试，超时/歧义失败保留证据并停止；本轮没有任何基础设施重试或错误。

所有worker共享条件锁和2,000,000 token上限；发送前以prompt UTF8字节+512+输出上限预留。预留是保守估算，不是tokenizer保证，实际超额会停止；本轮577次实际均不超过预留。最多2000正常调用、2100HTTP，达到阈值停止不扩容。历史预计564次/839,660 tokens，配置峰值费率保守上界USD2.4；实际577次/978,566，未触阈值。

封存文件和hash见checkpoints/ALL_GENERATION_SEALED.json。在线完成后再进行离线评分，最终审计验证封存以来所有响应/规则未变。断点复用、pending阻断、预算硬停等离线测试不调用API。
''')
 doc('04_FOUR_WAY_RESULTS.md',f'''# A/B/C/D 正式结果

{four}

{note}

A/B都是同一500条4096输出；C/D使用这500次加33次8192、11次16384，共544请求的生成流程。E是辅助33次，实际实验唯一请求577。A/B、C/D从未分别独立生成500题。

{contributions}

B较A少计7并非模型数学能力下降，因为输出完全相同；它反映新评分器类型覆盖不足。D较B增加27是固定评分口径下预算流程的收益；D较A增加20同时混合预算改善与评分口径改变。因此主要推断用B对D，不用D对A单独证明能力。

原始逐题数据four_way_task_comparison.csv保留答案、四个正确性、完成状态、两档调用、累积输入/输出/总token、评分影响与预算影响。空正确性字段代表unknown，不能将其解释为数学false。旧新详细判定及证据分别保存在legacy_scoring_results.jsonl和fixed_scoring_results.jsonl。

事后审计敏感性成绩首轮467/500、自适应496/500，保留自动true并仅审查所有分歧/剩余候选；它不是本表的新第五评分器，也不是全面独立人工标注成绩。
''')
 trans=table(['比较','两者正确','仅前者正确','仅后者正确','两者未确认正确','净差'],[[title,s[key]['both_correct'],s[key]['first_only_correct_harm'],s[key]['second_only_correct_benefit'],s[key]['both_not_confirmed_correct'],s[key]['second_correct']-s[key]['first_correct']] for title,key in [('A→B','paired_A_vs_B'),('C→D','paired_C_vs_D')]])
 doc('05_SCORING_CONTRIBUTION.md',f'''# 评分修复独立贡献

{trans}

B−A=-7，D−C=-9。两组输出均有相同2例度符号/百分数修复，但更多合法文本、单位和结构格式被unknown或false拒判。A→B丢失9项包含8unknown、1false；C→D丢失11项包含10unknown、1false。评分修复收益未在独立新题上复现。

评分分歧CSV包含完整模型输出、旧/新答案、原参考答案、两判定、解析证据、原始响应路径/hash、逐案数学证据、歧义与标签完整性标记。所有22条分歧均离线复核完成；task_id仅用于诊断记录的索引，没有进入运行时评分逻辑。

A/B同答案；因此Scoring Fix新增API调用和token均为0，但本地计算有成本。577条唯一响应上，两种评分共同用12进程耗时{s['scoring_local_wall_seconds']:.3f}秒；Legacy各worker调用耗时合计{s['legacy_sum_worker_seconds']:.3f}秒、Fixed合计{s['fixed_sum_worker_seconds']:.3f}秒。后两项是函数计时之和，非CPU计费秒，受初始化/并行/计时噪声影响。未以API价格伪造本地成本金额。

A→B精确McNemar p={s['paired_A_vs_B']['mcnemar_exact_two_sided_p']}；bootstrap差值95%区间[-2.8,-0.2]pp。离散精确检验与百分位bootstrap在小量不一致配对时可能给出不同阈值结论；不能因为后者不跨0就宣称所有检验均在0.05显著。C→D p={s['paired_C_vs_D']['mcnemar_exact_two_sided_p']}，CI[-3.2,-0.4]pp。这些是辅助分析，主要预算检验另见06。
''')
 groups=table(['分组','n','A','B','C','D','D−B','额外tokens'],[[g['group'],g['count'],g['A'],g['B'],g['C'],g['D'],g['D']-g['B'],g['extra_tokens']] for g in s['group_metrics']])
 doc('06_ADAPTIVE_BUDGET_CONTRIBUTION.md',f'''# 自适应预算独立贡献

固定Fixed评分下：449/500→476/500，净+27题（+5.4pp）。配对矩阵：449均正确，27只D正确，0只B正确，24均未确认正确。精确双侧McNemar p=1.4901161193847656e-08；预声明seed20261012、20,000次任务配对bootstrap，95%差值CI[3.4,7.4]pp。unknown按未确认正确计数并单列，不据此认定数学错误。

{stages}

4096截断33；8192完成22（19自动true、2unknown、1明确数学错），16384额外完成且自动正确8；3仍截断。自动恢复27/33=81.82%，完成恢复30/33=90.91%。独立逐案数学检查支持8192的2unknown也正确，因而敏感性正确恢复29/33=87.88%，并非30/33。

首轮全部467个完整回答中，两项自动false其实是集合格式与线段标签误判；审计未发现首轮完整数学错。唯一明确数学错由8192完成后显现。控制器不对这个完整错答增加预算。这说明完成状态控制不能保证数学正确。

{groups}

各学科/难度只是描述性分组，未作多重检验后的组内显著性主张。number_theory无净正确提升；难度5得到+11，额外165,044 tokens。所有分组和逐题分布均公开，不筛掉无收益类别。

额外44次，输入10,760、输出281,152、总291,912 tokens。全500的增量中位数0、均值583.824、P95约3005.75、最大25,432；升级33题的中位数4,993、均值8,845.82、P90约22,327.6。分位采用线性插值，见summary.json。

预算流程包括检测、独立重采样和增加上限，B→D收益不能全部归因于长度上限。07中的同预算E是部分机制拆分。即使E对照支持更大上限，本轮也没有干预模型隐藏推理链或控制每条生成轨迹。
''')
 rec=list(csv.DictReader((OUT/'truncation_recovery.csv').open()))
 eonly=[r['task_id'] for r in rec if r['control4096_correct']=='True' and r['upgrade8192_correct']!='True']
 honly=[r['task_id'] for r in rec if r['control4096_correct']!='True' and r['upgrade8192_correct']=='True']
 ec=[c for c in calls if c['stage']=='control4096'];hc=[c for c in calls if c['stage']=='upgrade8192']
 ds=table(['阶段','完整/33','Fixed正确/33','平均输出tokens','输出中位数','总tokens','估计USD'],[[stage,complete,correct,f'{distribution([x["output_tokens"] for x in cs])["mean"]:.2f}',distribution([x['output_tokens'] for x in cs])['median'],sum(x['total_tokens'] for x in cs),cost] for stage,cs,complete,correct,cost in [('E4096',ec,10,9,'0.072773478'),('8192',hc,22,19,'0.106279878')]])
 doc('07_RESAMPLING_CONTROL.md',f'''# 普通重采样辅助对照

两组都是同一33个首轮未完成ID；各生成一次，prompt/model/temperature完全一致。预算唯一变化4096或8192。发送顺序预声明随机交错，全部由一个64线程池限制，E不参与自适应调度或最终选答。

{ds}

Fixed配对：两者正确8、仅E正确1、仅8192正确11、两者未确认正确13。净增10/33=30.30pp，双侧精确McNemar p=0.00634765625；配对bootstrap95%CI[12.12,48.48]pp。相较E，8192多用55,844输出tokens（输入相同），估计多USD0.0335064。

仅E正确：{', '.join(eonly)}。

仅8192正确：{', '.join(honly)}。

逐题完成/正确/token在truncation_recovery.csv；E原始响应在same_budget_retry.jsonl。审计后E为10个正确，8192为21个正确（另1完整错答）；主比较仍保留冻结9对19。E/8192中的prealgebra_551同为90而被参考换行单位卡住，均已审查。

同预算重采样本身恢复9个自动确认正确题，因此不能将全部预算流程收益归因于增加上限。8192在相同题上比E多10个自动正确，提供增加预算有额外价值的证据；但两个独立采样的随机性、33题小样本、服务后端未固定及单次重复，不足以把贡献精确拆成相互独立的“纯采样”与“纯长推理”因果效应。温度0在该模型thinking模式下也不保证确定性。
''')
 failure_table=table(['task_id','主分类','证据'],[[r['task_id'],r['category_after_manual_review'],r['manual_review']['review_evidence']] for r in fail])
 doc('08_REMAINING_FAILURES.md',f'''# 剩余失败：逐题审计

D主结果476true，24个非true：3截断false、18unknown、3完整false。不能将这24题都称为推理错误。检查完整输出与原参考解，并用exact arithmetic/SymPy核验后分为：**17评分覆盖缺口、3标签提取漏解、3仍截断、1完整且明确错误**。相应jsonl保留审计前/后类别、原模型完整答案、参考解、评分证据、最终预算及原响应hash。

复核由Codex助手阅读证据并执行代码完成，无独立人类双盲裁决。所有评分分歧及D非true均审查；其余自动true未逐一独立重新证明。敏感性结果基线467、增强496（+29）；不是新的冻结评分器成绩，也没有反哺请求、评分器或标签。

## 完整数学错误

`math_test_number_theory_491`：应求四个最小连续正整数且积末位4、积>1000之和。模型8192先正确找到n=6与3024，随后在“The four smallest such starting integers”改成列举四组起点6,11,16,21，最终54。正确四整数6,7,8,9，和30。错误定位是目标对象追踪/聚合对象混淆，并非乘法本身；原始解与最小合法起点枚举保存在remaining_true_math_errors.jsonl与code/manual_audit.py。

该题4096截断，8192完整错误后不再升16384。没有发现“一批”完整数学错误，只有1个清楚案例。它可成为下一阶段输出目标校验的候选，但样本不足以支持大规模复杂Skill或多路径机制结论。

## 逐题证据

{failure_table}

三截断题最终正文均为空，隐藏推理中出现正确候选也不视为最终交付。geometry_56与intermediate_algebra_494显示反复核对造成未完成；algebra_1161额外存在“逆函数”与“逆关系”的题意歧义：图不满足单射，参考6对应逆关系值域最大值。这一歧义是次级标记，不与主类重复加总。

3个多解标签问题的原参考解包含全部解；冻结last-box提取只留下最后一个。报告数学核验时用完整问题和参考解，不把错误的单元素提取当唯一真值；但为了保留预先冻结主比较，本轮不改标签、不回写主评分结果。后续必须解决这个评测协议缺陷。
''')
 costtable=table(['方法','总tokens','tokens/自动正确题','估计USD'],[[x['method'],x['total_tokens'],f"{x['tokens_per_correct']:.2f}",f"{x['cost_usd_estimate']:.9f}"] for x in s['four_way']])
 doc('09_ACCURACY_AND_COST.md',f'''# 正确率、调用、token与费用

{costtable}

A/B共享500次，C/D共享544次；实际总调用=500+33+11+33(E)=577，HTTP577，无429/超时/基础设施重试。输入80,550、输出898,016、合计978,566。reasoning_tokens是输出tokens的子项，不二次相加；provider未提供的精确revision等字段保留unavailable。

{stages}

自适应相对基线新增44次，输入10,760、输出281,152、总291,912、估计USD0.169853616；以主结果+27计，每新增正确题10,811.56 tokens、USD0.006290875。按审计敏感性+29计则10,065.93 tokens、USD0.005856...，只能作为单列事后口径。

E研究对照另外33次，输入7,873、输出119,854、总127,727，估计USD0.072773478。相对500次基线，本轮包含对照的研究新增77次，输入18,633、输出401,006、总419,639，估计USD0.242627094。全实验估计USD0.550120644。请勿把四方法合计当实际账单。

定价依据运行日[DeepSeek官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)：此次请求都在周六非高峰；每百万输入缓存命中USD0.003、未命中USD0.15、输出USD0.6。逐响应prompt_cache_hit/miss计费明细在token_costs.csv。抓取时间、页面SHA和费率在evidence/pricing.json。上述都是公开费率估算，没有读取账户最终账单；不同账户、抵扣及供应商变更可能影响实付。

预算统计：预留上限2M；实际978,566。多档累积成本含原始4096，不仅是新增调用。评分修复额外API tokens=0，本地两评分器合并wall time{s['scoring_local_wall_seconds']:.3f}s，Fixed worker耗时合计{s['fixed_sum_worker_seconds']:.3f}s；没有将本地CPU时间假装为免费。

统计主检验B对D：差+5.4pp，配对95%bootstrapCI[3.4,7.4]pp，精确McNemar p=1.49e-8；未知不算确认正确但不标数学错。辅助E对8192差+30.30pp（n33），CI[12.12,48.48]pp，p=.0063477。20,000次重采样固定seed20261012，代码和测试均提供。分组只是描述性，未筛选显著类别，没有跨多次实验挑最优随机种子。

{groups}

完整token增量分布见summary.json；单题累积见four_way_task_comparison.csv。未做统计功效外推或声称推理能力全面提高。模型别名后端、独立采样、参考标签完整性、评分unknown以及近重复筛查范围构成实际限制。
''')
 doc('10_NEXT_RESEARCH_DECISION.md','''# 研究决策：PARTIAL

自适应预算的收益在新独立500题上成立：Frozen Fixed口径+27题，配对统计支持正差；同预算重采样可救9题，8192能救19题，为更大上限提供额外证据。评分修复只有2个新正改判，更多原正确被拒判，净-7，因此不符合“两项均可重复受益”的GO条件。

优先处理一般性的评测可靠性：完整多解参考答案构建、单位和文本类型、±集合/区间、矩阵、线段标签、定义域。保留严格反例和unknown；不要用宽松近似强行判对。只能在独立开发池上开发新版评分器，再预注册新held-out数据，不许在本轮500题上调试后将同批结果当独立泛化证据。

第二优先仍是答案完成。三题16384依旧没有可见最终正文，其中两个推理已有正确候选但重复核查；一个还涉及题目逆函数歧义。后续可单独研究公开可观察的最终答案输出策略/预算管理，但本轮没有实现新的隐藏推理控制，也不据此宣称复杂Memory或Skill必要。

真正完整错答目前只有number_theory_491一个，机制是目标对象被替换。可将“问题要求的对象与最终聚合对象一致性”作为后续候选假设，需在新的更难独立数据上寻找多例、预注册比较后再判断是否值得多路径搜索或验证驱动推理。当前证据不足以支持“一批难题需要新推理算法”。

保持本轮正式成绩、unknown、全套失败证据和3个标签完整性缺陷公开；事后496/500不能冒称为预先冻结Fixed成绩，更不能与历史分数无条件直接比较。完成当前报告、归档、测试、GitHub提交及远端核验后停止，不自动启动其他数据集或额外API调用。
''')
 doc('README.md','''# math500_scoring_and_budget_v2

本轮依照USER_GUIDE.txt执行；独立新500题、原生FlowEvo无Skill/无gold的CoT路径；4096→8192→16384完成状态控制；同题同预算重采样辅助组。

**主结果A456/B449/C485/D476；决策PARTIAL。**先读[00_EXECUTIVE_SUMMARY.md](00_EXECUTIVE_SUMMARY.md)。正式自动分数与事后数学审计分开；审计敏感性为首轮467、自适应496，非冻结评分器成绩。

## 报告

- 01_DATASET_AND_CONFIG_AUDIT.md：独立抽样、真实配置与隔离；01_EVALUATOR_AUDIT.md：旧评分回归。
- 02_SCORING_FIX_VALIDATION.md、05_SCORING_CONTRIBUTION.md：评分泛化失败与逐案证据。
- 03_COMPLETION_CONTROLLER.md、06_ADAPTIVE_BUDGET_CONTRIBUTION.md：完成规则、预算贡献。
- 04_FOUR_WAY_RESULTS.md、09_ACCURACY_AND_COST.md：四组分数、统计与成本。
- 07_RESAMPLING_CONTROL.md：E4096与8192的同题配对。
- 08_REMAINING_FAILURES.md、10_NEXT_RESEARCH_DECISION.md：24候选审查与下一步判断。

## 证据与重现

api_calls.jsonl及raw/提供577条完整请求、响应、原始HTTP正文和attempt账本；first_pass/adaptive/same_budget分别指向共享输出。四组逐题CSV、两评分jsonl、分歧CSV、恢复CSV、费用CSV、summary均公开。审计附加manual_audit_results.jsonl、remaining_true_math_errors.jsonl、label_integrity_audit.json；evidence下保留审计前原数据快照。

在仓库根目录、已安装本项目依赖的现有Python3.10环境离线执行：

```bash
Flowevo-Bot/.venv/bin/python -m pytest experiments/math500_scoring_and_budget_v2/tests experiments/math_truncation_and_scoring_audit/tests/test_scoring.py -q
Flowevo-Bot/.venv/bin/python experiments/math500_scoring_and_budget_v2/code/audit_artifacts.py
```

上传包不包含虚拟环境或凭据；新环境按项目requirements安装，精确实测包版本见evidence/runtime_packages.json。code/evaluators.py复用仓库内旧评估器和FlowEvo-Recovery/math_scoring_v2.py；源码hash记录在pre_api_freeze.json，归档另外打包这些依赖源码。

从封存输出重新生成统计会重写派生文件，因此应在**新的工作副本**运行：先code/analyze.py（全部生成seal已存在，离线无API），再code/manual_audit.py，再code/write_reports.py。它们不修改原模型响应/评分器。运行耗时属于该次重放，可能与原记录不同。

run_experiment.py是付费生成入口，本轮已完成；不要为查看报告重跑它。prepare_dataset/export_native_prompts/preflight/freeze是调用前的一次性准备步骤，也不要在已封存目录重复执行。重新研究需新目录/新预注册，而不是覆盖本轮证据。

最终测试67项通过（evidence/tests_final.txt）；预调用59项通过。最终新增pending恢复测试首次因临时fixture未传配置而失败，已修正测试fixture后全通过；在线冻结源码未修改，首轮测试日志也保留。

run_manifest.json为全部本轮文件及复用源码的SHA256索引；ZIP位于仓库根目录math500_scoring_and_budget_v2.zip，对应校验文件math500_scoring_and_budget_v2.zip.sha256。发布前检查秘密、历史hash、stage实际文件与上传manifest；commit的真实SHA以GitHub远端及最终交付消息为准，避免在提交内制造自引用hash。
''')
 print('Rendered 11 requested reports plus README; primary scores unchanged.')
if __name__=='__main__':main()
