"""Tax-Calculator 6.9.0 counterfactual from a dossier's final TC inputs (settings as scripts/run_taxcalc.py:77-96)."""
import json, sys
from pathlib import Path
import pandas as pd
from taxcalc import Calculator, Policy, Records
REPO = Path(__file__).resolve().parents[2]

def tc(case, year, **changes):
    d = json.loads((REPO / f"results/dossiers/{case}.json").read_text())["other_models"][f"taxcalc-6.9.0-{year}"]
    row = {k[3:]: v for k, v in d.items() if k.startswith("in_")}
    for k, v in changes.items():
        row[k] = row.get(k, 0) + v if k.startswith("+") is False and k in row and isinstance(v, str) else v
    frame = pd.DataFrame([row]).fillna(0)
    frame["RECID"] = 1; frame["FLPDYR"] = year
    rec = Records(data=frame, start_year=year, gfactors=None, weights=None, exact_calculations=True)
    pol = Policy()
    pol.implement_reform({"eitc_claim_prob_scale": {year: 9e99}, "actc_claim_prob_scale": {year: 9e99},
                          "eitc_claim_prob_min": {year: 1.0}, "actc_claim_prob_min": {year: 1.0}})
    pol.set_year(year)
    c = Calculator(policy=pol, records=rec); c.calc_all()
    g = lambda n: round(float(c.array(n)[0]), 2)
    line1 = round(g("c09200") - g("setax") - g("ptax_amc"), 2)
    return dict(c00100=g("c00100"), c04800=g("c04800"), standard=g("standard"), c04470=g("c04470"), line1=line1, refund=g("refund"))

if __name__ == "__main__":
    case, year = sys.argv[1], int(sys.argv[2])
    changes = {k: float(v) for k, v in (a.split("=") for a in sys.argv[3:])}
    print(case, year, "base", tc(case, year))
    if changes: print(case, year, changes, tc(case, year, **changes))
