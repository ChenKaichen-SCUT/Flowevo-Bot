"""Exact equivalence proofs. Numerical similarity is never a sufficient proof."""
import sympy as s
from .models import Unsupported


def exact(a,b):
    if a==b:return True,'structural_equality',{'difference':'0'}
    diff=s.cancel(s.together(a-b))
    if diff==0:return True,'exact_rational_or_polynomial_identity',{'difference':'0'}
    diff=s.simplify(diff)
    if diff==0:return True,'symbolic_identity',{'difference':'0'}
    if not diff.free_symbols and diff.is_zero is False:return False,'exact_nonzero_difference',{'difference':str(diff)}
    if diff.is_polynomial(*sorted(diff.free_symbols,key=str)) if diff.free_symbols else False:
        return False,'nonzero_polynomial',{'difference':str(diff)}
    return None,'identity_not_proven',{'difference':str(diff)}


def compare(a,b,spec):
    if a.kind!=b.kind:return False,'typed_object_mismatch',{'prediction_type':a.kind,'reference_type':b.kind}
    if a.domain!=b.domain:
        # Domain equality is a requirement, not something random tests can prove.
        try:equal=a.domain.symmetric_difference(b.domain)==s.EmptySet
        except (AttributeError,TypeError):equal=False
        if not equal:return None,'domain_equivalence_not_established',{'prediction_domain':str(a.domain),'reference_domain':str(b.domain)}
    if a.kind in ('choice','text','base_numeral'):
        return a.value==b.value,'exact_label_or_numeral',{'prediction':str(a.value),'reference':str(b.value)}
    if a.kind in ('finite_set','interval'):
        if a.value==b.value:return True,'exact_set_equality',{'symmetric_difference':'EmptySet'}
        if a.kind=='finite_set':
            if len(a.value)!=len(b.value):return False,'set_cardinality_mismatch',{'prediction_size':len(a.value),'reference_size':len(b.value)}
            unmatched=list(b.value)
            for x in a.value:
                index=next((i for i,y in enumerate(unmatched) if exact(x,y)[0] is True),None)
                if index is None:
                    verdicts=[exact(x,y)[0] for y in unmatched]
                    return (False if all(v is False for v in verdicts) else None),'finite_set_membership_mismatch',{'unmatched_prediction':str(x)}
                unmatched.pop(index)
            return True,'exact_elementwise_set_equality',{'unmatched':[]}
        diff=s.SymmetricDifference(a.value,b.value)
        if diff==s.EmptySet:return True,'exact_set_equality',{'symmetric_difference':'EmptySet'}
        if diff.is_empty is False:return False,'unequal_solution_sets',{'symmetric_difference':str(diff)}
        return None,'set_equality_unresolved',{'symmetric_difference':str(diff)}
    if a.kind in ('tuple','matrix'):
        shape_a=a.value.shape if a.kind=='matrix' else (len(a.value),)
        shape_b=b.value.shape if b.kind=='matrix' else (len(b.value),)
        if shape_a!=shape_b:return False,'dimension_mismatch',{'prediction_shape':shape_a,'reference_shape':shape_b}
        checks=[exact(x,y) for x,y in zip(a.value,b.value)]
        status=False if any(x[0] is False for x in checks) else True if all(x[0] is True for x in checks) else None
        return status,'ordered_component_comparison',{'checks':checks}
    if a.kind=='equation':
        x=a.value.lhs-a.value.rhs;y=b.value.lhs-b.value.rhs
        if x==0 or y==0:return (x==y),'equation_degeneracy_check',{'prediction_zero':x==0,'reference_zero':y==0}
        ratio=s.cancel(x/y)
        if not ratio.free_symbols and ratio.is_zero is False:return True,'nonzero_constant_equation_multiple',{'ratio':str(ratio)}
        syms=x.free_symbols|y.free_symbols
        if len(syms)==1:
            var=next(iter(syms));domain=s.S.Complexes if spec.domain=='complex' else s.S.Integers if spec.domain=='integer' else s.S.Reals
            sa=s.solveset(x,var,domain=domain);sb=s.solveset(y,var,domain=domain)
            if not sa.has(s.ConditionSet) and not sb.has(s.ConditionSet):return sa==sb,'exact_equation_solution_sets',{'prediction':str(sa),'reference':str(sb)}
        return None,'equation_zero_set_not_proven',{'residuals':[str(x),str(y)]}
    if a.kind=='quantity':
        if a.dimension!=b.dimension:return False,'unit_dimension_mismatch',{'prediction_dimension':a.dimension,'reference_dimension':b.dimension}
        da=next((n for n in a.notes if n.startswith('direction=')),None);db=next((n for n in b.notes if n.startswith('direction=')),None)
        if da!=db and 'direction=unspecified' not in (da,db):return False,'opposite_direction_of_change',{'prediction':da,'reference':db}
    verdict,method,evidence=exact(a.value,b.value)
    if verdict is not True and spec.decimal_places is not None and not (a.value.free_symbols or b.value.free_symbols):
        # Round exact rationals to requested digits, ties away from zero. Reference
        # rounding does not license a prediction outside the requested precision.
        def rounded(x):
            scale=10**spec.decimal_places
            return s.sign(x)*s.floor(s.Abs(x)*scale+s.Rational(1,2))/scale
        if a.value.is_Rational and b.value.is_Rational and a.value==rounded(a.value) and a.value==rounded(b.value):
            return True,'explicit_decimal_rounding',{'places':spec.decimal_places,'rounding':'half away from zero'}
    return verdict,method,evidence
