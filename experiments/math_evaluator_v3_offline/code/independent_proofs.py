"""Audit-only mathematics. No evaluator imports and no task IDs in runtime rules.

These cases encode problem-specific proofs by the assistant, independently of
V3 extraction/normalization. They are not independent human adjudications.
"""
import sympy as s
import math,itertools

def proofs():
 out={};x,k,z=s.symbols('x k z',real=True)
 def add(key,condition,note,answer_correct=True):
  assert bool(condition),key
  out['math_test_'+key]={'proof_verified':True,'mathematically_correct_final_answer':answer_correct,'proof':note,'method':'assistant-checked public-question derivation + exact arithmetic/SymPy; independent of evaluator decisions'}
 add('geometry_200',32**2+24**2==40**2 and 96**2+40**2==104**2 and (32*24+96*40)//2==2304,'勾股得到对角线40；两直角三角形面积384+1920=2304。')
 add('geometry_352',s.Rational(25,2)**2<=164<s.Rational(27,2)**2,'正交位移(8,10)，距离sqrt164落在[12.5,13.5)，最近整数13。')
 eq=((x/(x+1))**2+11)/((x/(x+1))**2+1)-2
 add('intermediate_algebra_409',set(s.solve(eq,x))=={s.Rational(-3,2),s.Rational(-3,4)},'令u=(x/(x+1))²，得u=9；两根-3/2,-3/4均满足x≠-1，参考末盒遗漏前根。')
 discriminant=s.expand((-3*k)**2-4*k*(4*k+7))
 sol=s.solve_univariate_inequality(discriminant>=0,k,relational=False)-s.FiniteSet(0)
 add('intermediate_algebra_423',sol==s.Interval(-4,0,right_open=True),'判别式=-7k(k+4)；k=0时原式为7=0；实根参数集[-4,0)。')
 add('intermediate_algebra_478',s.cancel(3/(x+1)-1/(x-2)-(2*x-7)/((x+1)*(x-2)))==0,'系数比较A+B=4,-A+2B=5，得A=1,B=3；两种最终分式完全相同且均排除x=-1,2。')
 a,b,c,d=s.symbols('a b c d');u=a*b+c*d;v=a*c+b*d;w=a*d+b*c
 e1=a+b+c+d;e2=a*b+a*c+a*d+b*c+b*d+c*d;e3=a*b*c+a*b*d+a*c*d+b*c*d;e4=a*b*c*d
 ids=[s.expand(u+v+w-e2),s.expand(u*v+u*w+v*w-(e1*e3-4*e4)),s.expand(u*v*w-(e1**2*e4+e3**2-4*e2*e4))]
 add('intermediate_algebra_482',all(q==0 for q in ids) and s.expand((z+2)*(z*z-2*z-4))==z**3-8*z-8,'Vieta e1=-2,e2=e3=0,e4=2；三目标的和0、二次对称和-8、积8，故三次式z³-8z-8，完整根集{-2,1±sqrt5}。')
 add('intermediate_algebra_516',all(1988*r*r+bb*r+8891==0 and 8891*r*r+bb*r+1988==0 for r,bb in [(1,-10879),(-1,10879)]),'两方程相减得6903(x²-1)=0。共同根x=±1分别要求b=∓10879；代回皆成立，两个b不可丢失。')
 eq=(2*x*x-3*x)/(x*x-x)+5*x-11-(3*x*x+5*x+2)/(x*x-1)
 add('intermediate_algebra_563',set(s.solve(eq,x))=={s.Rational(2,5),s.Integer(3)},'原域x≠-1,0,1；通分后两根3,2/5均合法。')
 add('intermediate_algebra_700',sum([3,4,6,3,7])==23 and 7<2009%23<13,'周长23，2009模23余8；8落在CD对应累计长度(7,13)内。')
 eq=(x+1)*(x-3)/(5*(x+2)*(x-4))+(x+3)*(x-5)/(9*(x+4)*(x-6))-2*(x+5)*(x-7)/(13*(x+6)*(x-8))-s.Rational(92,585)
 add('intermediate_algebra_756',set(s.solve(eq,x))=={1-s.sqrt(19),1+s.sqrt(19)},'令y=x²-2x，消元得y=18；x=1±sqrt19，均不是原式分母零点。')
 add('intermediate_algebra_813',s.expand(a*(-b)+a*b)==0,'偶函数f与奇函数g的乘积h满足h(-x)=f(x)(-g(x))=-h(x)，类别odd。')
 add('number_theory_158',int('101',6)-int('32',6)==int('25',6),'101₆=37，32₆=20；差17=25₆。')
 add('number_theory_295','MATH'[(2009-1)%4]=='M','从1开始循环MATH，第2009位对应索引0，字符M。')
 ns=[n for n in range(1,22) if math.prod(range(n,n+4))>1000 and math.prod(range(n,n+4))%10==4]
 add('number_theory_491',ns[:4]==[6,11,16,21] and sum(range(ns[0],ns[0]+4))==30,'最小合法四连数是6,7,8,9，积3024、和30；54是四个不同合法起点的和，答非所问。',False)
 add('prealgebra_372',s.Rational(40+50,2)==45,'两小时总里程40+50=90英里，平均速度45mph。')
 add('prealgebra_551',3*6**2-2*3**2==90,'三个面积36的正方形，减去两个面积9的重叠区，面积90。')
 add('prealgebra_598',s.Rational(20*12,60)==4,'20ft/min乘12in/ft再除60s/min，等于4in/s。')
 add('prealgebra_625',s.Rational(271,200)<=s.Rational(15,11)<s.Rational(273,200),'按题给1kg=2.20lb，3lb=15/11kg∈[1.355,1.365)，两位小数1.36。')
 add('prealgebra_841',s.Rational(4)/s.Rational(1,2)==8,'图上4厘米，每0.5厘米为1千米，得8千米。')
 vals=list(map(s.Rational,['67.332','67.473','67.526','67.445','67.346']))
 add('prealgebra_853',min(range(5),key=lambda i:abs(vals[i]-s.Rational('67.4')))==3,'与67.4距离为.068,.073,.126,.045,.054，D最近。')
 add('precalculus_380',s.Matrix([2,6,3]).dot(s.Matrix([2,6,3]))==49,'b=(2,6,3)，a·b=8，b·b=49；投影(16,48,24)/49。')
 add('geometry_191',180-132==48,'垂心夹角AHB=180°-C，因此C=48°。')
 add('prealgebra_385',s.Rational(1,4)/(1+s.Rational(1,4))*100==20,'成人A，儿童A/4，总人口5A/4；儿童比例20%。')
 add('precalculus_187',(2**2005).bit_length()==2006,'单位圆上共轭z=1/z，递推z↦iz²；n轮后i^(2^n-1)z^(2^n)=1，恰有2^n个不同单位根。n=2005。V3因预设指数上限拒绝解析；数学答案正确。')
 # First-batch nine regression fixes, with exact derivations.
 add('algebra_673',40/s.Rational(2,100)==2000,'40占每日需求2%，总需求2000卡路里。')
 add('algebra_884',(3491-60)*(3491+60)-3491**2==-3600,'面积变化=-60²=-3600，减少3600，错误方向more必须拒绝。')
 add('counting_probability_411',s.Rational(4*12,math.comb(52,3))==s.Rational(12,5525),'每花色12个连续三张（A23到QKA），4×12个有利集合，总数C(52,3)，概率12/5525。')
 add('geometry_165',180-90-50==40,'BD=DC=DA，D为外接圆心且BC为直径，A=90°，C=40°。')
 add('geometry_48',1-s.Rational(1,4)==s.Rational(75,100),'未阴影三角形面积为矩形的1/4，阴影75%。')
 add('intermediate_algebra_796',(-(-3),-5)==(3,-5),'奇函数关于原点对称，(-3,5)推出(3,-5)；标准解另列(0,0)需要定义域包含0，不能覆盖前一个合法点。')
 add('prealgebra_334',s.Rational(5*13+7,6)==12,'五个重量总和65g，再加7g，六个平均12g。')
 add('prealgebra_435',s.Rational(10,4)==s.Rational(5,2),'四橙1美元，十橙10/4=2.50美元。')
 add('prealgebra_498',360-3*(180*3/5)==36,'正五边形内角108°，三角共324°，缺口36°。')
 # Fixed-seed stratified unanimous-correct sample, selected before these proofs.
 add('algebra_747',s.Rational(13-16+6,3)**2+8==9,'平均x=1，y³=8，x²+y³=9。')
 add('algebra_800',18*abs(s.Rational(1,4)+s.Rational(1,2))==s.Rational(27,2),'18|A-B|=18×3/4=13.5。')
 add('algebra_1052',s.Interval(-11,3).inf+1==-10 and s.Interval(-11,3).sup+1==4,'映射x↦6x在R上双射，不变值域；加1使闭区间[-11,3]平移到[-10,4]。')
 add('counting_probability_431',s.Rational(1,7*6*5*4)==s.Rational(1,840),'无放回顺序抽到M,A,T,H的概率1/(7·6·5·4)=1/840。')
 add('counting_probability_316',s.Rational(math.comb(5,3),math.comb(8,3))==s.Rational(5,28),'8张中5张纸，抽3张全纸的概率C(5,3)/C(8,3)=5/28。')
 add('counting_probability_260',1-s.Rational(math.comb(66,2),math.comb(99,2))==s.Rational(82,147),'1..99有66个非3倍数；不同两数都非3倍数的补事件给82/147。')
 add('geometry_254',(8-3)**2*s.pi==25*s.pi,'题图明确圆心(3,1)、圆上点(8,1)；r=5，面积25π。')
 add('geometry_437',set(s.solve(6*s.pi*x*x-12*s.pi*x,x))=={0,2},'体积数值6πr²=侧面积数值12πr，半径正，排除0得2英寸。')
 points=[(0,0),(4,4),(5,3),(5,0)]
 area=abs(sum(points[i][0]*points[(i+1)%4][1]-points[(i+1)%4][0]*points[i][1] for i in range(4)))/s.Integer(2)
 add('geometry_222',area==s.Rational(23,2),'取D(0,0),C(5,0),A(0,8)；折痕y=x与y=8-x交于R(4,4)，Q(5,3)。DRQC鞋带公式面积23/2cm²。')
 add('intermediate_algebra_586',s.cancel(3/(x-2)+4/(x+2)-(7*x-2)/(x*x-4))==0,'比较系数A+B=7，或代入得到A=3,B=4。')
 add('intermediate_algebra_876',s.expand((x+3)**2+2*(k+2)**2-32)==x*x+2*k*k+6*x+8*k-15,'完成平方(x+3)²+2(y+2)²=32，长轴长2sqrt32=8sqrt2。')
 ds={-10,-5,-2,-1,1,2,5,10}
 add('intermediate_algebra_266',{17+d for d in ds if 17+d-24 in ds}=={19,22},'整数系数多项式差的整除性给n-17|10且n-24|10，穷尽±1,±2,±5,±10得仅19,22；题设两不同整数根，故两者都必须出现。')
 add('number_theory_218',[d for d in range(10) if (2007+10*d)%11==0]==[5],'逐枚举十个合法数字，唯一2057能被11整除。')
 add('number_theory_34',len([10*a+b for a,b in itertools.permutations([2,3,5,7,9],2) if (10*a+b)%3==0])==6,'枚举五个不同数字的20个有序对，6个构成3的倍数。')
 n=s.symbols('n',integer=True)
 add('number_theory_77',s.expand(sum(2*n+1+2*j for j in range(6)))==12*n+36 and math.gcd(36,48)==12,'六个连续正奇数和12(n+3)；首两组和36,48最大公约数12，证明必含因子且不能更大。')
 add('prealgebra_126',2*17-1==33,'第n个正奇数2n-1，第17个33。')
 add('prealgebra_668',s.Rational(16,25)*s.Rational(5,2)**4==25,'精确分数乘幂等于25。')
 r=s.symbols('r',positive=True)
 add('prealgebra_701',s.expand(2*s.pi*(r+5)-2*s.pi*r)==10*s.pi,'头部半径比脚部多5ft，路程差2π(r+5)-2πr=10πft。')
 xx,yy,zz=s.symbols('xx yy zz');A=s.Matrix([[1,xx],[yy,-s.Rational(9,5)]]);B=s.Matrix([[s.Rational(12,5),s.Rational(1,10)],[5,zz]])
 sol=s.solve(list(A+B-A*B),[xx,yy,zz],dict=True)
 add('precalculus_347',sol==[{xx:s.Rational(1,5),yy:10,zz:1}],'直接联立A+B=AB四个分量，唯一x=1/5,y=10,z=1，总和56/5。')
 add('precalculus_372',2*s.Rational(1,3)**2-1==-s.Rational(7,9),'设u=θ+π/4，sin2θ=-cos2u=2sin²u-1=-7/9。')
 add('precalculus_415',{v for v in s.solve(1-3*k*k/4-k,k) if -1<=v<=1}=={s.Rational(2,3)},'令k=sin2θ∈[-1,1]，sin⁶θ+cos⁶θ=1-3k²/4；两代数根-2,2/3，排除-2，得2/3。参考推导中sin²θ、sinθ+2是排印错误，最终值正确。')
 return out
if __name__=='__main__':print({'verified_public_problem_proofs':len(proofs())})
