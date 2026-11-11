"""Probe 5: itemized deductions (SALT cap, medical floor, charitable floor, 37% haircut), CDCC 2026,
capital losses, Social Security taxation, AMT, nonprop, NIIT on otherprop/scorp, dependent std deduction."""
import csv, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun
B=dict(year=2026,state=0)
cases=[
 (1,"single w150k proptax 50k",dict(mstat=1,page=40,pwages=150000,proptax=50000)),
 (2,"single w150k otheritem 50k",dict(mstat=1,page=40,pwages=150000,otheritem=50000)),
 (3,"single w150k proptax 20k otheritem 30k",dict(mstat=1,page=40,pwages=150000,proptax=20000,otheritem=30000)),
 (4,"single w150k mortgage 50k",dict(mstat=1,page=40,pwages=150000,mortgage=50000)),
 (5,"single w600k proptax 50k (SALT phase-down)",dict(mstat=1,page=40,pwages=600000,proptax=50000)),
 (6,"single w700k proptax 50k",dict(mstat=1,page=40,pwages=700000,proptax=50000)),
 (7,"single w700k mortgage 50k (37% haircut?)",dict(mstat=1,page=40,pwages=700000,mortgage=50000)),
 (8,"single w100k mortgage 20k",dict(mstat=1,page=40,pwages=100000,mortgage=20000)),
 (9,"single w100k mortgage 20000 otheritem 0 proptax 0 -> compare charity vs mortgage impossible",dict(mstat=1,page=40,pwages=100000,mortgage=20000)),
 (10,"joint w50k+50k 2 kids 4,9 childcare 10000",dict(mstat=2,page=35,sage=35,pwages=50000,swages=50000,depx=2,age1=4,age2=9,childcare=10000)),
 (11,"joint w50k+0 2 kids 4,9 childcare 10000",dict(mstat=2,page=35,sage=35,pwages=100000,swages=0,depx=2,age1=4,age2=9,childcare=10000)),
 (12,"joint w100k+100k 2 kids childcare 10000",dict(mstat=2,page=35,sage=35,pwages=100000,swages=100000,depx=2,age1=4,age2=9,childcare=10000)),
 (13,"single w40k 1 kid 1 childcare 9600",dict(mstat=1,page=35,pwages=40000,depx=1,age1=1,childcare=9600)),
 (14,"single w40k 1 kid 13 childcare 3000",dict(mstat=1,page=35,pwages=40000,depx=1,age1=13,childcare=3000)),
 (15,"single w2000 1 kid 5 childcare 3000 (earned-income limit)",dict(mstat=1,page=35,pwages=2000,intrec=40000,depx=1,age1=5,childcare=3000)),
 (16,"single w50k ltcg -20000",dict(mstat=1,page=40,pwages=50000,ltcg=-20000)),
 (17,"single w50k stcg -2000 ltcg 10000",dict(mstat=1,page=40,pwages=50000,stcg=-2000,ltcg=10000)),
 (18,"single age70 gssi 30000 pension 20000",dict(mstat=1,page=70,gssi=30000,pensions=20000)),
 (19,"single age70 gssi 30000 pension 20000 intrec 5000",dict(mstat=1,page=70,gssi=30000,pensions=20000,intrec=5000)),
 (20,"joint ages 70 gssi 40000 pension 30000",dict(mstat=2,page=70,sage=70,gssi=40000,pensions=30000)),
 (21,"single w50k nonprop -3000",dict(mstat=1,page=40,pwages=50000,nonprop=-3000)),
 (22,"single w50k nonprop 3000",dict(mstat=1,page=40,pwages=50000,nonprop=3000)),
 (23,"single w250k otherprop 50000 (NIIT)",dict(mstat=1,page=40,pwages=250000,otherprop=50000)),
 (24,"single w250k scorp 50000 (NIIT?)",dict(mstat=1,page=40,pwages=250000,scorp=50000)),
 (25,"single w250k pbusinc 50000 (NIIT?)",dict(mstat=1,page=40,pwages=250000,pbusinc=50000)),
 (26,"single w250k psemp 50000 (NIIT?)",dict(mstat=1,page=40,pwages=250000,psemp=50000)),
 (27,"single w250k intrec 50000",dict(mstat=1,page=40,pwages=250000,intrec=50000)),
 (28,"single w250k dividends 50000",dict(mstat=1,page=40,pwages=250000,dividends=50000)),
 (29,"single w250k ltcg 50000",dict(mstat=1,page=40,pwages=250000,ltcg=50000)),
 (30,"single w250k pensions 50000",dict(mstat=1,page=40,pwages=250000,pensions=50000)),
 (31,"single w250k nonprop 50000",dict(mstat=1,page=40,pwages=250000,nonprop=50000)),
 (32,"single ltcg 1,000,000 (AMT?)",dict(mstat=1,page=40,ltcg=1000000)),
 (33,"joint w400k proptax 40000 otheritem 40000 (AMT)",dict(mstat=2,page=40,sage=40,pwages=400000,proptax=40000,otheritem=40000)),
 (34,"single pui 10000 w20000",dict(mstat=1,page=40,pui=10000,pwages=20000)),
 (35,"single transfers 50000",dict(mstat=1,page=40,transfers=50000)),
 (36,"single w30k scorp -5000 (passive loss limitation?)",dict(mstat=1,page=40,pwages=30000,scorp=-5000)),
 (37,"single age 70 pension 10000 (sec 22 credit?)",dict(mstat=1,page=70,pensions=30000)),
 (38,"single age 70 gssi 3000 pension 25000",dict(mstat=1,page=70,gssi=3000,pensions=25000)),
]
recs=[]
for cid,_,r in cases:
    d=dict(taxsimid=cid,**B); d.update(r); recs.append(d)
res=tsrun.run(recs)
open(HERE/'probe5_items_in.csv','w').write(tsrun.to_csv(recs))
keys=["fiitax","tfica","v10","v12","v13","v17","v18","v19","v22","v24","v25","v26","v27","v28","qbid","niit","addmed","actc"]
with open(HERE/'probe5_items_out.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(['id','desc']+list(res[0].keys()))
    for (cid,desc,_),r in zip(cases,res): wr.writerow([cid,desc]+list(r.values()))
for (cid,desc,_),r in zip(cases,res):
    print(f"{cid:>3} {desc[:50]:<50} "+" ".join(f"{k}={r[k]:.0f}" for k in keys if isinstance(r.get(k),float) and r.get(k)))
