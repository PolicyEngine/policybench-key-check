"""Probe 9: is proptax (and otheritem) added back for the AMT, and does the SALT cap reach otheritem at high income?

Run: python3 probes/probe9_amt_salt.py  (writes probes/probe9_in.csv and probes/probe9_out.csv)
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun  # noqa: E402

cases = [
    (1, "single ltcg 1M, mortgage 20000, proptax 40000", dict(mstat=1, page=40, ltcg=1000000, mortgage=20000, proptax=40000)),
    (2, "single ltcg 1M, mortgage 20000, otheritem 40000", dict(mstat=1, page=40, ltcg=1000000, mortgage=20000, otheritem=40000)),
    (3, "single ltcg 1M, mortgage 30000", dict(mstat=1, page=40, ltcg=1000000, mortgage=30000)),
    (4, "single ltcg 1M, mortgage 20000", dict(mstat=1, page=40, ltcg=1000000, mortgage=20000)),
    (5, "single ltcg 1M, mortgage 60000", dict(mstat=1, page=40, ltcg=1000000, mortgage=60000)),
]
records = []
for cid, _, rec in cases:
    r = dict(taxsimid=cid, year=2026, state=0)
    r.update(rec)
    records.append(r)
res = tsrun.run(records, idtl=2)
with open(HERE / "probe9_in.csv", "w") as fh:
    fh.write(tsrun.to_csv(records))
keys = ["v10", "v17", "v18", "v19", "v27", "v28", "fiitax", "niit"]
with open(HERE / "probe9_out.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "desc"] + [k for k in res[0] if not k.startswith("_")])
    for (cid, desc, _), r in zip(cases, res):
        w.writerow([cid, desc] + [r[k] for k in res[0] if not k.startswith("_")])
for (cid, desc, _), r in zip(cases, res):
    print(cid, desc, " ".join(f"{k}={r[k]:.2f}" for k in keys))
