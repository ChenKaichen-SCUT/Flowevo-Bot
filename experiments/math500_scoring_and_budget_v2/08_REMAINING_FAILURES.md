# 剩余失败：逐题审计

D主结果476true，24个非true：3截断false、18unknown、3完整false。不能将这24题都称为推理错误。检查完整输出与原参考解，并用exact arithmetic/SymPy核验后分为：**17评分覆盖缺口、3标签提取漏解、3仍截断、1完整且明确错误**。相应jsonl保留审计前/后类别、原模型完整答案、参考解、评分证据、最终预算及原响应hash。

复核由Codex助手阅读证据并执行代码完成，无独立人类双盲裁决。所有评分分歧及D非true均审查；其余自动true未逐一独立重新证明。敏感性结果基线467、增强496（+29）；不是新的冻结评分器成绩，也没有反哺请求、评分器或标签。

## 完整数学错误

`math_test_number_theory_491`：应求四个最小连续正整数且积末位4、积>1000之和。模型8192先正确找到n=6与3024，随后在“The four smallest such starting integers”改成列举四组起点6,11,16,21，最终54。正确四整数6,7,8,9，和30。错误定位是目标对象追踪/聚合对象混淆，并非乘法本身；原始解与最小合法起点枚举保存在remaining_true_math_errors.jsonl与code/manual_audit.py。

该题4096截断，8192完整错误后不再升16384。没有发现“一批”完整数学错误，只有1个清楚案例。它可成为下一阶段输出目标校验的候选，但样本不足以支持大规模复杂Skill或多路径机制结论。

## 逐题证据

| task_id | 主分类 | 证据 |
|---|---|---|
| math_test_algebra_1161 | still_truncated | 16384 时仍无正文最终答案。按逆关系解释，值域等于原函数定义域，最大值6；但图中 f(1)=f(5)=2，不是单射，严格逆函数未定义。隐藏推理反复讨论此歧义；不能把隐藏推理中的候选数字当交付答案。 |
| math_test_geometry_200 | scorer_coverage_failure | YW=sqrt(32²+24²)=40，96²+40²=104²；面积=32×24/2+96×40/2=2304。square units 单位格式未被评分器接受。 |
| math_test_geometry_352 | scorer_coverage_failure | 两方向成直角，距离sqrt(8²+10²)=sqrt164，四舍五入13。参考答案的 text{13} 包装导致 unknown。 |
| math_test_geometry_56 | still_truncated | 区域为圆心(4,0)、半径4、圆心角135°的扇形加顶点(0,0),(4,0),(3,-1)三角形，面积6π+2。隐藏推理已出现此值但仍反复核对；16384耗尽时正文为空。 |
| math_test_intermediate_algebra_409 | label_extraction_incomplete | 令u=(x/(x+1))²，(u+11)/(u+1)=2⇒u=9，解为-3/2,-3/4，均满足原式且x≠-1。原参考解分别boxed两个答案，last-box提取只保留-3/4；模型两解完整。 |
| math_test_intermediate_algebra_423 | scorer_coverage_failure | 判别式=-7k(k+4)≥0⇒-4≤k≤0；k=0时原式为7=0，排除0。因此[-4,0)与模型不等式相同，评分器类型比较保守拒判。 |
| math_test_intermediate_algebra_478 | scorer_coverage_failure | 系数比较A+B=4,-A+2B=5⇒A=1,B=3。3/(x+1)-1/(x-2)=(2x-7)/((x+1)(x-2))，两表达式定义域相同。displaystyle 包装触发保守的定义域分支。 |
| math_test_intermediate_algebra_482 | scorer_coverage_failure | Vieta推得三目标值的三次式z³-8z-8=(z+2)(z²-2z-4)。集合{-2,1-sqrt5,1+sqrt5}等于参考的{1±sqrt5,-2}；后者解析成嵌套集合造成false。模型uvw对称恒等式已用SymPy验证。 |
| math_test_intermediate_algebra_494 | still_truncated | 每区间[n,n+1)有n个高度1/2的V形段。x≤2006时每V形与2^(x-2007)相交两次，最后右端点2006仅计一次；x>2006指数超过1/2不再相交。总数2Σ(n=1..2005)n=4022030。隐藏推理已有该值但输出未结束；不计正确。 |
| math_test_intermediate_algebra_516 | label_extraction_incomplete | 两方程相减⇒6903(x²-1)=0，共同根±1，分别得b=-10879,+10879；代回两式均为0。参考解有两个boxed，last-box仅留下正值。 |
| math_test_intermediate_algebra_563 | label_extraction_incomplete | 原式要求x≠-1,0,1；通分化简为(x-3)(5x-2)=0，两解3和2/5都合法。参考解多个boxed被last-box截成2/5。 |
| math_test_intermediate_algebra_700 | scorer_coverage_failure | 周长23，2009=23×87+8，8落在CD的接触区间(7,13)。题目明确要求输入CD，参考overline{CD}是线段标记；评分器按代数表达式误判。两评分器都false，所以不能只审查评分分歧。 |
| math_test_intermediate_algebra_756 | scorer_coverage_failure | 令y=x²-2x，原式化为1/(y-8)+1/(y-24)=2/(y-48)，解y=18，故x=1±sqrt19。均不在原分母零点中。展开两根与±写法等价，解析结构类型不一致导致unknown。 |
| math_test_intermediate_algebra_813 | scorer_coverage_failure | h(-x)=f(-x)g(-x)=f(x)(-g(x))=-h(x)，故odd正确。参考text{odd}未支持。 |
| math_test_number_theory_158 | scorer_coverage_failure | 101_6=37，32_6=20，差17=25_6。模型25后接内联数学下标的格式未被解析。 |
| math_test_number_theory_295 | scorer_coverage_failure | 2009 mod4=1，循环MATH首字母M。参考text{M}未支持。 |
| math_test_number_theory_491 | confirmed_math_error | 模型正确找到最小起点n=6及积3024，却在“The four smallest such starting integers”处将目标偷换为四个合法起点6,11,16,21，求和54。题目要求最小四个连续整数6,7,8,9之和30。首轮4096截断，8192给出完整但错误的54；按规则没有继续升至16384。 |
| math_test_prealgebra_372 | scorer_coverage_failure | 总路程40+50=90英里，总时间2小时，均速45 mph。复合速度单位未解析。 |
| math_test_prealgebra_551 | scorer_coverage_failure | 三个6×6正方形扣除两个3×3重叠区域，3×36-2×9=90。8192和E4096均输出90；参考text中的换行单位造成unknown。 |
| math_test_prealgebra_598 | scorer_coverage_failure | 20 ft/min×12 in/ft÷60 s/min=4 in/s。单位规范化残留inches per。 |
| math_test_prealgebra_625 | scorer_coverage_failure | 3/2.20=15/11≈1.3636，依题目四舍五入至1.36kg。grams子串被移除后残留kilo。 |
| math_test_prealgebra_841 | scorer_coverage_failure | 4/0.5=8km；meters子串被移除后残留kilo。 |
| math_test_prealgebra_853 | scorer_coverage_failure | 五选项距67.4的差为.068,.073,.126,.045,.054，最小对应D。题目A.格式未被只认(A)的选项处理覆盖。 |
| math_test_precalculus_380 | scorer_coverage_failure | b·b=4+36+9=49，proj_b(a)=8b/49=(16,48,24)/49，与参考相同。矩阵前的displaystyle阻止专用解析。 |

三截断题最终正文均为空，隐藏推理中出现正确候选也不视为最终交付。geometry_56与intermediate_algebra_494显示反复核对造成未完成；algebra_1161额外存在“逆函数”与“逆关系”的题意歧义：图不满足单射，参考6对应逆关系值域最大值。这一歧义是次级标记，不与主类重复加总。

3个多解标签问题的原参考解包含全部解；冻结last-box提取只留下最后一个。报告数学核验时用完整问题和参考解，不把错误的单元素提取当唯一真值；但为了保留预先冻结主比较，本轮不改标签、不回写主评分结果。后续必须解决这个评测协议缺陷。
