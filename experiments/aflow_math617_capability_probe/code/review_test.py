"""Response-bound posthoc mathematical review, NEVER imported by generation/selection.

This is an audit transcription, not a replacement scorer. Ambiguous contracts remain
unresolved even when the output agrees with an intended/reference interpretation.
"""
from common import *

PROOFS={
'math_test_prealgebra_66':'Previously reviewed identical response reused. 100*0.05*(60-48)=60 cents. Explicit cents suffix is the requested unit, not a wrong mathematical object.',
'math_test_prealgebra_594':'Three successive multiplications give 2*(2/3)^3=16/27 gallons. The submitted fraction and unit are correct; trailing gallons prose is not parsed.',
'math_test_prealgebra_72':'12<sqrt(30)+sqrt(50)<13. An exact upper bound is sqrt(30)<11/2 and sqrt(50)<15/2, and a strict lower bound is sqrt(30)>5 and sqrt(50)>7. Submitted 12 and 13 follows the requested format; the prose conjunction is unsupported.',
'math_test_prealgebra_119':'Trapezoid area=(x+2x)*x/2=3x^2/2 for positive geometric length x. V3 answer contract is uncertain, while the derivation and requested expression are correct.',
'math_test_counting_probability_141':'Under the usual independent-trial model used by the reference, success before try6 is 1-(3/4)^5=781/1024. The candidate includes this exact fraction plus consistent approximate decimal/percentage; redundant prose triggers Unknown.',
'math_test_precalculus_77':'Unit vector along (-5,12) is (-5/13,12/13); it has norm1, slope -12/5 and points toward x<=7. Optional matrix row-spacing [2pt] is presentation only, misread by frozen V3.',
'math_test_precalculus_56':'Reflect a=(-2,5) in span b=(1,3): 2*(13/10)*b-a=(23/5,14/5). Intersect its positive ray with a+t(b-a): t=13/8, giving c=(23/8,7/4). Optional matrix row spacing [2mm] causes the false incorrect.',
'math_test_precalculus_418':'Distances to the two planes have denominators7 and13. The positive signed bisector is 13*(3x-6y+2z+5)-7*(4x-12y+3z-3)=11x+6y+5z+86. It vanishes at (-5,-1,-5), has positive first coefficient and coefficient gcd1. Final equation is correct; equation contract unsupported.',
'math_test_precalculus_300':'Product-to-sum telescopes the original left side into cos(theta)-cos(15theta), including theta=0 without division. Thus cos(15theta)=1/2 on [0,360deg], giving theta=4deg or20deg. The model initially divides by sin(theta); checking theta=0 directly excludes it, so the submitted set remains complete. V3 does not support degree notation.',
'math_test_number_theory_75':'Binary 0.0011_2=2^-3+2^-4=3/16. Both radix-point and base annotation are correct; the parser does not support this binary fractional contract.',
'math_test_precalculus_437':'Orthogonal projection matrix onto v=(1,7) is vv^T/(v^Tv)=[[1,7],[7,49]]/50. Submitted entries are exact. Optional [4pt] row spacing is layout and causes a false incorrect.',
'math_test_prealgebra_133':'Sine law gives BC=20*sin(30deg)/sin(45deg)=10*sqrt(2) centimeters. Explicit cm matches the requested quantity; V3 incorrectly infers a conflicting unit from the public diagram/text.',
'math_test_precalculus_147':'b-a=(-16,4,32) has norm36; requested forward unit direction is (-4/9,1/9,8/9). Submitted vector is correct; optional [2pt] matrix spacing is misparsed.',
'math_test_number_theory_32':'Geometric series has first term1/2 and ratio-1/2, so sum=(1/2)/(1+1/2)=1/3. The question explicitly requests a fraction with decimal-base numerator and denominator, which the response supplies; V3 incorrectly enforces a base numeral.',
'math_test_number_theory_44':'1960 through1999 contains10 leap years; 40*365+10=14610=1 mod7. January1,1960 is therefore the day before Saturday, Friday. Word answer is correct and unsupported by V3.',
'math_test_counting_probability_48':'Under the independent-trial interpretation used by the benchmark, failure probability is (4/5)^n. At n=6,4^7=16384>5^6=15625; at n=7,4^8=65536<5^7=78125. Monotonicity proves minimum n=7. V3 inferred specification is uncertain.',
'math_test_precalculus_8':'Solving the three affine equations gives s=1,t=-1,u=-2; both parameterizations then give (1,4,3). For an intersection point, this ordered coordinate tuple and the reference column vector denote the same point. Frozen V3 enforces a false tuple/matrix type mismatch.',
'math_test_number_theory_451':'(b^4+b^3+b+1)*(b-1)+(b^3+1)=b^5+b^2, represented as100100_b for integer base b>=2. The base subscript is legitimate and unsupported by V3.',
'math_test_precalculus_196':'Let t=cos^2(x), with 0<t<1 from sec/csc existence. Exact determinant expansion equals t^2, whose attained range is the open interval(0,1). The final interval is correct; V3 misclassifies the goal as a finite set.',
}
AMBIGUOUS={
'math_test_precalculus_442':{'proof':'The question omits the inverse-cotangent principal range. With acot in(0,pi), as the model explicitly states, acot(1/x)=atan(x) for x>0 and atan(x)+pi for x<0. Thus 2|x|/(1+x^2)=1/3, giving all four submitted roots ±(3±2sqrt2). With the branch implicit in the reference, acot(1/x)=atan(x), only the two positive roots solve it. Both inverse branches exist; no unique contractual answer is specified. This is reference/semantic ambiguity, not a confirmed model constraint error.','conditional_results':{'model_explicit_acot_range_0_pi':'correct four roots','reference_implicit_signed_branch':'two extra negative roots'}},
'math_test_precalculus_469':{'proof':'There are two distinct specification issues. Under the intended recurrence for n>=0, let b=a-1; iteration is b_next=b^3-3b, conjugate on[-2,2] to angle tripling. M=3^2007; cos(M theta)=cos(theta) has M distinct theta in[0,pi], so the submitted3^2007 is correct. V3 refuses exponent2007. However the public question literally says the recurrence holds for positive integers n, excluding n=0. Then a1 is not linked to a0: for any real a0, an a1 exists with f^2006(a1)=a0 because this iterate is an odd-degree real polynomial and is surjective. Hence all real a0 are possible under the literal statement. Keep this indexing ambiguity unresolved rather than silently repairing the question.','conditional_results':{'intended_n_ge_0':'submitted3^2007 correct','literal_n_ge_1':'infinitely many possible real a0'}},
}

def main():
 if (OUT/'test1_adjudications.jsonl').exists():print('Completed manual audit reused');return
 rows=[]
 for s in jl(OUT/'grading/test1_noncorrect.jsonl'):
  tid=s['task_id'];r=read(OUT/'raw'/f"{s['source_job_id']}.json");assert r['response_hash']==s['response_hash']
  if s['status']=='prediction_incomplete':
   category='A';correct=False;visible=r['response']['choices'][0]['message'].get('content')or ''
   proof=f'Provider finish_reason=length; visible content has {len(visible)} characters and no complete final submission. No credit for partial output and no mathematical-error inference from hidden reasoning.'
  elif tid in AMBIGUOUS:category='H';correct=None;proof=AMBIGUOUS[tid]['proof']
  else:category='B';correct=True;proof=PROOFS[tid]
  rows.append({'task_id':tid,'job_id':s['source_job_id'],'response_hash':s['response_hash'],'split':'test','candidate':1,'v3_status':s['status'],'category':category,'mathematical_correct':correct,'complete_math_error':False,'proof':proof,'conditional_results':AMBIGUOUS.get(tid,{}).get('conditional_results'),'source':'Manual post-generation mathematical review; not used by generation, selection or any gold-triggered retry','audited_at':now()})
 assert len(rows)==26
 lines('test1_adjudications.jsonl',rows);save('evidence/ambiguous_reference_cases.json',AMBIGUOUS)
 print({'reviewed':len(rows),'corrected_evaluation_cases':sum(r['category']=='B'for r in rows),'ambiguous':sum(r['category']=='H'for r in rows),'incomplete':sum(r['category']=='A'for r in rows)})
if __name__=='__main__':main()
