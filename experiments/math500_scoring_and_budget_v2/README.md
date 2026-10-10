# math500_scoring_and_budget_v2

本轮依照USER_GUIDE.txt执行；独立新500题、原生FlowEvo无Skill/无gold的CoT路径；4096→8192→16384完成状态控制；同题同预算重采样辅助组。

**主结果A456/B449/C485/D476；决策PARTIAL。**先读[00_EXECUTIVE_SUMMARY.md](00_EXECUTIVE_SUMMARY.md)。正式自动分数与事后数学审计分开；审计敏感性为首轮467、自适应496，非冻结评分器成绩。

## 报告

- 01_DATASET_AND_CONFIG_AUDIT.md：独立抽样、真实配置与隔离；01_EVALUATOR_AUDIT.md：旧评分回归。
- 02_SCORING_FIX_VALIDATION.md、05_SCORING_CONTRIBUTION.md：评分泛化失败与逐案证据。
- 03_COMPLETION_CONTROLLER.md、06_ADAPTIVE_BUDGET_CONTRIBUTION.md：完成规则、预算贡献。
- 04_FOUR_WAY_RESULTS.md、09_ACCURACY_AND_COST.md：四组分数、统计与成本。
- 07_RESAMPLING_CONTROL.md：E4096与8192的同题配对。
- 08_REMAINING_FAILURES.md、10_NEXT_RESEARCH_DECISION.md：24候选审查与下一步判断。

## 证据与重现

api_calls.jsonl及raw/提供577条完整请求、响应、原始HTTP正文和attempt账本；first_pass/adaptive/same_budget分别指向共享输出。四组逐题CSV、两评分jsonl、分歧CSV、恢复CSV、费用CSV、summary均公开。审计附加manual_audit_results.jsonl、remaining_true_math_errors.jsonl、label_integrity_audit.json；evidence下保留审计前原数据快照。

在仓库根目录、已安装本项目依赖的现有Python3.10环境离线执行：

```bash
Flowevo-Bot/.venv/bin/python -m pytest experiments/math500_scoring_and_budget_v2/tests experiments/math_truncation_and_scoring_audit/tests/test_scoring.py -q
Flowevo-Bot/.venv/bin/python experiments/math500_scoring_and_budget_v2/code/audit_artifacts.py
```

上传包不包含虚拟环境或凭据；新环境按项目requirements安装，精确实测包版本见evidence/runtime_packages.json。code/evaluators.py复用仓库内旧评估器和FlowEvo-Recovery/math_scoring_v2.py；源码hash记录在pre_api_freeze.json，归档另外打包这些依赖源码。

从封存输出重新生成统计会重写派生文件，因此应在**新的工作副本**运行：先code/analyze.py（全部生成seal已存在，离线无API），再code/manual_audit.py，再code/write_reports.py。它们不修改原模型响应/评分器。运行耗时属于该次重放，可能与原记录不同。

run_experiment.py是付费生成入口，本轮已完成；不要为查看报告重跑它。prepare_dataset/export_native_prompts/preflight/freeze是调用前的一次性准备步骤，也不要在已封存目录重复执行。重新研究需新目录/新预注册，而不是覆盖本轮证据。

最终测试67项通过（evidence/tests_final.txt）；预调用59项通过。最终新增pending恢复测试首次因临时fixture未传配置而失败，已修正测试fixture后全通过；在线冻结源码未修改，首轮测试日志也保留。

run_manifest.json为全部本轮文件及复用源码的SHA256索引；ZIP位于仓库根目录math500_scoring_and_budget_v2.zip，对应校验文件math500_scoring_and_budget_v2.zip.sha256。发布前检查秘密、历史hash、stage实际文件与上传manifest；commit的真实SHA以GitHub远端及最终交付消息为准，避免在提交内制造自引用hash。
