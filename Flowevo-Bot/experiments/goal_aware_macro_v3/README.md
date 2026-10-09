# Goal-Aware Executable Macro V3

本轮完成离线研究并按预注册门槛停止付费实验。没有新的DeepSeek调用，没有MATH500。

- 人工工具：原dev 20/1549完整可解，直接提交20/20正确；其余1529题需要LLM，未执行。
- 自动bank：2/1549完整可解，直接提交2/2正确；其余1547题需要LLM，未执行。
- 独立保留池1115题：仅1题符合完整求解条件，B/C均正确；不足12道适用题、3道自动宏题、3类结构的预注册门槛。
- A Bot-NoBank未运行。B/C直接提交比例是离线覆盖率，不能当作全体准确率；新输入/输出/总token实际支出均为0，没有新的A-B-C模型性能结论。

受限DSL从603条已审计首次成功训练轨迹中提取9条可绑定的操作记录，合成根和、根积两个系数算术程序，排除12个来源拟合但通用验证失败的候选。语法、数学原语、系数特征和验证规则由人工提供；学到的是AST组合与其bank条目，不是自动学习全部题意语义或发现新定理。自动库没有把人工余式工具冒充学习成果。暂不进入production。

报告依次为 [实现](01_IMPLEMENTATION_REPORT.md)、[目标解析及覆盖](02_GOAL_PARSER_AND_COVERAGE.md)、[自动构建](03_AUTOMATIC_MACRO_DISCOVERY.md)、[离线验证](04_OFFLINE_VERIFICATION.md)、[条件试验](05_PILOT_RESULTS.md)、[机制与成本](06_MECHANISM_AND_COST.md)、[下一轮决策](07_NEXT_ITERATION.md)。原始指引和冻结运行代码在snapshots；所有候选/反例、来源、逐题Goal/Guard/证书、失败记录及完整账本在data。

```bash
# 在 Flowevo-Bot 项目根目录
python -m pip install -e '.[dev,experiment,rmmd]'
python -m pytest tests experiments/goal_aware_macro_v3/tests -q
python experiments/goal_aware_macro_v3/code/analyze.py
python scripts/verify_goal_v3.py
```

132项回归通过；核心求解代码与bank在保留池之前固定为 `5b7cf1bbcfc980e4cfe6dea32f6ab5b4d89645c2da88446ab47d3d4c53cdbce2`。`code/analyze.py`、`code/artifact_schema.py`与最终核验脚本是事后分析，没有改变冻结运行逻辑。工程首轮发现的LaTeX末尾问号问题在独立池之前修正，首轮源码及记录另存，旧V1/V2/RMMD实验完全保留。

本目录已完成；不要覆盖其中的冻结实验或重新把1115题称为未见数据。完整压缩包为项目根目录 `goal_aware_macro_v3.zip`，wheel版本0.4.0。本轮结论是继续改进自动宏发现与独立数据设计，暂不扩大付费实验。
