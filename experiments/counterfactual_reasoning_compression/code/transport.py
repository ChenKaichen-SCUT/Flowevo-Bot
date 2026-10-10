"""Global durable budget, including rejected and cancelled feasibility probes."""
from common import *
import threading,time,gzip,requests

class BudgetStop(RuntimeError):pass

def token_bound(request):
    # Conservative UTF-8 byte bound for tokenizer input plus chat framing.
    return sum(len(str(m.get(k,'')).encode()) for m in request['messages'] for k in ('content','reasoning_content'))+1024+request['max_tokens']

class Ledger:
    def __init__(self,out=OUT,transport=None,max_calls=150,max_tokens=350000):
        self.out=Path(out);self.transport=transport;self.max_calls=max_calls;self.max_tokens=max_tokens
        self.key=(ROOT/'miyao.txt').read_text().strip() if transport is None else None
        for name in ('raw','attempts'):(self.out/name).mkdir(parents=True,exist_ok=True)
        for pending in (self.out/'attempts').glob('*.pending.json'):
            final=pending.with_name(pending.name.replace('.pending.json','.json'))
            if not final.exists():save(final,dict(read(pending),status='unknown_after_crash',usage_known=False))
            pending.unlink()
        old=[read(p) for p in (self.out/'attempts').glob('*.json')]
        self.calls=len(old);self.used=sum(r.get('total_tokens',0) for r in old if r['usage_known'])
        self.unknown=sum(r['reserved_tokens'] for r in old if not r['usage_known'])
        self.active=self.peak=self.reserved=0;self.lock=threading.Condition()

    def reserve(self,bound):
        with self.lock:
            while self.active and self.used+self.unknown+self.reserved+bound>self.max_tokens:self.lock.wait(.1)
            if self.calls>=self.max_calls or self.used+self.unknown+self.reserved+bound>self.max_tokens:raise BudgetStop('User call/token cap would be exceeded')
            self.calls+=1;self.active+=1;self.reserved+=bound;self.peak=max(self.peak,self.active)

    def call(self,job,request,meta=None,endpoint='https://api.deepseek.com/chat/completions',cancel_chars=None):
        assert request['model']=='deepseek-flash' and 0<request['max_tokens']<=16384
        path=self.out/'raw'/(job+'.json')
        if path.exists():
            record=read(path);assert record['request']==request and record['endpoint']==endpoint
            assert record.get('response_hash')==digest(record.get('response'))
            return record
        # Unknown crash attempts are never invisibly resubmitted.
        if (self.out/'attempts'/(job+'.json')).exists():raise RuntimeError('Existing failed attempt requires explicit inspection: '+job)
        bound=token_bound(request);self.reserve(bound);start=time.perf_counter()
        attempt=dict(job_id=job,started_at=now(),reserved_tokens=bound,request_hash=digest(request),endpoint=endpoint)
        pending=self.out/'attempts'/(job+'.pending.json');ap=self.out/'attempts'/(job+'.json')
        save(pending,dict(attempt,request=request));data=None;status='transport_failed';http=None;known=False;usage={};error=None;trace={}
        try:
            if self.transport:data=self.transport(request);http=200;status='completed'
            else:
                with requests.post(endpoint,json=request,headers={'Authorization':'Bearer '+self.key},stream=True,timeout=(30,600)) as response:
                    http=response.status_code;response.encoding='utf-8'
                    if http!=200:
                        error=response.text.replace(self.key,'[REDACTED]')[:2000]
                        status='http_rejected';known=http in (400,401,403,404,422);usage={'total_tokens':0} if known else {}
                    else:data,trace=self.consume(response,self.out/'raw'/(job+'.sse.gz'),cancel_chars);status='cancelled_probe' if trace['cancelled'] else 'completed'
            if data is not None:
                usage=data.get('usage') or {};known=isinstance(usage.get('total_tokens'),int)
                if known:
                    assert usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens']
                    assert usage['total_tokens']<=bound
                if status=='completed' and not known:raise RuntimeError('Completed response missing usage')
        except Exception as exc:
            error=type(exc).__name__
        finally:
            total=usage.get('total_tokens',0)
            record=dict(attempt,request=request,meta=meta or {},http_status=http,status=status,error=error,
                response=data,response_hash=digest(data),usage_known=known,total_tokens=total if known else None,
                input_tokens=usage.get('prompt_tokens'),output_tokens=usage.get('completion_tokens'),
                reasoning_tokens=usage.get('completion_tokens_details',{}).get('reasoning_tokens'),
                latency_seconds=time.perf_counter()-start,finished_at=now(),stream_observation=trace)
            save(path,record);save(ap,dict(attempt,status=status,usage_known=known,total_tokens=total if known else 0,
                http_status=http,error=error,finished_at=record['finished_at']))
            pending.unlink()
            with self.lock:
                self.used+=total if known else 0;self.unknown+=0 if known else bound
                self.active-=1;self.reserved-=bound;self.lock.notify_all()
            print(json.dumps(dict(job=job,status=status,tokens=record['total_tokens'],cumulative_tokens=self.used,unknown_bound=self.unknown)),flush=True)
        return record

    @staticmethod
    def consume(response,path,cancel_chars=None):
        obj={};content=[];reason=[];usage=None;finish=None;done=False;cancelled=False;chunks=0
        with gzip.open(path,'wt',encoding='utf-8') as f:
            for line in response.iter_lines(decode_unicode=True,chunk_size=1):
                if isinstance(line,bytes):line=line.decode()
                f.write((line or '')+'\n')
                if not line or not line.startswith('data:'):continue
                data=line[5:].strip()
                if data=='[DONE]':done=True;break
                part=json.loads(data);chunks+=1
                if 'error' in part:raise RuntimeError('Provider stream error')
                for key in ('id','model','created','system_fingerprint'):
                    if key in part:obj[key]=part[key]
                if part.get('usage'):usage=part['usage']
                for c in part.get('choices',[]):
                    if c.get('finish_reason') is not None:finish=c['finish_reason']
                    d=c.get('delta',{});reason.append(d.get('reasoning_content') or '');content.append(d.get('content') or '')
                if cancel_chars is not None and sum(map(len,reason))>=cancel_chars:
                    cancelled=True;break
        if not cancelled and (not done or finish is None or usage is None):raise RuntimeError('Incomplete stream')
        obj.update(object='chat.completion',usage=usage,choices=[dict(index=0,finish_reason=finish,message=dict(role='assistant',reasoning_content=''.join(reason),content=''.join(content)))])
        return obj,dict(cancelled=cancelled,done=done,chunks=chunks,visible_reasoning_chars=sum(map(len,reason)),received_final_usage=usage is not None)

def base_request(messages,max_tokens):
    return dict(model='deepseek-flash',messages=messages,temperature=0,max_tokens=max_tokens,stream=True,stream_options={'include_usage':True})
