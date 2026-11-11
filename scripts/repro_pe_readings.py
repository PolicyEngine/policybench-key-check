"""One-household PolicyEngine-US experiments on facts the blind second maps read differently.

  envs/pe260/bin/python scripts/repro_pe_readings.py        # policyengine-us 2.60.0
  envs/pe211615/bin/python scripts/repro_pe_readings.py     # newest release

The comparison of the second input maps with the first (docs/second-map-*.md) turned on a
handful of facts: a scholarship, survivor benefits, an early retirement distribution, a
passive loss, a health savings account deduction above the limit, a negative
miscellaneous income, the Alaska Permanent Fund Dividend, and a pension distribution
beside a saver's credit. Each case here builds a small synthetic household the way
PolicyBench's builder does and prints what the engine does with the fact. No board or
draw household is used, and nothing applies PolicyBench's conventions: these are the
engine's own rules. The script states what it reads; it rules on nothing.
"""

from __future__ import annotations

import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repro_pe_draw import YEAR, build  # noqa: E402

HEAD = {"is_tax_unit_head": True}
SPOUSE = {"is_tax_unit_spouse": True}
INCOME = ["irs_gross_income", "adjusted_gross_income", "taxable_income", "income_tax_before_refundable_credits"]

CASES = [
    {
        "name": "R1 educational assistance beside wages",
        "law": "26 U.S.C. 117(a)-(b): a scholarship is excluded only for a degree candidate and only as far as it pays tuition and required fees, books, supplies and equipment.",
        "people": {"head": {**HEAD, "age": 20, "employment_income": 13_000, "educational_assistance": 5_000}},
        "read": INCOME,
    },
    {
        "name": "R2 survivor benefits beside wages",
        "law": "26 U.S.C. 61(a) and 72: a survivor annuity is gross income unless an exclusion applies (101(a) life insurance proceeds, 104(a)(1) workers' compensation, 38 U.S.C. 5301 veterans' benefits).",
        "people": {"head": {**HEAD, "age": 60, "employment_income": 20_000, "survivor_benefits": 28_800}},
        "read": INCOME,
    },
    {
        "name": "R3 a taxable 401(k) distribution at age 48",
        "law": "26 U.S.C. 72(t)(1): 10% additional tax on an early distribution unless an exception of 72(t)(2) applies; here 10% of 20,000.",
        "people": {"head": {**HEAD, "age": 48, "employment_income": 40_000, "taxable_401k_distributions": 20_000}},
        "read": ["qualified_retirement_penalty", *INCOME],
    },
    {
        "name": "R3 variant: the same with qualified_retirement_penalty stated as 2,000",
        "law": "As R3: shows whether the engine's line includes the additional tax when the input holds it.",
        "people": {"head": {**HEAD, "age": 48, "employment_income": 40_000, "taxable_401k_distributions": 20_000}},
        "tax_unit": {"qualified_retirement_penalty": 2_000},
        "read": ["qualified_retirement_penalty", *INCOME],
    },
    {
        "name": "R4 a net loss from rent and farm rent at wages of 199,000",
        "law": "26 U.S.C. 469(a), (c)(2), (i): a rental activity is passive and its net loss is disallowed; the $25,000 allowance needs active participation and is gone at modified AGI of $150,000.",
        "people": {"head": {**HEAD, "age": 45, "employment_income": 199_000, "rental_income": 2_000, "farm_rent_income": -2_446.59}},
        "read": INCOME,
    },
    {
        "name": "R4 variant: a rental loss of 10,000 at wages of 60,000",
        "law": "As R4: within the 469(i) allowance only if the taxpayer actively participates.",
        "people": {"head": {**HEAD, "age": 45, "employment_income": 60_000, "rental_income": -10_000}},
        "read": INCOME,
    },
    {
        "name": "R5 a health savings account deduction of 9,915.44 for a single person aged 20",
        "law": "26 U.S.C. 223(b): for 2026 at most $4,400 with self-only coverage and $8,750 with family coverage (Rev. Proc. 2025-19).",
        "people": {"head": {**HEAD, "age": 20, "employment_income": 30_000}},
        "tax_unit": {"health_savings_account_ald": 9_915.44},
        "read": ["health_savings_account_ald", "above_the_line_deductions", "adjusted_gross_income"],
    },
    {
        "name": "R6 a negative miscellaneous income beside wages",
        "law": "Form 1040 Schedule 1 line 8 takes other income; whether a stated negative amount reduces income depends on what it is, which the household does not state.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 50_000, "miscellaneous_income": -5_000}},
        "read": INCOME,
    },
    {
        "name": "R7 an Alaska resident with wages only",
        "law": "The Alaska Permanent Fund Dividend is federal gross income (Form 1040 Schedule 1 line 8g); the household states no dividend.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 49_000}},
        "state": "AK",
        "read": ["ak_permanent_fund_dividend", *INCOME],
    },
    {
        "name": "R8 a saver's credit with a taxable pension distribution above the contribution",
        "law": "26 U.S.C. 25B(d)(2)(A): distributions from a qualified plan in the testing period reduce the contributions that count; here 2,000 of contributions less 3,000 of distributions leaves nothing.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 30_000, "traditional_ira_contributions_desired": 2_000,
                            "taxable_private_pension_income": 3_000}},
        "read": ["savers_credit", "adjusted_gross_income"],
    },
    {
        "name": "R8 variant: the distribution stated as a taxable 401(k) distribution",
        "law": "As R8.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 30_000, "traditional_ira_contributions_desired": 2_000,
                            "taxable_401k_distributions": 3_000}},
        "read": ["savers_credit", "adjusted_gross_income"],
    },
    {
        "name": "R9 disability benefits at age 50 with one child",
        "law": "Employer-paid disability retirement benefits count as earned income for the EITC until the plan's minimum retirement age (IRS Pub. 596); the household does not state the plan or that age.",
        "people": {"head": {**HEAD, "age": 50, "disability_benefits": 15_000}, "child": {"age": 10}},
        "read": ["taxable_disability_benefits", "tax_unit_earned_income", "eitc", "adjusted_gross_income"],
    },
    {
        "name": "R10 rent of 10,000 with unadjusted basis of qualified property stated",
        "law": "26 U.S.C. 199A(c)(1), (d)(1): qualified business income comes from a qualified trade or business; the household states the basis and not whether the rental is a trade or business.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 50_000, "rental_income": 10_000,
                            "unadjusted_basis_qualified_property": 200_000}},
        "read": ["qualified_business_income", "qualified_business_income_deduction", "taxable_income"],
    },
    {
        "name": "R10 variant: the same rent with rental_income_would_be_qualified false",
        "law": "As R10.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 50_000, "rental_income": 10_000,
                            "unadjusted_basis_qualified_property": 200_000, "rental_income_would_be_qualified": False}},
        "read": ["qualified_business_income", "qualified_business_income_deduction", "taxable_income"],
    },
]


def main() -> None:
    from policyengine_us import CountryTaxBenefitSystem, Simulation

    system = CountryTaxBenefitSystem()
    wanted = set(sys.argv[1:])
    print(f"policyengine-us {version('policyengine-us')}, tax year {YEAR}, the engine's own rules")
    for case in CASES:
        if wanted and not any(case["name"].startswith(w) for w in wanted):
            continue
        print(f"\n== {case['name']}")
        try:
            situation = build(case["people"], system, tax_unit=case.get("tax_unit"),
                              household=case.get("household"), state=case.get("state", "TX"))
            sim = Simulation(situation=situation)
        except Exception as error:  # noqa: BLE001
            print(f"   could not build ({type(error).__name__}: {str(error)[:200]})")
            continue
        print(f"   stated: {case['people']}" + (f"; tax unit {case['tax_unit']}" if case.get("tax_unit") else "")
              + (f"; state {case['state']}" if case.get("state") else ""))
        for name in case["read"]:
            try:
                values = sim.calculate(name, YEAR)
                shown = getattr(values, "decode_to_str", lambda: values)()
                print(f"   {name}: {[str(v) if not hasattr(v, 'item') else v.item() for v in shown]}")
            except Exception as error:  # noqa: BLE001
                print(f"   {name}: not available ({type(error).__name__}: {str(error)[:120]})")
        print(f"   law: {case['law']}")


if __name__ == "__main__":
    main()
