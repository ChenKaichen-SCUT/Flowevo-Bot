# MATH/GSM8K：关闭 gold 反思

2026-10-09 修改 `src/code_math/runner.py`。数学题每题生成一次；`gold_answer` 仅参与最终离线评分，不再进入 prompt，也不再决定 retry。程序题仍使用独立测试反馈进行恢复。数学题的 skill 检索和首轮注入保持开启。

测试阶段冻结数学库，不把测试题的 gold 正误转为后续历史或 ExpeL 提示。允许显式训练运行通过 `cfg['math_train_build']=True` 收集首次成功解答。可用 `run_condition(..., math_library=library)` 或 CLI 参数 `--math-library-json` 注入预先构建的训练库。

原 version 1 checkpoint 可能包含 gold 引导的结果，因此拒绝混用；请为新协议使用新的输出目录，历史结果保留。

离线验证：

```bash
.venv/bin/python -m unittest discover -s tests -p test_math_goldfree.py
```

检验包括替换 gold 后 prompt/调用次数不变、错误数学题不重试、测试答案不入库、MATH/GSM8K 均保留训练 skill 注入。

与 Flowevo-Bot 的 500 题比较使用 `scripts/export_goldfree_math_prompts.py` 调用本仓库 `CodeSkillLibrary` 和 `build_goldfree_math_prompt`。共享 API 客户端、逐请求 token 账本、输出额度与数学评分器，避免将不同客户端/评分器差异误记为算法差异。

实验文件位于 `../Flowevo-Bot/experiments/math500_goldfree_20261009/`。`native_math_library.json` 可以用于上述 CLI 参数。详细实验设置在 `protocol.json`，结果在 `REPORT.md`。
