"""Run PolicyBench households through Tax-Calculator at its own current law.

  envs/tc690/bin/python scripts/run_taxcalc.py --scenarios <scenarios.csv> --year 2026 \
      [--shared results/shared/<file>.csv] --out results/taxcalc/<name>.csv

Each household becomes one filing unit through keycheck.map_taxcalc (the stated facts, plus
the shared state and local tax amount, e18400, when --shared is given).
Tax-Calculator runs one year with no extrapolation: Records(data, start_year=year,
gfactors=None, weights=None) leaves every input as given (taxcalc/data.py:87-125).

The default policy draws a seeded lottery for claiming the EITC and the refundable child
tax credit (calcfunctions.py, "Credit claiming logic"; records.py:197-199). This check
compares liabilities under the law, so it sets eitc_claim_prob_scale and
actc_claim_prob_scale to 9e99, which the code documents as "always claim credit", and
both claim_prob_min to 1. Records runs with exact_calculations=True, so phase-outs step
as the statute and forms do.

Four passes: the IRA deduction, the student loan interest deduction and the saver's
credit are amounts Tax-Calculator takes as given, and each depends on Tax-Calculator's
own adjusted gross income (keycheck/map_taxcalc.py: after_pass).

Notes that bear only on itemized deductions (keycheck.map_taxcalc.itemizer_notes: the
shared state and local tax amount and the unit's itemized readings) are kept only for
units Tax-Calculator itemizes in the final pass (out_c04470 > 0).

Inputs that only the larger draw's facts fill (keycheck/map_taxcalc.py: e03270, e03300,
e58990, e24515, e24518, PT_binc_w2_wages) enter a row only when non-zero, so a run of the
board's households keeps its `in_*` columns and a run of the draw has those extra ones.

Output: one row per household. Columns `in_*` are the inputs sent, `out_*` every
calculated variable, `unexpressed` and `map_computed` the map's notes (joined with
" || "), and four `q_*`
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

# Notes can contain ";"; scripts/build_answers.py splits on this separator.
SEPARATOR = " || "


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

    def calculate(rows: list[dict]):
        frame = pd.DataFrame(rows).fillna(0)
        frame["RECID"] = range(1, len(frame) + 1)
        frame["FLPDYR"] = args.year
        records = Records(
            data=frame, start_year=args.year, gfactors=None, weights=None,
            exact_calculations=True,
        )
        policy = Policy()
        policy.implement_reform(
            {
                "eitc_claim_prob_scale": {args.year: 9e99},
                "actc_claim_prob_scale": {args.year: 9e99},
                "eitc_claim_prob_min": {args.year: 1.0},
                "actc_claim_prob_min": {args.year: 1.0},
            }
        )
        policy.set_year(args.year)
        calculator = Calculator(policy=policy, records=records)
        if calculator.current_year != args.year:
            raise SystemExit(f"calculator is at {calculator.current_year}, not {args.year}")
        calculator.calc_all()
        return frame, calculator

    households = H.load(args.scenarios)
    shared = read_shared(args.shared)
    rows, units, unexpressed, computed = [], [], [], []
    for household in households:
        row, unit, notes, made = map_taxcalc.row(household, args.year, shared.get(household["id"]))
        rows.append(row)
        units.append(unit)
        unexpressed.append(notes)
        computed.append(made)
    # Passes 1 to 3 each fix the income measure of one amount Tax-Calculator takes as given.
    for pass_number in (1, 2, 3):
        _, calculator = calculate(rows)
        agi = np.asarray(calculator.array("c00100"))
        rows = [
            map_taxcalc.after_pass(pass_number, row, unit, float(agi[i]), computed[i])
            for i, (row, unit) in enumerate(zip(rows, units))
        ]
    frame, calculator = calculate(rows)

    variables = json.loads((Path(taxcalc.__file__).parent / "records_variables.json").read_text())
    calc_names = sorted(variables["calc"])
    out = pd.DataFrame({"case_id": [u.case_id for u in units]})
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

    # Listed members with earnings of their own: their own return, for payroll and
    # self-employment tax only (the board's payroll and self-employment outputs count
    # every member; its income tax outputs count the head's return).
    members = [
        (index, member) for index, unit in enumerate(units) for member in unit.members_with_own_payroll
    ]
    out["members_fed_employee_payroll_tax"] = 0.0
    out["members_self_employment_tax"] = 0.0
    if members:
        _, member_calc = calculate([map_taxcalc.member_row(m, args.year) for _, m in members])
        fica = np.asarray(member_calc.array("ptax_was")) / 2
        setax = np.asarray(member_calc.array("setax"))
        for position, (index, _) in enumerate(members):
            out.loc[index, "members_fed_employee_payroll_tax"] += float(fica[position])
            out.loc[index, "members_self_employment_tax"] += float(setax[position])
        out["q_fed_employee_payroll_tax"] += out["members_fed_employee_payroll_tax"]
        out["q_self_employment_tax"] += out["members_self_employment_tax"]

    itemizes = np.asarray(calculator.array("c04470")) > 0
    for i, unit in enumerate(units):
        if itemizes[i]:
            unexpressed[i] = unexpressed[i] + map_taxcalc.itemizer_notes(unit, shared.get(unit.case_id))
    out["unexpressed"] = [SEPARATOR.join(dict.fromkeys(n)) for n in unexpressed]
    out["map_computed"] = [SEPARATOR.join(dict.fromkeys(n)) for n in computed]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    meta = {
        "taxcalc": taxcalc.__version__,
        "year": args.year,
        "policy": "current law; exact_calculations=True; eitc/actc claim_prob_scale 9e99 and claim_prob_min 1.0",
        "input_map": "keycheck/map_taxcalc.py",
        "input_map_version": map_taxcalc.VERSION,
        "unit_version": map_taxcalc.U.VERSION,
        "shared": str(args.shared) if args.shared else None,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"wrote {len(out)} households to {args.out}")


if __name__ == "__main__":
    main()
