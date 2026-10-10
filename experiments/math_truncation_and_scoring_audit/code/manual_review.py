"""Independent exact arithmetic checks supporting the two remaining diagnoses.
This is offline reporting only; it never changes grades or routes requests.
"""
from prepare import ROOT,OUT,read,sha
from flowevo_bot.common import write_json
from sympy import symbols,Rational,solve,simplify,pi,factor,diff
import json,re

def main():
 x,y,k=symbols('x y k',real=True)
 solutions=solve([y-x*x-k,x-y*y-k,4*x*y-1],[x,y,k],dict=True)
 assert {r[k] for r in solutions}=={Rational(1,4),Rational(-3,4)}
 validations=[]
 for r in solutions:
  eqs=[simplify((y-x*x-k).subs(r)),simplify((x-y*y-k).subs(r)),simplify((2*x-1/(2*y)).subs(r))]
  assert eqs==[0,0,0]
  validations.append({'k':str(r[k]),'point':[str(r[x]),str(r[y])],'first_slope':str(2*r[x]),'second_slope':str(1/(2*r[y])),'equation_and_slope_residuals':[str(v) for v in eqs],'intersection_quartic_factorization':str(factor((x*x+r[k])**2+r[k]-x))})
 theta_sin=symbols('s',real=True)
 gs=solve(pi*(3/pi)**2*(6*theta_sin)-6,theta_sin)
 assert gs==[pi/9]
 items=[]
 for tid in ('math_test_geometry_66','math_test_intermediate_algebra_253'):
  r=read(OUT/'raw'/f'{tid}_16384.json');c=r['response']['choices'][0];t=c['message'].get('reasoning_content','')
  base={'task_id':tid,'selected_budget':16384,'finish_reason':c['finish_reason'],'visible_content_chars':len(c['message'].get('content') or ''),'reasoning_tokens':r['reasoning_tokens'],'reasoning_chars':len(t),'raw_evidence':'raw/'+tid+'_16384.json','raw_sha256':sha(OUT/'raw'/f'{tid}_16384.json'),'classification':'still_truncated','reliable_complete_math_error':False,'scoring_override':False,'review_method':'assistant inspection plus independent exact SymPy calculations; not a second human adjudicator'}
  assert base['visible_content_chars']==0 and base['reasoning_tokens']==16384
  if tid.endswith('geometry_66'):
   snippet="Thus sin = π/9.";pos=t.find(snippet)
   base.update(mechanism='Repeated reconsideration of circumference, seam/helix and height despite obtaining the intended numerical result; final-answer emission failed.',independent_derivation='Unjoined rhombus sides form rims of circumference6; r=3/pi; height=6 sin(theta); volume=(54/pi) sin(theta)=6 => sin(theta)=pi/9.',exact_sympy_solution=str(gs[0]),evidence_excerpt=snippet,evidence_character_offset=pos,pi_over_nine_mentions=len(re.findall(r'π/9|\\frac\{\\pi\}\{9\}',t)),unknowns='Cannot infer whether a different sample, compressed reasoning or explicit completion would finish. Hidden intermediate values do not qualify as a submitted final answer.')
  else:
   snippet='For a=-1/2: k=-1/2 - 1/4=-3/4.';pos=t.find(snippet)
   base.update(mechanism='Repeated deliberation over local common-tangent definition versus unique non-crossing contact expected by the reference; no final submission.',independent_derivation='Intersection implies (x-y)(x+y+1)=0. Equal tangent slopes imply4xy=1. Exact system gives k=1/4 at(1/2,1/2), and k=-3/4 at(-1/2,-1/2). The latter shares tangent y=-x-1, with cubic intersection multiplicity, and another transverse intersection at(3/2,3/2).',sympy_checks=validations,reference_issue='Reference assumes the common tangent must be y=x and lists only1/4. Under local differential tangency -3/4 is also valid; uniqueness/no-crossing interpretation singles out1/4. Wording does not explicitly impose it.',evidence_excerpt=snippet,evidence_character_offset=pos,unknowns='Semantic ambiguity is independently confirmed under the stated interpretation. Do not claim a submitted alternative answer was unfairly marked wrong: visible final content is empty. Future grading should adjudicate task wording first.')
  assert pos>=0
  items.append(base)
 write_json(OUT/'evidence/manual_math_review.json',{'items':items,'reliable_complete_math_errors':0,'new_reference_ambiguity_flags':1,'score_changes_from_this_review':0})
 (OUT/'remaining_true_failures.jsonl').write_text('')
 print(json.dumps({'tangent_checks':validations,'cylinder_answer':str(gs[0]),'true_failures':0,'ambiguity_flags':1},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
