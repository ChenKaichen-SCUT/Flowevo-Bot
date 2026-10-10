"""Durable gold-blind FlowEvo prompt replay. No evaluator/label imports or paths."""
from common import ROOT,OUT,read,save,lines,sha,digest,now
from completion import detect
import concurrent.futures as cf,threading,time,random,json
import requests

class BudgetStop(RuntimeError):pass

def request_for(prompt,config,budget):
 for k in ('skill_injection','history_retrieval','gold_answer_feedback','gold_driven_reflection','correctness_retries','format_repair_prompt'):
  if config[k] is not False:raise ValueError('Forbidden experiment setting: '+k)
 assert config['native_library'] is None and config['native_condition']=='cot_baseline'
 return {'model':config['model'],'messages':[{'role':'system','content':config['system_prompt']},{'role':'user','content':prompt}],'temperature':config['temperature'],'max_tokens':budget}

def require_public(entry):
 if set(entry)!={'task_id','prompt','skill_injected','skill_retrieval_count','gold_exposed'}:raise ValueError('Non-public prompt record')
 if entry['gold_exposed'] or entry['skill_injected'] or entry['skill_retrieval_count']!=0:raise ValueError('Forbidden context')

class Runner:
 def __init__(self,config=None,transport=None):
  self.config=config or read(OUT/'config.json');self.transport=transport
  self.key=(ROOT/'miyao.txt').read_text().strip() if transport is None else None
  self.lock=threading.Condition();self.reserved=0;self.active=0;self.peak=0;self.abort=False
  if list((OUT/'raw').glob('*.pending.json')):raise RuntimeError('Unknown prior billing: pending requests block blind resends')
  prior=[read(p) for p in (OUT/'raw').glob('*.json') if not p.name.endswith(('.error.json','.attempts.json'))]
  self.actual=sum(x['total_tokens'] for x in prior);self.normal_calls=len(prior);self.http_attempts=sum(x['http_attempts'] for x in prior)
  self.frozen=read(OUT/'evidence/pre_api_freeze.json')
  for x in self.frozen['files']:assert sha(ROOT/x['path'])==x['sha256'],x['path']
  assert self.actual<=self.config['max_total_token_reservation']
 def reserve(self,bound):
  with self.lock:
   while not self.abort and self.actual+self.reserved+bound>self.config['max_total_token_reservation'] and self.active:self.lock.wait(1)
   if self.abort or self.actual+self.reserved+bound>self.config['max_total_token_reservation'] or self.normal_calls>=self.config['max_normal_calls']:raise BudgetStop('Global budget safety stop; cap not increased')
   self.reserved+=bound;self.active+=1;self.peak=max(self.peak,self.active);self.normal_calls+=1
   assert self.active<=64
 def call(self,entry,stage,budget):
  require_public(entry);tid=entry['task_id'];req=request_for(entry['prompt'],self.config,budget)
  job=f'{tid}__{stage}';path=OUT/'raw'/f'{job}.json'
  if path.exists():
   r=read(path);assert r['request']==req and r['response_hash']==digest(r['response']);return r
  bound=sum(len(x['content'].encode()) for x in req['messages'])+512+budget
  self.reserve(bound);started=now();pending=path.with_suffix('.pending.json')
  save(pending,{'job_id':job,'task_id':tid,'stage':stage,'request':req,'started_at':started,'reserved_tokens':bound})
  t=time.perf_counter();attempts=[]
  try:
   for attempt in range(self.config['max_explicit_rejections_retries_per_call']+1):
    with self.lock:
     if self.http_attempts>=self.config['max_http_attempts']:raise BudgetStop('HTTP attempt cap')
     self.http_attempts+=1
    if self.transport:data=self.transport(req);status=200;body=json.dumps(data);headers={}
    else:
     response=requests.post(self.config['endpoint'],headers={'Authorization':'Bearer '+self.key},json=req,timeout=(30,600))
     status=response.status_code;body=response.text;headers=response.headers
    bodypath=OUT/'raw'/f'{job}.http{attempt+1}.txt';bodypath.write_text(body)
    attempts.append({'attempt_id':attempt+1,'api_status':status,'finished_at':now(),'raw_body':str(bodypath.relative_to(OUT)),'usage':'unavailable' if status!=200 else 'in response'})
    save(path.with_suffix('.attempts.json'),attempts)
    if status==200:
     if not self.transport:data=response.json()
     break
    if status==429 and attempt<self.config['max_explicit_rejections_retries_per_call']:
     try:delay=min(10,max(1,float(headers.get('Retry-After',2**attempt))))
     except ValueError:delay=2
     time.sleep(delay);continue
    raise RuntimeError('Provider rejection or ambiguous failure')
   u=data['usage'];assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
   state=detect(tid,data,budget)
   r={'run_id':self.config['run_id'],'task_id':tid,'job_id':job,'request_id':data.get('id','unavailable'),'attempt_id':stage,'stage':stage,'model':req['model'],'model_version':data.get('model','unknown'),'backend_revision':data.get('system_fingerprint','unavailable'),'endpoint':self.config['endpoint'],'prompt_hash':digest(req['messages']),'request_hash':digest(req),'config_hash':digest(self.config),'max_tokens':budget,'temperature':req['temperature'],'request':req,'response':data,'response_hash':digest(data),'finish_reason':state['finish_reason'],'completion_status':state['completion_status'],'completion':state,'retry_required':state['retry_required'],'retry_reason':state['retry_reason'],'input_tokens':u['prompt_tokens'],'output_tokens':u['completion_tokens'],'reasoning_tokens_if_available':u.get('completion_tokens_details',{}).get('reasoning_tokens','unavailable'),'total_tokens':u['total_tokens'],'latency':time.perf_counter()-t,'started_at':started,'finished_at':now(),'api_status':status,'http_attempts':len(attempts),'infrastructure_retries':len(attempts)-1,'correctness_retries':0,'gold_exposed':False,'skill_injected':False,'skill_retrieval_count':0,'reserved_tokens':bound,'code_freeze_hash':digest(self.frozen),'raw_attempts':attempts}
   save(path,r);pending.unlink()
   with self.lock:
    self.actual+=r['total_tokens'];self.reserved-=bound;self.active-=1
    if r['total_tokens']>bound:self.abort=True
    self.lock.notify_all()
   if self.abort:raise BudgetStop('Usage exceeds reservation or concurrent infrastructure failure')
   print(json.dumps({'task_id':tid,'stage':stage,'finish_reason':r['finish_reason'],'complete':not r['retry_required'],'tokens':r['total_tokens'],'cumulative_tokens':self.actual}),flush=True)
   return r
  except Exception as e:
   with self.lock:
    self.abort=True;self.lock.notify_all()
   save(path.with_suffix('.error.json'),{'task_id':tid,'stage':stage,'error_type':type(e).__name__,'billing_unknown':not path.exists(),'no_blind_resend':True,'finished_at':now()})
   raise RuntimeError('Request stopped; durable evidence retained; do not blindly resend') from None

def run_stage(runner,jobs):
 with cf.ThreadPoolExecutor(max_workers=runner.config['api_workers']) as pool:
  fs=[pool.submit(runner.call,*job) for job in jobs]
  return [f.result() for f in fs]

def seal_phase(name,records):
 artifact={'sealed_at':now(),'records':[{'task_id':r['task_id'],'stage':r['stage'],'request_hash':r['request_hash'],'response_hash':r['response_hash']} for r in records]}
 save('checkpoints/'+name+'.json',artifact);return digest(artifact)

def main():
 r=Runner();entries=read(OUT/'data/native_prompts.json')['prompts'];assert len(entries)==500
 for e in entries:require_public(e)
 first=run_stage(r,[(e,'base4096',4096) for e in entries]);base_seal=seal_phase('base4096_seal',first)
 selected=[e for e,c in zip(entries,first) if c['retry_required']]
 save('checkpoints/base_escalation.json',{'task_ids':[x['task_id'] for x in selected],'decision_at':now(),'base_seal':base_seal,'rule':'frozen syntactic completion only','scorer_used':False})
 jobs=[(e,stage,budget) for e in selected for stage,budget in [('upgrade8192',8192),('control4096',4096)]]
 random.Random(r.config['branch_interleaving_seed']).shuffle(jobs)
 save('checkpoints/second_stage_schedule.json',[{'task_id':e['task_id'],'stage':stage,'budget':b} for e,stage,b in jobs])
 second=run_stage(r,jobs);second_seal=seal_phase('second_stage_seal',second)
 needs={x['task_id'] for x in second if x['stage']=='upgrade8192' and x['retry_required']}
 save('checkpoints/upgrade_escalation.json',{'task_ids':sorted(needs),'decision_at':now(),'second_seal':second_seal,'scorer_used':False})
 third=run_stage(r,[(e,'upgrade16384',16384) for e in selected if e['task_id'] in needs]);seal_phase('third_stage_seal',third)
 records=first+second+third;lines('api_calls.jsonl',records)
 amap={x['task_id']:x for x in first}
 for x in sorted([z for z in records if z['stage'].startswith('upgrade')],key=lambda z:z['max_tokens']):amap[x['task_id']]=x
 lines('first_pass_results.jsonl',first);lines('adaptive_results.jsonl',[amap[e['task_id']] for e in entries]);lines('same_budget_retry.jsonl',[x for x in second if x['stage']=='control4096'])
 save('checkpoints/ALL_GENERATION_SEALED.json',{'sealed_at':now(),'api_calls_sha256':sha(OUT/'api_calls.jsonl'),'first_pass_sha256':sha(OUT/'first_pass_results.jsonl'),'adaptive_sha256':sha(OUT/'adaptive_results.jsonl'),'control_sha256':sha(OUT/'same_budget_retry.jsonl'),'new_normal_calls':len(records),'http_attempts':sum(x['http_attempts'] for x in records),'actual_tokens':sum(x['total_tokens'] for x in records),'peak_api_concurrency':r.peak,'offline_scoring_not_yet_started':True})
 print('ALL GENERATION SEALED '+str(len(records))+' calls '+str(r.actual)+' tokens',flush=True)
if __name__=='__main__':main()
