# FlowEvo实际接入与重现

新组件`FlowEvo/src/math_evaluation`与新入口`FlowEvo/src/code_math/evaluate_offline.py`只做已提交答案的离线评分。已有solver、router、prompt、skill库、预算controller和旧评分代码均未改动。`OfflineScoringConfig`可选legacy/fixed/v3，默认legacy。

从仓库根目录运行（已有环境依赖已固定）：

```bash
Flowevo-Bot/.venv/bin/python experiments/math_evaluator_v3_offline/code/reproduce_history.py
Flowevo-Bot/.venv/bin/python experiments/math_evaluator_v3_offline/code/build_regression_fixtures.py
Flowevo-Bot/.venv/bin/python experiments/math_evaluator_v3_offline/code/run_all_tests.py
PYTHONPATH=FlowEvo/src:Flowevo-Bot/src:FlowEvo-Recovery/src Flowevo-Bot/.venv/bin/python -m code_math.evaluate_offline --input experiments/math_evaluator_v3_offline/evidence/input_records.jsonl --output /tmp/math_v3_replay.jsonl --evaluator v3 --workers 12 --unknown-output /tmp/math_v3_unknown.jsonl
```

输出必须是新文件，已有文件不会被覆盖；重复运行请换输出名。只比较status/typed evidence和hash，elapsed_seconds自然会变化。安装到新环境时使用`FlowEvo/requirements-math-evaluator-v3.txt`；原有FlowEvo基础依赖不变。

原生任务适配：`from_flowevo_task(CodeTaskInstance, runner_record, submission_sealed=True)`使用`task.canonical_solution`；不把loader截断的`metadata.gold_answer`给V3。原生runner记录键`solution`映射为可见模型回答；没有finish_reason时保留None并标识不可用，不伪造stop。legacy/fixed仍可重放其传入的冻结历史gold。

本轮实际用原生`load_math()`从本地Parquet读取6道题，按问题全文关联之前已封存的回答，导出`evidence/native_loader_tasks.jsonl`及`native_runner_records.jsonl`，三种CLI均运行。它不是新的solver运行。命令与结果在`evidence/integration_smoke.json`。

Gold隔离是接口契约：必须有submission_sealed标记；没有任何结果回调、反思或重试入口；ModelExtractor签名没有gold参数；批处理worker禁止socket连接。调用者拥有输入数据时仍需遵守进程阶段隔离，这不是阻止恶意调用者读本地gold文件的访问控制系统。

历史实验配置中的skill_injection/history_retrieval/gold_answer_feedback/gold_driven_reflection/correctness_retries均为false，本轮没有生成阶段。此前项目仍保留显式指定旧训练策略库的通用能力；本轮未调用或开启它。哈希证明旧执行代码、请求响应和Prompt全部不变。
