"""Minimal standard-library runner for NBER's TAXSIM test build (taxsimtest-osx.exe).

run(records, idtl=2) writes the records as a TAXSIM csv on stdin and parses the csv reply.
Each record is a dict of TAXSIM input names to numbers. Every record is sent with the same
column list (missing values become 0), as the TAXSIM page requires ("No missing value codes").
"""
import csv
import io
import subprocess
from pathlib import Path

BINARY = Path(
    "INPUT/taxsim/taxsimtest-osx.exe"
)

INPUT_ORDER = [
    "taxsimid", "year", "state", "mstat", "page", "sage", "depx",
    "age1", "age2", "age3", "age4", "age5", "age6", "age7", "age8",
    "pwages", "swages", "psemp", "ssemp", "dividends", "intrec", "stcg", "ltcg",
    "otherprop", "nonprop", "pensions", "gssi", "pui", "sui", "transfers", "rentpaid",
    "proptax", "otheritem", "childcare", "mortgage", "scorp", "pbusinc", "sbusinc",
    "pprofinc", "sprofinc", "idtl",
]


def fmt(v):
    if isinstance(v, float):
        s = f"{v:.2f}"
        return s
    return str(v)


def to_csv(records, idtl=2, namelist=None):
    cols = [c for c in INPUT_ORDER if c != "idtl"]
    extra = sorted({k for r in records for k in r} - set(cols) - {"idtl"})
    if extra:
        raise ValueError(f"unknown TAXSIM inputs: {extra}")
    out = io.StringIO()
    if namelist:
        out.write(namelist.strip() + "\n")
    out.write(",".join(cols + ["idtl"]) + "\n")
    for r in records:
        row = [fmt(r.get(c, 0)) for c in cols] + [str(idtl)]
        out.write(",".join(row) + "\n")
    return out.getvalue()


def run(records, idtl=2, namelist=None, raw=False):
    text = to_csv(records, idtl=idtl, namelist=namelist)
    p = subprocess.run([str(BINARY)], input=text, capture_output=True, text=True, timeout=120)
    if raw:
        return text, p.stdout, p.stderr
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("taxsimid"):
        raise RuntimeError(f"no output header; stdout={p.stdout[-3000:]!r} stderr={p.stderr!r}")
    header = [h.strip().strip('"') for h in next(csv.reader([lines[0]]))]
    res = []
    messages = []
    for ln in lines[1:]:
        row = next(csv.reader([ln]))
        try:
            float(row[0])
            ok = len(row) == len(header)
        except ValueError:
            ok = False
        if not ok:
            messages.append(ln)
            continue
        d = {}
        for h, v in zip(header, row):
            try:
                d[h] = float(v)
            except ValueError:
                d[h] = v
        res.append(d)
    ids_in = [float(r.get("taxsimid", 0)) for r in records]
    ids_out = [r["taxsimid"] for r in res]
    if ids_in != ids_out:
        raise RuntimeError(
            f"TAXSIM returned {len(res)} rows for {len(records)} records (ids differ); "
            f"messages={messages[:40]!r} stderr={p.stderr!r}"
        )
    if messages:
        res[-1]["_messages"] = messages
    return res
