"""Reference construction from full solution and public answer contract."""
import re
from .text import boxes,math_spans,presentation
from .models import Extraction,Candidate
from .extraction import extract_model

def build_reference(question,solution,spec):
    bs=boxes(solution)
    from .certificates import parity_point
    certificate=parity_point(question)
    if certificate:
        return {'status':'ok','candidates':[x.to_dict() for x in bs],'selected':certificate['canonical'],'complete':True,'reason':'public theorem proves a valid answer independently of candidate boxes','certificate':certificate,'reference_caveat':'Other reference points may require unstated domain assumptions.'}
    if not solution.strip():return {'status':'reference_invalid','candidates':[],'selected':None,'complete':False,'reason':'missing original reference solution'}
    # Explicit terminal conclusion outside earlier boxes takes precedence only
    # when it is syntactically an answer, not an unrelated numeric calculation.
    final_markers=list(re.finditer(r'(?:final answer\s*:|the answer is)\s*',solution,re.I))
    if final_markers and (not bs or final_markers[-1].start()>bs[-1].end):
        ex=extract_model(solution,spec=spec)
        return {'status':'ok','candidates':[x.to_dict() for x in bs]+ex.to_dict()['candidates'],'selected':ex.selected,'complete':ex.selected is not None,'reason':'explicit terminal reference conclusion supersedes earlier boxed work','omission_risk':False}
    if not bs:
        ex=extract_model(solution,spec=spec)
        return {'status':'ok' if ex.selected else 'reference_ambiguous','candidates':ex.to_dict()['candidates'],'selected':ex.selected,'complete':bool(ex.selected),'reason':'reference final-line extraction; full typed parsing required','omission_risk':True}
    chosen=bs
    if spec.all_solutions and len(bs)>1:
        terminal_start=solution.rfind('\n\n',0,bs[-1].start)+2
        chosen=[x for x in bs if x.start>=terminal_start]
        # A terminal all-roots clause may span multiple lines/paragraphs.
        assignments=[];other_assignments=[]
        if spec.target:
            for x in bs:
                pre=solution[max(0,x.start-80):x.start]
                m=re.search(r'([A-Za-z])\s*=\s*\$?\s*$',pre)
                if m and m[1]==spec.target:assignments.append(x)
                elif m:other_assignments.append(x)
        if assignments and len(assignments)+len(other_assignments)==len(bs):chosen=assignments
        elif len(chosen)<len(bs):
            # Earlier boxes might also be required solutions; do not silently lose them.
            return {'status':'reference_ambiguous','candidates':[x.to_dict() for x in bs],'selected':None,'complete':False,'reason':'all-solutions boxes span disconnected clauses without target evidence','omission_risk':True}
        if re.search(r'\b(?:example|extraneous|reject|discard)\b',solution[chosen[0].start:chosen[-1].end],re.I):
            return {'status':'reference_ambiguous','candidates':[x.to_dict() for x in bs],'selected':None,'complete':False,'reason':'candidate roots include exclusion/example language','omission_risk':True}
        return {'status':'ok','candidates':[x.to_dict() for x in bs],'selected':', '.join(x.text for x in chosen),'complete':True,'reason':'all-solutions contract + connected terminal roots or explicit requested-variable assignments','omission_risk':False,'multiple_boxes_reconstructed':True}
    # Single-answer multiple boxes are checked for equivalence by the engine.
    # No blind concatenation and no last-box-only assumption.
    return {'status':'ok','candidates':[x.to_dict() for x in bs],'selected':bs[-1].text,'complete':True,'reason':'boxed reference; multiple candidates require equality or explicit intermediate labeling','omission_risk':False,'alternative_candidates':[x.text for x in bs[:-1] if not re.search(r'\b(?:intermediate|example)\b',solution[max(solution.rfind('.',0,x.start),solution.rfind('\n',0,x.start))+1:x.start],re.I)]}
