"""Probe set 1: dependents, payroll/SE outputs, senior/aged deduction, 2026 parameters.

Run: python3 probes/probe1.py  (writes probes/probe1_in.csv and probes/probe1_out.csv)
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun  # noqa: E402

Y = 2026
cases = [
    # id, description, record
    (1, "single wages 50k", dict(mstat=1, pwages=50000)),
    (2, "single wages 30k, 1 dep age 5", dict(mstat=1, pwages=30000, depx=1, age1=5)),
    (3, "single wages 30k, 1 dep age 17", dict(mstat=1, pwages=30000, depx=1, age1=17)),
    (4, "single wages 30k, 1 dep age 30", dict(mstat=1, pwages=30000, depx=1, age1=30)),
    (5, "single wages 30k, 1 dep age 0 (unspecified?)", dict(mstat=1, pwages=30000, depx=1, age1=0)),
    (6, "single wages 30k, 1 dep age 1", dict(mstat=1, pwages=30000, depx=1, age1=1)),
    (7, "single wages 30k, depx=1 ages blank, age1 not set", dict(mstat=1, pwages=30000, depx=1)),
    (9, "joint wages 60k, 2 kids 5,8", dict(mstat=2, pwages=60000, depx=2, age1=5, age2=8)),
    (10, "joint wages 60k, 3 deps 5,8,19", dict(mstat=2, pwages=60000, depx=3, age1=5, age2=8, age3=19)),
    (11, "joint wages 60k, 3 deps 5,8,18", dict(mstat=2, pwages=60000, depx=3, age1=5, age2=8, age3=18)),
    (12, "single age 70 pension 50k", dict(mstat=1, page=70, pensions=50000)),
    (13, "single age 64 pension 50k", dict(mstat=1, page=64, pensions=50000)),
    (14, "joint ages 70,68 pension 80k", dict(mstat=2, page=70, sage=68, pensions=80000)),
    (15, "joint ages 70,60 pension 80k", dict(mstat=2, page=70, sage=60, pensions=80000)),
    (16, "single age 70 pension 120k (senior ded phaseout)", dict(mstat=1, page=70, pensions=120000)),
    (17, "single age 0 (=40?) pension 50k", dict(mstat=1, page=0, pensions=50000)),
    (18, "single psemp 30k", dict(mstat=1, page=40, psemp=30000)),
    (19, "single pbusinc 30k", dict(mstat=1, page=40, pbusinc=30000)),
    (20, "single pprofinc 30k", dict(mstat=1, page=40, pprofinc=30000)),
    (21, "single scorp 30k", dict(mstat=1, page=40, scorp=30000)),
    (22, "single wages 40k + psemp 30k", dict(mstat=1, page=40, pwages=40000, psemp=30000)),
    (23, "single wages 250k", dict(mstat=1, page=40, pwages=250000)),
    (24, "joint wages 200k+100k", dict(mstat=2, page=40, sage=40, pwages=200000, swages=100000)),
    (25, "single wages 190k + psemp 20k", dict(mstat=1, page=40, pwages=190000, psemp=20000)),
    (26, "single intrec 300k", dict(mstat=1, page=40, intrec=300000)),
    (27, "single psemp -5000 + pension 30k", dict(mstat=1, page=40, psemp=-5000, pensions=30000)),
    (28, "single pbusinc -5000 + pension 30k", dict(mstat=1, page=40, pbusinc=-5000, pensions=30000)),
    (29, "single scorp -5000 + pension 30k", dict(mstat=1, page=40, scorp=-5000, pensions=30000)),
    (30, "single otherprop -5000 + pension 30k", dict(mstat=1, page=40, otherprop=-5000, pensions=30000)),
    (31, "single pprofinc 600 + wages 30k (QBI min ded?)", dict(mstat=1, page=40, pprofinc=1200, pwages=30000)),
    (32, "single wages 0 age 30 (childless EITC age)", dict(mstat=1, page=30, pwages=8000)),
    (33, "single wages 8000 age 22", dict(mstat=1, page=22, pwages=8000)),
    (34, "single wages 8000 age 66", dict(mstat=1, page=66, pwages=8000)),
    (35, "dependent filer mstat 8 wages 45000 age 16", dict(mstat=8, page=16, pwages=45000)),
    (36, "dependent filer mstat 8 intrec 5000 age 16", dict(mstat=8, page=16, intrec=5000)),
    (37, "dependent filer mstat 8 wages 3000 age 16", dict(mstat=8, page=16, pwages=3000)),
]

records = []
for cid, _, rec in cases:
    r = dict(taxsimid=cid, year=Y, state=0)
    r.update(rec)
    records.append(r)

res = tsrun.run(records, idtl=2)
keys = ["fiitax", "fica", "tfica", "v10", "v13", "v14", "v17", "v18", "v19", "v22", "v24", "v25",
        "v27", "v28", "qbid", "niit", "addmed", "actc"]
with open(HERE / "probe1_in.csv", "w") as f:
    f.write(tsrun.to_csv(records))
with open(HERE / "probe1_out.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "desc"] + list(res[0].keys()))
    for (cid, desc, _), r in zip(cases, res):
        w.writerow([cid, desc] + list(r.values()))
for (cid, desc, _), r in zip(cases, res):
    print(f"{cid:>3} {desc[:46]:<46} " + " ".join(f"{k}={r[k]:.0f}" for k in keys if r.get(k)))
