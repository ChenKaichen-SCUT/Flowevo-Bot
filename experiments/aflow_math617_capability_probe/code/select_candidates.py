"""Public-only typed answer equivalence and deliberately narrow exact certificates.

No evaluator, reference builder, label file, task-specific rule or model calls.
Parsing/answer equivalence cannot certify the candidate's entire proof.
"""
from common import *
import importlib,re,signal,concurrent.futures as cf,argparse,collections
from math_control.parser_bridge import NAME,AnswerSpec,CFG,infer_spec,normalize
extract_model=importlib.import_module(NAME+'.extraction').extract_model
compare=importlib.import_module(NAME+'.equivalence').compare
import sympy as s

class SelectionTimeout(BaseException):pass

def public_certificate(question):
 q=' '.join(question.split())
 # Full question match is essential: an embedded equation need not be the goal.
 m=re.fullmatch(r'(?:Compute|Evaluate|Simplify|Find the value of)\s*\$([^$]+)\$\s*[.?]?',q,re.I)
 if m and '='not in m[1]:
  spec=infer_spec(question);target=normalize(m[1],spec,CFG)
  if target.kind=='expression':return target,spec,{'method':'exact_public_expression','premises':m[1],'scope':'Answer equivalence for the complete matched expression-only question; not full reasoning verification.'}
 m=re.fullmatch(r'Find (?:all (?:real )?(?:solutions|roots)|the (?:real )?solutions) (?:to|of) (?:the equation )?\$([^$]+)\$\s*[.?]?',q,re.I)
 if m:
  eq=normalize(m[1],AnswerSpec(kind='equation'),CFG)
  if eq.kind!='equation':return None
  expr=eq.value.lhs-eq.value.rhs
  if len(expr.free_symbols)!=1:return None
  var=next(iter(expr.free_symbols))
  if not expr.is_polynomial(var)or s.degree(expr,var)>4:return None
  roots=s.solveset(expr,var,domain=s.S.Reals)
  if not isinstance(roots,s.FiniteSet):return None
  spec=AnswerSpec(kind='finite_set',target=str(var),all_solutions=True,unordered=True)
  target=normalize(r'\{'+','.join(s.latex(v)for v in roots)+r'\}',spec,CFG)
  return target,spec,{'method':'exact_full_real_polynomial_root_set','premises':m[1],'degree':int(s.degree(expr,var)),'derived_solution_set':str(roots),'scope':'All real roots of a fully matched polynomial equation question; no arbitrary proof verification.'}
 return None

def choose(question,candidates):
 allowed={'job_id','candidate','response_hash','content','reasoning','finish_reason','syntactic_complete'}
 for c in candidates:
  if set(c)!=allowed:raise ValueError('Candidate carries forbidden/non-public fields')
 candidates=sorted(candidates,key=lambda x:x['candidate']);spec=infer_spec(question);parsed={};diagnostics=[];groups=[]
 try:certificate=public_certificate(question)
 except Exception:certificate=None
 for c in candidates:
  d={'job_id':c['job_id'],'candidate':c['candidate'],'source_response_hash':c['response_hash'],'syntactic_complete':c['syntactic_complete'],'proof_validity':'not_established_by_answer_parser','verification_status':'insufficient_evidence','verification_evidence':None}
  if not c['syntactic_complete']or c['finish_reason']!='stop':d.update(parse_status='incomplete',answer=None);diagnostics.append(d);continue
  extracted=extract_model(c['content'],c['finish_reason'],spec);d['answer']=extracted.selected
  try:
   if spec.uncertain:raise ValueError('Uncertain answer specification')
   obj=normalize(extracted.selected,spec,CFG);parsed[c['candidate']]=obj;d.update(parse_status='parsed',normalized=obj.to_dict())
   placed=False
   for g in groups:
    same,method,evidence=compare(obj,parsed[g[0]],spec)
    if same is True:g.append(c['candidate']);placed=True;d['equivalence_evidence']={'to_candidate':g[0],'method':method,'evidence':evidence};break
   if not placed:groups.append([c['candidate']])
   if certificate:
    target,certspec,proof=certificate
    actual=normalize(extracted.selected,certspec,CFG);ok,method,evidence=compare(actual,target,certspec)
    d.update(verification_status='certified_answer'if ok is True else 'refuted_answer'if ok is False else 'insufficient_evidence',verification_evidence={'certificate':proof,'comparison':method,'evidence':evidence})
  except Exception as ex:d.update(parse_status='unsupported',parse_reason=type(ex).__name__)
  diagnostics.append(d)
 def vote(eligible):
  gs=[[k for k in g if k in eligible]for g in groups];gs=[g for g in gs if g]
  if gs:return min(gs,key=lambda g:(-len(g),min(g)))[0]
  complete=[c['candidate']for c in candidates if c['syntactic_complete']and c['candidate']in eligible]
  return min(complete or eligible or [candidates[0]['candidate']])
 allks=[c['candidate']for c in candidates];majority=vote(allks)
 certified=[d['candidate']for d in diagnostics if d['verification_status']=='certified_answer']
 nonrefuted=[d['candidate']for d in diagnostics if d['verification_status']!='refuted_answer']
 verified=vote(certified or nonrefuted)
 tags={c['candidate']:sorted(set(re.findall(r'\b(?:modulo|congruence|remainder|factor|roots|quadratic|binomial|inclusion.exclusion|generating function|recurrence|symmetry|trigonometric|cosine|sine|substitution|casework|combinations|permutations)\b',c['reasoning']+' '+c['content'],re.I)))for c in candidates}
 return {'selections':{'first':candidates[0]['candidate'],'majority':majority,'verification':verified},'equivalence_groups':groups,'candidate_diagnostics':diagnostics,'certificate_applicable':certificate is not None,'verification_policy':'Certified answers first; otherwise exclude publicly refuted answers and apply typed majority; tie earliest. No certificate means no claimed verification.','structure_tags':tags,'structure_measure':'Exploratory lexical method tags only; different tags do not establish mathematically independent strategies.','gold_access':False}

def work(item):
 task,candidates=item
 def alarm(*a):raise SelectionTimeout()
 signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,15)
 try:result=choose(task['problem'],candidates)
 except SelectionTimeout:
  first=min(c['candidate']for c in candidates);result={'selections':dict(first=first,majority=first,verification=first),'equivalence_groups':[],'candidate_diagnostics':[],'certificate_applicable':False,'selection_status':'public_symbolic_timeout_first_fallback','gold_access':False}
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 return {'task_id':task['task_id'],'subject':task['subject'],'k':len(candidates),'selected_at':now(),'response_hashes':{c['job_id']:c['response_hash']for c in candidates},**result}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('k',type=int,choices=[4,8]);k=ap.parse_args().k
 for stage in ['validation1','validation4']+(['validation8']if k==8 else []):
  seal=read(OUT/'checkpoints'/f'{stage}_SEALED.json')
  for p,h in seal['files'].items():assert sha(OUT/p)==h
 path=OUT/f'selection_public_k{k}.jsonl'
 if path.exists():print('Sealed public selection reused');return
 tasks=[t for t in jl(OUT/'data/public_tasks.jsonl')if t['split']=='validation'];jobs=[]
 for t in tasks:
  cs=[]
  for n in range(1,k+1):
   r=read(OUT/'raw'/f"{t['task_id']}__c{n}.json");m=r['response']['choices'][0]['message']
   cs.append({'job_id':r['job_id'],'candidate':n,'response_hash':r['response_hash'],'content':m.get('content')or '','reasoning':m.get('reasoning_content')or '','finish_reason':r['finish_reason'],'syntactic_complete':not r['completion']['retry_required']})
  jobs.append((t,cs))
 with cf.ProcessPoolExecutor(max_workers=12)as pool:results=list(pool.map(work,jobs))
 lines(path,results);save(f'checkpoints/selection_k{k}_SEALED.json',{'at':now(),'path':str(path.relative_to(OUT)),'sha256':sha(path),'code_sha256':sha(Path(__file__)),'new_candidate_grading_not_started':not(OUT/f'grading/validation{k}.jsonl').exists(),'gold_access':False,'local_workers':12})
 print({'selected':len(results),'k':k,'certificate_tasks':sum(r['certificate_applicable']for r in results)})
if __name__=='__main__':main()
