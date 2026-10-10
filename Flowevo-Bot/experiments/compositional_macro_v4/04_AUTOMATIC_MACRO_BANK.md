# 04 — 自动宏库

唯一新入研究库宏：`auto_integer_congruence_c14ff981351b`。

任务：有显式整数表达式的余数或十进制个位问题。适用表达式为整数、加法、乘法、字面正整数幂；不支持含变量、除法、求和省略号、阶乘、递推、约束推断等任务。

来源4题：`math_train_number_theory_210, math_train_number_theory_537, math_train_number_theory_809, math_train_prealgebra_992`。原题、完整模型解答、source_hash、逐步位置保存在source_extractions与macro_candidates。使用每题真实的非最终算式作为额外样本约束，不能仅从最终数字回归公式。

顺序：`reduce_literals → reduce_powers → evaluate → canonical_residue`，4个执行步骤，属于受限多步程序；Guard是完整目标语义、整数表达式类型、正整数指数、合法模数及资源上限。Guard来自人工文法/类型与原语合法性传播，并非自动发现新数论条件。符号义务全部通过；每次执行还要独立验证。独立确认使用次数0，工程使用1，生产admission=False。

候选记录：仅evaluate→canonical_residue虽然拟合最终值，没有所需非最终状态，来源支持0；reduce_literals的3步版本支持537/809；reduce_powers的3步版本支持210/992；两种4步顺序均支持4题，最终按冻结规则选字典序较小者。不是从五种候选中发现全新数学定理。

与人工工具的程序完全相同。5个组合的搜索空间、原语、语义、正确性规则都人工设计；自动所得为组合选择和多来源准入证据。旧V3根和/根积宏保持原文件，未算作本轮新宏。
