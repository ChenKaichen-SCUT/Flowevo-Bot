# 实现与交付报告

## 结果

已按《指引.txt》完成 Stage 0–6 的独立研究原型与离线验收。项目目录为 `/mnt/Space1/FlowEvo+BoT/Flowevo-Bot`。本阶段真实 LLM/API 调用数为 **0**，实际模型费用为 **0**；没有运行真实 MATH 500 题或其他批量推理实验。

原始 FlowEvo 与 BoT 未修改，历史实验未覆盖。开始时的逐文件 hash 与 Git 状态保存在 `source_snapshot.json`，结束时核验见 `SOURCE_UNCHANGED.json`。只读审计捕获到了原始 FlowEvo 数学 gold-assisted retry 风险，以及本地数学 skill 注入已开启的现状。

## 阶段记录

| 阶段 | 已完成内容 | 实际离线检查 |
|---|---|---|
| Stage 0 | 真实路径/commit/license/接口/prompt/反馈/成本审计，来源快照 | 文件读取、接口确认、原始状态记录 |
| Stage 1 | 独立包装、严格 schema、七学科分类、base mock 路径、token ledger | 首批 9 项通过 |
| Stage 2 | 合法首轮轨迹、多题结构聚类、一次蒸馏、拒绝无通用策略、去重合并 | Stage 1–2 共 16 项通过 |
| Stage 3 | 独立 paired dev、四格表、成本和伤害阈值、shadow/active/certificate | 入库与路由组 9 项通过 |
| Stage 4 | 题面触发、同学科检索、成本/置信度/风险过滤、Base 回退 | 更贵 A/便宜可靠 B/前提不满足 C 的选择测试通过 |
| Stage 5 | 七种模式、gold-blind 求解/评分、格式修复、可恢复 checkpoint | 集成和泄漏组 16 项通过 |
| Stage 6 | CLI 全流程、配对/摊销报告、真实数据划分、原生代码回归、安装检查 | 最终测试以 `test_results.xml` / `TEST_REPORT.md` 为准；当前 52 项通过 |

所有测试均禁用 socket 网络访问；原生 HumanEval/MBPP 子进程只执行手工算术函数和断言，不创建 LLM 客户端。离线 CLI 使用显式 mock transport。

## 新增和保留的文件

新实现代码位于 `src/flowevo_bot/`、`src/code_math/`、`src/runtime/`。完整逐文件清单见 `FILE_INVENTORY.json`，测试列表见 `TEST_REPORT.md`。

- `configs/default.yaml`、`math_strategy.yaml`、`experiment_modes.yaml`：独立模型、策略、admission、router、评估和预算。
- `scripts/make_fixtures.py`：可追溯的人工合成题及七学科 candidate schema 示例。
- `scripts/offline_acceptance.py`：完整建库、七模式评估、18 条配对比较。
- `data/manifests/`：公开题面文件与隔离标签文件；fixture 与真实 MATH 使用不同目录和 synthetic 标记。
- `data/skill_banks/`：空库、七学科示例和离线 mock 建库产物；没有宣称存在已真实验证的 active skill。
- `vendor/flowevo`、`vendor/bot`：所审计本地源码的必要快照与许可证。未复制原环境、Git、缓存、秘密配置和旧 runs。
- `docs/`：审计、架构、实验指引、变更、测试、数据检查和原目录保护证据。
- `dist/`：可独立安装的 wheel；运行库不从两个原始项目导入模块。

## 已实现机制

1. MATH 七学科标准化、公开 metadata 来源记录与保守规则分类。默认同学科检索，可显式跨学科。
2. 完整内部 SkillRecord 和受限 compact_prompt 分离。来源、版本、验证、token、生命周期、composition_tags 和 executor 字段均可序列化。
3. 多个不同 clean train-build 首轮正确轨迹才能提炼。聚类使用题面特征、初步标签与解题变换特征，不把每题答案直接变 active skill。
4. distiller 接受 no_generalizable_skill；结构化解析和 schema 验证。泛泛建议、超预算压缩、不支持的条件以及丢失声明例外均可拒绝。
5. 独立 dev 的 paired base/skill 验证；生成完成后才读取 gold。记录有益、有害、都对、都错、输入/输出 tokens 和格式修复成本；相同数字掩码结构不重复抬高有效样本数。
6. admission、内容证据、shadow、active、quarantine、retire；合并和拆分均清空验证，需要重新验证；revision 独立计费。
7. dev 成本均值与节省下界、Wilson 风险界、置信度与题长范围判断。没有充分证据时不用精确预测假装可靠，而是 Base。
8. 七模式运行开关；共同的答案格式、temperature 和生成上限。数学历史文本注入在专门 baseline 中保留。
9. 每请求独立 usage、估计标志、用途、延迟、请求/响应 hash。总建库成本包含失败来源题、被拒绝候选、验证和维护；不会因为没有 active skill 就把这些成本清零。
10. 请求缓存与 pending journal、原子 checkpoint、恢复一致性校验。已完成 bank 恢复保持相同内容 hash。
11. 新项目内的真实 MATH 数据副本及独立划分；逐题 CSV/JSONL、分类准确率、路由率、配对 token差、单策略收益和摊销指标。
12. 可选 Route C 的精确算术子域，默认关闭。

## 实际离线验收

最终验收目录：`runs/offline_verified/`。对应 bank：`data/skill_banks/offline_verified_bank.json`。

- 七个模式各执行 3 道手工 mock 题，共 21 个任务结果。
- 相同题目与 base_onepass 的逐题配对共 18 条。
- 来源 train fixture 6 题，两个策略各有 3 个不同来源，dev 每学科 2 题；验证不足，两个策略都保留 shadow。
- 固定历史/模板/紧凑策略实验能发生注入；默认 admission/cost-aware 路径会跳过这些 shadow 策略。这是验证保守路由的预期行为。
- Mock 能解答这些手工题不代表 DeepSeek 在 MATH 的实际正确率。模拟 token 估计和净收益不能作为科研结论；报告中显式标记 simulated/estimated。

MATH 初版仅在学科/难度内分组时发现 12 个规范化跨 split 重复和 151 个共享前缀的明显近重复命中，已替换为全局重复组优先的划分。初版留在 `docs/development_artifacts` 作为审计材料，未用于真实实验。最终划分为 5951/1549/4500，另排除500；同一规则的跨 split 检查通过。

## gold 防泄漏措施

- `ProblemView` 与 `EvaluationRecord` 分类型、分文件；solver 类型检查拒绝 richer task 对象。
- 当前题标签不能进入题面特征、retrieval、router、distillation 或 retry 参数。
- 原生 `wrong: predicted=..., gold=...` 路径不被新的数学 solver 调用。
- 只有缺少最终答案格式时才恢复；正确/错误评分发生在全部提交密封之后，不能形成停止条件。
- 来源字段和诊断文本自动检测；旧库无来源证据不能直接激活。
- Canary 测试检查 prompt、router 输入、bank、retry、checkpoint 和 evaluator 顺序。
- 校验器只返回 correct/incorrect，无 gold 错误文本；测试阶段冻结 bank，不在线学习。
- `--dry-run` 始终 mock；实时 API 必须显式 opt-in，真实运行拒绝 synthetic bank/manifests。

## 与目标方案的明确边界

- 本阶段没有从真实 DeepSeek 正确解答训练出策略库，没有声称降低 token 或提升准确率。只有后续预先声明的真实实验能验证研究假设。
- 中等粒度策略依赖 LLM 后续抽象质量；当前规则聚类/特征是透明的第一版启发式，不是高召回语义检索。没有强制 embedding，暂未提供向量后端。
- Admission active 表示达到工程门槛，不表示已统计证明非劣；默认成本路由会进一步因置信界不足跳过。正式 bootstrap CI 与非劣检验尚未实现。
- 独立数学评分器支持数字、简单分数及保守规范化文本比较，平衡解析 boxed；不是完整的符号等价判定器。等价但格式不同的复杂 LaTeX 可能出现假阴性，需要在 dev 上声明并固定未来评分协议。
- 近重复检测覆盖数字掩码、前后缀 blocking 与字符相似度；无法证明排除所有语义近重复。
- Route C 只完成严格识别的整数四则任务。通用方程、几何或任意模型生成代码的安全验证不在当前覆盖范围，按指引作为第二优先级后续扩展。
- 监督参考解蒸馏和在线测试增长被明确拒绝，避免与默认协议混用。后续可以独立实现和授权。
- 数学特定策略尚未接入 MBPP 新策略机制；原生 HumanEval/MBPP 快照与离线验证能力保留，协议接口留有扩展点。
- 单策略成本归因可计算，多策略仅在显式 composition_tags 兼容时用于固定检索消融；成本路由不推断未经联合验证的组合收益。
- JSON hash/certificate 是内容一致性证据，不是防恶意本地编辑的安全签名。使用者负责来源文件的可信保管。

## 停止点

完成离线交付后停止，不自动开展真实实验或消费模型额度。下一步由用户决定真实 train-build/dev 子集、预算、模型设置和正式 holdout 协议。

最终交付机器可读状态：`DELIVERY_STATUS.json`。独立 wheel 安装实测已通过，证据位于 `WHEEL_INSTALL_CHECK.json`。
