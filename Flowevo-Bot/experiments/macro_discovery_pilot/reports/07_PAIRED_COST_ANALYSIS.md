# 配对与完整成本分析

| family | method | n | benefit | harm | both_correct | both_not_confirmed_correct | mean_saved_input | mean_saved_output | mean_saved_total | bootstrap95_mean_saved_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | B_Compact | 14 | 0 | 0 | 14 | 0 | -73.71428571428571 | -244.85714285714286 | -318.57142857142856 | [-654.6428571428571, -101.64285714285714] |
| ALL | C_Executable | 14 | 0 | 0 | 14 | 0 | -24.428571428571427 | -20.428571428571427 | -44.857142857142854 | [-408.42857142857144, 297.07142857142856] |
| root_invariants | B_Compact | 10 | 0 | 0 | 10 | 0 | -80 | -313.7 | -393.7 | [-847.9, -119.6] |
| root_invariants | C_Executable | 10 | 0 | 0 | 10 | 0 | -70.2 | -287.6 | -357.8 | [-705.4, -70.6] |
| polynomial_remainder | B_Compact | 4 | 0 | 0 | 4 | 0 | -58 | -72.75 | -130.75 | [-353.0, 71.75] |
| polynomial_remainder | C_Executable | 4 | 0 | 0 | 4 | 0 | 90 | 647.5 | 737.5 | [510.25, 1103.75] |

正数为相对A节省。bootstrap固定seed、10000次任务配对重采样，n很小时区间极不稳定，不是准确率非劣证明。全部任务（含截断）保留，unknown单列；benefit/harm按是否确认正确计算，不将unknown解释为确定错误。

| method | family | coverage | eligible_mean_saved | unconditional_mean_saved_assuming_same_effect |
| --- | --- | --- | --- | --- |
| B_Compact | root_invariants | 0.00505902192242833 | -393.7 | -1.9917369308600337 |
| B_Compact | polynomial_remainder | 0.0042158516020236085 | -130.75 | -0.5512225969645869 |
| C_Executable | root_invariants | 0.00505902192242833 | -357.8 | -1.8101180438448565 |
| C_Executable | polynomial_remainder | 0.0042158516020236085 | 737.5 | 3.109190556492411 |

完整成本账：{
  "new_macro_generation_api_tokens": 0,
  "new_experiment_api_tokens": 34896,
  "new_experiment_api_calls": 38,
  "source_trace_acquisition_tokens": 795435,
  "incremental_source_reuse_tokens": 0,
  "full_source_plus_current_research_tokens": 830331,
  "previous_v1_all_bank_build_tokens": 1069731,
  "previous_v2_research_tokens": 102316,
  "cumulative_research_including_failed_prior_versions_tokens": 1206943,
  "agent_chat_and_engineering_cost": "not available in DeepSeek ledger; excluded, not assumed free",
  "local_mining_seconds": 2.449935546028428,
  "local_selection_seconds": 1.9526494350284338,
  "cpu_price": "not priced; execution and verification seconds reported per task",
  "B_Compact_coverage_weighted_tokens_saved_per_task_scenario": -2.5429595278246206,
  "B_Compact_source_plus_pilot_break_even_total_tasks_scenario": null,
  "B_Compact_pilot_only_break_even_total_tasks_scenario": null,
  "C_Executable_coverage_weighted_tokens_saved_per_task_scenario": 1.2990725126475546,
  "C_Executable_source_plus_pilot_break_even_total_tasks_scenario": 639173,
  "C_Executable_pilot_only_break_even_total_tasks_scenario": 26863
}

余式C消耗确定性CPU并避免LLM调用；这是工具替代产生的token节省，不能归因于短提示压缩。根C仍调用LLM，因此其input/output差异检验中间量是否真正减少模型推理。B只增加紧凑思路，以真实输入增量计费；是否有节省由配对表决定。宏对题目是否有实质帮助最终仍要看harm与输出变化。

source+pilot和pilot-only均给出覆盖加权摊销；覆盖只取未使用原dev分母1186，效果由已选条件样本估计，部分样本来自保留unused train，故只作为强假设情景。MATH500上没有新测量，不报告总体提升。该轮全量A/B/C支出计入研究成本，不能只把生产C的0token当作免费建库。

<!-- POST_EXPERIMENT_INTERPRETATION -->
## 事后机制核查（不改运行方案）

A 14/14、9936 tokens；B 14/14、14396（+44.89%）；C 14/14、10564（+6.32%）。所有提交均未截断，因而本轮不存在截断救回解释；benefit=harm=0，只能说明这14题没有观察到正确率差异。14/14的Wilson 95%正确率区间约[78.5%,100%]，更不能证明准确率非劣。每题每组仅一次模型采样，温度0不保证固定后端或确定输出。

根宏：B/C均10/10题参与，分别只有1/10题减少token、9/10增加。B多3937，C多3578；C输入多702、输出多2876，即增加并非仅因提示长度。C确实执行并提供全部e_k和p_k，不能据此认定这些中间量替代了主要推理；模型仍要选择目标表达式，也可能重新推导。该版本计算不按目标裁剪，部分幂和无用，是后续需改的明确模块。

余式：B仅1/4节省、3/4增加，共增加523；C 4/4完整证书通过、4次调用避免，共节省2950，其中输入360、输出2590。4题本地总耗时约0.08971秒（执行0.00051、验证0.00674，其他为解析）；这些是本机单次观测而非稳定吞吐基准。局部代数计算有实测成本，不计入LLM token。

最强个例 intermediate_algebra_429：A 1275 tokens，先在x=2,-2,-1取值、求解余式的3个系数；C用QQ精确除法及独立递推得到-8x²+13x+20，再验证完整恒等式，0调用，确实替代整段求解。该题非根库来源。

最差个例 intermediate_algebra_1150：A 892 tokens，通过P'(1)/P(1)=12得到倒数和；B 3168（增加2276），改为t=1-p的多项式展开再用Vieta，答案仍12。C给原多项式对称量后2507（增加1615），也没有省下主要目标变换。这支持“通用Vieta提示可能诱导更长路径”的个例解释，不能从单次采样推出必然因果。

完整成本口径：新增API34896；沿用语料的增量采集0；若从头采集原700题再完成本轮，总830331 tokens。再包含旧V1失败建库与V2研发的历史累计1206943，均单列，未冒称本轮支出。助手会话/人工工程成本不在DeepSeek账本中可测，未假定其免费。

如果只保留余式工具、禁用根宏，事后情景为{"method": "C_Executable polynomial_remainder only; root macro disabled in hypothetical scenario", "coverage_numerator": 5, "coverage_denominator": 1186, "eligible_mean_saved_tokens": 737.5, "coverage_weighted_savings_scenario": 3.109190556492411, "pilot_only_break_even": 11224, "source_plus_pilot_break_even": 267057, "status": "post-hoc scenario only, not a new evaluated routing policy"}。这不是新跑出的策略，只演示为什么高条件节省与低覆盖不能混为一谈。实际冻结C混合策略的原dev覆盖加权情景每总体任务仅省约1.299 tokens，源采集+本轮约需639173题摊销；条件样本本身并未节省，故这个情景不能用作扩到500的依据。
