"""Fill the README's tables from the committed result files.

Each table in README.md sits between `<!-- generated:NAME -->` and `<!-- /generated -->`.
This script recounts every table from the file it rests on and rewrites the blocks, so a
number in the README cannot drift from the data.

  python3 scripts/make_readme_tables.py            # rewrite README.md in place
  python3 scripts/make_readme_tables.py --check    # exit 1 if a block is out of date
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINES = (
    ("federal_income_tax_before_refundable_credits", "Tax before refundable credits"),
    ("federal_refundable_credits", "Refundable credits"),
    ("self_employment_tax", "Self-employment tax"),
    ("federal_employee_payroll_tax", "Federal employee payroll tax"),
)
CLASSES = (
    ("all_agree", "All three agree"),
    ("two_agree:policyengine", "PolicyEngine apart"),
    ("two_agree:taxcalc", "Tax-Calculator apart"),
    ("two_agree:taxsim", "TAXSIM apart"),
    ("all_differ", "All differ"),
)
STATUSES = (
    ("reproduced", "Reproduced by a run of another lineage"),
    ("contested", "Contested"),
    ("resting_on_one_model", "Resting on PolicyEngine alone"),
)


def read(path: str) -> list[dict]:
    with open(ROOT / path, newline="") as handle:
        return list(csv.DictReader(handle))


def table(header: list[str], rows: list[list], align: str | None = None) -> str:
    align = align or "l" + "r" * (len(header) - 1)
    rule = "|" + "|".join("---:" if a == "r" else "---" for a in align) + "|"
    out = ["| " + " | ".join(header) + " |", rule]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def agreement(path: str) -> str:
    rows = read(path)
    known = {key for key, _ in CLASSES}
    other = sorted({r["class"] for r in rows} - known)
    header = ["Line", *(label for _, label in CLASSES), *other]
    body = []
    for line, label in LINES:
        counts = Counter(r["class"] for r in rows if r["quantity"] == line)
        if sum(counts.values()) != 100:
            raise SystemExit(f"{path}: {line} has {sum(counts.values())} households")
        body.append([label, *(counts[key] for key, _ in CLASSES), *(counts[key] for key in other)])
    return table(header, body)


def cell_status() -> str:
    rows = read("results/cell_status.csv")
    body = []
    for key, label in STATUSES:
        mine = [r for r in rows if r["status"] == key]
        trivial = sum(1 for r in mine if r["trivial"] == "true")
        body.append([label, len(mine), sum(1 for r in mine if r["board_scores_it"] == "yes"), trivial])
    body.append(["Total", len(rows), sum(1 for r in rows if r["board_scores_it"] == "yes"),
                 sum(1 for r in rows if r["trivial"] == "true")])
    return table(["Status", "Cells", "Of which the board scores", "Of which trivial zeros"], body)


def cell_status_by_quantity() -> str:
    rows = read("results/cell_status.csv")
    quantities = [*LINES, ("state_employee_payroll_tax", "State employee payroll tax")]
    body = []
    for line, label in quantities:
        counts = Counter(r["status"] for r in rows if r["quantity"] == line)
        body.append([label, *(counts[key] for key, _ in STATUSES)])
    return table(["Quantity", *(label for _, label in STATUSES)], body)


def draw() -> str:
    rows = [r for r in read("results/draw1000_summary.csv") if r["section"] == "agreement"]
    body = []
    for line, label in LINES:
        counts = {r["class"]: int(r["count"]) for r in rows if r["line"] == line}
        body.append([label, *(counts.get(key, 0) for key, _ in CLASSES)])
    return table(["Line", *(label for _, label in CLASSES)], body)


def second_map() -> str:
    body = []
    for engine, label in (("taxcalc", "Tax-Calculator"), ("taxsim", "TAXSIM")):
        rows = read(f"results/second_map/{engine}_answers_diff.csv")
        for line, line_label in LINES:
            mine = [r for r in rows if r["line"] == line]
            pairs = Counter((r["first_agrees_key"], r["second_agrees_key"]) for r in mine)
            body.append([label, line_label, pairs[("yes", "yes")], pairs[("yes", "no")],
                         pairs[("no", "yes")], pairs[("no", "no")]])
    return table(["Engine", "Line", "Both maps give the key", "Only the first", "Only the second", "Neither"],
                 body, "llrrrr")


def facts() -> str:
    body = []
    for path, label in (("maps/board_facts.csv", "The board's 100 households"),
                        ("maps/draw_facts.csv", "The draw's 1,000 households")):
        rows = [r for r in read(path) if r["entity"] != "structure" and r["fact"] != "employment_income"]
        federal = [r for r in rows if r["effect_on_the_four_lines_in_the_key"] == "federal"]
        has = lambda rs, col: sum(1 for r in rs if r[col])  # noqa: E731
        none = sum(1 for r in federal if not (r["axiom_oracles_concept_id"] or r["taxcalc_field"] or r["taxsim_field"]))
        body.append([label, len(rows), len(federal), has(federal, "axiom_oracles_concept_id"),
                     has(federal, "taxcalc_field"), has(federal, "taxsim_field"), none])
    return table(["Households", "Stated inputs", "Can reach a federal line", "Of those: axiom-oracles concept id",
                  "Tax-Calculator field", "TAXSIM field", "None of the three"], body)


def causes() -> str:
    rows = read("results/causes.csv")
    cells = read("results/cause_cells.csv")
    with_cells = Counter()
    for kind in {r["kind"] for r in rows}:
        ids = {r["cause_id"] for r in rows if r["kind"] == kind}
        with_cells[kind] = len({(c["case_id"], c["quantity"], c["table"]) for c in cells if c["cause_id"] in ids})
    counts = Counter(r["kind"] for r in rows)
    body = [[f"`{kind}`", counts[kind], with_cells[kind]] for kind in sorted(counts, key=lambda k: (-counts[k], k))]
    body.append(["Total", len(rows), len({(c["case_id"], c["quantity"], c["table"]) for c in cells})])
    return table(["Kind of cause", "Entries", "Household-line-table cells they move"], body)


def contested_scored() -> str:
    names = dict(LINES)
    rows = [r for r in read("results/cell_status.csv") if r["status"] == "contested" and r["board_scores_it"] == "yes"]
    body = [[r["case_id"], names.get(r["quantity"], r["quantity"]), f"{float(r['key_value']):,.2f}",
             r["contested_reasons"].replace(";", "; "), ", ".join(f"`{c}`" for c in r["contesting_cause_ids"].split(";") if c)]
            for r in sorted(rows, key=lambda r: (r["case_id"], r["quantity"]))]
    if not body:
        return "No scored cell is contested."
    return table(["Household", "Line", "Key's answer", "Why contested", "Cause entries"], body, "llrll")


def shared_salt() -> str:
    rows = read("results/bindings.csv")
    body = []
    for run in sorted({r["run"] for r in rows if r["model"] != "policyengine-us"}):
        mine = [r for r in rows if r["run"] == run]
        body.append([f"`{run}`", sum(1 for r in mine if r["model_itemizes"] == "true"),
                     sum(1 for r in mine if r["map_computed"]), sum(1 for r in mine if r["unexpressed_facts"])])
    return table(["Run", "Households where the model itemizes on the shared amount",
                  "Households with an amount this repo computed from statute",
                  "Households with a fact the model could not take or a named reading"], body)


BLOCKS = {
    "board-2026-key": lambda: agreement("results/agreement/board100_2026_key.csv"),
    "board-2026-rerun": lambda: agreement("results/agreement/board100_2026_rerun.csv"),
    "board-2025": lambda: agreement("results/agreement/board100_2025.csv"),
    "cell-status": cell_status,
    "cell-status-by-quantity": cell_status_by_quantity,
    "draw-1000": draw,
    "second-map": second_map,
    "facts": facts,
    "causes": causes,
    "contested-scored": contested_scored,
    "shared-inputs": shared_salt,
}
PATTERN = re.compile(r"(<!-- generated:([a-z0-9-]+) -->\n)(.*?)(\n<!-- /generated -->)", re.S)


def render(text: str) -> tuple[str, list[str]]:
    seen = []

    def fill(match: re.Match) -> str:
        name = match.group(2)
        if name not in BLOCKS:
            raise SystemExit(f"README names an unknown block: {name}")
        seen.append(name)
        return match.group(1) + BLOCKS[name]() + match.group(4)

    return PATTERN.sub(fill, text), seen


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    args = parser.parse_args(argv)
    text = args.readme.read_text()
    new, seen = render(text)
    if args.check:
        if new != text:
            sys.exit("README tables are out of date: run python3 scripts/make_readme_tables.py")
        print(f"{len(seen)} README tables are current")
        return
    args.readme.write_text(new)
    print(f"filled {len(seen)} tables: {', '.join(seen)}")


if __name__ == "__main__":
    main()
