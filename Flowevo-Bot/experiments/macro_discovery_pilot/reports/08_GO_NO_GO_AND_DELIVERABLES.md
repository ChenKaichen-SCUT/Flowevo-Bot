# 决策与交付

**继续改进**。余式工具路线与Compact提示路线分别看待：前者用精确恒等式覆盖完整答案，能够省去调用；后者仍由LLM推理，未因名字叫macro就获得同样的节省。最强省token个例math_train_intermediate_algebra_429 / C_Executable，节省1275；最差math_train_intermediate_algebra_1150 / B_Compact，节省-2276（负数为增加）。正确率损伤见逐题配对，不隐去。

工具候选实际独立样本少，广泛覆盖及采集成本摊销尚不支持直接进入500题。下一阶段如获新的研究指示，应优先修改问题级结构解析/任务完成证书及中层变换覆盖，不以增删“简洁”提示或筛掉失败题来美化本轮结果。当前单轮实验已结束，没有自动扩大样本或运行MATH500。

reports/00–08完整研究报告；data/clean_success_traces.jsonl、excluded_traces.jsonl、trace_manifest.json；reasoning_operations.jsonl、pattern_clusters.json、pattern_frequency.csv、pattern_examples.md；macro_candidates.json、macro_screening.csv、macro_skill_bank.json、dev_tasks.json；task_results.jsonl、task_pairwise.csv、group_metrics.csv、cost_summary.json；api_calls/完整安全请求与响应；submissions/评分前提交；tests/本地检验；evidence/预算、版本、冻结、历史文件保护；snapshots/实际运行代码。

独立归档位于 Flowevo-Bot/macro_discovery_pilot.zip。推送前扫描凭据，不包含miyao.txt或密钥、venv、缓存。远端继续使用已确认的单连字符 ChenKaichen-SCUT/Flowevo-Bot。

<!-- POST_EXPERIMENT_INTERPRETATION -->
## 最终判定

选择 **继续改进**，本轮到此停止。具体区分：当前Compact与根中间量提示路线不进入扩大验证，因成本普遍增加且没有正确率收益；保留余式的“严格题意解析＋完整执行证书”作为工具路线，后续只在新的授权阶段改进覆盖及独立问题类型。不会把余式4题的确定性计算成功写成BoT提示压缩成功。

实现边界：typed IR可以表示已解析恒等式，但语境方程和自然语言推理仍unknown；macro bank中的Trigger树是描述性元数据，执行路径使用已冻结的题面识别器及机器guard，尚未做到从任意bank树自动编译完整验证器。当前两个候选实际执行条件已测试；下一阶段若扩展树语义，必须增加未知状态/否定/组合guard的验证，而不能假设通用推理程序已完成。
