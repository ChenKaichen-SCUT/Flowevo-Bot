# RMMD 状态核对与预注册

上一轮本地与远端 main 均为 206a6caa6954283e41f219d6c61f84f6904eb5f8，开始时仅指引.txt变化。原始审计见 evidence/version_audit.json。本轮位于独立 macro_discovery_pilot，不覆盖旧实验或上游代码。snapshots/protected_files.json 固定3414个旧文件，最终逐项复核。

研究问题：从已确认首次正确的真实训练解法中，能否找出具有结构变化的数学操作，并区分短提示与确定性执行的收益？本轮是受限工程化识别器的可行性实验，不宣称自动发现新的数学定理。

硬上限120次请求、200000新API tokens；实际计划14题、42份提交，其中可直接验证的余式题无需C组API。API16并发、CPU12并发，低于用户允许的64/12。DeepSeek Flash，温度0，max_tokens4096，与基线同一system和结束格式。没有额外“简洁回答”指令，没有gold反思或正确性重试。

付费前固定代码、宏、题单、预算和标签文件hash，保存prepaid_freeze与runtime_before_paid.zip。标签内容仅在全部提交seal完成后由离线评分块读取。训练解法正确性来自独立旧评分复核；其答案或官方解答不进入新求解器。所有新API请求和完整安全响应（包括reasoning_content）保存。

禁止完整MATH500、禁止根据本轮结果再调提示或补样本；报告后停止。预算用实际usage加所有在途请求的保守上界，未知账单保留pending并停止，无盲目重发。
