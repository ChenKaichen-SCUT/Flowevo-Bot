# 01 — 603 条轨迹的提取瓶颈

603 traces → 9 traces → 9 traces → 9 traces → 9 traces → 6 traces → 6 traces → 4 traces → 4 traces → 2 programs。

最大损失是完整目标文法：603→9，丢失594（98.51%）。learning.extract_operations 在检查任何解题步骤前即以 parse_goal.state 过滤。9条的 transformation_spans 只是复制等式/同余片段；不能称为9条完整语义链。

历史逐步提取在267条轨迹中找到至少一项已验证操作；其中259条被V3目标文法拒绝。这是 parser 与过程提取耦合过早的直接证据；不证明这些操作均可构成完整任务宏。

A：没有任何轨迹被证明绝无复用价值，计0；未理解步骤保持unknown。B：594条目标入口损失，不等于594条已证明有复用结构。C：3条分别为e2、倒数和、对称有理式，来源不足。D：2条余式来源有结构差异，但标量DSL不支持多项式过程。E：这2条同时缺少余式目标证明规则（共因，不重复计入主类别）；V3的12个拟合候选被反例否决属于验证成功拒错，不是验证器失效。

重复结构按输出目标族统计：root_sum、root_product、remainder共6条；两来源/结构门槛后仍6条；DSL与prover联合门槛后4条；4条支持2条已认证标量程序。完整逐轨迹状态、失败点和真实来源步骤见JSONL。

### B: math_train_number_theory_210

What is the remainder of $8^6 + 7^7 + 6^8$ divided by 5?

Source solution excerpt (model-generated training trace):

```text
Compute modulo 5:

- \(8 \equiv 3 \pmod{5}\), so \(8^6 \equiv 3^6 \pmod{5}\).  
  Since \(3^2 \equiv 4 \equiv -1\), then \(3^6 = (3^2)^3 \equiv (-1)^3 \equiv -1 \equiv 4 \pmod{5}\).

- \(7 \equiv 2 \pmod{5}\), so \(7^7 \equiv 2^7 \pmod{5}\).  
  Powers of 2 mod 5 cycle: \(2,4,3,1\). Since \(7 \equiv 3 \pmod{4}\), \(2^7 \equiv 2^3 \equiv 8 \equiv 3 \pmod{5}\).

- \(6 \equiv 1 \pmod{5}\), so \(6^8 \equiv 1^8 \equiv 1 \pmod{5}\).

Thus,
\[
8^6+7^7+6^8 \equiv 4+3+1 \equiv 8 \equiv 3 \pmod{5}.
\]

The answer is 3.
```

Failure: {'task_id': 'math_train_number_theory_210', 'reason': 'no_supported_complete_grammar', 'stage': 'goal_extraction', 'goal_state': 'fallback'}.

### C: math_train_algebra_558

Let the reciprocals of the roots of $5x^2 + 3x + 4$ be $\alpha$ and $\beta$. Evaluate $\alpha + \beta$.

Source solution excerpt (model-generated training trace):

```text
Let the roots of \(5x^2+3x+4\) be \(r_1\) and \(r_2\).  
Then the reciprocals are

\[
\alpha=\frac1{r_1}, \qquad \beta=\frac1{r_2}.
\]

We need

\[
\alpha+\beta=\frac1{r_1}+\frac1{r_2}
=\frac{r_1+r_2}{r_1r_2}.
\]

For the quadratic \(5x^2+3x+4=0\),

\[
r_1+r_2=-\frac{3}{5}, \qquad r_1r_2=\frac{4}{5}.
\]

Thus,

\[
\alpha+\beta=\frac{-\frac35}{\frac45}=-\frac34.
\]

The answer is \(\boxed{-\frac34}\).
```

Failure: family=reciprocal_sum.

### D/E: math_train_intermediate_algebra_891

Determine the remainder when $(x^4-1)(x^2-1)$ is divided by $1+x+x^2$.

Source solution excerpt (model-generated training trace):

```text
Work modulo \(1+x+x^2\). Since
\[
x^2+x+1=0 \implies x^2\equiv -x-1,
\]
we also get
\[
x^3\equiv x(-x-1)=-x^2-x\equiv -(-x-1)-x=1,
\]
so
\[
x^4\equiv x.
\]

Now compute:
\[
(x^4-1)(x^2-1)\equiv (x-1)((-x-1)-1)
\]
\[
=(x-1)(-x-2)
=-x^2-x+2.
\]
Using \(x^2\equiv -x-1\),
\[
-x^2-x+2\equiv -(-x-1)-x+2=x+1-x+2=3.
\]

Thus the remainder is \(3\).

The answer is 3.
```

Failure: family=polynomial_remainder.

本轮选择：从完整目标入口解耦步骤提取，优先研究训练数据反复出现的整数同余计算。多项式/有理式/约束集类型暂缓；不先堆砌算子。
