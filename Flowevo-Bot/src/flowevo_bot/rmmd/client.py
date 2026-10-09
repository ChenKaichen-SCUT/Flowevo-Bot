"""Durable single-attempt paid calls under a global actual+inflight budget."""
import hashlib,json,threading,time
from pathlib import Path
from flowevo_bot.common import digest,write_json,read_json
SYSTEM='You are an expert programmer and mathematician.'
ENDPOINT='https://api.deepseek.com/chat/completions'

class Budget:
    def __init__(self,max_calls=120,max_tokens=200000):
        self.max_calls=max_calls;self.max_tokens=max_tokens;self.calls=0;self.actual=0;self.reserved=0;self.lock=threading.Lock();self.failed=False
    def reserve(self,request):
        # UTF-8 bytes are a conservative upper bound for ordinary BPE input;
        # 512 extra tokens cover fixed message framing. Completion is capped.
        bound=sum(len(m['content'].encode()) for m in request['messages'])+512+request['max_tokens']
        with self.lock:
            if self.failed or self.calls>=self.max_calls or self.actual+self.reserved+bound>self.max_tokens:raise RuntimeError('hard_budget_stop')
            self.calls+=1;self.reserved+=bound
        return bound
    def settle(self,bound,actual):
        with self.lock:
            self.reserved-=bound;self.actual+=actual
            if actual>bound or self.actual+self.reserved>self.max_tokens:self.failed=True;raise RuntimeError('provider_usage_exceeded_reservation')
    def fail(self):
        with self.lock:self.failed=True

class Client:
    def __init__(self,root,key,budget,transport=None):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.key=key;self.budget=budget;self.transport=transport;self.accounted=set();self.lock=threading.Lock()
    def complete(self,prompt,job_id,code_hash):
        request={'model':'deepseek-flash','messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],'temperature':0.0,'max_tokens':4096}
        identity=digest({'request':request,'job_id':job_id,'code_hash':code_hash,'endpoint':ENDPOINT})
        path=self.root/(identity+'.json');pending=self.root/(identity+'.pending.json')
        if pending.exists():raise RuntimeError('unknown_prior_billing_no_resend')
        if path.exists():
            record=read_json(path)
            if record['request']!=request or record['code_hash']!=code_hash:raise ValueError('cache_identity')
            with self.lock:
                if identity not in self.accounted:
                    bound=self.budget.reserve(request);self.budget.settle(bound,record['total_tokens']);self.accounted.add(identity)
            return record
        bound=self.budget.reserve(request);write_json(pending,{'call_id':identity,'job_id':job_id,'request':request,'code_hash':code_hash,'reserved_tokens':bound})
        start=time.perf_counter()
        try:
            if self.transport:status,data=self.transport(request)
            else:
                import requests
                response=requests.post(ENDPOINT,headers={'Authorization':'Bearer '+self.key},json=request,timeout=180)
                status=response.status_code;data=response.json() if status==200 else None
            if status!=200:raise RuntimeError('http_'+str(status))
            usage=data['usage'];total=usage['total_tokens']
            if total!=usage['prompt_tokens']+usage['completion_tokens']:raise ValueError('usage_arithmetic')
            record={'call_id':identity,'job_id':job_id,'request':request,'response':data,'code_hash':code_hash,'prompt_hash':digest(request),'response_hash':digest(data),'endpoint':ENDPOINT,'http_attempts':1,'infrastructure_retries':0,'correctness_retries':0,'input_tokens':usage['prompt_tokens'],'output_tokens':usage['completion_tokens'],'total_tokens':total,'latency':time.perf_counter()-start,'simulated':self.transport is not None,'reserved_tokens':bound}
            write_json(path,record);pending.unlink();self.budget.settle(bound,total)
            with self.lock:self.accounted.add(identity)
            return record
        except Exception as exc:
            self.budget.fail();write_json(self.root/(identity+'.error.json'),{'job_id':job_id,'error_type':type(exc).__name__,'error_code':str(exc) if isinstance(exc,(RuntimeError,ValueError)) else 'transport_failure','billing_unknown':True,'retry':False})
            raise RuntimeError('call_failed_pending_retained') from None
