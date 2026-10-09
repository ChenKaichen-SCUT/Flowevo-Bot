# 评分器修复与历史复核

V2 使用独立离线评分入口 `v2/evaluator.py`。原始评分和旧评分器保留用于历史重放；V2 研究入口全部使用修复后的评分器。
全部提交校验 seal 后才打开标签；solver、Trigger、Router 不接收 gold 或判分反馈。新增测试包含未封存记录阻止 label IO、负号、未知表达式、集合/有序对/区间端点、截断与嵌套分数。

选择位置最后的显式最终答案或 balanced boxed，修复 first-answer 错取。题面明确给出单位时才移除对应尾随单位；数字/符号由 Math-Verify/SymPy 在最多12个进程中限时解析，禁用字符串 fallback。集合与有序对分开，不能安全判定的文本/格式记 unknown。截断记预算失败并保留所有 usage，绝不判对。

已知两例：geometry_367 的 `18 square centimeters` 对金标 `18` 经题面单位约束规范化为正确；precalculus_250 的末尾 `(A)` 被正确提取，与金标选项一致。完整例子和原始模型解答在 CSV/JSON 内。仍不支持任意自然语言、所有单位和多种选项+表达式混写；unknown 不等于数学错误。

以下是**历史离线复核**，不构成本轮新增测试成绩，原始正确数不变。保守解析新增 unknown，因此不可只看 rechecked_true 数就宣称模型准确率下降。
| 历史组 | n | 原始正确 | 复核确认正确 | unknown |
| --- | --- | --- | --- | --- |
| dev_base | 39 | 32 | 33 | 1 |
| dev_counting_probability_669101e83d955915 | 18 | 16 | 16 | 0 |
| dev_geometry_ee3896b4fd724c16 | 10 | 8 | 8 | 0 |
| dev_intermediate_algebra_4a5d6d54c25d8d89 | 1 | 1 | 1 | 0 |
| dev_precalculus_5193e2e6c7ae508d | 10 | 7 | 8 | 1 |
| flowevo | 500 | 462 | 447 | 21 |
| flowevo_bot | 500 | 464 | 448 | 22 |
| train | 700 | 627 | 603 | 35 |

共复核 1778 份封存答案，86 条评分状态不同。全部差异实例如下；完整题面、gold、解答和 seal 见 `data/scoring_disagreements.csv`。

| 任务/方法 | 原→复核 | 提取答案 | gold | 原因 |
| --- | --- | --- | --- | --- |
| math_train_counting_probability_163/train | False → None | \( \frac{1}{29{,}322{,}216} \) | \dfrac{1}{29,\!322,\!216} | unparsed_expression |
| math_train_geometry_106/train | False → None | 3 trips | 3 | unparsed_expression |
| math_train_counting_probability_42/train | True → None | B | \text{B} | unparsed_expression |
| math_train_geometry_621/train | False → None | \textbf{(A)} | s^2 \le 8r^2 | unparsed_expression |
| math_train_geometry_597/train | False → True | [E] \(\frac{9}{\pi^2}(\sqrt{3}+3)\) | \frac{9}{\pi^2}(\sqrt{3}+3) | last_final_answer_and_structured_equivalence:symbolic |
| math_train_geometry_582/train | True → None | (B) \(\{4,5,7\}\) | \{4,5,7\} | answer_type_ambiguity |
| math_train_geometry_728/train | True → None | \(164\pi\) | 164 \pi \mbox{ square feet} | unparsed_expression |
| math_train_geometry_598/train | False → None | \textbf{(D)}\ AB=9,\ CD=4 | AB=9, CD=4 | unparsed_expression |
| math_train_intermediate_algebra_229/train | True → None | odd | \text{odd} | unparsed_expression |
| math_train_intermediate_algebra_460/train | True → None | two lines | \text{two lines} | unparsed_expression |
| math_train_intermediate_algebra_612/train | False → None | 1, 9 | 9 | answer_type_ambiguity |
| math_train_number_theory_766/train | False → None | 8:34 PM | 8\!:\!34 \text{ p.m.} | unparsed_expression |
| math_train_number_theory_664/train | True → None | \(\textbf{(D)}\ 8\) | 8 | unparsed_expression |
| math_train_prealgebra_124/train | True → None | 89, 88, 85, 73, 70 | 89, 88, 85, 73, 70 | unparsed_expression |
| math_train_number_theory_322/train | True → None | 7 | 7 \text{ distinct integers} | unparsed_expression |
| math_train_prealgebra_61/train | True → None | \(\frac{2}{15}\) gallons | \frac{2}{15} | unparsed_expression |
| math_train_prealgebra_644/train | False → True | 675 square centimeters | 675 | question_unit_removed |
| math_train_prealgebra_587/train | True → None | 99 cents | 99 | unparsed_expression |
| math_train_prealgebra_894/train | True → None | 18 | 18 \text{ degrees} | unparsed_expression |
| math_train_prealgebra_174/train | True → None | August | \text{August} | unparsed_expression |
| math_train_precalculus_203/train | True → None | \(\begin{pmatrix} -2 \\ 0 \\ 6 \end{pmatrix}\) | \begin{pmatrix} -2 \\ 0 \\ 6 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_212/train | True → None | \(\begin{pmatrix}0 & 0 \\ 0 & 0\end{pmatrix}\) | \begin{pmatrix} 0 & 0 \\ 0 & 0 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_262/train | True → None | \(\frac{\pi}{5}\) to the right | \frac{\pi}{5} | unparsed_expression |
| math_train_precalculus_264/train | True → None | \(\begin{pmatrix} -2 & -7 \\ 5 & -7 \end{pmatrix}\) | \begin{pmatrix} -2 & -7 \\ 5 & -7 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_235/train | True → None | \(\begin{pmatrix} -10 \\ 6 \end{pmatrix}\) | \begin{pmatrix} -10 \\ 6 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_376/train | True → None | \(\begin{pmatrix}6\\-33\end{pmatrix}\) | \begin{pmatrix} 6 \\ -33 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_364/train | False → None | \begin{pmatrix} \frac{4}{13} & -\frac{6}{13} \\[2pt] -\frac{6}{13} & \frac{9}{13} \end{pmatrix} | \begin{pmatrix} 4/13 & -6/13 \\ -6/13 & 9/13 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_228/train | True → None | \begin{pmatrix}1\\3\\1\end{pmatrix} | \begin{pmatrix} 1 \\ 3 \\ 1 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_428/train | True → None | \(\begin{pmatrix} 16 & -4 \\ 37 & -13 \end{pmatrix}\) | \begin{pmatrix} 16 & -4 \\ 37 & -13 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_251/train | True → None | \(\begin{pmatrix}0&0&0\\0&0&0\\0&0&0\end{pmatrix}\) | \begin{pmatrix} 0 & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_459/train | True → None | \(\begin{pmatrix}\frac{7}{17}&-\frac{3}{17}\\\frac{1}{17}&\frac{2}{17}\end{pmatrix}\) | \begin{pmatrix} 7/17 & -3/17 \\ 1/17 & 2/17 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_431/train | True → None | \(\begin{pmatrix}0 & 1 & 0\\1 & 0 & 0\\0 & 0 & 2\end{pmatrix}\) | \begin{pmatrix} 0 & 1 & 0 \\ 1 & 0 & 0 \\ 0 & 0 & 2 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_532/train | True → None | \(\begin{pmatrix}-1 & -5\\1 & 4\end{pmatrix}\) | \begin{pmatrix} -1 & -5 \\ 1 & 4 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_399/train | False → None |  \mathbf R= \begin{pmatrix} \frac13&-\frac23&\frac23\\ -\frac23&\frac13&\frac23\\ \frac23&\frac23&\frac13 \end{pmatrix} | \begin{pmatrix} \frac{1}{3} & -\frac{2}{3} & \frac{2}{3} \\ -\frac{2}{3} & \frac{1}{3} & \frac{2}{3} \\ \frac{2}{3} & \frac{2}{3} & \frac{1}{3} \end{pmatrix} | unparsed_expression |
| math_train_precalculus_700/train | True → None | \(\begin{pmatrix} 7 \\ -13 \end{pmatrix}\) | \begin{pmatrix} 7 \\ -13 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_728/train | True → None | \begin{pmatrix}0\\ \frac{1}{11}\end{pmatrix} | \begin{pmatrix} 0 \\ 1/11 \end{pmatrix} | unparsed_expression |
| math_train_precalculus_5/train | False → None | \(a\in\mathbb R\setminus\{3\}\), i.e. all real numbers except \(3\) | (-\infty,3) \cup (3,\infty) | unparsed_expression |
| math_test_algebra_673/flowevo | False → None | 2000 calories | 2000 | unparsed_expression |
| math_test_algebra_602/flowevo | True → None | 65 | 65 \text{ children tickets } | unparsed_expression |
| math_test_algebra_1097/flowevo | True → None | 25 feet | 25 \text{ ft} | question_unit_removed |
| math_test_algebra_884/flowevo | True → None | \(-3600\) (a decrease of \(3600\) square units) | 3600 | unparsed_expression |
| math_test_algebra_781/flowevo | False → None | 6 sticks | 6 | unparsed_expression |
| math_test_geometry_240/flowevo | True → None | 864 square inches | 864 \mbox{ inches}^2 | question_unit_removed |
| math_test_counting_probability_411/flowevo | False → None | \frac{12}{5525} | \frac{12}{5,\!525} | unparsed_expression |
| math_test_intermediate_algebra_877/flowevo | False → True | (A) | \text{(A)} | last_final_answer_and_structured_equivalence:option_label |
| math_test_prealgebra_334/flowevo | True → None | 12 | 12 \text{ gm} | unparsed_expression |
| math_test_prealgebra_534/flowevo | True → None | 20 | 20\text{ degrees} | unparsed_expression |
| math_test_prealgebra_789/flowevo | False → None | 24 cones | 24 | unparsed_expression |
| math_test_prealgebra_457/flowevo | True → None | Devon | \text{Devon} | unparsed_expression |
| math_test_precalculus_207/flowevo | True → None | \(\begin{pmatrix} 7 \\ -2 \end{pmatrix}\) | \begin{pmatrix} 7 \\ -2 \end{pmatrix} | unparsed_expression |
| math_test_prealgebra_607/flowevo | True → None | Navin | \text{Navin} | unparsed_expression |
| math_test_precalculus_104/flowevo | True → None | 0 \text{ and } 4 | 0,4 | unparsed_expression |
| math_test_prealgebra_112/flowevo | True → None | \(12^\circ\) | 12\text{ degrees} | unparsed_expression |
| math_test_precalculus_101/flowevo | True → None | \(\begin{pmatrix}0&0\\0&1\end{pmatrix}\) | \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix} | unparsed_expression |
| math_test_precalculus_335/flowevo | True → None | \begin{pmatrix} \frac{\sqrt2}{2} & \frac{\sqrt2}{2}\\ -\frac{\sqrt2}{2} & \frac{\sqrt2}{2} \end{pmatrix} | \begin{pmatrix} 1/\sqrt{2} & 1/\sqrt{2} \\ -1/\sqrt{2} & 1/\sqrt{2} \end{pmatrix} | unparsed_expression |
| math_test_precalculus_386/flowevo | True → None | \(\begin{pmatrix}0&1&0\\0&0&1\\1&1&1\end{pmatrix}\) | \begin{pmatrix} 0 & 1 & 0 \\ 0 & 0 & 1 \\ 1 & 1 & 1 \end{pmatrix} | unparsed_expression |
| math_test_precalculus_237/flowevo | True → None | x=0 \text{ or } x=3a | 0,3a | unparsed_expression |
| math_test_precalculus_162/flowevo | False → None | 9° | 9^\circ | unparsed_expression |
| math_test_precalculus_534/flowevo | True → None | \(\begin{pmatrix}-6\\9\end{pmatrix}\) | \begin{pmatrix} -6 \\ 9 \end{pmatrix} | unparsed_expression |
| math_test_algebra_673/flowevo_bot | False → None | 2000 calories | 2000 | unparsed_expression |
| math_test_algebra_602/flowevo_bot | True → None | 65 | 65 \text{ children tickets } | unparsed_expression |
| math_test_algebra_1097/flowevo_bot | True → None | 25 feet | 25 \text{ ft} | question_unit_removed |
| math_test_algebra_884/flowevo_bot | False → None | 3600 square units less | 3600 | unparsed_expression |
| math_test_geometry_154/flowevo_bot | True → None | 20 square inches | 20 | unparsed_expression |
| math_test_geometry_240/flowevo_bot | True → None | 864 | 864 \mbox{ inches}^2 | unparsed_expression |
| math_test_geometry_165/flowevo_bot | False → None | 40° | 40^\circ | unparsed_expression |
| math_test_counting_probability_411/flowevo_bot | False → None | \frac{12}{5525} | \frac{12}{5,\!525} | unparsed_expression |
| math_test_prealgebra_200/flowevo_bot | True → None | \(1\frac{9}{10}\) cups of flour | 1\frac{9}{10} | unparsed_expression |
| math_test_prealgebra_334/flowevo_bot | False → None | 12 grams | 12 \text{ gm} | unparsed_expression |
| math_test_prealgebra_435/flowevo_bot | False → None | 2.50 dollars | \$2.50 | unparsed_expression |
| math_test_prealgebra_534/flowevo_bot | True → None | 20 degrees | 20\text{ degrees} | question_unit_removed |
| math_test_prealgebra_457/flowevo_bot | True → None | Devon | \text{Devon} | unparsed_expression |
| math_test_prealgebra_607/flowevo_bot | True → None | Navin | \text{Navin} | unparsed_expression |
| math_test_precalculus_101/flowevo_bot | True → None | \begin{pmatrix}0&0\\0&1\end{pmatrix} | \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix} | unparsed_expression |
| math_test_precalculus_207/flowevo_bot | True → None | \(\begin{pmatrix}7\\-2\end{pmatrix}\) | \begin{pmatrix} 7 \\ -2 \end{pmatrix} | unparsed_expression |
| math_test_precalculus_104/flowevo_bot | True → False | \(k=0,4\) | 0,4 | last_final_answer_and_structured_equivalence:structured |
| math_test_precalculus_237/flowevo_bot | True → None | x=0 \text{ or } x=3a | 0,3a | unparsed_expression |
| math_test_precalculus_335/flowevo_bot | True → None | \(\begin{pmatrix}\frac{\sqrt2}{2} & \frac{\sqrt2}{2}\\-\frac{\sqrt2}{2} & \frac{\sqrt2}{2}\end{pmatrix}\) | \begin{pmatrix} 1/\sqrt{2} & 1/\sqrt{2} \\ -1/\sqrt{2} & 1/\sqrt{2} \end{pmatrix} | unparsed_expression |
| math_test_precalculus_386/flowevo_bot | True → None | \(\begin{pmatrix}0&1&0\\0&0&1\\1&1&1\end{pmatrix}\) | \begin{pmatrix} 0 & 1 & 0 \\ 0 & 0 & 1 \\ 1 & 1 & 1 \end{pmatrix} | unparsed_expression |
| math_test_precalculus_534/flowevo_bot | True → None | \begin{pmatrix}-6\\9\end{pmatrix} | \begin{pmatrix} -6 \\ 9 \end{pmatrix} | unparsed_expression |
| math_test_prealgebra_112/flowevo_bot | True → None | \(12^\circ\) | 12\text{ degrees} | unparsed_expression |
| math_test_prealgebra_498/flowevo_bot | False → None | 36° | 36^\circ | unparsed_expression |
| math_train_geometry_367/dev_base | False → True | 18 square centimeters | 18 | question_unit_removed |
| math_train_precalculus_250/dev_precalculus_5193e2e6c7ae508d | False → True | (A) | \text{(A)} | last_final_answer_and_structured_equivalence:option_label |
| math_train_precalculus_471/dev_base | False → None | \(4\) or \(-4\) | -4 | unparsed_expression |
| math_train_precalculus_471/dev_precalculus_5193e2e6c7ae508d | False → None | \(\pm 4\) | -4 | answer_type_ambiguity |
