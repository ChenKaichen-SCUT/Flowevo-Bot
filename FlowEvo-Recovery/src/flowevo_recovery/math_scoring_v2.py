"""Offline scorer v2: explicit final answers, typed equivalence and limited proofs.

Extends flowevo_bot.v2.evaluator without changing historical frozen graders.
No task IDs or reference-specific rules. Never import into an online solver.
"""
import re
from flowevo_bot.v2.evaluator import balanced, presentation, split_top, parse_scalar


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


def complete(text):
    a,_=extract(text)
    return a is not None and bool(a.strip())


def normalize(value,question):
    s=presentation(value);notes=[]
    # Thousands grouping only within a scalar token, never across top-level tuples.
    s=re.sub(r'(?<![\d,])([+-]?\d{1,3}(?:,\d{3})+)(?![\d,])',lambda m:m[0].replace(',',''),s) if not (s.startswith(('(', '[',r'\{'))) else s
    # Recognized units are conditioned on the public question, never on the gold.
    groups=[(r'calories?',r'calories?'),(r'grams?',r'(?:grams?|gm)'),(r'dollars?|nearest cent',r'dollars?'),(r'centimeters?|\bcm\b',r'(?:centimeters?|cm)'),(r'meters?',r'meters?'),(r'inches|inch',r'(?:inches|inch)'),(r'feet|foot|\bft\b',r'(?:feet|foot|ft)'),(r'pounds?',r'pounds?'),(r'miles?',r'miles?'),(r'hours?',r'hours?'),(r'minutes?',r'minutes?'),(r'seconds?',r'seconds?')]
    for trigger,unit in groups:
        if re.search(trigger,question,re.I):
            pat=r'\s*(?:\\(?:text|mathrm|mbox)\{\s*)?(?:(?:square|cubic)\s+)?'+unit+r'\s*\}?(?:\^\{?[23]\}?)?$'
            ns=re.sub(pat,'',s,flags=re.I)
            if ns!=s:notes.append('question_unit');s=ns.strip()
    if re.search(r'dollars?|nearest cent',question,re.I):s=s.replace(r'\$','').strip('$')
    if re.search(r'degrees?|angle',question,re.I):
        s=re.sub(r'(?:\^\{?\\circ\}?|°|\s*(?:\\text\{\s*)?degrees?\s*\}?)$','',s,flags=re.I)
    if re.search(r'(?:what|which|find|express|as a|to a)[^?\n]*percent',question,re.I):s=re.sub(r'\\?%$','',s).strip()
    # A magnitude question accepts a magnitude plus explicitly retained direction.
    # No sign is changed; signed-change questions are deliberately excluded.
    if re.search(r'by how much.*area change',question,re.I):
        m=re.fullmatch(r'(.+?)\s+square units(?:\s+(less|more))?',s,re.I)
        if m:s=m[1];notes.append('area_change_magnitude; direction='+str(m[2]))
    if re.search(r'how many',question,re.I):
        # Count/measurement labels must literally occur in the question (allow possessive).
        m=re.search(r'(?:\s+|\s*\\text\{\s*)([A-Za-z]+(?:\s+[A-Za-z]+){0,3})\s*\}?$',s)
        if m:
            noun=m[1].strip();qwords=question.lower().replace("'s",'')
            if re.search(r'\b'+re.escape(noun.lower())+r'\b',qwords):
                s=s[:m.start()].strip();notes.append('literal_question_count_unit')
    # Explicit variable assignment is removable only for the variable requested.
    target=re.search(r'(?:values? of|solve for)\s*\$?([A-Za-z])\b',question,re.I)
    if target:
        var=target[1];parts=re.split(r'\s*\\text\{\s*or\s*\}\s*|\s+or\s+|,',s)
        cleaned=[re.sub(r'^'+re.escape(var)+r'\s*=\s*','',v.strip()) for v in parts]
        if any(x!=y.strip() for x,y in zip(cleaned,parts)):
            s=','.join(cleaned);notes.append('requested_variable_assignment')
    return presentation(s),notes


def parse_value(value,question=''):
    from sympy import FiniteSet,Interval,Tuple,Union,ImmutableMatrix
    s=presentation(value)
    matrix=re.fullmatch(r'\\begin\{([pb]matrix)\}(.*?)\\end\{\1\}',s,re.S)
    if matrix:
        rows=[[parse_scalar(x.strip()) for x in row.split('&')] for row in matrix[2].split('\\\\')]
        if not rows or any(x is None for row in rows for x in row) or len({len(row) for row in rows})!=1:return None
        return ImmutableMatrix(rows)
    if r'\cup' in s:
        xs=[parse_value(x,question) for x in s.split(r'\cup')]
        if any(x is None for x in xs):return None
        try:return Union(*xs)
        except Exception:return None
    if s.startswith(r'\{') and s.endswith(r'\}'):
        xs=[parse_scalar(x) for x in split_top(s[2:-2])]
        return None if any(x is None for x in xs) else FiniteSet(*xs)
    if len(s)>1 and s[0] in '([' and s[-1] in ')]':
        parts=split_top(s[1:-1])
        if len(parts)>1:
            xs=[parse_scalar(x) for x in parts]
            if any(x is None for x in xs):return None
            interval=bool(re.search(r'interval|inequalit|solution set|range of|domain|\\ge|\\le|[<>]',question,re.I)) or 'infty' in s or s[0]=='[' or s[-1]==']'
            if interval:
                if len(xs)!=2:return None
                return Interval(*xs,left_open=s[0]=='(',right_open=s[-1]==')')
            if s[0]=='(' and s[-1]==')':return Tuple(*xs)
            return None
    parts=split_top(s)
    if len(parts)>1:
        if re.search(r'roots|solutions|set of|values of|solve for',question,re.I):
            xs=[parse_scalar(x) for x in parts]
            return None if any(x is None for x in xs) else FiniteSet(*xs)
        return None
    return parse_scalar(s)


def symmetry_witness(question,pv):
    """Prove a forced graph point by parity; no assumption that 0 is in domain."""
    from sympy import Tuple
    if not isinstance(pv,Tuple) or len(pv)!=2:return None
    if not re.search(r'what other point must.*graph pass through',question,re.I):return None
    parity=re.search(r'\b(odd|even) function\b',question,re.I)
    point=re.search(r'passes through the point\s*\$?\(\s*([+-]?\d+(?:/\d+)?)\s*,\s*([+-]?\d+(?:/\d+)?)\s*\)',question,re.I)
    if not parity or not point:return None
    from sympy import Rational
    x,y=Rational(point[1]),Rational(point[2]);target=Tuple(-x,-y if parity[1].lower()=='odd' else y)
    if pv==target and pv!=Tuple(x,y):return {'theorem':'odd: f(-x)=-f(x); even: f(-x)=f(x)','given':str(Tuple(x,y)),'entailed':str(target)}
    return None


def grade(item):
    from sympy import Set,Tuple,Expr,simplify,MatrixBase
    from math_verify import verify
    a,status=extract(item['solution'])
    out={'task_id':item.get('task_id'),'answer':a,'original_correct':item.get('original_correct'),'correct':None,'status':status,'evidence':{}}
    if item.get('truncated'):return dict(out,correct=False,status='truncated')
    if a is None:return out
    try:
        q=item.get('question','');p,pnotes=normalize(a,q);g,gnotes=normalize(item['gold_answer'],q)
        out['evidence'].update(candidate_normalized=p,reference_normalized=g,normalizations=pnotes+gnotes)
        direction=re.search(r'square units\s+(less|more)$',a,re.I)
        if direction:
            # Verify the direction from the public rectangular-area transformation;
            # a magnitude-only reference must not silently excuse the wrong sign.
            cleanq=q.replace('$','')
            rect=re.search(r'A\s+(\d+)\s+by\s+(\d+)\s+square.*length (decreased|increased) by\s+(\d+).*width (decreased|increased) by\s+(\d+)',cleanq,re.I)
            if not rect:return dict(out,status='unknown_direction_constraint')
            x,y=int(rect[1]),int(rect[2]);dx=int(rect[4])*(-1 if rect[3].lower()=='decreased' else 1);dy=int(rect[6])*(-1 if rect[5].lower()=='decreased' else 1)
            delta=(x+dx)*(y+dy)-x*y
            out['evidence']['public_area_change']=delta
            if (direction[1].lower()=='less' and delta>=0) or (direction[1].lower()=='more' and delta<=0):return dict(out,correct=False,status='wrong_direction')
        explicit_dim=re.search(r'\b(square|cubic)\s+(?:inches|meters|centimeters|feet)\b',a,re.I)
        if explicit_dim:
            expected=2 if re.search(r'area',q,re.I) else (3 if re.search(r'volume|how many cubic|can.*hold',q,re.I) else None)
            if expected and expected!=(2 if explicit_dim[1].lower()=='square' else 3):return dict(out,correct=False,status='wrong_unit_dimension')
        option=lambda s:re.fullmatch(r'(?:\\text\{)?\(?([A-E])\)?\}?',s)
        pm,gm=option(p),option(g)
        if re.search(r'\([A-E]\)',q) and pm and gm:return dict(out,correct=pm[1]==gm[1],status='option_label')
        plain=lambda s:re.sub(r'^\\text\{\s*([A-Za-z]+)\s*\}$',r'\1',s)
        pt,gt=plain(p),plain(g)
        if re.search(r'\bwho\b',q,re.I) and all(re.fullmatch(r'[A-Za-z]+',x) and re.search(r'\b'+re.escape(x)+r'\b',q) for x in (pt,gt)):
            return dict(out,correct=pt==gt,status='named_choice')
        pv,gv=parse_value(p,q),parse_value(g,q)
        out['evidence'].update(candidate_parsed=str(pv),reference_parsed=str(gv))
        proof=symmetry_witness(q,pv)
        if proof:return dict(out,correct=True,status='public_question_witness',proof=proof)
        if pv is None or gv is None:return dict(out,status='unknown_parse')
        if isinstance(pv,MatrixBase) or isinstance(gv,MatrixBase):
            if not (isinstance(pv,MatrixBase) and isinstance(gv,MatrixBase)):return dict(out,status='unknown_answer_type')
            eq=pv.shape==gv.shape and all(simplify(x-y)==0 for x,y in zip(pv,gv))
            return dict(out,correct=bool(eq),status='matrix')
        if isinstance(pv,(Set,Tuple)) or isinstance(gv,(Set,Tuple)):
            if type(pv)!=type(gv):return dict(out,status='unknown_answer_type')
            if isinstance(pv,Tuple):eq=len(pv)==len(gv) and all(verify(y,x,timeout_seconds=2,strict=True) for x,y in zip(pv,gv))
            else:eq=pv==gv
            return dict(out,correct=bool(eq),status='structured')
        # Preserve domains: no cancellation-based identity acceptance when the raw
        # rational forms differ and symbols may disappear during parser evaluation.
        def variable_denominator(s):
            for m in re.finditer(r'\\frac\s*',s):
                pos=m.end()
                for component in range(2):
                    while pos<len(s) and s[pos].isspace():pos+=1
                    if pos>=len(s):return True
                    if s[pos]=='{':v,pos=balanced(s,pos+1)
                    else:v,pos=s[pos],pos+1
                    if v is None:return True
                    if component==1:
                        parsed=parse_scalar(v)
                        if parsed is None or parsed.free_symbols:return True
            for m in re.finditer(r'/\s*(\([^)]*\)|[A-Za-z][A-Za-z0-9_]*|\\[A-Za-z]+)',s):
                v=parse_scalar(m[1])
                if v is None or v.free_symbols:return True
            return False
        if re.sub(r'\s+','',p)!=re.sub(r'\s+','',g) and any(variable_denominator(s) for s in (p,g)):
            return dict(out,status='unknown_domain_obligations')
        result=bool(verify(gv,pv,timeout_seconds=2,strict=True))
        if isinstance(pv,Expr) and isinstance(gv,Expr):out['evidence']['difference']=str(simplify(pv-gv))
        return dict(out,correct=result,status='symbolic')
    except Exception as e:return dict(out,status='unknown_exception',error=type(e).__name__)
