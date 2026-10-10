"""Post-hoc case adjudications; never imported by the frozen solver or scorers.
These ID-indexed notes are an audit ledger, NOT a new evaluator or corrected gold set.
"""
from common import *
import csv,collections,shutil,math
import sympy as s
from completion import balanced
import re

# Every mathematical check is offline and independent of the online budget decision.
def exact_checks():
 x,k,z=s.symbols('x k z',real=True)
 checks={}
 def check(tid,ok):
  assert bool(ok),tid
  checks['math_test_'+tid]=True
 check('geometry_200',32**2+24**2==40**2 and 96**2+40**2==104**2 and (32*24+96*40)//2==2304)
 check('geometry_352',round(math.sqrt(8**2+10**2))==13)
 eq=((x/(x+1))**2+11)/((x/(x+1))**2+1)-2
 check('intermediate_algebra_409',set(s.solve(eq,x))=={s.Rational(-3,2),s.Rational(-3,4)})
 check('intermediate_algebra_423',s.expand((-3*k)**2-4*k*(4*k+7))==-7*k**2-28*k and (4*k+7).subs(k,0)==7)
 check('intermediate_algebra_478',s.cancel(3/(x+1)-1/(x-2)-(2*x-7)/((x+1)*(x-2)))==0)
 a,b,c,d=s.symbols('a b c d');u=a*b+c*d;v=a*c+b*d;w=a*d+b*c
 e1=a+b+c+d;e2=a*b+a*c+a*d+b*c+b*d+c*d;e3=a*b*c+a*b*d+a*c*d+b*c*d;e4=a*b*c*d
 check('intermediate_algebra_482',s.expand(u*v*w-(e1**2*e4+e3**2-4*e2*e4))==0 and s.expand((z+2)*(z*z-2*z-4))==z**3-8*z-8)
 check('intermediate_algebra_516',all(1988*r*r+bb*r+8891==0 and 8891*r*r+bb*r+1988==0 for r,bb in [(1,-10879),(-1,10879)]) and 1988+8891==10879)
 eq=(2*x*x-3*x)/(x*x-x)+5*x-11-(3*x*x+5*x+2)/(x*x-1)
 check('intermediate_algebra_563',set(s.solve(eq,x))=={s.Rational(2,5),s.Integer(3)})
 check('intermediate_algebra_700',sum([3,4,6,3,7])==23 and 7<2009%23<13)
 eq=(x+1)*(x-3)/(5*(x+2)*(x-4))+(x+3)*(x-5)/(9*(x+4)*(x-6))-2*(x+5)*(x-7)/(13*(x+6)*(x-8))-s.Rational(92,585)
 check('intermediate_algebra_756',set(s.solve(eq,x))=={1-s.sqrt(19),1+s.sqrt(19)})
 check('intermediate_algebra_813',s.simplify(e1*(-e2)+e1*e2)==0) # h(-x)=f(x)(-g(x))
 check('number_theory_158',int('101',6)-int('32',6)==int('25',6))
 check('number_theory_295','MATH'[(2009-1)%4]=='M')
 valid=[n for n in range(1,22) if math.prod(range(n,n+4))>1000 and math.prod(range(n,n+4))%10==4]
 check('number_theory_491',valid[:4]==[6,11,16,21] and sum(range(valid[0],valid[0]+4))==30 and sum(valid[:4])==54)
 check('prealgebra_372',(40+50)/2==45)
 check('prealgebra_551',3*6**2-2*3**2==90)
 check('prealgebra_598',s.Rational(20*12,60)==4)
 check('prealgebra_625',s.Rational(271,200)<=s.Rational(15,11)<s.Rational(273,200))
 check('prealgebra_841',s.Rational(4)/s.Rational(1,2)==8)
 options=[s.Rational(v) for v in ['67.332','67.473','67.526','67.445','67.346']]
 check('prealgebra_853',min(range(5),key=lambda i:abs(options[i]-s.Rational('67.4')))==3)
 check('precalculus_380',2**2+6**2+3**2==49 and [8*v for v in [2,6,3]]==[16,48,24])
 check('geometry_191',180-132==48)
 check('prealgebra_385',s.Rational(1,4)/(1+s.Rational(1,4))*100==20)
 check('algebra_1161',max([1,3,5,6])==6) # inverse relation range; function ambiguity noted below
 check('geometry_56',s.Rational(135,360)*s.pi*4**2+s.Rational(4,2)==6*s.pi+2)
 check('intermediate_algebra_494',2*sum(range(1,2006))==4022030)
 return checks

# (category, mathematical final-answer verdict, reproducible explanation)
CASES={
'algebra_1161':('still_truncated',None,'16384 时仍无正文最终答案。按逆关系解释，值域等于原函数定义域，最大值6；但图中 f(1)=f(5)=2，不是单射，严格逆函数未定义。隐藏推理反复讨论此歧义；不能把隐藏推理中的候选数字当交付答案。'),
'geometry_200':('scorer_coverage_failure',True,'YW=sqrt(32²+24²)=40，96²+40²=104²；面积=32×24/2+96×40/2=2304。square units 单位格式未被评分器接受。'),
'geometry_352':('scorer_coverage_failure',True,'两方向成直角，距离sqrt(8²+10²)=sqrt164，四舍五入13。参考答案的 text{13} 包装导致 unknown。'),
'geometry_56':('still_truncated',None,'区域为圆心(4,0)、半径4、圆心角135°的扇形加顶点(0,0),(4,0),(3,-1)三角形，面积6π+2。隐藏推理已出现此值但仍反复核对；16384耗尽时正文为空。'),
'intermediate_algebra_409':('label_extraction_incomplete',True,'令u=(x/(x+1))²，(u+11)/(u+1)=2⇒u=9，解为-3/2,-3/4，均满足原式且x≠-1。原参考解分别boxed两个答案，last-box提取只保留-3/4；模型两解完整。'),
'intermediate_algebra_423':('scorer_coverage_failure',True,'判别式=-7k(k+4)≥0⇒-4≤k≤0；k=0时原式为7=0，排除0。因此[-4,0)与模型不等式相同，评分器类型比较保守拒判。'),
'intermediate_algebra_478':('scorer_coverage_failure',True,'系数比较A+B=4,-A+2B=5⇒A=1,B=3。3/(x+1)-1/(x-2)=(2x-7)/((x+1)(x-2))，两表达式定义域相同。displaystyle 包装触发保守的定义域分支。'),
'intermediate_algebra_482':('scorer_coverage_failure',True,'Vieta推得三目标值的三次式z³-8z-8=(z+2)(z²-2z-4)。集合{-2,1-sqrt5,1+sqrt5}等于参考的{1±sqrt5,-2}；后者解析成嵌套集合造成false。模型uvw对称恒等式已用SymPy验证。'),
'intermediate_algebra_494':('still_truncated',None,'每区间[n,n+1)有n个高度1/2的V形段。x≤2006时每V形与2^(x-2007)相交两次，最后右端点2006仅计一次；x>2006指数超过1/2不再相交。总数2Σ(n=1..2005)n=4022030。隐藏推理已有该值但输出未结束；不计正确。'),
'intermediate_algebra_516':('label_extraction_incomplete',True,'两方程相减⇒6903(x²-1)=0，共同根±1，分别得b=-10879,+10879；代回两式均为0。参考解有两个boxed，last-box仅留下正值。'),
'intermediate_algebra_563':('label_extraction_incomplete',True,'原式要求x≠-1,0,1；通分化简为(x-3)(5x-2)=0，两解3和2/5都合法。参考解多个boxed被last-box截成2/5。'),
'intermediate_algebra_700':('scorer_coverage_failure',True,'周长23，2009=23×87+8，8落在CD的接触区间(7,13)。题目明确要求输入CD，参考overline{CD}是线段标记；评分器按代数表达式误判。两评分器都false，所以不能只审查评分分歧。'),
'intermediate_algebra_756':('scorer_coverage_failure',True,'令y=x²-2x，原式化为1/(y-8)+1/(y-24)=2/(y-48)，解y=18，故x=1±sqrt19。均不在原分母零点中。展开两根与±写法等价，解析结构类型不一致导致unknown。'),
'intermediate_algebra_813':('scorer_coverage_failure',True,'h(-x)=f(-x)g(-x)=f(x)(-g(x))=-h(x)，故odd正确。参考text{odd}未支持。'),
'number_theory_158':('scorer_coverage_failure',True,'101_6=37，32_6=20，差17=25_6。模型25后接内联数学下标的格式未被解析。'),
'number_theory_295':('scorer_coverage_failure',True,'2009 mod4=1，循环MATH首字母M。参考text{M}未支持。'),
'number_theory_491':('confirmed_math_error',False,'模型正确找到最小起点n=6及积3024，却在“The four smallest such starting integers”处将目标偷换为四个合法起点6,11,16,21，求和54。题目要求最小四个连续整数6,7,8,9之和30。首轮4096截断，8192给出完整但错误的54；按规则没有继续升至16384。'),
'prealgebra_372':('scorer_coverage_failure',True,'总路程40+50=90英里，总时间2小时，均速45 mph。复合速度单位未解析。'),
'prealgebra_551':('scorer_coverage_failure',True,'三个6×6正方形扣除两个3×3重叠区域，3×36-2×9=90。8192和E4096均输出90；参考text中的换行单位造成unknown。'),
'prealgebra_598':('scorer_coverage_failure',True,'20 ft/min×12 in/ft÷60 s/min=4 in/s。单位规范化残留inches per。'),
'prealgebra_625':('scorer_coverage_failure',True,'3/2.20=15/11≈1.3636，依题目四舍五入至1.36kg。grams子串被移除后残留kilo。'),
'prealgebra_841':('scorer_coverage_failure',True,'4/0.5=8km；meters子串被移除后残留kilo。'),
'prealgebra_853':('scorer_coverage_failure',True,'五选项距67.4的差为.068,.073,.126,.045,.054，最小对应D。题目A.格式未被只认(A)的选项处理覆盖。'),
'precalculus_380':('scorer_coverage_failure',True,'b·b=4+36+9=49，proj_b(a)=8b/49=(16,48,24)/49，与参考相同。矩阵前的displaystyle阻止专用解析。'),
'geometry_191':('confirmed_scoring_fix_gain',True,'锐角三角形垂心夹角AHB=180°-C，因此C=48°。修复器正确识别Unicode度符号与LaTeX度符号等价，无假阳性。'),
'prealgebra_385':('confirmed_scoring_fix_gain',True,'成人A，成年女性A/2，其中一半各有一孩，儿童A/4，总人口5A/4，儿童占1/5=20%。百分号处理修复有效，无假阳性。'),
}

def main():
 checks=exact_checks();calls=jl(OUT/'api_calls.jsonl');byjob={r['job_id']:r for r in calls}
 fixed={r['job_id']:r for r in jl(OUT/'fixed_scoring_results.jsonl')};legacy={r['job_id']:r for r in jl(OUT/'legacy_scoring_results.jsonl')}
 labels={r['task_id']:r for r in jl(OUT/'data/offline_labels.jsonl')}
 source=OUT/'evidence/remaining_failures_automatic.jsonl'
 if not source.exists():shutil.copy2(OUT/'remaining_failures.jsonl',source)
 dis_source=OUT/'evidence/scoring_disagreements_automatic.csv'
 if not dis_source.exists():shutil.copy2(OUT/'scoring_disagreements.csv',dis_source)
 failures=jl(source);dis=list(csv.DictReader(dis_source.open()))
 jobs={r['job_id'] for r in dis}|{Path(r['raw_evidence']).stem for r in failures}
 reviews=[]
 for job in sorted(jobs):
  call=byjob[job];tid=call['task_id'];category,verdict,proof=CASES[tid.removeprefix('math_test_')]
  assert checks[tid]
  assert (call['finish_reason']=='length')==(verdict is None)
  reviews.append({'task_id':tid,'job_id':job,'stage':call['stage'],'category':category,'mathematically_correct_final_answer':verdict,'review_evidence':proof,'exact_check_passed':True,'legacy_grade':legacy[job]['grade'],'fixed_grade':fixed[job]['grade'],'gold_answer_frozen':labels[tid]['gold_answer'],'reference_solution':labels[tid]['reference_solution'],'raw_evidence':f'raw/{job}.json','response_hash':call['response_hash'],'original_final_text':call['response']['choices'][0]['message'].get('content') or '', 'reference_ambiguity':tid=='math_test_algebra_1161','label_incomplete':category=='label_extraction_incomplete','reviewer':'Codex assistant inspection plus exact arithmetic/SymPy; no independent human adjudication','scope':'post-hoc audit only; frozen evaluator, outputs, labels and official scores unchanged'})
 rm={r['job_id']:r for r in reviews};lines('manual_audit_results.jsonl',reviews)
 for r in failures:
  review=rm[Path(r['raw_evidence']).stem]
  r.update({'category_after_manual_review':review['category'],'mathematical_error_confirmed':review['mathematically_correct_final_answer'] is False,'manual_review_required':False,'manual_review':review})
 lines('remaining_failures.jsonl',failures)
 lines('remaining_true_math_errors.jsonl',[r for r in failures if r['mathematical_error_confirmed']])
 for r in dis:
  a=rm[r['job_id']];r.update({'manual_review_required':False,'ambiguous':a['reference_ambiguity'],'manual_mathematically_correct':a['mathematically_correct_final_answer'],'manual_category':a['category'],'mathematical_review_evidence':a['review_evidence'],'label_incomplete':a['label_incomplete'],'response_hash':a['response_hash']})
 with (OUT/'scoring_disagreements.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(dis[0]));w.writeheader();w.writerows(dis)
 label_cases=[]
 for tid,(_,verdict,note) in CASES.items():
  if CASES[tid][0]=='label_extraction_incomplete':
   item=labels['math_test_'+tid];boxes=[balanced(item['reference_solution'],m.end())[0] for m in re.finditer(r'\\boxed\s*\{',item['reference_solution'])]
   label_cases.append({'task_id':item['task_id'],'frozen_gold_answer':item['gold_answer'],'all_reference_boxes':boxes,'proof':note,'policy':'Do not replace primary labels after outcomes; document full solution set separately.'})
 save('label_integrity_audit.json',{'extraction_policy':'frozen historical last-box extract_answer','cases':label_cases,'future_action':'Validate complete reference solution sets on independent development data before next held-out evaluation.'})
 def adjudicated(job):
  return (rm[job]['mathematically_correct_final_answer'] if job in rm else fixed[job]['grade']['correct']) is True
 totals={name:sum(adjudicated(r['job_id']) for r in jl(OUT/file)) for name,file in [('base','first_pass_results.jsonl'),('adaptive','adaptive_results.jsonl'),('E','same_budget_retry.jsonl')]}
 totals['upgrade8192']=sum(adjudicated(r['job_id']) for r in calls if r['stage']=='upgrade8192')
 assert totals=={'base':467,'adaptive':496,'E':10,'upgrade8192':21},totals
 counts=dict(collections.Counter(r['category_after_manual_review'] for r in failures))
 save('manual_audit_summary.json',{'reviewed_unique_tasks':len({r['task_id'] for r in reviews}),'reviewed_unique_responses':len(reviews),'all_disagreement_responses_reviewed':len(dis),'remaining_primary_nontrue':len(failures),'remaining_categories':counts,'sensitivity_only':totals,'sensitivity_adaptive_gain':totals['adaptive']-totals['base'],'sensitivity_remaining_truncated':3,'sensitivity_confirmed_complete_math_errors':1,'primary_scores_unchanged':True,'caution':'Post-hoc review of disagreements and all D nontrue; other automatically-true answers were not independently exhaustively proved. Sensitivity counts are not a new frozen-evaluator score, and not independent human ground truth.','evaluators_or_labels_changed':False})
 print(json.dumps({'reviews':len(reviews),'counts':counts,'sensitivity':totals},ensure_ascii=False))
if __name__=='__main__':main()
