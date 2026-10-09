import pytest
import sympy as sp
from flowevo_bot.schemas import ProblemView
from flowevo_bot.v2.features import extract
from flowevo_bot.v2.skills import Trigger,evaluate,check_nonzero,multiplication_direction,symmetry_quotient,trigger_for

def task(text,subject='intermediate_algebra'):
    return ProblemView(task_id='unit',problem=text,subject=subject)

def test_no_quadratic_prefix_false_match():
    assert extract(task(r'Solve $x^{20}+x^2=0$.'))['facts']['math:quadratic'] is False
    assert extract(task(r'Solve $x^3+x^2=1$.'))['facts']['math:quadratic'] is False
    assert extract(task(r'Solve $x^2+x=1$.'))['facts']['math:quadratic'] is True

def test_rational_without_nonzero_word():
    f=extract(task(r'Find all real $x$ with $\frac{x(x+1)}{(x-4)^2}\ge12$.'))
    assert evaluate(trigger_for('S07'),f['facts'])['value'] is True
    assert f['variable_denominators'][0]['latex']=='(x-4)^2'

def test_numeric_denominator_not_rational_macro():
    f=extract(task(r'Find foci of $\frac{x^2}{9}-\frac{y^2}{4}=1$.'))
    assert evaluate(trigger_for('S07'),f['facts'])['value'] is False

@pytest.mark.parametrize('text',[
    r'Solve $\sqrt{4x-3}+\frac{10}{\sqrt{4x-3}}=7$.',
    r'Given $\frac{x+y}{x-y}+\frac{x-y}{x+y}=1$, find a ratio.',
])
def test_parsed_substitution(text):
    f=extract(task(text))
    assert evaluate(trigger_for('S07'),f['facts'])['value'] is True
    assert f['rational_relations'][0]['substitution']

def test_or_and_unknown_not_optional():
    assert evaluate(Trigger.model_validate({'any_of':[{'feature':'a'},{'feature':'b'}]}),{'a':True,'b':False})['value'] is True
    assert evaluate(Trigger.model_validate({'all_of':[{'feature':'a'},{'feature':'b'}]}),{'a':True,'b':False})['value'] is False
    assert evaluate(Trigger.model_validate({'not':{'feature':'missing'}}),{})['value'] is None
    assert evaluate(Trigger.model_validate({'optional':{'feature':'missing'}}),{})['value'] is True
    assert evaluate(Trigger(guard='nonzero'),{})['guard_passed'] is False
    with pytest.raises(ValueError):Trigger.model_validate({'feature':'a','any_of':[]})

def test_guards():
    assert check_nonzero(sp.Integer(0)) is False
    assert check_nonzero(sp.Symbol('x')) is None
    assert multiplication_direction(sp.Integer(-2))=='reverse'
    assert multiplication_direction(sp.Symbol('x'))=='split_sign_cases'
    assert symmetry_quotient(8,[1,3,3,1]) is None  # binary necklaces, not 8/3
    assert symmetry_quotient(12,[2]*6)==6

def test_boundary_and_unknown():
    with pytest.raises(TypeError):extract({'problem':'private object'})
    f=extract(task(r'Solve $\frac{1}{x$'))
    assert f['uncertain']
    assert evaluate(trigger_for('S07'),f['facts'])['value'] is None

def test_options_are_not_given_equations():
    f=extract(task(r'Which of the following must be true? $c/a<1$'))
    assert evaluate(trigger_for('S07'),f['facts'])['value'] is False
