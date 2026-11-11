"""Probe 3: EITC by tax year (2023-2026), single, 1 child age 5, wage grid; does 2026 differ from earlier years?"""
import csv, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun
recs=[]; meta=[]; i=0
for y in (2023,2024,2025,2026):
    for kids in (0,1,2):
        for w in (5000,10000,13020,20000,30000,40000,50000):
            i+=1
            r=dict(taxsimid=i,year=y,state=0,mstat=1,page=30,pwages=w,depx=kids)
            for k in range(kids): r[f'age{k+1}']=5
            recs.append(r); meta.append((y,kids,w))
res=tsrun.run(recs)
open(HERE/'probe3_eitc_years_in.csv','w').write(tsrun.to_csv(recs))
with open(HERE/'probe3_eitc_years_out.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(['year','kids','wages','v25','fiitax','actc','v22'])
    for m,r in zip(meta,res): wr.writerow(list(m)+[r['v25'],r['fiitax'],r['actc'],r['v22']])
cur=None
for m,r in zip(meta,res):
    if m[:2]!=cur:
        cur=m[:2]; print(f"\nyear={m[0]} kids={m[1]}: ",end='')
    print(f"{m[2]}:{r['v25']:.0f}",end=' ')
print()
