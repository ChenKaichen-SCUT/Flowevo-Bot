import sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'FlowEvo/src'))
from math_evaluation import MathEvaluatorV3
FIXTURES=[json.loads(x) for x in (Path(__file__).resolve().parents[1]/'evidence/regression_fixtures.jsonl').read_text().splitlines()]
@pytest.mark.parametrize('fixture',FIXTURES,ids=lambda x:x['category']+':'+x['record']['record_id'])
def test_historical_case(fixture):
 r=MathEvaluatorV3().evaluate(fixture['record'])
 assert r['status']==fixture['expected_status'],{k:v for k,v in r.items() if k not in ('question','prediction_raw','reference_raw')}
