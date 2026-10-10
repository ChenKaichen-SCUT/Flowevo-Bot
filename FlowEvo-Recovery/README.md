# FlowEvo-Recovery

本轮独立模块，基于已关闭数学 gold reflection 的 FlowEvo 流程，研究公开失败信号、一次恢复动作和训练阶段冻结的恢复经验。历史 FlowEvo / Flowevo-Bot / V1–V4 文件保持不变。

## 运行与复核

在仓库根目录使用现有环境（Python 3.10），或先安装兄弟目录 `Flowevo-Bot` 的依赖。模块复用其冻结数学评测器和有界整数表达式检查器，因此需要两个源码路径：

```bash
export PYTHONPATH="$PWD/FlowEvo-Recovery/src:$PWD/Flowevo-Bot/src"
Flowevo-Bot/.venv/bin/python -m pytest -q FlowEvo-Recovery/tests
```

实验目录为 `experiments/failure_recovery_pilot/`。`code/prepare.py`、`refine_split.py`、`campaign.py`、`build_memory.py`、`freeze.py`、`confirm.py` 保存了实际执行阶段；现有冻结实验不应重新初始化。真实调用需要根目录本地 `miyao.txt`，此文件不发布。实验已完成后，仅运行 `code/analyze.py` 和 `code/verify.py` 即可复核保存的输出与账本，不需要 API。

## 边界

- `public.py` 的 Task / State 拒绝额外字段，控制器只使用公开状态。
- `checks.py` 只运行公开测试；代码在 Linux 隔离子进程中执行，有 CPU、内存、时间和 seccomp 系统调用限制。该执行器用于本次标准数据集，不宣称是完整的对抗沙箱。
- `grading.py` 只在全部决策与输出封存后使用参考答案 / 隐藏测试。代码只公开第一条测试，剩余测试离线使用。
- `controller.py` 包含单次解答、固定重试、确定性失败后重试、A、C 与打乱 Memory 对照。每个方法至多一次额外模型调用；相同题与动作共享一次真实输出以减少采样噪声，逐方法仍计入完整逻辑成本。
- `client.py` 持久化单次请求、实际 usage 和保守 token 预留；未知计费请求保留 pending 并停止，无基础设施或按正确性自动重试。
- `adapter_audit.py` 是确认前预定的零调用代码提取敏感性分析：按公开函数名选取函数定义块，不使用隐藏测试挑选代码。它帮助分辨接口修复和算法恢复。

详细结论、未完成分支、数据暴露边界、计费与统计限制见实验报告。此模块不自动启动下一轮实验。
