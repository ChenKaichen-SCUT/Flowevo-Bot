# FlowEvo + Buffer of Thoughts / Flowevo-Bot

这是完整研究工作区的可发布快照，包含原始实现的本地修改版、独立 Flowevo-Bot 项目、MATH/GSM8K 数据集、既有真实实验和下一阶段离线诊断。

## 先阅读最新研究结论

[Skill Admission 研究摘要](Flowevo-Bot/diagnostics/skill_admission_audit/reports/00_EXECUTIVE_SUMMARY.md) · [12 个 Skill 原文](Flowevo-Bot/diagnostics/skill_admission_audit/reports/01_ALL_SKILLS.md) · [诊断包下载](Flowevo-Bot/diagnostics/skill_admission_audit.zip)

本轮为零新增 API 的离线诊断：9/12 策略不能匹配来源题、8/12 缺少可用开发验证；另外发现条件语义和两次评分假阴性。500题Bot本轮请求路径等价于空库，测试token节省不能归因于BoT复用。原始结果与核心实现均保留，未降低阈值或新增真实实验。

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
.venv/bin/python diagnostics/skill_admission_audit/scripts/analyze.py
.venv/bin/python diagnostics/skill_admission_audit/scripts/render_reports.py
.venv/bin/python -m pytest diagnostics/skill_admission_audit/tests -q
```

历史manifest包含运行时绝对路径和哈希，迁移后需保持相同内容并按目录调整路径。诊断分析自身从当前源码目录定位实验文件；历史完整性测试中的原始绝对路径反映原实验环境。旧dist wheel是之前开发阶段的构建产物，复现新诊断使用当前源码。

不上传 `miyao.txt`、环境变量文件、私钥、虚拟环境、缓存及嵌套Git内部目录。数据集与真实实验记录已包含；新增付费模型实验须单独授权并自行在本地配置密钥。本轮仅完成诊断与发布。

原项目各自许可证及数据集说明均保留，见各子目录 LICENSE、NOTICE.md、licenses 和数据卡；本仓库不重新授权第三方内容。
