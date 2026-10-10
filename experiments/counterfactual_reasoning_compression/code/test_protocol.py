from common import *
from states import *
from transport import *
import pytest

def request():return base_request([{'role':'user','content':'What is 2+3?'}],128)
def response():return {'choices':[{'message':{'content':'5','reasoning_content':'2+3=5'},'finish_reason':'stop'}],
    'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30,'completion_tokens_details':{'reasoning_tokens':6}}}

def test_budget_call_cap(tmp_path):
    ledger=Ledger(tmp_path,lambda req:response(),max_calls=1)
    ledger.call('a',request())
    with pytest.raises(BudgetStop):ledger.call('b',request())

def test_budget_tokens_reserve_before_request(tmp_path):
    ledger=Ledger(tmp_path,lambda req:pytest.fail('must not send'),max_tokens=10)
    with pytest.raises(BudgetStop):ledger.call('a',request())

def test_completed_resume_never_calls_again(tmp_path):
    ledger=Ledger(tmp_path,lambda req:response());r=ledger.call('a',request())
    assert ledger.call('a',request())==r and ledger.calls==1 and ledger.used==30

def test_crash_unknown_reserved(tmp_path):
    (tmp_path/'attempts').mkdir();save(tmp_path/'attempts/a.pending.json',{'reserved_tokens':500})
    ledger=Ledger(tmp_path,lambda req:response())
    assert ledger.unknown==500 and ledger.calls==1

def test_prefix_observations_do_not_read_future():
    prefix='The answer is 17.\n\nWe need to check positivity.'
    first=asdict(observe('x','Find the answer.',prefix))
    full=prefix+'\n\nActually the answer is 19.'
    assert first==asdict(observe('x','Find the answer.',full[:len(prefix)]))
    assert first['recent_unresolved']

def test_arbitrary_number_is_not_candidate():
    assert not candidate_events('Find a probability.','Intermediate probability is 0.5. The count is 7.')
    assert candidate_events('Find a probability.','Thus the answer is 0.5.')

def test_balanced_boundaries():
    text='Step one.\n\nA formula \\frac{1\n\n}{2}.\n\nFinal.'
    pos=boundary_near(text,.5)
    assert safe_boundary(text,pos) and not text[:pos].endswith('{1')

def test_cancel_stream_cannot_claim_exact_usage(tmp_path):
    class Stream:
        def iter_lines(self,**kwargs):
            yield 'data: '+json.dumps({'choices':[{'delta':{'reasoning_content':'thinking more'},'finish_reason':None}]})
    data,trace=Ledger.consume(Stream(),tmp_path/'cancel.gz',4)
    assert trace['cancelled'] and data['usage'] is None and not trace['received_final_usage']

def test_empty_final_keeps_usage(tmp_path):
    raw=response();raw['choices'][0]['message']['content']='';raw['choices'][0]['finish_reason']='length'
    ledger=Ledger(tmp_path,lambda req:raw);r=ledger.call('a',request())
    assert r['total_tokens']==30 and ledger.used==30

def test_config_resume_mismatch_rejected(tmp_path):
    ledger=Ledger(tmp_path,lambda req:response());ledger.call('a',request())
    changed=request();changed['max_tokens']=129
    with pytest.raises(AssertionError):ledger.call('a',changed)
