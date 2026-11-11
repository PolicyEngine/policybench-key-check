"""keycheck/households.py: the board's rule that an unlisted amount is 0 and an unlisted
status is false, and who counts as a member other than the head and spouse."""

import csv
import json
import sys
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keycheck import households as H  # noqa: E402

KEYS = st.sampled_from(["taxable_interest_income", "is_disabled", "rental_income", "tip_income"])


def person(name, age=40, wages=None, **inputs):
    p = {"name": name, "age": age, "inputs": dict(inputs)}
    if wages is not None:
        p["employment_income"] = wages
    return p


def household(*people, children=()):
    return {
        "id": "case", "state": "TX", "year": 2026,
        "adults": list(people), "children": list(children),
        "tax_unit_inputs": {}, "spm_unit_inputs": {}, "household_inputs": {},
    }


@given(KEYS)
def test_unlisted_amount_is_zero_and_unlisted_status_false(key):
    p = person("head")
    assert H.amount(p, key) == 0.0
    assert H.flag(p, key) is False
    assert H.amount(None, key) == 0.0
    assert H.flag(None, key) is False


def test_stated_values_and_none():
    p = person("head", wages=50_000, taxable_interest_income=12.5, is_disabled=True, rental_income=None)
    assert H.amount(p, "employment_income") == 50_000
    assert H.amount(p, "taxable_interest_income") == 12.5
    assert H.amount(p, "rental_income") == 0.0  # a stated null is 0
    assert H.flag(p, "is_disabled") is True
    assert H.amount(person("head"), "employment_income") == 0.0


@given(st.integers(min_value=0, max_value=4), st.integers(min_value=0, max_value=4), st.booleans())
def test_head_spouse_and_others(n_dependents, n_children, with_spouse):
    adults = [person("head")] + ([person("spouse")] if with_spouse else [])
    adults += [person(f"dependent{i}", 20) for i in range(1, n_dependents + 1)]
    children = [person(f"child{i}", 5) for i in range(1, n_children + 1)]
    h = household(*adults, children=children)
    assert H.head(h)["name"] == "head"
    assert (H.spouse(h) is not None) == with_spouse
    others = H.others(h)
    assert len(others) == n_dependents + n_children
    assert all(p["name"] not in ("head", "spouse") for p in others)
    assert len(H.people(h)) == len(others) + 1 + int(with_spouse)


def test_load_reads_scenario_json(tmp_path):
    h = household(person("head", 30, wages=1_000))
    path = tmp_path / "scenarios.csv"
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scenario_id", "scenario_json"])
        writer.writeheader()
        writer.writerow({"scenario_id": "case", "scenario_json": json.dumps(h)})
    assert H.load(path) == [h]
