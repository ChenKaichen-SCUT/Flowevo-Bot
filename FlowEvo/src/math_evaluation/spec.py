"""Explicit public-question answer contracts; uncertain requests stay unknown."""
import re
from .models import AnswerSpec
from .text import public_text

def infer_spec(question):
    q=public_text(question);plain=q.replace('$','');low=plain.lower()
    # Take the last explicit request, not an incidental object in the givens.
    matches=list(re.finditer(r'\b(?:find|compute|calculate|simplify|solve|subtract|round|convert|determine|what(?: is| are)?|which|how (?:many|old|tall|long|much)|by how much|for which|express|enter|give|write|is .*even)\b',plain,re.I))
    semantic=[m for m in matches if not re.match(r'(?:express|enter|give|write)\s+(?:(?:your|the) answer|it in)',plain[m.start():],re.I)]
    matches=semantic or matches
    target_text=plain[matches[-1].start():] if matches else plain
    target_low=target_text.lower()
    target=None
    for pat in [r'(?:values? of|solve for)\s*(?:the\s+)?([a-zA-Z])\b',r'\bfind\s+([A-Za-z])(?:\(|\b)']:
        m=re.search(pat,plain,re.I)
        if m:target=m[1];break
    all_solutions=bool(re.search(r'(?:all (?:the |real |possible )*(?:solutions|roots|values)|(?:roots|solutions),? separated by commas|real roots of)',plain,re.I))
    if re.search(r'(?:sum|product|number|count) of (?:all |the |real )*(?:roots|solutions)',target_text,re.I):all_solutions=False
    if all_solutions and not target:
        target='x' if re.search(r'\bx\b',q) else None
    # Prompt-provided answer vocabularies are distinct from algebra symbols.
    quoted=re.findall(r'"([A-Za-z]+)"',target_text)
    choices=tuple(dict.fromkeys(quoted)) if len(quoted)>=2 else ()
    if choices:return AnswerSpec(kind='choice',choices=choices,evidence=('explicit quoted answer vocabulary',))
    if re.search(r'(?:^|\n)\s*A[.)]\s',plain):
        choices=tuple(dict.fromkeys(re.findall(r'(?:^|\n)\s*([A-Z])[.)]\s',plain))) or tuple('ABCDE')
        return AnswerSpec(kind='choice',choices=choices,evidence=('explicit multiple-choice labels',))
    if re.search(r'\b(?:odd|even).*\b(?:odd|even).*neither',target_text,re.I):return AnswerSpec(kind='choice',choices=('odd','even','neither'),evidence=('parity category request',))
    if re.search(r'what letter|which letter',plain,re.I):return AnswerSpec(kind='text',evidence=('letter requested',))
    if re.search(r'\bwho\b',target_low):
        names=tuple(dict.fromkeys(re.findall(r'\b[A-Z][a-z]+\b',q)))
        return AnswerSpec(kind='choice',choices=names,evidence=('named choice requested',))
    base_matches=list(re.finditer(r'(?:answer|express|write)[^.?]*?in base\s*\$?(\d+)\$?',plain,re.I))
    base_match=base_matches[-1] if base_matches else re.search(r'in base\s*(\d+)\s*[.?]?$',target_text,re.I)
    base=int(base_match[1]) if base_match else None
    if base and not 2<=base<=36:return AnswerSpec(uncertain=True,evidence=('unsupported numeral base',))
    places=None
    for pattern,n in [(r'nearest (?:integer|whole number)',0),(r'nearest (?:tenth|10th)',1),(r'nearest (?:hundredth|100th|cent)',2),(r'nearest (?:thousandth|1000th)',3)]:
        if re.search(pattern,plain,re.I):places=n
    mp=re.search(r'(\d+) decimal places',plain,re.I)
    if mp:places=int(mp[1])
    assumptions=[]
    # Generic positivity in the givens is not an assumption on every symbol.
    # Conservative inference leaves these unset; callers may supply an explicit spec.
    domain='complex' if re.search(r'complex (?:number|root)|\bi\b',plain) else 'real'
    if all_solutions and re.search(r'integer (?:roots|solutions|values)',plain,re.I):domain='integer'
    kind='unknown';evidence=[]
    if re.search(r'interval notation|for which values|(?:find|what is|determine) (?:the )?(?:domain|range)\b',target_text,re.I):kind='interval';evidence.append('domain/range or inequality parameter request')
    elif all_solutions or re.search(r'unordered set|set of.*(?:solutions|roots)|determine the.*set|comma-separated list, in either order',target_text,re.I):kind='finite_set';evidence.append('all solutions or unordered set requested')
    elif not re.search(r'how many|number of|sum of|smallest.*coordinate',target_text,re.I) and re.search(r'ordered (?:pair|triple|quadruple|tuple)|coordinates|find the (?:center|reflection of the point|point)|what other point|at which point',target_text,re.I):kind='tuple';evidence.append('ordered geometric object requested')
    elif re.search(r'(?:find|compute|determine).*projection|\bproj\b|find (?:the |a )?matrix\b|compute\s*\\\[\s*\\begin\{[pbv]?matrix\}',target_text,re.I):kind='matrix';evidence.append('matrix or projection requested')
    elif re.search(r'(?:find|determine).*equation|in the form.*y\s*=|image of the line',target_text,re.I):kind='equation';evidence.append('equation requested')
    elif re.search(r'find the remainder|remainder when the polynomial',plain,re.I):kind='polynomial';evidence.append('polynomial remainder requested')
    elif re.search(r'\b(?:compute|evaluate|calculate|simplify|solve|subtract|round|convert|express|enter|find|determine|what|which|how much|how many|how old|how tall|how long|by how much)\b',plain,re.I):kind='expression';evidence.append('explicit mathematical value request; candidate must fully parse')
    # Percent input convention is determined by the requested output, not givens.
    percent='percent_number' if re.search(r'(?:what|which|find|express|as a)[^?\n]*percent',plain,re.I) else None
    if percent:kind='percentage'
    from .units import expected_unit
    unit,allow=expected_unit(plain,target_text)
    if percent:unit=None
    if unit and kind=='expression':kind='quantity'
    if base:kind='base_numeral'
    return AnswerSpec(kind=kind,target=target,domain=domain,all_solutions=all_solutions,unordered=kind=='finite_set',unit=unit,allow_unit_conversion=allow,decimal_places=places,percent_mode=percent,base=base,assumptions=tuple(assumptions),evidence=tuple(evidence),uncertain=kind=='unknown')
