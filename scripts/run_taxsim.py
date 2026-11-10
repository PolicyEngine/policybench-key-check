"""Run PolicyBench households through NBER's TAXSIM binary.

  python3 scripts/run_taxsim.py --scenarios <scenarios.csv> --year 2026 \
      --binary work/nber/taxsimtest-osx.exe [--shared results/shared/<file>.csv] \
      --out results/taxsim/<name>.csv

Each household becomes one TAXSIM record through keycheck.map_taxsim (stated facts
only). Four passes, as for Tax-Calculator: TAXSIM takes the IRA deduction, student loan
interest and the itemized medical and charitable amounts as given, and each depends on
TAXSIM's own adjusted gross income (v10).

TAXSIM reports one FICA column for the taxpayer (`tfica`: employee Social Security and
Medicare tax, self-employment tax and Additional Medicare Tax). Two more runs split it:
gross wages with the self-employment boxes as mapped, and the same with those boxes
zeroed. Self-employment tax = (tfica - addmed) - (tfica0 - addmed0).

Output: one row per household. `in_*` the final-pass record, `out_*` TAXSIM's columns,
`unexpressed` and `map_computed` the map's notes, and the board's lines:
  q_fed_tax_before_refundable = fiitax + v25 + actc   (fiitax is after refundable credits
      and holds net investment income tax but not Additional Medicare Tax in this build)
  q_refundable_credits        = v25 + actc
  q_self_employment_tax       = (tfica - addmed) - (tfica0 - addmed0)
  q_fed_employee_payroll_tax  = tfica - q_self_employment_tax
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from keycheck import households as H  # noqa: E402
from keycheck import map_taxsim, taxsim  # noqa: E402


def read_shared(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
    shared: dict[str, dict[str, float]] = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            shared.setdefault(row["case_id"], {})[row["name"]] = float(row["value"])
    return shared


def run_all(records: list[dict], binary: Path) -> tuple[list[dict | None], str, dict[int, str]]:
    """Run every record; a record TAXSIM rejects stops its whole file, so on a failure
    run one at a time and return None for the rejected ones."""
    numbered = [dict(r, taxsimid=i) for i, r in enumerate(records, start=1)]
    try:
        out, stamp = taxsim.run(numbered, binary)
        return out, stamp, {}
    except taxsim.TaxsimError:
        results, errors, stamp = [], {}, ""
        for record in numbered:
            try:
                one, stamp = taxsim.run([record], binary)
                results.append(one[0])
            except taxsim.TaxsimError as error:
                results.append(None)
                errors[record["taxsimid"] - 1] = str(error).replace("\n", " | ")[:400]
        return results, stamp, errors


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--shared", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    households = H.load(args.scenarios)
    shared = read_shared(args.shared)
    records, units, unexpressed, computed, states = [], [], [], [], []
    for household in households:
        record, unit, notes, made = map_taxsim.first_pass(household, args.year, shared.get(household["id"]))
        records.append(record)
        units.append(unit)
        unexpressed.append(notes)
        computed.append(made)
        states.append({})

    errors: dict[int, str] = {}
    for pass_number in (1, 2, 3):
        out, stamp, failed = run_all(records, args.binary)
        errors.update(failed)
        records = [
            record if result is None else map_taxsim.after_pass(
                pass_number, record, unit, result["v10"], computed[i], unexpressed[i], states[i]
            )
            for i, (record, unit, result) in enumerate(zip(records, units, out))
        ]
    final, stamp, failed = run_all(records, args.binary)
    errors.update(failed)

    pairs = [map_taxsim.payroll_records(record, unit) for record, unit in zip(records, units)]
    gross, _, failed_gross = run_all([p[0] for p in pairs], args.binary)
    no_se, _, failed_no_se = run_all([p[1] for p in pairs], args.binary)
    errors.update(failed_gross)
    errors.update(failed_no_se)

    members = [(i, m) for i, unit in enumerate(units) for m in unit.members_with_own_payroll]
    member_payroll = [0.0] * len(units)
    member_se = [0.0] * len(units)
    if members:
        member_pairs = [map_taxsim.member_records(m, args.year) for _, m in members]
        m_full, _, _ = run_all([p[0] for p in member_pairs], args.binary)
        m_none, _, _ = run_all([p[1] for p in member_pairs], args.binary)
        for (index, _), full, none in zip(members, m_full, m_none):
            if full is None or none is None:
                errors[index] = "a member's own record was rejected"
                continue
            se_tax = (full["tfica"] - full["addmed"]) - (none["tfica"] - none["addmed"])
            member_se[index] += se_tax
            member_payroll[index] += none["tfica"] - none["addmed"]

    rows = []
    for i, unit in enumerate(units):
        row = {"case_id": unit.case_id}
        for name, value in records[i].items():
            row[f"in_{name}"] = value
        if i in errors or final[i] is None or gross[i] is None or no_se[i] is None:
            row["status"] = "error"
            row["error"] = errors.get(i, "rejected")
        else:
            result = final[i]
            for name, value in result.items():
                row[f"out_{name}"] = value
            se_tax = (gross[i]["tfica"] - gross[i]["addmed"]) - (no_se[i]["tfica"] - no_se[i]["addmed"])
            row["out_tfica_gross_wages"] = gross[i]["tfica"]
            row["out_addmed_gross_wages"] = gross[i]["addmed"]
            row["out_tfica_no_self_employment"] = no_se[i]["tfica"]
            row["members_fed_employee_payroll_tax"] = member_payroll[i]
            row["members_self_employment_tax"] = member_se[i]
            row["q_fed_tax_before_refundable"] = result["fiitax"] + result["v25"] + result["actc"]
            row["q_refundable_credits"] = result["v25"] + result["actc"]
            row["q_self_employment_tax"] = se_tax + member_se[i]
            row["q_fed_employee_payroll_tax"] = gross[i]["tfica"] - se_tax + member_payroll[i]
            row["status"] = "ok"
        row["unexpressed"] = "; ".join(dict.fromkeys(unexpressed[i]))
        row["map_computed"] = "; ".join(dict.fromkeys(computed[i]))
        rows.append(row)

    fields = list(dict.fromkeys(name for row in rows for name in row))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    meta = {
        "taxsim_build": stamp,
        "binary": args.binary.name,
        "year": args.year,
        "dependents_path": "counts (depx, dep13, dep17, dep18)" if args.year >= 2026 else "ages (age1..)",
        "input_map": "keycheck/map_taxsim.py",
        "input_map_version": map_taxsim.VERSION,
        "unit_version": map_taxsim.U.VERSION,
        "shared": str(args.shared) if args.shared else None,
        "rejected_records": len(errors),
    }
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"wrote {len(rows)} households to {args.out}; {len(errors)} rejected")


if __name__ == "__main__":
    main()
