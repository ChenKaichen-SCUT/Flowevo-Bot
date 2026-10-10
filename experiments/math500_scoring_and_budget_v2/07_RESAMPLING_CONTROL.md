# 普通重采样辅助对照

两组都是同一33个首轮未完成ID；各生成一次，prompt/model/temperature完全一致。预算唯一变化4096或8192。发送顺序预声明随机交错，全部由一个64线程池限制，E不参与自适应调度或最终选答。

| 阶段 | 完整/33 | Fixed正确/33 | 平均输出tokens | 输出中位数 | 总tokens | 估计USD |
|---|---|---|---|---|---|---|
| E4096 | 10 | 9 | 3631.94 | 4096.0 | 127727 | 0.072773478 |
| 8192 | 22 | 19 | 5324.18 | 4888.0 | 183571 | 0.106279878 |

Fixed配对：两者正确8、仅E正确1、仅8192正确11、两者未确认正确13。净增10/33=30.30pp，双侧精确McNemar p=0.00634765625；配对bootstrap95%CI[12.12,48.48]pp。相较E，8192多用55,844输出tokens（输入相同），估计多USD0.0335064。

仅E正确：math_test_geometry_200。

仅8192正确：math_test_counting_probability_42, math_test_geometry_238, math_test_geometry_345, math_test_geometry_410, math_test_geometry_85, math_test_intermediate_algebra_122, math_test_intermediate_algebra_238, math_test_intermediate_algebra_57, math_test_precalculus_391, math_test_precalculus_423, math_test_precalculus_75。

逐题完成/正确/token在truncation_recovery.csv；E原始响应在same_budget_retry.jsonl。审计后E为10个正确，8192为21个正确（另1完整错答）；主比较仍保留冻结9对19。E/8192中的prealgebra_551同为90而被参考换行单位卡住，均已审查。

同预算重采样本身恢复9个自动确认正确题，因此不能将全部预算流程收益归因于增加上限。8192在相同题上比E多10个自动正确，提供增加预算有额外价值的证据；但两个独立采样的随机性、33题小样本、服务后端未固定及单次重复，不足以把贡献精确拆成相互独立的“纯采样”与“纯长推理”因果效应。温度0在该模型thinking模式下也不保证确定性。
