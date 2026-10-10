from common import *
import csv
FIRST=['algebra_673','algebra_884','counting_probability_411','geometry_165','geometry_48','intermediate_algebra_796','prealgebra_334','prealgebra_435','prealgebra_498']
COVERAGE=['geometry_200','geometry_352','intermediate_algebra_423','intermediate_algebra_478','intermediate_algebra_482','intermediate_algebra_700','intermediate_algebra_756','intermediate_algebra_813','number_theory_158','number_theory_295','prealgebra_372','prealgebra_551','prealgebra_598','prealgebra_625','prealgebra_841','prealgebra_853','precalculus_380']
LABELS=['intermediate_algebra_409','intermediate_algebra_516','intermediate_algebra_563']

def main():
 fixtures=[]
 for r in read(ROOT/'experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json'):
  if r['task_id'].removeprefix('math_test_') in FIRST:
   fixtures.append({'record':{'record_id':'first_batch:'+r['task_id'],'task_id':r['task_id'],'question':r['question'],'reference_raw':r['reference_solution'],'prediction_raw':r['solution'],'finish_reason':'stop','submission_sealed':True,'source_path':'experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json'},'expected_status':'correct','category':'first_batch_9_confirmed_false_negatives'})
 for r in jl(OUT/'evidence/input_records.jsonl'):
  key=r['task_id'].removeprefix('math_test_')
  if key in COVERAGE+LABELS or key in ['number_theory_491','algebra_1161','geometry_56','intermediate_algebra_494']:
   expected='prediction_incomplete' if r['finish_reason']=='length' else 'incorrect' if key=='number_theory_491' else 'correct'
   fixtures.append({'record':r,'expected_status':expected,'category':'coverage17' if key in COVERAGE else 'label3' if key in LABELS else 'wrong_or_truncated'})
 dis=list(csv.DictReader((OLD/'scoring_disagreements.csv').open()))
 labels={r['task_id']:r for r in jl(OLD/'data/offline_labels.jsonl')}
 for r in dis:
  raw=read(OLD/r['raw_evidence']);call=next(x for x in jl(OLD/'api_calls.jsonl') if x['job_id']==r['job_id'])
  record={'record_id':'historical_disagreement:'+r['job_id'],'task_id':r['task_id'],'question':r['question'],'reference_raw':labels[r['task_id']]['reference_solution'],'prediction_raw':r['solution'],'finish_reason':call['finish_reason'],'submission_sealed':True,'source_path':str((OLD/r['raw_evidence']).relative_to(ROOT)),'request_hash':call['request_hash'],'response_hash':call['response_hash']}
  fixtures.append({'record':record,'expected_status':'correct','category':'all_22_historical_disagreements'})
 # Deterministic ordinary regression examples include scalar/matrix/equation/tuple.
 ids=['algebra_1020','precalculus_120','precalculus_243','algebra_944','prealgebra_385']
 fixtures.extend({'record':r,'expected_status':'correct','category':'old_both_true_normal'} for r in jl(OUT/'evidence/input_records.jsonl') if r['task_id'].removeprefix('math_test_') in ids)
 lines('evidence/regression_fixtures.jsonl',fixtures)
 print({'records':len(fixtures),'first_batch':sum(r['category'].startswith('first') for r in fixtures),'historical_disagreement_responses':len(dis)})
if __name__=='__main__':main()
