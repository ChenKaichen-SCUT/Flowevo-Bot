# FlowEvo 无 gold 反思 vs Flowevo-Bot：MATH 500 题实测

本地 MATH 测试集按学科和难度分层抽样，非标准 MATH-500。两者使用同一批题、相同模型设置和冻结训练历史。

| 方法 | 正确题数 | 正确率 | 输入 token | 输出 token | 测试总 token | 每题平均 token |
|---|---:|---:|---:|---:|---:|---:|
| FlowEvo（关闭 gold 反思） | 462/500 | 92.40% | 169,251 | 472,704 | 641,955 | 1283.91 |
| Flowevo-Bot（成本感知模式） | 464/500 | 92.80% | 62,237 | 460,783 | 523,020 | 1046.04 |

Flowevo-Bot 正确率差值 +0.40 个百分点；测试 token 节省 118,935（18.53%）。

共同训练历史生成：795,435 token；Bot 额外蒸馏与验证：274,296 token。包括建库后，FlowEvo 共 1,437,390，Bot 共 1,592,751 token。

训练题 700，独立验证题 350；首次正确且无 gold 暴露的历史 627 条；策略状态 {'quarantine': 9, 'shadow': 3}。

FlowEvo 路由：{'base': 39, 'history': 461}；Flowevo-Bot 路由：{'base': 500}。未使用策略的题由原始模型直接求解，不代表策略复用有效。

每题只生成一次，不依据 gold 重试，不从测试题入库。API 并发上限 64，评分进程 12，本地 CPU affinity 12 核；temperature=0，max_output_tokens=4096。
FlowEvo 使用原仓库 CodeSkillLibrary 与 build_goldfree_math_prompt 导出的原生 prompt，共用 API 传输及评分器，避免客户端和评分差异。
评分：math-verify 0.8.0 的符号等价验证，加保守文本/分数相等；评分只在提交封存后执行。另保留严格字符串归一化分数。
模型输出被截断的题按错误统计，token 全部计入。每次 API usage 的输入和输出 token 都保存，缺失 usage 会显式标为估算。
本次为单次配对样本结果，不能据此断言普遍显著优势；测试集曾经的其他暴露情况未知。

逐题 CSV：paired_results.csv；完整设置和成本：comparison.json；逐请求 prompt/response/usage：flowevo/calls.json 和 flowevo_bot/calls.json。

<!-- POST_RUN_AUDIT -->

## 分学科结果

| 学科 | 题数 | FlowEvo 正确 | Bot 正确 | FlowEvo token | Bot token |
|---|---:|---:|---:|---:|---:|
| algebra | 78 | 76 | 76 | 56,502 | 39,554 |
| counting_probability | 52 | 48 | 49 | 66,383 | 55,676 |
| geometry | 53 | 48 | 46 | 90,781 | 79,563 |
| intermediate_algebra | 103 | 88 | 90 | 179,462 | 152,681 |
| number_theory | 59 | 58 | 58 | 61,795 | 48,122 |
| prealgebra | 98 | 91 | 89 | 93,777 | 77,484 |
| precalculus | 57 | 53 | 56 | 93,255 | 69,940 |

配对样本中，只有 FlowEvo 正确 8 题，只有 Bot 正确 10 题。McNemar 双侧精确检验 p=0.8145；正确率差值的配对近似 95% 区间为 [-1.26, 2.06] 个百分点。本次 0.4 个百分点差异不足以认定准确率提升。

测试 token 节省的 89.98% 来自输入减少。Bot 本轮所有测试题均未注入策略，不能将收益归因于策略复用。

350 是独立验证题候选池；实际匹配到 39 道题，执行 39 对 base/skill 共 78 次验证调用。8 个策略缺少匹配验证样例，1 个观察到有害案例，另外 3 个未满足收益/证据要求。

完整实验实际请求 1,802 次，共 2,234,706 token；这里共同训练历史只计算一次。按每套方法独立部署分别计算时，使用正文的两套端到端成本。

DeepSeek 默认思考模式为 enabled/high；请求中的 temperature=0 在该模式下不生效，输出 token 包含思考 token。参考 [DeepSeek 官方文档](https://api-docs.deepseek.com/guides/thinking_mode/)。符号评分器来源：[Hugging Face Math-Verify](https://github.com/huggingface/Math-Verify)。

核对通过：每套 500 个相同题号、封存答案、独立真实请求和原始 provider usage；总数与逐题/逐请求账本一致；0 次估算；测试期间代码及库哈希未变化；未发现密钥泄露。离线检验 54+2 项通过。
