"""Offline-only adjudication. Never imported by controller or prompt builders."""
import re
from flowevo_bot.v2.evaluator import grade,extract,presentation
from .checks import extract_code,run_tests

def normalize(value,question):
 value=presentation(value)
 value=re.sub(r'(?<=\d),(?:\\!)?\s*(?=\d{3}(?:\D|$))','',value)
 value=re.sub(r'\\(?:!|,)','',value)
 if re.search('percent',question,re.I):
  if '=' in value:value=value.split('=')[-1].strip()
  value=value.replace('\\%','').replace('%','')
 if re.search(r'dollars?|\$|nearest cent',question,re.I):
  if '\\approx' in value and re.search('round|nearest',question,re.I):value=value.split('\\approx')[-1].strip()
  value=value.replace('\\$','').strip('$').strip()
  value=re.sub(r'\s*dollars?\.?$','',value,flags=re.I)
 if re.search('degrees|angle',question,re.I):value=value.replace('^\\circ','').replace('^{\\circ}','').replace('°','')
 if 'calories' in question.lower():value=re.sub(r'\s+calories$','',value,flags=re.I)
 if 'grams' in question.lower():value=re.sub(r'\s*(?:grams?|\\text\{\s*gm\s*\})$','',value,flags=re.I)
 return value.strip()

def score(task,solution,truncated,label):
 if task.domain=='code':
  r=run_tests(extract_code(solution),label['hidden_tests'],task.setup)
  return {'correct':r['passed'],'status':'hidden_tests','detail':r}
 raw=grade({'task_id':task.task_id,'question':task.problem,'solution':solution,'truncated':truncated,'gold_answer':label['gold_answer']})
 ans,_=extract(solution)
 if ans and not truncated:
  p,g=normalize(ans,task.problem),normalize(label['gold_answer'],task.problem)
  revised=grade({'task_id':task.task_id,'question':task.problem,'solution':'The answer is \\boxed{'+p+'}.','truncated':False,'gold_answer':g})
  return {'correct':revised['rechecked_correct'],'status':revised['parse_status'],'raw_grader':raw,'normalizations':{'candidate':p!=presentation(ans),'reference':g!=presentation(label['gold_answer'])}}
 return {'correct':raw['rechecked_correct'],'status':raw['parse_status'],'raw_grader':raw}
