import pytest
from flowevo_bot.v2.evaluator import grade, extract, seal, score_sealed

def g(pred, gold, question='', truncated=False):
    return grade(dict(task_id='unit', solution='The answer is '+pred, gold_answer=gold, question=question, truncated=truncated))

@pytest.mark.parametrize('pred,gold,question,expected', [
    (r'\frac{1}{2}', '0.5', '', True),
    ('-2', '2', '', False),
    (r'\sqrt{8}', r'2\sqrt{2}', '', True),
    ('18 square centimeters', '18', 'What is the area in square centimeters?', True),
    (r'\(18\) square centimeters', '18', 'Area in square centimeters?', True),
    ('18 elephants', '18', '', None),
    ('(A)', r'\text{(A)}', 'Options (A) Line (B) Circle', True),
    ('(A) Line', 'A', 'Evaluate variable A.', None),
    (r'\{1,2\}', r'\{2,1\}', 'Find the set of roots.', True),
    ('(1,2)', '(2,1)', 'Find the ordered pair.', False),
    ('(1,2)', '[1,2)', 'Give the solution interval.', False),
    ('1,2', '2,1', 'Find all solutions.', True),
    ('garbage 18', '18', '', None),
    (r'\frac{1}{', '1', '', None),
])
def test_equivalence(pred,gold,question,expected):
    assert g(pred,gold,question)['rechecked_correct'] is expected

def test_nested_box_last_marker():
    assert extract(r'\boxed{\frac{1}{\sqrt{2}}}')[0] == r'\frac{1}{\sqrt{2}}'
    assert extract('The answer is (A) Line.\nThe answer is (A).')[0] == '(A)'
    assert extract(r'\boxed{1} then \boxed{\frac{2}{')[0] is None

def test_truncated_not_accepted():
    assert g('2', '2', truncated=True)['rechecked_correct'] is False

def test_labels_unopened_until_every_seal(tmp_path):
    valid=seal(dict(task_id='unit',solution='The answer is 2.'))
    bad={**valid,'solution':'tampered'}
    with pytest.raises(ValueError, match='Unsealed'):
        score_sealed([valid,bad],tmp_path/'MUST_NOT_OPEN',{},'unused',workers=1)
