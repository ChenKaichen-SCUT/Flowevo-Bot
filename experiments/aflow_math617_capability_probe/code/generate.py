"""Gold-blind fixed-prompt generation, durable attempts, bounded transport recovery.

Only public task/config files are read. Mathematical correctness never triggers a call.
Completed outputs are immutable; successful streaming responses include exact usage.
"""
from common import *
import concurrent.futures as cf,threading,time,gzip,argparse,random
import requests
sys.path.append(str(ROOT/'experiments/math500_scoring_and_budget_v2/code'))
from completion import detect
PUBLIC_FIELDS={'task_id','problem','subject','level','prompt'}

def request_for(e,cfg):
 if set(e)!=PUBLIC_FIELDS:raise ValueError('Only public prompt schema accepted')
 if e['prompt']!='Problem: '+e['problem']+'\n\nSolve step by step. End with: The answer is [your answer].':raise ValueError('Unexpected base prompt')
 if cfg['gold_feedback'] or cfg['skill_injection'] or cfg['gold_reflection']:raise ValueError('Forbidden feedback/context')
 return {'model':cfg['model'],'messages':[{'role':'system','content':cfg['system_prompt']},{'role':'user','content':e['prompt']}],'temperature':0,'max_tokens':16384,'stream':True,'stream_options':{'include_usage':True}}

def consume(response,path):
 obj={};reason=[];content=[];usage=None;finish=None;done=False
 with gzip.open(path,'wt',encoding='utf-8')as f:
  for line in response.iter_lines(decode_unicode=True):
   if isinstance(line,bytes):line=line.decode('utf-8')
   f.write((line or '')+'\n')
   if not line or not line.startswith('data:'):continue
   data=line[5:].strip()
   if data=='[DONE]':done=True;break
   part=json.loads(data)
   if 'error'in part:raise RuntimeError('Provider stream error')
   for key in ('id','model','created','object','system_fingerprint'):
    if key in part:obj[key]=part[key]
   if part.get('usage'):usage=part['usage']
   for choice in part.get('choices',[]):
    if choice.get('finish_reason')is not None:finish=choice['finish_reason']
    delta=choice.get('delta',{});reason.append(delta.get('reasoning_content')or '');content.append(delta.get('content')or '')
 if usage is None or finish is None or not done:raise RuntimeError('Incomplete transport or missing usage')
 obj.update(object='chat.completion',choices=[{'index':0,'message':{'role':'assistant','reasoning_content':''.join(reason),'content':''.join(content)},'finish_reason':finish}],usage=usage)
 return obj

class BudgetStop(RuntimeError):pass
class Runner:
 def __init__(self,cfg,out=OUT,transport=None):
  self.out=Path(out);self.cfg=cfg;self.transport=transport;self.key=(ROOT/'miyao.txt').read_text().strip()if transport is None else None
  (self.out/'raw').mkdir(parents=True,exist_ok=True);(self.out/'attempts').mkdir(exist_ok=True)
  self.lock=threading.Condition();self.active=0;self.peak=0;self.reserved=0
  # A prior crash is a billed-unknown attempt, not an invisible resend.
  for p in (self.out/'attempts').glob('*.pending.json'):
   a=read(p);final=p.with_name(p.name.replace('.pending.json','.json'))
   if not final.exists():save(final,dict(a,status='transport_unknown_after_crash',usage_known=False,error_type='UnfinishedProcess',finished_at=now()))
   p.unlink()
  attempts=[read(p)for p in (self.out/'attempts').glob('*.json')]
  self.actual=sum(a.get('total_tokens',0)for a in attempts);self.unknown=sum(a['reserved_tokens']for a in attempts if not a['usage_known']);self.calls=len(attempts)
 def reserve(self,bound):
  with self.lock:
   while self.active and self.actual+self.unknown+self.reserved+bound>self.cfg['max_total_tokens']:self.lock.wait(.1)
   if self.actual+self.unknown+self.reserved+bound>self.cfg['max_total_tokens']or self.calls>=self.cfg['max_http_attempts']:raise BudgetStop('Frozen safety budget reached')
   self.calls+=1;self.active+=1;self.reserved+=bound;self.peak=max(self.peak,self.active)
 def call(self,e,candidate):
  req=request_for(e,self.cfg);job=f"{e['task_id']}__c{candidate}";path=self.out/'raw'/f'{job}.json'
  if path.exists():
   r=read(path)
   assert r['request']==req and r['response_hash']==digest(r['response'])
   return r
  previous=list((self.out/'attempts').glob(job+'__a*.json'))
  bound=sum(len(m['content'].encode())for m in req['messages'])+512+req['max_tokens']
  for attempt in range(len(previous)+1,self.cfg['max_attempts_per_job']+1):
   aid=f'{job}__a{attempt}';ap=self.out/'attempts'/f'{aid}.json';pending=ap.with_suffix('.pending.json')
   self.reserve(bound);start=time.perf_counter()
   a={'attempt_id':aid,'job_id':job,'task_id':e['task_id'],'candidate':candidate,'started_at':now(),'reserved_tokens':bound,'request_hash':digest(req),'trigger':'scheduled'if attempt==1 else 'transport_recovery_only','gold_access':False}
   save(pending,dict(a,request=req));data=None
   try:
    if self.transport:data=self.transport(req)
    else:
     with requests.post(self.cfg['endpoint'],headers={'Authorization':'Bearer '+self.key},json=req,stream=True,timeout=(30,900))as resp:
      a['http_status']=resp.status_code
      if resp.status_code!=200:raise RuntimeError('HTTP rejection')
      resp.encoding='utf-8';data=consume(resp,self.out/'raw'/f'{aid}.sse.gz')
    u=data['usage'];actual=u['total_tokens'];assert actual==u['prompt_tokens']+u['completion_tokens'];assert actual<=bound
    comp=detect(e['task_id'],data,16384);rt=u.get('completion_tokens_details',{}).get('reasoning_tokens','unavailable')
    r={'job_id':job,'task_id':e['task_id'],'candidate':candidate,'request':req,'request_hash':digest(req),'response':data,'response_hash':digest(data),'model':req['model'],'model_version':data.get('model'),'backend_revision':data.get('system_fingerprint','unavailable'),'input_tokens':u['prompt_tokens'],'output_tokens':u['completion_tokens'],'total_tokens':actual,'reasoning_tokens':rt,'final_content_tokens':u['completion_tokens']-rt if isinstance(rt,int)else 'unavailable','finish_reason':comp['finish_reason'],'completion':comp,'max_tokens':16384,'started_at':a['started_at'],'finished_at':now(),'latency_seconds':time.perf_counter()-start,'actual_attempt_id':aid,'reused':False,'gold_feedback':False,'gold_reflection':False,'skill_injected':False,'thinking':'default enabled; omitted','reasoning_effort':'default high; omitted','sampling':'temperature=0 sent but ignored in thinking mode; no provider seed support; independent calls, backend stochasticity unpinned','raw_stream':f'raw/{aid}.sse.gz'}
    save(path,r);save(ap,dict(a,status='completed',usage_known=True,total_tokens=actual,input_tokens=u['prompt_tokens'],output_tokens=u['completion_tokens'],response_hash=r['response_hash'],finished_at=r['finished_at']))
    pending.unlink()
    with self.lock:self.actual+=actual;self.reserved-=bound;self.active-=1;self.lock.notify_all()
    print(json.dumps({'job':job,'finish':r['finish_reason'],'tokens':actual,'new_tokens':self.actual}),flush=True)
    return r
   except Exception as ex:
    save(ap,dict(a,status='transport_failed',usage_known=False,error_type=type(ex).__name__,finished_at=now()))
    if pending.exists():pending.unlink()
    with self.lock:self.unknown+=bound;self.reserved-=bound;self.active-=1;self.lock.notify_all()
    print(json.dumps({'job':job,'attempt':attempt,'transport_error':type(ex).__name__,'usage_unknown_upper_bound':bound}),flush=True)
    if attempt<self.cfg['max_attempts_per_job']:time.sleep(2)
  raise RuntimeError('Bounded transport recovery exhausted: '+job)

def main():
 arg=argparse.ArgumentParser();arg.add_argument('stage',choices=['validation1','validation4','validation8','test1']);stage=arg.parse_args().stage
 cfg=read(OUT/'config.json');freeze=read(OUT/'evidence/pre_api_freeze.json')
 for p,h in freeze['files'].items():assert sha(ROOT/p)==h,p
 if stage=='test1':assert (OUT/'checkpoints/METHOD_FROZEN_FOR_TEST.json').exists()
 if stage=='validation8':assert read(OUT/'checkpoints/pass8_decision.json')['run_pass8']
 meta={r['task_id']:r for r in jl(OUT/'data/public_tasks.jsonl')};entries=jl(OUT/'data/public_prompts.jsonl')
 split='test'if stage=='test1'else 'validation';ks={'validation1':[1],'validation4':[2,3,4],'validation8':[5,6,7,8],'test1':[1]}[stage]
 jobs=[(e,k)for e in entries if meta[e['task_id']]['split']==split for k in ks]
 sealpath=OUT/'checkpoints'/f'{stage}_SEALED.json'
 if sealpath.exists():
  seal=read(sealpath)
  for p,h in seal['files'].items():assert sha(OUT/p)==h
  print('Completed stage reused; zero API calls');return
 random.Random(cfg['schedule_seed']+sum(ks)).shuffle(jobs)
 save('checkpoints/'+stage+'_schedule.json',[{'task_id':e['task_id'],'candidate':k}for e,k in jobs])
 runner=Runner(cfg);results=[];errors=[]
 with cf.ThreadPoolExecutor(max_workers=cfg['api_workers'])as pool:
  fs={pool.submit(runner.call,e,k):(e['task_id'],k)for e,k in jobs}
  for f in cf.as_completed(fs):
   try:results.append(f.result())
   except Exception as ex:errors.append({'job':fs[f],'error_type':type(ex).__name__})
 save('checkpoints/'+stage+'_progress.json',{'at':now(),'finished':len(results),'expected':len(jobs),'errors':errors,'peak_api_concurrency':runner.peak,'cumulative_new_known_tokens':runner.actual,'cumulative_unknown_token_bound':runner.unknown,'cumulative_http_attempts':runner.calls})
 if errors:raise RuntimeError('Stage incomplete; saved jobs retained, inspect progress before resuming')
 save(sealpath,{'sealed_at':now(),'stage':stage,'n':len(results),'files':{f"raw/{r['job_id']}.json":sha(OUT/'raw'/f"{r['job_id']}.json")for r in results},'labels_read':False,'peak_api_concurrency':runner.peak})
 print('SEALED '+stage,flush=True)
if __name__=='__main__':main()
