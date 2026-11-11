"""Properties of the map-side statutory amounts (keycheck/statute.py)."""

import sys
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keycheck import statute as S  # noqa: E402

years = st.sampled_from([2025, 2026])
statuses = st.sampled_from([S.SINGLE, S.JOINT, S.SEPARATE, S.HEAD_OF_HOUSEHOLD, S.SURVIVING_SPOUSE])
money = st.floats(min_value=0, max_value=2e6, allow_nan=False)
ages = st.integers(min_value=0, max_value=100)


@given(years, statuses, ages, money, money, st.booleans(), st.booleans())
def test_ira_limit_bounds_and_monotone(year, status, age, magi, more, active, spouse_active):
    a = S.ira_deductible_limit(year, status, age, magi, active, spouse_active)
    b = S.ira_deductible_limit(year, status, age, magi + more, active, spouse_active)
    full = S.AMOUNTS[year]["ira_limit"] + (S.AMOUNTS[year]["ira_catch_up_50"] if age >= 50 else 0)
    assert 0 <= a <= full
    assert b <= a  # more income never raises the limit
    assert a == 0 or a >= 200
    assert a % 10 == 0 or a == full
    if not active and not spouse_active:
        assert a == full


@given(years, statuses, money, money, money)
def test_student_loan_bounds_and_monotone(year, status, interest, magi, more):
    a = S.student_loan_interest_deduction(year, status, interest, magi)
    b = S.student_loan_interest_deduction(year, status, interest, magi + more)
    assert 0 <= a <= min(interest, 2500) + 1e-9
    assert b <= a + 1e-9
    assert S.student_loan_interest_deduction(year, status, interest + more, magi) >= a - 1e-9


@given(years, statuses, money, money)
def test_mortgage_interest_never_exceeds_interest_paid(year, status, interest, balances):
    d = S.deductible_mortgage_interest(year, status, interest, balances)
    assert 0 <= d <= interest + 1e-9
    if balances <= 375_000:
        assert d == interest


@given(st.lists(money, min_size=1, max_size=4), money)
def test_scale_to_limit_conserves_total_and_shares(amounts, limit):
    scaled = S.scale_to_limit(amounts, limit)
    total = sum(amounts)
    assert sum(scaled) <= max(limit, 0) + 1e-6 or total <= limit
    assert abs(sum(scaled) - min(total, limit if total > limit else total)) < 1e-6 * max(1.0, total)
    for before, after in zip(amounts, scaled):
        assert after <= before + 1e-9


@given(years, statuses, money, money)
def test_savers_rate_steps_down(year, status, agi, more):
    assert S.savers_credit_rate(year, status, agi) in (0.5, 0.2, 0.1, 0.0)
    assert S.savers_credit_rate(year, status, agi + more) <= S.savers_credit_rate(year, status, agi)


@given(years, statuses, money, st.lists(money, min_size=1, max_size=2), st.data())
def test_savers_credit_bounds(year, status, agi, contributions, data):
    distributions = data.draw(st.lists(money, min_size=len(contributions), max_size=len(contributions)))
    credit = S.savers_credit(year, status, agi, contributions, distributions)
    assert 0 <= credit <= 0.5 * 2000 * len(contributions) + 1e-9
    none = S.savers_credit(year, status, agi, contributions, [0.0] * len(contributions))
    assert credit <= none + 1e-9  # a distribution never raises the credit


def test_published_examples():
    # Notice 2025-67: 2026 joint active participants, range 129,000 to 149,000
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 129_000, True, False) == 7_500
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 149_000, True, False) == 0
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 139_000, True, False) == 3_750
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 148_900, True, False) == 200
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 245_000, False, True) == 5_250
    assert S.ira_deductible_limit(2026, S.SINGLE, 55, 86_000, True, False) == 4_300
    assert S.elective_deferral_limit(2026, 35) == 24_500
    assert S.elective_deferral_limit(2026, 55) == 32_500
    assert S.elective_deferral_limit(2026, 61) == 35_750
    assert S.elective_deferral_limit(2026, 64) == 32_500
    assert S.student_loan_interest_deduction(2026, S.SINGLE, 3_000, 92_500) == 1_250
    assert S.student_loan_interest_deduction(2026, S.JOINT, 3_000, 150_000) == 2_500
    assert S.savers_credit_rate(2026, S.JOINT, 48_500) == 0.5
    assert S.savers_credit_rate(2026, S.JOINT, 48_501) == 0.2
    assert S.savers_credit_rate(2026, S.SINGLE, 40_251) == 0.0
    assert S.deductible_mortgage_interest(2026, S.JOINT, 2_743, 1_000_000) == 2_743 * 0.75
    assert S.educator_expense_deduction(2026, [337.5, 400]) == 337.5 + 350


def test_published_examples_2025():
    # Notice 2024-80: 2025 IRA phase-out ranges (single 79,000-89,000, joint 126,000-146,000,
    # spouse of an active participant 236,000-246,000); IRA limit $7,000, catch-up $1,000.
    assert S.ira_deductible_limit(2025, S.SINGLE, 40, 79_000, True, False) == 7_000
    assert S.ira_deductible_limit(2025, S.SINGLE, 40, 89_000, True, False) == 0
    assert S.ira_deductible_limit(2025, S.SINGLE, 40, 84_000, True, False) == 3_500
    assert S.ira_deductible_limit(2025, S.JOINT, 40, 126_000, True, False) == 7_000
    assert S.ira_deductible_limit(2025, S.JOINT, 40, 146_000, True, False) == 0
    assert S.ira_deductible_limit(2025, S.JOINT, 55, 136_000, True, False) == 4_000
    assert S.ira_deductible_limit(2025, S.JOINT, 40, 236_000, False, True) == 7_000
    assert S.ira_deductible_limit(2025, S.JOINT, 40, 241_000, False, True) == 3_500
    assert S.ira_deductible_limit(2025, S.JOINT, 40, 246_000, False, True) == 0
    # Notice 2024-80: elective deferral $23,500, catch-up $7,500, ages 60-63 $11,250.
    assert S.elective_deferral_limit(2025, 49) == 23_500
    assert S.elective_deferral_limit(2025, 50) == 31_000
    assert S.elective_deferral_limit(2025, 60) == 34_750
    assert S.elective_deferral_limit(2025, 63) == 34_750
    assert S.elective_deferral_limit(2025, 64) == 31_000
    # Rev. Proc. 2024-40: student loan interest phase-out 85,000-100,000 (170,000-200,000 joint).
    assert S.student_loan_interest_deduction(2025, S.SINGLE, 3_000, 85_000) == 2_500
    assert S.student_loan_interest_deduction(2025, S.SINGLE, 3_000, 92_500) == 1_250
    assert S.student_loan_interest_deduction(2025, S.SINGLE, 3_000, 100_000) == 0
    assert S.student_loan_interest_deduction(2025, S.JOINT, 3_000, 185_000) == 1_250
    assert S.student_loan_interest_deduction(2025, S.JOINT, 3_000, 200_000) == 0
    assert S.student_loan_interest_deduction(2025, S.SEPARATE, 3_000, 10_000) == 0
    # Notice 2024-80: saver's credit AGI ceilings, joint 47,500 / 51,000 / 79,000.
    assert S.savers_credit_rate(2025, S.JOINT, 47_500) == 0.5
    assert S.savers_credit_rate(2025, S.JOINT, 51_000) == 0.2
    assert S.savers_credit_rate(2025, S.JOINT, 79_000) == 0.1
    assert S.savers_credit_rate(2025, S.JOINT, 79_001) == 0.0
    assert S.savers_credit_rate(2025, S.HEAD_OF_HOUSEHOLD, 59_250) == 0.1
    assert S.savers_credit_rate(2025, S.SINGLE, 39_501) == 0.0
    # Rev. Proc. 2024-40: educator expenses $300 each.
    assert S.educator_expense_deduction(2025, [337.5, 250]) == 300 + 250


def test_spouse_of_active_participant_range_2026():
    # 26 U.S.C. 219(g)(7); Notice 2025-67: 242,000-252,000.
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 242_000, False, True) == 7_500
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 247_000, False, True) == 3_750
    assert S.ira_deductible_limit(2026, S.JOINT, 40, 252_000, False, True) == 0
    # Married filing separately with an active-participant spouse: 0-10,000 (219(g)(3)(B)(iii)).
    assert S.ira_deductible_limit(2026, S.SEPARATE, 40, 5_000, False, True) == 3_750
    assert S.ira_deductible_limit(2026, S.SINGLE, 40, 500_000, False, True) == 7_500


def test_qbi_threshold():
    # 26 U.S.C. 199A(e)(2); Rev. Proc. 2025-32 sec. 4.26 and Rev. Proc. 2024-40 sec. 2.27.
    assert S.qbi_threshold(2026, S.SINGLE) == 201_750
    assert S.qbi_threshold(2026, S.HEAD_OF_HOUSEHOLD) == 201_750
    assert S.qbi_threshold(2026, S.SURVIVING_SPOUSE) == 201_750
    assert S.qbi_threshold(2026, S.SEPARATE) == 201_775
    assert S.qbi_threshold(2026, S.JOINT) == 403_500
    assert S.qbi_threshold(2025, S.SINGLE) == 197_300
    assert S.qbi_threshold(2025, S.JOINT) == 394_600


@given(st.lists(money, min_size=1, max_size=4), money)
def test_scale_to_limit_keeps_shares(amounts, limit):
    scaled = S.scale_to_limit(amounts, limit)
    total = sum(amounts)
    if total > limit and total > 0:
        for before, after in zip(amounts, scaled):
            # Each share of the total is kept: scaled_i * total == amount_i * limit.
            assert abs(after * total - before * limit) <= 1e-6 * max(1.0, before * limit)
        assert abs(sum(scaled) - limit) <= 1e-6 * max(1.0, limit)
    else:
        assert scaled == [max(0.0, x) for x in amounts]


@given(years, statuses, money, st.floats(min_value=0, max_value=3e6, allow_nan=False))
def test_mortgage_interest_exact(year, status, interest, balances):
    limit = 375_000 if status == S.SEPARATE else 750_000
    expected = interest if balances <= limit else interest * limit / balances
    assert abs(S.deductible_mortgage_interest(year, status, interest, balances) - expected) <= 1e-9 * max(1.0, interest)


def test_mortgage_interest_examples():
    assert S.deductible_mortgage_interest(2026, S.SEPARATE, 10_000, 750_000) == 5_000
    assert S.deductible_mortgage_interest(2026, S.SEPARATE, 10_000, 375_000) == 10_000
    assert S.deductible_mortgage_interest(2025, S.SINGLE, 10_000, 1_500_000) == 5_000
    assert S.deductible_mortgage_interest(2025, S.JOINT, 10_000, 0) == 10_000


# Differential: the code's 219(g) against a literal reading in exact decimal arithmetic
# (verify-unit-statute's scratch test): the reduction is the dollar limit times excess over
# width (219(g)(2)(A)), rounded down to the next lowest $10 (219(g)(2)(C)); a limit that is
# not zero is at least $200 (219(g)(2)(B)).

from decimal import ROUND_FLOOR, Decimal  # noqa: E402

from hypothesis import settings  # noqa: E402


def literal_ira(year, status, age, magi, active, spouse_active):
    a = S.AMOUNTS[year]
    dollars = Decimal(a["ira_limit"] + (a["ira_catch_up_50"] if age >= 50 else 0))
    if active:
        start, width = a["ira_phase_out"][status]
    elif spouse_active and status == S.JOINT:
        start, width = a["ira_phase_out"]["spouse_of_participant"]
    elif spouse_active and status == S.SEPARATE:
        start, width = a["ira_phase_out"][S.SEPARATE]
    else:
        return float(dollars)
    excess = Decimal(str(magi)) - start
    if excess <= 0:
        return float(dollars)
    reduction = dollars * excess / width
    if dollars - reduction <= 0:
        return 0.0
    reduction = (reduction / 10).to_integral_value(rounding=ROUND_FLOOR) * 10
    return float(max(Decimal(200), dollars - reduction))


@settings(max_examples=3000)
@given(years, statuses, st.integers(18, 90),
       st.one_of(st.integers(0, 300_000), st.floats(0, 300_000, allow_nan=False).map(lambda x: round(x, 2))),
       st.booleans(), st.booleans())
def test_ira_limit_equals_the_literal_reading(year, status, age, magi, active, spouse_active):
    assert S.ira_deductible_limit(year, status, age, magi, active, spouse_active) == literal_ira(
        year, status, age, magi, active, spouse_active
    )


def test_ira_limit_equals_the_literal_reading_on_a_grid():
    bad = []
    for year in (2025, 2026):
        for status, active, spouse_active, key in (
            (S.SINGLE, True, False, S.SINGLE), (S.JOINT, True, False, S.JOINT),
            (S.JOINT, False, True, "spouse_of_participant"), (S.SEPARATE, True, False, S.SEPARATE),
        ):
            start, width = S.AMOUNTS[year]["ira_phase_out"][key]
            for age in (40, 55):
                for cents in range(max(0, start - 50) * 100, (start + width + 50) * 100, 337):
                    magi = cents / 100
                    got = S.ira_deductible_limit(year, status, age, magi, active, spouse_active)
                    want = literal_ira(year, status, age, magi, active, spouse_active)
                    if got != want:
                        bad.append((year, status, age, magi, got, want))
    assert not bad, bad[:5]


# Facts only the larger draw states (run causes-and-draw, unit draw-maps) -------------


def test_draw_published_amounts():
    # 26 U.S.C. 415(c)(1)(A): Notice 2025-67 (2026) and Notice 2024-80 (2025).
    assert S.AMOUNTS[2026]["annual_additions"] == 72_000
    assert S.AMOUNTS[2025]["annual_additions"] == 70_000
    # The OASDI contribution and benefit base (SSA cost-of-living notices).
    assert S.AMOUNTS[2026]["social_security_wage_base"] == 184_500
    assert S.AMOUNTS[2025]["social_security_wage_base"] == 176_100
    assert S.VEHICLE_LOAN_INTEREST_CAP == 10_000


def test_vehicle_loan_interest_schedule_1a_examples():
    # Schedule 1-A lines 24-30: the smaller of the interest or $10,000, less $200 for each
    # $1,000 (rounded up: "increase 1.5 to 2, and increase 0.05 to 1") of MAGI above
    # $100,000 ($200,000 if married filing jointly).
    assert S.vehicle_loan_interest_deduction(S.SINGLE, 12_000, 100_000) == 10_000
    assert S.vehicle_loan_interest_deduction(S.SINGLE, 12_000, 101_500) == 10_000 - 2 * 200
    assert S.vehicle_loan_interest_deduction(S.SINGLE, 12_000, 100_050) == 10_000 - 1 * 200
    assert S.vehicle_loan_interest_deduction(S.JOINT, 5_000, 150_000) == 5_000
    assert S.vehicle_loan_interest_deduction(S.JOINT, 5_000, 210_000) == 5_000 - 10 * 200
    # A surviving spouse uses $100,000 (experiment E4: policyengine-us allows 5,000).
    assert S.vehicle_loan_interest_deduction(S.SURVIVING_SPOUSE, 5_000, 150_000) == 0
    assert S.vehicle_loan_interest_deduction(S.HEAD_OF_HOUSEHOLD, 0, 50_000) == 0


@given(statuses, money, money, money)
def test_vehicle_loan_interest_bounds_and_monotone(status, interest, magi, more):
    d = S.vehicle_loan_interest_deduction(status, interest, magi)
    assert 0 <= d <= min(interest, 10_000)
    assert S.vehicle_loan_interest_deduction(status, interest, magi + more) <= d   # phase-out
    assert S.vehicle_loan_interest_deduction(status, interest + more, magi) >= d
    full = min(interest, 10_000)
    assert d == 0 or abs((full - d) / 200 - round((full - d) / 200)) < 1e-6   # $200 steps
    start = 200_000 if status == S.JOINT else 100_000
    if magi <= start:
        assert d == full
    if magi > start + 50_000:   # 50 steps of $200 remove the whole $10,000 cap
        assert d == 0
    assert S.vehicle_loan_interest_deduction(S.JOINT, interest, magi) >= S.vehicle_loan_interest_deduction(S.SINGLE, interest, magi)


def test_net_capital_gain_and_election_examples():
    assert S.net_capital_gain(298, 2_197) == 2_197             # a short-term gain is not part of it
    assert S.net_capital_gain(-3_000, 10_000) == 7_000
    assert S.net_capital_gain(-12_000, 10_000) == 0
    # Form 4952 line 4g: at most qualified dividends plus net capital gain.
    assert S.elected_investment_income(6_000, 10_000, 0, 0) == 6_000
    assert S.elected_investment_income(31_035, 12_606, 298, 2_197) == 12_606 + 2_197
    assert S.elected_investment_income(-5, 1_000, 0, 0) == 0


def test_investment_interest_examples():
    # Experiment E1: interest 20,000 against 1,000 of taxable interest: 163(d)(1) allows
    # 1,000 (policyengine-us 2.60.0 deducts 20,000).
    assert S.investment_interest_deduction(20_000, 1_000, 0, 0, 0, 0, 0) == 1_000
    # E1 variant B: 10,000 of qualified dividends, 6,000 elected (163(d)(4)(B)): 7,000.
    assert S.investment_interest_deduction(20_000, 1_000, 0, 10_000, 0, 0, 6_000) == 7_000
    # Without an election, qualified dividends and net capital gain are not investment income.
    assert S.investment_interest_deduction(20_000, 0, 0, 10_000, 0, 50_000, 0) == 0
    # Non-qualified dividends and a net short-term gain are (163(d)(4)(B)(i)-(ii)).
    assert S.investment_interest_deduction(20_000, 0, 2_000, 0, 3_000, 0, 0) == 5_000
    # Interest below the limit is deductible in full.
    assert S.investment_interest_deduction(500, 1_000, 0, 0, 0, 0, 0) == 500


gain = st.floats(min_value=-200_000, max_value=200_000, allow_nan=False)


@given(money, money, money, money, gain, gain, money, money)
def test_investment_interest_bounds_and_monotone(interest, taxable, nqd, qd, short, long, elected, more):
    d = S.investment_interest_deduction(interest, taxable, nqd, qd, short, long, elected)
    assert 0 <= d <= interest + 1e-6
    net_short = max(0.0, max(0.0, short + long) - S.net_capital_gain(short, long))
    assert d <= taxable + nqd + net_short + min(elected, qd + S.net_capital_gain(short, long)) + 1e-6
    assert S.investment_interest_deduction(interest + more, taxable, nqd, qd, short, long, elected) >= d - 1e-6
    assert S.investment_interest_deduction(interest, taxable + more, nqd, qd, short, long, elected) >= d - 1e-6
    assert S.investment_interest_deduction(interest, taxable, nqd, qd, short, long, elected + more) >= d - 1e-6
    e = S.elected_investment_income(elected, qd, short, long)
    assert 0 <= e <= min(elected, qd + S.net_capital_gain(short, long)) + 1e-6


def test_self_employment_tax_examples():
    # Experiment E3: Schedule C 30,000, no wages, 2026: policyengine-us gives a deduction for
    # half the tax of 2,119.43.
    assert abs(S.self_employment_tax(2026, 30_000, 0) / 2 - 2_119.43) < 0.01
    # Above the contribution and benefit base only the 2.9% applies.
    assert abs(S.self_employment_tax(2026, 300_000, 184_500) - 0.029 * 0.9235 * 300_000) < 1e-6
    assert abs(S.self_employment_tax(2025, 300_000, 0) - (0.124 * 176_100 + 0.029 * 0.9235 * 300_000)) < 1e-6
    # 1402(b)(2): no tax when net earnings are under $400.
    assert S.self_employment_tax(2026, 433, 0) == 0           # 0.9235 * 433 = 399.9
    assert S.self_employment_tax(2026, 434, 0) > 0
    assert S.self_employment_tax(2026, -5_000, 0) == 0


@given(years, money, money, money)
def test_self_employment_tax_bounds_and_monotone(year, profit, wages, more):
    t = S.self_employment_tax(year, profit, wages)
    assert 0 <= t <= 0.153 * 0.9235 * profit + 1e-6
    assert S.self_employment_tax(year, profit + more, wages) >= t - 1e-6
    assert S.self_employment_tax(year, profit, wages + more) <= t + 1e-6
    assert t >= 0.029 * 0.9235 * profit - 1e-6 or 0.9235 * profit < 400


def test_self_employed_pension_examples():
    assert S.self_employed_pension_contribution(2026, 80_000, 200_000) == 72_000   # 415(c)(1)(A)
    assert S.self_employed_pension_contribution(2025, 80_000, 200_000) == 70_000
    assert S.self_employed_pension_contribution(2026, 5_000, 3_000) == 3_000       # Schedule C income
    assert S.self_employed_pension_contribution(2026, 5_000, -1_000) == 0
    # A SEP: 20% of (net profit - half the self-employment tax), the 25% plan rate of
    # 404(h)(1)(C) on compensation net of the contribution itself.
    half = S.self_employment_tax(2026, 100_000, 0) / 2
    limit = S.sep_deduction_limit(100_000, half)
    assert abs(limit - 0.2 * (100_000 - half)) < 1e-9
    assert abs(limit - 0.25 * (100_000 - half - limit)) < 1e-6


@given(years, money, gain, money)
def test_self_employed_pension_bounds(year, desired, schedule_c, more):
    c = S.self_employed_pension_contribution(year, desired, schedule_c)
    assert 0 <= c <= min(desired, S.AMOUNTS[year]["annual_additions"], max(0.0, schedule_c)) + 1e-9
    assert S.self_employed_pension_contribution(year, desired + more, schedule_c) >= c
    assert S.self_employed_pension_contribution(year, desired, schedule_c + more) >= c


@given(money, gain, money)
def test_self_employed_health_insurance_bounds(premiums, earned, more):
    d = S.self_employed_health_insurance_deduction(premiums, earned)
    assert 0 <= d <= premiums and d <= max(0.0, earned)
    assert S.self_employed_health_insurance_deduction(premiums, earned + more) >= d
    assert S.self_employed_health_insurance_deduction(premiums + more, earned) >= d
    # Experiment E3: premiums 40,000 on Schedule C income 30,000: the key's limit gives 30,000.
    assert S.self_employed_health_insurance_deduction(40_000, 30_000) == 30_000
