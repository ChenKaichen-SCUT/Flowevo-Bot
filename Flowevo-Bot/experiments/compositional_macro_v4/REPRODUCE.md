# 复核与数据位置

在完整GitHub工作区的`Flowevo-Bot/`目录运行，使用现有Python3.10虚拟环境。V4新增依赖为`rapidfuzz==3.14.1`；其他数学依赖及实测版本见`evidence/environment.json`。新包在`src/flowevo_bot/compositional_v4/`，旧`goal_v3/`等包没有修改。

```bash
.venv/bin/python -m compileall -q src/flowevo_bot/compositional_v4 experiments/compositional_macro_v4/code
.venv/bin/python -m pytest tests experiments/goal_aware_macro_v3/tests experiments/macro_discovery_pilot/tests -q
.venv/bin/python experiments/compositional_macro_v4/code/verify.py
```

测试无需密钥或网络。最后一个命令复核4075个历史文件和38个冻结文件，重建来源宏/候选、重算数学证书、验证9592条封存记录并重放5条完整提交；会刷新本轮verification证据，不修改原始运行器或输出。发布后若只需只读核验，可在一次性完整副本中运行。

研究归档`compositional_macro_v4.zip`包含所有V4报告、数据、代码、证据、完整Python源码及603原始来源。它不重复打包全部历史上游数据集；全历史保护检查和重做划分需要完整仓库。压缩包内artifact_inventory.json列出SHA256，外部同名.sha256给出ZIP hash。

V4运行次序见README。split.py/freeze.py会拒绝重新覆盖已冻结划分；若开展新的复现实验，应在副本中换实验输出目录。不要在已看过的确认题上继续调参，也不要把本轮4796题再次称作未见数据。

未运行API协议，因此不存在真实task_results.jsonl模型结果；机器可读离线结果为offline_task_results.jsonl，回退题正确性/tokens保持null。api_calls.jsonl为空，paid_gate.json明确NOT RUN。
