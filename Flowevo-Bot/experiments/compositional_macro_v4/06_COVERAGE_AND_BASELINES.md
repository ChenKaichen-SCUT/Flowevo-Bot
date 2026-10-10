# 06 — 同先验人工与自动对照

A Bot-NoBank未运行。B和C共享V4完整目标文法、可用原语、预算、Guard及独立验证器，并继续保留冻结V3路由。B的模运算顺序是人工固定；C真正执行合成bank内的DSL序列，搜索不读取MANUAL_PROGRAM（测试中破坏人工常量仍合成同一结果）。二者最后恰好选择同一序列。

| split | method | denominator | parsed | guards | full | correct | fallback | local_seconds |
|---|---|---|---|---|---|---|---|---|
| dev-engineering | B | 1184 | 1 | 1 | 1 | 1 | 1183 | 3.5235019660321996 |
| dev-engineering | C | 1184 | 1 | 1 | 1 | 1 | 1183 | 0.20456169836688787 |
| dev-selection | B | 1229 | 0 | 0 | 0 | 0 | 1229 | 1.9304063139134087 |
| dev-selection | C | 1229 | 0 | 0 | 0 | 0 | 1229 | 1.751245518680662 |
| heldout-confirmation | B | 2383 | 2 | 2 | 2 | 2 | 2381 | 2.7447747014812194 |
| heldout-confirmation | C | 2383 | 2 | 2 | 1 | 1 | 2382 | 2.1311926533817314 |


| split | both | B_only | C_only | neither |
|---|---|---|---|---|
| dev-engineering | 1 |  |  | 1183 |
| dev-selection |  |  |  | 1229 |
| heldout-confirmation | 1 | 1 |  | 2381 |


完整执行正确只是已提交子集正确，不是全池准确率；所有其他题未调用LLM，结果保持null。确认B2/2383=0.0839%覆盖，C1/2383=0.0420%，C新增0。V4新宏工程B/C各1、选择各0、确认各0；B独有来自旧V3库差异。整个新池B3/4796、C2/4796，其中V4额外工具仅1/4796（描述性0.02085%），不是原始MATH总体估计。

数学误接管0；没有证据给出未触发题的准确率。回退细分见summary JSON：主要semantic_unsupported_whole_question/旧V3无完整文法；确认C有1题no_certified_automatic_macro（DSL/库覆盖缺失），没有实际Guard失败或验证失败。无中间结果注入LLM。

表中总local_seconds仅描述运行开销：导入、缓存、路由顺序会偏移B/C，不能用它宣称算法加速。预热且100次交替配对的唯一V4独立开发命中，B中位40.2245µs，C40.9845µs，C/B=1.0189；未达≤0.8的成本门槛，样本亦极少。CPU计时不是推理token收益。
