import sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'FlowEvo-Recovery/src'),str(ROOT/'Flowevo-Bot/src')]
from flowevo_recovery.math_scoring_v2 import grade,extract,complete

def score(p,g,q='Compute the value.'):
 return grade({'solution':'The answer is '+p+'.','gold_answer':g,'question':q,'truncated':False})

@pytest.mark.parametrize('p,g,q',[
 (r'\boxed{\frac{\sqrt{8}}{2}}',r'\sqrt{2}','Compute the value.'),
 ('0.125',r'\frac18','Compute the value.'),
 ('x^2+2x+1','(x+1)^2','Expand the polynomial.'),
 (r'\{3,1,2\}',r'\{1,2,3\}','Find the set.'),
 ('[0,1)', '[0,1)','Find the interval.'),
 ('7 grams',r'7\text{gm}','What is the weight in grams?'),
 ('180 calories','180','How many calories are required?'),
 ('30%', '30','What percent is shaded?'),
 ('14°',r'14^\circ','What is the angle in degrees?'),
 ('1,234', '1234','Compute the value.'),
 (r'\frac{9}{2,\!345}',r'\frac{9}{2345}','Compute the fraction.'),
 ('16 square inches','16','What is the surface area of a cube of side two inches?'),
 (r'\begin{pmatrix}0&1\\2&3\end{pmatrix}',r'\begin{pmatrix}0 & 1 \\ 2 & 3\end{pmatrix}','Find the matrix.'),
 ('z=2,5','5,2','Find all values of z.'),
 ('x=1 \\text{ or } x=7','7,1','Solve for x.'),
 ('49 square units less','49','A 100 by 100 square has its length decreased by 7 and its width increased by 7. By how much does its area change?'),
 ('Mira',r'\text{Mira}','Mira and Liam compete. Who wins?'),
 ('3 feet',r'3\text{ft}','What is the length in feet?'),
] )
def test_equivalent(p,g,q):
 assert score(p,g,q)['correct'] is True

@pytest.mark.parametrize('p,g,q',[
 ('-5','5','Compute the value.'),
 ('(2,9)','(9,2)','Give an ordered pair.'),
 ('[0,1]','(0,1)','Find the interval.'),
 (r'\{1,2\}',r'\{1,2,3\}','Find the set.'),
 ('0.75','75','What percent is shaded?'),
 ('x+y','x-y','Find the polynomial.'),
 (r'\sqrt{x^2}','x','For real x, simplify.'),
 ('-49 square units less','49','A 100 by 100 square has its length decreased by 7 and its width increased by 7. By how much does its area change?'),
 (r'\begin{pmatrix}1&2\\3&4\end{pmatrix}',r'\begin{pmatrix}1&3\\2&4\end{pmatrix}','Find the matrix.'),
] )
def test_non_equivalent(p,g,q):
 assert score(p,g,q)['correct'] is not True

@pytest.mark.parametrize('p,g,q',[
 ('x/x','1','Simplify, retaining the domain.'),
 (r'\frac{x^2-1}{x-1}','x+1','Simplify, retaining the domain.'),
 ('9 kilograms','9','How many grams?'),
 ('9 perhaps, but 8 is possible','9','Compute the value.'),
 ('(2,3) with x>0','(2,3)','Give all solutions.'),
])
def test_unknown(p,g,q):assert score(p,g,q)['correct'] is None

def test_last_marker_and_nested():
 assert extract(r'Intermediate \boxed{7}. Final answer: \boxed{\frac{\sqrt{5}}{2}}')[0]==r'\frac{\sqrt{5}}{2}'
 assert extract('The answer is 7.\nFinal answer: -8.')[0]=='-8'
 assert not complete(r'Final answer: \boxed{\frac{1}{2}')
 assert not complete('Still thinking')
 assert grade({'solution':'Final answer: 3','gold_answer':'3','truncated':True})['correct'] is False

def test_symmetry_general_unseen_positive_negative():
 q='The graph passes through the point $(2,-7)$. It is an odd function. What other point must the graph pass through?'
 r=score('(-2,7)','(0,0)',q);assert r['correct'] is True and r['status']=='public_question_witness'
 assert score('(-2,-7)','(0,0)',q)['correct'] is False
 q=q.replace('odd','even')
 assert score('(-2,-7)','(99,99)',q)['correct'] is True
 assert score('(-2,7)','(99,99)',q)['correct'] is False
 q=q.replace('even','unspecified')
 assert score('(-2,-7)','(99,99)',q)['correct'] is False

def test_historical_regression_all500():
 root=Path(__file__).resolve().parents[1]
 rows=json.loads((root/'evidence/rescored_500_detailed.json').read_text())
 assert len(rows)==500
 assert all(r['correct'] is True for r in rows if r['original_correct'])
 assert sum(r['correct'] is True for r in rows)==473
 assert sum(r['status']=='truncated' for r in rows)==27


def test_direction_and_dimensions():
 q='A 40 by 40 square has its length decreased by 4 and its width increased by 4. By how much does its area change?'
 assert score('16 square units more','16',q)['correct'] is False
 assert score('16 square units less','16',q)['correct'] is True
 assert score('20 cubic inches','20','What is the surface area in square inches?')['correct'] is False
