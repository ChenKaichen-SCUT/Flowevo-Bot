import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from run_budgets import eligible,request_for

def reply(text,finish='stop',correct=None):
 return {'response':{'choices':[{'message':{'content':text},'finish_reason':finish}]},'offline_correct':correct}

def test_wrong_complete_never_escalates():
 assert not eligible(reply('The answer is 999.',correct=False))
 assert not eligible(reply('The answer is 999.',correct=True))
 assert eligible(reply('',finish='length'))
 assert eligible(reply('Work in progress'))
 assert eligible(reply(r'The answer is \boxed{1',finish='stop'))
 assert eligible(reply('The answer is 1.',finish='length'))

def test_only_budget_changes():
 task={'request':{'model':'deepseek-flash','messages':[{'role':'system','content':'s'},{'role':'user','content':'u'}],'temperature':0.0,'max_tokens':4096}}
 for n in (8192,16384):
  r=request_for(task,n)
  assert [k for k in r if r[k]!=task['request'][k]]==['max_tokens']
  assert 'thinking' not in r and r['max_tokens']==n
