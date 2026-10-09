# Skill Admission 离线诊断包

阅读顺序：reports/00_EXECUTIVE_SUMMARY.md → 01_ALL_SKILLS.md → 03_ADMISSION_DIAGNOSIS.md → 08_RECOMMENDATIONS.md。

- reports：9份完整中文报告。
- data/skills_full.json：12个真实Skill的完整原记录。
- data/skill_diagnostics.csv、admission_decisions.jsonl：逐Skill、逐关数据。
- data/skill_task_matches.csv：12×350=4200条开发匹配记录；不使用标签生成特征。
- data/task_pairwise.csv：500题实际配对，不修改历史分数。
- data/cost_breakdown.csv、prompt_config_comparison.csv：账本与公平性审计。
- data/evidence：71条必要来源轨迹、4个准确率不一致开发题、真实prompt示例和provenance证据，未打包整个历史响应库。
- scripts：可复现的只读诊断/渲染及人工质量评注。
- tests：网络禁用、契约/反例/账本/历史哈希验证。
- manifest.json：源commit、哈希、数据/模型与unknown项。报告时间使用Asia/Shanghai。

从Flowevo-Bot目录复现：

```bash
.venv/bin/python diagnostics/skill_admission_audit/scripts/analyze.py
.venv/bin/python diagnostics/skill_admission_audit/scripts/render_reports.py
.venv/bin/python -m pytest diagnostics/skill_admission_audit/tests -q
```

需要原experiments目录及当前项目依赖。analyze.py主动禁用socket连接，不调用模型；输出限制在本诊断目录。独立zip可直接阅读全部报告及必要证据；完整重算还需manifest引用的大日志。

本轮新增API调用0，token0，成本0。所有反事实仅重放规则；所有数学反例是明确标注的本地构造，不是模型实验数据。已有生产核心代码与历史结果全部保留。
