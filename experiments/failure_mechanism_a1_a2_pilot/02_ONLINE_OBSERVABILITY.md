# API行为与实际在线可观察性

调用前查询只读/models接口，HTTP200，未产生模型生成。官方依据：[Thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/)、[Chat completion](https://api-docs.deepseek.com/api/create-chat-completion/)、[Models](https://api-docs.deepseek.com/api/list-models/)、[Pricing](https://api-docs.deepseek.com/quick_start/pricing/)。检索时API说明max_tokens为上限，thinking默认enabled/high；thinking模式temperature不影响采样，保留历史temperature=0不能宣称确定性。top_p继续省略。

本轮B0、B1、B2和提醒请求全部使用同样的SSE传输及stream_options.include_usage。123份完成响应均观察到reasoning_content/content分离返回和实际usage；所有这些响应都有reasoning_tokens明细，该值已包含在completion_tokens中。final_content_tokens=completion_tokens-reasoning_tokens，未把推理重复累加。finish_reason=length判不完整，stop还必须具备可提取的最终答案。

B2在25/40题、41个候选事件中可以定位接收时刻，见pilot_stream_candidate_timing.jsonl及raw/*.stream.json。时间是客户端收到候选片段的时间，不是内部形成答案的时间。连续接收不会自动证明候选正确。B2所有40题最终完成，候选出现未触发任何提前终止。

本轮没有取消流或声称保持隐藏推理状态。A1若触发，会在B2未完成后发送独立短请求，把可见题目、候选和有限文本作为普通上下文；这会重新消耗tokens。普通无工具请求不能把重发reasoning_content当作原始内部状态续接。

历史reasoning不可用的500个基础响应显式标记不可观察。历史F1/F2确认均来自有文本的响应；gold等价证明仅用于离线标注。A2只用题面GoalSpec及提交文本，未访问reference模块或评分结果。匿名化不是本任务需求，原题及模型回答均保留；密钥文件和认证头不进入证据或上传。

一次TLS中断未收到usage，保留pending/error记录后才按用户“部分交付可重跑”要求补跑同一请求；没有变更模型、题目、阈值或思考强度。详见transport_recovery_plan.json和infrastructure_attempts.jsonl。提供方只返回deepseek-flash别名，无法据此固定后端权重版本。
