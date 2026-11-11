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
199A(e)(2), 219, 221, 402(g), 414(v). For the facts only the larger draw states (run
causes-and-draw, unit draw-maps): 26 U.S.C. 162(l), 163(d), 163(h)(4), 401(c)(2), 415(c),
1401 and 1402, Schedule 1-A (2025), and the Social Security contribution and benefit base
for 2025 and 2026 (Federal Register notices of the cost-of-living adjustment).
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
        # 26 U.S.C. 415(c)(1)(A); Notice 2025-67 (sources/irs/n-25-67.txt:28-29)
        "annual_additions": 72_000,
        # 42 U.S.C. 430; SSA, 90 FR (2025-19763) (sources/ssa/fr-2025-19763-cola-2026.txt:380-403)
        "social_security_wage_base": 184_500,
        # 26 U.S.C. 223(b)(2)(A)-(B); Rev. Proc. 2025-19 (sources/irs/rp-25-19.txt:41, :45);
        # 223(b)(3)(B): the catch-up from age 55 is $1,000 from 2009 (sources/uscode/lii-26-223.txt:42)
        "hsa_self_only": 4_400, "hsa_family": 8_750, "hsa_catch_up_55": 1_000,
        # 26 U.S.C. 199A(i)(1)(B), (2)(A) (sources/uscode/usc26-s199A.txt:273-283): from 2026
        # (Pub. L. 119-21 sec. 70105); indexed only after 2026 (199A(i)(3))
        "qbi_minimum_deduction": 400, "qbi_minimum_active_income": 1_000,
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
        # Notice 2024-80 (sources/irs/n-24-80.txt:28-29)
        "annual_additions": 70_000,
        # SSA, 89 FR (2024-24871) (sources/ssa/fr-2024-24871-cola-2025.txt:380-403)
        "social_security_wage_base": 176_100,
        # Rev. Proc. 2024-25 (sources/irs/rp-24-25.txt:36-38, :41-43); 223(b)(3)(B)
        "hsa_self_only": 4_300, "hsa_family": 8_550, "hsa_catch_up_55": 1_000,
        # 199A(i) applies to taxable years beginning after 2025
        "qbi_minimum_deduction": 0, "qbi_minimum_active_income": math.inf,
    },
}

# 26 U.S.C. 72(t)(1) (sources/uscode/lii-26-72.txt:586-588): 10% additional tax on the part
# of a distribution from a qualified retirement plan (4974(c)) included in gross income,
# unless 72(t)(2) excepts it (age 59 1/2, disability under 72(m)(7), medical care, ...: :590-611).
EARLY_DISTRIBUTION_RATE = 0.10
# 72(t)(2)(B) (lii-26-72.txt:610-611): distributions up to the 213 deduction for the year's
# medical care, figured whether or not the taxpayer itemizes: expenses above 7.5% of AGI (213(a)).
MEDICAL_FLOOR = 0.075
# 26 U.S.C. 170(b)(1)(G)(i), (A), (I) (sources/uscode/usc26-s170.txt:56, 96-99, 111):
# cash to a public charity up to 60% of the contribution base, other gifts to one up to 50%
# less the cash allowed ((G)(iii)(II)), and from 2026 only the excess of the total over 0.5%.
CHARITY_CASH_CEILING, CHARITY_PUBLIC_CEILING = 0.60, 0.50
CHARITY_FLOOR = {2026: 0.005, 2025: 0.0}

# 26 U.S.C. 163(h)(4)(C), taxable years 2025 through 2028 (sources/uscode/usc26-s163.txt:263,
# 266; Schedule 1-A lines 24-30, sources/irs/f1040s1a.txt:84-91): interest up to $10,000,
# reduced by $200 for each $1,000 (or part of $1,000) of MAGI above $100,000 ($200,000 on a
# joint return). Not indexed.
VEHICLE_LOAN_INTEREST_CAP = 10_000
VEHICLE_LOAN_PHASE_OUT_START = {JOINT: 200_000, "other": 100_000}

# 26 U.S.C. 1401(a), (b)(1): 12.4% OASDI and 2.9% HI on self-employment income
# (sources/uscode/usc26-s1401.txt:32, 35); 1402(a)(12): the deduction that makes net
# earnings 92.35% of net profit (usc26-s1402.txt:54-56); 1402(b)(1)-(2): OASDI only up to
# the contribution and benefit base less wages, and none below $400 (usc26-s1402.txt:74-75).
SE_OASDI_RATE, SE_HI_RATE, SE_NET_EARNINGS_SHARE, SE_FLOOR = 0.124, 0.029, 0.9235, 400.0


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


def vehicle_loan_interest_deduction(filing_status: str, interest: float, magi: float) -> float:
    """26 U.S.C. 163(h)(4)(C), Schedule 1-A lines 24-30: qualified passenger vehicle loan
    interest up to $10,000, less $200 for each $1,000 or part of $1,000 of modified AGI over
    $100,000 ($200,000 on a joint return only: a surviving spouse uses $100,000). Sources at
    VEHICLE_LOAN_INTEREST_CAP. Modified AGI is AGI plus excluded foreign and possession
    income (163(h)(4)(C)(ii)), none of which the board states."""
    allowed = min(max(0.0, interest), VEHICLE_LOAN_INTEREST_CAP)
    start = VEHICLE_LOAN_PHASE_OUT_START[JOINT if filing_status == JOINT else "other"]
    excess = magi - start
    if excess <= 0:
        return allowed
    steps = math.ceil(excess / 1_000 - 1e-9)
    return max(0.0, allowed - 200.0 * steps)


def net_capital_gain(short_term: float, long_term: float) -> float:
    """26 U.S.C. 1222(11): net long-term capital gain in excess of net short-term capital loss
    (1(h) and 163(d)(4)(B) use it; Form 4952 line 4e)."""
    return max(0.0, long_term - max(0.0, -short_term))


def elected_investment_income(elected: float, qualified_dividends: float, short_term: float, long_term: float) -> float:
    """26 U.S.C. 163(d)(4)(B)(iii) and its last sentence: the qualified dividends and net
    capital gain a taxpayer elects to treat as investment income (sources/uscode/
    usc26-s163.txt:70-71), at most the qualified dividends plus the net capital gain (Form
    4952 line 4g takes them from lines 4b and 4e)."""
    return min(max(0.0, elected), max(0.0, qualified_dividends) + net_capital_gain(short_term, long_term))


def investment_interest_deduction(
    interest: float, taxable_interest: float, non_qualified_dividends: float,
    qualified_dividends: float, short_term: float, long_term: float, elected: float,
) -> float:
    """26 U.S.C. 163(d)(1): investment interest up to net investment income
    (sources/uscode/usc26-s163.txt:45; definitions (d)(3)-(4) at :51-75).

    Investment income (163(d)(4)(B)): gross income from property held for investment
    (here taxable interest and non-qualified dividends), the net gain from dispositions in
    excess of the net capital gain (the net short-term gain), and the elected qualified
    dividends and net capital gain. Investment expenses (163(d)(4)(C)) and a carryforward
    (163(d)(2)) are taken as zero (keycheck.unit.READINGS["investment_interest"]).
    """
    net_gain = max(0.0, short_term + long_term)
    income = (
        max(0.0, taxable_interest) + max(0.0, non_qualified_dividends)
        + max(0.0, net_gain - net_capital_gain(short_term, long_term))
        + elected_investment_income(elected, qualified_dividends, short_term, long_term)
    )
    return min(max(0.0, interest), income)


def self_employment_tax(year: int, net_profit: float, wages: float) -> float:
    """26 U.S.C. 1401(a) and (b)(1) on self-employment income (1402(b)): 12.4% of net earnings
    up to the contribution and benefit base (184,500 for 2026, 176,100 for 2025; AMOUNTS)
    less wages, and 2.9% of all net earnings, where net earnings are 92.35% of net profit
    (1402(a)(12)) and nil below $400 (1402(b)(2)); sources at SE_OASDI_RATE. The 0.9% of
    1401(b)(2) (usc26-s1401.txt:38) is left out: the 164(f) deduction excludes it
    (usc26-s164.txt:134). Half of this is the 164(f) deduction."""
    earnings = SE_NET_EARNINGS_SHARE * max(0.0, net_profit)
    if earnings < SE_FLOOR:
        return 0.0
    room = max(0.0, AMOUNTS[year]["social_security_wage_base"] - max(0.0, wages))
    return SE_OASDI_RATE * min(earnings, room) + SE_HI_RATE * earnings


def self_employed_pension_contribution(year: int, desired: float, schedule_c: float) -> float:
    """The self-employed pension contribution the board's key allows: the lesser of the
    desired amount, the 415(c)(1)(A) annual additions limit (72,000 for 2026, 70,000 for
    2025; AMOUNTS, Notices 2025-67 and 2024-80) and Schedule C income (415(c)(1)(B): 100%
    of compensation, taken as Schedule C income as the key does; policyengine-us
    self_employed_pension_contribution_limit.py; keycheck.unit.READINGS["se_pension"]: the
    plan type that sets the 404 limit is not stated)."""
    return max(0.0, min(desired, AMOUNTS[year]["annual_additions"], max(0.0, schedule_c)))


def sep_deduction_limit(net_profit: float, half_se_tax: float) -> float:
    """26 U.S.C. 404(a)(3)(A), (h)(1)(C) and (a)(8)(D): a SEP contribution for a
    self-employed person is deductible up to 25% of compensation, where compensation is
    earned income net of the contribution itself (401(c)(2)(A)(v)) and of the 164(f)
    deduction: 25% of (net profit - half the self-employment tax - the contribution), or
    20% of (net profit - half the self-employment tax). Sources: sources/uscode/
    lii-26-404.txt:105, 150-158, 239; lii-26-401.txt:704-717."""
    return max(0.0, 0.2 * (net_profit - half_se_tax))


def self_employed_health_insurance_deduction(premiums: float, earned_income: float) -> float:
    """26 U.S.C. 162(l)(1), (2)(A): premiums up to the earned income (401(c)(2)) from the
    business under which the plan is established (sources/uscode/lii-26-162.txt:205-216;
    401(c)(2)(A)(v)-(vi): net of the 404 deduction and the 164(f) deduction,
    lii-26-401.txt:704-717). Called with Schedule C income for the key's looser limit."""
    return min(max(0.0, premiums), max(0.0, earned_income))


def hsa_deduction_limit(year: int, age: int) -> float:
    """26 U.S.C. 223(b)(1)-(3): the limit for one eligible individual with self-only coverage
    for the whole year (4,400 for 2026, 4,300 for 2025: Rev. Proc. 2025-19 and 2024-25),
    plus the $1,000 additional contribution from age 55 (223(b)(3)). Sources at AMOUNTS.
    keycheck.unit.READINGS["hsa"]: the stated deduction states one eligible individual, the
    head; family coverage and a second eligible spouse are not stated."""
    a = AMOUNTS[year]
    return float(a["hsa_self_only"] + (a["hsa_catch_up_55"] if age >= 55 else 0))


def early_distribution_tax(early_distributions: float, medical_expenses: float, agi: float) -> float:
    """26 U.S.C. 72(t)(1): 10% of the early distributions included in gross income, less the
    distributions 72(t)(2)(B) excepts: up to the amount deductible under 213 for the year's
    medical care (expenses above 7.5% of AGI), figured whether or not the taxpayer itemizes.
    `early_distributions` holds only distributions no other stated fact excepts
    (keycheck.unit.READINGS["retirement_penalty"])."""
    early = max(0.0, early_distributions)
    medical = max(0.0, max(0.0, medical_expenses) - MEDICAL_FLOOR * max(0.0, agi))
    return EARLY_DISTRIBUTION_RATE * max(0.0, early - medical)


def charitable_deduction(year: int, cash: float, non_cash: float, contribution_base: float) -> float:
    """26 U.S.C. 170(b)(1) for gifts to public charities (170(b)(1)(A) organizations): cash
    up to 60% of the contribution base (170(b)(1)(G)(i)); other gifts, ordinary-income
    property, up to 50% less the cash allowed (170(b)(1)(A), (G)(iii)(II)); then from 2026
    only the part of the total above 0.5% of the contribution base (170(b)(1)(I)). The
    contribution base is AGI without a net operating loss carryback (170(b)(1)(H)). The
    excess over a ceiling carries forward five years (170(d)(1), (b)(1)(G)(ii)); no household
    states a carryforward into the year. keycheck.unit.READINGS["charity"]."""
    base = max(0.0, contribution_base)
    cash_allowed = min(max(0.0, cash), CHARITY_CASH_CEILING * base)
    other_allowed = min(max(0.0, non_cash), max(0.0, CHARITY_PUBLIC_CEILING * base - cash_allowed))
    return max(0.0, cash_allowed + other_allowed - CHARITY_FLOOR[year] * base)


def passive_activity_allowed(amounts: list[float]) -> list[float]:
    """26 U.S.C. 469(a)-(b) (sources/uscode/lii-26-469.txt:15-30) for one return's passive
    activities, each given as its net income (+) or loss (-): a net passive activity loss is
    disallowed and carries forward to the next year (469(b)); the disallowed loss falls on
    the loss activities in proportion to their losses (Temp. Reg. 1.469-1T(f)(2)(i),
    sources/cfr/lii-26-cfr-1.469-1T.txt:165-198). Returns each activity's allowed amount:
    income stands; each loss keeps its share of the passive income. No 469(i) offset: no
    household states active participation (keycheck.unit.READINGS["passive_activity"])."""
    income = sum(x for x in amounts if x > 0)
    losses = -sum(x for x in amounts if x < 0)
    if losses <= income:
        return [float(x) for x in amounts]
    share = income / losses
    return [float(x) if x >= 0 else float(x) * share for x in amounts]


# 26 U.S.C. 24(b)(1), (h)(2)-(4) (sources/uscode/usc26-s24.txt:35, :92-97): $2,200 a
# qualifying child (2025; indexed after 2025, $2,200 for 2026: Rev. Proc. 2025-32,
# sources/irs/rp-25-32.txt:594) and $500 a dependent
# who is not one, reduced by $50 for each $1,000 "or fraction thereof" of modified AGI
# above $400,000 on a joint return and $200,000 otherwise.
CHILD_CREDIT_THRESHOLD = {JOINT: 400_000, "other": 200_000}


def child_credit_reduction(filing_status: str, magi: float) -> float:
    """26 U.S.C. 24(b)(1): $50 for each $1,000 or fraction thereof of modified AGI above the
    threshold of 24(h)(3) (usc26-s24.txt:35, :94)."""
    threshold = CHILD_CREDIT_THRESHOLD.get(filing_status, CHILD_CREDIT_THRESHOLD["other"])
    excess = max(0.0, magi - threshold)
    return 50.0 * math.ceil(round(excess, 2) / 1000.0)

