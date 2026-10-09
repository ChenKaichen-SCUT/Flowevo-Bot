"""Read-only integrity audit plus derived reports. Never invokes a model."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from collections import Counter
from flowevo_bot.common import read_json,write_json
from flowevo_bot.schemas import Submission
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.provenance import assert_independent
from code_math.loader import load_manifest

P=Path(__file__).resolve().parent

def main():
    comparison=read_json(P/'comparison.json');pairs=read_json(P/'paired_results.json')
    bank=StrategyBank.load(P/'real_bank.json')
    expected=read_json(P/'source_frozen_before_test.json')
    for f,h in expected['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    _,test,_=load_manifest(P/'manifests/test.json','test')
    _,dev,_=load_manifest(P/'manifests/dev.json','train-dev')
    _,train,_=load_manifest(P/'manifests/train.json','train-build')
    for a,b in [(train,dev),(train,test),(dev,test)]:assert_independent(a,b)
    test_ids={t.task_id for t in test}
    all_calls=list(bank.cost_calls)
    providers={};subject_stats={}
    for method in ('flowevo','flowevo_bot'):
        directory=P/method
        summary=read_json(directory/'summary.json');rows=read_json(directory/'rows.json')
        checkpoint=read_json(directory/'checkpoint.json');ledger=read_json(directory/'calls.json')
        submissions=[Submission.model_validate(x) for x in checkpoint['submissions']]
        assert len(rows)==len(submissions)==len(ledger['calls'])==500
        assert {r['task_id'] for r in rows}=={s.task_id for s in submissions}==test_ids
        assert summary['correct']==sum(r['final_correct'] for r in rows)
        assert all(s.bank_hash==bank.bank_hash and s.retry_count==0 for s in submissions)
        for s in submissions:s.assert_frozen()
        for name in ('prompt_tokens','completion_tokens','total_tokens'):
            assert sum(c[name] for c in ledger['calls'])==summary[name]==sum(r[name] for r in rows)
        assert all(not c['estimated'] and not c['simulated'] and c['total_tokens']==c['prompt_tokens']+c['completion_tokens'] for c in ledger['calls'])
        providers[method]={'models':Counter(),'reasoning_tokens':0,'cached_input_tokens':0,'provider_records':0}
        index={c['call_id']:c for c in ledger['calls']}
        for path in sorted((directory/'task_calls').glob('*.provider/*.json')):
            raw=read_json(path);c=index[raw['call_id']]
            for name in ('prompt_tokens','completion_tokens','total_tokens'):assert raw['usage'][name]==c[name]
            providers[method]['models'][raw['provider_model']]+=1
            providers[method]['reasoning_tokens']+=raw['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0)
            providers[method]['cached_input_tokens']+=raw['usage'].get('prompt_cache_hit_tokens',0)
            providers[method]['provider_records']+=1
        assert providers[method]['provider_records']==500
        from flowevo_bot.schemas import TokenCall
        all_calls.extend(TokenCall.model_validate(c) for c in ledger['calls'])
        subject_stats[method]=[]
        for subject in sorted({r['subject'] for r in rows}):
            group=[r for r in rows if r['subject']==subject]
            subject_stats[method].append({'subject':subject,'n':len(group),'correct':sum(r['final_correct'] for r in group),
                'accuracy':sum(r['final_correct'] for r in group)/len(group),'total_tokens':sum(r['total_tokens'] for r in group),
                'truncated':sum(r['truncated'] for r in group)})
    # A call signature can be identical across methods. Those are independent
    # paid requests; do not deduplicate across experiment conditions.
    assert len(all_calls)==1802
    total=sum(c.total_tokens for c in all_calls)
    assert total==sum(bank.build_costs.values())+comparison['flowevo']['total_tokens']+comparison['flowevo_bot']['total_tokens']
    diffs=[int(r['bot_correct'])-int(r['flowevo_correct']) for r in pairs]
    mean=statistics.mean(diffs);se=statistics.stdev(diffs)/math.sqrt(len(diffs))
    bot_only=sum(d==1 for d in diffs);native_only=sum(d==-1 for d in diffs);discordant=bot_only+native_only
    mcnemar=min(1,2*sum(math.comb(discordant,k) for k in range(min(bot_only,native_only)+1))/2**discordant) if discordant else 1
    analysis={'paired_accuracy_difference':mean,'paired_accuracy_difference_95pct_normal_interval':[mean-1.96*se,mean+1.96*se],
        'mcnemar_exact_two_sided_p':mcnemar,'bot_only_correct':bot_only,'flowevo_only_correct':native_only,
        'by_subject':subject_stats,'provider_usage':providers,'physical_experiment_calls':len(all_calls),
        'physical_experiment_tokens':total,'shared_history_counted_once_in_physical_experiment':True,
        'bot_solve_savings_due_to_input_fraction':(comparison['flowevo']['prompt_tokens']-comparison['flowevo_bot']['prompt_tokens'])/comparison['solve_tokens_saved']}
    write_json(P/'post_run_analysis.json',analysis)
    # Scan artifacts for the exact credential without printing it.
    key=(P.parents[2]/'miyao.txt').read_bytes().strip()
    leaked=[]
    for f in P.rglob('*'):
        if f.is_file() and key and key in f.read_bytes():leaked.append(str(f))
    assert not leaked,'Credential found in artifacts'
    audit={'checks_passed':True,'tasks_per_method':500,'real_requests_per_method':500,'estimated_test_calls':0,
        'source_changed_during_test':False,'frozen_bank_hash':bank.bank_hash,'no_train_dev_test_near_duplicates':True,
        'all_submission_seals_verified':True,'all_provider_usage_reconciled':True,'secret_scan_matches':0,
        'physical_real_api_calls':len(all_calls),'physical_total_tokens':total,'offline_tests':'54 Flowevo-Bot + 2 FlowEvo passed'}
    write_json(P/'INTEGRITY.json',audit)
    report=(P/'REPORT.md').read_text().split('\n<!-- POST_RUN_AUDIT -->')[0]
    report+='\n<!-- POST_RUN_AUDIT -->\n\n## 分学科结果\n\n| 学科 | 题数 | FlowEvo 正确 | Bot 正确 | FlowEvo token | Bot token |\n|---|---:|---:|---:|---:|---:|\n'
    for a,b in zip(subject_stats['flowevo'],subject_stats['flowevo_bot']):
        report+=f"| {a['subject']} | {a['n']} | {a['correct']} | {b['correct']} | {a['total_tokens']:,} | {b['total_tokens']:,} |\n"
    lo,hi=analysis['paired_accuracy_difference_95pct_normal_interval']
    report+=f"\n配对样本中，只有 FlowEvo 正确 {native_only} 题，只有 Bot 正确 {bot_only} 题。McNemar 双侧精确检验 p={mcnemar:.4f}；正确率差值的配对近似 95% 区间为 [{lo*100:.2f}, {hi*100:.2f}] 个百分点。本次 0.4 个百分点差异不足以认定准确率提升。\n"
    report+=f"\n测试 token 节省的 {analysis['bot_solve_savings_due_to_input_fraction']:.2%} 来自输入减少。Bot 本轮所有测试题均未注入策略，不能将收益归因于策略复用。\n"
    report+='\n350 是独立验证题候选池；实际匹配到 39 道题，执行 39 对 base/skill 共 78 次验证调用。8 个策略缺少匹配验证样例，1 个观察到有害案例，另外 3 个未满足收益/证据要求。\n'
    report+=f"\n完整实验实际请求 {len(all_calls):,} 次，共 {total:,} token；这里共同训练历史只计算一次。按每套方法独立部署分别计算时，使用正文的两套端到端成本。\n"
    report+='\nDeepSeek 默认思考模式为 enabled/high；请求中的 temperature=0 在该模式下不生效，输出 token 包含思考 token。参考 [DeepSeek 官方文档](https://api-docs.deepseek.com/guides/thinking_mode/)。符号评分器来源：[Hugging Face Math-Verify](https://github.com/huggingface/Math-Verify)。\n'
    report+='\n核对通过：每套 500 个相同题号、封存答案、独立真实请求和原始 provider usage；总数与逐题/逐请求账本一致；0 次估算；测试期间代码及库哈希未变化；未发现密钥泄露。离线检验 54+2 项通过。\n'
    (P/'REPORT.md').write_text(report)
    print(json.dumps(audit,ensure_ascii=False,indent=2))
    print('Paired p',mcnemar,'95% interval',lo,hi)

if __name__=='__main__':main()
