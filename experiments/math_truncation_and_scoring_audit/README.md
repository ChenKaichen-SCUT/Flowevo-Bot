# MATH 截断与评分审计

结果：9道评分假阴性全部修正；原封存输出473/500；27道截断题在两档新采样中恢复25道，探索性组合498/500。37次调用共288,397 tokens。可靠完整数学错误0道，剩余2道仍截断。详细结论和局限见00—06报告。

目录内保留原500题封存证据、全部新HTTP body/JSON、逐题评分、成本、升级名单与代码哈希。`remaining_true_failures.jsonl` 特意为空（0条），不是缺失。`evidence/manual_math_review.json` 记录两道未完成题和额外发现的参考语义歧义，未从隐藏推理修改成绩。

在工作区根目录运行以下命令可离线重现统计与验证，不调用模型：

```bash
Flowevo-Bot/.venv/bin/python experiments/math_truncation_and_scoring_audit/code/analyze.py
Flowevo-Bot/.venv/bin/python experiments/math_truncation_and_scoring_audit/code/manual_review.py
Flowevo-Bot/.venv/bin/python experiments/math_truncation_and_scoring_audit/code/write_reports.py
Flowevo-Bot/.venv/bin/python -m pytest -q experiments/math_truncation_and_scoring_audit/tests
```

若需要从原封存正文重做评分器阶段，先运行 `code/rescore.py`，随后按上述顺序执行 analyze.py；后者重建同时含 A/B/C 的最终 CSV。环境为Python3.10，实际依赖见 evidence/runtime_packages.json。新评分器位于 FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py；原评分器保持原样，差异见 evidence/scorer_before_after.diff。

`code/prepare.py` 是一次性冻结脚本，不应对发布后快照重新执行。`code/run_budgets.py` 是已完成的真实生成入口，本轮已停止调用；复现统计不需要运行它。精确原请求+max_tokens变化、gold-blind升级和原始响应完整性均有测试。

发布压缩包包含本目录、评分器及其直接依赖，完整环境和历史代码以GitHub仓库为准。run_manifest.json记录其余交付文件的SHA256；自身和ZIP不能循环自哈希，ZIP哈希单独记录在发布审计中。
