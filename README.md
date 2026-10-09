# FlowEvo + Buffer of Thoughts / Flowevo-Bot

这是完整研究工作区的可发布快照，包含原始实现的本地修改版、独立 Flowevo-Bot 项目、MATH/GSM8K 数据集、历史实验、离线诊断、V2 和 RMMD 真实研究。

## 先阅读最新研究结论

[RMMD 宏发现研究](Flowevo-Bot/experiments/macro_discovery_pilot/README.md) · [三组结果](Flowevo-Bot/experiments/macro_discovery_pilot/reports/06_SMALL_BUDGET_EXPERIMENT.md) · [配对与完整成本](Flowevo-Bot/experiments/macro_discovery_pilot/reports/07_PAIRED_COST_ANALYSIS.md) · [本轮ZIP](Flowevo-Bot/macro_discovery_pilot.zip)

最新一轮从1,840条真实记录筛出603条干净训练首次成功轨迹，实现根对称量和多项式余式两个宏。14题三组均14/14正确：NoBank 9,936、Compact 14,396、Executable 10,564 tokens。4道余式题由精确执行完成，不调用LLM；根中间量增加的消耗抵消了其收益。本轮38次调用共34,896 tokens，107项回归通过。决策“继续改进”，优先任务级解析与可执行覆盖，未运行新MATH500。不得将14道条件筛选题当作MATH总体结果。

下列为保持原样的上一轮 V2 结论。

[V2 实验结果](Flowevo-Bot/experiments/flowevo_bot_v2_math500/03_MATH500_RESULTS.md) · [实现报告](Flowevo-Bot/experiments/flowevo_bot_v2_math500/01_IMPLEMENTATION_REPORT.md) · [机制与成本](Flowevo-Bot/experiments/flowevo_bot_v2_math500/04_MECHANISM_ANALYSIS.md) · [完整研究包](Flowevo-Bot/experiments/flowevo_bot_v2_math500.zip)

本轮修复评分、结构化 Trigger/Guard、多轨迹蒸馏及 shadow 准入，完成20题三组真实对照：NoBank 18/20、25,728 tokens；旧策略19/20、26,436 tokens；新策略19/20、28,579 tokens。两条新卡均为shadow、0 active，按指引停止正式500。63次新增API调用共102,316 tokens，未降低准入门槛。Guard为求解期指令，尚未实现机器证明；唯一正确率提升来自基础组截断、策略组完成，不能认定稳定数学推理提升。

[上一轮离线诊断](Flowevo-Bot/diagnostics/skill_admission_audit/reports/00_EXECUTIVE_SUMMARY.md) · [旧12卡原文](Flowevo-Bot/diagnostics/skill_admission_audit/reports/01_ALL_SKILLS.md)。历史数据与原始评分保留。

## 工作区结构

- `Flowevo-Bot/`：独立策略库与成本感知复用原型；源码、测试、配置、实验及诊断。
- `FlowEvo/`：FlowEvo 本地实现，MATH/GSM8K skill 注入已打开，gold 反思已关闭。
- `buffer-of-thought-llm/`：Buffer of Thoughts 实现及 DeepSeek 单题适配记录。
- `指引.txt`：本阶段完整研究要求。
- `UPLOAD_MANIFEST.json` / `UPLOAD_EXCLUSIONS.json`：发布文件哈希与排除清单。

[500题原实验报告](Flowevo-Bot/experiments/math500_goldfree_20261009/REPORT.md)：FlowEvo 462/500，Bot 464/500；测试token 641,955 vs 523,020；包括建库1,437,390 vs 1,592,751。该500题为本地MATH分层抽样，不是标准MATH-500。

## 离线复现

```bash
cd Flowevo-Bot
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,experiment]'
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/verify_v2_research.py
.venv/bin/python scripts/report_v2_research.py
```

历史manifest包含运行时绝对路径和哈希，迁移后需保持相同内容并按目录调整路径。旧诊断脚本属于冻结历史，V2 使用新入口。V2 的构建产物为0.2.0；0.1.0旧wheel保留作历史记录。

不上传 `miyao.txt`、环境变量文件、私钥、虚拟环境、缓存及嵌套Git内部目录。数据集与真实请求/响应安全日志已包含。后续每轮按已确认的单连字符仓库地址发布，见 [PUBLISHING.md](PUBLISHING.md)。新付费实验需明确预算和独立新目录；本轮已在用户授权范围内执行并结束。

原项目各自许可证及数据集说明均保留，见各子目录 LICENSE、NOTICE.md、licenses 和数据卡；本仓库不重新授权第三方内容。
