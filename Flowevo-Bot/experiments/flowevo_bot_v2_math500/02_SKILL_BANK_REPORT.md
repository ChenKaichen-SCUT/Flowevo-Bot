# Skill Bank V2

旧库12条：0 active、3 shadow、9 quarantine；全部原样保留。新库仅蒸馏2条：counting_probability 1条、intermediate_algebra 1条；均为shadow，0 active。没有足够证据展示3–5条有效技能，不补造卡片。

| 技能 | dev n | benefit / harm | 每次平均节省 | 节省95%下界 | 100次净收益（候选成本） | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| S04_v2_591ca36f47b0 | 10 | 1 / 0 | 85 | -389.24 | -56802 | shadow |
| S07_v2_3602556c556a | 10 | 0 / 0 | -370.1 | -602.16 | -82171.0 | shadow |

## S04_v2_591ca36f47b0 · Constrained Counting by Complement or Disjoint Cases

1. Determine the counting model: whether order matters, whether items are distinct or repeated, and allowed repetitions; identify the total space and constraints.
2. Partition into disjoint, exhaustive cases, often valid cases directly or total minus complement/forbidden cases; check pairwise overlaps and exact coverage.
3. Count each case with ordered choices, permutations, products, or multinomial coefficients, respecting constraints and fixed positions.
4. Combine case counts by addition/subtraction. For symmetry, divide by orbit size only after proving equal orbit sizes or a free action; otherwise count fixed points/cases.

短策略：

> Model count: fix order, distinctness, repetition. Count all, or split valid into disjoint exhaustive cases (or total minus complement). Check overlaps exactly once. Use permutations/products/multinomials per case. For symmetry, divide only if all orbits equal/free; otherwise count fixed cases. Sum/subtract cases.

来源：math_train_counting_probability_679, math_train_counting_probability_715, math_train_counting_probability_195, math_train_counting_probability_323, math_train_counting_probability_690, math_train_counting_probability_265。状态 **shadow**；本轮实际shadow注入10次，生产注入0次。

## S07_v2_3602556c556a · Guarded substitution and denominator clearing

1. Identify a repeated radical, ratio, or denominator expression; set a single new variable t for it and record its admissible range, including strict positivity or zero/nonzero cases.
2. Record every original denominator zero and exclude it before any clearing or multiplying; for inequalities, determine the sign of each denominator factor or use sign cases instead of multiplying by an unknown sign.
3. Clear denominators only by nonzero factors, reduce to a polynomial/equation/inequality in t, and solve it.
4. Back-substitute into the original variables, enforce the recorded t-range and excluded zero cases, and test all final candidates/endpoints in the original relation.

短策略：

> Use t for repeated radical/ratio. Record original denominator zeros and t's range/zero cases. Clear denominators only by nonzero factors. For inequalities, use denominator sign or sign cases; never multiply by unknown sign. Solve. Back-substitute within t range, handle excluded zeros, and check solutions/endpoints in original relation.

来源：math_train_intermediate_algebra_1030, math_train_intermediate_algebra_902, math_train_intermediate_algebra_704。状态 **shadow**；本轮实际shadow注入10次，生产注入0次。

完整 schema、trigger、guard、trace hashes、验证统计和token历史见 skill_bank_v2.json 与 data/skills_v2_full.json。
