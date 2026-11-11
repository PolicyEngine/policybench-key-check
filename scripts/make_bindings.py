"""Write results/bindings.csv: for each household in each run, how the run was bound to it.

One row per case and run (see README, "Bindings"). A binding says which input map turned
the household's stated facts into the model's inputs and who wrote it, what the map did
for this household, which stated facts the model could not take, which amounts this
repo computed from the statute because the model takes them as given, and which inputs
came from another run. Two runs share a lineage where they share an engine, a convention
file, an input map or an input that another run computed, so these columns are what a
reader needs to decide which agreements are independent.

  python3 scripts/make_bindings.py --runs results/runs.csv --out results/bindings.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = (
    "case_set", "case_id", "run", "model", "release", "period",
    "input_map", "input_map_version", "input_map_author",
    "records_sent", "model_itemizes",
    "inputs_from_other_runs", "input_from_other_run_bears_on_answer",
    "unexpressed_facts", "map_computed",
)
SEPARATOR = " || "


def read(path: Path) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def positive(row: dict, column: str) -> bool:
    try:
        return float(row.get(column, "") or 0) > 0
    except ValueError:
        return False


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--case-set", default="board-100")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--answers", type=Path, default=Path("results/answers.csv"))
    args = parser.parse_args(argv)

    rows = []
    for run in read(args.runs):
        source = args.root / run["source"]
        base = {
            "case_set": args.case_set, "run": run["run"], "model": run["model"],
            "release": run["release"], "period": run["period"],
            "input_map_author": run.get("input_map_author", ""),
        }
        if run["model"] == "policyengine-us":
            # The key and its reruns: PolicyBench's own builder states every fact to the engine.
            if run["run"].startswith("pb-reference"):
                cases = sorted({r["case_id"] for r in read(args.answers) if r["run"] == run["run"]})
            else:
                cases = sorted({r["scenario_id"] for r in read(source)})
            for case in cases:
                rows.append({
                    **base, "case_id": case, "input_map": run["input_map"], "input_map_version": "PolicyBench c7ede86c",
                    "records_sent": "one household situation", "model_itemizes": "",
                    "inputs_from_other_runs": "", "input_from_other_run_bears_on_answer": "false",
                    "unexpressed_facts": "", "map_computed": "",
                })
            continue
        meta = json.loads(source.with_suffix(".meta.json").read_text())
        shared = {r["case_id"]: r for r in read(args.root / meta["shared"])} if meta.get("shared") else {}
        shared_run = run.get("inputs_from_other_runs", "").rpartition("from ")[2]
        for r in read(source):
            case = r["case_id"]
            if run["model"] == "taxcalc":
                itemizes = positive(r, "out_c04470")
                records = "one record; the last of four passes (the earlier passes give the AGI that limits the IRA deduction, the student loan interest deduction and the saver's credit)"
            else:
                itemizes = positive(r, "out_v17")
                second = r.get("out_b_fiitax", "") not in ("", "nan")
                records = "record A (income tax and payroll tax) and a run with self-employment income zeroed (splits self-employment tax from payroll tax)"
                if second:
                    records += "; record B (the EITC's children, where they differ from the children under 17)"
            given = shared.get(case)
            from_other = ""
            if given:
                from_other = f"state and local income or sales tax paid = {float(given['value']):.2f}, computed by run {shared_run}" if shared_run else f"state and local income or sales tax paid = {float(given['value']):.2f}, computed by {given['source']}"
            rows.append({
                **base, "case_id": case,
                "input_map": meta["input_map"] + " on keycheck/unit.py",
                "input_map_version": f"{meta['input_map_version']} on {meta['unit_version']}",
                "records_sent": records, "model_itemizes": str(itemizes).lower(),
                "inputs_from_other_runs": from_other,
                "input_from_other_run_bears_on_answer": str(bool(given) and itemizes).lower(),
                "unexpressed_facts": r.get("unexpressed", ""), "map_computed": r.get("map_computed", ""),
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
