"""Write maps/board_facts.csv: every fact a board household states, as data.

One row per stated input: the axiom-oracles concept id that carries it today (if any,
read from axiom_oracles/core/case.py at 9717404e8), the Tax-Calculator field and the
TAXSIM field keycheck's maps send it to, and whether it can reach one of the four
federal lines in the key. The script fails if a household states an input that has no
row, so the file cannot fall behind the board.

With --draw it writes the same map for the 1,000-household draw (maps/draw_facts.csv):
the board rows the draw states (two restated in DRAW_OVERRIDES) and the rows for the 23
inputs only the draw states (DRAW_FACTS). It fails if a draw household states an input
with no row, or if a DRAW_FACTS row has no household stating it.

  python3 scripts/make_fact_map.py --scenarios <scenarios.csv> --out maps/board_facts.csv
  python3 scripts/make_fact_map.py --draw --scenarios data/draw/draw1000_seed20261110.csv --out maps/draw_facts.csv
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
    ("person", "educational_assistance"): ("", "", "", "none", "not taxable in the maps: read as a qualified scholarship (keycheck/unit.py READINGS educational_assistance)"),
    ("person", "educator_expense"): ("", "e03220 (the map applies the limit)", "nonprop, negative", "federal", ""),
    ("person", "employer_sponsored_insurance_premiums"): NONE,
    ("person", "estate_income"): ("", "e02000", "intrec, either sign", "federal", "not qualified business income in the maps or the key"),
    ("person", "farm_income"): ("", "", "", "none", "repeats farm_operations_income wherever the board states it; the engine does not read it (READINGS farm_income)"),
    ("person", "farm_operations_income"): ("", "e02100p/s", "psemp/ssemp", "federal", ""),
    ("person", "farm_rent_income"): ("", "e02000 and e27200", "scorp", "federal", ""),
    ("person", "financial_assistance"): ("", "", "", "none", "a gift, not gross income, in the maps (READINGS financial_assistance)"),
    ("person", "fsla_overtime_premium"): ("", "overtime_income", "", "federal", "TAXSIM has no input for the overtime deduction"),
    ("person", "has_american_opportunity_credit_1098_t_or_exception"): NONE,
    ("person", "has_american_opportunity_credit_institution_ein"): NONE,
    ("person", "has_champva_health_coverage_at_interview"): NONE,
    ("person", "has_esi"): NONE,
    ("person", "has_indian_health_service_coverage_at_interview"): NONE,
    ("person", "has_other_means_tested_health_coverage_at_interview"): NONE,
    ("person", "health_insurance_premiums_without_medicare_part_b"): ("", "e17500", "mortgage (the map applies the 7.5% floor)", "federal", "itemizers only; every listed member's counts (26 U.S.C. 213(a))"),
    ("person", "home_mortgage_interest"): (A + "housing/household#mortgage_interest_paid", "e19200 (the map applies the debt limit)", "mortgage", "federal", "itemizers only"),
    ("person", "hourly_wage"): NONE,
    ("person", "hours_worked_last_week"): NONE,
    ("person", "is_blind"): (A + "demographics/person#blind", "blind_head, blind_spouse", "", "federal", "TAXSIM has no input for blindness"),
    ("person", "is_disabled"): (A + "demographics/person#disabled", "XTOT, EIC (a dependent's class, derived)", "depx, dep18; age 18 on the 2025 ages path (a dependent's class, derived)", "none", "the engine's tax rules read other disability inputs, which the board never states; keycheck/unit.py reads it for a member with no earnings as permanent and total disability (READINGS is_disabled)"),
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
    ("person", "non_sch_d_capital_gains"): ("", "e01100, or p23250 when the unit has Schedule D items", "ltcg", "federal", "capital gain distributions"),
    ("person", "other_health_insurance_premiums"): ("", "", "", "none", "not counted again: part of the premiums without Medicare Part B (READINGS other_health_insurance_premiums)"),
    ("person", "other_medical_expenses"): ("", "e17500", "mortgage (the map applies the 7.5% floor)", "federal", "itemizers only; every listed member's counts (26 U.S.C. 213(a))"),
    ("person", "over_the_counter_health_expenses"): ("", "", "", "none", "left out of medical expenses in the maps and the key (READINGS over_the_counter)"),
    ("person", "partnership_s_corp_income"): ("", "e02000 and e26270", "scorp", "federal", ""),
    ("person", "partnership_se_income"): ("", "k1bx14p/s", "psemp/ssemp, taken out of scorp", "federal", "self-employment earnings inside the partnership income, not more income"),
    ("person", "pre_subsidy_rent"): (A + "housing/household#rent_paid", "", "rentpaid (state credits only; not sent)", "none", ""),
    ("person", "qualified_bdc_income"): ("", "", "", "none", "read as part of the stated dividends (READINGS qualified_bdc_income); the engine reads it in no formula"),
    ("person", "qualified_dividend_income"): (A + "income/person#qualified_dividend_income", "e00650 and e00600", "dividends", "federal", ""),
    ("person", "qualified_reit_and_ptp_income"): ("", "", "", "federal", "a component of the qualified business income deduction neither other model has"),
    ("person", "real_estate_taxes"): (A + "housing/household#property_tax_paid", "e18500", "proptax", "federal", "itemizers only"),
    ("person", "receives_wic"): NONE,
    ("person", "rental_income"): (A + "income/person#rental_income", "e02000", "intrec, either sign (this build ignores otherprop from 2024)", "federal", "qualified business income in the key by default; not in the maps (READINGS rental_qbi)"),
    ("person", "roth_401k_contributions_desired"): ("", "e07240 (saver's credit, computed by the map)", "", "federal", "shares the 402(g) limit with traditional deferrals and, with them, is limited to wages"),
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
    ("person", "tip_income"): ("", "tip_income (sent as 0)", "", "none", "the key gives no tip deduction: it needs an occupation code the board cannot state; the maps read stated tips as not qualified (READINGS tips)"),
    ("person", "traditional_401k_contributions_desired"): ("", "pencon_p/s, and out of e00200p/s", "nonprop, negative (pwages/swages stay gross)", "federal", "limited by 402(g) and, with Roth deferrals, to wages"),
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

# Inputs only the 1,000-household draw states . The
# effect column follows the reader's trace of policyengine-us 2.60.0
# (evidence/traces/draw-inputs.md F1-F14); the fields are the ones keycheck's maps send.
DRAW_FACTS = {
    ("household", "qualified_passenger_vehicle_loan_interest"): ("", "auto_loan_interest (Tax-Calculator applies the cap and phase-out)", "", "federal", "26 U.S.C. 163(h)(4) from 2025; TAXSIM has no input, and its note gives the statute's size at TAXSIM's AGI"),
    ("person", "bond_assets"): NONE,
    ("person", "health_insurance_premiums"): ("", "e17500, or e03270 for the 162(l) part of a self-employed filer's", "mortgage (the map applies the 7.5% floor), or nonprop, negative, for the 162(l) part", "federal", "one amount with the premiums without Medicare Part B (READINGS health_insurance_premiums, se_health_insurance)"),
    ("person", "investment_income_elected_form_4952"): ("", "e58990 (limited to qualified dividends and net capital gain)", "moves net capital gain, then qualified dividends, from ltcg and dividends to intrec", "federal", "raises the 163(d) limit and leaves the rate preference (26 U.S.C. 163(d)(4)(B)); Tax-Calculator takes it from qualified dividends only"),
    ("person", "investment_interest_expense"): ("", "e19200, with mortgage interest (the map applies 163(d))", "mortgage (the map applies 163(d))", "federal", "itemizers only; the key deducts it in full (READINGS investment_interest)"),
    ("person", "is_incapable_of_self_care"): ("", "f2441 (care individuals, derived)", "childcare; TAXSIM counts children under 13 only", "federal", "the care credit only, and only with care expenses (READINGS incapable)"),
    ("person", "is_military"): NONE,
    ("person", "is_related_to_head_or_spouse"): ("", "MARS (head of household, derived)", "", "federal", "head of household only: an unrelated qualifying relative is not a qualifying person (READINGS unrelated_member)"),
    ("person", "is_self_employed"): ("", "e03270 with health_insurance_premiums (derived)", "nonprop, negative, with health_insurance_premiums (derived)", "federal", "only through health_insurance_premiums (the 162(l) deduction)"),
    ("person", "is_separated"): ("", "MARS 3 or 4 (derived)", "mstat 6, or 1 with a qualifying child (derived)", "federal", "married filing separately, or head of household with a qualifying child (READINGS separated)"),
    ("person", "is_snap_abawd_discretionary_exempt"): NONE,
    ("person", "long_term_capital_gains_on_collectibles"): ("", "e24518", "", "federal", "a 28% rate gain inside long-term gains; TAXSIM has no input for it"),
    ("person", "meets_ssi_disability_criteria"): ("", "", "", "none", "SSI and other programs only; nearest concept: demographics/person#disabled"),
    ("person", "partnership_income"): ("", "e02000 and e26270", "scorp", "federal", "policyengine-us 2.60.0's name for the board's partnership_s_corp_income"),
    ("person", "partnership_self_employment_net_earnings"): ("", "k1bx14p/s", "psemp/ssemp, taken out of scorp", "federal", "policyengine-us 2.60.0's name for the board's partnership_se_income; a loss there does not offset pprofinc in TAXSIM (probe D4)"),
    ("person", "pre_subsidy_care_expenses"): (A + "tax/household#childcare_expenses", "e32800 with f2441, for a qualifying individual", "childcare", "federal", "care of the person who states them; the concept is household-level"),
    ("person", "schedule_d_capital_gain_distributions"): ("", "", "", "none", "a memo item already inside long-term gains (MEMO_INPUTS)"),
    ("person", "self_employed_pension_contributions_desired"): ("", "e03300 (the map applies 415(c) and the Schedule C limit)", "nonprop, negative", "federal", "also an IRA active-participant trigger and a saver's credit contribution (READINGS se_pension)"),
    ("person", "sstb_w2_wages_from_qualified_business"): ("", "PT_binc_w2_wages (the kind of business PT_SSTB_income selects)", "", "federal", "limits the qualified business income deduction above the threshold only; TAXSIM applies no such limit"),
    ("person", "taxable_sep_distributions"): (A + "income/person#pension_income", "e01400, with IRA distributions", "pensions", "federal", "the concept is pension income of any kind"),
    ("person", "w2_wages_from_qualified_business"): ("", "PT_binc_w2_wages (the kind of business PT_SSTB_income selects)", "", "federal", "limits the qualified business income deduction above the threshold only; TAXSIM applies no such limit"),
    ("tax_unit", "selected_marketplace_plan_benchmark_ratio"): ("", "", "", "none", "reaches the premium tax credit only, which is not one of the four lines"),
    ("tax_unit", "unrecaptured_section_1250_gain"): ("", "e24515", "", "federal", "a 25% rate gain inside long-term gains; TAXSIM has no input for it"),
}


# Board rows whose note speaks of the board only, restated for the draw.
DRAW_OVERRIDES = {
    ("person", "is_surviving_spouse"): ("", "MARS 5 when a qualifying child is claimed", "", "federal", "TAXSIM has no such status (READINGS surviving_spouse)"),
    ("person", "farm_income"): ("", "", "", "none", "the engine does not read it (READINGS farm_income); one draw member states an amount different from farm_operations_income"),
}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--draw", action="store_true",
                        help="the draw's stated inputs: board rows the draw states, plus DRAW_FACTS")
    args = parser.parse_args(argv)

    stated = Counter()
    households = H.load(args.scenarios)
    for household in households:
        seen = set()
        for person in H.people(household):
            seen.update(("person", key) for key in person["inputs"])
        for entity in ("tax_unit", "spm_unit", "household"):
            seen.update((entity, key) for key in household[f"{entity}_inputs"])
        stated.update(seen)
    always = lambda k: k[0] == "structure" or k == ("person", "employment_income")  # noqa: E731
    if args.draw:
        # Board rows the draw does not state drop out; every draw-only row must be stated.
        facts = {k: DRAW_OVERRIDES.get(k, v) for k, v in FACTS.items() if always(k) or k in stated}
        facts.update(DRAW_FACTS)
        check = DRAW_FACTS
    else:
        facts = check = FACTS
    missing = sorted(set(stated) - set(facts))
    if missing:
        raise SystemExit(f"stated inputs with no row: {missing}")
    unused = sorted(k for k in check if not always(k) and k not in stated)
    if unused:
        raise SystemExit(f"rows for inputs no household states: {unused}")

    rows = []
    for (entity, name), (concept, taxcalc, taxsim, effect, note) in facts.items():
        rows.append({
            "entity": entity, "fact": name,
            "households_stating_it": stated.get((entity, name), len(households) if always((entity, name)) else 0),
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
