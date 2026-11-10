"""Run PolicyBench households through Tax-Calculator at its own current law.

  envs/tc690/bin/python scripts/run_taxcalc.py --scenarios <scenarios.csv> --year 2026 \
      [--shared results/shared/<file>.csv] --out results/taxcalc/<name>.csv

Each household becomes one filing unit through keycheck.map_taxcalc (stated facts only).
Tax-Calculator runs one year with no extrapolation: Records(data, start_year=year,
gfactors=None, weights=None) leaves every input as given (taxcalc/data.py:87-125).

The default policy draws a seeded lottery for claiming the EITC and the refundable child
tax credit (calcfunctions.py, "Credit claiming logic"; records.py:197-199). This check
compares liabilities under the law, so it sets eitc_claim_prob_scale and
actc_claim_prob_scale to 9e99, which the code documents as "always claim credit".

Output: one row per household. Columns `in_*` are the inputs sent, `out_*` every
calculated variable, `unexpressed` and `map_computed` the map's notes, and four `q_*`
columns the board's lines as Tax-Calculator's variables give them:
  q_fed_tax_before_refundable = c09200 - setax - ptax_amc   (c09200 holds other taxes,
      net investment income tax, self-employment tax and Additional Medicare Tax:
      calcfunctions.py C1040)
  q_refundable_credits        = refund
  q_self_employment_tax       = setax
  q_fed_employee_payroll_tax  = ptax_was / 2 + ptax_amc     (ptax_was holds both shares of
      OASDI and HI on wages: calcfunctions.py EI_PayrollTax)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from keycheck import households as H  # noqa: E402
from keycheck import map_taxcalc  # noqa: E402


def read_shared(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
    shared: dict[str, dict[str, float]] = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            shared.setdefault(row["case_id"], {})[row["name"]] = float(row["value"])
    return shared


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--shared", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    import taxcalc
    from taxcalc import Calculator, Policy, Records

    households = H.load(args.scenarios)
    shared = read_shared(args.shared)
    rows, notes = [], []
    for index, household in enumerate(households, start=1):
        row, unexpressed, computed = map_taxcalc.row(
            household, args.year, shared.get(household["id"], {})
        )
        row["RECID"] = index
        row["FLPDYR"] = args.year
        rows.append(row)
        notes.append((household["id"], unexpressed, computed))
    frame = pd.DataFrame(rows).fillna(0)

    records = Records(data=frame, start_year=args.year, gfactors=None, weights=None)
    policy = Policy()
    policy.adjust(
        {
            "eitc_claim_prob_scale": [{"year": args.year, "value": 9e99}],
            "actc_claim_prob_scale": [{"year": args.year, "value": 9e99}],
        },
        print_warnings=False,
    )
    policy.set_year(args.year)
    calculator = Calculator(policy=policy, records=records)
    if calculator.current_year != args.year:
        raise SystemExit(f"calculator is at {calculator.current_year}, not {args.year}")
    calculator.calc_all()

    calc_names = sorted(Records.CALCULATED_VARS)
    out = pd.DataFrame({"case_id": [n[0] for n in notes]})
    for name in frame.columns:
        out[f"in_{name}"] = frame[name].to_numpy()
    for name in calc_names:
        values = np.asarray(calculator.array(name))
        if values.dtype.kind in "biuf":
            out[f"out_{name}"] = values
    out["q_fed_tax_before_refundable"] = out["out_c09200"] - out["out_setax"] - out["out_ptax_amc"]
    out["q_refundable_credits"] = out["out_refund"]
    out["q_self_employment_tax"] = out["out_setax"]
    out["q_fed_employee_payroll_tax"] = out["out_ptax_was"] / 2 + out["out_ptax_amc"]
    out["unexpressed"] = ["; ".join(n[1]) for n in notes]
    out["map_computed"] = ["; ".join(n[2]) for n in notes]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    meta = {
        "taxcalc": taxcalc.__version__,
        "year": args.year,
        "policy": "current law; eitc_claim_prob_scale and actc_claim_prob_scale set to 9e99",
        "input_map": "keycheck/map_taxcalc.py",
        "input_map_version": map_taxcalc.VERSION,
        "shared": str(args.shared) if args.shared else None,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"wrote {len(out)} households to {args.out}")


if __name__ == "__main__":
    main()
