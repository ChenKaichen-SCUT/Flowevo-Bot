"""Only completed, graded training interventions enter the frozen action memory."""
from common import *
from flowevo_recovery.public import ACTIONS
from flowevo_recovery.checks import feature_key
from flowevo_recovery.controller import action_a
import collections,random

def main():
 assert not (OUT/'evidence/freeze.json').exists()
 source={r['state']['task']['task_id']:r for r in lines(OUT/'data/counterfactual_sources.jsonl')}
 groups=collections.defaultdict(list)
 for r in lines(OUT/'counterfactual_branches.jsonl'):groups[r['state']['task']['task_id']].append(r)
 experiences=[];excluded=[]
 for tid,rows in sorted(groups.items()):
  if {r['action'] for r in rows}!=set(ACTIONS) or any(type(r['score']['correct']) is not bool for r in rows):excluded.append(tid);continue
  for r in sorted(rows,key=lambda r:r['action']):
   experiences.append({'experience_id':digest([tid,r['action'],r['state']['call_id']]),'source_id':tid,'domain':r['state']['task']['domain'],
    'feature_key':feature_key(source[tid]['features']),'action':r['action'],'recovered':r['score']['correct'],'additional_tokens':r['additional_tokens'],
    'source_state_hash':r['source_state_hash'],'intervention_call_id':r['state']['call_id'],'counterfactual_verified':True})
 # Shuffle action labels within each source, preserving action counts, costs and outcomes.
 shuffled=[];rng=random.Random(20261010)
 for tid in sorted({r['source_id'] for r in experiences}):
  rows=[r for r in experiences if r['source_id']==tid];actions=[r['action'] for r in rows];rng.shuffle(actions)
  for r,a in zip(rows,actions):shuffled.append({**r,'action':a,'shuffled_control':True})
 jl(OUT/'recovery_experiences.jsonl',experiences);jl(OUT/'data/shuffled_experiences.jsonl',shuffled)
 write(OUT/'evidence/memory_build.json',{'created_at':now(),'source_count':len({r['source_id'] for r in experiences}),'experience_count':len(experiences),'excluded_incomplete_or_unknown_sources':excluded,
  'feature_groups':dict(collections.Counter(r['feature_key'] for r in experiences)), 'shuffled_action_changes':sum(a['action']!=b['action'] for a,b in zip(experiences,shuffled)),
  'contents':'flags/action/recovered/cost/provenance only; no question, answer, or solution', 'all_sources_outside_confirmation':not ({r['source_id'] for r in experiences}&set(read(OUT/'dataset_split_manifest.json')['confirmation_ids']))})
 print('memory',len(experiences),'experiences',len({r['source_id'] for r in experiences}),'sources','excluded',excluded)
if __name__=='__main__':main()
