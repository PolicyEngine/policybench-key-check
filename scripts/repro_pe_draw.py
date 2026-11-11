"""One-household PolicyEngine-US experiments on inputs the 1,000-household draw states.

  envs/pe260/bin/python scripts/repro_pe_draw.py        # policyengine-us 2.60.0
  envs/pe211615/bin/python scripts/repro_pe_draw.py     # newest release

The reader of the draw's extra inputs asked for these six experiments (E1 to E6): each
builds a small synthetic household the way PolicyBench's builder does (the head and
spouse roles set as person inputs, every member in one tax unit, state TX, tax year
2026), sets the inputs under test, and prints the variables that show what the engine
does. No draw household is used. Nothing here applies PolicyBench's conventions: these
are the engine's own rules.
"""

from __future__ import annotations

from importlib.metadata import version

YEAR = 2026


def build(people: dict[str, dict], system, tax_unit: dict | None = None, household: dict | None = None,
          state: str = "TX") -> dict:
    """A situation with each input placed on the entity the engine defines it for."""
    names = list(people)
    groups = {"tax_unit": dict(tax_unit or {}), "household": dict(household or {})}
    persons: dict[str, dict] = {}
    for name, facts in people.items():
        persons[name] = {}
        for key, value in facts.items():
            entity = system.variables[key].entity.key
            if entity == "person":
                persons[name][key] = {str(YEAR): value}
            elif entity in groups:
                groups[entity][key] = groups[entity].get(key, 0) + value
            else:
                raise ValueError(f"{key} belongs to {entity}")
    married = [n for n in names if persons[n].get("is_tax_unit_head") or persons[n].get("is_tax_unit_spouse")]
    marital = {"couple": {"members": married}} if len(married) == 2 else {}
    for name in names:
        if not (len(married) == 2 and name in married):
            marital[f"{name}_unit"] = {"members": [name]}
    yearly = lambda d: {k: {str(YEAR): v} for k, v in d.items()}  # noqa: E731
    return {
        "people": persons,
        "tax_units": {"tax_unit": {"members": names, **yearly(groups["tax_unit"])}},
        "spm_units": {"spm_unit": {"members": names}},
        "families": {"family": {"members": names}},
        "marital_units": marital,
        "households": {"household": {"members": names, "state_code": {str(YEAR): state}, **yearly(groups["household"])}},
    }


HEAD = {"is_tax_unit_head": True}
SPOUSE = {"is_tax_unit_spouse": True}

CASES = [
    {
        "name": "E1 investment interest expense above investment income",
        "law": "26 U.S.C. 163(d)(1): investment interest is deductible only up to net investment income; here $1,000 of interest income.",
        "people": {"head": {**HEAD, "age": 45, "employment_income": 120_000, "taxable_interest_income": 1_000,
                            "investment_interest_expense": 20_000, "real_estate_taxes": 12_000}},
        "read": ["interest_deduction", "itemized_taxable_income_deductions", "tax_unit_itemizes", "taxable_income",
                 "income_tax_before_refundable_credits"],
    },
    {
        "name": "E1 variant B: qualified dividends with a Form 4952 election of $6,000",
        "law": "26 U.S.C. 163(d)(4)(B): net investment income includes qualified dividends only so far as the taxpayer elects, and the elected amount leaves the rate preference of 1(h); the statute's deduction here is $1,000 + $6,000.",
        "people": {"head": {**HEAD, "age": 45, "employment_income": 120_000, "taxable_interest_income": 1_000,
                            "investment_interest_expense": 20_000, "real_estate_taxes": 12_000,
                            "qualified_dividend_income": 10_000, "investment_income_elected_form_4952": 6_000}},
        "read": ["net_capital_gain", "interest_deduction", "taxable_income", "income_tax_before_refundable_credits"],
    },
    {
        "name": "E2 a separated head with an older member who has no income",
        "law": "26 U.S.C. 7703(b) and 2(b): a married person living apart files as head of household only with a qualifying child at home; otherwise separately.",
        "people": {"head": {**HEAD, "age": 40, "is_separated": True, "employment_income": 50_000},
                   "other": {"age": 70}},
        "read": ["filing_status", "head_of_household_eligible", "is_tax_unit_dependent"],
    },
    {
        "name": "E2 variant B: the other member is aged 10",
        "law": "As E2.",
        "people": {"head": {**HEAD, "age": 40, "is_separated": True, "employment_income": 50_000},
                   "other": {"age": 10}},
        "read": ["filing_status", "head_of_household_eligible", "is_tax_unit_dependent"],
    },
    {
        "name": "E2 variant C: a married couple and a third adult who is separated",
        "law": "As E2: the third adult's status does not bear on the couple's return.",
        "people": {"head": {**HEAD, "age": 40, "employment_income": 50_000},
                   "spouse": {**SPOUSE, "age": 40},
                   "other": {"age": 35, "is_separated": True}},
        "read": ["filing_status", "is_tax_unit_spouse", "is_tax_unit_dependent"],
    },
    {
        "name": "E3 self-employed health insurance premiums above Schedule C income",
        "law": "26 U.S.C. 162(l)(2)(A) with 401(c)(2): the deduction cannot exceed earned income from the business net of the deduction for half the self-employment tax; premiums deducted here are not medical expenses (162(l)(3)).",
        "people": {"head": {**HEAD, "age": 45, "is_self_employed": True, "self_employment_income": 30_000,
                            "health_insurance_premiums": 40_000,
                            "health_insurance_premiums_without_medicare_part_b": 40_000}},
        "read": ["self_employed_health_insurance_ald", "self_employment_tax", "self_employment_tax_ald",
                 "medical_expense", "medical_expense_deduction", "adjusted_gross_income"],
    },
    {
        "name": "E4 qualified vehicle loan interest of a surviving spouse at MAGI 150,000",
        "law": "26 U.S.C. 163(h)(4)(C)(ii): the phase-out starts at $100,000 ($200,000 on a joint return); 50 steps of $200 exceed $5,000, so the statute allows nothing.",
        "people": {"head": {**HEAD, "age": 50, "is_surviving_spouse": True, "employment_income": 150_000},
                   "child": {"age": 10}},
        "household": {"qualified_passenger_vehicle_loan_interest": 5_000},
        "read": ["filing_status", "auto_loan_interest_deduction"],
    },
    {
        "name": "E5 care expenses for a spouse incapable of self-care",
        "law": "26 U.S.C. 21(b)(1)(C) and (d)(2): an incapable spouse is a qualifying individual and has deemed earned income of $250 a month ($3,000).",
        "people": {"head": {**HEAD, "age": 45, "employment_income": 50_000},
                   "spouse": {**SPOUSE, "age": 45, "is_incapable_of_self_care": True, "pre_subsidy_care_expenses": 4_000}},
        "read": ["count_cdcc_eligible", "min_head_spouse_earned", "cdcc_relevant_expenses", "cdcc",
                 "tax_unit_childcare_expenses"],
    },
    {
        "name": "E5 variant B: an incapable member aged 30 with $10,000 of wages",
        "law": "26 U.S.C. 21(b)(1)(B): a person incapable of self-care who would be a dependent but for the gross income test is a qualifying individual.",
        "people": {"head": {**HEAD, "age": 45, "employment_income": 50_000},
                   "spouse": {**SPOUSE, "age": 45, "employment_income": 20_000},
                   "other": {"age": 30, "is_incapable_of_self_care": True, "employment_income": 10_000,
                             "pre_subsidy_care_expenses": 4_000}},
        "read": ["is_tax_unit_dependent", "is_cdcc_eligible", "count_cdcc_eligible", "cdcc_relevant_expenses", "cdcc"],
    },
    {
        "name": "E6 partnership income and partnership self-employment earnings under the 2.60.0 names",
        "law": "The same two facts the board states as partnership_s_corp_income and partnership_se_income.",
        "people": {"head": {**HEAD, "age": 45, "partnership_income": 50_000,
                            "partnership_self_employment_net_earnings": 50_000}},
        "read": ["partnership_s_corp_income", "adjusted_gross_income", "self_employment_tax",
                 "qualified_business_income_deduction", "eitc_earned_income"],
    },
    {
        "name": "E6 variant: the board's older name for partnership income",
        "law": "As E6: the answers should equal E6's.",
        "people": {"head": {**HEAD, "age": 45, "partnership_s_corp_income": 50_000,
                            "partnership_self_employment_net_earnings": 50_000}},
        "read": ["partnership_s_corp_income", "adjusted_gross_income", "self_employment_tax",
                 "qualified_business_income_deduction", "eitc_earned_income"],
    },
]


def main() -> None:
    from policyengine_us import CountryTaxBenefitSystem, Simulation

    system = CountryTaxBenefitSystem()
    print(f"policyengine-us {version('policyengine-us')}, tax year {YEAR}, the engine's own rules")
    for case in CASES:
        print(f"\n== {case['name']}")
        try:
            situation = build(case["people"], system, household=case.get("household"))
            sim = Simulation(situation=situation)
        except Exception as error:  # noqa: BLE001
            print(f"   could not build ({type(error).__name__}: {error})")
            continue
        print(f"   members: {list(case['people'])}")
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
