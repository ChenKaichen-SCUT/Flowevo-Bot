# 08 — 机制归因与成本

**RQ1**：在很小的人工DSL内自动组合成功。4来源的真实中间表达式约束选出了四步序列，优于仅拟合最终数字；但只有5个可选组合，算法/类型/守卫基本由人工限定，未学会新的高层数学策略。所有anti-unification来源对根结构不匹配，不能把typed hole当作强结构归纳成果。

**RQ2**：仅工程集一题验证了两因子乘积向既有三因子来源的项数和措辞迁移；选择、确认无V4任务命中，其他结构未独立验证。根和确认成功属于V3。

**RQ3**：未优于人工工具。匹配相同基础原语/语义时，新程序与B完全相同，C新增覆盖0，也无本地成本优势。没有测量人工工时，不主张工程建库成本减少。

**RQ4**：没有MATH全分布摊销证据。历史700训练调用实际795435tokens（其中603成功子集518212，不能重复相加）；本轮复用，新增建库API0。基于已测“C相对B新增接管率=0”，无法通过额外免LLM调用回收任何新增成本。B/C相对A的实际平均节省S未测，p也受历史筛查影响，不能把N≥T_build/(p×S)代入猜测数字当作实测。大规模学习和算子维护的人工/本地费用也未定价。

**RQ5**：停止当前路线的规模化token收益主张，保留负结果与原型。继续盲目增加目标文法和手工算子会增加人工能力，无法检验原问题中的自动结构学习贡献。

| component | status | calls | total_tokens | local_wall_seconds | note |
|---|---|---|---|---|---|
| V4_new_model_calls | NOT RUN | 0 | 0 | None | no API experiment; no observed savings |
| historical_700_source_acquisition | previously_paid_reused | 700 | 795435 | None | includes unsuccessful/unknown traces; not newly billed |
| selected_603_source_subset | subset_do_not_add_again | 603 | 518212 | None | subset of historical acquisition; new source acquisition = 0 |
| V4_extraction_and_synthesis | executed_offline | 0 | 0 | 0.30204335699090734 | includes synthesis; do not add synthesis again |
| V4_synthesis_and_proof_subset | subset_do_not_add_again | 0 | 0 | 0.12651499098865315 | exact typed search with certificates |
| V4_coverage_and_grading | executed_offline | 0 | 0 | 2.852687365957536 | 12 processes; monetary CPU cost not instrumented |


本轮API实际费用为0；历史美元/人民币费用没有价格账单，不补写推算。代码搜索/验证的本地秒数是实际计时，不能直接转换为API tokens。完整source、config、bank与代码hash见run_manifest与freeze记录。
