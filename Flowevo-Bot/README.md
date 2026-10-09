# Flowevo-Bot

按照父目录《指引.txt》实现的独立数学策略库研究原型。将 FlowEvo 的数学解题/历史解答基线与 BoT 的策略蒸馏思想结合，加入多题聚合、七学科检索、独立 admission、成本路由和 gold 隔离。

**最新 Goal-Aware Macro V3 已完成离线研究，付费门槛未通过。** 原dev 1,549题中，人工工具完整求解20题、自动构建宏完整求解2题；直接提交均正确，但不代表端到端准确率。独立保留池1,115题仅1题适用，因此本轮新增API调用和tokens均为0，未运行MATH500。受限DSL自动合成根和/根积两个程序，尚未超过人工工具基线。[本轮报告](experiments/goal_aware_macro_v3/README.md) · [自动构建机制](experiments/goal_aware_macro_v3/03_AUTOMATIC_MACRO_DISCOVERY.md) · [条件试验结果](experiments/goal_aware_macro_v3/05_PILOT_RESULTS.md) · [归档](goal_aware_macro_v3.zip)。新增模块 `src/flowevo_bot/goal_v3/`，包版本0.4.0，132项测试通过。

**上一轮 RMMD 宏发现试验：603 条干净训练轨迹，14 题三组均14/14正确；NoBank 9,936、Compact 14,396、Executable 10,564 tokens。38次API共34,896 tokens，未运行新500题。** 余式工具直接完成4题省2,950 tokens，但根对称量中间提示增加消耗；决策为继续改进任务级解析与可执行覆盖，暂停扩展当前提示路线。[RMMD研究包](experiments/macro_discovery_pilot/README.md) · [三组结果](experiments/macro_discovery_pilot/reports/06_SMALL_BUDGET_EXPERIMENT.md) · [配对与成本](experiments/macro_discovery_pilot/reports/07_PAIRED_COST_ANALYSIS.md) · [独立ZIP](macro_discovery_pilot.zip)。这些是条件筛选的小样本，不能外推MATH总体准确率。

历史研究完整保留：[V2 20题研究](experiments/flowevo_bot_v2_math500/03_MATH500_RESULTS.md) · [V1 500题实验](experiments/math500_goldfree_20261009/REPORT.md)。以下原始CLI示例仍为v1离线演示，mock分数不代表模型性能。

RMMD新增模块位于 `src/flowevo_bot/rmmd/`。安装 `pip install -e '.[dev,experiment,rmmd]'`；运行 `python -m pytest tests experiments/macro_discovery_pilot/tests -q`。离线报告重建见本轮README，付费执行已结束，不应覆盖冻结目录重跑。

V2 使用 `scripts/run_v2_research.py` 分阶段运行，修复模块位于 `src/flowevo_bot/v2/`；旧实现保留以重放历史结果。安装数学实验依赖 `pip install -e '.[dev,experiment]'`。报告可离线重建：`python scripts/report_v2_research.py`；完整性检验：`python scripts/verify_v2_research.py`。

## 安装与检查

```bash
cd /mnt/Space1/FlowEvo+BoT/Flowevo-Bot
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

已经创建 `.venv`。`requirements.lock.txt` 记录交付环境；精确重建时先安装锁文件再安装本项目。核心包只依赖 Pydantic、PyYAML、requests，无强制 embedding 服务、GPU、torch 或原始源码目录依赖。

## 离线入口

```bash
# 读取两个指定本地仓库，缺失时明确失败
.venv/bin/python -m flowevo_bot.cli audit \
  --flowevo-path ../FlowEvo --bot-path ../buffer-of-thought-llm

# 从标明 synthetic 的训练 fixture 收集成功轨迹，聚类、蒸馏并在独立 dev fixture 上验证
.venv/bin/python -m flowevo_bot.cli build-bank \
  --config configs/math_strategy.yaml \
  --train-manifest data/manifests/train.json \
  --dev-manifest data/manifests/dev.json \
  --output data/skill_banks/my_demo_bank.json --dry-run

# 冻结评测：新的输出目录；每次回答先密封，再由隔离 evaluator 评分
.venv/bin/python -m flowevo_bot.cli evaluate \
  --config configs/experiment_modes.yaml --mode subject_strategy_costaware \
  --split test --bank data/skill_banks/my_demo_bank.json \
  --output-dir runs/my_demo --dry-run

.venv/bin/python -m flowevo_bot.cli analyze \
  --runs-dir runs/my_demo --output runs/my_demo/ANALYSIS.md
```

`--dry-run` 强制使用离线 mock，即使环境中有密钥或同时传入 `--allow-paid-api` 也不会联网。默认配置同样关闭真实 API。已有输出不被静默覆盖；恢复执行须使用 `--resume`，且 bank、配置、数据版本和 split 必须一致。

完整离线验收：

```bash
.venv/bin/python scripts/offline_acceptance.py my_new_acceptance
```

每次使用新的名称。已完成的验收保存在 `runs/offline_verified/`，七种模式共 21 个 mock 任务、18 条逐题配对结果；`data/skill_banks/offline_verified_bank.json` 中两条策略为 **shadow**，不能当作已验证的真实活跃 skill。

## 数据和模式

实际 MATH 数据已复制为新项目自己的题面/标签文件，位于 `data/manifests/math_grouped/`：train-build 5,951，train-dev 1,549，测试候选 4,500。先按规范化/近重复题组成连通组，再按学科与难度分层；详见 [数据检查](docs/DATA_SPLIT_VALIDATION.json)。所有被保守排除的 algebra 前 500 测试题 ID 单独记录。**这不是 MATH-500，也不宣称剩余题目完全未被接触。**

`data/manifests/{train,dev,test}.json` 是很小的手工 mock fixture，默认仅用于离线演示。`docs/development_artifacts/` 保存开发中被替代的初版划分，禁止用于正式实验。

支持七个模式：`base_onepass`、`flowevo_goldfree`、`flowevo_context_goldfree`、`bot_template`、`subject_strategy`、`subject_strategy_admission`、`subject_strategy_costaware`。详细差异和未来真实实验授权方法见 [EXPERIMENT_GUIDE](docs/EXPERIMENT_GUIDE.md)。

## 交付索引

- [架构与接口边界](docs/ARCHITECTURE.md)
- [实现报告、限制和测试结果](docs/IMPLEMENTATION_REPORT.md)
- [测试用例列表](docs/TEST_REPORT.md)
- [变更记录](docs/CHANGELOG.md)
- [七学科可加载 schema 示例](data/skill_banks/schema_examples.json)，全部为 candidate
- [来源和许可](NOTICE.md)

本原型默认只选择一条约 100 estimated tokens 的紧凑策略；超预算会拒绝，不能直接截断。成本预测缺乏证据、收益不为正或风险超限时回到 Base LLM。自动反馈修复只针对输出格式，绝不依据 gold 判定是否重试。Route C 默认关闭，当前仅支持可完全识别的整数四则算式，不把一般中间计算当成整题成功。
