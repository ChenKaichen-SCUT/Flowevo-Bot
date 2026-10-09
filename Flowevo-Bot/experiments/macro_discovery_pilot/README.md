# Reusable Mathematical Macro Discovery Pilot

根据本轮《指引.txt》完成的单轮真实研究。原始上游、V1、V2记录全部保留。

从1,840条真实求解记录中筛出603条干净首次正确训练轨迹，6条根对称量来源、2条余式来源支持两个宏候选。14题×3组均14/14正确，A NoBank 9,936 tokens，B Compact 14,396，C Executable 10,564。C的4道余式题通过全任务数学证书直接完成，其余10题提供验证中间量后仍调用LLM。共38次真实API、34,896 tokens，无截断、重试或gold反思。

这是经过严格筛选的独立开发小样本，余式仅4题，不能推出MATH总体正确率或准确率非劣。Compact组比A增加44.89% tokens，C整体增加6.32%；工具替代值得继续检查，当前根中间量提示没有体现经济收益。决策：**继续改进任务级结构解析与可执行覆盖，暂停扩展当前提示路线**。未运行新500题或后续调参。

- [00 状态与协议](reports/00_STATE_AND_PROTOCOL.md)
- [01 语料审计](reports/01_TRACE_CORPUS_AUDIT.md)
- [02 操作挖掘](reports/02_REASONING_PATTERN_MINING.md)
- [03 候选排序](reports/03_MACRO_CANDIDATE_RANKING.md)
- [04 实现](reports/04_MACRO_IMPLEMENTATION.md)
- [05 付费前验证](reports/05_PREPAID_VALIDATION.md)
- [06 真实三组结果](reports/06_SMALL_BUDGET_EXPERIMENT.md)
- [07 配对与完整成本](reports/07_PAIRED_COST_ANALYSIS.md)
- [08 决策及交付](reports/08_GO_NO_GO_AND_DELIVERABLES.md)

目录包含 data/ 语料、IR、频数、候选、银行、题单和逐题结果，api_calls/ 完整安全请求响应，submissions/ 评分前密封输出，evidence/ 预算和冻结审计，snapshots/ 运行前源码快照，tests/ 验证记录。完整学习语料不包含官方参考解答。历史离线评分和发布的数据标签不参与在线求解。

从项目根目录离线验证与重建报告：

```bash
python -m pip install -e '.[dev,experiment,rmmd]'
python -m pytest tests experiments/macro_discovery_pilot/tests -q
python experiments/macro_discovery_pilot/code/reports.py
python scripts/finalize_rmmd.py
python scripts/verify_rmmd.py
```

付费前代码在 `snapshots/runtime_before_paid.zip`，由 `evidence/prepaid_freeze.json`逐项SHA固定。公开问题池用于选题，标签文件付费前只读hash；全部42提交seal完成后才离线读答案。报告补充及最终验证脚本是事后分析，不改变冻结求解代码、题单和请求。

本目录已完成并冻结。复现新的模型输出需新目录和预算，不能覆盖已有调用。缓存恢复只读取相同请求/代码hash，未知计费pending不自动重发。新代码以0.3.0 wheel交付，旧0.1.0/0.2.0产物保留；独立归档在项目根目录 `macro_discovery_pilot.zip`。
