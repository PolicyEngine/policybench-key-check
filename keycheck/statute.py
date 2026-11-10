"""Amounts a tax model may take as given, figured from the statute.

Tax-Calculator and TAXSIM take some deductions and credits as amounts the caller has
already limited (Tax-Calculator: e03150, e03210, e03220, e19200, e07240, pencon_p and
pencon_s; TAXSIM: adjustments entered as negative income). PolicyBench's households
state the underlying facts instead (contributions, interest paid, balances), so the
input maps apply each limit here, from the statute and the IRS's published amounts for
the year. A cell that depends on one of these functions is flagged `map_computed` in
the answers table: it is this file's reading of the law, not the model's.

Published amounts (sources saved by the law-2026 reader of run understand-inputs):
Rev. Proc. 2025-32 and 2024-40; IRS Notices 2025-67 and 2024-80; 26 U.S.C. 25B, 163(h),
199A(e)(2), 219, 221, 402(g), 414(v).
"""

from __future__ import annotations

import math

SINGLE, JOINT, SEPARATE, HEAD_OF_HOUSEHOLD, SURVIVING_SPOUSE = (
    "single", "joint", "separate", "head_of_household", "surviving_spouse",
)

AMOUNTS = {
    2026: {
        # 26 U.S.C. 402(g)(1), 414(v)(2)(B)(i) and (E)(i); Notice 2025-67
        "deferral_limit": 24_500, "deferral_catch_up_50": 8_000, "deferral_catch_up_60_63": 11_250,
        # 26 U.S.C. 219(b)(5)(A) and (B)(ii); Notice 2025-67
        "ira_limit": 7_500, "ira_catch_up_50": 1_100,
        # 26 U.S.C. 219(g)(3)(B) and (g)(7); Notice 2025-67: (start, width)
        "ira_phase_out": {
            SINGLE: (81_000, 10_000), HEAD_OF_HOUSEHOLD: (81_000, 10_000),
            JOINT: (129_000, 20_000), SURVIVING_SPOUSE: (129_000, 20_000),
            SEPARATE: (0, 10_000), "spouse_of_participant": (242_000, 10_000),
        },
        # 26 U.S.C. 221(b); Rev. Proc. 2025-32 sec. 4.29: (start, width)
        "student_loan_cap": 2_500,
        "student_loan_phase_out": {JOINT: (175_000, 30_000), "other": (85_000, 15_000)},
        # 26 U.S.C. 62(a)(2)(D); Rev. Proc. 2025-32
        "educator_cap": 350,
        # 26 U.S.C. 25B(b); Notice 2025-67: AGI ceilings of the 50%, 20% and 10% rates
        "savers": {
            JOINT: (48_500, 52_500, 80_500), HEAD_OF_HOUSEHOLD: (36_375, 39_375, 60_375),
            "other": (24_250, 26_250, 40_250),
        },
        "savers_contribution_cap": 2_000,
        # 26 U.S.C. 163(h)(3)(F)(i)(II): acquisition debt incurred after 2017-12-15
        "mortgage_debt_limit": {SEPARATE: 375_000, "other": 750_000},
        # 26 U.S.C. 199A(e)(2) threshold amount; Rev. Proc. 2025-32 sec. 4.26
        "qbi_threshold": {JOINT: 403_500, SEPARATE: 201_775, "other": 201_750},
    },
    2025: {
        "deferral_limit": 23_500, "deferral_catch_up_50": 7_500, "deferral_catch_up_60_63": 11_250,
        "ira_limit": 7_000, "ira_catch_up_50": 1_000,
        "ira_phase_out": {
            SINGLE: (79_000, 10_000), HEAD_OF_HOUSEHOLD: (79_000, 10_000),
            JOINT: (126_000, 20_000), SURVIVING_SPOUSE: (126_000, 20_000),
            SEPARATE: (0, 10_000), "spouse_of_participant": (236_000, 10_000),
        },
        "student_loan_cap": 2_500,
        "student_loan_phase_out": {JOINT: (170_000, 30_000), "other": (85_000, 15_000)},
        "educator_cap": 300,
        "savers": {
            JOINT: (47_500, 51_000, 79_000), HEAD_OF_HOUSEHOLD: (35_625, 38_250, 59_250),
            "other": (23_750, 25_500, 39_500),
        },
        "savers_contribution_cap": 2_000,
        "mortgage_debt_limit": {SEPARATE: 375_000, "other": 750_000},
        # Rev. Proc. 2024-40 sec. 2.27
        "qbi_threshold": {JOINT: 394_600, SEPARATE: 197_300, "other": 197_300},
    },
}


def elective_deferral_limit(year: int, age: int) -> float:
    """26 U.S.C. 402(g)(1) plus the catch-up of 414(v) for the participant's age at year end."""
    a = AMOUNTS[year]
    if 60 <= age <= 63:
        return a["deferral_limit"] + a["deferral_catch_up_60_63"]
    if age >= 50:
        return a["deferral_limit"] + a["deferral_catch_up_50"]
    return a["deferral_limit"]


def scale_to_limit(amounts: list[float], limit: float) -> list[float]:
    """Scale amounts down in proportion so their total does not exceed the limit.

    The statute caps the total and leaves the split to the participant. PolicyBench's
    households state "desired" amounts, and its key scales them in proportion
    (policyengine-us elective_deferral_contribution_scale, ira_contribution_scale);
    the maps use the same split so that the split is not a source of difference.
    """
    total = sum(max(0.0, x) for x in amounts)
    if total <= limit or total <= 0:
        return [max(0.0, x) for x in amounts]
    return [max(0.0, x) * limit / total for x in amounts]


def ira_contribution_limit(year: int, age: int, compensation: float) -> float:
    """26 U.S.C. 219(b)(1): the lesser of the dollar limit (with catch-up) and compensation."""
    a = AMOUNTS[year]
    dollars = a["ira_limit"] + (a["ira_catch_up_50"] if age >= 50 else 0)
    return max(0.0, min(dollars, compensation))


def ira_deductible_limit(
    year: int, filing_status: str, age: int, magi: float,
    active_participant: bool, spouse_active_participant: bool,
) -> float:
    """26 U.S.C. 219(g): the dollar limit an active participant (or the spouse of one) may deduct.

    The limit falls in proportion to MAGI across the phase-out range (219(g)(2)(A)); the
    reduction is rounded down to the next lowest $10 (219(g)(2)(C)), which, with a dollar
    limit that is a multiple of $10 (every limit here is), is the same as rounding the
    reduced limit up to the next $10, as the code does; while any of it is left it is at
    least $200 (219(g)(2)(B)).
    """
    a = AMOUNTS[year]
    dollars = a["ira_limit"] + (a["ira_catch_up_50"] if age >= 50 else 0)
    if active_participant:
        start, width = a["ira_phase_out"][filing_status]
    elif spouse_active_participant and filing_status == JOINT:
        start, width = a["ira_phase_out"]["spouse_of_participant"]
    elif spouse_active_participant and filing_status == SEPARATE:
        start, width = a["ira_phase_out"][SEPARATE]
    else:
        return float(dollars)
    excess = magi - start
    if excess <= 0:
        return float(dollars)
    if excess >= width:
        return 0.0
    reduced = dollars * (1 - excess / width)
    reduced = math.ceil(reduced / 10 - 1e-9) * 10
    return float(max(200, reduced))


def student_loan_interest_deduction(year: int, filing_status: str, interest: float, magi: float) -> float:
    """26 U.S.C. 221: interest up to the cap, reduced in proportion across the MAGI range.

    No deduction on a separate return (221(e)(2)).
    """
    if filing_status == SEPARATE:
        return 0.0
    a = AMOUNTS[year]
    allowed = min(max(0.0, interest), a["student_loan_cap"])
    start, width = a["student_loan_phase_out"][JOINT if filing_status == JOINT else "other"]
    fraction = min(1.0, max(0.0, (magi - start) / width))
    return allowed * (1 - fraction)


def educator_expense_deduction(year: int, expenses_by_person: list[float]) -> float:
    """26 U.S.C. 62(a)(2)(D): each eligible educator's expenses up to the cap."""
    cap = AMOUNTS[year]["educator_cap"]
    return sum(min(max(0.0, x), cap) for x in expenses_by_person)


def deductible_mortgage_interest(year: int, filing_status: str, interest: float, balances: float) -> float:
    """26 U.S.C. 163(h)(3)(F): interest on acquisition debt up to $750,000 ($375,000 separate).

    With debt above the limit the deductible share is limit / balance (IRS Pub. 936,
    Table 1, line 14). A household that states interest and no balance deducts it all.
    Every loan is treated as incurred after 2017-12-15: the households state no dates
    (keycheck.unit.READINGS["mortgage_date"]).
    """
    limits = AMOUNTS[year]["mortgage_debt_limit"]
    limit = limits[SEPARATE] if filing_status == SEPARATE else limits["other"]
    if balances <= limit or balances <= 0:
        return max(0.0, interest)
    return max(0.0, interest) * limit / balances


def savers_credit_rate(year: int, filing_status: str, agi: float) -> float:
    """26 U.S.C. 25B(b): 50%, 20% or 10% by AGI, zero above the last ceiling."""
    table = AMOUNTS[year]["savers"]
    ceilings = table.get(filing_status, table["other"])
    for rate, ceiling in zip((0.5, 0.2, 0.1), ceilings):
        if agi <= ceiling:
            return rate
    return 0.0


def savers_credit(
    year: int, filing_status: str, agi: float,
    contributions_by_filer: list[float], distributions_by_filer: list[float],
) -> float:
    """26 U.S.C. 25B: the tentative credit before the limit to tax (the model applies that).

    Each eligible filer's qualified contributions, less distributions in the testing
    period, count up to $2,000 (25B(a), (d)(2)). On a joint return a distribution to
    either spouse reduces both spouses' contributions (25B(d)(2)(D)). The households
    state only the tax year's distributions, so the rest of the testing period (the two
    prior years and the next year up to the return's due date, 25B(d)(2)(B)) is taken as
    zero (keycheck.unit.READINGS["savers_credit"]).
    """
    cap = AMOUNTS[year]["savers_contribution_cap"]
    rate = savers_credit_rate(year, filing_status, agi)
    if filing_status == JOINT:
        reduction = [sum(distributions_by_filer)] * len(contributions_by_filer)
    else:
        reduction = distributions_by_filer
    total = 0.0
    for contribution, distribution in zip(contributions_by_filer, reduction):
        total += min(cap, max(0.0, contribution - distribution))
    return rate * total


def qbi_threshold(year: int, filing_status: str) -> float:
    """26 U.S.C. 199A(e)(2): the taxable income above which the W-2 wage and property limit
    of 199A(b)(2)(B) phases in."""
    table = AMOUNTS[year]["qbi_threshold"]
    return float(table.get(filing_status, table["other"]))
