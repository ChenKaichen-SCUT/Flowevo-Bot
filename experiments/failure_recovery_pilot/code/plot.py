"""Standalone descriptive figure from recorded method costs; no API."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).resolve().parents[1];rows=json.loads((p/'evidence/analysis_summary.json').read_text())['method_stats'];r={x['method']:x for x in rows if x['domain']=='all'}
fig,ax=plt.subplots(figsize=(9.5,5.8),layout='constrained')
labels={'single':'Single pass','fixed_retry':'Fixed retry','deterministic_retry':'Deterministic / shuffled','A':'A / C'}
for m,label in labels.items():
 x=r[m]['total_tokens']/1000;y=r[m]['final_correct'];z=r[m]['adapter_correct']
 ax.plot([x,x],[y,z],color='#bbc3cb',linewidth=1,zorder=1)
 ax.scatter(x,y,s=75,color='#24649a',label='Original first-block extraction' if m=='single' else None,zorder=3)
 ax.scatter(x,z,s=80,color='#b56218',marker='D',label='Predeclared public-entrypoint extraction' if m=='single' else None,zorder=3)
 offset=(-70,-19) if m=='A' else (7,-17 if m=='fixed_retry' else 7)
 ax.annotate(label,(x,y),xytext=offset,textcoords='offset points',fontsize=10)
 if m in ('single','A'):ax.annotate(f'{z}/48',(x,z),xytext=(6,8),textcoords='offset points',fontsize=10)
ax.set(xlabel='Logical test tokens per method (thousands)',ylabel='Correct tasks out of 48',title='Recovery pilot: apparent gains shrink after fixing extraction',ylim=(33,45),xlim=(48,119))
ax.grid(alpha=.2);ax.legend(loc='lower left',fontsize=9)
fig.text(.01,-.035,'24 MATH + 24 MBPP; post-seal explicit answer adjudications. Paired small-sample, descriptive results.\nExtraction sensitivity reuses the same sealed outputs; it does not select a block using hidden tests.',fontsize=9)
(p/'figures').mkdir(exist_ok=True)
for suffix in ('png','svg','pdf'):fig.savefig(p/'figures'/f'accuracy_cost.{suffix}',dpi=180,bbox_inches='tight')
print('saved png svg pdf')
