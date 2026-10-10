# 测试与历史案例覆盖

全部相关项目测试结果：**460通过，0失败，0跳过**。BoT两个`test_templates.py`是字符串模板常量，不含可收集测试，pytest返回5；已单独列出，不虚报为已执行测试。

| 测试组 | 通过数 | 结果 |
| --- | --- | --- |
| FlowEvo/tests | 2 | PASS |
| FlowEvo-Recovery/tests | 20 | PASS |
| Flowevo-Bot/diagnostics/skill_admission_audit/tests | 11 | PASS |
| Flowevo-Bot/experiments/goal_aware_macro_v3/tests | 42 | PASS |
| Flowevo-Bot/experiments/macro_discovery_pilot/tests | 17 | PASS |
| Flowevo-Bot/tests | 134 | PASS |
| Flowevo-Bot/vendor/bot | 0 | 0个可收集测试（常量文件） |
| buffer-of-thought-llm | 0 | 0个可收集测试（常量文件） |
| experiments/math500_scoring_and_budget_v2/tests | 31 | PASS |
| experiments/math_evaluator_v3_offline/tests | 153 | PASS |
| experiments/math_truncation_and_scoring_audit/tests | 42 | PASS |
| experiments/math_evaluator_v3_offline/tests/test_artifacts.py | 8 | PASS |


V3基础正反例64项，历史真实记录89项。后者包括首批9个确认误判、第二批全部22份旧新评分分歧（包括非主表的E控制响应）、17覆盖问题和3漏解题的两套输出、完整错误/截断和普通样本。

负例覆盖缺一个根、±只取正支、区间错误端点、百分数语义混淆、量纲错误、more/less方向错误、变量域丢失、矩阵维度/元组顺序、任意Python表达式、资源限制、隐藏reasoning、仅示例的boxed、最后答案推翻中间结果、未封存回答。task ID改名后结果不变。新评测模块中不存在task ID特例。

原FlowEvo gold隔离、Recovery、BoT所有历史策略和实验数据完整性测试仍通过。测试进程强制禁止网络；历史测试中的LLM均为FakeLLM/模拟transport。

第一次全套测试使用pytest importlib模式，导致原BoT中直接`from conftest import ...`的5个模块收集失败；恢复其原有prepend模式后仅重跑该组，134项全过。保留首次日志和重跑日志，未修改旧项目测试以迁就新接口。

实际集成另执行原生MATH loader读取本地数据，导出6道封存回答，通过Legacy默认、Fixed、V3三种CLI配置；V3六道全部正确。输入/输出路径相同或已存在时拒绝覆盖。
