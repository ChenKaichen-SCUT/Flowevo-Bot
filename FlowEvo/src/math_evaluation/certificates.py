"""Small deterministic public-question proofs; no task IDs or learned gold rules."""
import re
import sympy as s
from .text import public_text

def parity_point(question):
    q=public_text(question).replace('$','')
    if not re.search(r'what other point.*graph',q,re.I):return None
    parity=re.search(r'\b(odd|even) function\b',q,re.I)
    point=re.search(r'passes through the point\s*\(\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\)',q,re.I)
    if not (parity and point):return None
    x,y=map(s.Integer,point.groups())
    if x==0:return None
    result=(-x,-y if parity[1].lower()=='odd' else y)
    return {'canonical':f'({result[0]},{result[1]})','method':'public_parity_graph_identity','premises':{'parity':parity[1].lower(),'known_point':[str(x),str(y)]},'proof':'Symmetric domain of odd/even function; f(-x) = -f(x) / f(x). Origin requires an additional domain assumption and is not used.'}

def area_direction(question):
    q=public_text(question).replace('$','')
    if not re.search(r'by how much.*area change',q,re.I):return None
    m=re.search(r'A\s+(\d+)\s+by\s+(\d+)\s+(?:square|rectangle).*length (decreased|increased) by\s+(\d+).*width (decreased|increased) by\s+(\d+)',q,re.I)
    if not m:return None
    x,y=int(m[1]),int(m[2]);dx=int(m[4])*(-1 if m[3].lower()=='decreased' else 1);dy=int(m[6])*(-1 if m[5].lower()=='decreased' else 1)
    if min(x,y,x+dx,y+dy)<=0:return None
    delta=(x+dx)*(y+dy)-x*y
    return {'delta':delta,'direction':'less' if delta<0 else 'more' if delta>0 else 'unchanged','method':'exact_public_rectangle_area_change','formula':'(x+dx)*(y+dy)-x*y'}
