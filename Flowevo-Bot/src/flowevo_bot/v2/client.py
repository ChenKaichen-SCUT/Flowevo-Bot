"""One global budget and HTTP pool; raw safe logs, checkpointing, bounded 429 retry.

No math feedback enters this module. A timeout leaves a pending journal and is
not automatically resent because provider completion/billing may be unknown.
"""
import threading
import time
from pathlib import Path
from ..common import digest,read_json,write_json
from ..token_accounting import estimate_tokens
from runtime.llm_client import SYSTEM


class Budget:
    def __init__(self,max_calls=64,max_tokens=400000):
        self.max_calls=max_calls;self.max_tokens=max_tokens;self.calls=0;self.tokens=0;self.lock=threading.Lock()

    def reserve(self,request):
        amount=sum(estimate_tokens(m['content']) for m in request['messages'])+request['max_tokens']
        with self.lock:
            if self.calls+1>self.max_calls or self.tokens+amount>self.max_tokens:raise RuntimeError('Global predeclared budget exhausted')
            self.calls+=1;self.tokens+=amount


class Client:
    def __init__(self,output_dir,key,budget,transport=None):
        self.root=Path(output_dir);self.key=key;self.budget=budget;self.transport=transport

    def complete(self,prompt,*,job_id,purpose,max_tokens=4096):
        request={'model':'deepseek-flash','messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
                 'temperature':0.0,'max_tokens':max_tokens}
        identity=digest({'request':request,'job_id':job_id,'purpose':purpose,'endpoint':'https://api.deepseek.com/chat/completions'})
        path=self.root/(identity+'.json');pending=self.root/(identity+'.pending.json')
        if path.exists():
            record=read_json(path)
            if record['request']!=request or record['job_id']!=job_id:raise ValueError('Resume identity mismatch')
            self.budget.reserve(request)  # cached calls count against the same run budget
            return record
        if pending.exists():raise RuntimeError('Uncertain prior request; reconcile pending journal before resending')
        self.budget.reserve(request)
        start=time.monotonic();attempts=[]
        for attempt in range(3):
            write_json(pending,{'job_id':job_id,'call_id':identity,'request_hash':digest(request),'attempt':attempt+1,'purpose':purpose})
            try:
                if self.transport is not None:
                    status,data=self.transport(request)
                else:
                    import requests
                    response=requests.post('https://api.deepseek.com/chat/completions',headers={'Authorization':'Bearer '+self.key},json=request,timeout=180)
                    status=response.status_code
                    data=response.json() if status==200 else None
            except Exception as exc:
                write_json(self.root/(identity+'.error.json'),{'call_id':identity,'job_id':job_id,'type':type(exc).__name__,
                    'completion_and_billing':'unknown','attempts':attempts,'math_retry':False})
                raise RuntimeError('Transport failure; pending request preserved, no blind paid retry') from None
            attempts.append({'attempt':attempt+1,'http_status':status,'usage':data.get('usage') if data else None})
            if status==200:break
            write_json(self.root/(identity+'.infrastructure.json'),{'job_id':job_id,'attempts':attempts,'math_retry':False,'error_usage':'provider did not report usage'})
            if status not in (429,503) or attempt==2:raise RuntimeError(f'Provider HTTP {status}; body withheld')
            pending.unlink(missing_ok=True);time.sleep(2**attempt)
        usage=data.get('usage',{})
        record={'call_id':identity,'job_id':job_id,'purpose':purpose,'endpoint':'https://api.deepseek.com/chat/completions',
                'request':request,'response':data,'model':data.get('model'),'input_tokens':usage.get('prompt_tokens'),
                'output_tokens':usage.get('completion_tokens'),'total_tokens':usage.get('total_tokens'),
                'reasoning_tokens':usage.get('completion_tokens_details',{}).get('reasoning_tokens'),
                'latency':time.monotonic()-start,'attempts':attempts,'prompt_hash':digest(request),'response_hash':digest(data),
                'estimated_usage':False,'simulated':self.transport is not None}
        write_json(path,record);pending.unlink(missing_ok=True)
        if any(record[k] is None for k in ('input_tokens','output_tokens','total_tokens')):
            raise RuntimeError('Missing provider usage; raw response retained for reconciliation')
        if record['total_tokens']!=record['input_tokens']+record['output_tokens']:raise RuntimeError('Usage arithmetic mismatch')
        return record
