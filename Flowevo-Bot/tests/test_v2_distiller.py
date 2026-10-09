import json
import pytest
from conftest import make_trace
from flowevo_bot.v2.distiller import build_skill

@pytest.mark.parametrize('text',[
    'Fix order, repetition; use disjoint exhaustive cases. Check overlaps. Divide symmetry only for equal orbit sizes.',
    'Fix order, distinguishability; use disjoint exhaustive cases. Check overlaps. Divide symmetry only if all orbits equal/free.',
])
def test_guard_synonyms_not_literal_conjunction(text):
    sources=[make_trace(i).model_dump(mode='json') for i in range(3)]
    raw=json.dumps({'name':'Counting','steps':['Partition.','Recombine.'],'compact_prompt':text})
    s=build_skill('S04','old',raw,sources,[],123)
    assert s.status=='shadow' and len(s.source_trace_hashes)==3

def test_unsafe_symmetry_compression_rejected():
    sources=[make_trace(i).model_dump(mode='json') for i in range(3)]
    raw=json.dumps({'name':'Bad','steps':['Partition.','Divide.'],
                   'compact_prompt':'Fix order and repetition; use disjoint exhaustive cases. Check overlaps. Divide by the symmetry group size.'})
    with pytest.raises(ValueError,match='guard'):build_skill('S04','old',raw,sources,[],123)
