# Counterfactual-Guided Reasoning Compression

结论与完整索引：[执行摘要](00_EXECUTIVE_SUMMARY.md)。本轮结论NO-GO；研究102次请求、已知299853tokens、取消上界1247。旧605题没有重新生成。

报告00–09依次记录轨迹、反事实、状态规则、API审计、实际控制器、独立验证、成本、归因和决策。机器可读主结果为`summary.json`，最终独立单位审计见`evidence/distinct_state_audit.json`；原门槛重复计数已更正为未通过，4题降级为探索性工程检查。所有物理请求在`api_calls.jsonl`，逐物理预算在`attempts/`，原始流在`raw/`。

运行环境沿用仓库`Flowevo-Bot/.venv`；V3依赖与哈希位于历史`experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json`。归档是工作区研究增量，历史原始轨迹在同一Git仓库保留，不在压缩包中重复拷贝。源码中的ROOT路径按仓库布局解析。

离线检查：

```bash
Flowevo-Bot/.venv/bin/python -m pytest -q experiments/counterfactual_reasoning_compression/code/test_protocol.py experiments/counterfactual_reasoning_compression/code/test_online.py
Flowevo-Bot/.venv/bin/python experiments/counterfactual_reasoning_compression/code/check_artifacts.py
```

按阶段的源码：grade_history → analyze_traces → api_audit → prepare_counterfactual → intervene → grade_and_fit → prepare_pilot → online_pilot → repair_negative_control → final_analysis → deduplicate_audit → write_reports。prepare脚本在已有冻结文件时拒绝重新选题；已封存生成脚本校验结果后复用，不重新付费。不要在发布结果上重新拟合或覆盖分析；如要新实验，应创建新目录和预算授权。

`counterfactual_outcomes.jsonl`是预注册主84次干预；`supplemental_negative_control_outcomes.jsonl`是审计发现段落过长后的3次修复对照，明确未用于重训。独立4题标签从生成进程隔离。`dataset_manifest.json`保留发现阶段冻结版本，独立扩展单列`independent_dataset_manifest.json`。
