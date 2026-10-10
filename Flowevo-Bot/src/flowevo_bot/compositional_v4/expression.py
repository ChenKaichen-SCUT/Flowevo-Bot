"""Small exact integer syntax. No eval, sympify, generated Python or floating point.

An IntegerExpression is a tuple tagged int/add/mul/pow. Exponents are literal
nonnegative integers and are NEVER reduced modulo the task's modulus.
"""
import re
MAX_NODES=96
MAX_DEPTH=12
MAX_BITS=8192
MAX_EXPONENT=1000000
MAX_MODULUS=10000

class ScopeError(ValueError): pass

def canonical(node):
    op=node[0]
    if op=='int':return ('int',node[1])
    if op=='pow':return ('pow',canonical(node[1]),node[2])
    children=[]
    for child in node[1:]:
        c=canonical(child)
        children.extend(c[1:] if c[0]==op else [c])
    return (op,*sorted(children,key=repr))

def validate(node,depth=0):
    if depth>MAX_DEPTH or not isinstance(node,(tuple,list)) or not node:raise ScopeError('expression_depth_or_type')
    op=node[0]
    if op=='int':
        if len(node)!=2 or type(node[1]) is not int or node[1].bit_length()>MAX_BITS:raise ScopeError('integer_budget')
        return 1
    if op=='pow':
        if len(node)!=3 or type(node[2]) is not int or not 1<=node[2]<=MAX_EXPONENT:raise ScopeError('literal_positive_exponent_budget')
        if node[1]==('int',0) and node[2]==0:raise ScopeError('zero_to_zero_undefined')
        n=1+validate(node[1],depth+1)
    elif op in ('add','mul') and 3<=len(node)<=MAX_NODES:
        n=1+sum(validate(c,depth+1) for c in node[1:])
    else:raise ScopeError('untrusted_expression_operator')
    if n>MAX_NODES:raise ScopeError('expression_node_budget')
    return n

def parse_expression(text):
    if not isinstance(text,str) or not text or len(text)>1800:raise ScopeError('expression_text_budget')
    t=text.strip().rstrip('.,?').replace('−','-')
    for x in ('\\left','\\right','\\,','\\!','\\;','\\:','~'):t=t.replace(x,'')
    for x in ('\\times','\\cdot'):t=t.replace(x,'*')
    t=re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))','',t)
    t=t.replace('{','(').replace('}',')')
    if re.search(r'[^\d\s()+*^\-]',t):raise ScopeError('unsupported_integer_syntax')
    tokens=re.findall(r'\d+|[()+*^\-]',t)
    if len(tokens)>250:raise ScopeError('token_budget')
    at=0
    def atom(depth=0):
        nonlocal at
        if depth>MAX_DEPTH or at>=len(tokens):raise ScopeError('syntax_or_depth')
        token=tokens[at];at+=1
        if token=='(':
            node=add(depth+1)
            if at>=len(tokens) or tokens[at]!=')':raise ScopeError('unclosed_parenthesis')
            at+=1
        elif token.isdigit():
            if len(token)>1000:raise ScopeError('literal_size')
            node=('int',int(token))
        else:raise ScopeError('expected_integer_atom')
        if at<len(tokens) and tokens[at]=='^':
            at+=1;wrapped=at<len(tokens) and tokens[at]=='('
            if wrapped:at+=1
            if at>=len(tokens) or not tokens[at].isdigit():raise ScopeError('literal_nonnegative_exponent_required')
            if len(tokens[at])>7:raise ScopeError('exponent_budget')
            exponent=int(tokens[at]);at+=1
            if wrapped:
                if at>=len(tokens) or tokens[at]!=')':raise ScopeError('exponent_must_be_literal')
                at+=1
            node=('pow',node,exponent)
        return node
    def signed(depth):
        nonlocal at
        sign=1
        if at<len(tokens) and tokens[at] in ('+','-'):
            sign=-1 if tokens[at]=='-' else 1;at+=1
        node=atom(depth)
        return node if sign==1 else ('int',-node[1]) if node[0]=='int' else ('mul',('int',-1),node)
    def mul(depth):
        nonlocal at
        nodes=[signed(depth)]
        while at<len(tokens) and (tokens[at]=='*' or tokens[at]=='('):
            if tokens[at]=='*':at+=1
            nodes.append(signed(depth))
        return nodes[0] if len(nodes)==1 else ('mul',*nodes)
    def add(depth):
        nonlocal at
        nodes=[mul(depth)]
        while at<len(tokens) and tokens[at] in ('+','-'):
            op=tokens[at];at+=1;node=mul(depth)
            if op=='-':node=('int',-node[1]) if node[0]=='int' else ('mul',('int',-1),node)
            nodes.append(node)
        return nodes[0] if len(nodes)==1 else ('add',*nodes)
    result=add(0)
    if at!=len(tokens):raise ScopeError('unconsumed_expression_tokens')
    validate(result);return canonical(result)

def checked(n):
    if type(n) is not int or n.bit_length()>MAX_BITS:raise ScopeError('intermediate_integer_budget')
    return n

def exact_eval(node):
    op=node[0]
    if op=='int':return checked(node[1])
    if op=='pow':
        a=exact_eval(node[1]);e=node[2]
        if a==0 and e==0:raise ScopeError('zero_to_zero_undefined')
        if abs(a)>1 and abs(a).bit_length()*e>MAX_BITS:raise ScopeError('power_integer_budget')
        return checked(pow(a,e))
    values=[exact_eval(c) for c in node[1:]]
    n=0 if op=='add' else 1
    for v in values:n=checked(n+v if op=='add' else n*v)
    return n

def structure(node):
    if node[0]=='int':return 'Integer'
    if node[0]=='pow':return ['pow',structure(node[1]),'NonnegativeExponent']
    return [node[0],*[structure(c) for c in node[1:]]]

def walk(node):
    yield node
    if node[0]=='pow':yield from walk(node[1])
    elif node[0]!='int':
        for c in node[1:]:yield from walk(c)

def has_power(node):return any(n[0]=='pow' for n in walk(node))
