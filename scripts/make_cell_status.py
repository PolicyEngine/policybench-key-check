"""Give each cell of the 2026 answer key a status, and write what each model can reproduce.

    python3 -I scripts/make_cell_status.py [--out-dir DIR]

With no arguments it writes results/cell_status.csv and docs/coverage.md in this repository.
With --out-dir it writes the same two files under DIR (results/ and docs/), for tests.

A cell is one board household and one key quantity for tax year 2026: the three federal income
tax and self-employment lines, the federal part of payroll tax and the state part. Each cell gets
one of three statuses, assigned here by fixed rules (docs/coverage.md states them):

  reproduced            reproduced by a run of another lineage
  contested             a cause entry, or the board's own record, puts the key's answer in dispute
  resting_on_one_model  resting on PolicyEngine alone

Every status is interim until the input maps have had an independent read.

The script reads files only (standard library; no model runs): results/answers.csv,
results/runs.csv, results/models.csv, results/bindings.csv, results/causes.csv,
results/cause_cells.csv, results/agreement/board100_2026_key.csv and board100_2025.csv,
results/dossiers/*.json (stated facts, board exclusion records), maps/board_facts.csv,
keycheck/unit.py (READINGS, parsed with ast, not imported) and, when they exist, the second
map's answers (second_map/<engine>/answers_2026.csv). It reads every version and run id from
these files.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1.0  # two answers agree within $1, the board's exact-match rule (scripts/agreement.py)
CASE_SET = "board-100"

L1 = "federal_income_tax_before_refundable_credits"
L2 = "federal_refundable_credits"
SE = "self_employment_tax"
FP = "federal_employee_payroll_tax"
SP = "state_employee_payroll_tax"
QUANTITIES = (L1, L2, SE, FP, SP)
FOUR_LINES = (L1, L2, SE, FP)
INCOME_TAX_LINES = (L1, L2)
BOARD_OUTPUT = {FP: "payroll_tax", SP: "payroll_tax"}  # the board scores federal plus state together
SECOND_MAP_ENGINES = ("taxcalc", "taxsim")  # second_map/<engine>/answers_2026.csv
DISPLAY = {"taxcalc": "Tax-Calculator", "taxsim": "NBER TAXSIM", "policyengine-us": "PolicyEngine-US"}
LINE_NAME = {
    L1: "federal income tax before refundable credits",
    L2: "federal refundable credits",
    SE: "self-employment tax",
    FP: "federal employee payroll tax",
    SP: "state employee payroll tax",
}

# Stated facts that carry the base of a tax, for the `trivial` flag (a zero key where the
# household states none of the base). The test checks that each name is a board fact.
SELF_EMPLOYMENT_FACTS = (
    "self_employment_income",
    "sstb_self_employment_income_before_lsr",
    "farm_operations_income",
    "partnership_se_income",
)
WAGE_FACTS = ("employment_income",)
TRIVIAL_BASE = {SE: SELF_EMPLOYMENT_FACTS, FP: WAGE_FACTS, SP: WAGE_FACTS}

STATUSES = ("reproduced", "contested", "resting_on_one_model")
STATUS_WORDING = {
    "reproduced": "reproduced by a run of another lineage",
    "contested": "contested",
    "resting_on_one_model": "resting on PolicyEngine alone",
}
# status_detail: one value per row, a closed set per status.
DETAILS = {
    "reproduced": ("no_input_from_key_run", "key_salt_amount_itemized"),
    "contested": (
        "key_not_supported_by_law",
        "turns_on_unstated_fact",
        "key_decided_value_unscored",
        "three_answers_differ",
    ),
    "resting_on_one_model": (
        "no_other_model_has_quantity",
        "no_other_run_takes_a_fact",
        "other_runs_depart_from_law",
        "unexplained",
    ),
}
CONTESTED_ORDER = DETAILS["contested"]  # precedence when more than one reason applies
SCOPES = (
    "both_runs_one_lineage",
    "one_run",
    "one_run_other_model_gap",
    "one_run_other_map_limit",
    "one_run_other_gap_and_map_limit",
    "one_run_other_unexplained",
)
SHARE_ORDER = ("key_salt_amount", "map_computed_amount", "reading")
SECOND_MAP_VALUES = ("pending", "agrees", "differs", "second_map_error", "no_answer", "not_covered")
# results/second_map/<engine>_answers_diff.csv: the comparer's ruling on each line. The script reads
# only `class` from it (its first-map columns describe the first map at the commit the file names).
SECOND_MAP_ERROR = "second_map_errs"
CLASS_TOKENS = re.compile(r"\s*[+;]\s*")
AGREES_2025 = ("yes", "partly", "no", "not_applicable")

# Cause kinds (docs/causes.md) and the contested reason each gives when the entry moves the key.
KEY_MOVING_REASON = {
    "model-law-departure": "key_not_supported_by_law",
    "model-no-provision": "key_not_supported_by_law",
    "key-decided-value": "key_not_supported_by_law",
    "pe-default-unstated-fact": "turns_on_unstated_fact",
    "shared-reading": "turns_on_unstated_fact",
    "map-limit": "turns_on_unstated_fact",
}
NO_POSITION_KINDS = {"unexplained"}  # an entry of this kind takes no position on who is right
MODEL_GAP_KINDS = {"model-no-provision", "model-law-departure"}
# The board's own exclusion record: an unlisted input makes the answer turn on an unstated fact;
# any other reason (an engine defect, law published after the freeze) says the law supports another answer.
BOARD_RECORD_REASON = {"reference_depends_on_unlisted_input": "turns_on_unstated_fact"}
BOARD_RECORD_OTHER = "key_not_supported_by_law"

# map_computed notes in results/answers.csv, by their opening words.
MAP_COMPUTED_TAGS = (
    ("IRA deduction figured", "ira_deduction"),
    ("educator expenses limited", "educator_expense_limit"),
    ("mortgage interest limited", "mortgage_debt_limit"),
    ("saver's credit figured", "savers_credit"),
    ("student loan interest deduction figured", "student_loan_interest"),
    ("traditional 401(k) deferrals limited", "deferral_limit"),
    ("charitable gifts (above 0.5% of AGI", "charitable_floor_in_mortgage"),
    ("medical expenses above 7.5% of AGI", "medical_floor_in_mortgage"),
    ("the EITC comes from a second TAXSIM record", "eitc_second_record"),
)
SALT_NOTE = "shared assumption: state and local income or sales tax paid"

# A shared-reading entry names a household's answer as one that would change.
NAMED_ANSWER = re.compile(r"\b(\d{3})'s (?:scored )?answer\b")
SENTENCE_SPLIT = re.compile(r"(?<=[.;])\s+")
WOULD = re.compile(r"\bwould\b")
READINGS_REF = re.compile(r"READINGS (\w+)")
PY_PATH = re.compile(r"[\w./-]+\.py")


# ---------------------------------------------------------------- reading the files
def read_csv(path: Path) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def parse_readings(path: Path) -> dict[str, str]:
    """keycheck/unit.py READINGS as a dict, without importing keycheck."""
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "READINGS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit(f"no READINGS in {path}")


def split_notes(text: str) -> list[str]:
    return [part.strip() for part in text.split("||") if part.strip()]


def reading_keys(text: str, readings: dict[str, str]) -> list[str]:
    """READINGS keys whose text appears in a cell's unexpressed_facts."""
    found = []
    for note in split_notes(text):
        for key, value in readings.items():
            if value in note and key not in found:
                found.append(key)
    return sorted(found)


def map_computed_tags(text: str) -> list[str]:
    tags = []
    for note in split_notes(text):
        for prefix, tag in MAP_COMPUTED_TAGS:
            if note.startswith(prefix):
                tags.append(tag)
                break
        else:
            tags.append("other:" + "_".join(re.findall(r"[a-z0-9]+", note.lower())[:5]))
    return sorted(set(tags))


def named_answers_that_would_change(text: str) -> set[str]:
    """Three-digit household ids whose answer a sentence names and says what it would be."""
    found = set()
    for sentence in SENTENCE_SPLIT.split(text):
        if WOULD.search(sentence):
            found.update(NAMED_ANSWER.findall(sentence))
    return found


def household_tokens(field: str) -> set[str]:
    """households_shared tokens that apply to the 2026 table (no suffix, or @2026)."""
    out = set()
    for token in filter(None, field.split(";")):
        case, _, table = token.partition("@")
        if table in ("", "2026"):
            out.add(case)
    return out


def persons(stated: dict) -> list[dict]:
    return [p for value in stated.values() if isinstance(value, list) for p in value if isinstance(p, dict)]


def stated_amount(person: dict, fact: str) -> float:
    value = person.get(fact, person.get("inputs", {}).get(fact, 0))
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def household_states(stated: dict, fact: str) -> bool:
    """True where any member, or any entity's inputs (household_inputs, tax_unit_inputs, ...),
    states the fact with a value other than 0."""
    if any(stated_amount(p, fact) != 0 for p in persons(stated)):
        return True
    return any(stated_amount(value, fact) != 0 for key, value in stated.items()
               if key.endswith("_inputs") and isinstance(value, dict))


def fmt_money(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def agree(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= TOLERANCE


# ---------------------------------------------------------------- lineage of runs
def lineage_groups(runs: list[dict], models: dict[str, dict]) -> dict[str, frozenset]:
    """Runs count as one lineage where they share an engine (models.csv lineage), a convention
    file or an input-map file (runs.csv). An input another run computed does not join them here;
    the script qualifies each cell where such an input bears on the answer."""
    parent = {r["run"]: r["run"] for r in runs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    by_key = defaultdict(list)
    for r in runs:
        by_key[("lineage", models[r["model"]]["lineage"])].append(r["run"])
        for path in PY_PATH.findall(r["input_map"]):
            by_key[("map", path)].append(r["run"])
        for path in PY_PATH.findall(r["conventions"]):
            by_key[("conventions", path)].append(r["run"])
    for members in by_key.values():
        for other in members[1:]:
            union(members[0], other)
    groups = defaultdict(set)
    for r in runs:
        groups[find(r["run"])].add(r["run"])
    return {run: frozenset(groups[find(run)]) for run in parent}


# ---------------------------------------------------------------- the data
class Data:
    def __init__(self, root: Path):
        self.root = root
        self.answers = {}
        for row in read_csv(root / "results/answers.csv"):
            if row["case_set"] == CASE_SET:
                self.answers[(row["run"], row["case_id"], row["quantity"])] = row
        self.runs = {r["run"]: r for r in read_csv(root / "results/runs.csv")}
        self.models = {m["model"]: m for m in read_csv(root / "results/models.csv")}
        self.bindings = {(b["case_id"], b["run"]): b for b in read_csv(root / "results/bindings.csv")
                         if b["case_set"] == CASE_SET}
        self.causes = read_csv(root / "results/causes.csv")
        self.cause_by_id = {c["cause_id"]: c for c in self.causes}
        self.cause_order = {c["cause_id"]: i for i, c in enumerate(self.causes)}
        self.cause_cells = read_csv(root / "results/cause_cells.csv")
        self.key_table = read_csv(root / "results/agreement/board100_2026_key.csv")
        self.table_2025 = read_csv(root / "results/agreement/board100_2025.csv")
        self.board_facts = read_csv(root / "maps/board_facts.csv")
        self.readings = parse_readings(root / "keycheck/unit.py")
        self.dossiers = {}
        for path in sorted((root / "results/dossiers").glob("scenario_*.json")):
            d = json.loads(path.read_text())
            self.dossiers[d["case_id"]] = d
        self.second_map = {}
        for engine in SECOND_MAP_ENGINES:
            path = root / "second_map" / engine / "answers_2026.csv"
            if path.exists():
                self.second_map[engine] = {(r["case_id"], r["quantity"]): r for r in read_csv(path)}
        self.second_map_class = {}
        for engine in SECOND_MAP_ENGINES:
            path = root / "results" / "second_map" / f"{engine}_answers_diff.csv"
            if path.exists():
                self.second_map_class[engine] = {(r["case_id"], r["line"]): r["class"] for r in read_csv(path)}

        # The key run and its engine rerun, as the 2026 agreement table names them.
        key_runs = Counter(r["key_run"] for r in self.key_table if r["quantity"] == L1)
        self.key_run = key_runs.most_common(1)[0][0]
        fallback = {r["key_run"] for r in self.key_table if r["key_run"] != self.key_run}
        key = self.runs[self.key_run]
        reruns = [r["run"] for r in self.runs.values()
                  if r["run"] != self.key_run and r["model"] == key["model"]
                  and r["release"] == key["release"] and r["period"] == key["period"]]
        if len(reruns) != 1 or (fallback and fallback != set(reruns)):
            raise SystemExit(f"cannot identify the key engine's rerun: {reruns} {fallback}")
        self.rerun = reruns[0]
        self.period = key["period"]
        runs_2025 = Counter(r["key_run"] for r in self.table_2025)
        self.key_run_2025 = runs_2025.most_common(1)[0][0]

        self.groups = lineage_groups(list(self.runs.values()), self.models)
        key_group = self.groups[self.key_run]
        if self.groups[self.key_run_2025] != key_group:
            raise SystemExit("the 2025 key-engine run is not in the key's lineage")
        present = {k[0] for k in self.answers}
        self.other_runs = sorted(r for r, row in self.runs.items()
                                 if row["period"] == self.period and r not in key_group and r in present)
        self.other_runs_2025 = sorted(r for r, row in self.runs.items()
                                      if row["period"] == self.runs[self.key_run_2025]["period"]
                                      and r not in key_group and r in present)
        self.counterpart_2025 = {}
        for run in self.other_runs:
            row = self.runs[run]
            match = [r for r in self.other_runs_2025
                     if self.runs[r]["model"] == row["model"] and self.runs[r]["release"] == row["release"]]
            self.counterpart_2025[run] = match[0] if len(match) == 1 else None
        self.cases = sorted({k[1] for k in self.answers if k[0] == self.key_run})
        self.class_2026 = {(r["case_id"], r["quantity"]): r for r in self.key_table}
        self.class_2025 = {(r["case_id"], r["quantity"]): r for r in self.table_2025}
        self.cells_by_cell = defaultdict(list)
        for row in self.cause_cells:
            self.cells_by_cell[(row["case_id"], row["quantity"], row["table"])].append(row)
        self.no_other_model_facts = facts_no_other_model_takes(self.board_facts)

    def value(self, run: str, case: str, quantity: str) -> float | None:
        row = self.answers.get((run, case, quantity))
        if row is None or row["status"] != "ok" or row["value"] == "":
            return None
        return float(row["value"])

    def status_of(self, run: str, case: str, quantity: str) -> str:
        row = self.answers.get((run, case, quantity))
        return "missing" if row is None else row["status"]

    def lineage_label(self, run: str) -> str:
        return "+".join(sorted({self.models[self.runs[r]["model"]]["lineage"] for r in self.groups[run]}))


def facts_no_other_model_takes(board_facts: list[dict]) -> list[dict]:
    """Board facts with an effect on the four lines that neither other model takes: no field, or a
    field the map sends as 0, or one with no effect in 2025 or 2026."""

    def dead(field: str) -> bool:
        return not field.strip() or "(sent as 0)" in field or "(no effect" in field

    return [r for r in board_facts
            if r["effect_on_the_four_lines_in_the_key"] in ("federal", "indirect")
            and dead(r["taxcalc_field"]) and dead(r["taxsim_field"])]


# ---------------------------------------------------------------- one cell
def key_value(data: Data, case: str, quantity: str) -> tuple[float | None, str]:
    value = data.value(data.key_run, case, quantity)
    if value is not None:
        return value, "committed_key"
    # The committed key holds payroll_tax (federal plus state); split it by the engine rerun's parts.
    total = data.value(data.key_run, case, "payroll_tax")
    federal = data.value(data.rerun, case, FP)
    state = data.value(data.rerun, case, SP)
    part = federal if quantity == FP else state
    if total is None or federal is None or state is None:
        return part, "engine_rerun"
    if abs(federal + state - total) > TOLERANCE:
        return part, "engine_rerun_split_differs_from_committed_payroll_tax"
    return part, "committed_payroll_tax_split_by_engine_rerun"


def run_shares(data: Data, case: str, quantity: str, run: str) -> tuple[list[str], list[str], list[str]]:
    """What a reproducing run shares with the key's run on this cell: the key's state and local tax
    amount (where the model itemizes and the quantity is an income tax line), amounts this repo
    computed from the statute (map_computed), and named readings of unstated facts."""
    row = data.answers[(run, case, quantity)]
    binding = data.bindings.get((case, run), {})
    bears = binding.get("input_from_other_run_bears_on_answer") == "true"
    note = SALT_NOTE in row["unexpressed_facts"]
    salt = quantity in INCOME_TAX_LINES and bears
    if quantity in INCOME_TAX_LINES and salt != note:
        raise SystemExit(f"{case} {quantity} {run}: bindings and answers disagree on the shared state and local tax")
    shares = []
    if salt:
        shares.append("key_salt_amount")
    computed = map_computed_tags(row["map_computed"])
    if computed:
        shares.append("map_computed_amount")
    readings = reading_keys(row["unexpressed_facts"], data.readings)
    if readings:
        shares.append("reading")
    return shares, computed, readings


def map_version(binding: dict) -> str:
    """'keycheck/map_taxcalc.py 2026-11-10.2 on keycheck/unit.py 2026-11-10.2' from bindings.csv's
    input_map ('a on b') and input_map_version ('v on w')."""
    files = binding["input_map"].split(" on ")
    versions = binding["input_map_version"].split(" on ")
    if len(files) == len(versions):
        return " on ".join(f"{f} {v}" for f, v in zip(files, versions))
    return f"{binding['input_map']} (version {binding['input_map_version']})"


def share_rank(shares: list[str]) -> tuple:
    return tuple(name in shares for name in SHARE_ORDER)


def classify(facts: dict) -> dict:
    """The status rules. `facts` holds what the script measured on one cell:

    has_other_model      some run of another lineage gives an answer for the quantity
    agreeing             runs of another lineage within $1 of the key
    apart                runs of another lineage with an answer more than $1 from the key
    key_moving           {cause_id: kind} for entries that move the key's answer by more than $1
    shared_named         cause ids of shared readings that name this household's answer as one that would change
    board_record_reason  the board's exclusion record for the output, where a shared reading lists the
                         household and the record's alternative differs from the key by more than $1
    shared_board         cause ids of the shared readings behind board_record_reason
    apart_causes         {run: [(cause_id, kind, names_reading)]} for entries that move each apart run
    cell_cause_ids       cause ids with a row on this cell in results/cause_cells.csv (2026 table)
    key_differs_from_rerun_unscored  the board does not score the output and the key differs from its engine's rerun
    others_all_differ    two or more other runs answer and no two of key and other runs agree
    salt_on_every_reproducing_run    every agreeing run itemizes on the key's state and local tax amount
    """
    reasons, contesting = [], []

    def add(reason, ids):
        if reason not in reasons:
            reasons.append(reason)
        for cid in ids:
            if cid not in contesting:
                contesting.append(cid)

    if not facts["has_other_model"]:
        return dict(status="resting_on_one_model", detail="no_other_model_has_quantity", reasons=[],
                    contesting=[], scope="")
    for cid, kind in facts["key_moving"].items():
        add(KEY_MOVING_REASON[kind], [cid])
    if facts["shared_named"]:
        add("turns_on_unstated_fact", facts["shared_named"])
    if facts["board_record_reason"]:
        add(facts["board_record_reason"], facts["shared_board"])
    if not facts["agreeing"]:
        reading_causes = [cid for run in facts["apart"] for cid, kind, names in facts["apart_causes"].get(run, [])
                          if kind == "shared-reading" or (kind == "map-limit" and names)]
        if reading_causes:
            add("turns_on_unstated_fact", reading_causes)
        # These two contest the key only where an entry with rows on the cell explains the difference.
        cell_ids = facts["cell_cause_ids"]
        if facts["key_differs_from_rerun_unscored"] and cell_ids:
            add("key_decided_value_unscored", cell_ids)
        if facts["others_all_differ"] and cell_ids:
            add("three_answers_differ", cell_ids)
    if reasons:
        reasons = [r for r in CONTESTED_ORDER if r in reasons]
        return dict(status="contested", detail=reasons[0], reasons=reasons, contesting=contesting, scope="")
    if facts["agreeing"]:
        if not facts["apart"]:
            scope = "both_runs_one_lineage" if len(facts["agreeing"]) > 1 else "one_run"
        else:
            kinds = {kind for run in facts["apart"] for _, kind, _ in facts["apart_causes"].get(run, [])}
            if not kinds:
                scope = "one_run_other_unexplained"
            elif kinds <= MODEL_GAP_KINDS:
                scope = "one_run_other_model_gap"
            elif kinds <= {"map-limit"}:
                scope = "one_run_other_map_limit"
            elif kinds <= MODEL_GAP_KINDS | {"map-limit"}:
                scope = "one_run_other_gap_and_map_limit"
            else:
                scope = "one_run_other_unexplained"
        detail = "key_salt_amount_itemized" if facts["salt_on_every_reproducing_run"] else "no_input_from_key_run"
        return dict(status="reproduced", detail=detail, reasons=[], contesting=[], scope=scope)
    kinds = {kind for run in facts["apart"] for _, kind, _ in facts["apart_causes"].get(run, [])}
    if not kinds or not facts["apart"] or any(not facts["apart_causes"].get(run) for run in facts["apart"]):
        detail = "unexplained"
    elif kinds <= {"model-no-provision", "map-limit"}:
        detail = "no_other_run_takes_a_fact"
    elif kinds <= MODEL_GAP_KINDS | {"map-limit"}:
        detail = "other_runs_depart_from_law"
    else:
        detail = "unexplained"
    return dict(status="resting_on_one_model", detail=detail, reasons=[], contesting=[], scope="")


def board_record(data: Data, case: str, quantity: str) -> dict | None:
    output = BOARD_OUTPUT.get(quantity, quantity)
    for record in data.dossiers[case].get("board_exclusion_records", []):
        if record["variable"] == output:
            return record
    return None


def cell(data: Data, case: str, quantity: str) -> dict:
    key, source = key_value(data, case, quantity)
    rerun = data.value(data.rerun, case, quantity)
    agreement_row = data.class_2026.get((case, quantity if quantity != SP else FP), {})
    scored = agreement_row.get("board_scores_it", "")
    record = board_record(data, case, quantity)
    stated = data.dossiers[case]["stated_facts"]

    answers = {run: data.value(run, case, quantity) for run in data.other_runs}
    has_other = any(v is not None for v in answers.values())
    agreeing = [run for run, v in answers.items() if agree(v, key)]
    apart = [run for run, v in answers.items() if v is not None and not agree(v, key)]

    # Cause entries: rows on this cell in the 2026 table, then shared readings that list the household.
    rows = data.cells_by_cell.get((case, quantity, data.period), [])
    row_ids = sorted({r["cause_id"] for r in rows}, key=data.cause_order.get)
    shared_ids = [c["cause_id"] for c in data.causes
                  if c["kind"] == "shared-reading" and case in household_tokens(c["households_shared"])
                  and quantity in c["quantities"].split(";") and c["cause_id"] not in row_ids]
    cause_ids = row_ids + shared_ids
    key_moving = {}
    for cid in row_ids:
        kind = data.cause_by_id[cid]["kind"]
        if kind not in KEY_MOVING_REASON and kind not in NO_POSITION_KINDS:
            raise SystemExit(f"cause kind {kind!r} ({cid}) has no status rule; add one to make_cell_status.py")
        amount = sum(float(r["amount"]) for r in rows if r["cause_id"] == cid and r["run"] == data.key_run)
        if abs(amount) > TOLERANCE and kind in KEY_MOVING_REASON:
            key_moving[cid] = kind
    apart_causes = {}
    for run in apart:
        model = data.runs[run]["model"]
        entries = []
        for cid in row_ids:
            if any(r["cause_id"] == cid and r["answerer"] == model for r in rows):
                cause = data.cause_by_id[cid]
                names = any(k in data.readings for k in READINGS_REF.findall(cause["release_or_build"]))
                entries.append((cid, cause["kind"], names))
        apart_causes[run] = entries
    shared_named = [cid for cid in shared_ids
                    if case.split("_")[-1] in named_answers_that_would_change(data.cause_by_id[cid]["who_is_right"])]
    record_reason, shared_board = "", []
    if record is not None and shared_ids and record.get("alternative_value") is not None:
        output = BOARD_OUTPUT.get(quantity, quantity)
        committed = data.value(data.key_run, case, output)
        if committed is not None and abs(float(record["alternative_value"]) - committed) > TOLERANCE:
            record_reason = BOARD_RECORD_REASON.get(record["reason_code"], BOARD_RECORD_OTHER)
            shared_board = shared_ids
    others_answering = [v for v in answers.values() if v is not None]
    values = [key] + others_answering
    others_all_differ = len(others_answering) >= 2 and all(
        not agree(a, b) for i, a in enumerate(values) for b in values[i + 1:])

    shares_by_run = {run: run_shares(data, case, quantity, run) for run in agreeing}
    facts = dict(
        has_other_model=has_other,
        agreeing=agreeing,
        apart=apart,
        key_moving=key_moving,
        shared_named=shared_named,
        board_record_reason=record_reason,
        shared_board=shared_board,
        apart_causes=apart_causes,
        cell_cause_ids=row_ids,
        key_differs_from_rerun_unscored=(scored == "no" and not agree(key, rerun)),
        others_all_differ=others_all_differ,
        salt_on_every_reproducing_run=bool(agreeing) and all(
            "key_salt_amount" in shares_by_run[r][0] for r in agreeing),
    )
    verdict = classify(facts)
    status = verdict["status"]

    reproduced_by = agreeing if status == "reproduced" else []
    measured_on, shares, computed, readings = "", [], [], []
    if reproduced_by:
        measured_on = min(reproduced_by, key=lambda r: (share_rank(shares_by_run[r][0]), r))
        shares, computed, readings = shares_by_run[measured_on]

    trivial = False
    if quantity in TRIVIAL_BASE and key is not None and abs(key) < 0.005:
        trivial = not any(household_states(stated, fact) for fact in TRIVIAL_BASE[quantity])

    no_other_facts = []
    if quantity in INCOME_TAX_LINES:
        no_other_facts = [f["fact"] for f in data.no_other_model_facts
                          if f["effect_on_the_four_lines_in_the_key"] == "federal" and household_states(stated, f["fact"])]

    # Tax year 2025: the same engines on the same households, against the key engine's 2025 run.
    pe_2025 = data.value(data.key_run_2025, case, quantity)
    agreeing_2025 = [r for r in data.other_runs_2025 if agree(data.value(r, case, quantity), pe_2025)]
    if status == "reproduced":
        counterparts = [data.counterpart_2025.get(r) for r in reproduced_by]
        hits = [c for c in counterparts if c in agreeing_2025]
        also_2025 = "yes" if len(hits) == len(counterparts) else ("partly" if hits else "no")
    else:
        also_2025 = "not_applicable"

    second, second_class = {}, {}
    for engine in SECOND_MAP_ENGINES:
        second_class[engine] = data.second_map_class.get(engine, {}).get((case, quantity), "")
        if engine not in data.second_map:
            second[engine] = "pending"
        elif quantity == SP:
            second[engine] = "not_covered"
        elif SECOND_MAP_ERROR in CLASS_TOKENS.split(second_class[engine]):
            second[engine] = "second_map_error"
        else:
            row = data.second_map[engine].get((case, quantity))
            try:
                value = float(row["value"]) if row and row.get("value", "") not in ("", "nan") else None
            except ValueError:
                value = None
            second[engine] = "no_answer" if value is None else ("agrees" if agree(value, key) else "differs")

    record_text = ""
    if record is not None:
        alt = record.get("alternative_value")
        record_text = f"{record['variable']}: {record['reason_code']}"
        if alt is not None:
            record_text += f"; alternative {float(alt):.2f}"

    out = dict(
        case_id=case,
        quantity=quantity,
        board_output=BOARD_OUTPUT.get(quantity, quantity),
        key_value=fmt_money(key),
        key_source=source,
        key_equals_engine_rerun="yes" if agree(key, rerun) else "no",
        board_scores_it=scored,
        board_record=record_text,
        status=status,
        status_detail=verdict["detail"],
        contested_reasons=";".join(verdict["reasons"]),
        contesting_cause_ids=";".join(verdict["contesting"]),
        trivial="true" if trivial else "false",
        agreeing_runs=";".join(agreeing),
        apart_runs=";".join(apart),
        reproduced_by=";".join(reproduced_by),
        reproducing_lineages=";".join(sorted({data.lineage_label(r) for r in reproduced_by})),
        reproducing_models=";".join(data.runs[r]["model"] for r in reproduced_by),
        reproducing_releases=";".join(data.runs[r]["release"] for r in reproduced_by),
        law_year=data.period,
        input_map_versions=";".join(f"{r}: {map_version(data.bindings[(case, r)])}" for r in reproduced_by),
        reproduction_scope=verdict["scope"],
        shares_with_key_run=(";".join(shares) if shares else "nothing") if reproduced_by else "",
        shares_measured_on=measured_on,
        shared_readings=";".join(readings),
        shared_map_computed=";".join(computed),
        facts_no_other_model_takes=";".join(no_other_facts),
        also_agrees_under_2025_law=also_2025,
        agreeing_runs_2025=";".join(agreeing_2025),
        cause_ids=";".join(cause_ids),
        second_map_taxcalc=second["taxcalc"],
        second_map_taxsim=second["taxsim"],
        second_map_taxcalc_class=second_class["taxcalc"],
        second_map_taxsim_class=second_class["taxsim"],
        interim="true",
    )
    out["note"] = note(data, out, apart, apart_causes)
    return out


def note(data: Data, row: dict, apart: list[str], apart_causes: dict) -> str:
    status = row["status"]
    parts = []
    if status == "reproduced":
        runs = row["reproduced_by"].split(";")
        parts.append("Reproduced by a run of another lineage: " + ", ".join(runs) + ".")
        if len(runs) > 1:
            parts.append("The two runs share one input map, so they count as one lineage.")
        for run in apart:
            ids = [cid for cid, _, _ in apart_causes.get(run, [])]
            parts.append(f"{DISPLAY[data.runs[run]['model']]} stands apart" + (": " + ", ".join(ids) + "." if ids else "."))
        if row["status_detail"] == "key_salt_amount_itemized":
            parts.append("The reproducing run itemizes on PolicyEngine's state and local tax amount.")
        if row["trivial"] == "true":
            parts.append("A zero with none of the tax's base stated: it tests little.")
    elif status == "contested":
        parts.append("Contested (" + row["contested_reasons"].replace(";", ", ") + "): "
                     + ", ".join(row["contesting_cause_ids"].split(";")) + ".")
        if row["agreeing_runs"]:
            parts.append("Runs of another lineage that still give the key's answer: "
                         + ", ".join(row["agreeing_runs"].split(";")) + ".")
    else:
        if row["status_detail"] == "no_other_model_has_quantity":
            parts.append("Resting on PolicyEngine alone: no other model computes state payroll taxes.")
        else:
            parts.append("Resting on PolicyEngine alone (" + row["status_detail"] + ").")
        if row["trivial"] == "true":
            parts.append("A zero with no wages stated on any member.")
    if row["board_record"]:
        parts.append("The board's exclusion record for " + row["board_record"] + ".")
    return " ".join(parts)


def build_rows(data: Data) -> list[dict]:
    rows = [cell(data, case, quantity) for quantity in QUANTITIES for case in data.cases]
    return rows


FIELDS = [
    "case_id", "quantity", "board_output", "key_value", "key_source", "key_equals_engine_rerun",
    "board_scores_it", "board_record", "status", "status_detail", "contested_reasons",
    "contesting_cause_ids", "trivial", "agreeing_runs", "apart_runs", "reproduced_by",
    "reproducing_lineages", "reproducing_models", "reproducing_releases", "law_year",
    "input_map_versions", "reproduction_scope", "shares_with_key_run", "shares_measured_on",
    "shared_readings", "shared_map_computed", "facts_no_other_model_takes",
    "also_agrees_under_2025_law", "agreeing_runs_2025", "cause_ids", "second_map_taxcalc",
    "second_map_taxsim", "second_map_taxcalc_class", "second_map_taxsim_class", "interim", "note",
]


def render_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


# ---------------------------------------------------------------- docs/coverage.md
SHORT = {L1: "income tax", L2: "refundable credits", SE: "self-employment tax", FP: "federal payroll",
         SP: "state payroll"}
MEMBER = re.compile(r"\b(?:dependent|child)\d+\b")
AGE_INCOME = re.compile(r" \(age [^)]*\)")
NOTE_WIDTH = 220  # characters of a map note shown in a table; results/answers.csv holds the whole note


def cell_text(text: str) -> str:
    text = text.replace("|", "/")
    return text if len(text) <= NOTE_WIDTH else text[:NOTE_WIDTH].rstrip() + " ..."


def table(header: list[str], body: list[list], align: str | None = None) -> list[str]:
    align = align or ("|---" + "|---:" * (len(header) - 1) + "|")
    return ["| " + " | ".join(header) + " |", align] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body]


def count_table(rows: list[dict], label: str) -> list[str]:
    body = []
    for quantity in QUANTITIES:
        sub = [r for r in rows if r["quantity"] == quantity]
        c = Counter(r["status"] for r in sub)
        body.append([f"`{quantity}`"] + [c.get(s, 0) for s in STATUSES] + [len(sub)])
    c = Counter(r["status"] for r in rows)
    body.append(["All quantities"] + [c.get(s, 0) for s in STATUSES] + [len(rows)])
    return table([label, "Reproduced", "Contested", "Resting on PolicyEngine alone", "Cells"], body)


def entries_moving(data: Data, run: str, quantity: str) -> Counter:
    table_year = data.runs[run]["period"]
    return Counter(r["cause_id"] for r in data.cause_cells
                   if r["run"] == run and r["quantity"] == quantity and r["table"] == table_year)


def entry_list(data: Data, moved: Counter) -> str:
    return "; ".join(f"`{cid}` ({n})" for cid, n in sorted(moved.items(), key=lambda kv: data.cause_order[kv[0]]))


def model_lines(data: Data, rows: list[dict], run: str) -> list[str]:
    """Counted facts for one model's 2026 run, line by line."""
    out = []
    for quantity in QUANTITIES:
        sub = [r for r in rows if r["quantity"] == quantity]
        if not any(data.value(run, r["case_id"], quantity) is not None for r in sub):
            statuses = sorted({data.status_of(run, r["case_id"], quantity) for r in sub})
            out.append(f"- {LINE_NAME[quantity].capitalize()}: no answer on any household "
                       f"(`results/answers.csv` status {', '.join(f'`{s}`' for s in statuses)}).")
            continue
        gives = [r for r in sub if run in r["agreeing_runs"].split(";")]
        scored = [r for r in sub if r["board_scores_it"] == "yes"]
        text = (f"- {LINE_NAME[quantity].capitalize()}: gives the key's answer within $1 on {len(gives)} of "
                f"{len(sub)} households ({sum(1 for r in gives if r['board_scores_it'] == 'yes')} of the "
                f"{len(scored)} the board scores).")
        moved = entries_moving(data, run, quantity)
        if moved:
            text += " Entries that move its answer, with households: " + entry_list(data, moved) + "."
        out.append(text)
    return out


def model_lines_2025(data: Data, run: str) -> list[str]:
    run_2025 = data.counterpart_2025.get(run)
    if run_2025 is None:
        return ["- No run of this model for tax year 2025."]
    out = []
    for quantity in FOUR_LINES:
        same = sum(agree(data.value(run_2025, c, quantity), data.value(data.key_run_2025, c, quantity))
                   for c in data.cases)
        same_2026 = sum(agree(data.value(run, c, quantity), key_value(data, c, quantity)[0]) for c in data.cases)
        text = (f"- {LINE_NAME[quantity].capitalize()}: `{run_2025}` agrees with `{data.key_run_2025}` on "
                f"{same} of {len(data.cases)} households (the 2026 run agrees with the 2026 key on {same_2026}).")
        moved = entries_moving(data, run_2025, quantity)
        if moved:
            text += " Entries that move its 2025 answer, with households: " + entry_list(data, moved) + "."
        out.append(text)
    return out


def model_notes(data: Data, run: str, column: str) -> list[tuple[str, str, int]]:
    """The map's notes on one run's answers in `column` (unexpressed_facts or map_computed), other
    than named readings and the shared state and local tax amount: (note, lines, households)."""
    found = defaultdict(lambda: (set(), set()))
    for (r, case, quantity), row in data.answers.items():
        if r != run or quantity not in QUANTITIES:
            continue
        for text in split_notes(row[column]):
            if column == "unexpressed_facts" and (
                    text.startswith(SALT_NOTE) or any(v in text for v in data.readings.values())):
                continue
            key = AGE_INCOME.sub("", MEMBER.sub("a member", text))
            found[key][0].add(quantity)
            found[key][1].add(case)
    out = [(text, ", ".join(SHORT[q] for q in QUANTITIES if q in lines), len(cases))
           for text, (lines, cases) in found.items()]
    return sorted(out, key=lambda t: (-t[2], t[0]))


def notes_table(data: Data, run: str, column: str, label: str) -> list[str]:
    notes = model_notes(data, run, column)
    if not notes:
        return [f"No `{column}` notes on this run's answers."]
    return table([label, "Lines", "Households"], [[cell_text(n), lines, k] for n, lines, k in notes],
                 "|---|---|---:|")


def one_model_facts(board_facts: list[dict], missing: str, present: str) -> list[dict]:
    def dead(field: str) -> bool:
        return not field.strip() or "(sent as 0)" in field or "(no effect" in field

    return [r for r in board_facts
            if r["effect_on_the_four_lines_in_the_key"] in ("federal", "indirect")
            and dead(r[missing]) and not dead(r[present])]


RULES_TEXT = """\
`scripts/make_cell_status.py` assigns every status by the rules below; nobody edits its output by
hand. It reads `results/answers.csv`, `results/runs.csv`, `results/models.csv`,
`results/bindings.csv`, `results/causes.csv`, `results/cause_cells.csv`, the agreement tables in
`results/agreement/`, the dossiers' stated facts and board exclusion records
(`results/dossiers/`), `maps/board_facts.csv`, the `READINGS` of `keycheck/unit.py` and, where
they exist, the second map's answers (`second_map/<engine>/answers_2026.csv`).

**Cells.** One row per board household and quantity for tax year {period} ({n_rows} rows): the
three federal lines (`{l1}`, `{l2}`, `{se}`), the federal part of payroll tax (`{fp}`) and the
state part (`{sp}`). The key's value for the three federal lines comes from the committed key
(`{key_run}`). The committed key publishes only `payroll_tax`, federal and state together, so the
script splits it by the parts of the key engine's rerun (`{rerun}`) and checks that the parts sum
to the committed amount within $1 (`key_source`). The board scores or excludes `payroll_tax` as a
whole, so both payroll parts take its `board_scores_it`.

**Lineage.** Two runs count as one lineage where they share an engine (`results/models.csv`
`lineage`), a convention file or an input-map file (`results/runs.csv`). The Tax-Calculator and
TAXSIM runs share `keycheck/unit.py`, so they form one lineage: a cell both reproduce counts once,
and `reproducing_lineages` names that one lineage. The PolicyEngine reruns belong to the key's
lineage and reproduce nothing. An input that one run computed and another takes (the state and
local tax amount) qualifies the cell instead (`shares_with_key_run`, below).

**Agreement.** A run of another lineage gives the key's answer when it answers within $1, the
board's exact-match rule (`agreeing_runs`; `apart_runs` lists the runs that answer and differ).

**Rules, in order.**

1. `resting_on_one_model` with detail `no_other_model_has_quantity`: no run of another lineage
   answers for the quantity (state payroll taxes).
2. `contested`, when any of these holds, whether or not a run agrees. `contested_reasons` lists
   every reason that holds, `status_detail` the first in this order, and `contesting_cause_ids`
   the entries behind them.
   - `key_not_supported_by_law`: an entry in `results/cause_cells.csv` moves the key's own answer
     by more than $1, and its kind is `model-law-departure`, `model-no-provision` or
     `key-decided-value`; or a `shared-reading` entry lists the household and the board's own
     exclusion record for the output holds an alternative more than $1 from the key for a reason
     other than `reference_depends_on_unlisted_input` (such as `reference_engine_defect`). An entry
     of kind `unexplained` takes no position, so it contests nothing; a kind the script does not
     know stops the script.
   - `turns_on_unstated_fact`: an entry of kind `pe-default-unstated-fact`, `shared-reading` or
     `map-limit` moves the key's answer by more than $1; or a `shared-reading` entry lists the
     household (`households_shared`) and its position (`who_is_right`) names the household's
     answer in a sentence that says what the answer would be (the pattern `NNN's answer` or
     `NNN's scored answer` in a sentence with "would"); or a `shared-reading` entry lists the
     household and the board's own exclusion record for the output, of reason
     `reference_depends_on_unlisted_input`, holds an alternative more than $1 from the key; or no
     run of another lineage agrees and an entry that moves a run that stands apart is a
     `shared-reading`, or a `map-limit` whose `release_or_build` names a `READINGS` key.
   - `key_decided_value_unscored`: no run of another lineage agrees, an entry has rows on the cell
     in `results/cause_cells.csv`, the board does not score the output, and the committed key
     differs from the key engine's rerun by more than $1: the key holds a value the board decided
     on an earlier release.
   - `three_answers_differ`: no two of the key, the Tax-Calculator answer and the TAXSIM answer
     agree, and an entry has rows on the cell.
3. `reproduced`: a run of another lineage gives the key's answer within $1 and rule 2 does not
   apply. `status_detail` reads `key_salt_amount_itemized` when every reproducing run itemizes on
   PolicyEngine's state and local tax amount (`results/bindings.csv`
   `input_from_other_run_bears_on_answer`, which the script checks against the answers table's
   note on that input), so a count can leave those cells out; otherwise `no_input_from_key_run`.
4. `resting_on_one_model` otherwise: no run of another lineage agrees and no entry disputes the
   key. The detail reads `no_other_run_takes_a_fact` when every entry that moves the runs that
   stand apart has kind `model-no-provision` or `map-limit`; `other_runs_depart_from_law` when
   some has kind `model-law-departure` and the rest have those kinds; `unexplained` otherwise (no
   entry covers a run that stands apart, or an entry of another kind does).

Every contested cell therefore names at least one entry, and the entry applies to the cell: a row
in `results/cause_cells.csv` for the cell, or a `shared-reading` entry whose `households_shared`
lists the household (for the 2026 table) and whose `quantities` hold the line.

**Within `reproduced`.** `reproduction_scope` reads `both_runs_one_lineage` when both runs give
the key. When one run gives it and the other stands apart, it names why the other stands apart:
that model's own gap or defect (`one_run_other_model_gap`: entries of kind `model-no-provision` or
`model-law-departure`), a limit of this repo's map for that model (`one_run_other_map_limit`),
both (`one_run_other_gap_and_map_limit`), or no entry (`one_run_other_unexplained`); `cause_ids`
names the entries. A cell both runs reproduce rests on two engines that share one input map; a
cell one run reproduces rests on one engine and that map.

**What a reproduction shares with the key's run** (`shares_with_key_run`). For each reproducing
run the script lists `key_salt_amount` (the run itemizes, so PolicyEngine's state and local tax
amount bears on the answer; income tax lines only), `map_computed_amount` (an amount
`keycheck/statute.py` computes because the model takes it as given; `shared_map_computed` names
each) and `reading` (a named reading of a fact the household does not state, from
`keycheck/unit.py` `READINGS`; `shared_readings` names each). The cell reports the reproducing run
that shares least (`shares_measured_on`), ranked first by the state and local tax amount, then by
map-computed amounts, then by readings. `nothing` means that run shares nothing with the key's run
but the household's stated facts. The flags come from the answers table's notes on each cell, so a
reading counts wherever the map applies it to a fact the household lists, whether or not it moves
the answer.

**Zeros** (`trivial`). A cell reads `trivial` when the key's value is 0 and the household states
none of the tax's base: no self-employment, farm or partnership self-employment income for
`{se}`; no wages on any member for the two payroll parts. The flag leaves the status as the rules
give it and lets a count leave the cell out. The income tax lines carry no such flag: a zero there
comes out of income, deductions and credits that the other models compute.

**Tax year 2025.** For a reproduced cell, `also_agrees_under_2025_law` says whether each
reproducing model's 2025 run also agrees with the key engine's 2025 run (`{key_run_2025}`): `yes`,
`partly` or `no`; other cells read `not_applicable`. `agreeing_runs_2025` lists, on every cell, the
2025 runs that agree with that run. The 2025 table tests the engines on these households, not the
2026 key.

**The second map.** A second pair of input maps, written without sight of the first, leaves its
answers in `second_map/<engine>/answers_2026.csv` (`case_id`, `quantity`, `value`). Where that file
exists the script compares each answer with the key itself and fills `second_map_taxcalc` and
`second_map_taxsim`: `agrees` or `differs` (within $1); `second_map_error` where the comparison
(`results/second_map/<engine>_answers_diff.csv`) rules the second map's answer on that line an
error of the second map (a `class` that holds `second_map_errs`, alone or with a reading);
`no_answer` (no value for the cell); or `not_covered` (state payroll). Where the answers file does
not exist the column reads `pending`. A `second_map_error` answer neither reproduces nor contests
anything on its cell. `second_map_taxcalc_class` and `second_map_taxsim_class` copy the
comparison's `class`; the script reads nothing else from the comparison files, whose first-map
columns describe the first map at the commit they name. A second-map run that reproduces the key
differs in lineage from the first map's run of the same engine only in its input map: the two
share the board's stated facts, the state and local tax file and the engine. The second-map
columns stay outside the status rules; they show whether a cell's agreement survives a change of
input map.
"""


def render_coverage(data: Data, rows: list[dict]) -> str:
    lines = [f"# Coverage of the {data.period} answer key", ""]
    lines += [
        "**Every status here is interim.** The statuses rest on this repo's input maps (`keycheck/`);",
        "they stay interim until those maps have had an independent read, and every row of",
        "`results/cell_status.csv` carries `interim` true until then. No status says the key is right:",
        "each cell carries one of three statuses, `reproduced` (reproduced by a run of another lineage),",
        "`contested`, or `resting_on_one_model` (resting on PolicyEngine alone).",
        "",
        "This file says what Tax-Calculator and NBER TAXSIM can and cannot reproduce of PolicyBench's",
        f"{data.period} answer key, and gives the count of the key's cells by status.",
        "`scripts/make_cell_status.py` writes it and `results/cell_status.csv`; rerun",
        "`python3 scripts/make_cell_status.py` after any regeneration of the files it reads.",
        "",
        "## Status rules",
        "",
    ]
    lines += RULES_TEXT.format(
        period=data.period, n_rows=len(rows), l1=L1, l2=L2, se=SE, fp=FP, sp=SP, key_run=data.key_run,
        rerun=data.rerun, key_run_2025=data.key_run_2025).rstrip("\n").split("\n")

    scored = [r for r in rows if r["board_scores_it"] == "yes"]
    lines += ["", "## Counts", "", "All cells:", ""]
    lines += count_table(rows, "Quantity")
    lines += ["", "Cells the board scores:", ""]
    lines += count_table(scored, "Quantity")
    lines += ["", "By status detail:", ""]
    body = []
    for status in STATUSES:
        for detail in DETAILS[status]:
            n_all = sum(1 for r in rows if r["status"] == status and r["status_detail"] == detail)
            n_scored = sum(1 for r in scored if r["status"] == status and r["status_detail"] == detail)
            body.append([f"`{status}`", f"`{detail}`", n_all, n_scored])
    lines += table(["Status", "Detail", "All cells", "Scored cells"], body, "|---|---|---:|---:|")
    lines += ["", "Contested cells by reason (a cell counts under every reason that holds):", ""]
    body = [[f"`{reason}`", sum(1 for r in rows if reason in r["contested_reasons"].split(";")),
             sum(1 for r in scored if reason in r["contested_reasons"].split(";"))] for reason in CONTESTED_ORDER]
    lines += table(["Reason", "All cells", "Scored cells"], body, "|---|---:|---:|")

    reproduced = [r for r in rows if r["status"] == "reproduced"]
    lines += ["", "Reproduced cells by what the reproduction shares with the key's run:", ""]
    share_counts = Counter(r["shares_with_key_run"] for r in reproduced)
    body = [[f"`{k}`", v, sum(1 for r in reproduced if r["shares_with_key_run"] == k and r["board_scores_it"] == "yes")]
            for k, v in sorted(share_counts.items(), key=lambda kv: (kv[0] != "nothing", kv[0]))]
    lines += table(["Shares with the key's run", "Cells", "Scored cells"], body, "|---|---:|---:|")
    lines += ["", "Reproduced cells by how many runs give the key:", ""]
    scope_counts = Counter(r["reproduction_scope"] for r in reproduced)
    body = [[f"`{s}`", scope_counts.get(s, 0),
             sum(1 for r in reproduced if r["reproduction_scope"] == s and r["board_scores_it"] == "yes")]
            for s in SCOPES]
    lines += table(["Reproduction scope", "Cells", "Scored cells"], body, "|---|---:|---:|")
    trivial = [r for r in rows if r["trivial"] == "true"]
    nothing = [r for r in reproduced if r["shares_with_key_run"] == "nothing" and r["trivial"] == "false"
               and r["status_detail"] == "no_input_from_key_run"]
    lines += [
        "",
        f"{len(trivial)} cells read `trivial` ({sum(1 for r in trivial if r['status'] == 'reproduced')} reproduced, "
        f"{sum(1 for r in trivial if r['status'] == 'resting_on_one_model')} resting on PolicyEngine alone). "
        f"{len(nothing)} reproduced cells ({sum(1 for r in nothing if r['board_scores_it'] == 'yes')} scored) are "
        "not trivial and share nothing with the key's run but the household's stated facts.",
    ]
    recorded = [r for r in rows if r["status"] == "resting_on_one_model" and r["board_record"]]
    if recorded:
        lines += [
            "",
            f"{len(recorded)} cells resting on PolicyEngine alone carry a board exclusion record "
            f"({', '.join(r['case_id'].split('_')[-1] + ' ' + SHORT[r['quantity']] for r in recorded)}). "
            "No other model computes the quantity, so no cause entry covers them and the rules leave them "
            "resting on PolicyEngine alone; `board_record` gives the record.",
        ]

    if data.second_map:
        lines += ["", "The second map against the key, by status (state payroll cells left out; each engine's "
                  "columns read agrees / differs / second-map error):", ""]
        body = []
        for status in STATUSES:
            sub = [r for r in rows if r["status"] == status and r["quantity"] != SP]
            if not sub:
                continue
            per_engine = []
            for engine in SECOND_MAP_ENGINES:
                c = Counter(r[f"second_map_{engine}"] for r in sub)
                per_engine.append(f"{c['agrees']} / {c['differs']} / {c['second_map_error']}")
            either = sum(1 for r in sub if "agrees" in (r["second_map_taxcalc"], r["second_map_taxsim"]))
            body.append([f"`{status}`", len(sub)] + per_engine + [either, len(sub) - either])
        lines += table(["Status", "Cells"] + [DISPLAY[e] for e in SECOND_MAP_ENGINES]
                       + ["Either agrees", "Neither agrees"], body, "|---|---:|---:|---:|---:|---:|")

        def listing(cells):
            return ", ".join(f"{r['case_id'].split('_')[-1]} {SHORT[r['quantity']]} ("
                             + ", ".join(f"{DISPLAY[e]} {r[f'second_map_{e}']}" for e in SECOND_MAP_ENGINES) + ")"
                             for r in cells)

        neither = [r for r in rows if r["status"] == "reproduced" and r["quantity"] != SP
                   and "agrees" not in (r["second_map_taxcalc"], r["second_map_taxsim"])]
        if neither:
            lines += ["", "Reproduced cells that no second-map run gives (a `second_map_error` answer counts for "
                      "neither side; where every second-map answer differs, the first map's agreement does not "
                      "survive the change of map): " + listing(neither) + "."]
        through_second = [r for r in rows if r["status"] != "reproduced" and r["quantity"] != SP
                          and "agrees" in (r["second_map_taxcalc"], r["second_map_taxsim"])]
        if through_second:
            lines += ["", "Cells the rules leave contested or resting on PolicyEngine alone where a second-map run "
                      "gives the key: " + listing(through_second) + "."]
        docs = [f"`docs/second-map-{e}.md`" for e in SECOND_MAP_ENGINES if (data.root / f"docs/second-map-{e}.md").exists()]
        lines += ["", "The columns read the second map's answers files as they stand when the script runs. "
                  + ("Its comparison documents: " + ", ".join(docs) + "." if docs else
                     "Its comparison documents (`docs/second-map-<engine>.md`) do not exist yet, so read these "
                     "columns as a first measurement.")]
    else:
        lines += ["", "The second map's answers do not exist yet (`second_map/<engine>/answers_2026.csv`), so "
                  "`second_map_taxcalc` and `second_map_taxsim` read `pending` on every row: that measurement "
                  "is pending."]

    contested = [r for r in rows if r["status"] == "contested"]
    lines += ["", "Contested cells:", ""]
    body = [[r["case_id"].split("_")[-1], SHORT[r["quantity"]], r["board_scores_it"], r["key_value"],
             r["contested_reasons"].replace(";", ", "),
             ", ".join(f"`{c}`" for c in r["contesting_cause_ids"].split(";")),
             r["agreeing_runs"].replace(";", ", ") or "none"] for r in contested]
    lines += table(["Case", "Line", "Scored", "Key", "Reasons", "Entries", "Runs that give the key"], body,
                   "|---|---|---|---:|---|---|---|")

    for run in data.other_runs:
        model = data.runs[run]["model"]
        lines += ["", f"## {DISPLAY.get(model, model)} ({data.runs[run]['release']})", "",
                  f"### Tax year {data.period}", ""]
        lines += model_lines(data, rows, run)
        lines += [""] + MODEL_TEXT.get(model, {}).get("2026", "").rstrip("\n").split("\n")
        lines += ["", f"Notes the map leaves on `{run}`'s answers, other than named readings and the shared "
                  "state and local tax amount (`results/answers.csv` `unexpressed_facts`):", ""]
        lines += notes_table(data, run, "unexpressed_facts", "Note")
        lines += ["", f"Amounts this repo computes for `{run}` because the model takes them as given, or "
                  "enters another way (`results/answers.csv` `map_computed`):", ""]
        lines += notes_table(data, run, "map_computed", "Amount")
        lines += ["", "### Tax year 2025, where it differs", ""]
        lines += model_lines_2025(data, run)
        lines += [""] + MODEL_TEXT.get(model, {}).get("2025", "").rstrip("\n").split("\n")

    lines += ["", "## Stated facts no model but PolicyEngine takes", ""]
    lines += [
        "From `maps/board_facts.csv`: stated facts with an effect on the four federal lines (federal, or",
        "indirect through the state and local tax deduction) that neither Tax-Calculator nor TAXSIM takes:",
        "neither has a field, the map sends the field as 0, or the field has no effect in 2025 or 2026. On",
        "the income tax lines `results/cell_status.csv` names the federal ones a household states",
        "(`facts_no_other_model_takes`).",
        "",
    ]
    body = [[f"`{f['fact']}`", f["households_stating_it"], f["effect_on_the_four_lines_in_the_key"],
             f["taxcalc_field"] or "none", f["taxsim_field"] or "none", f["note"] or ""]
            for f in data.no_other_model_facts]
    lines += table(["Fact", "Households", "Effect", "Tax-Calculator", "TAXSIM", "Note"], body,
                   "|---|---:|---|---|---|---|")
    for missing, present, name, other in (("taxsim_field", "taxcalc_field", "TAXSIM", "Tax-Calculator"),
                                          ("taxcalc_field", "taxsim_field", "Tax-Calculator", "TAXSIM")):
        facts = one_model_facts(data.board_facts, missing, present)
        lines += ["", f"Facts {name} does not take and {other} does (a cell that turns on one can still "
                  f"reproduce through {other}):", ""]
        if facts:
            body = [[f"`{f['fact']}`", f["households_stating_it"], f["effect_on_the_four_lines_in_the_key"],
                     f[present], f[missing] or "none"] for f in facts]
            lines += table(["Fact", "Households", "Effect", other, name], body, "|---|---:|---|---|---|")
        else:
            lines += ["None."]
    lines += [""] + FACTS_TEXT.rstrip("\n").split("\n")
    return "\n".join(lines) + "\n"


MODEL_TEXT = {
    "taxcalc": {
        "2026": """\
What it can reproduce, and what it cannot (each claim cites `evidence/taxcalc.md` by item):

- **Tax before refundable credits** (`c09200 - setax - ptax_amc`, `scripts/run_taxcalc.py`; C4).
  It computes the 2026 rate schedules (D10, D15), the standard deduction with the aged and blind
  amounts and the 2026 charitable deduction for non-itemizers (D7), the deductions for tips,
  overtime, car-loan interest and seniors (D2-D5), itemized deductions with the $40,400 state and
  local tax cap and the medical and charitable floors (B11, B13), the 2/37 limit (D6), the
  qualified business income deduction with the 2026 $400 minimum (D9, D14), the AMT (D12), the
  net investment income tax (D13), the child and other-dependent credits (D17) and the 2026 child
  care credit rates (D16).
- It takes as given the IRA deduction, the student loan interest deduction, the educator expense
  limit, mortgage interest under the debt limit and the saver's credit (B2, B12, D22;
  `evidence/law-2026.md` Part G), so `keycheck/statute.py` computes them; agreement on such a cell
  tests this repo's reading of the statute as much as the model (`shared_map_computed`).
- It has no input for qualified REIT dividends and PTP income (D9), no disability path for the
  credit for the elderly or disabled (D21), and no input for a divorce instrument dated before 2019
  (B3). Rent outside `e26270` and `e27200` does not count as qualified business income (D9), so
  the map's reading `rental_qbi` decides two households
  (`map-rental-not-qualified-business-income`).
- It has no state model, so it takes PolicyEngine's state and local tax amount
  (`results/runs.csv`); where it itemizes, agreement tests the federal computation given that
  amount.
- **Refundable credits** (`refund`; C5). It computes the EITC by formula (D19) and the refundable
  child credit with the three-child alternative (D18). The run switches off its claiming lottery
  (A9, A12; `results/runs.csv`). The refundable American opportunity credit needs a tentative
  credit as input (D20).
- **Self-employment tax** (`setax`; C2): per person, on 92.35% of net earnings, with the $400 floor
  (B10) and the Social Security wage base shared with wages.
- **Federal employee payroll tax** (`ptax_was / 2 + ptax_amc`, `scripts/run_taxcalc.py`; C1, C7).
  A record holds the head and spouse only (B35); the map gives a member with earnings of their own
  a record of their own (`scripts/run_taxcalc.py`).
- **State employee payroll tax**: no state model; every cell rests on PolicyEngine alone.""",
        "2025": """\
The same code gives 2025 law (`evidence/taxcalc.md` B10, B11, D6, D7, D14, D16;
`evidence/law-2026.md` Part F): the $176,100 wage base, the $40,000 state and local tax cap, no
charitable deduction for non-itemizers, no 2/37 limit, no $400 minimum qualified business income
deduction and the pre-2026 child care credit rates, as the law has them for 2025.""",
    },
    "taxsim": {
        "2026": """\
What it can reproduce, and what it cannot (each claim cites `evidence/taxsim.md` by probe or item):

- **Tax before refundable credits** (`fiitax + v25 + actc`, `scripts/run_taxsim.py`; P11.2). The
  build gives the 2026 ordinary brackets (P12.1), the standard deduction with the 65-and-over
  amount (P8.3), the senior deduction (L7, P8.4) and the $2,200 child credit with its phase-out
  (L5, P5.4) as the law has them.
- It has no input for overtime, tips, car-loan interest (P1.2, B2), blindness (P1.2, P8.3),
  tax-exempt interest (P15.5) or pre-tax contributions (P1.2), and no saver's credit
  (`taxsim-no-savers-credit`). For 2026 it has no charitable deduction for non-itemizers (P9.5)
  and no 2/37 limit (P9.6); it caps state and local taxes at 2025's $40,000 (P9.1), pays the child
  care credit at the pre-2026 rates (P5.2), gives no $400 minimum qualified business income
  deduction (P13.4), lacks the 2026 AMT exemption phase-out (P11.4, P13.1) and sets capital gains
  breakpoints about 0.9% above the published ones (P12.2).
- The map enters deductible medical expenses and charitable gifts in `mortgage`, which the build
  deducts uncapped (D6, P9.3), so `keycheck/statute.py` applies the floors first
  (`shared_map_computed`). Adjustments to income enter as negative `nonprop`, which also lowers
  earned income for the EITC (P7.1; `map-ira-deduction-in-nonprop-cuts-eitc`). Like
  Tax-Calculator it takes PolicyEngine's state and local tax amount (`results/runs.csv`).
- **Refundable credits** (`v25 + actc`, `scripts/run_taxsim.py`). The 2026 EITC with children
  matches the law on the dependent-count path the map uses and misses it on the age path (P3.4,
  P4.2). The refundable child credit comes out short by the child care credit (P3.7, P5.3), and the
  three-child alternative counts the whole self-employment tax
  (`taxsim-three-child-refundable-credit-alternative`; `probes/taxsim/actc_3kids_alt.in.csv`). The
  build denies the EITC at investment income equal to the limit (P15.4) and counts `nonprop` as
  earned income (P6.10).
- **Self-employment tax**: the map splits it out of `tfica` with a second run that zeroes the
  self-employment boxes (P10; `scripts/run_taxsim.py`). The build charges self-employment tax
  below $400 of net earnings (P10.3), and a loss in one box does not offset earnings in another
  (P7.4).
- **Federal employee payroll tax** (`tfica` less self-employment tax): matches the law's formula on
  every probe (P10.1, P10.2).
- **State employee payroll tax**: no probe found a column for it (an inference in
  `evidence/taxsim.md`, board facts list); every cell rests on PolicyEngine alone.""",
        "2025": """\
The entries `results/causes.csv` limits to 2026 (`law_years`: `taxsim-no-nonitemizer-charitable-deduction`,
`taxsim-2026-child-care-credit-old-rates`, `taxsim-2026-salt-cap-40000`) do not apply at 2025 law.
At 2025 law the state and local tax cap matches the law (P9.1), the EITC matches the law on every
dependent path (P4.1), and for a single filer the qualified business income deduction's phase-in
for a specified service business matches the published numbers (P13.2). The missing inputs (overtime, blindness, tax-exempt interest, pre-tax contributions), the missing
saver's credit and the short refundable child credit (P5.3) stay, and the capital gains
breakpoints sit about 0.2% above the published ones (P12.2).""",
    },
}

FACTS_TEXT = """\
Beyond the stated facts:

- **State payroll taxes** (`state_employee_payroll_tax`): neither model computes them
  (`results/answers.csv` status `not_covered`), so every such cell rests on PolicyEngine alone,
  and the board's `payroll_tax` holds them.
- **State and local income or sales tax paid** does not appear among the stated facts. Both models
  take PolicyEngine's amount (`results/runs.csv`, `results/bindings.csv`
  `inputs_from_other_runs`); where a model itemizes, its answer rests on that amount
  (`key_salt_amount` in `shares_with_key_run`)."""


# ---------------------------------------------------------------- main
def build(root: Path = ROOT) -> tuple[str, str, list[dict]]:
    data = Data(root)
    rows = build_rows(data)
    return render_csv(rows), render_coverage(data, rows), rows


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="write results/cell_status.csv and docs/coverage.md under this folder")
    args = parser.parse_args(argv)
    csv_text, doc_text, rows = build(ROOT)
    out = args.out_dir or ROOT
    (out / "results").mkdir(parents=True, exist_ok=True)
    (out / "docs").mkdir(parents=True, exist_ok=True)
    (out / "results/cell_status.csv").write_text(csv_text)
    (out / "docs/coverage.md").write_text(doc_text)
    counts = Counter(r["status"] for r in rows)
    print(f"wrote {len(rows)} rows: " + ", ".join(f"{s} {counts.get(s, 0)}" for s in STATUSES))


if __name__ == "__main__":
    main()
