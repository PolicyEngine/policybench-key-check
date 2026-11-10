"""Write one file per household with everything each model was given and answered.

  python3 scripts/make_dossiers.py --scenarios <scenarios.csv> --out results/dossiers

A dossier holds the household's stated facts, the return keycheck/unit.py derives from
them, the committed key and any exclusion record, PolicyEngine's parts, and the inputs
and outputs of each Tax-Calculator and TAXSIM run, so a disagreement can be reconciled
without rerunning anything.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from keycheck import households as H  # noqa: E402
from keycheck import unit as U  # noqa: E402

PE_RUNS = {
    "pe-2.60.0-board-2026": "results/pe/board100_pe2.60.0_board_2026.csv",
    "pe-2.60.0-board-2025": "results/pe/board100_pe2.60.0_board_2025.csv",
    "pe-2.116.15-board-2026": "results/pe/board100_pe2.116.15_board_2026.csv",
    "pe-2.116.15-none-2026": "results/pe/board100_pe2.116.15_none_2026.csv",
}
WIDE_RUNS = {
    "taxcalc-6.9.0-2026": "results/taxcalc/board100_tc6.9.0_2026.csv",
    "taxcalc-6.9.0-2025": "results/taxcalc/board100_tc6.9.0_2025.csv",
    "taxsim-cd2026110117-2026": "results/taxsim/board100_cd2026110117_2026.csv",
    "taxsim-cd2026110117-2025": "results/taxsim/board100_cd2026110117_2025.csv",
}
AGREEMENT = {
    "2026, against the committed key": "results/agreement/board100_2026_key.csv",
    "2026, against the engine rerun": "results/agreement/board100_2026_rerun.csv",
    "2025 law": "results/agreement/board100_2025.csv",
}


def number(text: str):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return text
    return round(value, 2)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--exclusions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    households = {h["id"]: h for h in H.load(args.scenarios)}
    with open(args.reference, newline="") as handle:
        reference = {(r["scenario_id"], r["variable"]): float(r["value"]) for r in csv.DictReader(handle)}
    exclusions: dict[str, list] = {}
    for record in json.loads(args.exclusions.read_text())["exclusions"]:
        exclusions.setdefault(record["scenario_id"], []).append(record)

    pe: dict[str, dict[str, dict]] = {run: {} for run in PE_RUNS}
    for run, path in PE_RUNS.items():
        with open(ROOT / path, newline="") as handle:
            for r in csv.DictReader(handle):
                entry = pe[run].setdefault(r["scenario_id"], {})
                value = number(r["value"])
                persons = json.loads(r["persons"]) if r["persons"] else None
                if persons is not None and r["variable"] != "person_names":
                    if any(p not in (0, 0.0, "") for p in persons):
                        entry[r["variable"]] = {"total": value, "persons": persons}
                elif r["variable"] == "person_names":
                    entry["person_names"] = persons
                elif value not in (0, 0.0):
                    entry[r["variable"]] = value
    wide: dict[str, dict[str, dict]] = {}
    for run, path in WIDE_RUNS.items():
        with open(ROOT / path, newline="") as handle:
            wide[run] = {}
            for r in csv.DictReader(handle):
                keep = {}
                for key, text in r.items():
                    value = number(text)
                    if key in ("unexpressed", "map_computed", "status", "error"):
                        if text:
                            keep[key] = text.split("; ") if key in ("unexpressed", "map_computed") else text
                    elif key.startswith("q_") or value not in (0, 0.0, ""):
                        keep[key] = value
                wide[run][r["case_id"]] = keep
    agreement: dict[str, dict[str, dict]] = {}
    for label, path in AGREEMENT.items():
        with open(ROOT / path, newline="") as handle:
            for r in csv.DictReader(handle):
                agreement.setdefault(r["case_id"], {}).setdefault(label, {})[r["quantity"]] = {
                    k: number(v) for k, v in r.items() if k not in ("case_id", "quantity", "notes")
                }

    args.out.mkdir(parents=True, exist_ok=True)
    for case, household in households.items():
        doc = {
            "case_id": case,
            "stated_facts": household,
            "return_from_stated_facts": {
                str(year): dataclasses.asdict(U.build(household, year)) for year in (2026, 2025)
            },
            "committed_key": {v: reference[(case, v)] for v in (
                "federal_income_tax_before_refundable_credits", "federal_refundable_credits",
                "payroll_tax", "self_employment_tax", "state_income_tax_before_refundable_credits")},
            "board_exclusion_records": exclusions.get(case, []),
            "agreement": agreement.get(case, {}),
            "policyengine": {run: pe[run].get(case, {}) for run in PE_RUNS},
            "other_models": {run: wide[run].get(case, {}) for run in WIDE_RUNS},
        }
        (args.out / f"{case}.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {len(households)} dossiers to {args.out}")


if __name__ == "__main__":
    main()
