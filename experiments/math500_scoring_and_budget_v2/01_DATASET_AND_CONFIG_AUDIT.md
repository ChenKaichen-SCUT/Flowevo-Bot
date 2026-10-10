# 数据与配置审计

参考提交`c2586290a0086b0b9da3705e9799c2d04e060b32`，运行前发布仓库main与远端main都与其一致；本地工作区根目录不是Git仓库，发布checkout在`/mnt/Space1/Flowevo-Bot-upload`。原生FlowEvo上游HEAD记录在evidence/pre_run_version_check.json。历史4,617个发布文件在最终审计中仅根目录指引.txt因本轮用户新指令改变，其余历史源码和实验输出均未覆盖。

## 独立性与固定抽样

本地MATH源是EleutherAI/hendrycks_math，train7,500/test5,000。全部train保守排除，覆盖历次建库、验证、V1–V4开发/确认池；通过历史实验、运行记录、诊断和代码记录排除1,190个test ID，其中含旧500、27截断和9评分修复题。原生math_subject_i别名保守归到test。逐条来源见evidence/exposure_registry.json和exposure_artifact_index.json。

剩余3,810 test候选，与全部8,690排除题做全局比较（没有按学科阻断）：小写、空白规范化、数字掩码后的RapidFuzz Indel/LCS相似度≥90%视为近重复。排除554，剩3,256。固定seed20261010分层洗牌，逐学科×难度匹配旧500数量；选中内部也做全对近重复过滤，另跳过3个候选。选择只依赖题目与元数据，没有按答案、历史正确率或截断表现筛选。

| 学科 | L1 | L2 | L3 | L4 | L5 | 合计 |
|---|---|---|---|---|---|---|
| algebra | 8 | 14 | 17 | 18 | 21 | 78 |
| counting_probability | 4 | 10 | 11 | 13 | 14 | 52 |
| geometry | 4 | 9 | 11 | 14 | 15 | 53 |
| intermediate_algebra | 6 | 14 | 22 | 29 | 32 | 103 |
| number_theory | 3 | 10 | 13 | 16 | 17 | 59 |
| prealgebra | 9 | 20 | 25 | 22 | 22 | 98 |
| precalculus | 5 | 11 | 14 | 12 | 15 | 57 |

500个ID、split、problem hash、seed、exposure状态在dataset_manifest.json；完整公共题干在data/public_tasks.jsonl，标签独立保存。2026-10-10 07:30:42 UTC冻结数据，07:34:03 UTC冻结在线配置/代码，所有API调用均在其后。audit_artifacts.py核对hash、时间及重试集合。

局限：这是对**项目可追踪研究使用记录**的独立性，不能排除模型预训练、未记录的外部使用或语义近重复。原始全量测试目录和静态数据清单以前已存在；其存在不等于已解题或参与调参，不把它们误称为从未可见。所有实际开发/确认池则明确排除。

## 求解环境

- 原生`FlowEvo/src/code_math/runner.py::build_goldfree_math_prompt`，`cot_baseline`、`library=None`；native prompt经导出逐字核验。
- 模型请求名`deepseek-flash`，endpoint `https://api.deepseek.com/chat/completions`，temperature=0；其他参数不随阶段改变，仅max_tokens=4096/8192/16384。
- thinking字段遵循历史方式省略。官方当时默认启用high reasoning；思考模式下temperature不生效，所以请求temperature=0不代表确定性。响应仅提供模型别名，精确后端revision未返回，记unavailable，不能声称已固定不可变模型权重。
- Gold反馈、Gold反思、Skill注入、历史Skill检索、正确性重试、额外修复提示均显式false。在线路径不读取offline_labels；公开prompt字段白名单+精确请求重建检查阻断额外答案字段。
- 64个共享API worker；账本时间区间重建峰值64；本地评分/近重复最多12进程。
- 运行Python3.10，依赖版本见evidence/runtime_packages.json。旧新评分器文件hash见evidence/evaluators_frozen.json。

源代码审计、配置拒绝测试、577条真实请求精确重建均通过：Gold/Skill实际注入0，检索0，正确性重试0。这里“无法读取答案”指实际在线代码/请求数据路径；不是声称有独立OS文件权限隔离，也不排除模型训练记忆。模型为无工具chat请求，不能自行访问本地标签文件。

API模型与thinking语义依据[DeepSeek官方接口说明](https://api-docs.deepseek.com/api/create-chat-completion/)，配置及获取时间证据见preflight与pricing文件。
