# 07 — 条件式模型实验

**NOT RUN**。冻结config的sha256 `17f1f0b1fc733e30c3601460ea9f9bf0074513f2d4b189894778e73067fe2d83`；冻结后没有改门槛。

| condition | passed |
|---|---|
| certified_composite | True |
| confirmation_eligible | False |
| confirmation_structure_classes | False |
| new_coverage_or_cost_advantage | False |
| correctness_tests | True |
| no_false_takeovers | True |


观察：认证组合宏1条；确认V4 eligible0（门槛12）；确认结构0（门槛3）；C-only0；本地成本优势False；193测试通过、未见错误接管。选择集V4 eligible也为0。付费实验不启动，不强行凑题，不跑MATH-500。

| 方法 | 正确率 | 输入tokens | 输出tokens | 总tokens | API调用 |
|---|---|---|---|---|---|
| A Bot-NoBank | NOT RUN | N/A | N/A | N/A | N/A |
| B Manual Tools | NOT RUN | N/A | N/A | N/A | N/A |
| C Automatic Macros | NOT RUN | N/A | N/A | N/A | N/A |

本轮实际新增调用账本为空，新增调用0、实际tokens0、新增API费用0；这只是未调用的账目，不是三种已运行模型方法的零成本优势。离线完整提交为真实计算，但“实际跳过在线LLM调用数”N/A，因为没有启动配对在线协议。Token节省N/A。

如果曾满足门槛，配置限DeepSeek Flash、temperature0、max_tokens4096、同system/base prompt、API并发≤64、本地≤12、最多120调用/200000tokens，gold反思和gold正确性重试关闭。本轮实验代码没有密钥访问或网络模型调用。发布安全扫描会在本地读取密钥文件用于检查泄漏，不上传密钥。
