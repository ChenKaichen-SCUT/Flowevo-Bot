# DeepSeek Flash 单次16384强基线

请求/返回model均为`deepseek-flash`；实际每次返回的`system_fingerprint`保留在raw与api账本，服务端权重版本不能锁定。沿用FlowEvo的原生数学CoT消息：system为“You are an expert programmer and mathematician.”，user为公开题目加分步求解和终答标记。Gold feedback、gold reflection、Skill检索/注入均关闭。

每题一次16384上限，默认thinking开启、reasoning effort high；参数省略，实际响应有reasoning字段和reasoning_tokens。请求temperature=0，但[官方思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/)说明该模式下此参数不生效；无可用seed。候选是独立HTTP调用，不宣称固定种子可重现服务端采样。API峰值64、本地12。

| 划分 | 题数 | 冻结V3判对 | 数学复核后确认正确 | 截断 | 语义未定 | 复核后准确率下界–上界 |
|---|---|---|---|---|---|---|
| validation | 119 | 112 | 118 | 1 | 0 | 99.16%–99.16% |
| test | 486 | 460 | 479 | 5 | 2 | 98.56%–98.97% |
| all | 605 | 572 | 597 | 6 | 2 | 98.68%–99.01% |

| 学科 | 题数 | V3判对 | 复核确认正确 | 截断 | 未定 | 复核准确率下界–上界 |
|---|---|---|---|---|---|---|
| Counting & Probability | 123 | 120 | 122 | 1 | 0 | 99.19%–99.19% |
| Number Theory | 154 | 146 | 152 | 2 | 0 | 98.70%–98.70% |
| Prealgebra | 193 | 185 | 192 | 1 | 0 | 99.48%–99.48% |
| Precalculus | 135 | 121 | 131 | 2 | 2 | 97.04%–98.52% |

验证先求解和审计；选择器输出在新增候选评分前封存；`METHOD_FROZEN_FOR_TEST.json`随后冻结方法，再正式请求测试集479个新输出。另7个测试输出复用上一轮无条件direct16384：请求体完全相同，逐份响应哈希可核实。没有复用按失败条件触发的高预算重试，也没有根据本轮正确性补采样。

| 划分/风险层 | 确认正确/题数 | 未定 | 截断 |
|---|---|---|---|
| validation/strict_clean | 82/83 | 0 | 1 |
| validation/recorded_or_near_exposure_risk | 36/36 | 0 | 0 |
| test/strict_clean | 320/327 | 2 | 5 |
| test/recorded_or_near_exposure_risk | 159/159 | 0 | 0 |

MathEvaluator-V3源码树哈希`ddf574ce8adacc73a91e59370cf0310daf82bd192bba66adcadfff563a9007e6`，配置哈希`6ac932c2464edb410709e5e30e373f354d3c38b8b15321c31a0914701211fab6`，版本3.0.0、4秒/题、12workers。本轮没有修改评分器。V3非正确项逐份补充数学复核证据；完整输出、thinking、finish_reason、tokens、Unknown原因、复核分轨见baseline_results/raw/grading。

本轮未给测试集运行Pass@4选择器，因此候选选择的提高只能称验证集探索结果，不能称独立测试集算法提升。已知历史暴露同样限制泛化主张。
