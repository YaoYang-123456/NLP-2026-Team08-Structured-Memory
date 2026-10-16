"""Plot saved stage-two conservative statistics; never calls a model."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--summary',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();data=json.loads(a.summary.read_text(encoding='utf-8'));a.out.mkdir(parents=True,exist_ok=True)
conditions=['A','B','C','D'];colors=['#566573','#8a6db1','#248b8b','#da9251']
fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
x=np.arange(3);width=.19
for i,c in enumerate(conditions):
    y=[data['main']['rounds'][str(r)][c]['Yes'] for r in range(3)]
    u=[data['main']['rounds'][str(r)][c]['uncertain'] for r in range(3)]
    axes[0].bar(x+(i-1.5)*width,y,width,color=colors[i],label=c)
    axes[0].bar(x+(i-1.5)*width,u,width,bottom=y,color='white',edgecolor=colors[i],hatch='///')
axes[0].set(xticks=x,xticklabels=['Round 1','Round 2','Round 3'],ylim=(0,10.8),ylabel='Answers out of 10',title='Correct + hatched uncertain (not correct)')
axes[0].legend(ncol=4,frameon=False)
comparisons=['C-A','D-B','B-A','D-C'];categories=['only_target','only_baseline','incomparable'];cc=['#248b8b','#bb5454','#b9b9b9']
bottom=np.zeros(4)
for cat,col in zip(categories,cc):
    counts=[len(data['main']['paired'][pair].get(cat,[])) for pair in comparisons]
    axes[1].bar(comparisons,counts,bottom=bottom,color=col,label=cat.replace('_',' '));bottom+=counts
axes[1].set(ylabel='Paired repeated observations',title='Changes and unresolved pairs (ties omitted)')
axes[1].legend(frameon=False,fontsize=9)
fig.suptitle('Stage 2: 10 development questions, 3 repeats; external AI assessment',fontsize=12)
fig.savefig(a.out/'metamem-stage2-results.png',dpi=180);fig.savefig(a.out/'metamem-stage2-results.svg');plt.close(fig)

svg=a.out/"metamem-stage2-results.svg"
svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines())+"\n",encoding="utf-8",newline="\n")
