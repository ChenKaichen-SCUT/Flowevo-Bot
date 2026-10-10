# 分歧逐题说明

共有首轮54份、自适应26份三状态分歧，其中36份是V3把旧incorrect拆为prediction_incomplete。所有分歧记录均纳入`adjudicated_cases.jsonl`，保留题目全文、原始最终文本、完整参考解答、所有候选、规范化对象、请求/响应hash、代码版本和独立问题证明。

之前20道确认问题逐题如下。ID均保留原始值；首轮仍截断的记录不因同题自适应答案正确而获得分数。

| task_id | 历史问题 | 首轮 V3 | 自适应 V3 | 题目数学证明 |
| --- | --- | --- | --- | --- |
| math_test_geometry_200 | 类型/格式覆盖 | prediction_incomplete | correct | 勾股得到对角线40；两直角三角形面积384+1920=2304。 |
| math_test_geometry_352 | 类型/格式覆盖 | correct | correct | 正交位移(8,10)，距离sqrt164落在[12.5,13.5)，最近整数13。 |
| math_test_intermediate_algebra_423 | 类型/格式覆盖 | correct | correct | 判别式=-7k(k+4)；k=0时原式为7=0；实根参数集[-4,0)。 |
| math_test_intermediate_algebra_478 | 类型/格式覆盖 | correct | correct | 系数比较A+B=4,-A+2B=5，得A=1,B=3；两种最终分式完全相同且均排除x=-1,2。 |
| math_test_intermediate_algebra_482 | 类型/格式覆盖 | correct | correct | Vieta e1=-2,e2=e3=0,e4=2；三目标的和0、二次对称和-8、积8，故三次式z³-8z-8，完整根集{-2,1±sqrt5}。 |
| math_test_intermediate_algebra_700 | 类型/格式覆盖 | correct | correct | 周长23，2009模23余8；8落在CD对应累计长度(7,13)内。 |
| math_test_intermediate_algebra_756 | 类型/格式覆盖 | correct | correct | 令y=x²-2x，消元得y=18；x=1±sqrt19，均不是原式分母零点。 |
| math_test_intermediate_algebra_813 | 类型/格式覆盖 | correct | correct | 偶函数f与奇函数g的乘积h满足h(-x)=f(x)(-g(x))=-h(x)，类别odd。 |
| math_test_number_theory_158 | 类型/格式覆盖 | correct | correct | 101₆=37，32₆=20；差17=25₆。 |
| math_test_number_theory_295 | 类型/格式覆盖 | correct | correct | 从1开始循环MATH，第2009位对应索引0，字符M。 |
| math_test_prealgebra_372 | 类型/格式覆盖 | correct | correct | 两小时总里程40+50=90英里，平均速度45mph。 |
| math_test_prealgebra_551 | 类型/格式覆盖 | prediction_incomplete | correct | 三个面积36的正方形，减去两个面积9的重叠区，面积90。 |
| math_test_prealgebra_598 | 类型/格式覆盖 | correct | correct | 20ft/min乘12in/ft再除60s/min，等于4in/s。 |
| math_test_prealgebra_625 | 类型/格式覆盖 | correct | correct | 按题给1kg=2.20lb，3lb=15/11kg∈[1.355,1.365)，两位小数1.36。 |
| math_test_prealgebra_841 | 类型/格式覆盖 | correct | correct | 图上4厘米，每0.5厘米为1千米，得8千米。 |
| math_test_prealgebra_853 | 类型/格式覆盖 | correct | correct | 与67.4距离为.068,.073,.126,.045,.054，D最近。 |
| math_test_precalculus_380 | 类型/格式覆盖 | correct | correct | b=(2,6,3)，a·b=8，b·b=49；投影(16,48,24)/49。 |
| math_test_intermediate_algebra_409 | 参考漏解 | correct | correct | 令u=(x/(x+1))²，得u=9；两根-3/2,-3/4均满足x≠-1，参考末盒遗漏前根。 |
| math_test_intermediate_algebra_516 | 参考漏解 | correct | correct | 两方程相减得6903(x²-1)=0。共同根x=±1分别要求b=∓10879；代回皆成立，两个b不可丢失。 |
| math_test_intermediate_algebra_563 | 参考漏解 | correct | correct | 原域x≠-1,0,1；通分后两根3,2/5均合法。 |


另外两道旧修复得分项：geometry_191的48°和prealgebra_385的20%继续判对。唯一V3新增弃权题precalculus_187在两分支均为2^2005，数学证明正确，解析限额不改变正式结果。

自适应仍未完成：algebra_1161、geometry_56、intermediate_algebra_494。完整但数学错误：number_theory_491提交54，正确30。这四道均未计为V3正确。
