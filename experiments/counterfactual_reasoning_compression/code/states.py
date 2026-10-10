"""Transparent, prefix-only observations. These are evidence cues, not proofs."""
from dataclasses import dataclass,asdict
import re,unicodedata

def normalize(text):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip().lower()

def paragraphs(text):
    result=[];start=0
    for match in re.finditer(r'\n\s*\n',text):
        end=match.start()
        if text[start:end].strip():result.append((start,end,text[start:end]))
        start=match.end()
    if text[start:].strip():result.append((start,len(text),text[start:]))
    return result

def safe_boundary(text,pos):
    prefix=text[:pos]
    return (prefix.count('{')==prefix.count('}') and prefix.count(r'\[')==prefix.count(r'\]')
        and prefix.count(r'\(')==prefix.count(r'\)') and prefix.count('$$')%2==0
        and (prefix.replace('$$','').count('$')%2==0))

def boundary_near(text,fraction):
    ends=[end for _,end,_ in paragraphs(text) if end<len(text) and safe_boundary(text,end)]
    if not ends:return None
    return min(ends,key=lambda end:abs(end/len(text)-fraction))

def candidate_events(problem,text):
    # Explicit target wording prevents arbitrary gold-matching numbers from
    # being counted as candidate formation. This function never receives gold.
    targets=[]
    for word in ('probability','area','volume','sum','product','domain','range','angle','remainder','maximum','minimum'):
        if re.search(r'\b'+word+r'\b',problem,re.I):targets.append(word)
    pattern=re.compile(r'(?:(?:the|our|final)\s+answer\s*(?:is|should be|would be|must be|=)|'
        r'(?:thus|therefore|so)[,:]?\s+(?:the\s+)?answer\s*(?:is|=)?)\s*([^\n]{1,180})',re.I)
    events=[]
    for match in pattern.finditer(text):
        expression=re.split(r'\.(?=\s|["\x27]|$)',match.group(1))[0].strip().strip('"')
        if not re.search(r'\d|\\(?:frac|sqrt|pi|infty)|[=<>]',expression):continue
        if re.search(r'\[your answer\]|we (?:need|must|should)|not (?:yet|known)|to (?:find|compute)',expression,re.I):continue
        events.append(dict(start=match.start(),end=match.start(1)+len(expression),
            expression=expression,evidence=text[match.start():match.start(1)+len(expression)],
            target_alignment='explicit answer phrase' if 'answer' in match.group(0).lower() else 'question target noun'))
    return events

@dataclass
class ReasoningState:
    task_id:str
    observed_chars:int
    current_candidate:str|None
    candidate_count:int
    distinct_candidate_count:int
    stable_candidate_repeats:int
    completed_steps:list
    unresolved_checks:list
    check_evidence:list
    repetition_evidence:list
    revision_evidence:list
    recent_unresolved:bool
    constraint_check_seen:bool
    explicit_candidate:bool
    evidence_scope:str='Only problem and observed prefix; no future continuation, reference or grade'

def observe(task_id,problem,prefix):
    steps=paragraphs(prefix)
    candidates=candidate_events(problem,prefix)
    candidate=candidates[-1]['expression'] if candidates else None
    norms=[normalize(c['expression']) for c in candidates]
    stable=0
    for value in reversed(norms):
        if value==norms[-1]:stable+=1
        else:break
    checks=[];unresolved=[];revisions=[];repeats=[];seen={}
    for start,end,step in steps:
        evidence=dict(start=start,end=end,text=step[:500])
        if re.search(r'\b(check|verify|indeed|satisf|consistent|valid|confirm)\w*\b',step,re.I):checks.append(evidence)
        if re.search(r'\b(need to check|must check|need to verify|not sure|unclear|maybe|but wait)\b',step,re.I):unresolved.append(evidence)
        if re.search(r'\b(wait|actually|mistake|incorrect|correction|instead|reconsider)\b',step,re.I):revisions.append(evidence)
        key=normalize(step)
        if key in seen and len(key)>35:repeats.append(dict(evidence,earlier_start=seen[key],kind='exact normalized paragraph repetition'))
        seen[key]=start
    if stable>=2:
        repeats.append(dict(kind='repeated same explicitly stated candidate',count=stable,
                            evidence=candidates[-stable:]))
    recent_start=steps[-3][0] if len(steps)>=3 else 0
    recent_unresolved=any(e['start']>=recent_start for e in unresolved)
    constraint=any(re.search(r'\b(domain|positive|negative|integer|root|range|boundary|condition|extraneous|constraint)\w*\b',e['text'],re.I) for e in checks)
    return ReasoningState(task_id,len(prefix),candidate,len(candidates),len(set(norms)),stable,
        [dict(start=s,end=e,text=t[:400]) for s,e,t in steps[-5:]],unresolved[-5:],checks[-5:],
        repeats[-5:],revisions[-5:],recent_unresolved,constraint,bool(candidates))

def features(state):
    state=asdict(state) if isinstance(state,ReasoningState) else state
    return {k:state[k] for k in ('task_id','observed_chars','candidate_count','distinct_candidate_count',
        'stable_candidate_repeats','recent_unresolved','constraint_check_seen','explicit_candidate')}|{
        'checks_seen':len(state['check_evidence']),'repetitions_seen':len(state['repetition_evidence']),
        'revisions_seen':len(state['revision_evidence'])}
