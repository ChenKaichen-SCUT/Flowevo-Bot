# 历史失败机制图谱

分析1195份不同响应，覆盖1031道题：第一批500个基础响应、第一批37个预算恢复响应、第二批577个不同预算/同预算对照响应、较早恢复试验81个数学响应（31道训练题）。本阶段模型生成调用为0；保留成功对照，按实际响应ID去重。较早恢复试验采用不同提示，只用于现象发现，不用作本轮无技能预算基线。

| 机制 | 响应数 | 不同题数 / 1,031 | 比例 | 后续/其他历史分支至少一次正确 | 未观察到确认正确 |
| --- | --- | --- | --- | --- | --- |
| F1 Answer Found but Not Finalized | 13 | 12 | 1.16% | 7 | 5 |
| F2 Repeated Reasoning / Verification Loop | 7 | 7 | 0.68% | 2 | 5 |
| F3 Goal Drift | 1 | 1 | 0.10% | 0 | 1 |
| F4 Constraint Drift | 2 | 1 | 0.10% | 0 | 1 |
| F5 Ambiguous Problem Semantics | 7 | 2 | 0.19% | 0 | 2 |
| F6 True Mathematical Error | 0 | 0 | 0.00% | 0 | 0 |
| F7 Evaluator / Interface Failure | 31 | 30 | 2.91% | 29 | 1 |
| F8 Unknown | 123 | 68 | 6.60% | 56 | 12 |


以上是**可确认的下界**，不是穷尽人工标注的发生率。主/辅标签及依据均保存在failure_cases.jsonl；重复标签已去重。一题可跨多个响应和机制。最后两列是跨历史分支是否出现过确认正确，不等于固定算法的最终成功率。所有分母均为1031，未仅以失败题为分母。

695/1195份响应保留reasoning_content，涉及558道题；第一批500份基础响应没有保存完整推理文本，因此不能判断其内部候选或循环。411份响应、342道题检出显式候选。F1中只有对已暴露候选进行离线精确类型/参考匹配或复用历史数学证明后才确认；这种正确性证明不能给在线控制器使用。12题中7题在其他历史分支成功、5题未交付确认正确的最终答案。

F2的7题来自5个已有深入审查案例和2个新增文本审查（counting_probability_42、intermediate_algebra_364）。纯“check/wait”或重复段落代理仅标记5题，不能直接当作无效循环：geometry_214虽然反复验证仍正常答对，是成功对照。确认F2的7题中2题随后成功。几何/代数较集中，但样本太少、缺失推理太多，不能推广因果。

F3：number_theory_491把四个连续整数6,7,8,9的和30替换成起点6,11,16,21的和54；可从最终描述观察对象改变。F4：prealgebra_76额外要求精确付款，回答10枚硬币；普通可支付解释只需8枚（总额32.80≥32.75）。若外部另加精确付款要求，10是正确的；因此该约束问题具有语义敏感性，不把它当算术错误。

F5：algebra_1161的非单射逆函数、intermediate_algebra_253的局部相切/唯一接触语义，复用先前精确审查。F7涉及30题31响应，包括旧评分修复和V3指数上限。F8涉及68题，保留不确定性；确认F6为0不表示F8均正确。

候选形成、重复输出和明确对象变化可以在线观察；候选是否真的正确、是否存在数学歧义还需要独立证明。当前证据支持研究A1现象，但尚不能证明控制器有效；A2仅1道明确目标漂移，缺少跨题支撑。

输出：failure_taxonomy.csv、failure_cases.jsonl、historical_records.jsonl、historical_candidate_events.jsonl、repeated_reasoning_cases.jsonl、goal_drift_cases.jsonl、online_observable_features.csv。evidence/stage1_sealed.json保留调用前证据哈希；最终报告汇总由atlas_summary_verified.json复核，个别F7学科/均值聚合修正记录在atlas_reporting_reconciliation.json，未改变封存案例。
