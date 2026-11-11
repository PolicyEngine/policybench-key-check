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


# Facts only the larger draw states (run causes-and-draw, unit draw-maps) -------------

import json  # noqa: E402

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOSSIERS = sorted((ROOT / "results" / "dossiers").glob("scenario_*.json"))
DRAW = ROOT / "data" / "draw" / "draw1000_seed20261110.csv"   # local only (git-ignored)


def with_inputs(person, **inputs):
    """make_person drops falsy inputs; a stated False goes in here."""
    person["inputs"].update(inputs)
    return person


def test_partnership_facts_under_either_release_name():
    old = make_person("head", 45, 0.0, partnership_s_corp_income=50_000, partnership_se_income=50_000)
    new = make_person("head", 45, 0.0, partnership_income=50_000, partnership_self_employment_net_earnings=50_000)
    a, b = U.build(make_household(old), 2026), U.build(make_household(new), 2026)
    assert a.amounts["partnership_s_corp"] == b.amounts["partnership_s_corp"] == 50_000
    assert a.head.partnership_se == b.head.partnership_se == 50_000
    assert a.notes == b.notes
    # A member's partnership income counts in the gross-income test and is named as their own.
    member = make_person("dependent1", 30, 0.0, partnership_income=6_000)
    unit = U.build(make_household(make_person("head", 50, 40_000), None, [member]), 2026)
    assert [d["name"] for d in unit.left_out] == ["dependent1"]
    assert any("dependent1 has income of their own (partnership_income)" in t for _, t in unit.notes)
    with pytest.raises(ValueError):
        U.build(make_household(make_person("head", 45, 0.0, partnership_s_corp_income=1, partnership_income=1)), 2026)
    with pytest.raises(ValueError):
        U.build(make_household(make_person("head", 45, 0.0, partnership_se_income=1, partnership_self_employment_net_earnings=1)), 2026)


def test_taxable_sep_distributions_are_ira_distributions():
    head = make_person("head", 50, 40_000, taxable_sep_distributions=3_000, taxable_ira_distributions=1_000)
    unit = U.build(make_household(head), 2026)
    assert unit.amounts["taxable_ira_distributions"] == 4_000
    assert unit.head.retirement_distributions == 4_000
    assert any("59 1/2" in t for _, t in unit.notes)
    member = make_person("dependent1", 30, 0.0, taxable_sep_distributions=6_000)
    unit = U.build(make_household(make_person("head", 60, 40_000), None, [member]), 2026)
    assert unit.left_out and unit.left_out[0]["gross_income"] == 6_000


def test_vehicle_loan_interest_is_the_households_amount():
    h = make_household(make_person("head", 50, 150_000, is_surviving_spouse=True), None, [make_person("child1", 10)])
    h["household_inputs"]["qualified_passenger_vehicle_loan_interest"] = 5_000
    unit = U.build(h, 2026)
    assert unit.amounts["qualified_vehicle_loan_interest"] == 5_000
    assert unit.amounts["auto_loan_interest"] == 0     # the board's own, unqualified input
    assert unit.status == S.SURVIVING_SPOUSE
    assert any("starts its phase-out at $200,000" in t for _, t in unit.notes)   # experiment E4


def test_investment_interest_limited_and_noted():
    # Experiment E1: 20,000 of investment interest against 1,000 of taxable interest.
    head = make_person("head", 45, 120_000, taxable_interest_income=1_000, investment_interest_expense=20_000)
    unit = U.build(make_household(head), 2026)
    assert unit.amounts["investment_interest"] == 20_000
    assert unit.amounts["investment_interest_allowed"] == 1_000
    assert any(U.READINGS["investment_interest"] in t for _, t in unit.notes)
    assert any("163(d)(1) allows 1,000" in t and "policyengine-us deducts all of it" in t for _, t in unit.notes)
    # E1 variant B: 10,000 of qualified dividends, 6,000 elected on Form 4952: 7,000.
    head = with_inputs(head, qualified_dividend_income=10_000, investment_income_elected_form_4952=6_000)
    unit = U.build(make_household(head), 2026)
    assert unit.amounts["form_4952_elected"] == 6_000 and unit.amounts["investment_interest_allowed"] == 7_000
    # An election above the qualified dividends and net capital gain is cut to them.
    head = make_person("head", 45, 50_000, qualified_dividend_income=1_867, investment_income_elected_form_4952=1_892)
    unit = U.build(make_household(head), 2026)
    assert unit.amounts["form_4952_elected"] == 1_867
    assert any("Form 4952 election of 1,892" in t for _, t in unit.notes)
    # A member's own investment interest is not the head's deduction.
    member = make_person("dependent1", 30, 9_000, investment_interest_expense=500)
    unit = U.build(make_household(make_person("head", 50, 40_000), None, [member]), 2026)
    assert unit.amounts["investment_interest"] == 0
    assert any(U.READINGS["member_deductions"] in t for _, t in unit.notes)


def test_rate_gains_are_memo_amounts():
    head = make_person("head", 60, 50_000, long_term_capital_gains=20_000, long_term_capital_gains_on_collectibles=3_000)
    h = make_household(head, unrecaptured_section_1250_gain=5_000)
    unit = U.build(h, 2026)
    assert unit.amounts["long_term_gains"] == 20_000           # never added to the gains
    assert unit.amounts["unrecaptured_1250"] == 5_000 and unit.amounts["collectibles_28"] == 3_000


def test_qbi_w2_wages_are_read():
    head = make_person("head", 50, 0.0, partnership_income=76_600, w2_wages_from_qualified_business=64_000,
                       sstb_w2_wages_from_qualified_business=64_000)
    unit = U.build(make_household(head), 2026)
    assert unit.amounts["qbi_w2_wages"] == 64_000 and unit.amounts["sstb_qbi_w2_wages"] == 64_000


def test_self_employed_health_insurance_under_162l():
    # Experiment E3: Schedule C 30,000, premiums 40,000 (stated both ways).
    head = make_person("head", 45, 0.0, is_self_employed=True, self_employment_income=30_000,
                       health_insurance_premiums=40_000, health_insurance_premiums_without_medicare_part_b=40_000)
    unit = U.build(make_household(head), 2026)
    half = S.self_employment_tax(2026, 30_000, 0) / 2
    assert abs(unit.head.se_earned_income - (30_000 - half)) < 1e-6
    assert abs(unit.head.se_health - (30_000 - half)) < 1e-6            # 401(c)(2) limit
    assert unit.head.se_health_key == 30_000                             # policyengine-us: 30,000
    assert abs(unit.amounts["se_health_insurance"] - unit.head.se_health) < 1e-9
    # 162(l)(3): the deducted premiums leave medical expenses; the two statements are one amount.
    assert abs(unit.amounts["medical"] - (40_000 - unit.head.se_health)) < 1e-6
    assert any(U.READINGS["se_health_insurance"] in t for _, t in unit.notes)
    assert any("policyengine-us allows 30,000" in t for _, t in unit.notes)
    assert not any(U.READINGS["self_employed_health_insurance"] in t for _, t in unit.notes)
    # is_self_employed alone moves nothing.
    plain = make_person("head", 45, 0.0, self_employment_income=30_000)
    flagged = make_person("head", 45, 0.0, self_employment_income=30_000, is_self_employed=True)
    assert U.build(make_household(plain), 2026).amounts == U.build(make_household(flagged), 2026).amounts
    # Premiums of a filer not stated self-employed: medical expenses only.
    head = make_person("head", 45, 50_000, health_insurance_premiums=4_000, health_insurance_premiums_without_medicare_part_b=3_000)
    unit = U.build(make_household(head), 2026)
    assert unit.amounts["se_health_insurance"] == 0 and unit.amounts["medical"] == 4_000


def test_self_employed_pension_contributions():
    head = make_person("head", 45, 50_000, self_employment_income=40_000, self_employed_pension_contributions_desired=15_000)
    unit = U.build(make_household(head), 2026)
    assert unit.head.se_pension == 15_000 and unit.amounts["se_pension"] == 15_000
    assert unit.head.active_participant
    assert any(U.READINGS["se_pension"] in t for _, t in unit.notes)
    assert any("exceeds what a SEP could deduct" in t for _, t in unit.notes)   # 20% of ~37,174
    head = make_person("head", 45, 0.0, self_employment_income=3_000, self_employed_pension_contributions_desired=5_000)
    assert U.build(make_household(head), 2026).head.se_pension == 3_000


def test_separated_head():
    # Experiment E2: a separated head with an older member without income: separately.
    h = make_household(make_person("head", 40, 50_000, is_separated=True), None, [make_person("dependent1", 70)])
    unit = U.build(h, 2026)
    assert unit.status == S.SEPARATE
    assert any(U.READINGS["separated"] in t for _, t in unit.notes)
    assert any("32(d)(1)" in t for _, t in unit.notes)
    # E2 variant B: the member is 10: head of household.
    h = make_household(make_person("head", 40, 50_000, is_separated=True), None, [make_person("child1", 10)])
    assert U.build(h, 2026).status == S.HEAD_OF_HOUSEHOLD
    # E2 variant C: a separated third adult does not bear on the couple's return.
    h = make_household(make_person("head", 40, 50_000), make_person("spouse", 40), [make_person("dependent1", 30, is_separated=True)])
    assert U.build(h, 2026).status == S.JOINT


def test_incapable_spouse_and_member_are_care_individuals():
    # Experiment E5: the spouse is incapable of self-care with 4,000 of care expenses.
    spouse = make_person("spouse", 45, 0.0, is_incapable_of_self_care=True, pre_subsidy_care_expenses=4_000)
    unit = U.build(make_household(make_person("head", 45, 50_000), spouse), 2026)
    assert [c["name"] for c in unit.care_individuals] == ["spouse"]
    assert unit.amounts["child_care"] == 4_000
    assert U.deemed_earnings_short(unit) == [("spouse", 0.0, 3_000.0)]
    assert any(U.READINGS["incapable"] in t for _, t in unit.notes)
    # E5 variant B: a member aged 30 with 10,000 of wages, left out on the gross-income test.
    member = make_person("dependent1", 30, 10_000, is_incapable_of_self_care=True, pre_subsidy_care_expenses=4_000)
    unit = U.build(make_household(make_person("head", 45, 50_000), make_person("spouse", 45), [member]), 2026)
    assert [d["name"] for d in unit.left_out] == ["dependent1"]
    assert [c["name"] for c in unit.care_individuals] == ["dependent1"]
    assert unit.amounts["child_care"] == 4_000
    assert U.deemed_earnings_short(unit) == []
    # A head without a spouse is not a qualifying individual: the expense is left out, noted.
    head = make_person("head", 45, 20_000, is_incapable_of_self_care=True, pre_subsidy_care_expenses=1_000)
    unit = U.build(make_household(head), 2026)
    assert unit.care_individuals == [] and unit.amounts["child_care"] == 0
    assert any("is not a qualifying individual" in t for _, t in unit.notes)
    # Both spouses incapable: one counts, as policyengine-us counts.
    both = make_household(make_person("head", 80, 0.0, is_incapable_of_self_care=True),
                          make_person("spouse", 75, 0.0, is_incapable_of_self_care=True))
    assert [c["name"] for c in U.build(both, 2026).care_individuals] == ["spouse"]


def test_unrelated_members():
    child = with_inputs(make_person("child1", 10), is_related_to_head_or_spouse=False)
    unit = U.build(make_household(make_person("head", 40, 30_000), None, [child]), 2026)
    assert unit.dependents[0]["kind"] == "qualifying_child" and not unit.dependents[0]["related"]
    assert unit.status == S.HEAD_OF_HOUSEHOLD
    assert any(U.READINGS["unrelated_member"] in t for _, t in unit.notes)
    adult = with_inputs(make_person("dependent1", 70), is_related_to_head_or_spouse=False)
    unit = U.build(make_household(make_person("head", 40, 30_000), None, [adult]), 2026)
    assert unit.dependents[0]["kind"] == "qualifying_relative"
    assert unit.status == S.SINGLE                 # 2(b)(3)(B)(i): no head of household


@settings(max_examples=300)
@given(households(), YEARS, small, small, small, st.booleans())
def test_care_individuals_property(household, year, care, premiums, pension, self_employed):
    head = household["adults"][0]
    head["inputs"].update({"is_incapable_of_self_care": True, "pre_subsidy_care_expenses": care,
                           "health_insurance_premiums": premiums, "is_self_employed": self_employed,
                           "self_employed_pension_contributions_desired": pension})
    unit = U.build(household, year)
    names = [c["name"] for c in unit.care_individuals]
    assert len(names) == len(set(names))
    assert {d["name"] for d in unit.dependents if d["age"] < 13} <= set(names)
    filers_in = [n for n in names if n in ("head", "spouse")]
    assert len(filers_in) <= (1 if unit.status == S.JOINT else 0)
    assert unit.amounts["care_expenses_of_incapable"] == (care if "head" in names else 0.0)
    for filer in unit.filers:
        assert 0 <= filer.se_pension <= max(0.0, filer.schedule_c) + 1e-9
        assert 0 <= filer.se_health <= filer.se_health_key + 1e-6 <= filer.se_health_premiums + 1e-6
    assert unit.amounts["medical"] >= -1e-6


# The coverage rule (the draw-inputs reader's item 12) ---------------------------------


def test_every_stated_input_is_read_or_named_as_having_no_effect():
    board = [json.loads(path.read_text())["stated_facts"] for path in DOSSIERS]
    assert len(board) == 100
    for h in board:
        assert U.unread_inputs(h) == [], h["id"]
    if DRAW.exists():
        from keycheck import households as H
        draw = H.load(DRAW)
        assert len(draw) == 1_000
        for h in draw:
            assert U.unread_inputs(h) == [], h["id"]
    # A new or renamed input fails the rule.
    h = make_household(make_person("head", 40, 50_000, brand_new_input=1))
    h["tax_unit_inputs"]["another_new_input"] = 2
    assert U.unread_inputs(h) == [("person", "brand_new_input"), ("tax_unit", "another_new_input")]
    assert not (U.READ_INPUTS & U.NON_TAX_INPUTS) and not (U.READ_INPUTS & U.MEMO_INPUTS)


# The board's return does not move ------------------------------------------------------

NEW_FILER = {"se_pension": 0.0, "se_health_premiums": 0.0, "se_health": 0.0, "se_health_key": 0.0,
             "se_earned_income": 0.0, "incapable": False}
NEW_MEMBER = {"related": True, "incapable": False}


def _same_or_neutral(stored, now, neutral, where):
    for key, value in now.items():
        if key in stored:
            assert stored[key] == value, (where, key)
        else:
            assert key in neutral and value == neutral[key], (where, key, value)


@pytest.mark.parametrize("path", DOSSIERS, ids=[p.stem for p in DOSSIERS])
def test_board_return_unchanged(path):
    """The return derived from each board household equals the committed dossier's, field by
    field; a field the dossier predates must be neutral (no board household states a draw fact)."""
    import dataclasses
    dossier = json.loads(path.read_text())
    for year in ("2026", "2025"):
        stored = dossier["return_from_stated_facts"][year]
        now = json.loads(json.dumps(dataclasses.asdict(U.build(dossier["stated_facts"], int(year)))))
        expected_care = [{"name": d["name"], "age": d["age"], "why": "under 13"} for d in now["dependents"] if d["age"] < 13]
        _same_or_neutral(stored, {k: v for k, v in now.items() if k not in ("head", "spouse", "dependents", "left_out", "amounts")},
                         {"care_individuals": expected_care}, (path.stem, year))
        for role in ("head", "spouse"):
            if stored[role] is None:
                assert now[role] is None
            else:
                _same_or_neutral(stored[role], now[role], NEW_FILER, (path.stem, year, role))
        for group in ("dependents", "left_out"):
            assert len(stored[group]) == len(now[group])
            for a, b in zip(stored[group], now[group]):
                _same_or_neutral(a, b, NEW_MEMBER, (path.stem, year, group))
        _same_or_neutral(stored["amounts"], now["amounts"], {k: 0.0 for k in now["amounts"]}, (path.stem, year, "amounts"))
