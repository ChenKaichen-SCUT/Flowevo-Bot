# 数学操作挖掘

603条首次正确解法逐学科处理，共2719条IR记录。每条包含operation_type/input_structure/output_structure/assumptions/required_guards/source_step_ids/verification_status；source_step_ids指向原model_solution中数学片段的零基序号。保留原LaTeX及变量重命名后的SymPy树。

| subject | operations | verified | unknown |
| --- | --- | --- | --- |
| algebra | 488 | 61 | 427 |
| counting_probability | 251 | 138 | 113 |
| geometry | 453 | 38 | 415 |
| intermediate_algebra | 552 | 39 | 513 |
| number_theory | 344 | 111 | 233 |
| prealgebra | 229 | 103 | 126 |
| precalculus | 402 | 21 | 381 |

验证状态：{'unknown': 56, 'unknown_requires_context': 1531, 'unknown_ValueError': 354, 'symbolically_verified_common_domain': 503, 'unknown_Exception': 264, 'verified_operation_with_confirmed_source': 8, 'unknown_AttributeError': 3}。每条最多检查48个显式等式，单次符号工作最多2秒，宏识别最多5秒。无显式可验证等式、自然语言证明、语境约束方程、无法解析的图形/LaTeX保留unknown。正确的最终答案不等于整段推理自动获得证明。

一般操作先解析等式，再验证有理差恒等为0，按展开/因式分解/有理正规化/数值运算等分类；分母非零作为条件保留。受语境约束的x²=4不误当恒等式。单纯数值运算即使频繁也不自动推荐。

两个中层候选组合多个步骤：根的数值多项式→首一化→基本对称量→Newton幂和→伴随矩阵核验；余式的多项式对→商环约化→独立系数递推→P=QD+R及次数核验。宏来源要求真实解法确实讨论相关数学关系且出现公式；可执行部分另独立计算与验证。来源解法中的自然语言步骤不是形式化证明，宏实现是人工编写的确定性算法。pattern_examples.md完整保留8条实际来源以供语义复核。

根候选6条来源涵盖二/三/四/六次、两三次因子合成、e2、e2/e4、根积和用根关系构造P(x)，不是一个仅换系数的模板。余式2条来源分别为四次除非首一线性式，及两因子乘积除二次式，后者需约化x³=1再组合。已见替代方法：直接求根、逐因子根积、长除法、线性余式定理。

失败反例：仅求实/有理/正根的子集，未定系数，多变量，零除式、非多项式、题目要求余式之后再求其他量。一般方程两边相等不表示可安全除以零；本轮不将“平方去根号”升级为可执行宏，故不会未经回代提交额外根。
