"""Durable, budget-capped, gold-blind generation. No evaluator/label reads."""
from common import ROOT,OUT,read,jl,save,lines,sha,digest,now
import concurrent.futures as cf,threading,time,random,json,sys,signal
from pathlib import Path
import requests
from math_control import finalization_decision,check_goal,goal_spec
from math_control.prompts import intervention_prompt
sys.path.insert(0,str(ROOT/'experiments/math500_scoring_and_budget_v2/code'))
from completion import detect

class BudgetStop(RuntimeError):pass
class AnalysisTimeout(BaseException):pass
PUBLIC_FIELDS={'task_id','problem','subject','level','prompt'}
def require_public(e):
 if set(e)!=PUBLIC_FIELDS:raise ValueError('Only exact public prompt schema is allowed')
 if e['prompt']!='Problem: '+e['problem']+'\n\nSolve step by step. End with: The answer is [your answer].':raise ValueError('Base prompt is not native cot_baseline')

def request_for(prompt,config,budget):
 if config['gold_feedback'] or config['skill_injection']:raise ValueError('Forbidden context')
 return {'model':config['model'],'messages':[{'role':'system','content':config['system_prompt']},{'role':'user','content':prompt}],'temperature':0,'max_tokens':budget,'stream':True,'stream_options':{'include_usage':True}}

def consume_sse(response,rawfile,start):
 """Persist actual stream, reconstruct exact text; observe without cancellation."""
 result={};reason=[];content=[];usage=None;finish=None;events=[];rc=0;cc=0;delta_count=0
 with rawfile.open('w') as f:
  for line in response.iter_lines(decode_unicode=True):
   if isinstance(line,bytes):line=line.decode('utf-8')
   f.write((line or '')+'\n');f.flush()
   if not line or not line.startswith('data:'):continue
   data=line[5:].strip()
   if data=='[DONE]':break
   part=json.loads(data)
   if 'error' in part:raise RuntimeError('Provider stream error')
   for key in ('id','model','created','object','system_fingerprint'):
    if key in part:result[key]=part[key]
   if part.get('usage'):usage=part['usage']
   for choice in part.get('choices',[]):
    if choice.get('finish_reason') is not None:finish=choice['finish_reason']
    delta=choice.get('delta',{});r=delta.get('reasoning_content') or '';c=delta.get('content') or ''
    if r or c:
     delta_count+=1;rc+=len(r);cc+=len(c);reason.append(r);content.append(c)
     events.append({'seconds':round(time.perf_counter()-start,4),'reasoning_chars':rc,'content_chars':cc,'reasoning_delta_chars':len(r),'content_delta_chars':len(c)})
 if usage is None or finish is None:raise RuntimeError('Missing final usage or finish reason; billing cannot be guessed')
 result.update(object='chat.completion',choices=[{'index':0,'message':{'role':'assistant','reasoning_content':''.join(reason),'content':''.join(content)},'finish_reason':finish}],usage=usage)
 return result,{'delta_count':delta_count,'events':events,'cancelled':False,'observed_during_generation':True,'all_raw_sse_retained':True}

class Runner:
 def __init__(self,config,transport=None,out=None,validate_freeze=True):
  self.config=config;self.out=Path(out or OUT);self.transport=transport
  (self.out/'raw').mkdir(parents=True,exist_ok=True)
  self.key=(ROOT/'miyao.txt').read_text().strip() if transport is None else None
  self.lock=threading.Condition();self.reserved=0;self.active=0;self.peak=0;self.abort=False;self.inflight=set()
  if list((self.out/'raw').glob('*.pending.json')):raise RuntimeError('Pending request has unknown billing; blind resends prohibited')
  prior=[read(p) for p in (self.out/'raw').glob('*.json') if not p.name.endswith(('.error.json','.stream.json'))]
  self.actual=sum(x['total_tokens'] for x in prior);self.calls=len(prior);self.http_attempts=len(prior)
  self.frozen=read(self.out/'evidence/pre_api_freeze.json') if validate_freeze else {}
  for p,h in self.frozen.get('files',{}).items():
   if sha(ROOT/p)!=h:raise RuntimeError('Frozen source/data mismatch: '+p)
  if self.actual>config['max_total_tokens'] or self.calls>config['max_calls']:raise BudgetStop('Prior budget exceeds frozen cap')
 def reserve(self,bound):
  with self.lock:
   while not self.abort and (self.actual+self.reserved+bound>self.config['max_total_tokens'] or self.active>=self.config['api_workers']) and self.active:self.lock.wait(.2)
   if self.abort or self.actual+self.reserved+bound>self.config['max_total_tokens'] or self.calls>=self.config['max_calls']:raise BudgetStop('Hard budget stop; no expansion')
   self.reserved+=bound;self.active+=1;self.calls+=1;self.peak=max(self.peak,self.active)
 def call(self,e,stage,budget,prompt=None):
  require_public(e);tid=e['task_id'];req=request_for(prompt or e['prompt'],self.config,budget);job=tid+'__'+stage;path=self.out/'raw'/f'{job}.json'
  with self.lock:
   while job in self.inflight:self.lock.wait(.2)
   if path.exists():
    r=read(path)
    if r['request']!=req or r['response_hash']!=digest(r['response']):raise ValueError('Saved request/response mismatch')
    return r
   if self.abort:raise BudgetStop('Global stop')
   self.inflight.add(job)
  bound=sum(len(x['content'].encode()) for x in req['messages'])+512+budget
  try:self.reserve(bound)
  except BaseException:
   with self.lock:self.inflight.remove(job);self.lock.notify_all()
   raise
  started=now();start=time.perf_counter();pending=path.with_suffix('.pending.json');save(pending,{'job_id':job,'request':req,'started_at':started,'reserved_tokens':bound})
  try:
   with self.lock:self.http_attempts+=1
   if self.transport:data=self.transport(req);stream={'test_transport':True}
   else:
    with requests.post(self.config['endpoint'],headers={'Authorization':'Bearer '+self.key},json=req,stream=True,timeout=(30,900)) as response:
     if response.status_code!=200:
      path.with_suffix('.http_error.txt').write_text(response.text)
      raise RuntimeError('HTTP rejection recorded, no automatic retry')
     response.encoding='utf-8';data,stream=consume_sse(response,path.with_suffix('.sse.txt'),start)
   usage=data['usage'];actual=usage['total_tokens']
   if actual!=usage['prompt_tokens']+usage['completion_tokens']:raise RuntimeError('Inconsistent provider usage')
   comp=detect(tid,data,budget);rt=usage.get('completion_tokens_details',{}).get('reasoning_tokens','unavailable')
   r={'task_id':tid,'job_id':job,'stage':stage,'model':req['model'],'model_version':data.get('model','unavailable'),'backend_revision':data.get('system_fingerprint','unavailable'),'request':req,'request_hash':digest(req),'response':data,'response_hash':digest(data),'max_tokens':budget,'input_tokens':usage['prompt_tokens'],'output_tokens':usage['completion_tokens'],'reasoning_tokens':rt,'final_content_tokens':usage['completion_tokens']-rt if isinstance(rt,int) else 'unavailable','total_tokens':actual,'completion':comp,'finish_reason':comp['finish_reason'],'started_at':started,'finished_at':now(),'latency_seconds':time.perf_counter()-start,'reasoning_effort':'default high (parameter omitted)','thinking':'default enabled (parameter omitted)','http_attempts':1,'gold_exposed':False,'skill_injected':False,'correctness_retries':0,'reserved_tokens':bound,'code_freeze_hash':digest(self.frozen),'stream_evidence_path':str(path.with_suffix('.stream.json').relative_to(self.out))}
   save(path.with_suffix('.stream.json'),stream);save(path,r);pending.unlink()
   with self.lock:
    self.actual+=actual;self.reserved-=bound;self.active-=1
    if actual>bound or self.actual>self.config['max_total_tokens']:self.abort=True
    self.inflight.remove(job);self.lock.notify_all()
   print(json.dumps({'task_id':tid,'stage':stage,'finish':r['finish_reason'],'tokens':actual,'cumulative':self.actual}),flush=True)
   if self.abort:raise BudgetStop('Conservative reservation exceeded or concurrent infrastructure failure')
   return r
  except Exception as e:
   with self.lock:self.abort=True;self.inflight.discard(job);self.lock.notify_all()
   save(path.with_suffix('.error.json'),{'error_type':type(e).__name__,'billing_unknown':not path.exists(),'no_blind_resend':True,'at':now()})
   raise RuntimeError('Durable request failure: no blind resend') from None

def run_jobs(runner,jobs):
 results=[];errors=[]
 with cf.ThreadPoolExecutor(max_workers=runner.config['api_workers']) as pool:
  fs={pool.submit(runner.call,*j):j[0]['task_id']+'__'+j[1] for j in jobs}
  for f in cf.as_completed(fs):
   try:results.append(f.result())
   except Exception as e:errors.append({'job_id':fs[f],'error_type':type(e).__name__})
 if errors:save(runner.out/'checkpoints/stopped.json',{'errors':errors,'actual_tokens':runner.actual,'calls_reserved':runner.calls});raise BudgetStop('Some jobs unexecuted/failed; inspect stopped.json')
 return results

def decide(item):
 e,r=item
 def expired(*a):raise AnalysisTimeout()
 signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,10)
 try:
  a1=finalization_decision(e['problem'],r['response'],r['completion'])
  a2=check_goal(e['problem'],r['response']['choices'][0]['message'].get('content') or '')
  a2['trigger']=not r['completion']['retry_required'] and a2['high_confidence_mismatch']
  return {'task_id':e['task_id'],'a1':a1,'a2':a2,'decided_at':now(),'reference_access':False,'source_response_hash':r['response_hash']}
 except AnalysisTimeout:return {'task_id':e['task_id'],'a1':{'trigger':False,'events':[],'reason':'public_parser_timeout'},'a2':{'trigger':False,'high_confidence_mismatch':False,'goal_spec':goal_spec(e['problem']).to_dict(),'evidence':[],'status':'uncertain_timeout'},'reference_access':False,'decided_at':now(),'source_response_hash':r['response_hash']}
 finally:signal.setitimer(signal.ITIMER_REAL,0)

def main():
 if (OUT/'checkpoints/ALL_GENERATION_SEALED.json').exists():print('All generation already sealed; reusing, no model calls');return
 config=read(OUT/'config.json');runner=Runner(config);entries=jl(OUT/'data/public_prompts.jsonl')
 for e in entries:require_public(e)
 jobs=[(e,s,b) for e in entries for s,b in [('b0',4096),('b2',16384)]];random.Random(config['schedule_seed']).shuffle(jobs)
 save('checkpoints/initial_schedule.json',[{'task_id':e['task_id'],'stage':s,'budget':b} for e,s,b in jobs])
 first=run_jobs(runner,jobs);by={(r['task_id'],r['stage']):r for r in first}
 save('checkpoints/initial_sealed.json',{'at':now(),'hashes':{r['job_id']:r['response_hash'] for r in first}})
 second=run_jobs(runner,[(e,'b1_8192',8192) for e in entries if by[e['task_id'],'b0']['completion']['retry_required']]);by.update({(r['task_id'],r['stage']):r for r in second})
 third=run_jobs(runner,[(e,'b1_16384',16384) for e in entries if (e['task_id'],'b1_8192') in by and by[e['task_id'],'b1_8192']['completion']['retry_required']]);by.update({(r['task_id'],r['stage']):r for r in third})
 dpath=OUT/'controller_decisions.jsonl'
 if dpath.exists():decisions=jl(dpath)
 else:
  with cf.ProcessPoolExecutor(max_workers=12) as pool:decisions=list(pool.map(decide,[(e,by[e['task_id'],'b2']) for e in entries]))
  lines(dpath,decisions)
 dmap={d['task_id']:d for d in decisions}
 for e in entries:assert dmap[e['task_id']]['source_response_hash']==by[e['task_id'],'b2']['response_hash']
 lines('goal_specs.jsonl',[{'task_id':d['task_id'],**d['a2']['goal_spec']} for d in decisions])
 lines('candidate_answer_events.jsonl',[dict(x,task_id=d['task_id']) for d in decisions for x in d['a1']['events']])
 jobs=[]
 for e in entries:
  r=by[e['task_id'],'b2'];m=r['response']['choices'][0]['message'];d=dmap[e['task_id']]
  for kind in ('a1','a2','generic'):
   if kind=='generic' or d[kind]['trigger']:jobs.append((e,kind,4096,intervention_prompt(e['prompt'],kind,m.get('content') or '',m.get('reasoning_content') or '',d.get(kind,{}))))
 random.Random(config['schedule_seed']+1).shuffle(jobs)
 save('checkpoints/intervention_schedule.json',[{'task_id':e['task_id'],'stage':s,'budget':b,'prompt_hash':digest(p)} for e,s,b,p in jobs])
 interventions=run_jobs(runner,jobs);allcalls=first+second+third+interventions;by.update({(r['task_id'],r['stage']):r for r in interventions})
 selected=[]
 for e in entries:
  tid=e['task_id'];b1=[by[tid,'b0']]+[by[tid,s] for s in ('b1_8192','b1_16384') if (tid,s) in by]
  branches={'B0':[by[tid,'b0']],'B1':b1,'B2':[by[tid,'b2']]}
  for k in ('a1','a2','generic'):branches['B2+'+k]=[by[tid,'b2']]+([by[tid,k]] if (tid,k) in by else [])
  for method,calls in branches.items():selected.append({'task_id':tid,'method':method,'final_job_id':calls[-1]['job_id'],'all_job_ids':[r['job_id'] for r in calls],'all_attempt_tokens':sum(r['total_tokens'] for r in calls)})
 lines('api_calls.jsonl',sorted(allcalls,key=lambda r:r['job_id']));lines('selected_responses.jsonl',selected)
 save('checkpoints/ALL_GENERATION_SEALED.json',{'sealed_at':now(),'api_calls_sha256':sha(OUT/'api_calls.jsonl'),'selected_sha256':sha(OUT/'selected_responses.jsonl'),'controller_sha256':sha(dpath),'new_normal_calls':len(allcalls),'http_attempts':runner.http_attempts,'actual_tokens':runner.actual,'peak_api_concurrency':runner.peak,'offline_scoring_not_yet_started':True,'no_stream_cancellations':True,'no_gold_or_skill':True})
 print('ALL_GENERATION_SEALED '+str(len(allcalls))+' calls '+str(runner.actual)+' tokens',flush=True)
if __name__=='__main__':main()
