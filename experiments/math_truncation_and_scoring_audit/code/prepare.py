import hashlib,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Flowevo-Bot/src'))
from flowevo_bot.common import digest,write_json
BASE=ROOT/'Flowevo-Bot/experiments/math500_goldfree_20261009'
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=read(ROOT/'UPLOAD_MANIFEST.json');write_json(OUT/'evidence/protected_previous_snapshot.json',manifest)
 shutil.copyfile('/root/.codex/attachments/f5ecb90e-1e18-46a6-874c-0a754b71c25f/已粘贴的文本.txt',OUT/'USER_GUIDE.txt')
 rows=read(BASE/'flowevo_bot/rows.json');ledger=read(BASE/'flowevo_bot/calls.json')
 subs={x['task_id']:x for x in read(BASE/'flowevo_bot/checkpoint.json')['submissions']}
 probs={x['task_id']:x for x in jl(BASE/'manifests/test.problems.jsonl')};labels={x['task_id']:x for x in jl(BASE/'manifests/test.labels.jsonl')}
 calls={x['task_id']:x for x in ledger['calls']}; records=[];public=[]
 for r in rows:
  tid=r['task_id'];c=calls[tid];cid=c['call_id'];s=subs[tid]
  side=read(BASE/'flowevo_bot/task_calls'/f'{tid}.provider'/f'{cid}.json')
  assert digest(side['request'])==c['prompt_hash']
  assert digest(s['solution'])==c['response_hash'] and s['solution']==ledger['responses'][cid]
  assert side['usage']['total_tokens']==r['total_tokens']==c['total_tokens']
  assert (side['finish_reason']=='length')==r['truncated']
  assert not s['provenance']['gold_exposed'] and not s['provenance']['reference_solution_exposed']
  records.append({'task_id':tid,'question':probs[tid]['problem'],'subject':r['subject'],'level':r['level'],'gold_answer':labels[tid]['gold_answer'],'reference_solution':labels[tid]['reference_solution'],'solution':s['solution'],'original_correct':r['final_correct'],'original_answer':r['final_answer'],'truncated':r['truncated'],'provider':side,'original_row':r,'original_submission':s})
  if r['truncated']:
   assert side['request']['max_tokens']==4096 and side['usage']['completion_tokens']==4096
   public.append({'task_id':tid,'question':probs[tid]['problem'],'subject':r['subject'],'level':r['level'],'request':side['request'],'historical_call_id':cid,'historical_tokens':side['usage']})
 assert len(records)==500 and sum(r['original_correct'] for r in records)==464 and len(public)==27
 write_json(OUT/'evidence/baseline_500.json',records);write_json(OUT/'evidence/public_27.json',public)
 write_json(OUT/'truncated_27_task_ids.json',[x['task_id'] for x in public])
 write_json(OUT/'evidence/baseline_file_hashes.json',[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(BASE.rglob('*')) if p.is_file() and '__pycache__' not in str(p)])
 prompt_bound=2*sum(sum(len(m['content'].encode()) for m in x['request']['messages'])+512 for x in public)
 output_bound=27*(8192+16384)
 plan={'reference_commit':'6acc7335bbe6b731ef3e387d573b6689b90c0550','endpoint':'https://api.deepseek.com/chat/completions','model':'deepseek-flash','temperature':0.0,'thinking_and_reasoning_effort':'omitted, identical to historical requests; provider defaults apply','rungs':[8192,16384],'max_normal_calls':54,'max_output_tokens_all_calls':output_bound,'conservative_input_reservation_utf8_bytes_plus_512_per_call':prompt_bound,'max_total_token_reservation':output_bound+prompt_bound,'historical_prompt_tokens_repeated_twice':2*sum(x['historical_tokens']['prompt_tokens'] for x in public),'api_concurrency':27,'api_global_limit':64,'local_workers':12,'gold_feedback':False,'additional_methods':False,'infrastructure_retries':0,'selection':'last executed rung; rung 16384 only if finish_reason=length OR no complete explicit final answer at 8192; no gold read by runner','baseline_new_calls':0,'capability_sources':['https://api-docs.deepseek.com/api/create-chat-completion/','https://api-docs.deepseek.com/guides/thinking_mode/','https://api-docs.deepseek.com/quick_start/pricing/'],'current_documented_flash_max_output':393216,'worst_peak_usd_estimate':(output_bound*1.2+prompt_bound*.3)/1e6,'budget_authorization':'User authorizes up to 54 normal solves at these rungs; no additional monetary/token cap specified in current guide. Prior pilot cap belongs to completed prior experiment.'}
 assert plan['max_total_token_reservation']<1000000
 write_json(OUT/'preflight.json',plan)
 print(json.dumps(plan,indent=2));print('Confirmed500 providers, all27 finish length, reasoning-only25; partial2; full historical reasoning text/raw HTTP not retained.')
if __name__=='__main__':main()
