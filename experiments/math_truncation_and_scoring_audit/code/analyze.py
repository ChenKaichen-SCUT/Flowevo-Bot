"""Offline only; require generation seal before opening labels and assessing new answers."""
from prepare import ROOT,OUT,read,sha
import sys,json,csv,concurrent.futures as cf
from collections import Counter
sys.path.insert(0,str(ROOT/'FlowEvo-Recovery/src'))
from flowevo_recovery.math_scoring_v2 import grade,extract,complete
from flowevo_bot.common import write_json,digest

def csvwrite(name,rows):
 if not rows:(OUT/name).write_text('task_id\n');return
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def jsonlines(name,rows):
 (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
def main():
 seal=read(OUT/'evidence/generation_complete_seal.json');assert sha(OUT/'api_calls.jsonl')==seal['api_calls_sha256']
 baseline=read(OUT/'evidence/baseline_500.json');bmap={x['task_id']:x for x in baseline};oldgrades=read(OUT/'evidence/rescored_500_detailed.json');gmap={x['task_id']:x for x in oldgrades}
 calls=[json.loads(s) for s in (OUT/'api_calls.jsonl').read_text().splitlines()];items=[]
 for r in calls:
  tid=r['task_id'];choice=r['response']['choices'][0]
  assert r['response_hash']==digest(r['response']) and r['request_hash']==digest(r['request'])
  assert {k:v for k,v in r['request'].items() if k!='max_tokens'}=={k:v for k,v in bmap[tid]['provider']['request'].items() if k!='max_tokens'}
  items.append({'task_id':tid,'question':bmap[tid]['question'],'solution':choice['message'].get('content') or '', 'gold_answer':bmap[tid]['gold_answer'],'truncated':choice['finish_reason']=='length'})
 with cf.ProcessPoolExecutor(max_workers=12) as pool:grades=list(pool.map(grade,items))
 percall=[]
 for c,i,g in zip(calls,items,grades):
  choice=c['response']['choices'][0]
  percall.append({'task_id':c['task_id'],'budget':c['budget'],'finish_reason':choice['finish_reason'],'complete_final_answer':choice['finish_reason']=='stop' and complete(i['solution']),'visible_chars':len(i['solution']),'reasoning_chars':len(choice['message'].get('reasoning_content') or ''),'grade':g,'input_tokens':c['input_tokens'],'output_tokens':c['output_tokens'],'total_tokens':c['total_tokens'],'reasoning_tokens':c['reasoning_tokens'],'response_model':c['response'].get('model'),'response_id':c['response'].get('id'),'raw_evidence':'raw/'+c['task_id']+'_'+str(c['budget'])+'.json','request_hash':c['request_hash'],'response_hash':c['response_hash'],'solution':i['solution']})
 write_json(OUT/'evidence/new_calls_offline_scores.json',percall)
 selected={x['task_id']:x for x in sorted(percall,key=lambda x:x['budget'])}
 escalation=read(OUT/'evidence/escalation_decision.json')['eligible_task_ids']
 assert set(x['task_id'] for x in percall if x['budget']==16384)==set(escalation)
 results=[]
 for tid in read(OUT/'truncated_27_task_ids.json'):
  b=bmap[tid];s=selected[tid];g=s['grade'];hist=b['provider']
  category=('still_truncated' if s['finish_reason']=='length' else 'recovered_correct' if g['correct'] is True else 'complete_math_wrong' if s['complete_final_answer'] and g['correct'] is False else 'complete_parse_failure' if s['finish_reason']=='stop' and g['status'].startswith(('unknown_parse','missing','incomplete')) else 'unknown')
  results.append({'task_id':tid,'subject':b['subject'],'level':b['level'],'question':b['question'],'gold_answer':b['gold_answer'],'reference_solution':b['reference_solution'],'original_correct':False,'original_answer':b['original_answer'],'original_finish_reason':hist['finish_reason'],'original_usage':hist['usage'],'original_visible_chars':len(b['solution']),'selected_budget':s['budget'],'selected_correct':g['correct'],'category':category,'selected':s,'all_attempts':[x for x in percall if x['task_id']==tid],'selection_reason':'last executed rung, observable completeness gate only','code_version':read(OUT/'preflight.json')['reference_commit'],'evaluator_sha256':sha(ROOT/'FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py')})
 jsonlines('truncation_task_results.jsonl',results)
 cases=[]
 for b in baseline:
  if not b['original_correct'] and not b['truncated']:
   cases.append({**b,'new_grade':gmap[b['task_id']],'extra_api_calls':0,'evidence':'evidence/baseline_500.json#'+b['task_id'],'code_version':read(OUT/'preflight.json')['reference_commit'],'evaluator_sha256':sha(ROOT/'FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py')})
 jsonlines('nine_scoring_cases.jsonl',cases)
 all500=[]
 for b in baseline:
  tid=b['task_id'];ng=gmap[tid];s=selected.get(tid);chosen=s['grade'] if s else ng
  all500.append({'task_id':tid,'subject':b['subject'],'level':b['level'],'A_original_correct':b['original_correct'],'B_rescored_correct':ng['correct'],'C_composite_correct':chosen['correct'],'original_answer':b['original_answer'],'rescored_answer':ng['answer'],'selected_answer':chosen['answer'],'B_status':ng['status'],'C_status':chosen['status'],'C_source':s['raw_evidence'] if s else 'evidence/baseline_500.json#'+tid,'C_budget':s['budget'] if s else 4096,'original_input_tokens':b['provider']['usage']['prompt_tokens'],'original_output_tokens':b['provider']['usage']['completion_tokens'],'original_total_tokens':b['provider']['usage']['total_tokens'],'selected_input_tokens':s['input_tokens'] if s else b['provider']['usage']['prompt_tokens'],'selected_output_tokens':s['output_tokens'] if s else b['provider']['usage']['completion_tokens'],'selected_total_tokens':s['total_tokens'] if s else b['provider']['usage']['total_tokens'],'model':b['provider']['request']['model'],'temperature':b['provider']['request']['temperature'],'endpoint':'https://api.deepseek.com/chat/completions','evaluator_sha256':sha(ROOT/'FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py'),'reference_commit':read(OUT/'preflight.json')['reference_commit']})
 csvwrite('math500_rescored.csv',all500)
 hist=[{'task_id':b['task_id'],'budget':4096,'finish_reason':b['provider']['finish_reason'],'complete_final_answer':b['provider']['finish_reason']=='stop' and complete(b['solution']),'grade':gmap[b['task_id']],'input_tokens':b['provider']['usage']['prompt_tokens'],'output_tokens':b['provider']['usage']['completion_tokens'],'total_tokens':b['provider']['usage']['total_tokens'],'reasoning_tokens':b['provider']['usage'].get('completion_tokens_details',{}).get('reasoning_tokens')} for b in baseline if b['truncated']]
 stats=[]
 for label,rs in [('original_4096',hist),('rung_8192',[x for x in percall if x['budget']==8192]),('rung_16384_conditional',[x for x in percall if x['budget']==16384]),('selected_last_rung',list(selected.values()))]:
  stats.append({'group':label,'tasks':len(rs),'complete_final_answers':sum(x['complete_final_answer'] for x in rs),'correct':sum(x['grade']['correct'] is True for x in rs),'complete_wrong':sum(x['complete_final_answer'] and x['grade']['correct'] is False for x in rs),'unknown':sum(x['grade']['correct'] is None for x in rs),'still_truncated':sum(x['finish_reason']=='length' for x in rs),**{k:sum(x[k] or 0 for x in rs) for k in ('input_tokens','output_tokens','total_tokens','reasoning_tokens')}})
 csvwrite('budget_comparison.csv',stats)
 costs=[]
 for x in hist+percall:
  costs.append({k:x[k] for k in ('task_id','budget','input_tokens','output_tokens','total_tokens','reasoning_tokens')}|{'stage':'historical' if x['budget']==4096 else 'new','new_spend':x['budget']!=4096,'correct':x['grade']['correct'],'finish_reason':x['finish_reason'],'model':'deepseek-flash','temperature':0.0,'evidence':x.get('raw_evidence','evidence/baseline_500.json#'+x['task_id']),'reference_commit':read(OUT/'preflight.json')['reference_commit'],'evaluator_sha256':sha(ROOT/'FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py')})
 csvwrite('token_costs.csv',costs)
 truefail=[x for x in results if x['category']=='complete_math_wrong'];jsonlines('remaining_true_failures.jsonl',truefail)
 summary={'A_correct':sum(x['A_original_correct'] for x in all500),'B_correct':sum(x['B_rescored_correct'] is True for x in all500),'C_correct':sum(x['C_composite_correct'] is True for x in all500),'denominator':500,'nine_fixed':sum(gmap[x['task_id']]['correct'] is True for x in cases),'old_true_to_false':sum(x['A_original_correct'] and x['B_rescored_correct'] is False for x in all500),'old_true_to_unknown':sum(x['A_original_correct'] and x['B_rescored_correct'] is None for x in all500),'category_counts':dict(Counter(x['category'] for x in results)),'budget_comparison':stats,'new_calls':len(percall),'infrastructure_retries':0,**{'new_'+k:sum(x[k] or 0 for x in percall) for k in ('input_tokens','output_tokens','total_tokens','reasoning_tokens')},**{'historical500_'+k:sum(b['provider']['usage'][k] for b in baseline) for k in ('prompt_tokens','completion_tokens','total_tokens')},'selected500_total_tokens':sum(x['selected_total_tokens'] for x in all500),'limitations':['Historical visible solution, request, usage and finish_reason retained; historical full HTTP JSON and reasoning_content text not retained.','Same model alias, but provider backend revision not pinned; stochastic fresh samples, not continuation of old reasoning.','Post-hoc selected difficulty subset; C is exploratory composite, not fresh standard MATH-500.','No concurrent 4096 re-sampling control; increased budget and sampling variation cannot be causally separated.']}
 write_json(OUT/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
 print('Needs manual math review:',[(x['task_id'],x['category'],x['selected']['grade']['answer']) for x in results if x['category']!='recovered_correct'])
if __name__=='__main__':main()
