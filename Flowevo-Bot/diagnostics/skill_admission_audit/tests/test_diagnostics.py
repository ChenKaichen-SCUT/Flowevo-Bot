import csv,json,sys,hashlib,itertools
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1];PROJECT=P.parents[1];EXP=PROJECT/'experiments/math500_goldfree_20261009'
sys.path.insert(0,str(P/'scripts'))
from analyze import gate_analysis
from flowevo_bot.common import read_json
from flowevo_bot.schemas import SkillRecord,ProblemView
from flowevo_bot.features import extract_features,matches
from flowevo_bot.evaluator import extract_answer
from flowevo_bot.experiment_grader import grade_one
from runtime.config import Config

def rows(name):
 with (P/'data'/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def test_full_original_records_no_truncation():
 actual=read_json(P/'data/skills_full.json');original=read_json(EXP/'real_bank.json')['skills']
 assert actual==original and len(actual)==12
 report=(P/'reports/01_ALL_SKILLS.md').read_text()
 for s in original:
  assert s['skill_id'] in report and s['compact_prompt'] in report
  assert s['source_task_ids'] and s['provenance']

def test_admission_replay_and_counterfactuals():
 cfg=Config.model_validate(read_json(EXP/'config.json'));skills=[SkillRecord.model_validate(s) for s in read_json(P/'data/skills_full.json')]
 for s in skills:assert gate_analysis(s,cfg)['status']==s.status
 result=[s.name for s in skills if gate_analysis(s,cfg,'positive_cost')['status']=='active']
 assert set(result)=={'Order-aware case counting with overcount correction','Triangle Relation-to-Equation Reduction'}
 assert not any(gate_analysis(s,cfg,'dev_count')['status']=='active' for s in skills)

def test_missing_evidence_not_false_zero():
 data=rows('skill_diagnostics.csv');empty=[r for r in data if r['dev_actual_uses']=='0']
 assert len(empty)==8
 for r in empty:
  assert r['dev_skill_correct']==r['dev_base_correct']==r['observed_token_saving']==r['estimated_token_saving']==''
  assert r['evidence_status']=='insufficient_evidence'

def test_trigger_matrix_and_no_gold_columns():
 data=rows('skill_task_matches.csv')
 assert len(data)==4200 and len({(r['skill_id'],r['task_id']) for r in data})==4200
 assert not any('gold' in k or 'solution' in k for k in data[0])
 assert sum(r['eligible']=='True' for r in data)==39

def test_source_self_match_and_representation_counterexample():
 skills=[SkillRecord.model_validate(x) for x in read_json(P/'data/skills_full.json')]
 s=next(s for s in skills if s.skill_id=='algebra_f19801d93b4c6de1')
 assert 'Only if one of' in s.compact_prompt
 assert not matches(s,frozenset({'quadratic'}))
 st=read_json(P/'data/evidence/skill_statistics.json')
 assert sum(x['source_matches']==0 for x in st.values())==9
 assert 'quadratic' in extract_features(ProblemView(task_id='synthetic',problem='x^20'))

def test_symmetry_condition_counterexample_is_local_not_model_data():
 strings=[''.join(v) for v in itertools.product('01',repeat=3)]
 orbits={min(s[i:]+s[:i] for i in range(3)) for s in strings}
 assert len(strings)==8 and len(orbits)==4
 assert len(strings)/3!=len(orbits)

def test_recorded_harm_separates_format_from_truncation():
 tid='math_train_precalculus_250';skill='precalculus_5193e2e6c7ae508d'
 s=read_json(EXP/'validation_v2'/skill/(tid+'.submission.json'))
 assert 'y-x=1' in s['solution'] and 'This is the equation of a line' in s['solution']
 assert extract_answer(s['solution'])=='(A) Line'
 assert grade_one((tid,s['final_answer'],r'\text{(A)}',False))['final_correct'] is False
 c=read_json(EXP/'validation_v2'/skill/'math_train_precalculus_88.calls.json')
 assert c['failures'] and c['calls'][0]['completion_tokens']==4096
 assert list(c['responses'].values())==['']

def test_empty_bank_replay_500_and_cost_reconcile():
 assert len(rows('nobank_replay.csv'))==500
 assert all(r['actual_bot_prompt_equals_empty_bank']=='True' for r in rows('nobank_replay.csv'))
 costs=rows('cost_breakdown.csv')
 assert sum(int(c['total_tokens']) for c in costs)==2234706
 assert sum(int(c['calls']) for c in costs)==1802
 assert all(c['estimated_calls']=='0' for c in costs)
 pairs=rows('task_pairwise.csv')
 assert {k:sum(r['pair_outcome']==k for r in pairs) for k in ('both_correct','flowevo_only','bot_only','both_wrong')}=={'both_correct':454,'flowevo_only':8,'bot_only':10,'both_wrong':28}

def test_lineage_and_read_only_hashes():
 lineage=read_json(P/'data/evidence/source_lineage.json')
 assert len(lineage)==71 and all(r['model_calls']==1 and r['retries']==0 and r['prompt_equals_clean_base'] for r in lineage)
 for f,h in read_json(P/'tests/input_hashes_before.json').items():
  original=Path(f)
  target=original if original.exists() else PROJECT.parent/str(original).split('/FlowEvo+BoT/',1)[1]
  assert hashlib.sha256(target.read_bytes()).hexdigest()==h
 assert read_json(P/'manifest.json')['new_llm_calls']==0
 assert read_json(P/'tests/read_only_check.json')['pass']

def test_all_requested_deliverables():
 assert len(list((P/'reports').glob('*.md')))==9
 for file in ('skills_full.json','skill_diagnostics.csv','admission_decisions.jsonl','skill_task_matches.csv','task_pairwise.csv','cost_breakdown.csv','prompt_config_comparison.csv'):
  assert (P/'data'/file).stat().st_size>0
