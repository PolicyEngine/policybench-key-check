"""Write maps/board_facts.csv: every fact a board household states, as data.

One row per stated input: the axiom-oracles concept id that carries it today (if any,
read from axiom_oracles/core/case.py at 9717404e8), the Tax-Calculator field and the
TAXSIM field keycheck's maps send it to, and whether it can reach one of the four
federal lines in the key. The script fails if a household states an input that has no
row, so the file cannot fall behind the board.

  python3 scripts/make_fact_map.py --scenarios <scenarios.csv> --out maps/board_facts.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from keycheck import households as H  # noqa: E402

A = "axiom:"
NONE = ("", "", "", "none", "")
# (entity, input): (concept id, Tax-Calculator field, TAXSIM field, effect in the key, note)
FACTS = {
    ("structure", "person role (head, spouse, dependent, child)"): (A + "demographics/person#household_relation", "MARS, XTOT, n24, EIC, f2441 (derived)", "mstat, depx and dep13/dep17/dep18 or age1.. (derived)", "federal", "filing status and dependents are derived in keycheck/unit.py"),
    ("structure", "age"): (A + "demographics/person#age", "age_head, age_spouse; dependents' ages feed the counts", "page, sage; dependents' ages feed the counts", "federal", ""),
    ("structure", "state"): (A + "location/household#state_code", "", "state (sent as 0)", "indirect", "reaches federal tax only through the state and local tax deduction, which is shared from the key"),
    ("person", "employment_income"): (A + "income/person#yearly_earned_income", "e00200p/s net of deferrals, with pencon_p/s", "pwages/swages", "federal", ""),
    ("person", "alimony_expense"): ("", "e03500 (no effect in 2025-2026)", "", "federal", "the key deducts it: the engine's default divorce year is 2010; the divorce date is not stated"),
    ("person", "alimony_income"): ("", "e00800 (no effect in 2025-2026)", "", "federal", "the key taxes it, for the same reason"),
    ("person", "attends_eligible_educational_institution_for_american_opportunity_credit"): NONE,
    ("person", "bank_account_assets"): ("", "", "", "none", "nearest concept: assets/household#cash_on_hand"),
    ("person", "charitable_cash_donations"): ("", "e19800", "mortgage (the map applies the 0.5% floor)", "federal", "TAXSIM has no deduction for a non-itemizer"),
    ("person", "charitable_non_cash_donations"): ("", "e20100", "mortgage", "federal", ""),
    ("person", "child_support_expense"): NONE,
    ("person", "child_support_received"): NONE,
    ("person", "disability_benefits"): ("", "e01200 (no dedicated input)", "pensions (no dedicated input)", "federal", "taxable and not wages in the key; who paid for the coverage is not stated"),
    ("person", "educational_assistance"): NONE,
    ("person", "educator_expense"): ("", "e03220 (the map applies the limit)", "nonprop, negative", "federal", ""),
    ("person", "employer_sponsored_insurance_premiums"): NONE,
    ("person", "estate_income"): ("", "e02000", "intrec", "federal", ""),
    ("person", "farm_income"): ("", "", "", "none", "repeats farm_operations_income wherever the board states it; the engine does not read it"),
    ("person", "farm_operations_income"): ("", "e02100p/s", "psemp/ssemp", "federal", ""),
    ("person", "farm_rent_income"): ("", "e02000 and e27200", "scorp", "federal", ""),
    ("person", "financial_assistance"): NONE,
    ("person", "fsla_overtime_premium"): ("", "overtime_income", "", "federal", "TAXSIM has no input for the overtime deduction"),
    ("person", "has_american_opportunity_credit_1098_t_or_exception"): NONE,
    ("person", "has_american_opportunity_credit_institution_ein"): NONE,
    ("person", "has_champva_health_coverage_at_interview"): NONE,
    ("person", "has_esi"): NONE,
    ("person", "has_indian_health_service_coverage_at_interview"): NONE,
    ("person", "has_other_means_tested_health_coverage_at_interview"): NONE,
    ("person", "health_insurance_premiums_without_medicare_part_b"): ("", "e17500", "mortgage (the map applies the 7.5% floor)", "federal", "itemizers only"),
    ("person", "home_mortgage_interest"): (A + "housing/household#mortgage_interest_paid", "e19200 (the map applies the debt limit)", "mortgage", "federal", "itemizers only"),
    ("person", "hourly_wage"): NONE,
    ("person", "hours_worked_last_week"): NONE,
    ("person", "is_blind"): (A + "demographics/person#blind", "blind_head, blind_spouse", "", "federal", "TAXSIM has no input for blindness"),
    ("person", "is_disabled"): (A + "demographics/person#disabled", "", "", "none", "the engine's tax rules read other disability inputs, which the board never states"),
    ("person", "is_enrolled_at_least_half_time_for_american_opportunity_credit"): NONE,
    ("person", "is_paid_hourly"): NONE,
    ("person", "is_pregnant"): (A + "demographics/person#pregnant", "", "", "none", ""),
    ("person", "is_pursuing_credential_for_american_opportunity_credit"): NONE,
    ("person", "is_surviving_spouse"): ("", "MARS 5 when a qualifying child is claimed", "", "federal", "no board household qualifies; TAXSIM has no such status"),
    ("person", "is_tax_unit_head"): (A + "demographics/person#household_relation", "MARS and the head's fields", "mstat and the primary taxpayer's fields", "federal", ""),
    ("person", "is_tax_unit_spouse"): (A + "demographics/person#household_relation", "MARS 2 and the spouse's fields", "mstat 2 and the secondary taxpayer's fields", "federal", ""),
    ("person", "is_unmarried_partner_of_household_head"): ("", "keeps the head from head of household status", "", "federal", "TAXSIM files any unmarried taxpayer with a dependent as head of household"),
    ("person", "long_term_capital_gains"): (A + "income/person#long_term_capital_gains", "p23250", "ltcg", "federal", ""),
    ("person", "miscellaneous_income"): ("", "e01200 (no dedicated input)", "pensions (no dedicated input)", "federal", ""),
    ("person", "non_qualified_dividend_income"): (A + "income/person#dividend_income", "e00600", "intrec", "federal", "the concept is total dividends; non-qualified is the total less qualified"),
    ("person", "non_sch_d_capital_gains"): ("", "e01100", "ltcg", "federal", ""),
    ("person", "other_health_insurance_premiums"): NONE,
    ("person", "other_medical_expenses"): ("", "e17500", "mortgage (the map applies the 7.5% floor)", "federal", "itemizers only"),
    ("person", "over_the_counter_health_expenses"): NONE,
    ("person", "partnership_s_corp_income"): ("", "e02000 and e26270", "scorp", "federal", ""),
    ("person", "partnership_se_income"): ("", "k1bx14p/s", "psemp/ssemp, taken out of scorp", "federal", "self-employment earnings inside the partnership income, not more income"),
    ("person", "pre_subsidy_rent"): (A + "housing/household#rent_paid", "", "rentpaid (state credits only; not sent)", "none", ""),
    ("person", "qualified_bdc_income"): NONE,
    ("person", "qualified_dividend_income"): (A + "income/person#qualified_dividend_income", "e00650 and e00600", "dividends", "federal", ""),
    ("person", "qualified_reit_and_ptp_income"): ("", "", "", "federal", "a component of the qualified business income deduction neither other model has"),
    ("person", "real_estate_taxes"): (A + "housing/household#property_tax_paid", "e18500", "proptax", "federal", "itemizers only"),
    ("person", "receives_wic"): NONE,
    ("person", "rental_income"): (A + "income/person#rental_income", "e02000", "intrec (this build ignores otherprop from 2024)", "federal", "qualified business income in the key by default; not in the other two"),
    ("person", "roth_401k_contributions_desired"): ("", "e07240 (saver's credit, computed by the map)", "", "federal", "shares the 402(g) limit with traditional deferrals"),
    ("person", "roth_ira_contributions_desired"): ("", "e07240 (saver's credit, computed by the map)", "", "federal", ""),
    ("person", "salt_refund_income"): ("", "e00700", "pensions (no dedicated input)", "federal", "taxable in full in the key; the prior-year tax benefit is not stated"),
    ("person", "self_employment_income"): (A + "income/person#self_employment_income", "e00900p/s", "psemp/ssemp", "federal", ""),
    ("person", "short_term_capital_gains"): (A + "income/person#short_term_capital_gains", "p22250", "stcg", "federal", ""),
    ("person", "social_security_dependents"): (A + "income/person#social_security_benefits", "e02400", "gssi", "federal", "one concept for all four benefit types"),
    ("person", "social_security_disability"): (A + "income/person#social_security_benefits", "e02400", "gssi", "federal", ""),
    ("person", "social_security_retirement"): (A + "income/person#social_security_benefits", "e02400", "gssi", "federal", ""),
    ("person", "social_security_survivors"): (A + "income/person#social_security_benefits", "e02400", "gssi", "federal", ""),
    ("person", "sstb_self_employment_income_before_lsr"): ("", "e00900p/s with PT_SSTB_income", "pprofinc/sprofinc", "federal", ""),
    ("person", "sstb_unadjusted_basis_qualified_property"): ("", "PT_ubia_property (when the unit's business is a specified service trade)", "", "federal", "limits the qualified business income deduction above the threshold only"),
    ("person", "stock_assets"): NONE,
    ("person", "student_loan_interest"): ("", "e03210 (the map applies the cap and phase-out)", "nonprop, negative", "federal", ""),
    ("person", "survivor_benefits"): ("", "", "", "none", "not taxable in the key; taxability is not stated"),
    ("person", "tax_exempt_interest_income"): (A + "income/person#tax_exempt_interest_income", "e00400", "", "federal", "TAXSIM has no input for it"),
    ("person", "tax_exempt_ira_distributions"): ("", "e07240 (reduces the saver's credit, computed by the map)", "", "federal", ""),
    ("person", "tax_exempt_private_pension_income"): ("", "e01500 above e01700", "", "federal", "reduces the credit for the elderly or disabled"),
    ("person", "taxable_401k_distributions"): (A + "income/person#pension_income", "e01500 and e01700", "pensions", "federal", "the concept is pension income of any kind"),
    ("person", "taxable_403b_distributions"): (A + "income/person#pension_income", "e01500 and e01700", "pensions", "federal", ""),
    ("person", "taxable_interest_income"): (A + "income/person#interest_income", "e00300", "intrec", "federal", ""),
    ("person", "taxable_ira_distributions"): (A + "income/person#pension_income", "e01400", "pensions", "federal", ""),
    ("person", "taxable_private_pension_income"): (A + "income/person#pension_income", "e01500 and e01700", "pensions", "federal", ""),
    ("person", "tip_income"): ("", "tip_income", "", "none", "the key gives no tip deduction: it needs an occupation code the board cannot state"),
    ("person", "traditional_401k_contributions_desired"): ("", "pencon_p/s, and out of e00200p/s", "out of pwages/swages for income tax; in for payroll tax", "federal", ""),
    ("person", "traditional_ira_contributions_desired"): ("", "e03150 (the map applies 26 U.S.C. 219)", "nonprop, negative", "federal", ""),
    ("person", "unadjusted_basis_qualified_property"): ("", "PT_ubia_property", "", "federal", "limits the qualified business income deduction above the threshold only"),
    ("person", "unemployment_compensation"): (A + "income/person#unemployment_insurance", "e02300", "pui", "federal", ""),
    ("person", "unreimbursed_business_employee_expenses"): ("", "e20400 (no effect)", "", "none", "the deduction is suspended"),
    ("person", "veterans_benefits"): ("", "", "", "indirect", "enters the income that picks the sales tax table amount, for itemizers"),
    ("person", "weeks_unemployed"): NONE,
    ("person", "workers_compensation"): ("", "", "", "indirect", "enters the income that picks the sales tax table amount, for itemizers"),
    ("household", "auto_loan_balance"): NONE,
    ("household", "auto_loan_interest"): ("", "auto_loan_interest (sent as 0)", "", "none", "the key gives no deduction: the loan is not stated to qualify"),
    ("household", "household_vehicles_value"): NONE,
    ("spm_unit", "receives_housing_assistance"): NONE,
    ("spm_unit", "spm_unit_energy_subsidy"): NONE,
    ("spm_unit", "spm_unit_pre_subsidy_childcare_expenses"): (A + "tax/household#childcare_expenses", "e32800 with f2441", "childcare", "federal", ""),
    ("tax_unit", "domestic_production_ald"): ("", "e03240 (no effect)", "", "none", "the deduction is repealed"),
    ("tax_unit", "first_home_mortgage_balance"): ("", "limits e19200 (computed by the map)", "limits mortgage (computed by the map)", "federal", "above $750,000 of debt"),
    ("tax_unit", "first_home_mortgage_interest"): ("", "", "", "none", "the board's builder drops it: the person-level interest carries the amount"),
    ("tax_unit", "health_savings_account_ald"): ("", "e03290", "nonprop, negative", "federal", ""),
    ("tax_unit", "second_home_mortgage_balance"): ("", "limits e19200 (computed by the map)", "limits mortgage (computed by the map)", "federal", ""),
    ("tax_unit", "second_home_mortgage_interest"): ("", "", "", "none", "the board's builder drops it"),
}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    stated = Counter()
    for household in H.load(args.scenarios):
        seen = set()
        for person in H.people(household):
            seen.update(("person", key) for key in person["inputs"])
        for entity in ("tax_unit", "spm_unit", "household"):
            seen.update((entity, key) for key in household[f"{entity}_inputs"])
        stated.update(seen)
    missing = sorted(set(stated) - set(FACTS))
    if missing:
        raise SystemExit(f"stated inputs with no row: {missing}")
    unused = sorted(k for k in FACTS if k[0] != "structure" and k != ("person", "employment_income") and k not in stated)
    if unused:
        raise SystemExit(f"rows for inputs no household states: {unused}")

    rows = []
    for (entity, name), (concept, taxcalc, taxsim, effect, note) in FACTS.items():
        rows.append({
            "entity": entity, "fact": name,
            "households_stating_it": stated.get((entity, name), 100 if entity == "structure" or name == "employment_income" else 0),
            "effect_on_the_four_lines_in_the_key": effect,
            "axiom_oracles_concept_id": concept,
            "taxcalc_field": taxcalc, "taxsim_field": taxsim, "note": note,
        })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    inputs = [r for r in rows if r["entity"] != "structure" and r["fact"] != "employment_income"]
    federal = [r for r in inputs if r["effect_on_the_four_lines_in_the_key"] == "federal"]
    def count(rs, test):
        return sum(1 for r in rs if test(r))
    print(f"{len(inputs)} stated inputs; {len(federal)} can reach a federal line in the key")
    for label, rs in (("all stated inputs", inputs), ("inputs that reach a federal line", federal)):
        print(f"  {label}: concept id {count(rs, lambda r: r['axiom_oracles_concept_id'])}, "
              f"Tax-Calculator field {count(rs, lambda r: r['taxcalc_field'])}, "
              f"TAXSIM field {count(rs, lambda r: r['taxsim_field'])}, "
              f"none of the three {count(rs, lambda r: not (r['axiom_oracles_concept_id'] or r['taxcalc_field'] or r['taxsim_field']))}")


if __name__ == "__main__":
    main()
