"""Render the adopted stage-three summaries; no model calls."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'reports/metamem-stage3-results.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig,axes=plt.subplots(1,3,figsize=(14,4.4))
colors=['#577590','#e09f3e'];arms=['baseline','candidate'];names=['Original prompt','Evidence prompt']
for i,arm in enumerate(arms):
    axes[0].bar([r+i*.34 for r in range(3)],[data['rounds'][str(r)][arm]['Yes'] for r in range(3)],width=.34,color=colors[i],label=names[i])
axes[0].set(xticks=[.17,1.17,2.17],xticklabels=['Round 1','Round 2','Round 3'],ylim=(0,10),ylabel='Yes / 10',title='Correctness (strict v2)');axes[0].legend(fontsize=8)
keys=['factual_support','temporal_count','citation_support'];positive=['supported','valid','supported']
for i,arm in enumerate(arms):
    axes[1].bar([r+i*.34 for r in range(3)],[data['quality']['totals'][arm][k].get(v,0) for k,v in zip(keys,positive)],width=.34,color=colors[i])
axes[1].set(xticks=[.17,1.17,2.17],xticklabels=['Factual\nsupport','Time/count\nvalid','Citation\nsupport'],ylim=(0,30),ylabel='Positive assessments / 30 outputs',title='Separate evidence quality')
axes[1].text(.02,.95,'N/A and uncertain are not negative labels',transform=axes[1].transAxes,va='top',fontsize=8)
axes[2].bar(names,[data['cost_by_condition'][a]['completion_tokens']/30 for a in arms],color=colors)
axes[2].set(ylabel='Mean completion tokens',title='Output cost')
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.suptitle('Exploratory paired development study: 10 questions, 3 repetitions; AI assessment, no human gold',fontsize=11)
fig.tight_layout(rect=[0,0,1,.94])
for ext in ['png','svg']:
    path=ROOT/f'reports/metamem-stage3-comparison.{ext}';fig.savefig(path,dpi=180,bbox_inches='tight')
    if ext=='svg':path.write_text('\n'.join(l.rstrip() for l in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
