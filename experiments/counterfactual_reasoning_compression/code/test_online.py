import online_pilot as online
from transport import Ledger

def test_staged_controller_accounts_for_first_stage_and_deduplicates(tmp_path,monkeypatch):
    monkeypatch.setattr(online,'OUT',tmp_path)
    sent=[]
    def fake(req):
        sent.append(req)
        first=req['max_tokens']==1024
        return {'choices':[{'message':{'content':'' if first else 'The answer is 5.',
            'reasoning_content':'The answer is 5.\n\nPositivity is checked and holds.\n\nUnfinished'},
            'finish_reason':'length' if first else 'stop'}],
            'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30,
                     'completion_tokens_details':{'reasoning_tokens':6}}}
    ledger=Ledger(tmp_path,fake)
    cfg={'methods':['B0_high','B1_fixed','B2_candidate','B3_repetition','B4_counterfactual'],
         'selected_rule':'candidate_clear','continuation_max_tokens':15360}
    cf={'mode':'beta_reasoning_prefix_replay','instructions':{'A':'Continue.','B':'Finish.','C':'Check briefly.'}}
    row=online.run_task({'task_id':'test','problem':'2+3?','subject':'number_theory','level':'Level 2'},ledger,cfg,cf)
    assert len(sent)==5  # B0 + shared first + unique A/B/C; no duplicate method calls
    assert row['choices']=={'B1_fixed':'B','B2_candidate':'B','B3_repetition':'A','B4_counterfactual':'C'}
    assert row['results'][0]['total_tokens']==30
    assert all(r['total_tokens']==60 and r['logical_calls']==2 for r in row['results'][1:])
    assert ledger.used==150
    online.run_task({'task_id':'test','problem':'2+3?','subject':'number_theory','level':'Level 2'},ledger,cfg,cf)
    assert len(sent)==5

def test_naturally_finished_first_stage_requires_no_extra_calls(tmp_path,monkeypatch):
    monkeypatch.setattr(online,'OUT',tmp_path)
    response={'choices':[{'message':{'content':'5','reasoning_content':'2+3=5.'},'finish_reason':'stop'}],
        'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30,'completion_tokens_details':{'reasoning_tokens':6}}}
    ledger=Ledger(tmp_path,lambda req:response)
    cfg={'methods':['B0_high','B1_fixed','B2_candidate','B3_repetition','B4_counterfactual'],
         'selected_rule':'candidate_clear','continuation_max_tokens':15360}
    row=online.run_task({'task_id':'done','problem':'2+3?','subject':'number_theory','level':'Level 2'},ledger,cfg,{})
    assert ledger.calls==2 and all(r['total_tokens']==30 for r in row['results'])
    assert all(not r['early_completion_triggered'] for r in row['results'])
