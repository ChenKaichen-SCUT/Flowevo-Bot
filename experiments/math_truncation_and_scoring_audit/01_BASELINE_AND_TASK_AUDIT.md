# 基线与任务审计

参考仓库 ChenKaichen-SCUT/Flowevo-Bot，基线提交 6acc7335bbe6b731ef3e387d573b6689b90c0550。原目录 `Flowevo-Bot/experiments/math500_goldfree_20261009/flowevo_bot/`，本轮读取的 manifests、rows、calls、checkpoint 及 500 个 provider sidecars 均已列入 `evidence/baseline_file_hashes.json`。上一发布快照全部文件哈希另存 `evidence/protected_previous_snapshot.json`，收尾逐文件复查，不覆盖历史实验数据或代码。根目录指引.txt 在本轮开始前为空（mtime 04:03 UTC，早于此次附件04:59 UTC）；已保留上一发布版指引和观测到的空状态，再将本轮附件写为当前指引。此文档更新是唯一上一快照文件变更，见 evidence/guide_version_transition.json。

500 个 task ID 唯一且逐一对应；历史正确 464，错误 36；27 道截断与 9 道非截断假阴性互不重叠。全部请求 route=base、skills=[]、retry_count=0，gold/reference_solution 暴露标记均为 false。本历史结果虽然存于 flowevo_bot 目录，但实际未触发策略注入，不能用它证明策略库有增益。

逐个核对了请求哈希、可见响应哈希、ledger/checkpoint 一致性、实际 usage、finish_reason 与旧评分标志。原请求均为 model=deepseek-flash，endpoint=https://api.deepseek.com/chat/completions，temperature=0.0，max_tokens=4096。system 为 `You are an expert programmer and mathematician.`；完整 user prompt 保存在 provider.request，统一要求 step by step 并以 The answer is 结尾。未设置 thinking/reasoning_effort，沿用服务端默认值；新请求也不增加这两个字段。

27 个真实 finish_reason 均为 length，且 completion_tokens 均等于请求上限 4096；并非仅根据输出长短猜测截断。25 道 reasoning_tokens=4096、可见正文为空。另两道如下：

| task_id | visible_chars | reasoning_tokens |
| --- | --- | --- |
| math_test_intermediate_algebra_6 | 906 | 3624 |
| math_test_prealgebra_100 | 369 | 3971 |


全部 27 道都未形成完整最终答案，原始完整答案数为 0。对空正文的 25 道可直接确认预算全部耗于 reasoning；另两道分别有少量可见推导，但也在上限处中止。相关数据在 `truncated_27_task_ids.json`、`evidence/baseline_500.json` 和 `truncation_task_results.jsonl`。

**历史日志限制**：500 次的精确 request、provider_model、response_id、usage（含 reasoning token）和 finish_reason 均保留，可见正文也完整保存在 checkpoint/ledger。但原 transport 未保存完整 HTTP JSON 和 reasoning_content 文本；本轮无法还原未保存的隐藏推导内容。新调用同时保存原始 HTTP body 与解析后的完整 JSON。模型别名一致不保证后端 revision 一致；历史也无可供固定的 revision/system_fingerprint。

官方文档来源（2026-10-10 核对）：[请求 API](https://api-docs.deepseek.com/api/create-chat-completion/)、[thinking 模式](https://api-docs.deepseek.com/guides/thinking_mode/)。文档说明 thinking 默认开启，temperature 在该模式下被接受但不生效。本轮仍保留原 temperature 字段，避免混入配置变化。
