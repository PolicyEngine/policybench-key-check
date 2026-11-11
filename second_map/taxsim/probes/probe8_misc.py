"""Probe 8: SE $400 floor, negative intrec, dependent-filer EITC, SALT phase-down threshold, SSTB loss with wages,
QBI with scorp + negative psemp, UI on joint return, sage on a single return (error?)."""
import csv, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun
cases=[
 (1,"psemp 300 + wages 20k",dict(mstat=1,page=40,pwages=20000,psemp=300)),
 (2,"psemp 450 + wages 20k",dict(mstat=1,page=40,pwages=20000,psemp=450)),
 (3,"psemp 1 + wages 20k",dict(mstat=1,page=40,pwages=20000,psemp=1)),
 (4,"wages 20k only",dict(mstat=1,page=40,pwages=20000)),
 (5,"intrec -2000 + wages 20k",dict(mstat=1,page=40,pwages=20000,intrec=-2000)),
 (6,"mstat 8 age 30 wages 10k",dict(mstat=8,page=30,pwages=10000)),
 (7,"mstat 1 age 30 wages 10k",dict(mstat=1,page=30,pwages=10000)),
 (8,"single w550k proptax 50k mortgage 20000",dict(mstat=1,page=40,pwages=550000,proptax=50000,mortgage=20000)),
 (9,"single w504k proptax 50k mortgage 20000",dict(mstat=1,page=40,pwages=504000,proptax=50000,mortgage=20000)),
 (10,"joint w26k+53k pprofinc -11400",dict(mstat=2,page=69,sage=66,pwages=26000,swages=53000,pprofinc=-11400)),
 (11,"joint w26k+53k",dict(mstat=2,page=69,sage=66,pwages=26000,swages=53000)),
 (12,"joint w97k psemp -2800 scorp 5350",dict(mstat=2,page=48,sage=47,pwages=97000,psemp=-2800,scorp=5350)),
 (13,"joint w97k scorp 5350",dict(mstat=2,page=48,sage=47,pwages=97000,scorp=5350)),
 (14,"joint ssemp 30335 swages 65881 scorp 19650",dict(mstat=2,page=47,sage=46,swages=65881,ssemp=30335,scorp=19650)),
 (15,"joint pui 5000 sui 3000 w 30k",dict(mstat=2,page=40,sage=40,pwages=30000,pui=5000,sui=3000)),
 (16,"single wages 20k pensions 5000 depx1 age 27",dict(mstat=1,page=50,pwages=20000,depx=1,age1=27)),
 (17,"joint 3 deps 12,18,27 w97k",dict(mstat=2,page=48,sage=47,pwages=97000,depx=3,age1=12,age2=18,age3=27)),
 (18,"single age 61 psemp -6260 intrec 25950 gssi 36105 pensions 28830",dict(mstat=1,page=61,psemp=-6260,intrec=25950,gssi=36105,pensions=28830)),
]
recs=[]
for cid,_,r in cases:
    d=dict(taxsimid=cid,year=2026,state=0); d.update(r); recs.append(d)
res=tsrun.run(recs)
open(HERE/'probe8_in.csv','w').write(tsrun.to_csv(recs))
keys=["fiitax","fica","tfica","v10","v12","v13","v17","v18","v19","v22","v25","v28","qbid","niit","addmed","actc"]
with open(HERE/'probe8_out.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(['id','desc']+[k for k in res[0].keys() if k!='_messages'])
    for (cid,desc,_),r in zip(cases,res): wr.writerow([cid,desc]+[v for k,v in r.items() if k!='_messages'])
for (cid,desc,_),r in zip(cases,res):
    print(f"{cid:>3} {desc[:50]:<50} "+" ".join(f"{k}={r[k]:.2f}" for k in keys if isinstance(r.get(k),float) and r.get(k)))
# separate: sage on single return
try:
    tsrun.run([dict(taxsimid=1,year=2026,state=0,mstat=1,page=40,sage=40,pwages=1000)])
    print("sage on single: accepted")
except Exception as e:
    print("sage on single:", str(e)[:300])
