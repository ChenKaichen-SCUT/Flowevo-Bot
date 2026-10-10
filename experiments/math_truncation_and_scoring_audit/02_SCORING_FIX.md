# 评分器修改与 9 道案例

新版本 `FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py` 继承现有 v2 的平衡括号和数学解析基础，历史版本保留；实验入口 rescore.py 使用新版本。修复前后差异见 evidence/scorer_before_after.diff。评分器中无 task ID 或特定标准答案分支。

最终答案按出现位置选取最后一个明确 marker/boxed，支持嵌套括号。单位规范化依赖公开题目，保留符号、维数、方向和变量顺序；集合与区间、矩阵分别作结构比较；数学解析禁用字符串 fallback。可能涉及有理式约分导致定义域丢失的情况保守 unknown。不同合法图像点由受限的奇偶函数条件证明，并保存 proof。无法解析、缺少必要条件或有歧义时保留 unknown。

对 500 题封存结果重新评分：473 true、27 truncated false、0 unknown。新增纠正仅为原 9 道；旧 464 true 全部保留，没有 true→false/unknown。数学判断证据包含规范化前后、解析对象、差值或公开条件证明，见 evidence/rescored_500_detailed.json。每道的完整原输出/参考推导/usage 在 nine_scoring_cases.jsonl。新增 API 调用 0。

本评分器仍是保守的答案评估器，并非通用数学证明器。与标准答案等价不意味着已机械验证整段解题推导；未覆盖的自由形式答案应复核，不应随意宽松接收。9 个 ID 仅用于以下报告定位，未进入评分算法。

### math_test_algebra_673

旧提取：`2000 calories`；参考：`2000`；新评分：True（symbolic）。

40 / 0.02 = 2000；末尾 calories 是题目单位。

### math_test_algebra_884

旧提取：`3600 square units less`；参考：`3600`；新评分：True（symbolic）。

(3491−60)(3491+60)−3491²=−3600；题目问变化量大小，答案 3600 且明确 less。通用矩形变换验证器另验方向，more 不会放过。

### math_test_counting_probability_411

旧提取：`\frac{12}{5525}`；参考：`\frac{12}{5,\!525}`；新评分：True（symbolic）。

4×12 / C(52,3) = 48/22100 = 12/5525；参考分母中的逗号及 LaTeX spacing 为千位分组。

### math_test_geometry_165

旧提取：`40°`；参考：`40^\circ`；新评分：True（symbolic）。

D 是 BC 中点且与 A/B/C 等距，BC 为直径，∠A=90°；∠C=180−90−50=40°。

### math_test_geometry_48

旧提取：`75%`；参考：`75`；新评分：True（symbolic）。

总面积4，两个阴影三角形面积1和2，百分比为75。75% 与问百分数时的数值75一致，0.75不会直接判成75。

### math_test_intermediate_algebra_796

旧提取：`\((3,-5)\)`；参考：`(0,0)`；新评分：True（public_question_witness）。

由奇函数 f(−x)=−f(x)，f(−3)=5 ⇒ f(3)=−5；(3,−5) 为另一必经点。它不等于参考 (0,0)，但可由公开条件直接证明。且一般奇函数定义域未必含0，不能无条件从奇性断言原点属于图像。

### math_test_prealgebra_334

旧提取：`12 grams`；参考：`12 \text{ gm}`；新评分：True（symbolic）。

(5×13+7)/6=12 grams；gm 与 grams 为同一单位。

### math_test_prealgebra_435

旧提取：`2.50 dollars`；参考：`\$2.50`；新评分：True（symbolic）。

10×(1/4)=2.50 dollars；金额单位规范化。

### math_test_prealgebra_498

旧提取：`36°`；参考：`36^\circ`；新评分：True（symbolic）。

正五边形内角108°，缺口360−3×108=36°；度数表达规范化。

测试包括未见数值、错误正负号、错方向、单位维数、坐标顺序、集合漏项、区间开闭、矩阵转置、符号恒等式、根号分支、变量分母定义域、末尾更正与未闭合 boxed；另外核对全部 500 题回归和 gold-blind 升级规则。生成前 38 项通过，见 evidence/tests_pre_generation.txt。
