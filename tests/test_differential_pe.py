"""Differential test: the return keycheck/unit.py derives from the board's stated facts against
what PolicyEngine 2.60.0 derived in its own run on the same 100 households
(results/pe/board100_pe2.60.0_board_2026.csv), for what both compute from the same rule.

The households come from the dossiers' `stated_facts` (the board's scenarios.csv sits in the
git-ignored work/ folder). Where the two differ by a reading or a rule the maps name, the
household is listed below with the reason; any other difference, or a listed one that goes
away, fails the test, so a change to either side shows up here.
"""

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from keycheck import map_taxcalc as MT  # noqa: E402
from keycheck import statute as S  # noqa: E402
from keycheck import unit as U  # noqa: E402

PE = ROOT / "results" / "pe" / "board100_pe2.60.0_board_2026.csv"
TAXCALC = ROOT / "results" / "taxcalc" / "board100_tc6.9.0_2026.csv"
DOSSIERS = sorted((ROOT / "results" / "dossiers").glob("scenario_*.json"))

# policyengine-us filing_status enum order (FilingStatus: SINGLE, JOINT, SEPARATE,
# HEAD_OF_HOUSEHOLD, SURVIVING_SPOUSE), as the run CSV writes its index.
PE_STATUS = {S.SINGLE: 0, S.JOINT: 1, S.SEPARATE: 2, S.HEAD_OF_HOUSEHOLD: 3, S.SURVIVING_SPOUSE: 4}

KNOWN = {
    # scenario_093: a 27-year-old member stated disabled who earns $45,000. The map does not
    # read a member with earnings as permanently and totally disabled (READINGS["is_disabled"]);
    # PolicyEngine claims them.
    "dependents": {"scenario_093": (0, 1)},
    # 067 (a 23-year-old) and 064 (a 27-year-old): a member stated disabled with no earnings,
    # an EITC child under the is_disabled reading; PolicyEngine 2.60.0 claims each as a
    # dependent but not as an EITC child (is_eitc_qualifying_child 0 in its run).
    "eitc_children": {"scenario_064": (3, 2), "scenario_067": (1, 0)},
    # Per filer. The map limits traditional plus Roth 401(k) deferrals to the filer's own
    # wages (READINGS["deferrals_wages"]); PolicyEngine 2.60.0 does not: each of these heads
    # states a desired deferral and no wages. (At the tax-unit level 064 differs too, because
    # PolicyEngine's unit total adds a dependent's own deferral; per filer it agrees.)
    "traditional_401k": {
        ("scenario_003", "head"): (0.0, 23925.80), ("scenario_004", "head"): (0.0, 15436.0),
        ("scenario_073", "head"): (0.0, 5556.96), ("scenario_085", "head"): (0.0, 8.49),
        ("scenario_089", "head"): (0.0, 5402.60),
    },
    # Map version 2026-11-11.1 (the board's rule for unstated facts).
    # 056 states an HSA deduction of 9,915.44; the map allows the head's self-only 223(b)
    # limit (READINGS["hsa"]); PolicyEngine takes the stated amount.
    "hsa": {"scenario_056": (4400.0, 9915.44)},
    # 038: Schedule C 15,525 and premiums of 100, no is_self_employed and no has_esi: the map
    # deducts them under 162(l) (READINGS["self_employed_health_insurance"]); PolicyEngine's
    # deduction needs is_self_employed.
    "se_health_insurance": {"scenario_038": (100.0, 0.0)},
    # 72(t) at PolicyEngine's AGI (READINGS["retirement_penalty"]): 023 (403(b) 8,000 at 28),
    # 064 (401(k) 20,000 at 48), 074 (IRA 384 at 54); PolicyEngine's qualified_retirement_penalty
    # is an input with no formula, 0 on the board.
    "retirement_penalty": {"scenario_023": (800.0, 0.0), "scenario_064": (2000.0, 0.0), "scenario_074": (38.4, 0.0)},
}

pytestmark = pytest.mark.skipif(not PE.exists() or len(DOSSIERS) != 100, reason="needs the PolicyEngine run and the 100 dossiers")


def _pe() -> dict:
    """{case: {variable: value}}, with each person-level variable also under
    `persons:<variable>` as {person name: value}."""
    rows: dict[str, dict[str, dict]] = {}
    with open(PE, newline="") as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(row["scenario_id"], {})[row["variable"]] = row
    values: dict[str, dict] = {}
    for case, by_variable in rows.items():
        names = json.loads(by_variable["person_names"]["persons"])
        out = values.setdefault(case, {})
        for variable, row in by_variable.items():
            try:
                out[variable] = float(row["value"])
            except ValueError:
                continue
            if row["persons"] and variable != "person_names":
                out["persons:" + variable] = dict(zip(names, json.loads(row["persons"])))
    return values


def _units() -> list[U.Unit]:
    return [U.build(json.loads(path.read_text())["stated_facts"], 2026) for path in DOSSIERS]


@pytest.fixture(scope="module")
def pairs():
    pe = _pe()
    return [(unit, pe[unit.case_id]) for unit in _units()]


def _differences(pairs, ours, theirs, tolerance=0.5):
    out = {}
    for unit, pe in pairs:
        a, b = ours(unit), pe[theirs]
        if abs(a - b) > tolerance:
            out[unit.case_id] = (round(a, 2), round(b, 2))
    return out


def _same_keys_close(found, known):
    assert set(found) == set(known), (found, known)
    for key, (a, b) in known.items():
        assert abs(found[key][0] - a) < 0.01 and abs(found[key][1] - b) < 0.01, (key, found[key], (a, b))


def test_filing_status_on_all_100(pairs):
    assert _differences(pairs, lambda u: PE_STATUS[u.status], "filing_status") == {}


def test_dependents(pairs):
    found = _differences(pairs, lambda u: len(u.dependents), "tax_unit_dependents")
    _same_keys_close(found, KNOWN["dependents"])


def test_child_credit_children_on_all_100(pairs):
    under_17 = lambda u: u.count(lambda d: d["kind"] == "qualifying_child" and d["age"] < 17)  # noqa: E731
    assert _differences(pairs, under_17, "ctc_qualifying_children") == {}


def test_eitc_children(pairs):
    found = _differences(pairs, lambda u: u.count(lambda d: d["kind"] == "qualifying_child"), "eitc_child_count")
    _same_keys_close(found, KNOWN["eitc_children"])


def _per_filer(pairs, ours, variable, tolerance=0.5):
    out = {}
    for unit, pe in pairs:
        by_person = pe["persons:" + variable]
        for filer in unit.filers:
            a, b = ours(unit, filer), by_person[filer.name]
            if abs(a - b) > tolerance:
                out[(unit.case_id, filer.name)] = (round(a, 2), round(b, 2))
    return out


def test_traditional_ira_contributions_per_filer_on_all_100(pairs):
    ours = lambda u, f: MT.ira_contributions(u)[f.name][0]  # noqa: E731
    assert _per_filer(pairs, ours, "traditional_ira_contributions") == {}


def test_traditional_401k_contributions_per_filer(pairs):
    found = _per_filer(pairs, lambda u, f: f.deferral, "traditional_401k_contributions")
    _same_keys_close(found, KNOWN["traditional_401k"])


@pytest.mark.skipif(not TAXCALC.exists(), reason="needs the Tax-Calculator 2026 run")
def test_student_loan_deduction_on_all_100(pairs):
    # The map figures 26 U.S.C. 221 from Tax-Calculator's pass-2 AGI; PolicyEngine from its own.
    with open(TAXCALC, newline="") as handle:
        sent = {row["case_id"]: float(row["in_e03210"] or 0) for row in csv.DictReader(handle)}
    differ = {
        unit.case_id: (sent[unit.case_id], pe["student_loan_interest_ald"])
        for unit, pe in pairs
        if abs(sent[unit.case_id] - pe["student_loan_interest_ald"]) > 0.5
    }
    assert differ == {}


def test_hsa_deduction(pairs):
    found = _differences(pairs, lambda u: u.amounts["hsa_deduction"], "health_savings_account_ald")
    _same_keys_close(found, KNOWN["hsa"])


def test_self_employed_health_insurance(pairs):
    found = _differences(pairs, lambda u: u.amounts["se_health_insurance"], "self_employed_health_insurance_ald")
    _same_keys_close(found, KNOWN["se_health_insurance"])


def test_retirement_penalty(pairs):
    agi = {unit.case_id: pe["adjusted_gross_income"] for unit, pe in pairs}

    def ours(unit):
        return S.early_distribution_tax(unit.amounts["early_distributions"], unit.amounts["medical"], agi[unit.case_id])
    found = _differences(pairs, ours, "qualified_retirement_penalty")
    _same_keys_close(found, KNOWN["retirement_penalty"])
