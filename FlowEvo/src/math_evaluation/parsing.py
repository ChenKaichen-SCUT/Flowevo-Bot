"""Restricted ANTLR parser front end. No Python eval/parse_expr on answer text."""
import re
import sympy as s
from .models import Unsupported,Invalid
from .text import presentation,balanced

def explicit_tex_arguments(text):
    # TeX frac/sqrt arguments are either a balanced group or a single token.
    for command,n in [('frac',2),('sqrt',1)]:
        offset=0
        while True:
            m=re.search(r'\\'+command+r'(?![A-Za-z])',text[offset:])
            if not m:break
            start=offset+m.start();end=offset+m.end();pos=end;args=[]
            if pos<len(text) and text[pos]=='[':offset=pos+1;continue
            for _ in range(n):
                while pos<len(text) and text[pos].isspace():pos+=1
                if pos>=len(text):raise Unsupported('missing_tex_argument')
                if text[pos]=='{':
                    v,newpos=balanced(text,pos+1)
                    if v is None:raise Unsupported('unbalanced_tex_argument')
                    args.append('{'+v+'}');pos=newpos
                elif text[pos].isalnum():args.append('{'+text[pos]+'}');pos+=1
                else:break
            if len(args)==n:
                replacement='\\'+command+''.join(args);text=text[:start]+replacement+text[pos:];offset=start+len('\\'+command)
            else:offset=pos+1
    return text


COMMANDS={'frac','sqrt','pi','infty','sin','cos','tan','cot','sec','csc','arcsin','arccos','arctan','log','ln','exp','abs','cdot','times','div','pm','mp','le','leq','ge','geq','ne','neq','cup','cap','emptyset','varnothing','mathbb','begin','end','alpha','beta','gamma','delta','theta','phi','lambda','mu','omega','vert','lvert','rvert','langle','rangle','overline','binom','det','vec','mathbf','bold','text','mathrm'}

def guard(text,config):
    if len(text)>config.max_answer_chars:raise Unsupported('answer_length_limit')
    if any(x in text for x in ['__','`',';','"',"'",'@','#']):raise Unsupported('unsafe_or_unsupported_token')
    if re.search(r'(?<!\d)\.(?!\d)|\.{2,}',text):raise Unsupported('attribute_or_ellipsis_not_supported')
    commands=re.findall(r'\\([A-Za-z]+)',text)
    if set(commands)-COMMANDS:raise Unsupported('unsupported_latex_command:'+','.join(sorted(set(commands)-COMMANDS)))
    remaining=re.sub(r'\\[A-Za-z]+',' ',text)
    remaining=re.sub(r'\{(?:p|b|v|B|V)?matrix\}',' ',remaining)
    if re.search(r'[A-Za-z]{3,}',remaining):raise Unsupported('unparsed_prose_or_multiletter_identifier')
    if re.search(r'\d{101,}',text):raise Unsupported('integer_length_limit')
    # Bound dangerous literals before ANTLR/SymPy constructors can evaluate them.
    if re.search(r'\d{4,}\s*!',text):raise Unsupported('factorial_limit')
    if re.search(r'\^\s*\{?\s*[+-]?\d{4,}',text):raise Unsupported('exponent_limit')
    if text.count('!')>1 or text.count('^')>30:raise Unsupported('operator_complexity_limit')
    depth=0
    for c in text:
        if c in '{([':depth+=1
        if c in '})]':depth-=1
        if depth>config.max_nesting:raise Unsupported('nesting_limit')
    if depth!=0:raise Unsupported('unbalanced_delimiters')

def scalar(text,spec,config):
    from latex2sympy2_extended.latex2sympy2 import _Latex2Sympy,ConversionConfig
    from antlr4 import Token
    t=presentation(text).replace('−','-').replace('×',r'\times').replace('π',r'\pi').replace('∞',r'\infty').replace('<=',r'\le ').replace('>=',r'\ge ')
    for f in ('sqrt','sin','cos','tan','log','exp','abs'):
        t=re.sub(r'(?<![A-Za-z\\])'+f+r'\s*\(',lambda m:'\\'+f+'(',t)
    # TeX permits single digit tokens as unbraced fraction arguments.
    t=explicit_tex_arguments(t)
    t=t.replace('**','^').replace('±',r'\pm ')
    # Grouping commas within numeric tokens, not top-level solution separators.
    t=re.sub(r'(\d)\s*\{,\}\s*(?=\d)',r'\1,',t)
    if re.fullmatch(r'[+-]?\d{1,3}(?:,\s*\d{3})+(?:\.\d+)?',t):t=t.replace(',','').replace(' ','')
    t=re.sub(r'(?<=[{])([+-]?\d{1,3}(?:,\s*\d{3})+)(?=[}])',lambda m:re.sub(r'[,\s]','',m[0]),t)
    if '_' in t:raise Unsupported('subscript_requires_specific_answer_type')
    guard(t,config)
    cv=ConversionConfig(interpret_as_mixed_fractions=True,interpret_simple_eq_as_assignment=False,interpret_contains_as_eq=False,lowercase_symbols=False)
    parser=_Latex2Sympy(config=cv)
    syntax=parser.create_parser(t);syntax.math()
    if syntax.getTokenStream().LA(1)!=Token.EOF:raise Unsupported('unconsumed_mathematical_tokens')
    value=parser.parse(t)
    if isinstance(value,s.MatrixExpr):value=value.doit()
    if isinstance(value,s.MatrixBase):value=s.ImmutableMatrix(value)
    if not isinstance(value,(s.Basic,s.MatrixBase)):raise Unsupported('nonmathematical_parse')
    # Convert decimal literals to exact decimal rationals before any verification.
    decimals={x:s.Rational(str(x)) for x in value.atoms(s.Float)}
    if len(list(s.preorder_traversal(value)))>config.max_nodes:raise Unsupported('expression_complexity_limit')
    for p in value.atoms(s.Pow):
        if p.exp.is_number and abs(p.exp)>1000:raise Unsupported('exponent_limit')
    for f in value.atoms(s.factorial):
        if f.args[0].is_number and abs(f.args[0])>500:raise Unsupported('factorial_limit')
    # Domain assumptions come from the public question; never rename variables.
    repl={}
    for v in value.free_symbols:
        kwargs={} if spec.domain=='complex' else {'integer':True} if spec.domain=='integer' else {'real':True}
        if 'positive' in spec.assumptions:kwargs={'positive':True}
        elif 'nonnegative' in spec.assumptions:kwargs={'nonnegative':True}
        repl[v]=s.Symbol(str(v),**kwargs)
    # xreplace may cancel x/x. Domain obligations must be captured first.
    obligations=[]
    for node in s.preorder_traversal(value):
        if isinstance(node,s.Pow):
            if node.exp.is_number and node.exp<0:obligations.append(('nonzero',node.base))
            if spec.domain!='complex' and node.exp.is_Rational and node.exp.q%2==0:obligations.append(('nonnegative',node.base))
        if node.func==s.log and spec.domain!='complex':obligations.append(('positive',node.args[0]))
        if node.func in (s.tan,s.sec) and spec.domain!='complex':obligations.append(('nonzero',s.cos(node.args[0])))
        if node.func in (s.cot,s.csc) and spec.domain!='complex':obligations.append(('nonzero',s.sin(node.args[0])))
    repl.update(decimals)
    value=value.xreplace(repl)
    obligations=[(kind,x.xreplace(repl)) for kind,x in obligations]
    return value,obligations

def domain_set(value,obligations,spec):
    symbols=set(value.free_symbols)
    for _,expr in obligations:symbols.update(expr.free_symbols)
    conditions=[]
    for kind,x in obligations:
        cond={'nonzero':s.Ne,'nonnegative':s.Ge,'positive':s.Gt}[kind](x,0)
        if cond is s.false:return s.EmptySet
        if cond is not s.true:conditions.append(cond)
    if not conditions:return s.S.Complexes if spec.domain=='complex' else s.S.Integers if spec.domain=='integer' else s.S.Reals
    if len(symbols)!=1:return ('constraints',tuple(sorted(map(str,conditions))))
    var=next(iter(symbols));domain=s.S.Complexes if spec.domain=='complex' else s.S.Integers if spec.domain=='integer' else s.S.Reals
    for cond in conditions:
        if isinstance(cond,s.Unequality):domain-=s.solveset(cond.lhs-cond.rhs,var,domain=domain)
        elif spec.domain=='complex':return ('constraints',tuple(sorted(map(str,conditions))))
        else:domain=domain.intersect(s.solve_univariate_inequality(cond,var,relational=False))
    return domain
