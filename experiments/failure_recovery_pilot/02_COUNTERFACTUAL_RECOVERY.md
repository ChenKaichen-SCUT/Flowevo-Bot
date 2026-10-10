# 同一失败状态的反事实恢复

四动作均从同一封存首轮开始，每次最多一个新模型请求：Continue、Independent Retry、Verify-and-Repair、Replan。Retry不带前一输出；其他动作使用同一公开状态，并统一限制6000字符上下文。Repair仅附公开检查证据。数学4096/代码2048最大输出token、temperature0，各动作一致；实际输出长短单独计费。

数学使用6个历史截断训练状态和1个语义约束错误；代码新增32个首轮后按预定hash选8个训练失败。共计划60分支、实际49。初始135,000训练软限额导致代码覆盖不足，在确认开始前只为完成原定分支扩到155,000；总240调用/300,000 tokens硬上限不变，没有按成功表现换题。仍缺11分支，4个不完整来源全部排除Memory。

| 题号 | 四分支完整 | 类别 | 成功动作 | 额外tokens |
| --- | --- | --- | --- | --- |
| math_train_counting_probability_424 | True | none_recovered_under_budget | 无 | 17526 |
| math_train_geometry_281 | True | retry_suffices_observed | continue,repair,retry,replan | 11666 |
| math_train_intermediate_algebra_337 | True | targeted_only_observed | continue,replan | 16041 |
| math_train_number_theory_791 | True | none_recovered_under_budget | 无 | 17110 |
| math_train_prealgebra_830 | True | retry_suffices_observed | continue,retry | 15736 |
| math_train_precalculus_444 | True | none_recovered_under_budget | 无 | 17386 |
| math_train_prealgebra_76 | True | none_recovered_under_budget | 无 | 15824 |
| mbpp_train_822 | True | targeted_only_observed | replan | 4712 |
| mbpp_train_865 | True | none_recovered_under_budget | 无 | 3078 |
| mbpp_train_650 | True | targeted_only_observed | repair | 3047 |
| mbpp_train_712 | True | none_recovered_under_budget | 无 | 9902 |
| mbpp_train_786 | False | retry_suffices_observed | retry | 561 |
| mbpp_train_691 | False | retry_suffices_observed | retry,repair | 1744 |
| mbpp_train_780 | False | incomplete_no_claim | 无 | 816 |
| mbpp_train_802 | False | incomplete_no_claim | 无 | 2066 |

完整11题中：2题retry已足够、3题targeted-only、6题全部已测动作失败。数学2/1/4；代码0/2/2。全15个来源里，另2个不完整来源已观察到retry成功，不能把“观察过成功”混成“四动作齐全”。

三个targeted-only来源：math_train_intermediate_algebra_337的Continue/Replan在这一次成功，Retry截断；原正文为空，不能证明方法稳定优势或前缀迁移。代码822和650是首代码块提取问题，未调用恢复前其完整函数已能通过隐藏测试；提取修正后Retry同样成功。这两个不是推理动作不可替代的证据。

所有未恢复案例仅表示本预算、本动作样本下未恢复；不表示模型能力上限。训练筛选确实依据离线错误标签，但只用于训练集建库，未进入确认题在线控制器。经验只采纳四动作齐全且离线正确性可判断的11个训练来源，负结果也保留。
