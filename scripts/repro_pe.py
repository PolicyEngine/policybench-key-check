"""One-household reproductions of PolicyEngine-US behaviours this check turned up.

  envs/pe260/bin/python scripts/repro_pe.py            # policyengine-us 2.60.0
  envs/pe211615/bin/python scripts/repro_pe.py         # newest release

Each case builds a small household, prints the variables that show the behaviour, and
states what the law gives with its citation. Nothing here uses PolicyBench's builder or
conventions: these are the engine's own defaults at tax year 2026.
"""

from __future__ import annotations

from importlib.metadata import version

YEAR = 2026


def situation(people: dict, tax_unit: dict | None = None, household: dict | None = None) -> dict:
    names = list(people)
    yearly = lambda d: {k: {str(YEAR): v} for k, v in d.items()}  # noqa: E731
    unit = {"members": names, **yearly(tax_unit or {})}
    home = {"members": names, "state_code": {str(YEAR): "TX"}, **yearly(household or {})}
    married = [n for n in names if n in ("head", "spouse")]
    marital = {"couple": {"members": married}} if len(married) == 2 else {}
    for name in names:
        if not (len(married) == 2 and name in married):
            marital[f"{name}_unit"] = {"members": [name]}
    return {
        "people": {n: yearly(p) for n, p in people.items()},
        "tax_units": {"tax_unit": unit},
        "spm_units": {"spm_unit": {"members": names}},
        "families": {"family": {"members": names}},
        "marital_units": marital,
        "households": {"household": home},
    }


CASES = [
    {
        "name": "credit for other dependents with no gross income test",
        "law": "26 U.S.C. 152(d)(1)(B): a qualifying relative's gross income must be under the exemption amount ($5,300 for 2026, Rev. Proc. 2025-32); a 27-year-old with $45,000 of wages is not a dependent, so no $500 credit (26 U.S.C. 24(h)(4)).",
        "situation": situation({
            "head": {"age": 50, "employment_income": 80_000, "is_tax_unit_head": True},
            "spouse": {"age": 50, "employment_income": 0, "is_tax_unit_spouse": True},
            "adult": {"age": 27, "employment_income": 45_000},
        }),
        "read": ["ctc", "non_refundable_ctc", "income_tax_before_refundable_credits"],
    },
    {
        "name": "surviving spouse: child tax credit phase-out threshold",
        "law": "26 U.S.C. 24(h)(3): $400,000 in the case of a joint return, $200,000 in any other case. At MAGI 300,000 one child's $2,200 credit is reduced by $50 x 100 = $5,000, to zero.",
        "situation": situation({
            "head": {"age": 45, "employment_income": 300_000, "is_tax_unit_head": True, "is_surviving_spouse": True},
            "child": {"age": 10, "employment_income": 0},
        }),
        "read": ["filing_status", "ctc", "ctc_phase_out"],
    },
    {
        "name": "surviving spouse: vehicle loan interest phase-out start",
        "law": "26 U.S.C. 163(h)(4)(C)(ii): reduced by $200 per $1,000 of MAGI over $100,000 ($200,000 for a joint return). At MAGI 150,000, $5,000 of interest is reduced by $10,000, to zero.",
        "situation": situation(
            {
                "head": {"age": 45, "employment_income": 150_000, "is_tax_unit_head": True, "is_surviving_spouse": True},
                "child": {"age": 10, "employment_income": 0},
            },
            household={"qualified_passenger_vehicle_loan_interest": 5_000},
        ),
        "read": ["filing_status", "auto_loan_interest_deduction"],
    },
    {
        "name": "overtime deduction phase-out: continuous, where the form steps",
        "law": "26 U.S.C. 225(b)(2): reduced by $100 for each $1,000 by which MAGI exceeds $150,000; Schedule 1-A drops a fraction of $1,000. At MAGI 160,500 the reduction is $1,000 and the deduction $11,500.",
        "situation": situation({
            "head": {"age": 40, "employment_income": 160_500, "fsla_overtime_premium": 12_500, "is_tax_unit_head": True},
        }),
        "read": ["adjusted_gross_income", "overtime_income_deduction"],
    },
    {
        "name": "saver's credit: a spouse's distribution does not reduce the other spouse's contributions",
        "law": "26 U.S.C. 25B(d)(2)(D): on a joint return a distribution to either spouse reduces both spouses' contributions. Here $2,000 of contributions less $3,000 of distributions leaves nothing, so no credit.",
        "situation": situation({
            "head": {"age": 40, "employment_income": 40_000, "traditional_ira_contributions_desired": 2_000, "is_tax_unit_head": True},
            "spouse": {"age": 40, "employment_income": 0, "taxable_ira_distributions": 3_000, "is_tax_unit_spouse": True},
        }),
        "read": ["adjusted_gross_income", "savers_credit"],
    },
    {
        "name": "rental income counts as qualified business income by default",
        "law": "26 U.S.C. 199A(d)(1): a qualified trade or business. Rental real estate qualifies only if it rises to a trade or business (or meets Rev. Proc. 2019-38); the household states no such fact.",
        "situation": situation({
            "head": {"age": 40, "employment_income": 50_000, "rental_income": 10_000, "is_tax_unit_head": True},
        }),
        "read": ["qualified_business_income_deduction", "taxable_income"],
    },
    {
        "name": "alimony paid is deductible when no divorce year is given",
        "law": "Pub. L. 115-97 sec. 11051: alimony under an instrument executed after 2018 is not deductible and not income. The engine's default divorce year is 2010.",
        "situation": situation({
            "head": {"age": 40, "employment_income": 80_000, "alimony_expense": 5_000, "is_tax_unit_head": True},
        }),
        "read": ["alimony_expense_ald", "adjusted_gross_income"],
    },
    {
        "name": "the $400 minimum qualified business income deduction with no active-business test",
        "law": "26 U.S.C. 199A(i): the minimum applies to a taxpayer with at least $1,000 of qualified business income from active trades or businesses in which the taxpayer materially participates.",
        "situation": situation({
            "head": {"age": 40, "employment_income": 50_000, "rental_income": 1_200, "is_tax_unit_head": True},
        }),
        "read": ["qualified_business_income_deduction"],
    },
]


def main() -> None:
    from policyengine_us import Simulation

    print(f"policyengine-us {version('policyengine-us')}, tax year {YEAR}")
    for case in CASES:
        sim = Simulation(situation=case["situation"])
        print(f"\n== {case['name']}")
        for name in case["read"]:
            try:
                values = sim.calculate(name, YEAR)
                shown = getattr(values, "decode_to_str", lambda: values)()
                print(f"   {name}: {[str(v) if not hasattr(v, 'item') else v.item() for v in shown]}")
            except Exception as error:  # noqa: BLE001
                print(f"   {name}: not available ({type(error).__name__}: {error})")
        print(f"   law: {case['law']}")


if __name__ == "__main__":
    main()
