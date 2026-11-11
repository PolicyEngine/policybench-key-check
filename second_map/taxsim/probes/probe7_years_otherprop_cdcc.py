"""Probe 7: otherprop and childcare across tax years 2023-2026 (is the 2026 behaviour year-specific?)."""
import csv, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun
recs=[]; meta=[]; i=0
for y in (2023,2024,2025,2026):
    for desc,r in [("otherprop 5000 w40k",dict(mstat=1,page=40,pwages=40000,otherprop=5000)),
                   ("otherprop -5000 w40k",dict(mstat=1,page=40,pwages=40000,otherprop=-5000)),
                   ("w40k only",dict(mstat=1,page=40,pwages=40000)),
                   ("joint 50k+50k kids 4,9 childcare 10000",dict(mstat=2,page=35,sage=35,pwages=50000,swages=50000,depx=2,age1=4,age2=9,childcare=10000)),
                   ("joint 50k+50k kids 4,9 childcare 0",dict(mstat=2,page=35,sage=35,pwages=50000,swages=50000,depx=2,age1=4,age2=9)),
                   ("single 60k kid 5 childcare 3000",dict(mstat=1,page=35,pwages=60000,depx=1,age1=5,childcare=3000)),
                   ("single 60k kid 5 childcare 0",dict(mstat=1,page=35,pwages=60000,depx=1,age1=5))]:
        i+=1
        d=dict(taxsimid=i,year=y,state=0); d.update(r); recs.append(d); meta.append((y,desc))
res=tsrun.run(recs)
open(HERE/'probe7_in.csv','w').write(tsrun.to_csv(recs))
with open(HERE/'probe7_out.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(['year','desc']+list(res[0].keys()))
    for m,r in zip(meta,res): wr.writerow(list(m)+list(r.values()))
for m,r in zip(meta,res):
    print(m, 'agi',r['v10'],'tax',r['v19'],'cdcc',r['v24'],'ctc',r['v22'],'eitc',r['v25'],'fiitax',r['fiitax'])
