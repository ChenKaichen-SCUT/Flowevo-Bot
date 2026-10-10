"""Durable single-attempt requests. One shared ledger/reservation budget across stages."""
import json,hashlib,threading,time
from pathlib import Path
ENDPOINT='https://api.deepseek.com/chat/completions'
SYSTEM='You are an expert programmer and mathematician.'
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def save(p,x):
 temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');temp.replace(p)

class BudgetStop(RuntimeError):pass
class Client:
 def __init__(self,root,key,config,code_hash,transport=None):
  self.root=Path(root);self.key=key;self.config=config;self.code_hash=code_hash;self.transport=transport
  self.lock=threading.Condition();self.reserved=0;self.active=0;self.failed=False
  if list(self.root.glob('*.pending.json')):raise RuntimeError('unknown prior billing: pending requests prohibit blind resends')
  prior=[json.loads(p.read_text()) for p in self.root.glob('*.json') if not p.name.endswith('.error.json')]
  self.calls=len(prior);self.actual=sum(x['total_tokens'] for x in prior)
  if self.calls>config['max_calls'] or self.actual>config['max_tokens']:raise BudgetStop('existing ledger over budget')
 def complete(self,task,prompt,job_id,stage,action):
  request={'model':self.config['model'],'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
    'temperature':self.config['temperature'],'max_tokens':self.config[task.domain+'_max_tokens']}
  if task.domain=='code':request['thinking']={'type':'disabled'}
  identity=digest({'job_id':job_id,'request':request,'endpoint':ENDPOINT});p=self.root/(identity+'.json')
  if p.exists():
   r=json.loads(p.read_text());assert r['request']==request;return r
  bound=sum(len(x['content'].encode()) for x in request['messages'])+512+request['max_tokens']
  with self.lock:
   while not self.failed and self.actual+self.reserved+bound>self.config['max_tokens'] and self.active:self.lock.wait(timeout=1)
   if self.failed or self.calls>=self.config['max_calls'] or self.actual+self.reserved+bound>self.config['max_tokens']:raise BudgetStop('hard_global_budget_stop')
   self.calls+=1;self.active+=1;self.reserved+=bound
  pending=self.root/(identity+'.pending.json');save(pending,{'request':request,'job_id':job_id,'reserved_tokens':bound})
  started=time.time()
  try:
   if self.transport:data=self.transport(request)
   else:
    import requests
    response=requests.post(ENDPOINT,headers={'Authorization':'Bearer '+self.key},json=request,timeout=180)
    if response.status_code!=200:raise RuntimeError('http_'+str(response.status_code))
    data=response.json()
   usage=data['usage'];total=usage['total_tokens'];assert total==usage['prompt_tokens']+usage['completion_tokens']
   if total>bound:raise RuntimeError('usage_above_reserved_bound')
   r={'call_id':identity,'task_id':task.task_id,'domain':task.domain,'stage':stage,'action':action,'job_id':job_id,
     'request':request,'response':data,'request_hash':digest(request),'response_hash':digest(data),'code_hash':self.code_hash,
     'input_tokens':usage['prompt_tokens'],'output_tokens':usage['completion_tokens'],'total_tokens':total,
     'started_unix':started,'seconds':time.time()-started,'http_attempts':1,'infrastructure_retries':0,'correctness_retries':0,'reserved_tokens':bound,'simulated':self.transport is not None}
   save(p,r);pending.unlink()
   with self.lock:self.actual+=total;self.reserved-=bound;self.active-=1;self.lock.notify_all()
   return r
  except Exception as e:
   with self.lock:self.failed=True;self.active-=1;self.lock.notify_all()
   save(self.root/(identity+'.error.json'),{'job_id':job_id,'error_type':type(e).__name__,'billing_unknown':True,'retry':False})
   raise RuntimeError('request failed; pending retained; no resend') from None
