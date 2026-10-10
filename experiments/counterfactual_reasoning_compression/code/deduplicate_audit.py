"""Final independent-unit audit; retain original records and invalidate weak gate."""
from common import *
from grade_and_fit import policy_metrics,decision
from collections import defaultdict

def main():
    states=jl(OUT/'counterfactual_states.jsonl');groups=defaultdict(list)
    for state in states:groups[(state['task_id'],state['prefix_sha256'])].append(state)
    unique=[ss[0] for ss in groups.values()]  # first declared state, never best output
    rule=read(OUT/'evidence/frozen_controller_rule.json')['selected_rule']
    outcomes={(r['state_id'],r['branch']):r for r in jl(OUT/'counterfactual_outcomes.jsonl')}
    dev=[s for s in unique if s['discovery_split']=='development']
    metrics=[policy_metrics(dev,outcomes,method,rule) for method in ['A_normal','B1_fixed','B2_candidate','B3_repetition','B4_counterfactual']]
    b4=next(m for m in metrics if m['method']=='B4_counterfactual')
    original=read(OUT/'evidence/online_gate.json')
    checks=dict(original['checks'],development_triggers=b4['triggers']>=2)
    report=dict(at=now(),declared_state_records=len(states),unique_primary_prefix_states=len(unique),
        unique_development_states=len(dev),development_tasks=len({s['task_id'] for s in dev}),
        duplicate_groups=[[s['state_id'] for s in ss] for ss in groups.values() if len(ss)>1],
        source='Two planned positions snapped to the same complete paragraph boundary.',
        original_record_count_gate_passed=original['run_online_pilot'],audited_distinct_state_gate_passed=all(checks.values()),
        audited_checks=checks,development_metrics=metrics,unique_trigger_states=b4['triggers'],
        distinct_trigger_tasks=len({s['task_id'] for s in dev if decision('B4_counterfactual',s,rule)!='A'}),
        selection='First declared state per identical task+prefix hash; preserve both physical samples in ledger.',
        no_new_api_calls=True,controller_not_retuned=True,
        consequence='The original2 development triggers were repeated samples of one prefix. The robust gate was not satisfied. Retain the already-run4 fresh tasks as an exploratory engineering audit, not a gate-qualified independent performance validation.')
    save('evidence/distinct_state_audit.json',report)
    summary=read(OUT/'summary.json');summary['distinct_state_audit']=report
    summary['counterfactual']['unique_primary_prefix_states']=len(unique)
    summary['counterfactual']['original_record_count_gate_passed']=original['run_online_pilot']
    summary['counterfactual']['online_gate_passed']=all(checks.values())
    summary['independent_scope']='Four fresh tasks, exploratory engineering audit only: original trigger gate inflated by one duplicate prefix.'
    summary['decision']='NO-GO';save('summary.json',summary)
    print(json.dumps(dict(unique_primary_states=len(unique),unique_development_states=len(dev),distinct_triggers=b4['triggers'],deduplicated_development_saving=b4['continuation_saving_vs_A'],audited_gate=all(checks.values()))))
if __name__=='__main__':main()
