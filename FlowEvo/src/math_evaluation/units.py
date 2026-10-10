"""Small explicit exact unit registry; longest whole suffix, never substring deletion."""
import re
from dataclasses import dataclass
import sympy as s
@dataclass(frozen=True)
class Unit:
    name:str
    dimension:tuple
    scale:object

# SI definitions are exact. Count/currency/generic geometric units stay distinct.
_BASE={
'm':(('L',),s.Integer(1),('m','meter','meters','metre','metres')),
'cm':(('L',),s.Rational(1,100),('cm','centimeter','centimeters','centimetre','centimetres')),
'km':(('L',),s.Integer(1000),('km','kilometer','kilometers','kilometre','kilometres')),
'mm':(('L',),s.Rational(1,1000),('mm','millimeter','millimeters')),
'in':(('L',),s.Rational(127,5000),('in','inch','inches')),
'ft':(('L',),s.Rational(381,1250),('ft','foot','feet')),
'mi':(('L',),s.Rational(201168,125),('mi','mile','miles')),
's':(('T',),s.Integer(1),('s','sec','second','seconds')),
'min':(('T',),s.Integer(60),('min','minute','minutes')),
'h':(('T',),s.Integer(3600),('h','hr','hour','hours')),
'kg':(('M',),s.Integer(1),('kg','kilogram','kilograms')),
'g':(('M',),s.Rational(1,1000),('g','gm','gram','grams')),
'lb':(('M',),s.Rational(45359237,100000000),('lb','lbs','pound','pounds')),
'deg':(('angle',),s.pi/180,('deg','degree','degrees','°')),
'rad':(('angle',),s.Integer(1),('rad','radian','radians')),
'USD':(('currency:USD',),s.Integer(1),('dollar','dollars','usd')),
'cent':(('currency:USD',),s.Rational(1,100),('cent','cents')),
'cal':(('energy',),s.Rational(523,125),('calorie','calories','cal')),
'unit':(('abstract_length',),s.Integer(1),('unit','units')),
}
ALIASES={};UNITS={}
for name,(dim,scale,aliases) in _BASE.items():
    UNITS[name]=Unit(name,dim,scale)
    for a in aliases:ALIASES[a.lower()]=name
for name in ('m','cm','km','mm','in','ft','mi','unit'):
    for power,word in [(2,'square'),(3,'cubic')]:
        canonical=f'{name}^{power}';u=UNITS[name];UNITS[canonical]=Unit(canonical,tuple(x+str(power) for x in u.dimension),u.scale**power)
        for a in _BASE[name][2]:
            for alias in [word+' '+a,a+'^'+str(power),a+'^{'+str(power)+'}',a+('²' if power==2 else '³')]:ALIASES[alias]=canonical
for length in ('m','cm','km','in','ft','mi'):
    for time in ('s','min','h'):
        name=length+'/'+time;UNITS[name]=Unit(name,('L','T-1'),UNITS[length].scale/UNITS[time].scale)
        for a in _BASE[length][2]:
            for b in _BASE[time][2]:
                ALIASES[a+' per '+b]=name;ALIASES[a+'/'+b]=name
ALIASES['mph']='mi/h';ALIASES['kmph']='km/h';ALIASES['kph']='km/h'
ALIASES[r'^\circ']='deg';ALIASES[r'^{\circ}']='deg'

def unit_key(text):
    s=' '.join(text.lower().split()).strip()
    s=s.replace(r'\,',' ').replace(r'\!','').strip()
    return ALIASES.get(s)

def split_unit(value):
    s=re.sub(r'\s*\^\s*', '^',value.strip());direction=None
    m=re.search(r'\s+(less|more)$',s,re.I)
    if m:direction=m[1].lower();s=s[:m.start()].strip()
    if s.startswith(r'\$'):return s[2:].strip(),'USD',direction
    for alias in sorted(ALIASES,key=len,reverse=True):
        if s.lower().endswith(alias):
            start=len(s)-len(alias)
            if start and (s[start-1].isalpha() or s[start-1]=='\\'):continue
            value=s[:start].strip()
            if value:return value,ALIASES[alias],direction
    return s,None,direction

def expected_unit(q,target=None):
    from .text import presentation
    low=re.sub(r'\s*\^\s*','^',presentation(q).lower().replace('$',''))
    request=presentation(target or q).lower().replace('$','')
    # Last explicit output-unit request wins over units in the givens.
    found=[]
    for alias,name in ALIASES.items():
        if len(alias)<2:continue
        for m in re.finditer(r'\b(?:how many|in|expressed in|in terms of)\s+('+re.escape(alias)+r')(?![a-z])',low):found.append((m.start(),len(alias),name))
    if found:return max(found)[2],False
    if re.search(r'(?:number of|in) degrees|angle',request) and not re.search(r'(?:sin|cos|tan)|bisector|length',request):return 'deg',False
    if 'nearest cent' in low or re.search(r'how much[^?]*dollars',low):return 'USD',False
    if re.search(r'what.*(?:average )?speed',low):
        if 'mph' in low:return 'mi/h',False
        for a in sorted(ALIASES,key=len,reverse=True):
            if '/' in UNITS[ALIASES[a]].name and re.search(r'(?<![a-z])'+re.escape(a)+r'(?![a-z])',low):return ALIASES[a],False
    if re.search(r'by how much.*area change',low):return 'unit^2',False
    if re.search(r'(?:what|find|express|compute|calculate).*area',request) and not re.search(r'ratio|fraction|percent|sum|w \+|x \+',request):
        lengths=[(low.rfind(a),n) for a,n in ALIASES.items() if n in ('ft','cm','m','in','mi','unit') and len(a)>1 and re.search(r'\b'+re.escape(a)+r'\b',low)]
        if lengths:return max(lengths)[1]+'^2',False
        return 'unit^2',False
    if re.search(r'\b(?:radius|diameter|perimeter|length|distance|how tall)\b',request) and not re.search(r'ratio|fraction',request):
        lengths=[(low.rfind(a),n) for a,n in ALIASES.items() if n in ('ft','cm','m','in','mi','unit') and len(a)>1 and re.search(r'\b'+re.escape(a)+r'\b',low)]
        if lengths:return max(lengths)[1],False
    return None,False
