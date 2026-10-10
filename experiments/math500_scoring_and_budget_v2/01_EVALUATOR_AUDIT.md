# 评分器冻结与回归审计

LegacyEvaluator 直接调用已发布的 `Flowevo-Bot/src/flowevo_bot/evaluator.py::extract_answer` 与 `experiment_grader.py::grade_one`，没有覆盖历史实现。FixedEvaluator 直接调用上一轮 `FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py::grade`；对应源文件哈希在 `evidence/evaluators_frozen.json`。两个适配器只增加耗时统计，不修改答案逻辑。

历史500题重跑得到：Legacy464、Fixed473；9道历史假阴性全部纠正，原464道正确题没有损失。逐题结果在 evaluator_regression.json。新反例覆盖坐标次序、区间开闭、集合漏项、负号、根号分支、变量分母定义域、百分数数量级和错误单位。预调用59项测试通过，其中包括上一轮完整评分器测试。

两套评分器都属于离线程序。在线 `run_experiment.py` 只导入独立 `completion.py`，其中只有从已验证实现复用的平衡括号、最终答案标记解析与无gold完成规则。在线程序不导入评分模块，不读取标签路径；它接收的 native_prompts.json 严格限定为题目prompt及无gold/无skill标记。输出完成且数学错误不会因为离线结果而触发重试。

所有生成分支完成后才打开 offline_labels.jsonl。新题结果不用于修改评分器、完成检测器、预算门槛、任务选择或prompt。人工数学审查仅生成辅助审计结论，不覆盖四组自动成绩。

命名边界：历史464/500来自 Flowevo-Bot 目录中实际route=base、无Skill的一次性输出。原来使用历史检索的另一组 FlowEvo 是不同条件，不能冒称其历史成绩为464。本轮按用户指定统一使用原生 FlowEvo `cot_baseline`、library=None，经原生代码导出的prompt与历史base_prompt逐字节相同。这里A/B/C/D使用的是该明确关闭Skill和gold的基础求解路径。
