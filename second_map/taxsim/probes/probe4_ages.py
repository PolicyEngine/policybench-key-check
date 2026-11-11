"""Probe 4: CTC/ODC/EITC/CDCC by dependent age (2025 vs 2026); dep13/dep17/dep18 legacy inputs."""
import csv, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun
recs=[]; meta=[]; i=0
for y in (2025,2026):
    for a in (1,12,13,16,17,18,19,20,23,24,30):
        i+=1
        r=dict(taxsimid=i,year=y,state=0,mstat=1,page=35,pwages=20000,depx=1,age1=a,childcare=3000)
        recs.append(r); meta.append((y,a))
res=tsrun.run(recs)
open(HERE/'probe4_ages_in.csv','w').write(tsrun.to_csv(recs))
with open(HERE/'probe4_ages_out.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(['year','age1','v13','v22_ctc','actc','v24_cdcc','v25_eitc','fiitax'])
    for m,r in zip(meta,res): wr.writerow(list(m)+[r['v13'],r['v22'],r['actc'],r['v24'],r['v25'],r['fiitax']])
for m,r in zip(meta,res):
    print(m, 'stdded',r['v13'],'ctc',r['v22'],'actc',r['actc'],'cdcc',r['v24'],'eitc',r['v25'],'fiitax',r['fiitax'])
