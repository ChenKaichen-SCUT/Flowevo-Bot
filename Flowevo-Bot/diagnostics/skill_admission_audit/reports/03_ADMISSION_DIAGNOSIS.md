# Admission 逐关诊断

入口 `src/flowevo_bot/skill_validator.py:SkillValidator.admit`；配置来自真实实验 config.json，而非默认示例。阈值来源：项目配置与程序常量；没有找到以独立数据校准这些阈值的记录（missing）。本次离线重放12/12与历史状态一致，没有发现状态计算结果与代码不一致。

执行顺序：

1. 需要独立证据：independent=true、evidence_hash正确、pairwise非空。空列表即 quarantine。
2. 任何 base_only_correct>0 即 quarantine。
3. 来源至少3、来源provenance/哈希数量有效、dev至少10、structurally_distinct_cases>0，否则shadow。
4. 平均节省的正态近似95%下界>0，并且平均节省×expected_future_uses(100)>sum(token_stats)，才可active；否则shadow。
5. active还要取得与字段内容绑定的证书。

这些判断是顺序短路的；下表是首次阻断，JSONL同时保留后续可计算门槛。无执行数据时，原始统计的0不等于测得零收益，导出均值/净收益留空并写unknown。

| ID | 来源 | dev对数 | base→skill正确 | 每次节省token | 100次预计净节省 | 首次阻断 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S02 | 5 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S03 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S04 | 6 | 18 | 15 → 16 | -74.944 | -53281.444 | saving_lower_bound | shadow |
| S05 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S06 | 6 | 10 | 7 → 8 | -119.0 | -63855.0 | saving_lower_bound | shadow |
| S07 | 6 | 1 | 1 → 1 | 1162.0 | 98749.0 | dev_count | shadow |
| S08 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S09 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S10 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S11 | 6 | 0 | missing / 未执行 → missing / 未执行 | missing / 未执行 | missing / 未执行 | independent_evidence | quarantine |
| S12 | 6 | 10 | 9 → 7 | -281.9 | -67144.0 | observed_harm | quarantine |

首次阻断互斥统计：独立证据为空8个、观察到harm1个、dev样本不足1个、正节省下界不成立2个。解释分类：8个应归入覆盖/证据不足，不是已证伪的低质量数学规则；S07为n=1样本不足；S04/S06已观测到平均增加token；S12由一例评分假阴性及一例截断触发harm。

可重叠原因：dev不足10个样本共9条（其中8条0样本）；平均成本增加3条；所有12条在当前真实数据下都不能通过成本证据要求（8条未知而非已证成本增加、S07下界人为0、3条平均负节省）；9条连来源题也无法词面匹配；10条有表示/条件语义问题；S04存在明确的对称商适用条件遗漏风险。不要将这些重叠数量相加。

## 实现与统计问题

- S02 明确 OR文字/AND机器条件失配。Distiller校验只要求preconditions属于词汇表、出现在compact中，不要求它们在来源题或独立题可满足；9条来源自匹配为0仍通过schema。
- 空pairwise的 independent 字段仍设true，admit再用非空检查隔离；决策防护实际生效，但状态语义混合了“缺数据”和“有害”。
- S12一次评分假阴性不是Admission布尔逻辑错误，却污染其输入。不得据此认定应该放宽reject_observed_harmful_patterns。
- 预算实验 `experiment_bank.validate_batch` 直接写 structurally_distinct=True；之前确实做过全局近重复检查，但这不能证明数学结构独立。该字段证据强度过高。
- 单卡token_stats未纳入第一次失败蒸馏及未入库训练题成本，而全局bank.cost_calls和成本报告包含这些支出。全局总数正确；单卡摊销估计不是全局总成本分摊。
- n=1时saving_lower_bound=0是程序默认值，不能当作估计置信区间。

不修改任何阈值、银行快照或历史分数。全部门槛输入、阈值、短路位置和额外失败项见 `data/admission_decisions.jsonl`。
