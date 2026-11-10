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
