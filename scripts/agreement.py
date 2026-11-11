"""Classify agreement among models for each household and quantity.

  python3 scripts/agreement.py --answers results/answers.csv --case-set board-100 \
      --key pb-reference-2.60.0 --key-fallback pe-2.60.0-board-2026 \
      --others taxcalc-6.9.0-2026 taxsim-cd2026110117-2026 \
      [--exclusions <reference_exclusions.json>] --out-prefix results/agreement/board100_2026

Two answers agree when they differ by no more than the tolerance ($1, the board's
exact-match rule for amounts). With three answers a household's quantity is:
  all_agree            the largest and smallest answers are within the tolerance
  two_agree:<model>    exactly one model stands apart from two that agree
  all_differ           no two answers are within the tolerance
(two answers can each sit within the tolerance of a third and not of each other; that is
counted as chain and listed). A model with no answer for the quantity leaves a two-model
comparison: pair_agree:<missing> or pair_differ:<missing>.

Writes <out-prefix>.csv (one row per household and quantity) and <out-prefix>.md (shares).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

LINES = (
    "federal_income_tax_before_refundable_credits",
    "federal_refundable_credits",
    "self_employment_tax",
    "federal_employee_payroll_tax",
)
BOARD_OUTPUT = {"federal_employee_payroll_tax": "payroll_tax"}


def classify(values: dict[str, float | None], tolerance: float) -> str:
    present = {m: v for m, v in values.items() if v is not None}
    missing = [m for m, v in values.items() if v is None]
    models = list(present)
    if len(models) <= 1:
        return "one_answer"
    if len(models) == 2:
        a, b = models
        verdict = "pair_agree" if abs(present[a] - present[b]) <= tolerance else "pair_differ"
        return f"{verdict}:{'+'.join(missing)}"
    close = {
        (a, b): abs(present[a] - present[b]) <= tolerance
        for i, a in enumerate(models)
        for b in models[i + 1:]
    }
    if max(present.values()) - min(present.values()) <= tolerance:
        return "all_agree"
    agreeing = [pair for pair, ok in close.items() if ok]
    if not agreeing:
        return "all_differ"
    if len(agreeing) == 1:
        odd = next(m for m in models if m not in agreeing[0])
        return f"two_agree:{odd}"
    return "chain"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument("--case-set", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--key-fallback")
    parser.add_argument("--others", nargs="+", required=True)
    parser.add_argument("--exclusions", type=Path)
    parser.add_argument("--tolerance", type=float, default=1.0)
    parser.add_argument("--out-prefix", required=True, type=Path)
    args = parser.parse_args(argv)

    answers = {}
    model_of = {}
    with open(args.answers, newline="") as handle:
        for row in csv.DictReader(handle):
            if row["case_set"] != args.case_set:
                continue
            answers[(row["run"], row["case_id"], row["quantity"])] = row
            model_of[row["run"]] = row["model"]
    excluded = set()
    if args.exclusions:
        for record in json.loads(args.exclusions.read_text())["exclusions"]:
            excluded.add((record["scenario_id"], record["variable"]))

    cases = sorted({k[1] for k in answers if k[0] in (args.key, args.key_fallback)})
    names = {args.key: "policyengine"}
    for run in args.others:
        names[run] = model_of[run]
    detail = []
    for quantity in LINES:
        for case in cases:
            key_row = answers.get((args.key, case, quantity))
            key_run = args.key
            if (key_row is None or key_row["status"] != "ok") and args.key_fallback:
                key_row = answers.get((args.key_fallback, case, quantity))
                key_run = args.key_fallback
            values, notes = {}, []
            values["policyengine"] = float(key_row["value"]) if key_row and key_row["status"] == "ok" else None
            for run in args.others:
                row = answers.get((run, case, quantity))
                ok = row is not None and row["status"] == "ok"
                values[names[run]] = float(row["value"]) if ok else None
                if row is not None and row["unexpressed_facts"]:
                    notes.append(f"{names[run]}: {row['unexpressed_facts']}")
                if row is not None and row["map_computed"]:
                    notes.append(f"{names[run]} (map computed): {row['map_computed']}")
            board_output = BOARD_OUTPUT.get(quantity, quantity)
            record = {
                "case_id": case,
                "quantity": quantity,
                "key_run": key_run,
                "class": classify(values, args.tolerance),
                "board_scores_it": "no" if (case, board_output) in excluded else "yes",
                "notes": " | ".join(notes),
            }
            for model, value in values.items():
                record[model] = "" if value is None else f"{value:.2f}"
            detail.append(record)

    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    fields = ["case_id", "quantity", "key_run", "class", "board_scores_it", *names.values(), "notes"]
    with open(args.out_prefix.with_suffix(".csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(detail)

    by_quantity = defaultdict(Counter)
    for record in detail:
        by_quantity[record["quantity"]][record["class"]] += 1
    classes = sorted({c for counts in by_quantity.values() for c in counts})
    lines = [
        f"Agreement within ${args.tolerance:g}, {args.case_set}: key {args.key}"
        + (f" (fallback {args.key_fallback})" if args.key_fallback else "")
        + f"; others {', '.join(args.others)}",
        "",
        "| Quantity | Households | " + " | ".join(classes) + " |",
        "|---|---:|" + "---:|" * len(classes),
    ]
    for quantity in LINES:
        counts = by_quantity[quantity]
        total = sum(counts.values())
        lines.append(
            f"| {quantity} | {total} | " + " | ".join(str(counts.get(c, 0)) for c in classes) + " |"
        )
    args.out_prefix.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
