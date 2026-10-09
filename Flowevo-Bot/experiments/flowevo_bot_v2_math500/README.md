# Flowevo-Bot V2 研究包

阅读顺序：01_IMPLEMENTATION_REPORT.md → 02_SKILL_BANK_REPORT.md → 03_MATH500_RESULTS.md → 04_MECHANISM_ANALYSIS.md → 05_NEXT_ITERATION.md。

本轮63次真实调用，20题三组对照；没有技能通过active准入，按指引停止正式500。不得将本目录名误解为已产生新的500题成绩。

机器入口：task_results.jsonl、task_pairwise.csv、skill_usage.csv、skill_bank_v2.json、skill_validation.csv、admission_decisions.jsonl、cost_breakdown.csv、api_calls.jsonl、dataset_manifest.json、run_manifest.json。

重放报告（不联网）：在Flowevo-Bot项目根目录执行 `.venv/bin/python scripts/report_v2_research.py`；完整验证 `.venv/bin/python -m pytest -q tests`，实验完整性验证 `.venv/bin/python scripts/verify_v2_research.py`。历史评分复核入口 scripts/recheck_v2_history.py，仅新增本目录文件。

复现执行阶段：`python scripts/run_v2_research.py prepare`、`distill --allow-paid-api`、`dev --allow-paid-api`。保留现有calls/submissions时使用缓存不重复请求；不要随意删除journal或修改冻结配置。为避免覆盖本次结果，开展新实验须复制脚本配置并使用新实验目录；本目录只用于同一冻结运行的恢复/审计。

报告和源码均随每轮同步到 https://github.com/ChenKaichen-SCUT/Flowevo-Bot 。API凭据与虚拟环境不随包发布。
