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
                  rental_income=draw(st.one_of(st.just(0.0), st.floats(-20_000, 20_000).map(lambda x: round(x, 2)))),
                  # Facts only the larger draw states.
                  self_employment_income=draw(st.one_of(st.just(0.0), small)),
                  is_self_employed=draw(st.booleans()),
                  health_insurance_premiums=draw(st.one_of(st.just(0.0), small)),
                  self_employed_pension_contributions_desired=draw(st.one_of(st.just(0.0), small)),
                  qualified_dividend_income=draw(st.one_of(st.just(0.0), small)),
                  short_term_capital_gains=draw(st.one_of(st.just(0.0), st.floats(-20_000, 20_000).map(lambda x: round(x, 2)))),
                  investment_income_elected_form_4952=draw(st.one_of(st.just(0.0), small)),
                  investment_interest_expense=draw(st.one_of(st.just(0.0), small)))
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


@settings(max_examples=400, deadline=None)  # a loaded host overruns the 200 ms default
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
    expected = -(sum(f.deferral for f in unit.filers) + educator + a["hsa_deduction"]
                 + a["se_health_insurance"] + a["se_pension"])
    assert abs(record["nonprop"] - expected) < 1e-6
    # The Form 4952 election moves the elected amounts into `intrec` and nothing else.
    elected = a["form_4952_elected"]
    assert abs(record["intrec"] - (a["taxable_interest"] + a["non_qualified_dividends"] + a["rental"] + a["estate"] + elected)) < 1e-6
    moved_gain = a["long_term_gains"] + a["capital_gain_distributions"] - record["ltcg"]
    moved_dividends = a["qualified_dividends"] - record["dividends"]
    assert moved_gain >= -1e-6 and moved_dividends >= -1e-6
    assert abs(moved_gain + moved_dividends - elected) < 1e-6
    assert moved_gain <= S.net_capital_gain(a["short_term_gains"], a["long_term_gains"] + a["capital_gain_distributions"]) + 1e-6
    if not elected:
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


# Facts only the larger draw states (run causes-and-draw, unit draw-maps) -------------

DRAW_INPUTS = ("e03270", "e03300", "e58990", "e24515", "e24518", "PT_binc_w2_wages")


@settings(max_examples=200)
@given(households(), st.sampled_from([2025, 2026]))
def test_taxcalc_draw_inputs_sent_only_when_non_zero(h, year):
    row, unit, _, _ = MT.row(h, year)
    a = unit.amounts
    for name in DRAW_INPUTS:
        assert name not in row or row[name] != 0
    assert row.get("e03270", 0.0) == a["se_health_insurance"]
    assert row.get("e03300", 0.0) == a["se_pension"]
    assert row.get("e58990", 0.0) == a["form_4952_elected"]
    mortgage = S.deductible_mortgage_interest(year, unit.status, a["mortgage_interest"], a["mortgage_balances"])
    assert abs(row["e19200"] - mortgage - a["investment_interest_allowed"]) < 1e-6
    assert row["f2441"] == len(unit.care_individuals)
    assert row["auto_loan_interest"] == a["qualified_vehicle_loan_interest"]


def test_taxcalc_board_shaped_row_has_no_draw_inputs():
    row, *_ = MT.row(household(person("head", 40, 50_000, self_employment_income=10_000)), 2026)
    assert not set(DRAW_INPUTS) & set(row)


def test_taxcalc_vehicle_loan_interest_and_rate_gains():
    h = household(person("head", 60, 90_000, long_term_capital_gains=20_000, long_term_capital_gains_on_collectibles=3_000),
                  unrecaptured_section_1250_gain=5_000)
    h["household_inputs"]["qualified_passenger_vehicle_loan_interest"] = 4_000
    row, *_ = MT.row(h, 2026)
    assert row["auto_loan_interest"] == 4_000                       # Tax-Calculator limits it
    assert row["e24515"] == 5_000 and row["e24518"] == 3_000 and row["p23250"] == 20_000


def test_taxcalc_investment_interest_and_election():
    head = person("head", 45, 120_000, taxable_interest_income=1_000, investment_interest_expense=20_000,
                  qualified_dividend_income=12_606, long_term_capital_gains=2_197, short_term_capital_gains=298,
                  investment_income_elected_form_4952=31_035)
    row, unit, unexpressed, computed = MT.row(household(head), 2026)
    assert row["e58990"] == 12_606 + 2_197
    # 163(d): interest 1,000 + net short-term gain 298 + elected 14,803 = 16,101 of 20,000.
    assert row["e19200"] == 16_101 == unit.amounts["investment_interest_allowed"]
    assert any("Form 4952 line 4e" in n and "2,197" in n for n in unexpressed)
    assert any("163(d)(1)" in c for c in computed)


def test_taxcalc_se_health_pension_and_compensation():
    head = person("head", 45, 0.0, self_employment_income=40_000, is_self_employed=True, health_insurance_premiums=6_000,
                  self_employed_pension_contributions_desired=5_000, traditional_ira_contributions_desired=7_000)
    row, unit, _, computed = MT.row(household(head), 2026)
    assert row["e03300"] == 5_000 and abs(row["e03270"] - 6_000) < 1e-9
    assert any("e03270" in c for c in computed) and any("e03300" in c for c in computed)
    plain = U.build(household(person("head", 45, 0.0, self_employment_income=40_000)), 2026)
    assert abs(MT._compensation(plain.head) - MT._compensation(unit.head) - 5_000) < 1e-6
    # The saver's credit counts the pension contribution as the key does (pass 3).
    small_head = person("head", 45, 0.0, self_employment_income=15_000, self_employed_pension_contributions_desired=1_000)
    row, unit, _, computed = MT.row(household(small_head), 2026)
    after = MT.after_pass(3, row, unit, 13_000.0, computed)
    assert after["e07240"] == 0.5 * 1_000


def test_taxcalc_care_individuals_and_deemed_income_note():
    spouse = person("spouse", 45, 0.0, is_incapable_of_self_care=True, pre_subsidy_care_expenses=4_000)
    row, unit, unexpressed, _ = MT.row(household(person("head", 45, 50_000), spouse), 2026)
    assert row["f2441"] == 1 and row["nu13"] == 0 and row["e32800"] == 4_000
    assert any("no deemed earned income" in n and "3,000" in n for n in unexpressed)


def test_taxcalc_w2_wages_follow_the_selected_kind():
    head = person("head", 50, 0.0, self_employment_income=10_000, sstb_self_employment_income_before_lsr=30_000,
                  w2_wages_from_qualified_business=50_000, sstb_w2_wages_from_qualified_business=20_000)
    row, _, _, computed = MT.row(household(head), 2026)
    # A mixed unit (SSTB 30,000 against other 10,000): the SSTB kind and its wages.
    assert row["PT_SSTB_income"] == 1 and row["PT_binc_w2_wages"] == 20_000
    assert any("PT_SSTB_income selects" in c for c in computed)
    # One kind only: the whole pool.
    head = person("head", 50, 0.0, sstb_self_employment_income_before_lsr=30_000,
                  w2_wages_from_qualified_business=50_000, sstb_w2_wages_from_qualified_business=50_000)
    row, _, _, computed = MT.row(household(head), 2026)
    assert row["PT_SSTB_income"] == 1 and row["PT_binc_w2_wages"] == 50_000
    assert not any("PT_SSTB_income selects" in c for c in computed)
    head = person("head", 50, 0.0, self_employment_income=10_000, sstb_self_employment_income_before_lsr=30_000,
                  partnership_income=60_000, w2_wages_from_qualified_business=50_000, sstb_w2_wages_from_qualified_business=20_000)
    row, _, _, computed = MT.row(household(head), 2026)
    assert row["PT_SSTB_income"] == 0 and row["PT_binc_w2_wages"] == 30_000   # the non-SSTB pool
    assert any("PT_SSTB_income selects" in c for c in computed)


def test_taxsim_separate_filer():
    h = household(person("head", 40, 50_000, is_separated=True), None, [person("dependent1", 70)])
    record, unit, unexpressed, _ = MS.first_pass(h, 2026)
    assert unit.status == S.SEPARATE and record["mstat"] == 6
    assert any("files a separate filer" in n for n in unexpressed)
    record, *_ = MS.first_pass(household(person("head", 40, 50_000, is_separated=True)), 2026)
    assert record["mstat"] == 6


def test_taxsim_se_adjustments_and_notes():
    head = person("head", 45, 0.0, self_employment_income=40_000, is_self_employed=True, health_insurance_premiums=6_000,
                  self_employed_pension_contributions_desired=5_000)
    record, unit, unexpressed, _ = MS.first_pass(household(head), 2026)
    assert abs(record["nonprop"] + 11_000) < 1e-6
    assert any("does not subtract them from qualified business income" in n for n in unexpressed)
    state = {}
    for pass_number in (1, 2, 3):
        record = MS.after_pass(pass_number, record, unit, 30_000.0, [], unexpressed, state)
    assert abs(record["nonprop"] + 11_000) < 1e-6


def test_taxsim_election_investment_interest_and_vehicle():
    head = person("head", 45, 120_000, taxable_interest_income=1_000, investment_interest_expense=20_000,
                  qualified_dividend_income=10_000, investment_income_elected_form_4952=6_000,
                  long_term_capital_gains=4_000)
    h = household(head)
    h["household_inputs"]["qualified_passenger_vehicle_loan_interest"] = 5_000
    record, unit, unexpressed, computed = MS.first_pass(h, 2026)
    # Net capital gain first (4,000), then 2,000 of qualified dividends.
    assert record["ltcg"] == 0 and record["dividends"] == 8_000 and record["intrec"] == 7_000
    assert any("Form 4952 election" in c for c in computed)
    unexpressed = list(unexpressed)
    record = MS.after_pass(3, record, unit, 110_000.0, computed, unexpressed, {})
    assert record["mortgage"] == unit.amounts["investment_interest_allowed"] == 7_000
    assert any("vehicle loan interest" in n and "3,000" in n for n in unexpressed)   # 5,000 - 10 x 200
    unexpressed = []
    MS.after_pass(3, record, unit, 160_000.0, [], unexpressed, {})
    assert not any("vehicle loan interest" in n for n in unexpressed)                 # fully phased out


def test_taxsim_rate_gains_and_care_notes():
    h = household(person("head", 60, 50_000, long_term_capital_gains=20_000), unrecaptured_section_1250_gain=5_000)
    _, _, unexpressed, _ = MS.first_pass(h, 2026)
    assert any("28-percent rate gain" in n for n in unexpressed)
    member = person("dependent1", 27, 1_900, is_incapable_of_self_care=True, pre_subsidy_care_expenses=4_680)
    record, unit, unexpressed, _ = MS.first_pass(household(person("head", 61, 100_000), None, [member]), 2026)
    assert record["childcare"] == 4_680 and record["dep13"] == 0
    assert any("counts only children under 13" in n and "dependent1" in n for n in unexpressed)
    spouse = person("spouse", 47, 0.0, is_incapable_of_self_care=True, pre_subsidy_care_expenses=1_600)
    _, _, unexpressed, _ = MS.first_pass(household(person("head", 43, 44_000), spouse), 2026)
    assert any("TAXSIM has no deemed earned income" in n for n in unexpressed)


def test_taxsim_se_box_loss_is_noted():
    # Probes P7.4 and D4: a loss in `psemp` does not offset `pprofinc` for self-employment tax.
    head = person("head", 50, 0.0, sstb_self_employment_income_before_lsr=20_000,
                  partnership_income=-10_000, partnership_self_employment_net_earnings=-10_000)
    record, unit, unexpressed, _ = MS.first_pass(household(head), 2026)
    assert record["psemp"] == -10_000 and record["pprofinc"] == 20_000
    se = [n for n in unexpressed if n.startswith("self_employment:") and "does not net a loss" in n]
    it = [n for n in unexpressed if n.startswith("income_tax:") and "164(f)" in n]
    assert len(se) == 1 and "-10,000" in se[0] and "20,000" in se[0] and len(it) == 1
    # Same signs: no note.
    same = person("head", 50, 0.0, sstb_self_employment_income_before_lsr=20_000, self_employment_income=5_000)
    _, _, unexpressed, _ = MS.first_pass(household(same), 2026)
    assert not any("does not net a loss" in n for n in unexpressed)


def _floor_notes(unexpressed):
    return [n for n in unexpressed if "has no $400 floor" in n]


def test_taxsim_400_floor_note():
    # Probe P10.3: the build charges self-employment tax under $400 of net earnings.
    for profit, expected in ((300.0, 1), (100.0, 1), (5.0, 0), (1.0, 0), (500.0, 0), (433.0, 1), (434.0, 0)):
        _, _, unexpressed, _ = MS.first_pass(household(person("head", 40, 30_000, self_employment_income=profit)), 2026)
        assert len(_floor_notes(unexpressed)) == expected, profit
    # A member's own self-employment earnings.
    member = person("dependent1", 20, 0.0, self_employment_income=100)
    _, _, unexpressed, _ = MS.first_pass(household(person("head", 45, 40_000), None, [member]), 2026)
    assert len(_floor_notes(unexpressed)) == 1 and "dependent1" in _floor_notes(unexpressed)[0]


@settings(max_examples=300)
@given(st.floats(min_value=0, max_value=2_000, allow_nan=False).map(lambda x: round(x, 2)))
def test_taxsim_400_floor_note_property(profit):
    _, _, unexpressed, _ = MS.first_pass(household(person("head", 40, 30_000, self_employment_income=profit)), 2026)
    earnings = S.SE_NET_EARNINGS_SHARE * profit
    fires = earnings < S.SE_FLOOR and earnings * (S.SE_OASDI_RATE + S.SE_HI_RATE) >= 1
    assert len(_floor_notes(unexpressed)) == int(fires)


def _zero_rate_notes(notes):
    return [n for n in notes if "2026 zero rate on net capital gain" in n]


def test_taxsim_zero_rate_band_note():
    # Probes D6a and D6g; Rev. Proc. 2025-32 (49,450 single, 98,900 joint).
    single = person("head", 30, 0.0, long_term_capital_gains=74_800, short_term_capital_gains=10_200,
                    qualified_dividend_income=1_344, non_qualified_dividend_income=1_656)
    record, unit, _, _ = MS.first_pass(household(single), 2026)
    notes = _zero_rate_notes(MS.final_notes(record, unit, {"v18": 71_900.0}))
    assert len(notes) == 1 and "449.33" in notes[0]          # 49,899.33 - 49,450
    joint = household(person("head", 30, 0.0, long_term_capital_gains=132_200), person("spouse", 30))
    record, unit, _, _ = MS.first_pass(joint, 2026)
    notes = _zero_rate_notes(MS.final_notes(record, unit, {"v18": 100_000.0}))
    assert len(notes) == 1 and "898.60" in notes[0]          # 99,798.60 - 98,900
    # Below the law's end, in 2025, or for a head of household: no note.
    record, unit, _, _ = MS.first_pass(household(single), 2026)
    assert _zero_rate_notes(MS.final_notes(record, unit, {"v18": 49_000.0})) == []
    record, unit, _, _ = MS.first_pass(household(single), 2025)
    assert _zero_rate_notes(MS.final_notes(record, unit, {"v18": 71_900.0})) == []
    hoh = household(single, None, [person("child1", 8)])
    record, unit, _, _ = MS.first_pass(hoh, 2026)
    assert unit.status == S.HEAD_OF_HOUSEHOLD
    assert _zero_rate_notes(MS.final_notes(record, unit, {"v18": 71_900.0})) == []


@settings(max_examples=300)
@given(st.floats(min_value=0, max_value=200_000, allow_nan=False), st.floats(min_value=0, max_value=200_000, allow_nan=False),
       st.booleans())
def test_taxsim_zero_rate_band_property(gains, ordinary, joint):
    spouse = person("spouse", 30) if joint else None
    h = household(person("head", 30, 0.0, long_term_capital_gains=round(gains, 2), taxable_interest_income=round(ordinary, 2)), spouse)
    record, unit, _, _ = MS.first_pass(h, 2026)
    law, build = MS.ZERO_RATE_END_2026[unit.status]
    taxable = max(0.0, gains + ordinary - (32_200 if joint else 16_100))
    notes = _zero_rate_notes(MS.final_notes(record, unit, {"v18": taxable}))
    preferred = min(round(gains, 2), taxable)
    band = min(build, taxable) - max(law, taxable - preferred)
    assert len(notes) == int(round(gains, 2) > 0 and 0.15 * band >= 1)
    assert band <= build - law + 1e-6                          # never more than the gap between the two ends
