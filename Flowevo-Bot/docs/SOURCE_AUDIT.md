# Stage 0 源码审计（2026-10-09）

审计在新项目实现之前完成。源文件逐项 SHA-256、真实绝对路径、Git 状态见 `source_snapshot.json`；该文件用于交付时确认原项目没有被修改。

## 本地版本与已有修改

- FlowEvo: `/mnt/Space1/FlowEvo+BoT/FlowEvo`，commit `36e81efd4d1fdbabca7366200b15808ebef157fa`，pyproject 0.1.0，要求 Python >=3.9，本地 3.10.12。Apache-2.0，许可证原文保留。
- BoT: `/mnt/Space1/FlowEvo+BoT/buffer-of-thought-llm`，commit `b46ac813cc2aa2c8f98aa93022d0e491b3862cfc`，未声明包版本，README 建议 Python 3.9，本地 3.10.12。MIT，copyright Ling Yang 2024。
- FlowEvo 当前 MATH/GSM8K 的提前 `return none` 已移除；本地另外有离线数据加载、DeepSeek 配置、两个 scripts、锁文件、README 修改和单题 runs。
- BoT 已有 API 按需加载、key-file/base-url/limit 参数、独立 API 依赖与 24 点单题 test_results。全部保留。
- 两仓库未发现自动化测试套件。BoT `test_templates.py` 是解题模板而非测试用例。新项目不能把已有一次单题通过解释成完整回归测试。

## FlowEvo 实际执行路径

`src.code_math.runner.main` -> `load_tasks` -> `run_condition`。`CodeTaskInstance` 同时含题目、reference 和 metadata.gold_answer，不能直接作为新 solver 的参数。

`CodeSkillLibrary.add` 在通过 verify 后保存完整解答；索引缓存题目前 200 字符和解答前 500 字符。`retrieve` 首先以 task_id exact 匹配，否则同 benchmark 词重合 >3 时返回一个历史解答上下文。checkpoint 保存 episodes 和整个 library，没有 bank/config/split 内容一致性校验。

数学首次提示词（cot=True）实际为：

```text
Problem: {task.prompt}

Solve step by step. End with: The answer is [your answer].
```

有上下文时在前面添加 `Here is a similar solved problem for reference:` 和历史 Problem/Solution。数学任务 Level 1 已使用上下文，ours 的代码任务 Level 1 仍抑制上下文。重试也可注入上下文。exact 检索结果在当前 run_condition 中没有直接 replay 分支，不能把类注释当成已实现的运行时复用。

`verify` 对数学题读取 gold，失败反馈为 `wrong: predicted=..., gold=...`。`run_condition` 用这一结果决定是否重试，并把反馈放进 retry prompt。因此原生数学 ours 不是 gold-blind；成功的 gold-assisted retry 还会进入原始库。必须重写此路径，不能仅删除反馈里的 gold 字符串而保留以 gold 判定重试。

runtime.LLMClient 返回逐次 prompt_tokens/completion_tokens/total_tokens/latency；缺失 usage 会转为 0。runner 只累积输入+输出，报告未分解单次成本。新项目需要重新封装缺失 usage 标记与逐次持久化。

## BoT 实际执行路径

`BoT.bot_run`: problem_distillation -> 按 problem_id 固定选择 game24/checkmate/word_sorting 模板 -> reasoner_instantiation -> 执行生成 Python；可按执行错误修复。

`BoT.bot_inference`: 蒸馏题目 -> LightRAG hybrid 检索并实例化 -> 对单个问题/解答 thought_distillation -> buffer_manager 动态更新。MetaBuffer 使用同一 API key/base URL 调用 chat 和 embeddings，embedding_dim 固定 3072；math.txt 为预置数学模板。去重依赖一次自然语言 True/False 判定，无独立跨题 admission、类别 bank、成本路由或来源隔离。

Pipeline.get_respond 仅返回 content；LightRAG 的完成接口也丢弃逐调用 usage。全量 requirements 涉及 torch/transformers/CUDA/Jupyter，API requirements 则只有 OpenAI/sympy/chess；数学 RAG 还有额外依赖。新项目借鉴多轨迹策略蒸馏与模板管理概念，重实现轻量接口，不强制 embedding API，不执行任意模型代码。

## 复用决定与论文/说明差异

保留 FlowEvo 本地原生源码独立快照，可恢复原生 HumanEval/MBPP 和旧算法；新项目保留其数学 base prompt 和历史文本检索作为 gold-free baseline。BoT 的模板与蒸馏机制提供设计来源，两项目许可证随快照保存。

必须新实现：ProblemView/EvaluationRecord 边界、冻结提交、来源筛选、多题聚类、结构化 bank、admission、成本路由、token ledger、数据划分和 checkpoint 校验。

公开仓库数学 runner 使用最小文本记忆，与论文/README 中更广义的可执行 skill 编译和治理框架并非同一实现；BoT 三基准为固定模板而非通用 embedding 检索。这里报告本地实现差异，不声称复现论文全部机制或指标。

## 数据现状

已有 MATH 7500 train/5000 test 和 GSM8K main 7473 train/1319 test。此前读取过 MATH algebra 第 1 题、运行过 GSM8K 第 1 题；用户指引提及 algebra 前 500 题可能用于调试，不能声明其 pristine holdout。新 manifest 会显式排除 algebra 前 500 题作为保守污染登记；不把它称为独立 MATH-500。新的 train-build/train-dev 按 subject/level 分层，并按近重复题组避免跨界。
