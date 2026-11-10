"""Properties and examples of the two input maps (keycheck/map_taxcalc.py, keycheck/map_taxsim.py)
and of the note format the runners and scripts/build_answers.py share."""

import importlib.util
import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from keycheck import map_taxcalc as MT  # noqa: E402
from keycheck import map_taxsim as MS  # noqa: E402
from keycheck import statute as S  # noqa: E402
from keycheck import unit as U  # noqa: E402

spec = importlib.util.spec_from_file_location("build_answers", ROOT / "scripts" / "build_answers.py")
build_answers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_answers)

SALT = {"salt_income_or_sales_tax": 2_000.0}


def person(name, age, wages=0.0, **inputs):
    return {"name": name, "age": age, "employment_income": wages, "inputs": {k: v for k, v in inputs.items() if v}}


def household(head, spouse=None, others=(), **tax_unit):
    adults = [head] + ([spouse] if spouse else []) + [p for p in others if p["age"] >= 18]
    return {
        "id": "case", "state": "TX", "year": 2026, "adults": adults,
        "children": [p for p in others if p["age"] < 18],
        "tax_unit_inputs": dict(tax_unit), "spm_unit_inputs": {}, "household_inputs": {},
    }


small = st.one_of(st.just(0.0), st.floats(min_value=1, max_value=30_000, allow_nan=False).map(lambda x: round(x, 2)))


@st.composite
def households(draw):
    head = person("head", draw(st.integers(18, 80)), draw(small) * 5,
                  traditional_401k_contributions_desired=draw(small),
                  roth_401k_contributions_desired=draw(small),
                  non_sch_d_capital_gains=draw(small),
                  long_term_capital_gains=draw(st.one_of(st.just(0.0), small)),
                  educator_expense=draw(st.one_of(st.just(0.0), st.floats(1, 600).map(lambda x: round(x, 2)))),
                  rental_income=draw(st.one_of(st.just(0.0), st.floats(-20_000, 20_000).map(lambda x: round(x, 2)))))
    spouse = draw(st.one_of(st.none(), st.builds(lambda w, t: person("spouse", 45, w, traditional_401k_contributions_desired=t), small, small)))
    others = [
        person(f"dependent{i}", draw(st.integers(0, 40)), draw(st.one_of(st.just(0.0), small)),
               is_disabled=draw(st.booleans()))
        for i in range(1, draw(st.integers(0, 6)) + 1)
    ]
    return household(head, spouse, others, health_savings_account_ald=draw(st.one_of(st.just(0.0), small)))


# Tax-Calculator ----------------------------------------------------------------------


def test_capital_gain_distributions_without_schedule_d_go_to_e01100():
    row, *_ = MT.row(household(person("head", 40, 50_000, non_sch_d_capital_gains=1_000)), 2026)
    assert row["e01100"] == 1_000 and row["p23250"] == 0


def test_capital_gain_distributions_with_schedule_d_join_p23250():
    h = household(person("head", 40, 50_000, non_sch_d_capital_gains=1_000, long_term_capital_gains=500))
    row, _, _, computed = MT.row(h, 2026)
    assert row["e01100"] == 0 and row["p23250"] == 1_500
    assert any("Schedule D (p23250)" in c for c in computed)
    # A short-term loss alone is a Schedule D item too.
    h = household(person("head", 40, 50_000, non_sch_d_capital_gains=1_000, short_term_capital_gains=-200))
    row, *_ = MT.row(h, 2026)
    assert row["e01100"] == 0 and row["p23250"] == 1_000 and row["p22250"] == -200


def test_tips_are_not_qualified_tips():
    row, _, unexpressed, _ = MT.row(household(person("head", 40, 50_000, tip_income=5_000)), 2026)
    assert row["tip_income"] == 0
    assert row["e00200"] == 50_000   # the tips stay inside the stated wages
    assert any(U.READINGS["tips"] in n for n in unexpressed)


def test_zeroed_employee_expenses_are_noted():
    h = household(person("head", 40, 50_000, unreimbursed_business_employee_expenses=900))
    row, _, unexpressed, _ = MT.row(h, 2026)
    assert row["e20400"] == 900
    assert any("e20400" in n for n in unexpressed)


def test_shared_salt_note_only_through_itemizer_notes():
    h = household(person("head", 40, 50_000, real_estate_taxes=3_000, other_health_insurance_premiums=100))
    _, unit, unexpressed, _ = MT.row(h, 2026, SALT)
    assert MT.SHARED_SALT_NOTE not in unexpressed
    notes = MT.itemizer_notes(unit, SALT)
    assert MT.SHARED_SALT_NOTE in notes
    assert any(U.READINGS["other_health_insurance_premiums"] in n for n in notes)
    assert MT.SHARED_SALT_NOTE not in MT.itemizer_notes(unit, {})
    # Without a shared file, the row itself says e18400 is 0.
    _, _, unexpressed, _ = MT.row(h, 2026)
    assert any("e18400 is 0" in n for n in unexpressed)


@settings(max_examples=300)
@given(households(), st.sampled_from([2025, 2026]))
def test_taxcalc_row_conserves_gains_and_wages(h, year):
    row, unit, _, _ = MT.row(h, year)
    a = unit.amounts
    assert abs(row["e01100"] + row["p23250"] - a["capital_gain_distributions"] - a["long_term_gains"]) < 1e-6
    assert row["e01100"] == 0 or not (a["short_term_gains"] or a["long_term_gains"])
    for filer, wages, pencon in ((unit.head, row["e00200p"], row["pencon_p"]),
                                 (unit.spouse, row["e00200s"], row["pencon_s"])):
        if filer is None:
            continue
        assert abs(wages + pencon - filer.wages) < 1e-6   # box 1 wages plus the deferral = gross
        assert 0 <= pencon <= filer.wages + 1e-6
    assert row["tip_income"] == 0


# TAXSIM ------------------------------------------------------------------------------


def test_record_a_sends_children_under_17_and_record_b_the_eitc_children():
    kids = [person("child1", 5), person("child2", 17), person("dependent1", 18)]
    record, unit, _, computed = MS.first_pass(household(person("head", 40, 30_000), None, kids), 2026)
    assert (record["depx"], record["dep13"], record["dep17"], record["dep18"]) == (3, 1, 1, 1)
    assert MS.needs_eitc_record(unit)
    assert any("second TAXSIM record" in c for c in computed)
    b = MS.eitc_record(record, unit)
    assert (b["depx"], b["dep13"], b["dep17"], b["dep18"]) == (3, 1, 1, 3)
    assert {k: v for k, v in b.items() if not k.startswith("dep")} == {k: v for k, v in record.items() if not k.startswith("dep")}


def test_no_record_b_when_three_or_more_count_either_way():
    kids = [person(f"child{i}", 3 + i) for i in range(1, 5)] + [person("child5", 17)]
    _, unit, _, _ = MS.first_pass(household(person("head", 40, 30_000), None, kids), 2026)
    assert not MS.needs_eitc_record(unit)   # min(3, 5) == min(3, 4)
    _, unit, _, _ = MS.first_pass(household(person("head", 40, 30_000), None, [person("dependent1", 30)]), 2026)
    assert not MS.needs_eitc_record(unit)   # a qualifying relative is no one's EITC child


def test_disabled_adult_without_earnings_is_an_eitc_child():
    member = person("dependent1", 23, disability_benefits=10_800, is_disabled=True)
    record, unit, _, _ = MS.first_pass(household(person("head", 60, 40_000), None, [member]), 2026)
    assert (record["depx"], record["dep17"], record["dep18"]) == (1, 0, 0)
    assert MS.needs_eitc_record(unit) and MS.eitc_record(record, unit)["dep18"] == 1


@settings(max_examples=400)
@given(households())
def test_2026_counts_respect_the_builds_order(h):
    record, unit, _, _ = MS.first_pass(h, 2026)
    ctc, eitc, care = MS.credit_counts(unit)
    assert 0 <= record["dep13"] <= record["dep17"] <= record["dep18"] <= record["depx"] == len(unit.dependents)
    assert record["dep18"] == ctc
    assert MS.needs_eitc_record(unit) == (min(3, eitc) != min(3, ctc))
    b = MS.eitc_record(record, unit)
    assert 0 <= b["dep13"] <= b["dep17"] <= b["dep18"] <= b["depx"]
    assert b["dep18"] == min(3, eitc)


def test_2025_ages_send_qualifying_children_17_and_over_as_18():
    others = [
        person("child1", 0), person("child2", 17),
        person("dependent1", 25),                                   # qualifying relative
        person("dependent2", 30, is_disabled=True),                 # the is_disabled reading
    ]
    record, unit, _, _ = MS.first_pass(household(person("head", 45, 40_000), None, others), 2025)
    assert [record[f"age{i}"] for i in range(1, 5)] == [1, 18, 18, 25]
    assert "age5" not in record


@settings(max_examples=300)
@given(households())
def test_2025_ages_property(h):
    record, unit, _, _ = MS.first_pass(h, 2025)
    ages = [record[k] for k in sorted((k for k in record if k.startswith("age")), key=lambda k: int(k[3:]))]
    assert len(ages) == min(10, len(unit.dependents))
    expected = sorted(18 if d["kind"] == "qualifying_child" and d["age"] >= 17 else max(1, d["age"]) for d in unit.dependents)[:10]
    assert ages == expected
    assert "dep18" not in record


def test_wages_gross_and_deferrals_in_nonprop():
    head = person("head", 40, 50_000, traditional_401k_contributions_desired=5_000, educator_expense=400)
    record, unit, _, computed = MS.first_pass(household(head), 2026)
    assert record["pwages"] == 50_000
    assert record["nonprop"] == -(5_000 + 350)   # the deferral and the educator cap (2026: $350)
    assert any("negative `nonprop`" in c for c in computed)
    assert MS.payroll_records(record, unit)["pwages"] == 50_000


@settings(max_examples=300)
@given(households(), st.sampled_from([2025, 2026]))
def test_taxsim_record_conserves_wages_and_adjustments(h, year):
    record, unit, _, _ = MS.first_pass(h, year)
    assert abs(record["pwages"] + record["swages"] - sum(f.wages for f in unit.filers)) < 1e-6
    a = unit.amounts
    educator = S.educator_expense_deduction(year, [f.educator_expense for f in unit.filers])
    expected = -(sum(f.deferral for f in unit.filers) + educator + a["hsa_deduction"])
    assert abs(record["nonprop"] - expected) < 1e-6
    assert abs(record["intrec"] - (a["taxable_interest"] + a["non_qualified_dividends"] + a["rental"] + a["estate"])) < 1e-6
    assert record["ltcg"] == a["long_term_gains"] + a["capital_gain_distributions"]


def test_rental_loss_goes_to_intrec_and_is_noted():
    head = person("head", 40, 50_000, rental_income=-3_000, taxable_interest_income=1_000)
    record, unit, unexpressed, _ = MS.first_pass(household(head), 2026)
    assert record["intrec"] == -2_000 and record["scorp"] == 0
    assert any("offsets interest" in n for n in unexpressed)
    assert any(U.READINGS["rental_qbi"] in n for n in unexpressed)


def test_final_notes_depend_on_taxsims_answer():
    head = person("head", 40, 50_000, self_employment_income=100_000, other_health_insurance_premiums=100)
    record, unit, _, _ = MS.first_pass(household(head), 2026, SALT)
    none = MS.final_notes(record, unit, {"v17": 0.0, "v18": 100_000, "qbid": 0.0}, SALT)
    assert none == []
    itemizes = MS.final_notes(record, unit, {"v17": 30_000.0, "v18": 100_000, "qbid": 0.0}, SALT)
    assert MS.SHARED_SALT_NOTE in itemizes
    assert any(U.READINGS["other_health_insurance_premiums"] in n for n in itemizes)
    over = MS.final_notes(record, unit, {"v17": 0.0, "v18": 190_000, "qbid": 20_000}, SALT)
    assert len(over) == 1 and "W-2 wage or property limit" in over[0]   # 210,000 > 201,750
    # A loss carries no deduction for the limit to cut.
    loss = person("head", 40, 400_000, self_employment_income=-5_000)
    record, unit, _, _ = MS.first_pass(household(loss), 2025)
    assert MS.final_notes(record, unit, {"v17": 0.0, "v18": 390_000, "qbid": 0.0}) == []


def test_payroll_record_zeroes_self_employment_only():
    head = person("head", 40, 50_000, self_employment_income=10_000, sstb_self_employment_income_before_lsr=2_000)
    record, unit, _, _ = MS.first_pass(household(head), 2026)
    without = MS.payroll_records(record, unit)
    assert without["psemp"] == 0 and without["pprofinc"] == 0
    assert {k: v for k, v in without.items() if k not in ("psemp", "ssemp", "pprofinc", "sprofinc")} == {
        k: v for k, v in record.items() if k not in ("psemp", "ssemp", "pprofinc", "sprofinc")
    }


# Notes -------------------------------------------------------------------------------


def test_notes_with_semicolons_survive_tagging():
    text = " || ".join([
        "income_tax: a reading; with a clause",
        "payroll: another",
        "all: shared; note",
    ])
    assert build_answers.tagged(text, "income_tax") == "a reading; with a clause || shared; note"
    assert build_answers.tagged(text, "payroll") == "another || shared; note"
    assert build_answers.tagged("", "payroll") == ""
