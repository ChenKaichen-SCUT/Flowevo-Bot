# 冻结的小预算三组实验

14道独立开发题，三组共42份提交，实际38次API、34896 tokens，0生成调用、0重试、0gold反思。硬预算120/200000均未触及。A/B/C共享题目、系统提示和输出要求；C余式以完整证书直接答题，tokens和API=0；C根提供验证中间量后仍调用同一模型。

| family | method | n | correct | accuracy | input_tokens | output_tokens | total_tokens | api_call_count | unknown | truncated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | A_NoBank | 14 | 14 | 1.0 | 1412 | 8524 | 9936 | 14 | 0 | 0 |
| ALL | B_Compact | 14 | 14 | 1.0 | 2444 | 11952 | 14396 | 14 | 0 | 0 |
| ALL | C_Executable | 14 | 14 | 1.0 | 1754 | 8810 | 10564 | 10 | 0 | 0 |
| root_invariants | A_NoBank | 10 | 10 | 1.0 | 1052 | 5934 | 6986 | 10 | 0 | 0 |
| root_invariants | B_Compact | 10 | 10 | 1.0 | 1852 | 9071 | 10923 | 10 | 0 | 0 |
| root_invariants | C_Executable | 10 | 10 | 1.0 | 1754 | 8810 | 10564 | 10 | 0 | 0 |
| polynomial_remainder | A_NoBank | 4 | 4 | 1.0 | 360 | 2590 | 2950 | 4 | 0 | 0 |
| polynomial_remainder | B_Compact | 4 | 4 | 1.0 | 592 | 2881 | 3473 | 4 | 0 | 0 |
| polynomial_remainder | C_Executable | 4 | 4 | 1.0 | 0 | 0 | 0 | 0 | 0 | 0 |

参与率：B在全部选中题注入短思路，C全部运行本地宏；余式直接完成，根只替代中间计算。集合是经过条件筛选的14题规模附近的小样本，不能当作MATH总体正确率。源题自匹配与负例属于付费前独立检验，没有只挑正确开发结果。

记录schema含run_id/task/subject/difficulty/method/macro_id/type/trigger/guard/attempt/verified/fallback/prompt_hash、完整usage、调用数、latency、answer、offline_correct、parse_status、truncated、gold_exposed及局部计算/核验时间。api_calls保存原始请求响应；submissions保存评分前seal；submission_barrier证明先提交后读label。
