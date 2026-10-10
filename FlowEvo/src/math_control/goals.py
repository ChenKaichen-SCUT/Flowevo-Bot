"""Conservative public GoalSpec and observable target-mismatch evidence."""
from dataclasses import dataclass,asdict
import re
from .parser_bridge import infer_spec,normalize,CFG,presentation,boxes

@dataclass(frozen=True)
class GoalSpec:
    target_object:str
    target_operation:str
    target_variables:tuple
    domain_constraints:tuple
    quantity_constraints:tuple
    answer_cardinality:object
    unit_requirements:object
    required_output_type:str
    target_question_span:str
    parse_confidence:str
    source:str='public_question_only'
    def to_dict(self):return asdict(self)

WORDS={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
def goal_spec(question):
    q=re.sub(r'\[asy\].*?\[/asy\]',' ',question,flags=re.S);q=q.replace('$','')
    requests=list(re.finditer(r'\b(?:find|compute|calculate|determine|what(?: is| are)?|how many|solve for|which)\b',q,re.I))
    target=q[requests[-1].start():] if requests else q
    # Preserve the requested object, including consecutive/n and operation.
    operation='sum' if re.search(r'\bsum\b',target,re.I) else 'product' if re.search(r'\bproduct\b',target,re.I) else 'count' if re.search(r'how many|number of',target,re.I) else 'solve' if re.search(r'roots|solutions|solve for|values of',target,re.I) else 'value'
    count=re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:(?:smallest|largest|positive|negative|such|consecutive|distinct)\s+)*(?:integers|numbers|roots|solutions)\b',target,re.I)
    # If 'consecutive' appears in givens and target says 'such', retain its binding.
    consecutive=bool(re.search(r'consecutive (?:positive |negative )?(?:integers|numbers)',q,re.I) and count)
    n=(WORDS.get(count[1].lower()) or int(count[1])) if count and count[1].isdigit() else WORDS.get(count[1].lower()) if count else None
    obj=target
    quantity=[]
    if n:quantity.append(f'object_count={n}')
    if consecutive:quantity.append('objects_are_consecutive');obj=f'{n} consecutive integers' if n else 'consecutive integers'
    spec=infer_spec(question)
    constraints=tuple(m[0] for m in re.finditer(r'\b(?:positive|negative|nonnegative|distinct|real|integer|complex|all|smallest|largest)\b',target,re.I))
    cardinality='all' if spec.all_solutions else 1
    if spec.kind=='finite_set' and n:cardinality=n
    requested_unit=spec.unit if re.search(r'\b(?:in|how many)\s+(?:(?:square|cubic)\s+)?(?:meters?|metres?|centimeters?|centimetres?|feet|inches|yards?|degrees?|radians?|dollars?|grams?|kilograms?|hours?|minutes?|seconds?|calories?)\b',target,re.I) else None
    return GoalSpec(obj,operation,(spec.target,) if spec.target else (),constraints,tuple(quantity),cardinality,requested_unit,spec.kind,target,'uncertain' if spec.uncertain else 'rule_supported')

def final_answer(text):
    matches=list(re.finditer(r'(?:the\s+(?:final\s+)?answer\s+is|final\s+answer\s*:)\s*([^\n]*)',text,re.I))
    if matches:return matches[-1][1].strip().removesuffix('.')
    bs=boxes(text);return bs[-1].text if bs else None

def check_goal(question,visible_text):
    goal=goal_spec(question);answer=final_answer(visible_text);evidence=[]
    if goal.parse_confidence=='uncertain':return {'goal_spec':goal.to_dict(),'status':'uncertain','high_confidence_mismatch':False,'evidence':[]}
    # Only affirmative final target descriptions near the submitted result count.
    tail=visible_text[-2400:]
    drift=re.search(r'(?:sum|product)\s+(?:of\s+)?(?:the\s+)?(?:\w+\s+){0,5}(?:starting (?:integers|values|numbers)|valid starts)|(?:the\s+)?(?:four|three|two|\d+)\s+smallest\s+(?:such\s+)?starting\s+integers',tail,re.I)
    if 'objects_are_consecutive' in goal.quantity_constraints and goal.target_operation in ('sum','product') and drift:
        context=tail[max(0,drift.start()-50):min(len(tail),drift.end()+100)]
        if not re.search(r'\b(?:not|rather than|instead of|incorrect)\b',context[:max(0,drift.start()-max(0,drift.start()-50))],re.I):evidence.append({'type':'target_object_changed','requested':goal.target_object,'observed':drift[0],'span':context})
    if answer:
        spec=infer_spec(question)
        try:
            value=normalize(answer,spec,CFG)
            if isinstance(goal.answer_cardinality,int) and goal.answer_cardinality>1 and value.kind=='finite_set' and len(value.value)!=goal.answer_cardinality:
                evidence.append({'type':'explicit_answer_cardinality_mismatch','expected':goal.answer_cardinality,'observed':len(value.value)})
        except Exception as exc:
            if (str(exc)=='wrong_requested_unit' and goal.unit_requirements is not None) or (str(exc)=='wrong_requested_numeral_base' and spec.base is not None) or (str(exc)=='nonreal_answer_in_real_domain' and spec.domain=='real'):
                evidence.append({'type':'explicit_public_constraint_violation','constraint':str(exc),'answer':answer})
    return {'goal_spec':goal.to_dict(),'status':'mismatch' if evidence else 'no_high_confidence_mismatch','high_confidence_mismatch':bool(evidence),'evidence':evidence,'correctness_claim':False}
