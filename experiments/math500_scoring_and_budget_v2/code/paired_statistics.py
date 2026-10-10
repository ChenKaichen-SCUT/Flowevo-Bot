"""Predeclared paired statistics using the standard library only."""
import math,random

def percentile(xs,p):
 if not xs:return None
 ys=sorted(xs);q=(len(ys)-1)*p;i=int(q);j=min(i+1,len(ys)-1)
 return ys[i]+(ys[j]-ys[i])*(q-i)

def paired(a,b,seed=20261012,repetitions=20000):
 assert len(a)==len(b)
 n=len(a)
 if not n:return {'n':0,'status':'unavailable_empty_subset'}
 benefit=sum(not x and y for x,y in zip(a,b));harm=sum(x and not y for x,y in zip(a,b));same_true=sum(x and y for x,y in zip(a,b));same_false=n-benefit-harm-same_true
 discordant=benefit+harm
 p=min(1.,2*sum(math.comb(discordant,i) for i in range(min(benefit,harm)+1))/2**discordant) if discordant else 1.
 rng=random.Random(seed);d=[int(y)-int(x) for x,y in zip(a,b)]
 boot=[sum(rng.choices(d,k=n))/n for _ in range(repetitions)]
 return {'n':n,'both_correct':same_true,'first_only_correct_harm':harm,'second_only_correct_benefit':benefit,'both_not_confirmed_correct':same_false,'first_correct':sum(a),'second_correct':sum(b),'accuracy_difference':(benefit-harm)/n,'difference_percentage_points':100*(benefit-harm)/n,'mcnemar_exact_two_sided_p':p,'paired_bootstrap_95ci':[percentile(boot,.025),percentile(boot,.975)],'bootstrap_seed':seed,'bootstrap_repetitions':repetitions,'unknown_policy':'not confirmed correct for primary counts; unknown reported separately; no assertion of mathematical error'}

def distribution(xs):
 return {'count':len(xs),'min':min(xs) if xs else None,'p25':percentile(xs,.25),'median':percentile(xs,.5),'mean':sum(xs)/len(xs) if xs else None,'p75':percentile(xs,.75),'p90':percentile(xs,.9),'p95':percentile(xs,.95),'max':max(xs) if xs else None}
