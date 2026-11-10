"""Properties and examples of keycheck/unit.py: the one federal return both maps start from."""

import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keycheck import statute as S  # noqa: E402
from keycheck import unit as U  # noqa: E402

YEARS = st.sampled_from([2025, 2026])
money = st.one_of(st.just(0.0), st.floats(min_value=1, max_value=300_000, allow_nan=False).map(lambda x: round(x, 2)))
small = st.one_of(st.just(0.0), st.floats(min_value=1, max_value=20_000, allow_nan=False).map(lambda x: round(x, 2)))


def make_person(name, age, wages=0.0, **inputs):
    return {"name": name, "age": age, "employment_income": wages, "inputs": {k: v for k, v in inputs.items() if v}}


def make_household(head, spouse=None, others=(), **tax_unit):
    adults = [head] + ([spouse] if spouse else []) + [p for p in others if p["age"] >= 18]
    children = [p for p in others if p["age"] < 18]
    return {
        "id": "case", "state": "TX", "year": 2026, "adults": adults, "children": children,
        "tax_unit_inputs": dict(tax_unit), "spm_unit_inputs": {}, "household_inputs": {},
    }


@st.composite
def filers(draw, name):
    return make_person(
        name, draw(st.integers(18, 90)), draw(money),
        traditional_401k_contributions_desired=draw(small) * 2,
        roth_401k_contributions_desired=draw(small),
        self_employment_income=draw(st.one_of(st.just(0.0), small)),
        taxable_ira_distributions=draw(st.one_of(st.just(0.0), small)),
        other_medical_expenses=draw(st.one_of(st.just(0.0), small)),
        is_surviving_spouse=draw(st.booleans()) if name == "head" else False,
    )


@st.composite
def members(draw, index):
    return make_person(
        f"dependent{index}", draw(st.integers(0, 90)),
        draw(st.one_of(st.just(0.0), small)),
        self_employment_income=draw(st.one_of(st.just(0.0), small)),
        disability_benefits=draw(st.one_of(st.just(0.0), small)),
        long_term_capital_gains=draw(st.one_of(st.just(0.0), st.floats(-20_000, 20_000).map(lambda x: round(x, 2)))),
        is_disabled=draw(st.booleans()),
        is_unmarried_partner_of_household_head=draw(st.booleans()),
        other_medical_expenses=draw(st.one_of(st.just(0.0), small)),
    )


@st.composite
def households(draw):
    head = draw(filers("head"))
    spouse = draw(st.one_of(st.none(), filers("spouse")))
    n = draw(st.integers(0, 4))
    others = [draw(members(i)) for i in range(1, n + 1)]
    return make_household(head, spouse, others)


@settings(max_examples=400)
@given(households(), YEARS)
def test_dependents_and_left_out_partition_the_other_members(household, year):
    unit = U.build(household, year)
    others = [p["name"] for p in household["adults"] + household["children"] if p["name"] not in ("head", "spouse")]
    claimed = [d["name"] for d in unit.dependents]
    left = [d["name"] for d in unit.left_out]
    assert sorted(claimed + left) == sorted(others)
    assert not set(claimed) & set(left)
    assert [f.name for f in unit.filers] == ["head"] + (["spouse"] if household_has_spouse(household) else [])


def household_has_spouse(household):
    return any(p["name"] == "spouse" for p in household["adults"])


@settings(max_examples=400)
@given(households(), YEARS)
def test_deferrals_never_exceed_wages_or_the_402g_limit(household, year):
    unit = U.build(household, year)
    for filer in unit.filers:
        total = filer.deferral + filer.roth_deferral
        assert filer.deferral >= 0 and filer.roth_deferral >= 0
        assert total <= max(0.0, filer.wages) + 1e-6
        assert total <= S.elective_deferral_limit(year, filer.age) + 1e-6
        if filer.wages <= 0:
            assert total == 0 and not filer.active_participant


@settings(max_examples=400)
@given(households(), YEARS)
def test_filing_status_rules(household, year):
    unit = U.build(household, year)
    head = household["adults"][0]
    claimants = [d for d in unit.dependents if not d["unmarried_partner"]]
    if household_has_spouse(household):
        assert unit.status == S.JOINT
    elif claimants and head["inputs"].get("is_surviving_spouse"):
        assert unit.status == S.SURVIVING_SPOUSE
    elif claimants:
        assert unit.status == S.HEAD_OF_HOUSEHOLD
    else:
        # A dependent only as the head's unmarried partner does not make a head of household.
        assert unit.status == S.SINGLE


@settings(max_examples=400)
@given(households(), YEARS)
def test_dependency_classes(household, year):
    unit = U.build(household, year)
    limit = U.QUALIFYING_RELATIVE_INCOME_LIMIT[year]
    people = {p["name"]: p for p in household["adults"] + household["children"]}
    reading = {d["name"] for d in unit.disabled_reading}
    for d in unit.dependents + unit.left_out:
        p = people[d["name"]]
        wages, se = U.own_earnings(p)
        disabled_reading = p["inputs"].get("is_disabled", False) and wages == 0 and se == 0 and d["age"] >= 19
        assert (d["name"] in reading) == bool(disabled_reading)
        if d["age"] < 19 or disabled_reading:
            assert d.get("kind") == "qualifying_child"
        elif d["gross_income"] < limit:
            assert d.get("kind") == "qualifying_relative"
        else:
            assert "kind" not in d and d in unit.left_out
    for record in unit.disabled_reading:
        assert record["with_reading"] == "qualifying_child"
        assert record["without_reading"] in ("qualifying_relative", "left_out")


@settings(max_examples=300)
@given(households(), YEARS)
def test_medical_counts_every_listed_member(household, year):
    unit = U.build(household, year)
    people = household["adults"] + household["children"]
    expected = sum(p["inputs"].get("other_medical_expenses", 0.0) for p in people)
    assert abs(unit.amounts["medical"] - expected) < 1e-6


@settings(max_examples=300)
@given(households(), YEARS)
def test_member_self_employment_gets_both_notes(household, year):
    unit = U.build(household, year)
    for member in unit.members_with_own_payroll:
        payroll = [t for g, t in unit.notes if g == "payroll" and t.startswith(member["name"] + " ")]
        assert payroll
        se = [t for g, t in unit.notes if g == "self_employment" and t.startswith(member["name"] + " ")]
        assert bool(se) == (member["self_employment"] > 0)


@given(st.floats(0, 100_000), st.floats(0, 200_000), st.floats(0, 200_000), st.floats(0, 20_000))
def test_taxable_social_security_bounds(benefits, other, more, exempt):
    a = U.taxable_social_security_unmarried(benefits, other, exempt)
    b = U.taxable_social_security_unmarried(benefits, other + more, exempt)
    assert 0 <= a <= 0.85 * benefits + 1e-6
    assert b >= a - 1e-6


def test_taxable_social_security_examples():
    # 26 U.S.C. 86(a)(1): provisional 30,000 is 5,000 over the $25,000 base: half of it.
    assert U.taxable_social_security_unmarried(20_000, 20_000, 0) == 2_500
    # 86(a)(2): 85% of the excess over $34,000 plus the lesser of the (a)(1) amount or 4,500.
    assert abs(U.taxable_social_security_unmarried(30_000, 40_000, 0) - (0.85 * 21_000 + 4_500)) < 1e-9
    assert U.taxable_social_security_unmarried(10_000, 0, 0) == 0
    # Tax-exempt interest counts in the test (86(b)(2)(B)).
    assert U.taxable_social_security_unmarried(20_000, 10_000, 10_000) == 2_500


def test_own_gross_income_counts_gains_without_losses():
    p = make_person("dependent1", 25, 0.0, long_term_capital_gains=3_000, short_term_capital_gains=-5_000)
    assert U.own_gross_income(p, 2026) == 3_000
    # Wages count net of the member's own traditional deferral.
    p = make_person("dependent1", 25, 6_000, traditional_401k_contributions_desired=1_000)
    assert U.own_gross_income(p, 2026) == 5_000


def test_disabled_member_without_earnings_is_a_qualifying_child():
    # scenario_067's shape: a 23-year-old stated disabled, own disability benefits 10,800.
    head = make_person("head", 60, 82_360)
    spouse = make_person("spouse", 58)
    member = make_person("dependent1", 23, disability_benefits=10_800, is_disabled=True)
    unit = U.build(make_household(head, spouse, [member]), 2026)
    assert [d["kind"] for d in unit.dependents] == ["qualifying_child"]
    assert unit.left_out == []
    assert unit.disabled_reading == [{
        "name": "dependent1", "age": 23, "gross_income": 10_800,
        "with_reading": "qualifying_child", "without_reading": "left_out",
        "income_readings_without": ["disability_benefits"],
    }]
    assert any("reading: dependent1 (age 23) is a qualifying child" in t for _, t in unit.notes)


def test_disabled_member_with_earnings_is_not():
    # scenario_093's shape: a 27-year-old stated disabled who earns 45,000.
    head = make_person("head", 55, 80_000)
    member = make_person("dependent1", 27, 45_000, is_disabled=True)
    unit = U.build(make_household(head, None, [member]), 2026)
    assert unit.dependents == [] and [d["name"] for d in unit.left_out] == ["dependent1"]
    assert unit.disabled_reading == []
    assert unit.status == S.SINGLE
    assert any("stated disabled but has earnings" in t for _, t in unit.notes)


def test_gross_income_reading_attached_when_it_decides_the_test():
    # The verify-unit-statute counterexample: 2025, a 19-year-old member with disability
    # benefits at the limit is left out, and the reading that decided it is named.
    head = make_person("head", 18)
    member = make_person("dependent1", 19, disability_benefits=5_200)
    unit = U.build(make_household(head, None, [member]), 2025)
    assert [d["name"] for d in unit.left_out] == ["dependent1"]
    assert any(t.startswith("reading: dependent1's gross-income test") and "Employment disability benefits" in t for _, t in unit.notes)


def test_roth_deferral_without_wages_is_zero():
    # The verify-unit-statute counterexample: head 18, wages 0, Roth 401(k) desired 1.00.
    head = make_person("head", 18, 0.0, roth_401k_contributions_desired=1.0)
    unit = U.build(make_household(head), 2025)
    assert unit.head.roth_deferral == 0 and unit.head.deferral == 0
    assert not unit.head.active_participant


def test_surviving_spouse_with_a_qualifying_relative():
    head = make_person("head", 50, 60_000, is_surviving_spouse=True)
    member = make_person("dependent1", 25, 3_000)
    unit = U.build(make_household(head, None, [member]), 2026)
    assert unit.status == S.SURVIVING_SPOUSE
    assert any(U.READINGS["surviving_spouse"] in t for _, t in unit.notes)


def test_retirement_penalty_note_at_59():
    head = make_person("head", 59, 30_000, taxable_ira_distributions=5_000)
    unit = U.build(make_household(head), 2026)
    assert any("may be under 59 1/2" in t for _, t in unit.notes)
    head = make_person("head", 60, 30_000, taxable_ira_distributions=5_000)
    assert not any("59 1/2" in t for _, t in U.build(make_household(head), 2026).notes)


def test_unclaimed_member_medical_counts_and_is_noted_for_itemizers():
    head = make_person("head", 50, 60_000)
    member = make_person("dependent1", 25, 9_000, other_medical_expenses=4_000)
    unit = U.build(make_household(head, None, [member]), 2026)
    assert [d["name"] for d in unit.left_out] == ["dependent1"]
    assert unit.amounts["medical"] == 4_000
    assert any("dependent1 is not claimed" in t for _, t in unit.itemized_notes)


def test_readings_named_for_stated_facts():
    head = make_person(
        "head", 40, 50_000, tip_income=1_000, rental_income=-2_000,
        educational_assistance=5_000, qualified_bdc_income=10, farm_income=-100,
    )
    unit = U.build(make_household(head), 2026)
    text = " ".join(t for _, t in unit.notes)
    for key in ("tips", "rental_qbi", "educational_assistance", "qualified_bdc_income", "farm_income"):
        assert U.READINGS[key] in text, key
    head = make_person("head", 40, 50_000, over_the_counter_health_expenses=100, other_health_insurance_premiums=200)
    itemized = " ".join(t for _, t in U.build(make_household(head), 2026).itemized_notes)
    assert U.READINGS["over_the_counter"] in itemized and U.READINGS["other_health_insurance_premiums"] in itemized


def test_every_reading_is_a_sentence():
    for key, text in U.READINGS.items():
        assert text.strip() and text.rstrip().endswith((".", ")")), key
