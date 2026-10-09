# 后续实验操作指引

## 当前阶段

开发已停在离线验证。不要把 fixture 上的结果纳入论文比较。没有学习过真实模型策略；`schema_examples.json` 只是格式示例，`offline_verified_bank.json` 是 synthetic bank，真实推理入口会拒绝加载它。

## 模式语义

| mode | 本实现的数学路径 |
|---|---|
| base_onepass | 原生 FlowEvo cot=True 数学提示，一次生成，不按 gold 或格式重试 |
| flowevo_goldfree | 对照原始公开数学无 context 路径；仅允许格式错误恢复，移除 gold 控制的 retry |
| flowevo_context_goldfree | 冻结的 clean train-build 成功解答库，原生词重合>3历史文本注入，数学检索开启 |
| bot_template | BoT 风格跨学科模板检索与完整步骤注入；不运行每题完整 LightRAG/蒸馏流程 |
| subject_strategy | 同学科紧凑策略固定检索；显式关闭 admission 的研究消融，允许 clean candidate/shadow |
| subject_strategy_admission | 只检索经 admission 的 active 策略，固定选择 |
| subject_strategy_costaware | active + dev 成本/风险预测 + 选择性跳过；默认主方法 |

数学全新题不能 exact replay 成历史答案。新模式均使用相同模型、temperature、输出格式和最大输出长度。原本的 `Here is a similar solved problem` 仅留在历史文本/模板对照；紧凑策略不用原题完整解答。

原生未经 gold 改造的代码仍位于 vendor，便于检视恢复；不要把它的数学 gold-assisted 结果与主方法直接比较。HumanEval/MBPP 测试器可运行，并有本地离线回归测试；未来下载原生基准需安装 `.[native]`，独立子进程中从 `vendor/flowevo` 调用其 runner。

## 数据准备

新项目无需再访问原始代码即可运行。已准备好完整 MATH 的新题面/标签副本：

- `data/manifests/math_grouped/train.json`：5,951 道 train-build。
- `data/manifests/math_grouped/dev.json`：1,549 道 train-dev。
- `data/manifests/math_grouped/test.json`：4,500 道测试候选。
- `excluded_test_ids.json`：algebra 原顺序前 500 道，保守登记曾用于调试或存在污染可能。

split 源是官方 train 7500 / test 5000，seed=42。重复题先形成跨学科/难度连通组，再按组代表学科/难度分层，所以实际比例不一定恰好 80:20。近重复检查是声明过的启发式，不能保证捕获所有语义重复。

不是独立 MATH-500，也不能把 algebra 的 500 道当成覆盖全类别的 MATH-500。当前来源 ID 为官方所下载 parquet 各类别内的顺序，manifest 包含内容 hash。未声称发现本地其他项目的独立 MATH-500 或恢复其 ID 列表。

重新准备（输出目录必须是新的）：

```bash
.venv/bin/python -m flowevo_bot.cli prepare-data \
  --math-dir /path/to/math_jsonl --output-dir data/manifests/new_split \
  --seed 42 --dev-fraction 0.2 --exclude-algebra-first 500
```

初始研究可选 Algebra/Number Theory 小规模子集。通过 `code_math.loader.load_manifest` 读取后，按公开 subject 选取 ProblemView；为同一批 ID 从隔离标签文件生成新的 train/dev/test manifest，使用 `flowevo_bot.data.write_manifest`，不要手改 count/hash，也不要为改善最终测试结果反复改变列表。

## 离线复现

README 给出了统一 CLI。`scripts/offline_acceptance.py NEW_NAME` 建立新 bank、逐个运行七模式并生成配对报告。该脚本不需要密钥。`--dry-run` 不联网；mock 只支持明确限定的手工简单算式、无抵消多项式次数和简单取余题，不支持的题保留为无法作答，不伪造标准答案。

## 未来真实 API（尚未执行）

决定实验方案后，设置 `DEEPSEEK_API_KEY` 环境变量，或者在一个不打印密钥的 Python 启动器中从 `../miyao.txt` 读取并传给子进程。项目不会自动复制/读取该文件，不应把 key 写入 YAML、shell 命令行字面量或报告。

真实请求同时需要非 dry-run 和显式 `--allow-paid-api`，或配置 `llm.allow_paid_api=true`。先用单独的非 synthetic manifest/bank；不要用 mock_bank 进行真实实验。模型、端点在 YAML 的 llm 中设置；`--model`、`--seed`、`--max-calls`、`--max-total-tokens` 可覆盖。供应商价格不在代码中硬编码；报告 token，费用按实验当天价格另算。

```bash
# 以下仅为未来授权后的命令示例，未执行
.venv/bin/python -m flowevo_bot.cli build-bank \
  --config configs/math_strategy.yaml \
  --train-manifest data/manifests/math_grouped/train.json \
  --dev-manifest data/manifests/math_grouped/dev.json \
  --output data/skill_banks/real_math_bank.json \
  --allow-paid-api --max-calls 100 --max-total-tokens 200000
```

这个示例预算会在完整训练集完成前耗尽，刻意不默许大规模运行。先预先声明并生成较小 manifest，再按实验设计设置预算。源轨迹生成、蒸馏和验证共享建库总预算；达到预算时中止并保存已完成记录。已完成任务不会重复请求。

按统一设置分别执行 base 和各实验模式，输出到不同子目录，之后对父目录 analyze。默认冻结 bank：测试途中不自动入库，也不据测试准确率调整策略阈值。

## 输出和断点

- `checkpoint.json`：密封回答，不含标签；绑定配置、bank、split、manifest 和 simulated 标志。
- `calls.json`：每次请求输入/输出 tokens、用途、route、skill ID、延迟、usage 是否估计、请求/响应 hash；记录原始模型内容和 prompt 以便审计。
- `calls.pending.json`：进程在真实请求期间中断时保留。服务商是否已计费/完成未知，必须核对后处理，程序不自动重发可能已收费的请求。
- `episodes.csv/jsonl`：逐题、首轮/最终正确、路由、输入/输出 token、重试数、bank版本、gold标记。
- `summary.json`：分类正确率、检索/注入/跳过率、每正确题成本、建库/验证/维护与摊销成本。
- 建库 `.work/`：训练轨迹、候选、独立验证调用和摘要。被淘汰候选与失败源题的已花费成本也保留。

`--resume` 必须使用相同声明的配置和输入。配置或 bank 改变会拒绝，已完成 bank 的 resume 返回同一内容 hash。不要把已完成结果当成新实验重新命名。需要不同预算/配置时明确建立新实验，不静默拼接不同协议。

## 配对分析

```bash
.venv/bin/python -m flowevo_bot.cli analyze \
  --runs-dir runs/experiment_family --output docs/EXPERIMENT_REPORT.md
```

报告会检查配对模式的模型、temperature、max_output_tokens、manifest和split。重复 task/condition 拒绝自动聚合，需选定一次重复实验。无匹配 baseline 时净节省为 null，而不是 0。

`.pairwise.json` 含四格正确性和逐题 token 差；`.amortized.json` 加入构建/验证/维护成本和单策略归因。多策略组合不进行虚假的独立收益归因。报告尚未实现 bootstrap CI 或正式非劣检验；这些是后续研究统计分析，而不是当前离线验收结论。
