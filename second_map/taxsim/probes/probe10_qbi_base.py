"""Probe 10: does the engine take the SE-tax deduction out of QBI for psemp, pbusinc and pprofinc alike?

The doc (taxsimtest_.txt:636-638) asks for psemp pre-FICA and 'the other QBI eligible amounts' post-FICA.
With wages 100k the QBI deduction is not limited by taxable income, so qbid shows the QBI base.
Run: python3 probes/probe10_qbi_base.py  (writes probes/probe10_in.csv and probes/probe10_out.csv)
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tsrun  # noqa: E402

cases = [
    (1, "single w100k psemp 30k", dict(mstat=1, page=40, pwages=100000, psemp=30000)),
    (2, "single w100k pbusinc 30k", dict(mstat=1, page=40, pwages=100000, pbusinc=30000)),
    (3, "single w100k pprofinc 30k", dict(mstat=1, page=40, pwages=100000, pprofinc=30000)),
    (4, "single w100k scorp 30k", dict(mstat=1, page=40, pwages=100000, scorp=30000)),
    (5, "single w100k pprofinc 3k", dict(mstat=1, page=40, pwages=100000, pprofinc=3000)),
    (6, "single w100k psemp 3k", dict(mstat=1, page=40, pwages=100000, psemp=3000)),
]
records = []
for cid, _, rec in cases:
    r = dict(taxsimid=cid, year=2026, state=0)
    r.update(rec)
    records.append(r)
res = tsrun.run(records, idtl=2)
with open(HERE / "probe10_in.csv", "w") as fh:
    fh.write(tsrun.to_csv(records))
cols = [k for k in res[0] if not k.startswith("_")]
with open(HERE / "probe10_out.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "desc"] + cols)
    for (cid, desc, _), r in zip(cases, res):
        w.writerow([cid, desc] + [r[k] for k in cols])
for (cid, desc, _), r in zip(cases, res):
    print(cid, desc, " ".join(f"{k}={r[k]:.2f}" for k in ("v10", "v18", "qbid", "tfica", "fiitax")))
