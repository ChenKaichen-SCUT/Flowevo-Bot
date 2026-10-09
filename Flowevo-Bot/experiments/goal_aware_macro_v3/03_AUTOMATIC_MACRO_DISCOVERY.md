# 从成功轨迹自动构建受限宏

输入仍是603条干净首次成功训练轨迹，SHA保持不变。自动提取9条可绑定目标且有数学步骤的ReasoningOperation，其余保留逐项失败原因。输入对象、目标类型、模型最终值、来源公式片段与位置、前置条件和验证规则完整保存。最终值来自已审计的模型成功轨迹，不是新测试gold。

自动化边界：数学片段、数值对象与模型最终值自动提取；目标类别由人工文法识别；按目标聚合后，程序枚举器在固定系数特征与四则算术DSL内寻找同时吻合多个来源的AST，再用形式根变量证明泛化。不是从自然语言思维链自动学习所有语义步骤；不能把来源公式片段的复制称为整段COT语义解析成功。

实际构建两条程序：

- 根和：`-(top1/lead)`，来源algebra_1366与1507，分别是展开式和非零右端平方方程。二者都是二次源题，跨次数推广来自符号证明，不来自广泛经验样本。
- 根积：`constant/(lead*parity)`，parity=(-1)^degree，来源intermediate_algebra_955（三次）与1151（两个三次因子的六次乘积）。系数奇偶特征为人工预置先验；表达式组合及路由条目由搜索得到。

枚举统计：[{"goal_kind": "root_product", "enumerated_programs": 2647, "training_fit_programs": 1, "certified_found": true, "seconds": 0.04953600699082017, "max_nodes": 5, "memoization": "AST exact vector cache, no lossy output-equivalence pruning"}, {"goal_kind": "root_sum", "enumerated_programs": 210, "training_fit_programs": 13, "certified_found": true, "seconds": 0.03739238600246608, "max_nodes": 5, "memoization": "AST exact vector cache, no lossy output-equivalence pruning"}]。共2857个程序枚举，14个来源精确拟合候选，其中12个被通用验证排除，2个认证。典型反例：`-top1`在两道首一来源上拟合，但非首一多项式失败；保留反例赋值。除法节点分母也逐节点证明在声明域非零，不能先约分掩盖不合法程序。

每个合格程序在次数2–6，替入L∏(x-r_i)的系数后，对“全部根之和/积”的定义做符号残差=0证明，非随机正确率替代理论验证。源码没有将已知Vieta AST直接写入bank；验证器预置目标定义及数学内核，不能据此宣称无人工先验的新定理发现。

未合格目标：[{"goal_kind": "pairwise_sum", "reason": "at_least_two_distinct_tasks_and_structures_required", "source_ids": ["math_train_intermediate_algebra_1007"], "structural_classes": [[3, "expanded"]]}, {"goal_kind": "polynomial_remainder", "reason": "bounded_scalar_DSL_has_no_admitted_polynomial_program_or_target_prover", "source_ids": ["math_train_intermediate_algebra_738", "math_train_intermediate_algebra_891"], "note": "Do not turn a manually preset remainder operator into an alleged learned program."}, {"goal_kind": "reciprocal_sum", "reason": "at_least_two_distinct_tasks_and_structures_required", "source_ids": ["math_train_algebra_558"], "structural_classes": [[2, "expanded"]]}, {"goal_kind": "symmetric_rational", "reason": "at_least_two_distinct_tasks_and_structures_required", "source_ids": ["math_train_intermediate_algebra_742"], "structural_classes": [[4, "expanded"]]}]。两两积和、倒数和、一般对称有理式各仅1条来源；余式有2条来源，但当前标量DSL没有多项式程序表示。余式只在B人工基线运行，没有把预写rem算子冒充自动宏。

两条均为数学认证研究候选，未进入production。根和有1道工程题及1道独立题重放；根积没有本轮原dev完整命中，独立开发验证不足。C相对B新增完整覆盖=0；这说明有限程序合成可行，不代表自动Skill Learning已获得性能或摊销收益。
