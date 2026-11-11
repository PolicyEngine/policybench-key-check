"""The causes table explains every disagreement on the board's 100 households.

Invariant: for every household, line and table, and every pair of answerers, the
difference between their answers in results/answers.csv equals the difference
between the sums of their amounts in results/cause_cells.csv, within $1.
docs/causes.md defines the kinds and the sign convention.
"""

import csv
import itertools
import re
from collections import defaultdict
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1.0
CASE_SET = "board-100"
LINES = (
    "federal_income_tax_before_refundable_credits",
    "federal_refundable_credits",
    "self_employment_tax",
    "federal_employee_payroll_tax",
)
KINDS = {
    "model-law-departure",
    "model-no-provision",
    "pe-default-unstated-fact",
    "key-decided-value",
    "map-limit",
    "shared-reading",
    "unexplained",
}
ANSWERERS = {"policybench-key", "policyengine-us", "taxcalc", "taxsim"}
LAW_YEARS = {"2026", "2025", "both"}
RUN = {
    ("2026", "policybench-key"): "pb-reference-2.60.0",
    ("2026", "policyengine-us"): "pe-2.60.0-board-2026",
    ("2026", "taxcalc"): "taxcalc-6.9.0-2026",
    ("2026", "taxsim"): "taxsim-cd2026110117-2026",
    ("2025", "policyengine-us"): "pe-2.60.0-board-2025",
    ("2025", "taxcalc"): "taxcalc-6.9.0-2025",
    ("2025", "taxsim"): "taxsim-cd2026110117-2025",
}
TABLES = {
    table: [run for (t, _), run in RUN.items() if t == table] for table in ("2026", "2025")
}
# The key does not publish the employee payroll line; scripts/agreement.py compares the
# engine rerun in its place, and so does this test.
KEY_FALLBACK = {"pb-reference-2.60.0": "pe-2.60.0-board-2026"}
CASE_LIST = re.compile(r"^(scenario_\d{3}(@(2026|2025))?)(;scenario_\d{3}(@(2026|2025))?)*$")
CAUSE_FIELDS = [
    "cause_id", "kind", "answerer", "release_or_build", "fixed_in", "law_years", "quantities",
    "summary", "law", "law_figure", "who_is_right", "existing_report", "evidence", "households",
    "households_shared", "opened_by", "entry_status",
]
CELL_FIELDS = ["cause_id", "case_id", "quantity", "table", "answerer", "run", "amount", "basis"]


def read(path):
    with open(ROOT / path, newline="") as handle:
        return list(csv.DictReader(handle))


ANSWER_ROWS = [r for r in read("results/answers.csv") if r["case_set"] == CASE_SET]
CAUSES = read("results/causes.csv")
CELLS = read("results/cause_cells.csv")
RUNS_CSV = {r["run"] for r in read("results/runs.csv")}


def answer_values(rows):
    values = defaultdict(dict)
    for row in rows:
        if row["status"] == "ok":
            values[(row["case_id"], row["quantity"])][row["run"]] = float(row["value"])
    return values


def cell_sums(cells):
    sums = defaultdict(float)
    for row in cells:
        sums[(row["case_id"], row["quantity"], row["run"])] += float(row["amount"])
    return sums


def residuals(values, sums):
    """(case, line, table, run_a, run_b) -> answer gap less cause gap."""
    out = {}
    for (case, quantity), by_run in values.items():
        if quantity not in LINES:
            continue
        for table, runs in TABLES.items():
            present = {}
            for run in runs:
                value = by_run.get(run)
                if value is None and run in KEY_FALLBACK:
                    value = by_run.get(KEY_FALLBACK[run])
                if value is not None:
                    present[run] = value
            for a, b in itertools.combinations(sorted(present), 2):
                gap = present[a] - present[b]
                explained = sums[(case, quantity, a)] - sums[(case, quantity, b)]
                out[(case, quantity, table, a, b)] = gap - explained
    return out


VALUES = answer_values(ANSWER_ROWS)
RESIDUALS = residuals(VALUES, cell_sums(CELLS))


def test_files_have_the_documented_columns():
    assert list(CAUSES[0]) == CAUSE_FIELDS
    assert list(CELLS[0]) == CELL_FIELDS


def test_the_invariant_covers_every_household_line_and_table():
    cases = {case for case, _ in VALUES}
    assert len(cases) == 100
    # 100 households x 4 lines: 6 pairs in the 2026 table, 3 in 2025.
    assert len(RESIDUALS) == 100 * len(LINES) * (6 + 3)


def test_every_pair_of_answers_differs_by_its_causes():
    bad = {k: round(v, 2) for k, v in RESIDUALS.items() if abs(v) > TOLERANCE}
    assert not bad, bad


@pytest.mark.parametrize(
    "table_file", ["board100_2026_key.csv", "board100_2026_rerun.csv", "board100_2025.csv"]
)
def test_every_cell_not_all_agree_has_a_cause(table_file):
    explained = {(r["case_id"], r["quantity"]) for r in CELLS}
    rows = read(f"results/agreement/{table_file}")
    missing = [
        (r["case_id"], r["quantity"])
        for r in rows
        if r["class"] != "all_agree" and (r["case_id"], r["quantity"]) not in explained
    ]
    assert not missing, missing


def test_cause_ids_match_both_ways():
    ids = [c["cause_id"] for c in CAUSES]
    assert len(ids) == len(set(ids))
    in_cells = {r["cause_id"] for r in CELLS}
    assert in_cells <= set(ids)
    for cause in CAUSES:
        # A cause that moves answers has cell rows; a reading the models share has
        # households and no cell rows.
        assert cause["cause_id"] in in_cells or cause["households_shared"], cause["cause_id"]


def test_no_cell_rows_for_a_cause_that_moves_every_answer_alike():
    # A cause that moves every answer in a table by the same amount leaves no trace in
    # any difference, so it belongs in households_shared, not in cause_cells.
    groups = defaultdict(dict)
    for row in CELLS:
        groups[(row["cause_id"], row["case_id"], row["quantity"], row["table"])][
            row["answerer"]
        ] = float(row["amount"])
    for (cause_id, case, quantity, table), moved in groups.items():
        answerers = {a for (t, a) in RUN if t == table}
        if set(moved) == answerers:
            assert max(moved.values()) - min(moved.values()) > TOLERANCE, (cause_id, case, table)


def test_causes_take_only_defined_values():
    for cause in CAUSES:
        assert cause["kind"] in KINDS, cause
        assert set(cause["answerer"].split(";")) <= ANSWERERS, cause
        assert cause["law_years"] in LAW_YEARS, cause
        assert set(cause["quantities"].split(";")) <= set(LINES), cause
        assert cause["law"].strip(), cause
        assert cause["who_is_right"].strip(), cause
        assert cause["opened_by"].strip(), cause
        assert cause["entry_status"] == "open", cause
        for column in ("households", "households_shared"):
            assert not cause[column] or CASE_LIST.match(cause[column]), (column, cause)


def test_no_unexplained_residual():
    assert not [c for c in CAUSES if c["kind"] == "unexplained"]


def test_cells_take_only_defined_values():
    seen = set()
    for row in CELLS:
        assert row["quantity"] in LINES, row
        assert row["table"] in TABLES, row
        assert row["answerer"] in ANSWERERS, row
        assert row["run"] == RUN[(row["table"], row["answerer"])], row
        assert row["run"] in RUNS_CSV, row
        assert float(row["amount"]) != 0, row
        assert row["basis"].strip(), row
        key = (row["cause_id"], row["case_id"], row["quantity"], row["table"], row["answerer"])
        assert key not in seen, key
        seen.add(key)


def test_cells_agree_with_their_cause():
    causes = {c["cause_id"]: c for c in CAUSES}
    households = defaultdict(set)
    for row in CELLS:
        cause = causes[row["cause_id"]]
        assert row["answerer"] in cause["answerer"].split(";"), row
        assert row["quantity"] in cause["quantities"].split(";"), row
        if cause["law_years"] != "both":
            assert row["table"] == cause["law_years"], row
        households[row["cause_id"]].add(row["case_id"])
    for cause_id, cases in households.items():
        assert set(causes[cause_id]["households"].split(";")) == cases, cause_id


# Properties of the check itself, so a pass means something.

cell_index = st.integers(min_value=0, max_value=len(CELLS) - 1)
big_delta = st.floats(min_value=1.5, max_value=1e5, allow_nan=False).flatmap(
    lambda x: st.sampled_from([x, -x])
)


@settings(max_examples=60, deadline=None)
@given(cell_index, big_delta)
def test_a_wrong_amount_breaks_the_invariant(index, delta):
    cells = [dict(r) for r in CELLS]
    cells[index]["amount"] = str(float(cells[index]["amount"]) + delta)
    moved = residuals(VALUES, cell_sums(cells))
    assert max(abs(v) for v in moved.values()) > TOLERANCE


case_keys = sorted({(case, quantity) for case, quantity in VALUES if quantity in LINES})


@settings(max_examples=60, deadline=None)
@given(
    st.sampled_from(case_keys),
    st.sampled_from(sorted(TABLES)),
    st.floats(min_value=-1e5, max_value=1e5, allow_nan=False),
)
def test_a_cause_shared_by_every_answer_leaves_no_trace(key, table, amount):
    case, quantity = key
    cells = list(CELLS) + [
        {"cause_id": "shared", "case_id": case, "quantity": quantity, "table": table,
         "answerer": answerer, "run": run, "amount": str(amount), "basis": ""}
        for (t, answerer), run in RUN.items()
        if t == table
    ]
    moved = residuals(VALUES, cell_sums(cells))
    for k, v in moved.items():
        assert abs(v - RESIDUALS[k]) < 1e-6 * max(1.0, abs(amount))


# The public account.

DOC = (ROOT / "docs" / "causes.md").read_text()


def test_docs_have_a_section_per_cause_and_define_each_kind():
    for cause in CAUSES:
        assert f"`{cause['cause_id']}`" in DOC, cause["cause_id"]
    for kind in KINDS:
        assert f"`{kind}`" in DOC, kind


def test_docs_table_lists_every_cell_not_all_agree_in_the_key_table():
    for row in read("results/agreement/board100_2026_key.csv"):
        if row["class"] != "all_agree":
            assert re.search(rf"\| {row['case_id'][-3:]} \| {row['quantity']} \|", DOC), row


def test_docs_use_the_cell_status_vocabulary():
    for word in ("confirmed", "verified", "settled", "closed"):
        assert not re.search(rf"\b{word}\b", DOC, re.IGNORECASE), word
