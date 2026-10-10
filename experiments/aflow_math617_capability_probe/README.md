# AFlow数学能力边界实验

实际官方数据605题（119验证/486测试），目录按用户指引保留617名称；不能称精确617复现。

阅读顺序：00摘要 → 01数据审计 → 02–08结果 → 09决策。所有机器可读指标由summary.json和逐题文件支持。冻结V3与响应哈希绑定的数学复核分别保存；两题H保持null。研究决策NO-GO，条件实验未满足门槛不是未完成交付。

已完成输出全部保留。不要为复现统计再次付费：在工作区使用`Flowevo-Bot/.venv/bin/python experiments/aflow_math617_capability_probe/code/analyze.py`和`code/write_reports.py`即可从现有证据重建报告（第二条使用相同目录前缀）。原始生成入口为`code/generate.py`，阶段参数依次validation1、validation4、test1；已有seal时只校验并退出，不重发。不得重新运行preflight来覆盖原始事前预算时间戳。

实际流程：数据审计/预算冻结 → 9项生成测试 → validation1生成封存/评分/人工复核及12项选择测试 → 完整validation4生成 → 公共选择封存 → 候选2–4评分/人工复核 → Pass8门槛决策/方法冻结 → test1单次生成（复用7份）→ 冻结V3评分（复用7份旧评分）→ 数学审计 → 汇总及交付验证。选例依赖公开数据元信息；gold只用于离线评分/审计/Oracle，未反馈给求解器。

原始作者档案、605题和官方行序位于data/official及evidence；source/data SHA见manifest和freeze。raw保存逐调用请求和完整响应，`.sse.gz`保留新调用原始流；attempts记录物理调用，api_calls含7份历史复用行。candidate_generations只有完整119验证集的476个候选，baseline_results包括605个第一候选。不要将逻辑方法费用重复加到物理API总账。

所有候选均无Skills/Gold反思；API64、本地12；冻结V3源代码不变。手工审计脚本的ID映射仅用于重现人工证据，不会被生成或选择程序读取。具体case证明可在*_adjudications.jsonl、failure_cases.jsonl和evidence/ambiguous_reference_cases.json中查阅。
