"""Visible final-answer extraction. Receives no reference, scores or reasoning field."""
import re
from .models import Candidate,Extraction
from .text import boxes,math_spans,presentation

def extract_model(text,finish_reason='stop',spec=None):
    if finish_reason=='length':return Extraction(None,status='prediction_incomplete',reason='provider length: no credit for hidden or partial answers')
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S|re.I)
    if re.search(r'<think>',text,re.I):return Extraction(None,status='prediction_incomplete',reason='unclosed hidden reasoning block')
    if not text.strip():return Extraction(None,status='prediction_incomplete',reason='empty visible answer')
    bs=boxes(text);candidates=list(bs)
    if re.search(r'\\(?:boxed|fbox)\s*\{',text) and not bs:return Extraction(None,status='prediction_incomplete',reason='unclosed final box')
    marker=re.compile(r'(?:\b(?:the\s+)?(?:final\s+)?answer\s*(?:is|:)\s*|\b(?:therefore|hence|thus)\b[, :]*)',re.I)
    explicit=[]
    for m in marker.finditer(text):
        prefix=text[max(0,m.start()-65):m.start()].lower()
        if re.search(r'(?:for example|example:|suppose|hypothetically)[^.!?\n]*$',prefix):continue
        suffix=text[m.end():].strip();line=suffix.split('\n\n')[0].strip()
        if '\n' in line and not (spec and spec.all_solutions) and not any(x in line for x in (r'\[',r'\begin','$$')):line=line.splitlines()[0].strip()
        if not line:continue
        clause_end=m.end()+len(text[m.end():])-len(text[m.end():].lstrip())+len(line)
        # A box wholly contained in the final answer clause is its scalar payload;
        # multiple boxes are retained as multiple submitted answers.
        sub=boxes(line)
        if sub:line=', '.join(x.text for x in sub)
        else:
            spans=math_spans(line)
            if len(spans)==1 and not line[:spans[0].start].strip() and re.fullmatch(r'[\s.,]*',line[spans[0].end:]):line=spans[0].text
        c=Candidate(line,m.start(),clause_end,'final_marker',text[max(0,m.start()-40):m.end()+80]);explicit.append(c);candidates.append(c)
    if explicit and not (bs and bs[-1].start>=explicit[-1].end):
        selected=explicit[-1].text
        # Preserve ordinary unit suffixes outside math delimiters.
        return Extraction(selected,candidates,reason='last explicit final submission; no gold selection')
    if bs:
        last=bs[-1];tail=text[last.end:]
        prefix=text[max(text.rfind('\n\n',0,last.start),text.rfind('.',0,last.start))+1:last.start]
        if re.search(r'for example|example:|hypothetically|suppose',prefix,re.I):return Extraction(None,candidates,'unknown','boxed example is not a final submission')
        if re.search(r'not (?:the |a )?(?:final )?answer|still need|unfinished|for example',tail,re.I):return Extraction(None,candidates,'prediction_incomplete','box followed by unresolved continuation')
        start=text.rfind('\n\n',0,last.start)+2
        group=[x for x in bs if x.start>=start]
        selected=', '.join(x.text for x in group) if spec and spec.all_solutions else last.text
        return Extraction(selected,candidates,reason='terminal boxed submission')
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    final=lines[-1]
    spans=math_spans(text)
    if spans and not text[spans[-1].end:].strip(' .\n'):
        final=spans[-1].text
    if re.search(r'for example|suppose|consider',final,re.I):return Extraction(None,candidates,'unknown','only explanatory example')
    # Normalizer, not a gold match, determines whether this final line is math.
    return Extraction(final,candidates+[Candidate(final,text.rfind(lines[-1]),len(text),'last_line')],reason='last standalone line; requires full typed parsing')
