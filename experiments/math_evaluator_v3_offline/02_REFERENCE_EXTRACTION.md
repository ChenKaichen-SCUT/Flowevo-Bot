# 完整参考答案

V3使用完整原始解答，而非最后一个盒子或原生loader浅层正则产出的metadata.gold_answer。先记录所有平衡盒子候选和上下文，再结合公开题目是否要求全部解、目标变量、候选相邻关系选择。明确标为中间计算的盒子不参加最终答案集合；跨段且归属不明时reference_ambiguous。单值题多个候选需要证明等价；多解题只有终结解列表/目标变量赋值支持时才合并。

| task_id | 冻结旧gold | V3完整参考 |
| --- | --- | --- |
| math_test_intermediate_algebra_409 | -\tfrac34 |  -\tfrac32, -\tfrac34 |
| math_test_intermediate_algebra_516 | 10879 | -10879, 10879 |
| math_test_intermediate_algebra_563 | \frac{2}{5} | 3, \frac{2}{5} |


409需两根-3/2,-3/4；516需b=±10879；563需x=3,2/5。两分支均正确恢复，历史gold文件保持不变。`reference_candidates`、`reference_builder`、`reference_complete`和`reference_normalized`保留全过程。

首批796中，奇函数图像经过(-3,5)，另一必过点(3,-5)由公开条件严格推出；参考另列(0,0)附带定义域假设。通用奇偶性证明模块选择可证明的对称点，记录附加假设问题，未根据模型值挑选gold。

本轮完整性队列含5个第二批题ID：上述3个历史漏解、`algebra_1161`逆函数非单射歧义、`precalculus_415`标准推导三角恒等式排印错误。1161的自动提交状态仍是prediction_incomplete，题意歧义单独记录；415的最终2/3经独立推导正确，自动评分不因参考中间笔误改成错。该队列是审计发现，不伪称V3已自动证明每条参考解答。

参考格式完整不等同于参考数学真值完整。V3并未构建通用自然语言证明核验器；无参考、候选冲突或解析失败均不能自动给模型正确。
