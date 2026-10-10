# 剩余失败分类与数学证据

27 道最终分类：{"recovered_correct": 25, "still_truncated": 2}。

| task_id | level | selected_budget | category | answer | reasoning_tokens |
| --- | --- | --- | --- | --- | --- |
| math_test_geometry_66 | Level 5 | 16384 | still_truncated | None | 16384 |
| math_test_intermediate_algebra_253 | Level 4 | 16384 | still_truncated | None | 16384 |


完整且确认数学错误的候选集在 remaining_true_failures.jsonl；包括题目/难度、候选完整解答、gold、原始和新 usage、全部请求来源以及人工数学复核。截断和解析 unknown 不列入“可靠数学错误”集合。

两道剩余题均为 **16,384 reasoning tokens、可见 content 为空、finish_reason=length**，故仍按未完成计分，不从隐藏推理中捞取答案。

- `math_test_geometry_66`：菱形卷圆柱。raw reasoning 反复重审侧边接缝、螺线和圆周/高度关系，多次得到参考数值却没有切换到最终作答。独立核验：圆周6 ⇒ r=3/π，h=6 sinθ，体积6=(54/π)sinθ ⇒ sinθ=π/9。这是观察到的反复推敲和答案未输出，不是已确认不会解。
- `math_test_intermediate_algebra_253`：两条抛物线相切。隐藏推理反复讨论题意，且其疑虑有数学依据。相交条件给出(x−y)(x+y+1)=0，相同切线斜率给出4xy=1。精确求解有 k=1/4、接触点(1/2,1/2)，以及 k=−3/4、接触点(−1/2,−1/2)。后者两斜率均为−1，共同切线y=−x−1，且另有(3/2,3/2)横截交点。代入得到交点方程因式分解(2x−3)(2x+1)^3/16，显示局部三重接触。参考仅列1/4，隐含“唯一接触且不横穿”的意图；按局部微分切触定义，−3/4也成立。此项属于新增的题意/参考歧义标记，**不新增一次评分纠正**，因为模型没有提交最终答案。

这与9道已纠正案例中的奇函数题不同：后者确实提交了能从公开条件证明的合法有序对；这里的两题最终正文都为空。不能把隐藏推理中的某个值追认为最终答案，也不能把参考答案未覆盖的合理解释直接诊断为模型数学错误。

详细数学复核、证据字符位置、原始响应哈希和 SymPy 精确检查见 evidence/manual_math_review.json、manual_review_run.log。参考歧义的新标记为1，评分变化仍为0。`remaining_true_failures.jsonl` 为合法空 JSONL，表示0条可靠完整错误，而不是漏写文件。本次仅诊断，不混入新算法、提示变更或验证器重试。
