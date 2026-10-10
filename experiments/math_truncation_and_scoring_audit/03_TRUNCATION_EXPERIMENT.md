# 27 道截断题的真实预算实验

实验预案 preflight.json 与生成代码哈希在调用前冻结。最大 54 个正常请求；两档总输出上界 663,552，输入以每请求 UTF-8 字节数+512 保守预留 55,024，总预留 718,576 tokens。按[官方峰时价格](https://api-docs.deepseek.com/quick_start/pricing/)输入 miss 0.30 美元/百万、输出 1.20 美元/百万估算最多约0.813美元；这是保守价格估算，非账单。当前官方接口最大输出393,216支持8192/16384；未超出本轮用户授权档位和调用数。

原始4096只读历史，无新 baseline 请求。先对全部27题执行8192，只复制原请求并改变 max_tokens。全部第一档原始响应封存后，依据 finish_reason=length 或未能提取完整明确最终答案，封存 escalation_decision.json，再执行16384。第二档参与 10 道。**没有使用正确性决定升级，也没有在两个档位中按 gold 挑选较优答案。** 最终选择每题最后执行档位。

实际 API 并发上限27（低于64），本地评分12进程，HTTP读取超时600秒；超时配置只影响运输等待，不影响生成参数。无基础设施错误、无重发、无数学错误重试。每次请求先持久化 pending；不确定计费的 pending 禁止盲目重发，已完成请求可从封存结果续跑。

| group | tasks | complete_final_answers | correct | complete_wrong | unknown | still_truncated | input_tokens | output_tokens | total_tokens | reasoning_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_4096 | 27 | 0 | 0 | 0 | 0 | 27 | 5375 | 110592 | 115967 | 109995 |
| rung_8192 | 27 | 17 | 17 | 0 | 0 | 10 | 5375 | 166798 | 172173 | 161013 |
| rung_16384_conditional | 10 | 8 | 8 | 0 | 0 | 2 | 1744 | 114480 | 116224 | 111754 |


16384 的分母是第一档未完成的子集，不能与8192的27题成功率直接比较。请求响应在 raw/；完整 reasoning_content 是模型内部推理输出，只作离线失败审计，不作为当前题重试反馈。api_calls.jsonl 记录实际 usage，generation_complete_seal.json 证明生成集合封存后才执行独立评分。重新执行分析时不会发起API。
