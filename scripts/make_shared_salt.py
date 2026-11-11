"""Write the state and local tax amount the other models take from a PolicyEngine run.

A household states its state, not the state and local income or sales tax it paid, and
neither Tax-Calculator nor this check's TAXSIM runs model it. So both take the amount
the PolicyEngine run of the same households and year computed
(`state_and_local_sales_or_income_tax`), and every answer that rests on it says so
(results/bindings.csv).

  python3 scripts/make_shared_salt.py --pe-run results/pe/board100_pe2.60.0_board_2026.csv \
      --label "policyengine-us 2.60.0, board conventions" \
      --out results/shared/board100_salt_from_pe2.60.0_2026.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

VARIABLE = "state_and_local_sales_or_income_tax"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pe-run", required=True, type=Path)
    parser.add_argument("--label", required=True, help="the run, as the source column names it")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    rows = []
    with open(args.pe_run, newline="") as handle:
        for record in csv.DictReader(handle):
            if record["variable"] == VARIABLE:
                rows.append({
                    "case_id": record["scenario_id"], "name": "salt_income_or_sales_tax",
                    "value": record["value"], "source": f"{args.label}: {VARIABLE}",
                })
    if len({r["case_id"] for r in rows}) != len(rows) or not rows:
        raise SystemExit(f"{args.pe_run}: expected one {VARIABLE} row per household, found {len(rows)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "name", "value", "source"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
