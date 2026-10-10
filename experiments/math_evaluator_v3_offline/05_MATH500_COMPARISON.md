# 两套500输出的配对比较

| 输出 | Legacy | Fixed | V3 自动确认正确 | V3 Unknown | V3 未完成 | V3 Incorrect |
| --- | --- | --- | --- | --- | --- | --- |
| 固定4096 | 456/500 (91.2%) | 449/500 (89.8%) | 466/500 (93.2%) | 1 | 33 | 0 |
| 自适应最终 | 485/500 (97.0%) | 476/500 (95.2%) | 495/500 (99.0%) | 1 | 3 | 1 |


| 分支 | 评分器 | Correct | Incorrect | Unknown | Ref ambiguous | Ref invalid | Incomplete |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | legacy | 456 | 44 | 0 | 0 | 0 | 0 |
| base | fixed | 449 | 35 | 16 | 0 | 0 | 0 |
| base | v3 | 466 | 0 | 1 | 0 | 0 | 33 |
| adaptive | legacy | 485 | 15 | 0 | 0 | 0 | 0 |
| adaptive | fixed | 476 | 6 | 18 | 0 | 0 | 0 |
| adaptive | v3 | 495 | 1 | 1 | 0 | 0 | 3 |


Legacy/Fixed没有独立reference和incomplete结果类别，表中保留其实际历史状态；旧评分器的incorrect包含截断，不能解释成纯数学错误。V3将未完成独立列出。

首轮相对Legacy新增11、退出确认1，净增10；相对Fixed新增18、退出确认1，净增17。自适应相对Legacy新增11、退出确认1，净增10；相对Fixed新增20、退出确认1，净增19。两分支各有9份V3新增正确且两个旧评分器都未确认。唯一退出确认的是precalculus_187，状态为Unknown而非Incorrect。

Fixed Unknown由首轮16降到V3总Unknown1，自适应18降到1；但这不是原Unknown集合的简单包含关系：原34份Fixed Unknown都获数学证明且V3确认，新增2份Unknown来自指数限额。见逐题`evaluator_comparison_500.csv`和三维`scoring_transitions.csv`。

V3全1000份批量离线评分墙钟 8.636 秒，12进程；逐记录耗时累计100.976秒。历史复现（Legacy+Fixed合并调度）墙钟4.433秒。逐分支/评分器的累计、均值、中位数见`evaluation_timing.csv`；累计并行耗时不等于墙钟，冷启动导入及缓存不对称，因此不能由这些数值推出公平吞吐倍数。

本轮新增模型token=0。过去生成token及预算分配保留在旧实验；没有重生成、预算加码、token节省宣称或新显著性泛化检验。
