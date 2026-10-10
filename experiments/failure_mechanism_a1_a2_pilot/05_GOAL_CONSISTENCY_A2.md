# A2：公开目标一致性

GoalSpec包含target_object、target_operation、target_variables、domain_constraints、quantity_constraints、answer_cardinality、unit_requirements、required_output_type，另保留请求句及解析置信度。实现基于题面规则，不调用模型抽取，不读标准答案。具体输出见goal_specs.jsonl。

Checker支持明确连续整数对象被起点替换、显式集合基数不符、明确请求单位/数制或实数域违规。它是保守的有限规则覆盖；“无高可信冲突”不等于全面数学验证，也没有实现通用语义级变量/所有存在性问题判定。解析不确定时不修复。

开发历史发现两次有效单位后缀误触发：题面给出单位不代表最终目标要求该维度；面积题的线性长度单位尤其易误判。已在试验前把单位触发限定为目标句中显式要求，并加入正/负回归。该修正没有使用独立40题结果。

新40题中目标漂移确认0、触发0、恢复0、误改0、额外调用0、tokens0。B2+A2复核后40/40，全部复用B2。Generic为37/40并损失3道已正确题，这只能说明本轮无条件重新检查存在风险，不能证明从未触发的结构化A2修复优于简单提醒。

历史明确F3仅number_theory_491一题；F4精确付款约束例并未被当前Checker捕捉。没有多道独立新题的目标修复证据，结论PARTIAL，当前部署NO-GO。A1/A2都未单独产生正向恢复，因此没有运行组合。
