"""Transparent action selection from public flags and frozen training aggregates."""
from collections import defaultdict
from .public import ACTIONS
from .checks import feature_key
FLAGS=('truncated','missing_final','local_contradiction','compile_failed','public_failed','environment_issue')
METHODS=('single','fixed_retry','deterministic_retry','A','C','C_shuffled')

def validate(f):
 if set(f)-set(FLAGS)-{'domain','evidence','final_status'}:raise ValueError('non-public feature field')
 if f['domain'] not in ('math','code'):raise ValueError('domain')
 for k in FLAGS:
  if type(f[k]) is not bool:raise ValueError('non-boolean flag')

def action_a(f):
 validate(f)
 if f['environment_issue']:return None
 if f['truncated']:return 'continue'
 if f['compile_failed'] or f['public_failed'] or f['local_contradiction']:return 'repair'
 if f['missing_final']:return 'continue'
 return None

def select(method,f,memory=(),min_sources=2):
 validate(f);base=action_a(f)
 if method=='single':return {'action':None,'reason':'single_pass','memory_sources':[]}
 if method=='fixed_retry':return {'action':'retry','reason':'fixed_extra_call','memory_sources':[]}
 if method=='deterministic_retry':return {'action':'retry' if not f['environment_issue'] and (f['truncated'] or f['compile_failed'] or f['public_failed']) else None,'reason':'public_failure_rule','memory_sources':[]}
 if method=='A' or base is None:return {'action':base,'reason':'public_flag_rule','memory_sources':[]}
 if method not in ('C','C_shuffled'):raise ValueError('method')
 group=[r for r in memory if r['feature_key']==feature_key(f)]
 sources={r['source_id'] for r in group};buckets=defaultdict(list)
 for r in group:buckets[r['action']].append(r)
 if len(sources)<min_sources or any(len(buckets[a])!=len(sources) for a in ACTIONS):
  return {'action':base,'reason':'memory_insufficient_fallback_A','memory_sources':[]}
 def stats(a):
  rows=buckets[a];return (sum(r['recovered'] for r in rows)/len(rows),sum(r['additional_tokens'] for r in rows)/len(rows))
 def utility(a):
  success,cost=stats(a);return success-cost/100000
 best=max(ACTIONS,key=lambda a:(utility(a),a==base));sb,cb=stats(best);sa,ca=stats(base)
 advantage=utility(best)-utility(base)
 change=best!=base and (advantage>=.05 or (sb==sa and cb<ca))
 return {'action':best if change else base,'reason':'memory_override' if change else 'memory_agrees_A',
         'memory_sources':sorted(sources),'utility_advantage':advantage,'training_stats':{a:stats(a) for a in ACTIONS}}
