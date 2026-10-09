# 真实轨迹审计

原始独立求解记录1840条：MATH 1838，另2条GSM8K/Game24真实smoke。可独立确认正确的MATH记录跨所有split为1620条，但仅603条训练首次成功可用于挖掘。

旧627条“成功”中，601条得到保守评分确认，26条unknown隔离；另从原来标False的训练记录恢复2条，合计603。没有把unknown当作正确。保留所有原始评分，新的离线评分另存。

| subject | clean |
| --- | --- |
| algebra | 100 |
| counting_probability | 88 |
| geometry | 70 |
| intermediate_algebra | 88 |
| number_theory | 92 |
| prealgebra | 91 |
| precalculus | 74 |

排除共1237条；原因可重叠：{'offline_incorrect_or_truncated': 134, 'offline_unknown': 80, 'test_set_excluded': 1000, 'previous_dev_used_for_selection_excluded': 138, 'outside_MATH_scope': 2, 'legacy_v1_no_complete_request_provenance': 1, 'different_benchmark': 1}。1000测试轨迹绝不学习；旧开发78及V2开发60都排除。700原训练为795435 acquisition tokens，603成功轨迹本身518212 tokens；失败训练也属于采集成本。

总计1261个唯一task ID、579条跨方法重复任务轨迹。history、bank.history、checkpoint和逐call文件只是同一请求的复制件，不新增样本。可审计MATH中未发现gold反思暴露；2条历史smoke完整请求证据不足，gold_exposed=null，均排除。75条干净训练轨迹曾作为旧技能来源，字段保留，不声称全新来源。

统一clean/excluded JSONL记录problem、model_solution、final_answer、offline_correct、gold_exposed、truncated、实际input/output/total tokens、source_run_id、source_hash、旧评分、seal、call ID和以前使用情况；clean不包含gold_answer。重新核对原始submission seal、prompt、response和冻结评分器hash。源轨迹是来源可查的首次调用，不包含gold引导后修订。
