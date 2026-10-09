# 宏实现

代码src/flowevo_bot/rmmd/macros.py；macro_skill_bank.json同时保存Compact和Executable、来源、触发/guard、证书scope。研究用途，未直接加入生产active库。

root_invariants：roots题且存在数量/表达式请求、唯一数值QQ多项式、次数2–6；拒绝显式根子集和未定参数。首一化→e_k→Newton幂和；用多项式重建及伴随矩阵trace分别核验。只提供ALL roots的中间量，绝不将其局部正确当成最终任务完成。若存在0根，仍可安全给e_k，但不得直接求倒数；LLM必须另检查目标分母及约束。

Compact：For all roots with multiplicity, Vieta gives e_k=(-1)^k a_(n-k)/a_n. Rewrite the requested symmetric expression in these elementary sums; use Newton identities for power sums. Reciprocal expressions require nonzero denominators. Coefficients alone do not determine a restricted subset of real, positive or rational roots. Verify the requested quantity after computing the invariants.

polynomial_remainder：全题匹配“Find/Determine/What is the remainder when/of M0 is divided by M1”文法，同一变量QQ多项式、被除式次数≤128、除式次数1–16、系数/长度/操作数有界。执行除法后，独立系数递推再验证，检查精确恒等式P=QD+R和degR<degD。仅这里允许直接提交，原因是文法完整消费题目且证书覆盖完整所求余式。其余叙述如“然后代入”拒绝。更高次表达式或参数除式不在证明范围。

Compact：Reduce powers and products modulo the nonzero polynomial divisor over the coefficient field. For ax+b evaluate at -b/a; repeated factors require multiplicity. Verify P=QD+R exactly and deg(R)<deg(D). Submit R only if the question asks precisely for this remainder.

结构触发支持all_of/any_of/not/guard，未知guard按False。真实流程同时检查trigger、guard、execution_verified；冻结选择时验证，运行时重新算且与冻结结果比较。C根执行失败不能静默改成B；当前冻结题均通过，若运行时不同则中止。记录execution_attempted、verified、full_task_verified与local_total_seconds。

真实接受案例：来源1007的ab+ac+bc=11/3；742的倒数两两积和e2/e4=9/4（宏只给中间量）；738余式52；891余式3。拒绝样例及原因见tests和data/guard_examples.json。随机性质测试仅是有界回归，完整数学保证来自QQ多项式恒等式及次数判据，不声称自然语言任意题目的泛化证明。
