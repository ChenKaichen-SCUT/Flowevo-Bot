# Stage4前置：API可行性实测

文档与2026-10-11（Asia/Shanghai）实测分开记录：

| 能力 | 证据与结论 |
|---|---|
| 观察reasoning | SSE有reasoning_content，能在最终答案前观察文本；不是全部内部计算状态 |
| Prefix输入 | Beta末尾assistant可设置prefix=true并提供reasoning_content；两项nonce测试均返回正确423，证明字段可作为可用上下文 |
| 普通多轮 | 官方说明，无tools的普通后续轮会忽略旧reasoning；本轮不把这种调用当作续接 |
| 强制最终前缀 | Beta content前缀测试被接受；只作为可行性测试，不在主实验单独改变某分支采样配置 |
| 客户端取消 | 在收到47个reasoning字符后关闭连接；未收到[DONE]或最终usage。后端实际停止时刻、实际计费token不可确认 |
| 无损状态续接 | 未证明；没有KV状态句柄或可验证的内部状态恢复，重传前缀会再次计入输入 |
| 可核算替代方案 | 服务器max_tokens完成一阶段，读取最终usage，再发完整记账的续写；已在独立题实测 |

取消测试的精确usage标记unavailable，预算预留输入UTF-8字节上界+聊天封装裕量+128输出上限，共1247。没有用47字符换算成精确token，也没有用关闭socket宣称省钱。

API正常模型返回`deepseek-flash`；实际fingerprint见summary。温度参数在thinking模式不起作用；本轮沿用默认high，未使用种子保证。价格用官方峰值未缓存输入USD0.3/M、输出USD1.2/M作保守估算，不是支付账单。

- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [Chat Prefix Completion](https://api-docs.deepseek.com/guides/chat_prefix_completion/)
- [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)
- [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)

审计证据：`evidence/api_feasibility.json`及`raw/audit_*.json/.sse.gz`。文档列出的功能只作为接口依据，实际控制能力以这里的请求响应为准。
