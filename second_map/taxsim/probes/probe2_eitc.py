"""Probe 2: EITC schedule in the 2026 test build (single and joint, 0-3 children, wage grid)."""
import csv, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun
recs=[]; meta=[]
i=0
for mstat in (1,2):
    for kids in (0,1,2,3):
        for w in (1000,5000,8000,10000,13020,15000,18290,20000,23890,25000,30000,31160,35000,40000,45000,50000,55000,60000,65000):
            i+=1
            r=dict(taxsimid=i,year=2026,state=0,mstat=mstat,page=30,pwages=w,depx=kids)
            if mstat==2: r['sage']=30
            for k in range(kids): r[f'age{k+1}']=5
            recs.append(r); meta.append((mstat,kids,w))
res=tsrun.run(recs)
open(HERE/'probe2_eitc_in.csv','w').write(tsrun.to_csv(recs))
with open(HERE/'probe2_eitc_out.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(['mstat','kids','wages','v25_eitc','tfica','fiitax','actc','v22'])
    for m,r in zip(meta,res): wr.writerow(list(m)+[r['v25'],r['tfica'],r['fiitax'],r['actc'],r['v22']])
cur=None
for m,r in zip(meta,res):
    if m[:2]!=cur:
        cur=m[:2]; print(f"\nmstat={m[0]} kids={m[1]}: ",end='')
    print(f"{m[2]}:{r['v25']:.0f}",end=' ')
print()
