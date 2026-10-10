from common import *
from transport import Ledger,base_request
def main():
    # Prefix contains a synthetic nonce absent from user text; no benchmark label.
    messages=[{'role':'system','content':'You are a precise assistant.'},
        {'role':'user','content':'Continue from your reasoning notes and return the computed integer only.'}]
    reasoning='The hidden work item was 137+286. I computed 137+286=423. The final result is ready.\n'
    ledger=Ledger()
    probes=[('audit_beta_reasoning',base_request(messages+[dict(role='assistant',content='',reasoning_content=reasoning,prefix=True)],128),
             'https://api.deepseek.com/beta/chat/completions',None),
            ('audit_beta_final_prefix',base_request(messages+[dict(role='assistant',content='The answer is ',reasoning_content=reasoning,prefix=True)],128),
             'https://api.deepseek.com/beta/chat/completions',None),
            ('audit_text_reprompt',base_request(messages+[dict(role='user',content='Visible working notes:\n'+reasoning+'\nFinish with the computed integer only.')],128),
             'https://api.deepseek.com/chat/completions',None),
            ('audit_cancel',base_request([dict(role='user',content='Find the sum of the squares of the first twenty positive integers. Work through the arithmetic.')],128),
             'https://api.deepseek.com/chat/completions',40)]
    results=[]
    for name,request,endpoint,cancel in probes:
        results.append(ledger.call(name,request,dict(stage='api_feasibility',synthetic_not_benchmark=True),endpoint,cancel))
    def content(r):return ((r.get('response') or {}).get('choices') or [{}])[0].get('message',{}).get('content','')
    facts=dict(at=now(),beta_reasoning_http=results[0]['http_status'],beta_reasoning_contains_nonce='423' in content(results[0]),
        beta_final_http=results[1]['http_status'],beta_final_contains_nonce='423' in content(results[1]),
        text_reprompt_contains_nonce='423' in content(results[2]),cancel=results[3]['stream_observation'],
        cancellation_exact_tokens=results[3]['total_tokens'],unknown_token_bound=ledger.unknown,
        mode='beta_reasoning_prefix_replay' if results[0]['http_status']==200 and '423' in content(results[0]) else 'text_prefix_reprompt',
        internal_state_resume_proven=False,comment='Accepted textual reasoning prefix is not a KV-cache snapshot. Socket close does not prove backend termination or request-specific final billing.')
    save('evidence/api_feasibility.json',facts);print(json.dumps(facts))
if __name__=='__main__':main()
