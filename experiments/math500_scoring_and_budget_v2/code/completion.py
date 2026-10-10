"""Purely syntactic completion detection, isolated from all scoring/label code."""
import re

def balanced(text, start, left='{', right='}'):
    depth = 1
    for i in range(start, len(text)):
        depth += (text[i] == left) - (text[i] == right)
        if depth == 0:
            return text[start:i], i + 1
    return None, len(text)

def extract(text):
    candidates=[]
    for m in re.finditer(r'\\(?:boxed|fbox)\s*\{',text):
        value,end=balanced(text,m.end());candidates.append((m.start(),value,'boxed' if value is not None else 'incomplete_box'))
    for m in re.finditer(r'(?:The\s+(?:final\s+)?answer\s+is|Final\s+answer\s*:)\s*([^\n]*)',text,re.I):
        value=m[1].strip().strip('*').strip().removesuffix('.')
        candidates.append((m.start(),value or None,'final_marker' if value else 'incomplete_answer'))
    if not candidates:return None,'missing_final_answer'
    _,v,s=max(candidates,key=lambda x:x[0])
    if v and (v.count('{')!=v.count('}') or v.endswith(('=',':',',','\\'))):return None,'incomplete_answer'
    return v,s


def detect(task_id,response,max_tokens):
 choice=response['choices'][0];finish=choice.get('finish_reason');text=choice['message'].get('content') or ''
 answer,extraction=extract(text);present=answer is not None and bool(answer.strip())
 usage=response.get('usage',{});output=usage.get('completion_tokens')
 reached=output is not None and output>=max_tokens
 if finish=='length':reason='provider_length'
 elif reached:reason='output_limit_reached'
 elif not text.strip():reason='empty_visible_content'
 elif not present:reason='missing_or_incomplete_explicit_final'
 elif finish!='stop':reason='unrecognized_finish_reason'
 else:reason=None
 return {'task_id':task_id,'finish_reason':finish,'final_answer_present':present,'extracted_answer':answer,'extraction_status':extraction,'visible_chars':len(text),'output_limit_reached':reached,'completion_status':'complete' if reason is None else 'incomplete_or_uncertain','retry_required':reason is not None,'retry_reason':reason}
