# 02 — 真实轨迹中的操作和组合证据

提取器先扫描每条轨迹的数学片段，不再要求完整题意先解析。字段包含operation_type、input/output_type、input/output_structure、preconditions、transformation、source_task_id、source_step_ids、verification_rule、confidence、provenance。603条均保留自然语言未理解标记。6029条记录中703条数学关系独立验证通过，5326条保留unknown；没有把unknown当作数学错误。

| kind | count |
|---|---|
| uninterpreted_mathematical_relation | 4722 |
| uninterpreted_natural_language | 603 |
| exact_integer_evaluation | 592 |
| integer_congruence | 111 |
| resource_limited_relation | 1 |


每个数值同余使用独立二进制模幂检查，精确等式使用有界整数计算；只验证显式局部关系，不声称解释整个自然语言推理链。未知变量、多项式、分式、集合推理均不勉强解析。

方向选择依据：训练中反复出现先将操作数/幂归约，再合并和/积，再取规范余数。来源210是三项幂和；537是六个连续整数之和；809是三个整数乘积；prealgebra992是乘法与幂的混合表达式。它们有实际中间表达式，不只是最终答案。

归一化保持整数常量的精确值、加法/乘法扁平化与交换排序。变量类型不在本轮范围内，故没有把变量重命名称为已学习能力。受限anti-unification保存不同数值/结构的typed holes并复用重复分歧；这里0/6个来源对保留非空共同根结构。根层IntegerExpressionHole属于弱信息，不能冒充共享数学解法。真正支持组合的是不同来源的已验证中间状态被同一执行序列复现。

这也暴露限制：程序组合在人工提供的通用树遍历原语中搜索；没有从异质自然语言自动推导新的高层数学算法。48片段消融有701操作/290来源，96片段有703/291；提升不能全部归因于去除入口过滤，也不能直接和旧RMMD不同算子集合的267来源作因果比较。

数论以外候选未新增实现。余式仅2源且结构差异大；倒数和/e2等只有1源；一般有理式与有限候选筛选需要额外语义守卫，当前没有足够来源支持新增完整流程。见source_extractions、pattern_clusters和逐条操作JSONL。
