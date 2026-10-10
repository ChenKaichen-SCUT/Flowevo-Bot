# AFlow公开冻结工作流检查

已恢复作者结果档案中的`MATH/graphs_test/round_5/graph.py`、prompt以及template operator，逐文件哈希见evidence/official_workflow_audit.json。两份历史测试CSV各486行、验证CSV119行与当前数据集合一致。已进行Python语法解析；没有实际执行/计分/付费调用。

该流程包括：Programmer生成并运行Python（带执行错误反馈重试）、Custom整理代码结果、独立详细解答、另外两份解答、ScEnsemble通过模型选择四份文本之一。它依赖历史MetaGPT ActionNode/provider接口，模板还引用Gsm8K路径；当前独立AFlow库使用不同接口。不能把当前算子直接替换后称为原封不动的官方运行。

本轮验证基线已118/119，多候选只恢复一次截断，尚无完整数学错误或选择能力缺口。按指引的可选条件，本轮不追加迁移后的付费对照，也不启动完整MCTS。不是宣称工作流永远不可运行，而是本轮没有足够研究信号且未经验证的接口替换会影响归因。

因此官方工作流相对DeepSeek基线的优劣为“未测”，调用数与tokens均0。原论文优化/执行模型与本实验不同，不引用原文正确率当作同条件比较。原始源文件和档案已随交付保存。
