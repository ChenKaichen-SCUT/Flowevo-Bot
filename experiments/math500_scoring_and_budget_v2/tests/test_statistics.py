import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from paired_statistics import paired,distribution

def test_exact_discordant_test_known_case():
 r=paired([False]*10,[True]*10,repetitions=100)
 assert r['mcnemar_exact_two_sided_p']==2/1024
 assert r['paired_bootstrap_95ci']==[1.0,1.0]
 assert r['second_only_correct_benefit']==10

def test_paired_direction_and_no_change():
 a=[True,False,True,False];b=[False,True,True,False]
 r=paired(a,b,repetitions=100)
 assert r['first_only_correct_harm']==r['second_only_correct_benefit']==1
 assert r['mcnemar_exact_two_sided_p']==1 and r['accuracy_difference']==0
 s=paired(a,a,repetitions=100);assert s['paired_bootstrap_95ci']==[0,0]

def test_empty_control_and_distribution():
 assert paired([],[])['status']=='unavailable_empty_subset'
 d=distribution([0,10,20]);assert d['median']==10 and d['mean']==10
