"""Every cell of the 2026 answer key carries one status, assigned by fixed rules.

results/cell_status.csv holds one row per board household and key quantity; docs/coverage.md
states the rules. scripts/make_cell_status.py writes both from files only. These tests read the
input files directly, apart from the script, wherever a property can be checked that way.

Invariants:
- one row per household and quantity (500 rows), every status and detail in its closed set,
  every row interim, no field that says "confirmed" or "verified";
- every contested cell names a cause entry that exists and applies to that cell;
- a cell is contested exactly where an entry's position on it (results/cause_positions.csv)
  supports another answer or turns on an unstated fact; the position and its grounds give the
  reason, never the entry's kind, and an entry that supports the key never contests;
- key_rests_on_readings names exactly the entries that support the key against a named other
  answer more than $1 away, and those columns never change a status;
- every reproduced cell agrees within $1 with each run in reproduced_by, in results/answers.csv,
  and Tax-Calculator plus TAXSIM count as one lineage;
- the counts by status add up to the agreement table's classes where the mapping is one to one;
- the script is deterministic and its committed output is current;
- classify() keeps its properties for every combination of measured facts (Hypothesis).
"""

import csv
import importlib.util
import io
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_cell_status.py"
TOLERANCE = 1.0
CASE_SET = "board-100"


def load_module():
    spec = importlib.util.spec_from_file_location("make_cell_status", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load_module()


def read_csv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def built():
    csv_text, doc_text, _ = M.build(ROOT)
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    return csv_text, doc_text, rows


@pytest.fixture(scope="module")
def rows(built):
    return built[2]


@pytest.fixture(scope="module")
def answers():
    out = {}
    for row in read_csv(ROOT / "results/answers.csv"):
        if row["case_set"] == CASE_SET:
            out[(row["run"], row["case_id"], row["quantity"])] = row
    return out


@pytest.fixture(scope="module")
def runs():
    return {r["run"]: r for r in read_csv(ROOT / "results/runs.csv")}


@pytest.fixture(scope="module")
def models():
    return {m["model"]: m for m in read_csv(ROOT / "results/models.csv")}


@pytest.fixture(scope="module")
def causes():
    return {c["cause_id"]: c for c in read_csv(ROOT / "results/causes.csv")}


@pytest.fixture(scope="module")
def cause_cells():
    return read_csv(ROOT / "results/cause_cells.csv")


@pytest.fixture(scope="module")
def positions():
    return {(r["cause_id"], r["case_id"], r["quantity"]): r for r in read_csv(ROOT / "results/cause_positions.csv")}


@pytest.fixture(scope="module")
def key_table():
    return {(r["case_id"], r["quantity"]): r for r in read_csv(ROOT / "results/agreement/board100_2026_key.csv")}


def value(answers, run, case, quantity):
    row = answers.get((run, case, quantity))
    if row is None or row["status"] != "ok" or row["value"] == "":
        return None
    return float(row["value"])


def split(field):
    return [x for x in field.split(";") if x]


# ---------------------------------------------------------------- shape and vocabulary
def test_one_row_per_household_and_quantity(rows, key_table, answers):
    households = sorted({case for case, _ in key_table})
    key_run = Counter(r["key_run"] for (_, q), r in key_table.items() if q == M.L1).most_common(1)[0][0]
    assert households == sorted({case for run, case, _ in answers if run == key_run})
    assert len(rows) == len(households) * len(M.QUANTITIES) == 500
    cells = Counter((r["case_id"], r["quantity"]) for r in rows)
    assert set(cells) == {(c, q) for c in households for q in M.QUANTITIES}
    assert set(cells.values()) == {1}


def test_closed_sets(rows):
    for r in rows:
        assert r["status"] in M.STATUSES
        assert r["status_detail"] in M.DETAILS[r["status"]]
        assert r["interim"] == "true"
        assert r["trivial"] in ("true", "false")
        assert r["also_agrees_under_2025_law"] in M.AGREES_2025
        assert r["second_map_taxcalc"] in M.SECOND_MAP_VALUES
        assert r["second_map_taxsim"] in M.SECOND_MAP_VALUES
        assert set(split(r["contested_reasons"])) <= set(M.DETAILS["contested"])
        if r["status"] == "reproduced":
            assert r["reproduction_scope"] in M.SCOPES
            shares = r["shares_with_key_run"]
            assert shares == "nothing" or set(split(shares)) <= set(M.SHARE_ORDER)
        else:
            assert r["reproduction_scope"] == "" and r["shares_with_key_run"] == "" and r["reproduced_by"] == ""
            assert r["also_agrees_under_2025_law"] == "not_applicable"
        if r["status"] == "contested":
            reasons = split(r["contested_reasons"])
            assert reasons and r["status_detail"] == reasons[0]
            assert reasons == [x for x in M.CONTESTED_ORDER if x in reasons]
        else:
            assert r["contested_reasons"] == "" and r["contesting_cause_ids"] == ""
        rests, others = split(r["key_rests_on_readings"]), split(r["other_reading_answers"])
        assert len(rests) == len(others) and set(rests) <= set(split(r["cause_ids"]))
        assert not set(rests) & set(split(r["contesting_cause_ids"]))


def test_no_field_or_sentence_says_confirmed_or_verified(built):
    csv_text, doc_text, _ = built
    for text in (csv_text, doc_text):
        assert not re.search(r"\b(confirm|verif)", text, re.IGNORECASE)


def test_columns_the_brief_names(built):
    header = built[0].splitlines()[0].split(",")
    for column in ("case_id", "quantity", "key_value", "board_scores_it", "status", "reproduced_by", "law_year",
                   "also_agrees_under_2025_law", "cause_ids", "shares_with_key_run", "note", "interim"):
        assert column in header


# ---------------------------------------------------------------- contested
def test_every_contested_cell_names_an_entry_that_applies_to_it(rows, causes, cause_cells):
    on_cell = {(r["cause_id"], r["case_id"], r["quantity"]) for r in cause_cells if r["table"] == "2026"}

    def applies(cid, case, quantity):
        if (cid, case, quantity) in on_cell:
            return True
        cause = causes[cid]
        shared = {t for t in split(cause["households_shared"]) if t.partition("@")[2] in ("", "2026")}
        return (cause["kind"] == "shared-reading" and {case, case + "@2026"} & shared
                and quantity in split(cause["quantities"]))

    contested = [r for r in rows if r["status"] == "contested"]
    assert contested
    for r in contested:
        ids = split(r["contesting_cause_ids"])
        assert ids, r["case_id"]
        assert all(cid in causes for cid in ids)
        assert set(ids) <= set(split(r["cause_ids"]))
        assert any(applies(cid, r["case_id"], r["quantity"]) for cid in ids), (r["case_id"], ids)


def test_cause_ids_exist_and_apply(rows, causes, cause_cells):
    on_cell = {(r["cause_id"], r["case_id"], r["quantity"]) for r in cause_cells if r["table"] == "2026"}
    for r in rows:
        for cid in split(r["cause_ids"]):
            cause = causes[cid]
            shared = {t.partition("@")[0] for t in split(cause["households_shared"])
                      if t.partition("@")[2] in ("", "2026")}
            assert (cid, r["case_id"], r["quantity"]) in on_cell or (
                r["case_id"] in shared and r["quantity"] in split(cause["quantities"]))


# ---------------------------------------------------------------- reproduced
def test_reproduced_cells_agree_with_each_reproducing_run(rows, answers, runs, models):
    for r in rows:
        if r["status"] != "reproduced":
            continue
        reproducing = split(r["reproduced_by"])
        assert reproducing
        key = float(r["key_value"])
        for run in reproducing:
            v = value(answers, run, r["case_id"], r["quantity"])
            assert v is not None and abs(v - key) <= TOLERANCE, (r["case_id"], r["quantity"], run)
            assert models[runs[run]["model"]]["lineage"] != "policyengine"
            assert runs[run]["period"] == r["law_year"]


def test_two_runs_of_one_input_map_count_as_one_lineage(rows):
    for r in rows:
        if r["status"] == "reproduced":
            assert len(split(r["reproducing_lineages"])) == 1
            if len(split(r["reproduced_by"])) == 2:
                assert r["reproduction_scope"] == "both_runs_one_lineage"


def test_reproduced_rows_name_model_release_law_year_and_map_version(rows, runs):
    bindings = {(b["case_id"], b["run"]): b for b in read_csv(ROOT / "results/bindings.csv")
                if b["case_set"] == CASE_SET}
    for r in rows:
        if r["status"] != "reproduced":
            continue
        reproducing = split(r["reproduced_by"])
        assert split(r["reproducing_models"]) == [runs[x]["model"] for x in reproducing]
        assert split(r["reproducing_releases"]) == [runs[x]["release"] for x in reproducing]
        versions = r["input_map_versions"]
        for run in reproducing:
            binding = bindings[(r["case_id"], run)]
            assert run in versions
            for v in binding["input_map_version"].split(" on "):
                assert v in versions


def test_key_values_come_from_the_committed_key(rows, answers, runs, key_table):
    key_run = Counter(r["key_run"] for (_, q), r in key_table.items() if q == M.L1).most_common(1)[0][0]
    by_cell = {(r["case_id"], r["quantity"]): r for r in rows}
    for (case, quantity), r in by_cell.items():
        if quantity in (M.L1, M.L2, M.SE):
            assert abs(float(r["key_value"]) - value(answers, key_run, case, quantity)) < 0.006
        if quantity in (M.L1, M.L2, M.SE, M.FP):
            # the agreement table's PolicyEngine column holds the key it compared with
            assert abs(float(r["key_value"]) - float(key_table[(case, quantity)]["policyengine"])) < 0.006
    for case in {c for c, _ in by_cell}:
        total = value(answers, key_run, case, "payroll_tax")
        parts = float(by_cell[(case, M.FP)]["key_value"]) + float(by_cell[(case, M.SP)]["key_value"])
        assert abs(total - parts) <= TOLERANCE


def test_salt_detail_follows_the_bindings(rows):
    bindings = {(b["case_id"], b["run"]): b for b in read_csv(ROOT / "results/bindings.csv")
                if b["case_set"] == CASE_SET}
    for r in rows:
        if r["status"] != "reproduced":
            continue
        bears = [bindings[(r["case_id"], run)]["input_from_other_run_bears_on_answer"] == "true"
                 for run in split(r["reproduced_by"])]
        expect = r["quantity"] in M.INCOME_TAX_LINES and all(bears)
        assert (r["status_detail"] == "key_salt_amount_itemized") == expect
        if r["status_detail"] == "key_salt_amount_itemized":
            assert "key_salt_amount" in split(r["shares_with_key_run"])


def test_shares_nothing_means_no_shared_input_on_the_measured_run(rows, answers):
    bindings = {(b["case_id"], b["run"]): b for b in read_csv(ROOT / "results/bindings.csv")
                if b["case_set"] == CASE_SET}
    readings = M.parse_readings(ROOT / "keycheck/unit.py")
    for r in rows:
        if r["status"] != "reproduced":
            continue
        run = r["shares_measured_on"]
        assert run in split(r["reproduced_by"])
        row = answers[(run, r["case_id"], r["quantity"])]
        has_map = bool(row["map_computed"].strip())
        has_reading = any(v in row["unexpressed_facts"] for v in readings.values())
        has_salt = (r["quantity"] in M.INCOME_TAX_LINES
                    and bindings[(r["case_id"], run)]["input_from_other_run_bears_on_answer"] == "true")
        shares = set(split(r["shares_with_key_run"]))
        assert ("map_computed_amount" in shares) == has_map
        assert ("reading" in shares) == has_reading
        assert ("key_salt_amount" in shares) == has_salt
        assert (r["shares_with_key_run"] == "nothing") == (not (has_map or has_reading or has_salt))


# ---------------------------------------------------------------- the agreement table
EXPECTED_AGREEING = {  # agreement class -> the other models that give the key's answer
    "all_agree": {"taxcalc", "taxsim"},
    "two_agree:taxsim": {"taxcalc"},
    "two_agree:taxcalc": {"taxsim"},
    "two_agree:policyengine": set(),
    "all_differ": set(),
}


def test_agreeing_runs_match_the_agreement_table(rows, runs, key_table):
    checked = 0
    for r in rows:
        if r["quantity"] == M.SP:
            continue
        cls = key_table[(r["case_id"], r["quantity"])]["class"]
        if cls not in EXPECTED_AGREEING:
            continue
        assert {runs[x]["model"] for x in split(r["agreeing_runs"])} == EXPECTED_AGREEING[cls]
        assert r["board_scores_it"] == key_table[(r["case_id"], r["quantity"])]["board_scores_it"]
        checked += 1
    assert checked == len(M.FOUR_LINES) * len({case for case, _ in key_table})


def test_status_counts_add_up_to_the_agreement_classes(rows, key_table):
    for quantity in M.FOUR_LINES:
        sub = [r for r in rows if r["quantity"] == quantity]
        classes = Counter(key_table[(r["case_id"], quantity)]["class"] for r in sub)
        status = Counter(r["status"] for r in sub)
        contested_agreeing = sum(1 for r in sub if r["status"] == "contested" and r["agreeing_runs"])
        contested_apart = status["contested"] - contested_agreeing
        key_agrees = classes["all_agree"] + classes["two_agree:taxsim"] + classes["two_agree:taxcalc"]
        key_alone = classes["two_agree:policyengine"] + classes["all_differ"]
        assert status["reproduced"] + contested_agreeing == key_agrees
        assert status["resting_on_one_model"] + contested_apart == key_alone
        both = sum(1 for r in sub if r["reproduction_scope"] == "both_runs_one_lineage")
        both_contested = sum(1 for r in sub if r["status"] == "contested" and len(split(r["agreeing_runs"])) == 2)
        assert both + both_contested == classes["all_agree"]


# The contested reason for each (position, grounds), restated here apart from the script.
REASON_OF = {
    ("supports_other_answer", "law"): "key_not_supported_by_law",
    ("supports_other_answer", "prompt_rule"): "key_not_supported_by_prompt_rule",
    ("turns_on_unstated_fact", ""): "turns_on_unstated_fact",
}


def entries_on_cell(causes, cause_cells):
    """{(case, quantity): {cause_id}}: rows on the cell in the 2026 table, and shared readings that
    list the household for the 2026 table on a line they name."""
    on = {}
    for r in cause_cells:
        if r["table"] == "2026":
            on.setdefault((r["case_id"], r["quantity"]), set()).add(r["cause_id"])
    for cause in causes.values():
        if cause["kind"] != "shared-reading":
            continue
        for token in split(cause["households_shared"]):
            case, _, table = token.partition("@")
            if table in ("", "2026"):
                for quantity in split(cause["quantities"]):
                    on.setdefault((case, quantity), set()).add(cause["cause_id"])
    return on


def key_run_of(key_table):
    return Counter(r["key_run"] for (_, q), r in key_table.items() if q == M.L1).most_common(1)[0][0]


def test_contest_follows_each_entrys_position_never_its_kind(rows, causes, cause_cells, positions):
    # Read only the positions file: the kind of an entry never enters the expectation.
    order = {cid: i for i, cid in enumerate(causes)}
    on = entries_on_cell(causes, cause_cells)
    reasons_seen, supporting_seen = Counter(), 0
    for r in rows:
        cell = (r["case_id"], r["quantity"])
        ids = sorted(on.get(cell, ()), key=order.get)
        assert split(r["cause_ids"]) == ids, cell
        held = {cid: positions[(cid, *cell)] for cid in ids if (cid, *cell) in positions}
        assert set(held) == {cid for cid in ids if causes[cid]["kind"] != "unexplained"}, cell
        disputing = [cid for cid in ids if cid in held and (held[cid]["position"], held[cid]["grounds"]) in REASON_OF]
        assert all(held[c]["position"] in ("supports_key", "no_effect") for c in held if c not in disputing), cell
        if r["status_detail"] == "no_other_model_has_quantity":
            assert not disputing, cell
            continue
        reasons = {REASON_OF[(held[c]["position"], held[c]["grounds"])] for c in disputing}
        assert (r["status"] == "contested") == bool(disputing), cell
        assert split(r["contesting_cause_ids"]) == disputing, cell
        assert set(split(r["contested_reasons"])) == reasons, cell
        reasons_seen.update(reasons)
        supporting_seen += len(held) - len(disputing)
    assert reasons_seen and supporting_seen


def test_every_entry_that_moves_the_key_contests_its_cell(rows, cause_cells, key_table):
    key_run = key_run_of(key_table)
    by_cell = {(r["case_id"], r["quantity"]): r for r in rows}
    moved = Counter()
    for c in cause_cells:
        if c["table"] == "2026" and c["run"] == key_run:
            moved[(c["cause_id"], c["case_id"], c["quantity"])] += float(c["amount"])
    hits = [k for k, amount in moved.items() if abs(amount) > TOLERANCE]
    assert hits
    for cid, case, quantity in hits:
        r = by_cell[(case, quantity)]
        assert r["status"] == "contested" and cid in split(r["contesting_cause_ids"]), (cid, case)


def test_board_record_alone_contests_nothing(rows, causes, cause_cells, positions):
    # A cell with a board exclusion record and no disputing entry keeps the status the rules give.
    on = entries_on_cell(causes, cause_cells)
    quiet = 0
    for r in rows:
        if not r["board_record"]:
            continue
        cell = (r["case_id"], r["quantity"])
        disputing = [cid for cid in on.get(cell, ()) if (cid, *cell) in positions
                     and positions[(cid, *cell)]["position"] in ("supports_other_answer", "turns_on_unstated_fact")]
        if not disputing:
            quiet += 1
            assert r["status"] != "contested", cell
    assert quiet


def test_readings_the_key_rests_on_follow_the_positions(rows, positions, causes):
    order = {cid: i for i, cid in enumerate(causes)}
    by_cell = {}
    for (cid, case, quantity), p in positions.items():
        if p["position"] == "supports_key" and p["other_reading_answer"].strip():
            by_cell.setdefault((case, quantity), []).append((cid, p))
    seen = 0
    for r in rows:
        cell = (r["case_id"], r["quantity"])
        key = float(r["key_value"])
        expect = [(cid, p) for cid, p in sorted(by_cell.get(cell, []), key=lambda e: order[e[0]])
                  if abs(float(p["other_reading_answer"]) - key) > TOLERANCE]
        assert split(r["key_rests_on_readings"]) == [cid for cid, _ in expect], cell
        assert [float(x) for x in split(r["other_reading_answers"])] == [
            float(p["other_reading_answer"]) for _, p in expect], cell
        for _, p in expect:
            assert abs(float(p["key_value"]) - key) < 0.005, cell
        seen += bool(expect)
        if r["status_detail"] == "other_runs_take_the_other_reading":
            assert expect and not split(r["agreeing_runs"]), cell
    assert seen


def test_positions_file_takes_the_scripts_values(positions):
    assert {r["position"] for r in positions.values()} <= set(M.POSITIONS)
    assert {r["grounds"] for r in positions.values()} <= set(M.GROUNDS)
    assert set(M.DISPUTING_POSITIONS) < set(M.POSITIONS)
    assert set(M.DISPUTING_POSITIONS) | set(M.SUPPORTING_POSITIONS) == set(M.POSITIONS)
    assert M.POSITION_REASON == REASON_OF
    assert set(M.POSITION_REASON.values()) == set(M.DETAILS["contested"]) == set(M.CONTESTED_ORDER)


def tree_with_positions(tmp_path, edit):
    """A copy of the repo by link, with results/cause_positions.csv rewritten by `edit`."""
    for child in ROOT.iterdir():
        if child.name not in ("results", ".git"):
            (tmp_path / child.name).symlink_to(child)
    (tmp_path / "results").mkdir()
    for child in (ROOT / "results").iterdir():
        if child.name != "cause_positions.csv":
            (tmp_path / "results" / child.name).symlink_to(child)
    with open(ROOT / "results/cause_positions.csv", newline="") as handle:
        reader = csv.DictReader(handle)
        kept = edit(list(reader))
        fields = reader.fieldnames
    with open(tmp_path / "results/cause_positions.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)
    return tmp_path


@pytest.mark.parametrize("which", ["shared_listing", "cell_row"])
def test_an_entry_on_a_cell_without_a_position_stops_the_script(tmp_path, causes, cause_cells, which):
    on_cell = {(r["cause_id"], r["case_id"], r["quantity"]) for r in cause_cells if r["table"] == "2026"}
    if which == "cell_row":
        target = sorted(on_cell)[0]
    else:
        target = next((c["cause_id"], case, split(c["quantities"])[0]) for c in causes.values()
                      if c["kind"] == "shared-reading"
                      for case, _, table in (t.partition("@") for t in split(c["households_shared"]))
                      if table in ("", "2026") and (c["cause_id"], case, split(c["quantities"])[0]) not in on_cell)
    root = tree_with_positions(tmp_path, lambda rs: [r for r in rs if (r["cause_id"], r["case_id"], r["quantity"]) != target])
    with pytest.raises(SystemExit, match="no position"):
        M.build(root)


def test_an_entry_that_moves_the_key_but_supports_it_stops_the_script(tmp_path, cause_cells, key_table):
    key_run = key_run_of(key_table)
    target = next((c["cause_id"], c["case_id"], c["quantity"]) for c in cause_cells
                  if c["table"] == "2026" and c["run"] == key_run and abs(float(c["amount"])) > TOLERANCE)

    def edit(rs):
        for r in rs:
            if (r["cause_id"], r["case_id"], r["quantity"]) == target:
                r.update(position="supports_key", grounds="law")
        return rs

    with pytest.raises(SystemExit, match="moves the key's answer"):
        M.build(tree_with_positions(tmp_path, edit))


def test_second_map_columns_follow_its_answers_and_the_comparers_rulings(rows):
    for engine in M.SECOND_MAP_ENGINES:
        path = ROOT / "second_map" / engine / "answers_2026.csv"
        column = f"second_map_{engine}"
        if not path.exists():
            assert {r[column] for r in rows} == {"pending"}
            continue
        answers2 = {(a["case_id"], a["quantity"]): a["value"] for a in read_csv(path)}
        diff = ROOT / "results" / "second_map" / f"{engine}_answers_diff.csv"
        ruled = {(d["case_id"], d["line"]): d["class"] for d in read_csv(diff)} if diff.exists() else {}
        for r in rows:
            cls = ruled.get((r["case_id"], r["quantity"]), "")
            assert r[f"{column}_class"] == cls
            if r["quantity"] == M.SP:
                expect = "not_covered"
            elif "second_map_errs" in re.split(r"[+;]", cls.replace(" ", "")):
                expect = "second_map_error"
            elif answers2.get((r["case_id"], r["quantity"]), "") in ("", "nan"):
                expect = "no_answer"
            else:
                agrees = abs(float(answers2[(r["case_id"], r["quantity"])]) - float(r["key_value"])) <= TOLERANCE
                expect = "agrees" if agrees else "differs"
            assert r[column] == expect, (r["case_id"], r["quantity"], engine)


def test_state_payroll_rests_on_policyengine_alone(rows, answers):
    for r in rows:
        if r["quantity"] == M.SP:
            assert (r["status"], r["status_detail"]) == ("resting_on_one_model", "no_other_model_has_quantity")


# ---------------------------------------------------------------- zeros and 2025
def test_trivial_flag_follows_its_rule(rows):
    import json
    for r in rows:
        if r["quantity"] in M.INCOME_TAX_LINES:
            assert r["trivial"] == "false"
            continue
        stated = json.loads((ROOT / f"results/dossiers/{r['case_id']}.json").read_text())["stated_facts"]
        holders = [p for group in (stated["adults"], stated["children"]) for p in group]
        holders += [v for k, v in stated.items() if k.endswith("_inputs")]
        facts = M.TRIVIAL_BASE[r["quantity"]]

        def amount(p, f):
            return float(p.get(f, p.get("inputs", {}).get(f, 0)) or 0)

        expect = float(r["key_value"]) == 0 and not any(amount(p, f) for p in holders for f in facts)
        assert (r["trivial"] == "true") == expect


def test_trivial_base_facts_are_board_facts():
    facts = {r["fact"] for r in read_csv(ROOT / "maps/board_facts.csv")}
    for names in M.TRIVIAL_BASE.values():
        assert set(names) <= facts


def test_2025_column_follows_the_2025_runs(rows, answers, runs):
    pe_2025 = Counter(r["key_run"] for r in read_csv(ROOT / "results/agreement/board100_2025.csv")).most_common(1)[0][0]
    for r in rows:
        if r["status"] != "reproduced":
            continue
        hits = []
        for run in split(r["reproduced_by"]):
            twin = [x for x, row in runs.items() if row["model"] == runs[run]["model"]
                    and row["release"] == runs[run]["release"] and row["period"] == runs[pe_2025]["period"]]
            assert len(twin) == 1
            a, b = value(answers, twin[0], r["case_id"], r["quantity"]), value(answers, pe_2025, r["case_id"], r["quantity"])
            hits.append(a is not None and b is not None and abs(a - b) <= TOLERANCE)
        expect = "yes" if all(hits) else ("partly" if any(hits) else "no")
        assert r["also_agrees_under_2025_law"] == expect


# ---------------------------------------------------------------- determinism and currency
def test_script_is_deterministic(tmp_path):
    outputs = []
    for name in ("a", "b"):
        out = tmp_path / name
        subprocess.run([sys.executable, "-I", str(SCRIPT), "--out-dir", str(out)], check=True,
                       capture_output=True, cwd=tmp_path)
        outputs.append(((out / "results/cell_status.csv").read_bytes(), (out / "docs/coverage.md").read_bytes()))
    assert outputs[0] == outputs[1]


def test_committed_output_is_current(built):
    csv_text, doc_text, _ = built
    assert (ROOT / "results/cell_status.csv").read_text() == csv_text
    assert (ROOT / "docs/coverage.md").read_text() == doc_text


# ---------------------------------------------------------------- the document
def test_coverage_opens_with_the_interim_note_and_counts_match(built, rows):
    _, doc, _ = built
    first = doc.split("\n## ")[0]
    assert "interim" in first.lower()
    counts = Counter(r["status"] for r in rows)
    total_line = next(line for line in doc.splitlines() if line.startswith("| All quantities |"))
    cells = [c.strip() for c in total_line.strip("|").split("|")]
    assert [int(x) for x in cells[1:4]] == [counts[s] for s in M.STATUSES]


PROPER = {"Tax-Calculator", "NBER", "TAXSIM", "PolicyEngine", "PolicyBench"}


def test_coverage_headings_in_sentence_case(built):
    for line in built[1].splitlines():
        if line.startswith("#"):
            words = line.lstrip("#").split()
            for word in words[1:]:
                bare = word.strip("()`,")
                assert bare in PROPER or not bare[:1].isupper(), line


def test_coverage_prose_has_no_be_plus_above_or_below(built):
    pattern = re.compile(r"\b(is|are|was|were|be|been) (just |still |even \S+ )?(above|below)\b", re.IGNORECASE)
    for line in built[1].splitlines():
        if not line.startswith("|"):
            assert not pattern.search(line), line


# ---------------------------------------------------------------- the rules, for every input
RUNS = ("tc", "ts")
IDS = [f"c{i}" for i in range(6)]
SUPPORTING_PAIRS = [("supports_key", "law"), ("supports_key", "prompt_rule"), ("no_effect", "")]
PAIRS = sorted(REASON_OF) + SUPPORTING_PAIRS


@st.composite
def measured(draw):
    has_other = draw(st.booleans())
    state = {run: draw(st.sampled_from(("agree", "apart", "none"))) if has_other else "none" for run in RUNS}
    if has_other and all(s == "none" for s in state.values()):
        state["tc"] = draw(st.sampled_from(("agree", "apart")))
    agreeing = [r for r in RUNS if state[r] == "agree"]
    apart = [r for r in RUNS if state[r] == "apart"]
    ids = st.sampled_from(IDS)
    held = draw(st.dictionaries(ids, st.sampled_from(PAIRS), max_size=4))
    rests_on = [cid for cid in draw(st.lists(ids, max_size=3, unique=True))
                if held.get(cid, ("",))[0] == "supports_key"]
    apart_causes = {r: draw(st.lists(st.tuples(ids, st.sampled_from(M.KINDS)), max_size=3)) for r in apart}
    return dict(
        has_other_model=has_other,
        agreeing=agreeing,
        apart=apart,
        held=held,
        rests_on=rests_on,
        apart_causes=apart_causes,
        salt_on_every_reproducing_run=bool(agreeing) and draw(st.booleans()),
    )


def disputing_of(facts):
    return [cid for cid, pair in facts["held"].items() if pair in REASON_OF]


@settings(max_examples=500, deadline=None)
@given(measured())
def test_classify_properties(facts):
    out = M.classify(facts)
    assert out["status"] in M.STATUSES and out["detail"] in M.DETAILS[out["status"]]
    if not facts["has_other_model"]:
        assert (out["status"], out["detail"]) == ("resting_on_one_model", "no_other_model_has_quantity")
        return
    disputing = disputing_of(facts)
    # contested exactly where an entry's position disputes the key or leaves it open
    assert (out["status"] == "contested") == bool(disputing)
    assert out["contesting"] == (disputing if out["status"] == "contested" else [])
    expected = {REASON_OF[facts["held"][c]] for c in disputing}
    assert out["reasons"] == [r for r in M.CONTESTED_ORDER if r in expected]
    if out["status"] == "contested":
        assert out["detail"] == out["reasons"][0]
    if out["status"] == "reproduced":
        assert facts["agreeing"] and out["scope"] in M.SCOPES
        assert (out["detail"] == "key_salt_amount_itemized") == facts["salt_on_every_reproducing_run"]
    assert (out["status"] == "reproduced") == (bool(facts["agreeing"]) and not disputing)
    if out["detail"] == "other_runs_take_the_other_reading":
        apart_ids = {cid for run in facts["apart"] for cid, _ in facts["apart_causes"][run]}
        assert apart_ids & set(facts["rests_on"])


@settings(max_examples=300, deadline=None)
@given(measured(), st.data())
def test_the_kind_never_decides_a_contest(facts, data):
    # Replace every kind on the apart runs: status, reasons and contesting entries stay put.
    out = M.classify(facts)
    rekinded = {run: [(cid, data.draw(st.sampled_from(M.KINDS))) for cid, _ in causes]
                for run, causes in facts["apart_causes"].items()}
    again = M.classify(dict(facts, apart_causes=rekinded))
    assert (again["status"], again["reasons"], again["contesting"]) == (out["status"], out["reasons"], out["contesting"])


@settings(max_examples=300, deadline=None)
@given(measured(), st.sampled_from(SUPPORTING_PAIRS), st.booleans())
def test_an_entry_that_supports_the_key_never_contests(facts, pair, named):
    # Adding an entry that supports the key, with or without a named other answer, changes no status.
    out = M.classify(facts)
    extra = dict(facts, held={**facts["held"], "extra": pair},
                 rests_on=facts["rests_on"] + (["extra"] if named and pair[0] == "supports_key" else []))
    again = M.classify(extra)
    assert (again["status"], again["reasons"], again["contesting"]) == (out["status"], out["reasons"], out["contesting"])


@settings(max_examples=300, deadline=None)
@given(measured(), st.sampled_from(sorted(REASON_OF)))
def test_an_entry_that_disputes_the_key_always_contests(facts, pair):
    if not facts["has_other_model"]:
        return
    out = M.classify(dict(facts, held={**facts["held"], "extra": pair}))
    assert out["status"] == "contested"
    assert REASON_OF[pair] in out["reasons"] and "extra" in out["contesting"]
