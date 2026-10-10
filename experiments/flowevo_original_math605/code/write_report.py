from common import *
from native import runner, score
from collections import Counter
import csv

def main():
    summary=read(OUT/'summary.json')
    old=read(OUT/'historical_16384/summary.json')
    rows=jl(OUT/'results.jsonl')
    checks={}
    checks['unique_605']=len(rows)==len({r['task_id'] for r in rows})==605
    checks['splits']=dict(Counter(r['split'] for r in rows))=={'validation':119,'test':486}
    checks['native_correct_count']=summary['groups']['all']['correct']==sum(r['passed'] for r in rows)
    checks['usage_sums']=all(r['total_tokens']==r['input_tokens']+r['output_tokens'] and r['output_tokens']==r['reasoning_tokens']+r['final_content_tokens'] for r in rows)
    checks['physical_ledger']=summary['known_billed_tokens']==sum(a['total_tokens'] for a in map(read,(OUT/'attempts').glob('*.json')) if a['usage_known'])
    checks['gold_retries_disabled']=all(e['retries']==0 for e in read(OUT/'native_runner/_checkpoint_math_ours.json')['episodes'])
    checks['original_native_summary']=read(OUT/'native_runner/summary.json')['math']['ours']['passed']==summary['groups']['all']['correct']
    checks['native_error_and_usage_semantics']=all(
        (r['native_reported_tokens']==0 and r['native_runner_feedback']=='error: OpenRouter returned empty content.')
        if r['empty_final_content'] else
        (r['native_reported_tokens']==r['total_tokens'] and not r['native_runner_feedback'].startswith('error:'))
        for r in rows)
    checks['compiled_library']=len(read(OUT/'native_runner/_checkpoint_math_ours.json')['library']['solutions'])==summary['groups']['all']['correct']
    checks['frozen_files_unchanged']=all(sha(ROOT/p)==h for p,h in read(OUT/'evidence/pre_api_freeze.json')['files'].items())
    checks['old_experiment_files_unchanged']=all(sha(ROOT/e['path'])==e['sha256'] for e in read(OUT/'evidence/previous_upload_manifest.json')['files'])
    checks['sealed_responses']=all(sha(OUT/p)==h for p,h in read(OUT/'GENERATION_SEALED.json')['files'].items())
    assert all(checks.values()),checks
    save('evidence/artifact_checks.json',dict(at=now(),checks=checks,passed=len(checks),total=len(checks)))
    current={r['task_id']:r for r in rows}
    historical=jl(OUT/'historical_16384/results.jsonl')
    paired=[]
    for h in historical:
        r=current[h['task_id']]
        paired.append(dict(task_id=r['task_id'],split=r['split'],subject=r['subject'],
            native2048_passed=r['passed'],historical16384_native_passed=h['passed'],
            native2048_tokens=r['total_tokens'],historical16384_tokens=h['total_tokens']))
    lines('budget_comparison.jsonl',paired)
    with (OUT/'cost_breakdown.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['run','split','n','correct','input_tokens','output_tokens','reasoning_tokens','total_tokens'])
        writer.writeheader()
        for name,groups in [('new_native2048',summary['groups']),('historical16384_native_regrade',old['groups'])]:
            for split,g in groups.items():
                writer.writerow(dict(run=name,split=split,**{key:g[key] for key in writer.fieldnames[2:]}))
    g=summary['groups']['all']
    table='\n'.join(f"| {label} | {v['correct']}/{v['n']} | {100*v['accuracy']:.2f}% | {v['input_tokens']:,} | {v['output_tokens']:,} | {v['total_tokens']:,} |" for label,v in [('验证集',summary['groups']['validation']),('测试集',summary['groups']['test']),('合计',g)])
    subject_table='\n'.join(f"| {subject} | {v['correct']}/{v['n']} | {100*v['accuracy']:.2f}% | {v['total_tokens']:,} |" for subject,v in summary['subjects'].items())
    versions=dict(Counter(r['model_version'] for r in rows))
    fingerprints=dict(Counter(r['backend_revision'] for r in rows))
    provenance=read(OUT/'evidence/source_provenance.json')
    report=f'''# 原始 FlowEvo：同一批 605 题的原始提取器成绩与 token 消耗

本次新运行：**{g['correct']}/605（{100*g['accuracy']:.2f}%）**，API 实际已知消耗 **{summary['known_billed_tokens']:,} token**。正确数量严格按原版提取器与评分器计算，没有 V3 修正或人工改判。

## 运行范围与配置

- 复用上轮恢复的 AFlow 官方 605 题：验证集 119、测试集 486；题目和划分文件完全不变。它们不是 605 道全新的独立测试题，也不声称恢复了论文的全部 617 题。
- FlowEvo 固定上游提交 `{provenance['upstream_commit']}`，原始 runner 和 loader 逐字保存在 `evidence/upstream_*.py`。
- 执行原始 `ours` 条件，唯一算法配置覆盖为 `retry=False`，延续用户此前关闭 gold 反思的要求。因此本结果应称为“原始 FlowEvo、关闭 gold 反思”，不是开启 gold 反馈重试的官方完整条件。
- 使用 DeepSeek Flash（通过工作区 `miyao.txt` 读取密钥，不保存密钥），原生每次输出上限 **2048 token**；原始 system/user prompt、temperature=0。不发送 thinking/reasoning_effort，沿用上一轮 provider 默认设置；没有种子保证或后端版本固定。
- 原版 MATH 检索分支不注入 skill。本轮调用独立，不加载历史策略库；原版 runner 仍按顺序编译判对解答。题目 ID 唯一，数学分支不会把这些解答注入后续题。
- API 并发峰值 **{summary['peak_api_concurrency']}**；本地评分单进程（不超过用户 12 并行上限）。每题一次生成，没有依据正确性或截断状态重试；仅网络失败允许最多一次传输恢复。
- 为支持并发和完整 token 账本，先以原始 prompt/settings 进行 streaming 调用，封存全部响应后，原样执行上游 `run_condition` 顺序读取这些响应。读取时逐条核对原版实际发出的 prompt、temperature、max_tokens，评分、编译和空输出报错保持原版行为；读取封存响应不再次付费。

## 新运行结果（2048 token 上限）

| 划分 | 原版判对 | 正确率 | 输入 tokens | 输出 tokens | 总 tokens |
|---|---:|---:|---:|---:|---:|
{table}

| 学科 | 原版判对 | 正确率 | 总 tokens |
|---|---:|---:|---:|
{subject_table}

平均每题 **{g['mean_tokens']:.2f} token**。输出中 reasoning tokens 为 **{g['reasoning_tokens']:,}**，最终文本 tokens 为 **{g['final_content_tokens']:,}**；reasoning 已包含在输出及总量中，不能再相加。完成原因：`{json.dumps(g['finish_reasons'])}`；最终文本为空 **{g['empty_final_content']}** 题。截断仍按原版提取与比较评分，没有事后恢复。

实际 HTTP 尝试 **{summary['http_attempts']}** 次，usage 不明尝试 **{summary['unknown_usage_attempts']}** 次。API 账本的已知实际 token 为 **{summary['known_billed_tokens']:,}**，605 个逻辑结果 token 为 **{g['total_tokens']:,}**；二者分列以便传输重试存在时不漏计。

原版客户端在最终文本为空时先抛异常，导致原版 runner 未累加该次 usage。它自己报告 **{g['native_reported_tokens']:,}** token，漏计 **{summary['native_token_undercount']:,}** token。本报告以 API usage 账本为实际消耗依据，原版未修正汇总保留在 `native_runner/summary.json`。

## 原始评分口径

参考答案使用 `loader._extract_math_answer`；模型输出使用 `runner.extract_math_answer`；两者通过 `runner._normalize_answer` 后按字符串相等判分，并由原始 `runner.verify` 实际执行。

这套提取器保留原版所有行为，包括取第一个 boxed、不能完整匹配嵌套花括号、答案句号截断及最后数字回退。因此“原版判对”不等同于人工数学审定正确率，既可能漏判，也可能误判；例如不同分母的两个分数可能被截成同一个 `\\frac{{1`。本轮没有修复这些行为。

## 历史 16384 输出的独立重评（没有重跑）

上轮 605 题的原始 prompt 与本轮一致，但输出预算为 16384。仅使用同一套原始提取器重新评分得到 **{old['groups']['all']['correct']}/605（{100*old['groups']['all']['correct']/605:.2f}%）**；验证集 **{old['groups']['validation']['correct']}/119**，测试集 **{old['groups']['test']['correct']}/486**。其原运行 token 为 **{old['groups']['all']['total_tokens']:,}**。本次重评分新增 API 调用及 token 均为 **0**。

历史 16384 输出和新 2048 输出是两次独立生成，不能把分数差全部归因于预算变化；本轮没有重跑已完成的 16384 实验。

## 复现与证据

运行命令（工作区根目录）：

```bash
Flowevo-Bot/.venv/bin/python experiments/flowevo_original_math605/code/generate.py
Flowevo-Bot/.venv/bin/python experiments/flowevo_original_math605/code/replay_native.py
Flowevo-Bot/.venv/bin/python experiments/flowevo_original_math605/code/regrade_existing.py
Flowevo-Bot/.venv/bin/python experiments/flowevo_original_math605/code/write_report.py
```

`generate.py` 对已封存的 605 个结果校验哈希后直接返回，不重新调用 API。复现只需保留当前目录和上一轮 `experiments/aflow_math617_capability_probe` 的数据文件；不需要联网下载题目。

- `results.csv` / `results.jsonl`：605 题预测提取值、参考提取值、原版判分、token 和响应哈希。
- `raw/*.json` / `raw/*.sse.gz`：完整请求、reasoning、最终输出、finish_reason、API usage 与原始流。
- `attempts/*.json` / `api_calls.jsonl`：逐物理请求、逐逻辑调用账本。
- `native_runner/`：真正执行上游 runner 的 checkpoint、汇总与报告。
- `historical_16384/`：历史输出原版重评分；`budget_comparison.jsonl`：605 题配对结果；`cost_breakdown.csv`：预算与划分汇总。
- `evidence/pre_api_freeze.json`：生成前代码、配置与数据哈希；`GENERATION_SEALED.json`：评分前封存的全部响应。
- `evidence/protocol_checks.json`：8 项协议检查通过；`evidence/artifact_checks.json`：{len(checks)} 项完整性检查通过，包括全部历史发布文件未改动。

实际返回模型计数：`{json.dumps(versions)}`。后端 fingerprint 计数：`{json.dumps(fingerprints)}`。
'''
    (OUT/'README.md').write_text(report)
    save('run_manifest.json',dict(created_at=now(),upstream_commit=provenance['upstream_commit'],
        previous_published_commit='046216f51de2258adfecb6ed8ab2046891ad8e22',
        config_sha256=sha(OUT/'config.json'),dataset_sha256=sha(PREVIOUS/'data/public_tasks.jsonl'),
        n=605,groups=summary['groups'],source_files_unchanged=True,new_calls=summary['http_attempts'],
        files={str(p.relative_to(OUT)):sha(p) for p in [OUT/'results.jsonl',OUT/'summary.json',OUT/'api_calls.jsonl',OUT/'README.md']}))
    print(json.dumps(dict(checks=checks,summary=summary['groups']['all']),ensure_ascii=False))

if __name__=='__main__':
    main()
