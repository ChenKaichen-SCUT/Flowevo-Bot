"""Post-experiment interpretation only; never modifies frozen solving artifacts."""
import sys,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/macro_discovery_pilot'
sys.path.insert(0,str(OUT/'code'))
from common import read,write,lines,table
MARK='\n<!-- POST_EXPERIMENT_INTERPRETATION -->\n'
def append(path,text):
    p=OUT/'reports'/path;body=p.read_text().split(MARK)[0];p.write_text(body+MARK+text.strip()+'\n')

def main():
    rows=lines(OUT/'data/task_results.jsonl');base={r['task_id']:r for r in rows if r['method']=='A_NoBank'}
    metrics=read(OUT/'data/aggregate_metrics.json');paired=read(OUT/'data/paired_summary.json');cost=read(OUT/'data/cost_summary.json');screen=read(OUT/'data/macro_candidates.json');selection=read(OUT/'data/selection_manifest.json')
    mechanism=[]
    for family in ['root_invariants','polynomial_remainder']:
        for method in ['B_Compact','C_Executable']:
            group=[r for r in rows if r['macro_id']==family and r['method']==method]
            mechanism.append({'family':family,'method':method,'n':len(group),'participating':len(group),'tasks_saving_tokens':sum(r['total_tokens']<base[r['task_id']]['total_tokens'] for r in group),'tasks_increasing_tokens':sum(r['total_tokens']>base[r['task_id']]['total_tokens'] for r in group),'avoided_calls':sum(base[r['task_id']]['api_call_count']-r['api_call_count'] for r in group),'execution_seconds':sum(r['execution_seconds'] for r in group),'verification_seconds':sum(r['verification_seconds'] for r in group),'total_local_seconds':sum(r['local_total_seconds'] for r in group)})
    table(OUT/'data/mechanism_metrics.csv',mechanism)
    tool=next(r for r in paired if r['family']=='polynomial_remainder' and r['method']=='C_Executable');coverage=next(c['eligible_original_dev'] for c in screen if c['macro_id']=='polynomial_remainder')/selection['original_dev_unused_denominator'];per=coverage*tool['mean_saved_total']
    toolcost={'method':'C_Executable polynomial_remainder only; root macro disabled in hypothetical scenario','coverage_numerator':5,'coverage_denominator':1186,'eligible_mean_saved_tokens':tool['mean_saved_total'],'coverage_weighted_savings_scenario':per,'pilot_only_break_even':math.ceil(34896/per),'source_plus_pilot_break_even':math.ceil(830331/per),'status':'post-hoc scenario only, not a new evaluated routing policy'}
    write(OUT/'data/tool_only_amortization_scenario.json',toolcost)
    append('07_PAIRED_COST_ANALYSIS.md',f'''## 事后机制核查（不改运行方案）

A 14/14、9936 tokens；B 14/14、14396（+44.89%）；C 14/14、10564（+6.32%）。所有提交均未截断，因而本轮不存在截断救回解释；benefit=harm=0，只能说明这14题没有观察到正确率差异。14/14的Wilson 95%正确率区间约[78.5%,100%]，更不能证明准确率非劣。每题每组仅一次模型采样，温度0不保证固定后端或确定输出。

根宏：B/C均10/10题参与，分别只有1/10题减少token、9/10增加。B多3937，C多3578；C输入多702、输出多2876，即增加并非仅因提示长度。C确实执行并提供全部e_k和p_k，不能据此认定这些中间量替代了主要推理；模型仍要选择目标表达式，也可能重新推导。该版本计算不按目标裁剪，部分幂和无用，是后续需改的明确模块。

余式：B仅1/4节省、3/4增加，共增加523；C 4/4完整证书通过、4次调用避免，共节省2950，其中输入360、输出2590。4题本地总耗时约0.08971秒（执行0.00051、验证0.00674，其他为解析）；这些是本机单次观测而非稳定吞吐基准。局部代数计算有实测成本，不计入LLM token。

最强个例 intermediate_algebra_429：A 1275 tokens，先在x=2,-2,-1取值、求解余式的3个系数；C用QQ精确除法及独立递推得到-8x²+13x+20，再验证完整恒等式，0调用，确实替代整段求解。该题非根库来源。

最差个例 intermediate_algebra_1150：A 892 tokens，通过P'(1)/P(1)=12得到倒数和；B 3168（增加2276），改为t=1-p的多项式展开再用Vieta，答案仍12。C给原多项式对称量后2507（增加1615），也没有省下主要目标变换。这支持“通用Vieta提示可能诱导更长路径”的个例解释，不能从单次采样推出必然因果。

完整成本口径：新增API34896；沿用语料的增量采集0；若从头采集原700题再完成本轮，总830331 tokens。再包含旧V1失败建库与V2研发的历史累计1206943，均单列，未冒称本轮支出。助手会话/人工工程成本不在DeepSeek账本中可测，未假定其免费。

如果只保留余式工具、禁用根宏，事后情景为{json.dumps(toolcost,ensure_ascii=False)}。这不是新跑出的策略，只演示为什么高条件节省与低覆盖不能混为一谈。实际冻结C混合策略的原dev覆盖加权情景每总体任务仅省约1.299 tokens，源采集+本轮约需639173题摊销；条件样本本身并未节省，故这个情景不能用作扩到500的依据。
''')
    append('08_GO_NO_GO_AND_DELIVERABLES.md','''## 最终判定

选择 **继续改进**，本轮到此停止。具体区分：当前Compact与根中间量提示路线不进入扩大验证，因成本普遍增加且没有正确率收益；保留余式的“严格题意解析＋完整执行证书”作为工具路线，后续只在新的授权阶段改进覆盖及独立问题类型。不会把余式4题的确定性计算成功写成BoT提示压缩成功。

实现边界：typed IR可以表示已解析恒等式，但语境方程和自然语言推理仍unknown；macro bank中的Trigger树是描述性元数据，执行路径使用已冻结的题面识别器及机器guard，尚未做到从任意bank树自动编译完整验证器。当前两个候选实际执行条件已测试；下一阶段若扩展树语义，必须增加未知状态/否定/组合guard的验证，而不能假设通用推理程序已完成。
''')
    verdict=read(OUT/'data/go_no_go.json');verdict.update(prompt_route='do_not_expand_current_compact_or_root_intermediate_version',tool_route='improve_question_parser_and_full_task_certificate_coverage_in_future_authorized_round',observed_total_token_change_B=4460,observed_total_token_change_C=628,accuracy_benefit_observed=0,accuracy_harm_observed=0);write(OUT/'data/go_no_go.json',verdict)
    print('Post-experiment interpretation written; no new API calls.')
if __name__=='__main__':main()
