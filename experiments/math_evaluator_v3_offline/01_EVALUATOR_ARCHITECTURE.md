# 实现与依赖审查

代码位于`FlowEvo/src/math_evaluation/`。六个职责单独实现：`spec.py`从公开题目推断AnswerSpec；`reference.py`从完整canonical solution构建参考；`extraction.py`只提取可见最终提交；`normalization.py`构造带类型对象；`equivalence.py`给出确定性等价证据；`engine.py`统一状态、超时、批处理和错误追踪。`certificates.py`提供两个可泛化的公开题目证明模板（函数奇偶对称点、矩形面积变化方向），不含任何task ID。

结构字段包括目标变量、实数/整数/复数域、是否要求全部解、无序性、单位、是否允许换单位、小数位数、百分数语义、选项和不确定性。自然语言识别仍是保守的规则层，不能把它宣传成通用题意理解。识别不可靠时输出Unknown。

解析复用Math-Verify依赖的ANTLR语法转换器，最终判定采用SymPy精确运算和自有类型/域约束。独立调用Math-Verify只对已解析的纯数值对象产生**非决定性诊断**；没有把它另列为独立基线，也不对原始答案调用其默认Expr解析或字符串fallback。[Math-Verify官方说明](https://github.com/huggingface/Math-Verify)、[LaTeX转换器](https://github.com/huggingface/latex2sympy2_extended)。

依赖固定：math-verify0.8.0 (Apache-2.0)、latex2sympy2_extended1.10.2 (MIT)、SymPy1.14.0 (BSD)、ANTLR runtime4.13.2 (BSD-3-Clause)、mpmath1.3.0 (BSD)。使用现有环境实际版本；包元数据、许可证全文/上游来源归档在`evidence/dependency_audit.json`及license文件。ANTLR安装元数据未带许可证，额外保存[4.13.2上游许可证](https://github.com/antlr/antlr4/blob/4.13.2/LICENSE.txt)。

未直接采用Math-Verify默认的单位删除、近似容差和字符串回退。SymPy文档提示`parse_expr`使用eval，因此V3的原始字符串不走该接口；ANTLR转换器的`variable_values`保持None，并检查整条token流消费完毕。[SymPy解析文档](https://docs.sympy.org/latest/modules/parsing.html)。私有ANTLR转换器接口的风险通过精确版本检查和回归测试控制。

数值使用精确有理数；符号比较通过恒等变换，不以有限随机代入相同作为证明。捕获分母非零、偶次根非负、对数正值等约束，再作符号替换。无法证明域等价时弃权。

资源限制：每条4秒、答案4096字符、原文100000字符、表达式600节点、嵌套40层、指数绝对值1000；独立批处理进程地址空间上限1536MiB；最多12进程。批处理worker禁止网络。直接单条evaluate采用字符/复杂度/信号超时保护，进程内存限额仅由batch worker施加；不应将单条接口当作通用不可信代码沙箱。

冻结版本3.0.0，config hash `6ac932c2464edb410709e5e30e373f354d3c38b8b15321c31a0914701211fab6`。正式结果发生在三次开发试跑和历史回归之后；开发结果保留在evidence，明确属于同数据回顾性修复。
