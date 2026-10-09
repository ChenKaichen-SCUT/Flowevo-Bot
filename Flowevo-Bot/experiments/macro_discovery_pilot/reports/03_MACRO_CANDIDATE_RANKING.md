# 候选排序与独立覆盖

| family | unique_source_tasks | chosen | reason |
| --- | --- | --- | --- |
| algebraic_identity | 21 | False | 仅低层恒等式或数值子操作；尚无可靠问题级触发与替代预算证据，本轮不付费 |
| constrained_equation | 361 | False | unknown/上下文未证明 |
| exact_numeric_evaluation | 224 | False | 仅低层恒等式或数值子操作；尚无可靠问题级触发与替代预算证据，本轮不付费 |
| polynomial_expansion | 11 | False | 仅低层恒等式或数值子操作；尚无可靠问题级触发与替代预算证据，本轮不付费 |
| polynomial_factorization | 19 | False | 仅低层恒等式或数值子操作；尚无可靠问题级触发与替代预算证据，本轮不付费 |
| polynomial_remainder | 2 | True | 结构多样且可独立验证，进入小样本 |
| rational_normalization | 6 | False | 仅低层恒等式或数值子操作；尚无可靠问题级触发与替代预算证据，本轮不付费 |
| root_invariants | 6 | True | 结构多样且可独立验证，进入小样本 |
| unparsed | 303 | False | unknown/上下文未证明 |

| macro_id | source_tasks | eligible_original_dev | eligible_supplement_train | selected | prompt_overhead_estimated |
| --- | --- | --- | --- | --- | --- |
| root_invariants | 6 | 6 | 12 | 10 | 96 |
| polynomial_remainder | 2 | 5 | 1 | 4 | 66 |

完整筛选分母6430：1186条尚未使用的原dev题 +5244条尚未使用的原train题。预筛含roots/remainder的278题并运行严格识别器；不满足词面必要条件的其他题不可能命中当前实现。剔除旧700训练、350开发及20V2题；使用数字归一化+相似度≥0.9、余式多项式支撑集结构、简单根和/根积目标类型排除模板重复。选中集合内再去重复。题单按原dev优先、公开难度及ID固定排序，无label或新正确率参与筛选。根宏补充的unused train题在本轮正式保留为dev，今后不再用于建库。

覆盖率不是MATH测试总体覆盖；按当前严格问题文法和去重准则测得。宏的eligible数也不保证一定节省推理。只有14题符合本轮独立性及结构多样性要求，余式未凑满10题，不放松guard补足。

Compact约96/66 tokens（UTF8 bytes/4估计，不是官方tokenizer精确值；实际API输入差额另计），阈值100。预计收益：根只可能替代对称量推导，仍要LLM解释目标；余式可替代完整求解。局部计算和核验成本以秒记录，均0额外API；宏生成由代码实现，本轮生成LLM tokens=0。完整采集成本795435 tokens，增量复用成本0。盈亏平衡需用新配对数据估计，付费前不声称收益。

高频加减乘除不推荐；仅有factor/reduce/simplify关键词不作为模式证据。其余学科的自然语言证明和组合约束尚未取得安全的中层可执行表示，因此没有为了覆盖七科而制作泛化工具菜单。
