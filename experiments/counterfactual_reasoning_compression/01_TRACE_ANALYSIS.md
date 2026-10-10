# Stage1：零API历史轨迹对齐

605对 task ID、响应哈希与usage核对一致；两次独立生成，低预算文本从未作为高预算的前缀。历史总量分别687195与1068216，所有记录提供完整 reasoning_tokens；final_content_tokens = completion_tokens - reasoning_tokens。计费子项是API整数，不由字符估计。

统一冻结MathEvaluator-V3后的状态：

| 预算 | 正确 | Unknown | 判错 | 未完成 |
|---|---|---|---|---|
| 2048 | 461 | 19 | 8 | 117 |
| 16384 | 572 | 19 | 8 | 6 |

高预算V3判对572题中：低预算461判对、105未完成、4Unknown、2判错。高低预算均V3判错6题、均未完成6题；这些分类不是全部数学错误证明。高预算历史复核597正确、2题意/参考歧义、6未完成的记录单独保留。低预算V3未判对没有被自动人工升级为错误或正确。

事件识别仅查看问题和当前可见文本：显式“answer is/so answer”等语句、候选重述、检查语言、未处理检查、重复段落及修正语言。任意与gold相同的数字不算Candidate Formation；没有出现显式短语也不代表实际没有候选答案。事件偏重英语显式措辞，可能漏检隐式推导。

597条复核正确中310条显式候选；138条候选后还有上述较长后缀。筛查使用字符定位和全文已知reasoning token的比例估计，只决定离线文本位置；不冒充截点精确生成tokens，更不作为实际节省金额。最早候选并不等于安全提交点。

`reasoning_events.jsonl`保留605条的来源哈希、字符位置、原始证据和事件置信度。Verification discussion / possible revision是候选事件标签，未自动宣称有效数学验证或冗余。选中轨迹的数学事件复核见`evidence/manual_trace_reviews.jsonl`：例如页码题的000重复扣除被后续检查纠正，说明关键后缀不能简单删除。

完整输入、reasoning、最终文本、输出和总量的分位数，按两种预算与V3状态分别写在`token_length_distribution.csv`。已完成分布统计使用全部605对数据，而非只选成功样本。
