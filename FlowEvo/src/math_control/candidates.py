"""Candidates from actually exposed text. Candidate presence is not correctness."""
import re,collections
from .parser_bridge import boxes,math_spans,presentation,parse_public
from .goals import check_goal

def candidate_events(question,reasoning):
    if not reasoning:return []
    candidates=[{'start':b.start,'end':b.end,'text':b.text,'source':'reasoning_box'} for b in boxes(reasoning)]
    marker=re.compile(r'\b(?:the\s+)?(?:final\s+)?(?:answer|result)\s*(?:is|would be|should be|=|:)\s*([^\n]+)',re.I)
    for m in marker.finditer(reasoning):
        text=m[1].strip();spans=math_spans(text)
        if spans:text=spans[0].text
        else:text=re.split(r'\.(?:\s|$)|\s+(?:because|since|so|which|but)\b',text,maxsplit=1)[0].strip()
        candidates.append({'start':m.start(),'end':m.end(),'text':text,'source':'explicit_reasoning_answer_marker'})
    # Bound parsing work; no reference value participates in candidate selection.
    candidates=sorted(candidates,key=lambda e:e['start'])
    if len(candidates)>32:candidates=candidates[:8]+candidates[-24:]
    events=[]
    for c in candidates:
        c=dict(c,context=reasoning[max(0,c['start']-100):min(len(reasoning),c['end']+180)],position_fraction=c['start']/max(1,len(reasoning)),observability='exposed_reasoning_text',correctness='not_known_online')
        if len(c['text'])>512:continue
        try:n=parse_public(c['text'],question);c.update(typed=True,normalized=n.to_dict(),canonical_key=str(n.to_dict()))
        except Exception as e:c.update(typed=False,parse_error=str(e)[:100])
        events.append(c)
    counts=collections.Counter(e['canonical_key'] for e in events if e['typed'])
    for e in events:e['same_candidate_occurrences']=counts.get(e.get('canonical_key'),0)
    return events

def finalization_decision(question,response,completion):
    message=response['choices'][0]['message'];events=candidate_events(question,message.get('reasoning_content') or '')
    if not completion['retry_required']:return {'trigger':False,'reason':'already_complete','events':events,'candidate':None,'interrupted_generation':False}
    eligible=[e for e in events if e['typed'] and e['position_fraction']>=.5 and (e['same_candidate_occurrences']>=2 or e['source']=='reasoning_box')]
    if not eligible:return {'trigger':False,'reason':'no_stable_typed_late_candidate','events':events,'candidate':None,'interrupted_generation':False}
    candidate=eligible[-1];goal=check_goal(question,message.get('reasoning_content') or '')
    if goal['high_confidence_mismatch'] or goal['goal_spec']['parse_confidence']=='uncertain':return {'trigger':False,'reason':'candidate_goal_uncertain_or_mismatched','events':events,'candidate':None,'interrupted_generation':False}
    return {'trigger':True,'reason':'incomplete_with_observed_typed_late_candidate','events':events,'candidate':candidate,'interrupted_generation':False,'candidate_is_not_verified_correct':True,'strategy':'new_short_finalization_request'}
