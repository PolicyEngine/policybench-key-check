"""Assemble every model's answers into one long table.

One row per case, quantity, model and run (see README, "The answers table"). Sources:
  --reference RUN=reference_outputs.csv   the board's committed key (four board outputs)
  --pe RUN=results/pe/<file>.csv          scripts/run_pe.py output (long, with parts)
  --taxcalc RUN=results/taxcalc/<file>.csv
  --taxsim RUN=results/taxsim/<file>.csv
Every RUN must be a row of results/runs.csv, which says what the run is.

  python3 scripts/build_answers.py --case-set board-100 --runs results/runs.csv \
      --reference pb-reference-2.60.0=<path> --pe pe-2.60.0-board-2026=<path> ... \
      --out results/answers.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

QUANTITIES = (
    "federal_income_tax_before_refundable_credits",
    "federal_refundable_credits",
    "self_employment_tax",
    "federal_employee_payroll_tax",
    "state_employee_payroll_tax",
    "payroll_tax",
)
# Which group of stated facts bears on which quantity: the maps tag each fact a model
# could not take with one of these groups.
GROUP = {
    "federal_income_tax_before_refundable_credits": "income_tax",
    "federal_refundable_credits": "income_tax",
    "self_employment_tax": "self_employment",
    "federal_employee_payroll_tax": "payroll",
    "state_employee_payroll_tax": "payroll",
    "payroll_tax": "payroll",
}
WIDE = {
    "federal_income_tax_before_refundable_credits": "q_fed_tax_before_refundable",
    "federal_refundable_credits": "q_refundable_credits",
    "self_employment_tax": "q_self_employment_tax",
    "federal_employee_payroll_tax": "q_fed_employee_payroll_tax",
}
FIELDS = (
    "case_set", "case_id", "period", "quantity", "model", "run", "value", "status",
    "unexpressed_facts", "map_computed",
)


def pairs(items):
    out = {}
    for item in items or []:
        run, _, path = item.partition("=")
        out[run] = Path(path)
    return out


# The runners join a row's notes with this separator; a note can contain ";".
SEPARATOR = " || "


def tagged(text: str, group: str) -> str:
    """The notes of one group, from SEPARATOR-joined 'group: note' entries."""
    keep = []
    for entry in (e.strip() for e in (text or "").split(SEPARATOR)):
        if not entry:
            continue
        tag, _, note = entry.partition(":")
        if tag.strip() in (group, "all"):
            keep.append(note.strip())
    return SEPARATOR.join(keep)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-set", required=True)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--reference", action="append")
    parser.add_argument("--pe", action="append")
    parser.add_argument("--taxcalc", action="append")
    parser.add_argument("--taxsim", action="append")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args(argv)

    with open(args.runs, newline="") as handle:
        runs = {row["run"]: row for row in csv.DictReader(handle)}
    rows = []

    def add(run, case_id, quantity, value, status="ok", unexpressed="", computed=""):
        if run not in runs:
            raise SystemExit(f"{run} is not in {args.runs}")
        rows.append(
            {
                "case_set": args.case_set,
                "case_id": case_id,
                "period": runs[run]["period"],
                "quantity": quantity,
                "model": runs[run]["model"],
                "run": run,
                "value": "" if value is None else f"{float(value):.2f}",
                "status": status,
                "unexpressed_facts": unexpressed,
                "map_computed": computed,
            }
        )

    for run, path in pairs(args.reference).items():
        with open(path, newline="") as handle:
            ref = {(r["scenario_id"], r["variable"]): float(r["value"]) for r in csv.DictReader(handle)}
        cases = sorted({k[0] for k in ref})
        for case in cases:
            for quantity in QUANTITIES:
                if (case, quantity) in ref:
                    add(run, case, quantity, ref[(case, quantity)])
                else:
                    add(run, case, quantity, None, "not_published")

    for run, path in pairs(args.pe).items():
        values: dict[tuple[str, str], float] = {}
        with open(path, newline="") as handle:
            for r in csv.DictReader(handle):
                if r["value"] not in ("", "nan"):
                    values[(r["scenario_id"], r["variable"])] = float(r["value"])
        for case in sorted({k[0] for k in values}):
            federal = (
                values[(case, "employee_social_security_tax")]
                + values[(case, "employee_medicare_tax")]
                + values[(case, "additional_medicare_tax")]
            )
            state = values[(case, "employee_state_payroll_tax")]
            total = values[(case, "board:payroll_tax")]
            if abs(federal + state - total) > 0.01:
                raise SystemExit(f"{run} {case}: payroll parts {federal + state} != {total}")
            add(run, case, "federal_income_tax_before_refundable_credits",
                values[(case, "board:federal_income_tax_before_refundable_credits")])
            add(run, case, "federal_refundable_credits", values[(case, "board:federal_refundable_credits")])
            add(run, case, "self_employment_tax", values[(case, "board:self_employment_tax")])
            add(run, case, "federal_employee_payroll_tax", federal)
            add(run, case, "state_employee_payroll_tax", state)
            add(run, case, "payroll_tax", total)

    for source in (args.taxcalc, args.taxsim):
        for run, path in pairs(source).items():
            with open(path, newline="") as handle:
                for r in csv.DictReader(handle):
                    for quantity in QUANTITIES:
                        group = GROUP[quantity]
                        unexpressed = tagged(r.get("unexpressed", ""), group)
                        computed = tagged(r.get("map_computed", ""), group)
                        if quantity not in WIDE:
                            add(run, r["case_id"], quantity, None, "not_covered",
                                "the model has no state payroll taxes")
                        elif r.get(WIDE[quantity], "") in ("", "nan"):
                            add(run, r["case_id"], quantity, None, r.get("status") or "error", unexpressed, computed)
                        else:
                            add(run, r["case_id"], quantity, float(r[WIDE[quantity]]), "ok", unexpressed, computed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append and args.out.exists() else "w"
    with open(args.out, mode, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
