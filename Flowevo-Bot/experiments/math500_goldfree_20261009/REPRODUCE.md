# 复现本次比较

从 `Flowevo-Bot` 目录运行。密钥只从父目录 `miyao.txt` 读取并注入进程环境，不保存到配置和结果。

```bash
uv pip install --python .venv/bin/python -e '.[experiment,dev]'
.venv/bin/python scripts/run_math500_comparison.py --stage train
.venv/bin/python scripts/run_math500_comparison.py --stage build
.venv/bin/python scripts/run_math500_comparison.py --stage compare
```

已有请求通过本地账本恢复，已有封存答案不会再次调用模型。对同一目录重复执行各阶段会复用记录；若 provider pending journal 仍存在，必须先判断请求是否完成，不能盲目重发。重新生成独立实验应复制配置与脚本并指定全新目录，不覆盖现有结果。

数据名单已固定在 `manifests/`，题面与标签分开存储。训练题 700、验证题候选池 350、测试题 500；验证实际调用只覆盖候选 skill 的可匹配题。每个候选最多 60 对。按学科/难度抽样，排除与训练/验证明显重复的测试题和之前调试使用的代数测试前 500 题，不等同于标准 MATH-500。

API 最大并发 64；本地评分 12 进程，主进程 CPU affinity 限制在 12 核，BLAS/OpenMP 单线程。测试阶段两方法各 500 次请求、每题一次、输出上限 4096。DeepSeek 默认开启思考模式；请求 temperature=0 在该模式下不生效，不能声称确定性。completion_tokens 计入服务端报告的思考与输出消耗。无测试 gold 反思、无测试 gold 入库。正式比较使用冻结历史，FlowEvo 原生检索/提示模板通过独立解释器导出，两方法共享 API 与评分器。

第一次蒸馏 12 次全未通过（9 次截断、3 次触发特征无效），已保留 `distillation/`、`bank_attempt_1_*`。随后明确触发词契约并仅将蒸馏输出上限改为 16384，在 `distillation_v2/` 生成 12 个合法候选。相关失败与修订成本全部计入建库，未丢弃、未使用测试反馈调参。

评分器使用 math-verify 0.8.0 的符号等价验证，保留严格归一化评分作参考；所有响应封存后才能读取标签。截断响应按错误处理且保留 token。测试逐请求 provider usage 的原始字段保存在各 `task_calls/*.provider/`。较早训练/建库请求保留了输入/输出 token 及 prompt、response，但当时还未保存原始 provider usage 的额外字段。

代码快照：`source_frozen_before_test.json`；完整依赖：`requirements.lock.txt`；测试日志：`tests.log`。旧阶段交付说明及旧 wheel 描述的是修改前状态；本次复现使用当前源码 editable 安装。

官方参考：
- DeepSeek 思考模式：https://api-docs.deepseek.com/guides/thinking_mode/
- Math-Verify：https://github.com/huggingface/Math-Verify
