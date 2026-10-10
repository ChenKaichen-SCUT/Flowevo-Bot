# 失败、评分错误与负迁移

本轮B2完整40题，未确认真实解题错误。冻结V3有两个异常题：

- prealgebra_66：0.05*(60-48)*100=60 cents；模型正确。V3没有从“how many more cents”识别请求单位，导致currency quantity与裸数字参考类型不符。B0/B2/Generic的三份实际响应均保留incorrect原分数，另附精确复核。
- precalculus_47：x=cos(2theta)趋于-1而y=cos(2theta)tan(theta)发散，渐近线x=-1。B2正确给出x=-1及r*cos(theta)=-1的等价形式；V3拒绝括号说明，保留Unknown。

新发现已写入posthoc_adjudications.jsonl，没有修补本轮冻结评分器，也没有回头重跑生成来让格式更适合评分。

低预算geometry_75、geometry_232没有完整输出；B1/B2均补足。Generic却把B2已完成且数学正确的geometry_75、geometry_232、precalculus_47再次带入验证，4096上限内未给正文答案，数学复核后净损失3题。

geometry_75的显式CN=4与Asy的N=(5,0)坐标冲突，Generic反复讨论图示与文字；正确的文字条件解为240/13。geometry_232反复检查无滑动位移符号，候选55mm已出现；precalculus_47反复检查极坐标/直角坐标等价形式，候选x=-1已出现。new_failure_mechanisms.jsonl保存原位置和上下文，5份未完成响应/3道题可见正确候选，2份Generic响应有明显重复验证，1题有图文冲突。

Generic采用额外4096上限的新请求并选择其最终输出，没有“失败时保留原正确答案”的隐藏兜底。因此负迁移同时受额外重采样和修复预算限制影响，不能推广为任何自检提示都会更差。当前证据反对无条件替换已完整的B2回答；无需新增复杂控制器即可避免这三次退化。

A1/A2从未真实触发，观测误改0并不证明触发后安全。历史错误率低、当前题集接近上限、评分器覆盖仍不完备，是研究结论的重要限制。
