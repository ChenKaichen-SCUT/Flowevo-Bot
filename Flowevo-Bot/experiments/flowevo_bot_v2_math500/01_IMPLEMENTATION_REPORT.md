# V2 实现与验证

本轮完成独立版本的算法实现、离线测试、真实蒸馏及20题三组对照；0 active触发停止条件，未执行正式500。原FlowEvo、BoT、旧实验结果、旧银行与旧评分均保留。

新增核心模块：src/flowevo_bot/v2/evaluator.py（封存后分级评分）、features.py（词面/数学结构拆分）、skills.py（递归逻辑schema和数学guard）、distiller.py（多阶段真实变换证据蒸馏）、admission.py（shadow/准入/生产路由）、client.py（单预算、安全原始日志、429/503有界基础设施重试、待定请求日志）。执行入口 scripts/run_v2_research.py；离线历史复核 scripts/recheck_v2_history.py；报告 scripts/report_v2_research.py。

为了保留历史可重放，V2不覆盖旧v1 evaluator/runner；V2研究脚本明确调用新模块。原CLI仍为v1，使用V2必须运行此处新入口。原FlowEvo的gold-free数学路径保持关闭gold反思及正确性驱动重试，MATH/GSM技能注入此前修改保留。

各阶段技术细节在reports/01–04，完整新旧卡对照与真实来源在data/。不改Router数值门槛；独立shadow验证可绕过生产成本路由采集开发证据，但不能生产强制注入。

所有模型请求/完整响应（含服务端reasoning_content和usage）保存在calls/，无请求头/密钥。单一API线程池上限64，本地评分/结构提取进程上限12，进程CPU亲和性限制12个核。未记录任何数学重试；基础设施仅明确429/503最多3次尝试，超时/未知完成状态保留journal并停止，避免盲目重复计费。此次所有63调用一次成功，输出截断均保留并计费。

预付费测试87通过；增加蒸馏同义词/危险对称压缩回归后完整测试90通过（tests/final_tests.log及Junit）；原FlowEvo两项gold-free回归通过。0.2.0 wheel构建、隔离导入、判分smoke和compileall通过，见tests/build_verification.json。历史源代码归档 snapshots/source_before_v2.zip，实际dev运行代码归档 snapshots/runtime_used_for_dev.zip，原历史文件SHA快照及最终复核在evidence/。蒸馏各次调用前未单独归档当时全模块代码，api_calls如实保留code_version=null及原始请求hash；不能倒填后来的dev代码hash。密钥miyao.txt只用于内存授权，不发布。

局限：数学解析保守unknown、当前Guard没有执行证明、计数trigger部分词面、训练轨迹正确性依赖历史评分且数学步骤未被形式化证明、source/dev语义独立性不能完全保证、单次DeepSeek别名采样无法锁定后端版本。输出长度截断可改变表面正确率，因此逐题区分预算失败和完成后的数学错误。
