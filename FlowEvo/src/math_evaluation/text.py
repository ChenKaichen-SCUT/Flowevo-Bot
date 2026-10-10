"""Balanced structural text scanning; does not compare candidate answers."""
import re
from .models import Candidate,Unsupported

def balanced(text,start,left='{',right='}'):
    depth=1
    for i in range(start,len(text)):
        if text[i]==left:depth+=1
        elif text[i]==right:depth-=1
        if depth==0:return text[start:i],i+1
    return None,len(text)

def boxes(text):
    out=[]
    for m in re.finditer(r'\\(?:boxed|fbox)\s*\{',text):
        val,end=balanced(text,m.end())
        if val is not None:out.append(Candidate(val,m.start(),end,'boxed',text[max(0,m.start()-120):min(len(text),end+80)]))
    return out

def math_spans(text):
    out=[]
    pat=r'\\\[(.*?)\\\]|\\\((.*?)\\\)|\$\$(.*?)\$\$|(?<!\\)\$(.*?)(?<!\\)\$'
    for m in re.finditer(pat,text,re.S):
        val=next(x for x in m.groups() if x is not None)
        out.append(Candidate(val,m.start(),m.end(),'math_environment',text[max(0,m.start()-70):m.end()+50]))
    return out

def presentation(value):
    s=value.strip().strip('*').strip().removesuffix('.').strip()
    # Only peel balanced outer presentation, never discard semantic suffixes.
    for _ in range(6):
        prior=s
        for left,right in [(r'\(',r'\)'),(r'\[',r'\]'),('$$','$$'),('$','$')]:
            if s.startswith(left) and s.endswith(right) and len(s)>len(left)+len(right):s=s[len(left):-len(right)].strip();break
        for cmd in ('boxed','fbox','text','mathrm','textrm','mbox','operatorname'):
            m=re.match(r'\\'+cmd+r'\s*\{',s)
            if m:
                value,end=balanced(s,m.end())
                if value is not None and not s[end:].strip():s=value.strip();break
        if s==prior:break
    s=s.replace(r'\displaystyle','').replace(r'\textstyle','').replace(r'\left','').replace(r'\right','').replace(r'\dfrac',r'\frac').replace(r'\tfrac',r'\frac')
    s=re.sub(r'\\(?:,|!|;|:|quad\b|qquad\b|enspace\b)',' ',s)
    # Text wrappers are unwrapped structurally, including nested braces.
    for _ in range(10):
        m=re.search(r'\\(?:text|mathrm|textrm|mbox)\s*\{',s)
        if not m:break
        val,end=balanced(s,m.end())
        if val is None:raise Unsupported('unbalanced_text_wrapper')
        s=s[:m.start()]+' '+val+' '+s[end:]
    return re.sub(r'\s+',' ',s).strip()

def split_top(s,separator=','):
    depth=0;start=0;out=[]
    for i,c in enumerate(s):
        if c in '([{':depth+=1
        elif c in ')]}':depth-=1
        elif c==separator and depth==0:out.append(s[start:i].strip());start=i+1
    return out+[s[start:].strip()]

def public_text(q):return re.sub(r'\[asy\].*?\[/asy\]',' ',q,flags=re.S)
