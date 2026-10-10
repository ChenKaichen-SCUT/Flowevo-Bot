# Failure Mechanism / A1 / A2 Pilot

入口：[研究摘要](00_EXECUTIVE_SUMMARY.md)。原始V3与异常复核分开保存；使用data/public_prompts.jsonl生成，全部封存后才读取offline_labels.jsonl。历史6572文件保持不变，旧实验/460项测试复用。

完成后再次执行run_pilot.py只复用封存结果，不会产生API请求。不要删除raw/checkpoints或封存文件以强行重跑。程序默认对未知计费中断停止；本轮一个TLS失败由用户明确授权、保留预留上界后通过recover_transport_and_seal.py补跑。该补跑只允许一项同请求、评分前执行。

已完成运行以封存文件为准，不需要重做流程。若在独立副本复现全流程：先核验参考版本、准备数据和历史候选提取，完成新增控制器单测；再用 reconcile_atlas.py / complete_atlas_review.py 合并历史已有评分，finalize_stage1_metadata.py 记录调用前的去重及接口标签恢复，最后冻结 preflight。verify_atlas_reporting.py 只核对聚合数字，不重新抽取或评分。

当前试验曾在预检阶段遇到同名历史 preflight 模块导入冲突，未发出请求，随后用新脚本的明确路径运行预检。原始日志保留，最终 pre_api_freeze.json 和 ALL_GENERATION_SEALED.json 是有效版本。新增 finalize_stage1_metadata.py 将调用前执行过的终端元数据修正保存为可检查源码；当前已完成运行不会执行它。

生成及所有干预全部封存后才能执行 analyze_pilot.py、audit_new_cases.py；前者再次执行复用本轮 V3 已有分数，后者复用已完成数学审查。原始 V3 评分与事后复核分开发布。所有新测试通过后生成报告；不要在已发布 HEAD 上把 stage0 的参考提交断言改成跳过。

候选检测/GoalSpec位于FlowEvo/src/math_control；冻结评分器没有变更。报告及JSONL保留实际usage和1次TLS失败的未知用量上界，不能把上界冒充实测值。
