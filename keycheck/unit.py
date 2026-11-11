"""Turn a PolicyBench household into the facts of one federal return, from stated facts only.

The board states people (Head, Spouse, Dependent N, Child N) and their amounts. A tax
model needs a return: who files, in what status, who is a dependent, and each line's
amount. This module derives that once, so the Tax-Calculator and TAXSIM maps start from
the same return. It reads nothing PolicyEngine computed.

Readings of facts the board does not state are named in READINGS and attached to every
unit they touch (Unit.notes, or Unit.itemized_notes for readings that can move an answer
only when the model itemizes), so a disagreement that comes from a reading can be told
from one that comes from a calculation. The rule for a fact the board does not state is
the board's own, as its prompt gives it to every model: a stated fact means what it says,
an unlisted amount is 0 and an unlisted status is false
(policybench/prompts.py:14-27 at c7ede86c).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import households as H
from . import statute as S

VERSION = "2026-11-11.1"

# 26 U.S.C. 152(d)(1)(B): a qualifying relative's gross income must be under the
# exemption amount (Rev. Proc. 2025-32 sec. 4.23: $5,300 for 2026; Rev. Proc. 2024-40
# sec. 2.24: $5,200 for 2025).
QUALIFYING_RELATIVE_INCOME_LIMIT = {2026: 5_300, 2025: 5_200}

# One fact under the names of two policyengine-us releases. The board's households state
# the old names; households built on policyengine-us 2.60.0 (the larger draw) state the
# new ones: partnership_s_corp_income there only adds partnership_income and
# s_corp_income (variables/household/income/person/self_employment/
# partnership_s_corp_income.py), and the board's builder renames partnership_se_income
# to partnership_self_employment_net_earnings (policybench/scenarios.py:161-163 at
# c7ede86c). A PolicyEngine run gives the same answers under either name (the lead's
# experiment E6, results/repro/draw_experiments_pe_2.60.0.txt).
PARTNERSHIP_INCOME_NAMES = ("partnership_s_corp_income", "partnership_income", "s_corp_income")
PARTNERSHIP_SE_NAMES = ("partnership_se_income", "partnership_self_employment_net_earnings")

# 26 U.S.C. 21(d)(2): a spouse incapable of self-care is deemed to earn $250 a month
# ($500 with two or more qualifying individuals).
DEEMED_MONTHLY_EARNINGS = {1: 250, 2: 500}

READINGS = {
    "dependents": (
        "A listed member other than the head and spouse is a dependent when the stated "
        "facts can meet 26 U.S.C. 152: a qualifying child when under 19 at year end, or at "
        "any age under the is_disabled reading (152(c)(3)); otherwise a qualifying relative "
        "when own gross income is under the exemption amount (152(d)(1)(B)). Relationship, "
        "residence and support are taken as met, as the board's 'one household group' says. "
        "No one is a full-time student (152(c)(3)(A)(ii), 152(f)(2)): the board states no "
        "full-time status, and its American opportunity enrollment flags (at least half "
        "time) are not read as full time."
    ),
    "is_disabled": (
        "A listed member other than the head and spouse whom the board states 'is disabled' "
        "and who has no earnings of their own (wages and self-employment earnings both zero) "
        "is taken as permanently and totally disabled (26 U.S.C. 22(e)(3)), so meets the "
        "qualifying-child age test at any age (152(c)(3)(B)): a dependent for the $500 credit "
        "(24(h)(4)) and an EITC qualifying child (32(c)(3)). A disabled member with earnings "
        "of their own is not: 22(e)(3) requires inability to engage in substantial gainful "
        "activity, and the board does not say the impairment is total or lasting. "
        "Unit.disabled_reading lists the members this reading moves and the class each "
        "would have without it."
    ),
    "disability_benefits": (
        "Employment disability benefits are taxable in full and are not earned income. "
        "policyengine-us documents the stated amount as including the taxable and the "
        "tax-exempt part without stating the split (disability_benefits), and an unlisted "
        "amount is 0, so the tax-exempt part (26 U.S.C. 104(a)(3): coverage the employee "
        "paid for with after-tax money) is 0 and 105(a) includes the rest. The plan's "
        "minimum retirement age is an unlisted number, so the filer has reached it: the "
        "payments are a pension, not earned income (Pub. 596 counts disability retirement "
        "payments as earned income only before that age). Alternatives: earned income "
        "before the minimum retirement age (the EITC of a filer under 65), or excluded "
        "under 104(a)(3) because who paid for the coverage is not stated."
    ),
    "survivor_benefits": (
        "Survivor benefits other than Social Security are taxable in full: they are gross "
        "income (26 U.S.C. 61(a); 72 for a survivor annuity), the investment in the "
        "contract is an unlisted amount (0), and each exclusion (101(a) life insurance, "
        "104(a)(1) workers' compensation, 38 U.S.C. 5301 veterans' benefits) needs a fact "
        "the board does not state. They are not earned income, and not a distribution from "
        "a qualified plan for the saver's credit or 72(t) (the plan is not stated). "
        "Tax-Calculator gets them as taxable pensions (e01500 and e01700), TAXSIM in "
        "`pensions`. policyengine-us leaves them out of gross income."
    ),
    "salt_refund_income": (
        "A stated state or local tax refund is taxable in full: policyengine-us documents "
        "salt_refund_income as the taxable refund reported on Schedule 1, line 1 (26 U.S.C. "
        "111). Alternative: the prior-year deduction's tax benefit (111(a)) is not stated, "
        "which would make none of it taxable."
    ),
    "alimony": (
        "Alimony follows each model's only or default treatment: the divorce date is not "
        "stated. Tax-Calculator and TAXSIM treat it as a post-2018 instrument (not income, "
        "not deductible); PolicyEngine's default divorce year makes it pre-2019."
    ),
    "tips": (
        "Stated tip income is not qualified tips (26 U.S.C. 224): the occupation is not "
        "stated, and an unstated status is false. The tips stay inside the stated wages; "
        "Tax-Calculator's tip_income is 0."
    ),
    "auto_loan_interest": "Stated auto loan interest is not qualified passenger vehicle loan interest: the loan's date and the vehicle's qualification are not stated.",
    "rental_qbi": (
        "Rent and farm rent are qualified business income only when the person states the "
        "unadjusted basis of qualified property (not the SSTB basis) and no other trade or "
        "business (self-employment, farm operations, partnership or S corporation income): "
        "qualified property is by definition held by a qualified trade or business "
        "(26 U.S.C. 199A(b)(6)(A)), and when the person's only stated activities that could "
        "hold it are rentals, the rentals are that business. Otherwise whether a rental is a "
        "section 162 trade or business (199A(d)(1); Treas. Reg. 1.199A-1(b)(14); the 250 "
        "hours of Rev. Proc. 2019-38) is not stated, so it is not. Estate income is not "
        "qualified business income. Tax-Calculator gets a qualified rental in e27200 (with "
        "e02000) and any other rental in e02000 only; TAXSIM gets a qualified rental in "
        "`scorp` and any other rental and estate income in `intrec`. Alternatives: no rental "
        "is qualified (the basis left without effect), or every rental is (policyengine-us's "
        "default: rental_income_would_be_qualified and farm_rent_income_would_be_qualified "
        "default to true)."
    ),
    "partnership_qbi": (
        "Partnership and S corporation income is qualified business income: the Schedule E "
        "line for it carries the entities' business income (Schedule K-1 box 1, ordinary "
        "business income), as policyengine-us's default reads it "
        "(partnership_s_corp_income_would_be_qualified defaults to true)."
    ),
    "passive_activity": (
        "A stated fact says that the person works in an activity only for self-employment "
        "income (Schedule C, SSTB included) and farm operations income (Schedule F): income "
        "from the person's own work in their own business, which with no other individual's "
        "work stated is material participation (26 U.S.C. 469(h)(1); Temp. Reg. "
        "1.469-5T(a)(2)) and makes personal services a material income-producing factor "
        "(401(c)(2)(A)(i)). Partnership and S corporation income, rent and farm rent state "
        "ownership, not work: those activities are passive (469(c)(1)-(2)), with no real "
        "estate professional status (469(c)(7)) and no active participation, so no $25,000 "
        "offset (469(i)). Estate income as stated is the nonpassive part (policyengine-us "
        "states the passive part separately). Per return, a net passive loss is disallowed "
        "and carries forward to the next year (469(a)-(b)); each loss activity keeps a "
        "ratable share of the passive income (Temp. Reg. 1.469-1T(f)(2)(i)); a disallowed "
        "loss also leaves net earnings from self-employment (1.469-1T(d)(3)). No household "
        "states a loss carried in from an earlier year. A partner's self-employment "
        "earnings are not earned income under 401(c)(2) (the partner's services are not "
        "stated). Passive income other than self-employment earnings is net investment "
        "income (1411(c)(2)(A), (c)(6)); the 2026 minimum qualified business income "
        "deduction counts only Schedule C and F income (199A(i)(2)(B)). Alternatives: no "
        "activity materially participated (Schedule C and F losses suspended too, and no "
        "401(c)(2) earned income from them), or every owner the only participant (only "
        "rentals passive). policyengine-us applies no 469 limit."
    ),
    "retirement_penalty": (
        "The additional tax on early distributions (26 U.S.C. 72(t)(1)) is 10% of a filer's "
        "taxable IRA, SEP, 401(k) and 403(b) distributions (qualified plans by their names, "
        "4974(c)) when the filer is 59 or younger (a stated age of 59 does not state 59 1/2), "
        "less the medical exception (72(t)(2)(B): distributions up to medical expenses above "
        "7.5% of AGI), and none for a filer disabled under 72(m)(7) (the is_disabled reading: "
        "stated disabled with no earnings of their own). Every other exception (separation "
        "from service after 55, equal periodic payments, first home, education, birth or "
        "adoption, and so on) needs an unstated fact, so none applies. A private pension is "
        "not taxed: whether the plan is a qualified plan (4974(c)) or an annuity contract "
        "(72(q)) is not stated. Tax-Calculator takes the tax as e09900; TAXSIM has no input "
        "for it. policyengine-us takes it as an input with no formula "
        "(qualified_retirement_penalty), so the key holds none; its line "
        "income_tax_before_refundable_credits adds it when stated."
    ),
    "medicare_part_b": "Medical expenses are the stated amounts; no Medicare Part B premium is added, since none is stated.",
    "other_health_insurance_premiums": (
        "Stated other health insurance premiums are not counted again: policyengine-us "
        "documents them as part of the stated premiums without Medicare Part B "
        "(variables/household/expense/health/other_health_insurance_premiums.py), so "
        "counting both would double count. Medical expenses take the premiums without "
        "Medicare Part B."
    ),
    "over_the_counter": (
        "Over-the-counter health expenses are left out of medical expenses: the stated "
        "amount is not said to be prescribed medicine or insulin (26 U.S.C. 213(b)) or other "
        "medical care (213(d)(1))."
    ),
    "educational_assistance": (
        "Stated educational assistance (scholarships, grants and other assistance) is "
        "taxable in full: 26 U.S.C. 117(a) excludes a qualified scholarship only for a "
        "degree candidate and only as far as it pays tuition and required fees, books and "
        "equipment (117(b)); neither is stated, and 127 needs an employer's program, also "
        "not stated. It is not earned income for the EITC (it is not pay for services). "
        "No filer on the board or the draw is a dependent, so the dependent's standard "
        "deduction (63(c)(5)) and the kiddie tax (1(g)) do not arise; a member's amount "
        "counts in the member's gross income (152(d)(1)(B)). Tax-Calculator gets it in "
        "e01200 (AGI only), TAXSIM in `pensions` (`nonprop` would count as EITC earned "
        "income). policyengine-us leaves it out of gross income."
    ),
    "financial_assistance": "Stated financial assistance from friends or relatives outside the household is a gift, not gross income (26 U.S.C. 102(a)).",
    "qualified_bdc_income": (
        "Stated qualified BDC income is not extra income: it is read as part of the stated "
        "dividends, which the board does not say. policyengine-us 2.60.0 reads it in no "
        "formula."
    ),
    "farm_income": "Stated farm income repeats farm_operations_income (equal wherever the board states both) and is not added.",
    "partnership_se": "Stated partnership self-employment earnings (K-1 box 14) sit inside the stated partnership income: they are self-employment earnings, not more income.",
    "overtime_premium": "The stated FLSA overtime premium sits inside the stated wages; it is not added to them.",
    "mortgage_date": "Every mortgage is acquisition debt incurred after 2017-12-15 (26 U.S.C. 163(h)(3)(F)(i)(II)): the loan dates are not stated.",
    "active_participant": (
        "A filer with a 401(k) deferral (traditional or Roth) is an active participant in an "
        "employer plan for the IRA deduction limit (26 U.S.C. 219(g)(5)); a filer with none "
        "is not, since no other plan coverage is stated."
    ),
    "deferrals_wages": "401(k) deferrals, traditional and Roth together, are limited to the filer's own wages: a deferral comes out of pay, and no self-employed plan is stated.",
    "savers_credit": (
        "The saver's credit testing period is the tax year only: distributions in the two "
        "prior years and in the next year before the return's due date (26 U.S.C. "
        "25B(d)(2)(B)) are not stated and are taken as zero. Distributions that reduce "
        "contributions are those from plans 25B(d)(2)(A) names by their own names: IRAs "
        "(SEP included), 401(k) and 403(b) plans, taxable or not. A private pension does "
        "not count: whether its plan is a qualified plan (4974(c)) is not stated. A filer "
        "is not a full-time student (25B(c)(2)(B)) unless stated; the American opportunity "
        "enrollment flags (at least half time) are not read as full time."
    ),
    "educator": "A stated educator expense is an eligible educator's (26 U.S.C. 62(d)(1)): hours worked in a school are not stated.",
    "hsa": (
        "The stated health savings account deduction is allowed up to the 26 U.S.C. 223(b) "
        "limit of one eligible individual, the head, with self-only coverage for the whole "
        "year (Rev. Proc. 2025-19: 4,400 for 2026; Rev. Proc. 2024-25: 4,300 for 2025), plus "
        "$1,000 when the head is 55 or older (223(b)(3)). The stated deduction states that "
        "the unit has an eligible individual; family coverage, a second eligible spouse and "
        "Medicare enrollment are not stated (the board's rule: do not infer coverage). "
        "Alternatives: family coverage (8,750 for 2026), or each spouse an eligible "
        "individual. policyengine-us takes the stated deduction as given."
    ),
    "charity": (
        "Stated charitable gifts go to public charities (170(b)(1)(A) organizations): a "
        "private foundation is not stated. Non-cash gifts are ordinary-income property, "
        "deductible at the stated amount up to 50% of the contribution base less the cash "
        "allowed (170(b)(1)(A), (G)(iii)): no appreciation is stated, so none is capital "
        "gain property (170(b)(1)(C)). Cash counts up to 60% (170(b)(1)(G)); from 2026 only "
        "the total above 0.5% of the contribution base counts (170(b)(1)(I)). The excess "
        "over a ceiling carries forward five years; none is stated as carried in. "
        "Tax-Calculator applies its own ceilings (30% for non-cash gifts, 60% in all, after "
        "the floor); a note names a difference."
    ),
    "self_employed_health_insurance": (
        "A filer with Schedule C or Schedule F earnings who states person-paid health "
        "insurance premiums deducts them under 26 U.S.C. 162(l): the Form 7206 instructions "
        "let a self-employed person filing Schedule C or F hold the policy in the business's "
        "name or the person's own (sources/irs/i7206.txt:59-63), so no other fact about the "
        "plan is needed, and is_self_employed is not required. See se_health_insurance for "
        "the limit."
    ),
    "roth_catch_up": "Catch-up deferrals are not moved to Roth under 26 U.S.C. 414(v)(7) (from 2026): prior-year FICA wages are not stated.",
    "surviving_spouse": (
        "'Is a surviving spouse' is read as meeting 26 U.S.C. 2(a)(1)(A) (the spouse died in "
        "one of the two preceding years), and a claimed dependent other than an unmarried "
        "partner as the taxpayer's son or daughter (2(a)(1)(B))."
    ),
    "member_expenses": (
        "A listed member's own real estate taxes, mortgage interest and gifts are not "
        "expenses of the head's return; medical expenses of every listed member count, "
        "including one left out only by the gross-income test (26 U.S.C. 213(a) disregards "
        "152(d)(1)(B))."
    ),
    "desired_contributions": "Stated 'desired' retirement contributions above a statutory limit are scaled down in proportion, as the board's key does.",
    # Readings for inputs the larger draw states and the board does not.
    "member_deductions": (
        "A listed member's own investment interest and self-employed pension contributions "
        "are not deductions of the head's return: they belong to the member's own return, "
        "which is outside the board's output."
    ),
    "se_health_insurance": (
        "A filer with Schedule C or Schedule F earnings deducts the person-paid premiums "
        "medical expenses count for the filer (health_insurance_premiums where stated, else "
        "the premiums without Medicare Part B) under 26 U.S.C. 162(l), up to the earned "
        "income of 401(c)(2) from the business under which the plan is taken as "
        "established, the one with the larger earned income: that business's income less "
        "its share of the deduction for half the self-employment tax (164(f)) among the "
        "filer's positive self-employment sources, and for Schedule C less the "
        "self-employed pension deduction. A stated has_esi of the filer or spouse is "
        "eligibility for an employer's subsidized plan and bars the deduction "
        "(162(l)(2)(B)); otherwise none is stated. Premiums deducted here leave medical "
        "expenses (162(l)(3)). policyengine-us deducts only health_insurance_premiums of a "
        "filer stated is_self_employed (self_employed_health_insurance_premiums.py: "
        "defined_for is_self_employed), up to self-employment income before those two "
        "reductions."
    ),
    "negative_miscellaneous": (
        "A negative miscellaneous income enters as 0: gross income items (26 U.S.C. 61; "
        "Treas. Reg. 1.61-14) are not negative, and a loss is deductible only under a "
        "provision whose facts are stated (165(c): a trade or business, or a transaction "
        "entered into for profit), which here they are not. policyengine-us adds sources "
        "of gross income only when positive (irs_gross_income.py)."
    ),
    "alaska_dividend": (
        "No Alaska Permanent Fund Dividend is added: the household does not state it, and "
        "the board says not to infer unlisted income. policyengine-us 2.60.0 adds a modeled "
        "dividend of $1,000 a person for 2025 and 2026 to the federal gross income of an "
        "Alaska household (parameters/gov/irs/gross_income/sources.yaml:41; "
        "parameters/gov/states/ak/dor/permanent_fund_dividend.yaml:6-7)."
    ),
    "health_insurance_premiums": (
        "Stated health insurance premiums (health_insurance_premiums) and premiums without "
        "Medicare Part B are one amount stated two ways: policyengine-us documents the "
        "first as an alternative to the decomposed inputs, not an additional expense "
        "(variables/household/expense/health/health_insurance_premiums.py), and uses it in "
        "their place where it is not zero. Medical expenses do the same."
    ),
    "se_pension": (
        "Stated self-employed pension contributions are taken up to the lesser of the "
        "26 U.S.C. 415(c)(1)(A) limit and the filer's Schedule C income, as the board's key "
        "does: the plan type (SEP, SIMPLE IRA or solo 401(k)) is not stated, and the "
        "deduction limit of 404 depends on it (for a SEP, 25% of compensation). The amount "
        "is an adjustment to income (62(a)(6)), makes the filer an active participant "
        "(219(g)(5)), counts as a saver's credit contribution, and reduces the filer's "
        "compensation for the IRA limit (219(f)(1), 401(c)(2))."
    ),
    "investment_interest": (
        "Stated investment interest expense is investment interest (26 U.S.C. 163(d)(3)), "
        "deductible by an itemizer up to net investment income (163(d)(1)): taxable "
        "interest, non-qualified dividends, net short-term gain and the elected qualified "
        "dividends and net capital gain (163(d)(4)(B)). Rent, estate, partnership and "
        "retirement income are not counted (their source is not stated); investment "
        "expenses (163(d)(4)(C)) and a carryforward from earlier years (163(d)(2)) are "
        "not stated and are taken as zero. A Form 4952 election above the qualified "
        "dividends and net capital gain is limited to them."
    ),
    "incapable": (
        "A person stated incapable of self-care lives in the home for more than half the "
        "year and spends at least 8 hours a day there (26 U.S.C. 21(b)(1)(B)-(C), "
        "(b)(2)(B)): a qualifying individual for the child and dependent care credit as "
        "the filers' spouse or dependent, including a member who is not claimed only "
        "because of the gross-income test (21(b)(1)(B) disregards 152(d)(1)(B)). Stated "
        "care expenses (pre_subsidy_care_expenses) are for the care of the person who "
        "states them, and count only when that person is a qualifying individual (a note "
        "names any that do not: policyengine-us adds every member's). On a joint return "
        "one incapable spouse counts, as policyengine-us counts (count_cdcc_eligible.py); a "
        "head stated incapable on a return without a spouse is not a qualifying "
        "individual. A spouse whose stated earnings fall short of the earned income "
        "21(d)(2) deems ($250 a month, $500 with two or more qualifying individuals) gets "
        "a note on each model that has no such rule."
    ),
    "separated": (
        "A head stated to be separated is married and living apart, with no decree of "
        "separate maintenance stated: 26 U.S.C. 7703(b) treats the head as unmarried only "
        "with a qualifying child in the home (its other conditions taken as met), so the "
        "head files as head of household; otherwise married filing separately. The absent "
        "spouse's income and itemizing are not stated and are taken as none."
    ),
    "unrelated_member": (
        "A member stated not related to the head or spouse is treated as policyengine-us "
        "treats them: a qualifying child when the age test is met, although 26 U.S.C. "
        "152(c)(2) requires a relationship (or an eligible foster child placed by an "
        "authorized agency) and neither is stated; and not a head of household or "
        "surviving spouse qualifying person when only a qualifying relative "
        "(2(b)(3)(B)(i), 2(a)(1)(B))."
    ),
}

# Stated inputs that reach none of the four federal lines in policyengine-us 2.60.0 (or
# that the board's builder drops), so this module does not read them. A household that
# states an input in none of READ_INPUTS, NON_TAX_INPUTS and MEMO_INPUTS fails
# unread_inputs(): the next rename cannot pass unseen. The reasons are in
# maps/board_facts.csv and maps/draw_facts.csv.
NON_TAX_INPUTS = frozenset({
    # Education-credit, coverage, asset, benefit and work facts.
    "attends_eligible_educational_institution_for_american_opportunity_credit",
    "has_american_opportunity_credit_1098_t_or_exception",
    "has_american_opportunity_credit_institution_ein",
    "is_enrolled_at_least_half_time_for_american_opportunity_credit",
    "is_pursuing_credential_for_american_opportunity_credit",
    "bank_account_assets", "stock_assets", "bond_assets",
    "child_support_expense", "child_support_received",
    "employer_sponsored_insurance_premiums", "has_esi",
    "has_champva_health_coverage_at_interview", "has_indian_health_service_coverage_at_interview",
    "has_other_means_tested_health_coverage_at_interview",
    "hourly_wage", "hours_worked_last_week", "is_paid_hourly", "weeks_unemployed",
    "is_pregnant", "pre_subsidy_rent", "receives_wic",
    "veterans_benefits", "workers_compensation",   # indirect only: the sales tax table's income
    "auto_loan_balance", "household_vehicles_value",
    "receives_housing_assistance", "spm_unit_energy_subsidy",
    "first_home_mortgage_interest", "second_home_mortgage_interest",  # dropped by the board's builder
    # Draw-only: SNAP, SSI, Medicaid, marketplace and military facts (draw-inputs F3, F14).
    "is_military", "meets_ssi_disability_criteria", "is_snap_abawd_discretionary_exempt",
    "selected_marketplace_plan_benchmark_ratio",
    # Roles: the household's structure, read through its names.
    "is_tax_unit_head", "is_tax_unit_spouse",
})
# Memo items: parts of another stated amount, never added to it.
MEMO_INPUTS = frozenset({
    # Inside long_term_capital_gains (policyengine-us documents it as a memo component).
    "schedule_d_capital_gain_distributions",
})
READ_INPUTS = frozenset({
    "employment_income", "age",
    "traditional_401k_contributions_desired", "roth_401k_contributions_desired",
    "traditional_ira_contributions_desired", "roth_ira_contributions_desired",
    "self_employment_income", "sstb_self_employment_income_before_lsr",
    "farm_operations_income", "farm_income", "farm_rent_income", "rental_income",
    *PARTNERSHIP_INCOME_NAMES, *PARTNERSHIP_SE_NAMES,
    "taxable_interest_income", "tax_exempt_interest_income",
    "qualified_dividend_income", "non_qualified_dividend_income", "qualified_bdc_income",
    "short_term_capital_gains", "long_term_capital_gains", "non_sch_d_capital_gains",
    "long_term_capital_gains_on_collectibles", "unrecaptured_section_1250_gain",
    "investment_income_elected_form_4952", "investment_interest_expense",
    "taxable_ira_distributions", "tax_exempt_ira_distributions",
    "taxable_sep_distributions", "tax_exempt_sep_distributions",
    "taxable_401k_distributions", "taxable_403b_distributions",
    "taxable_private_pension_income", "tax_exempt_private_pension_income",
    "social_security_retirement", "social_security_disability",
    "social_security_survivors", "social_security_dependents",
    "unemployment_compensation", "miscellaneous_income", "salt_refund_income",
    "disability_benefits", "survivor_benefits", "estate_income",
    "alimony_income", "alimony_expense", "educational_assistance", "financial_assistance",
    "tip_income", "fsla_overtime_premium", "educator_expense", "student_loan_interest",
    "unreimbursed_business_employee_expenses",
    "health_insurance_premiums_without_medicare_part_b", "other_health_insurance_premiums",
    "health_insurance_premiums", "is_self_employed", "other_medical_expenses",
    "over_the_counter_health_expenses",
    "self_employed_pension_contributions_desired",
    "real_estate_taxes", "home_mortgage_interest", "first_home_mortgage_balance",
    "second_home_mortgage_balance", "charitable_cash_donations", "charitable_non_cash_donations",
    "health_savings_account_ald", "domestic_production_ald",
    "spm_unit_pre_subsidy_childcare_expenses", "pre_subsidy_care_expenses",
    "is_incapable_of_self_care",
    "auto_loan_interest", "qualified_passenger_vehicle_loan_interest",
    "unadjusted_basis_qualified_property", "sstb_unadjusted_basis_qualified_property",
    "w2_wages_from_qualified_business", "sstb_w2_wages_from_qualified_business",
    "qualified_reit_and_ptp_income",
    "is_blind", "is_disabled", "is_surviving_spouse", "is_separated",
    "is_unmarried_partner_of_household_head", "is_related_to_head_or_spouse",
})


def unread_inputs(household: dict) -> list[tuple[str, str]]:
    """Stated inputs (entity, name) in none of READ_INPUTS, NON_TAX_INPUTS and MEMO_INPUTS."""
    known = READ_INPUTS | NON_TAX_INPUTS | MEMO_INPUTS
    stated = set()
    for person in H.people(household):
        stated.update(("person", key) for key in person.get("inputs", {}))
    for entity in ("tax_unit", "spm_unit", "household"):
        stated.update((entity, key) for key in household.get(f"{entity}_inputs", {}))
    return sorted(item for item in stated if item[1] not in known)


def partnership_income(person: dict | None) -> float:
    """Partnership and S corporation income under either release's names."""
    return sum(H.amount(person, key) for key in PARTNERSHIP_INCOME_NAMES)


def partnership_se(person: dict | None) -> float:
    """A partner's self-employment earnings (K-1 box 14) under either release's names."""
    return sum(H.amount(person, key) for key in PARTNERSHIP_SE_NAMES)


def _check_names(person: dict) -> None:
    """A person may not state one fact under both releases' names (the board's builder
    raises in the same case: policybench/scenarios.py:562-566 at c7ede86c)."""
    inputs = person.get("inputs", {})
    if "partnership_s_corp_income" in inputs and ("partnership_income" in inputs or "s_corp_income" in inputs):
        raise ValueError(f"{person['name']} states partnership_s_corp_income and one of its parts")
    if all(name in inputs for name in PARTNERSHIP_SE_NAMES):
        raise ValueError(f"{person['name']} states partnership_se_income under both names")

# A member's own income items that count as gross income for the qualifying-relative test.
_GROSS_INCOME_ITEMS = (
    "taxable_interest_income", "qualified_dividend_income",
    "non_qualified_dividend_income", "taxable_private_pension_income",
    "taxable_ira_distributions", "taxable_401k_distributions", "taxable_403b_distributions",
    "unemployment_compensation", "miscellaneous_income", "salt_refund_income",
    "disability_benefits", "estate_income", "taxable_sep_distributions",
    # Taxable in full (READINGS["educational_assistance"], READINGS["survivor_benefits"]).
    "educational_assistance", "survivor_benefits",
)
_GROSS_INCOME_NET_ITEMS = (  # counted when positive: the board states net amounts only
    "self_employment_income", "sstb_self_employment_income_before_lsr",
    "farm_operations_income", "rental_income", "farm_rent_income",
)
# Partnership income counts once, as one net amount, under whichever names are stated.
_GAINS = ("short_term_capital_gains", "long_term_capital_gains", "non_sch_d_capital_gains")
_SOCIAL_SECURITY = (
    "social_security_retirement", "social_security_disability",
    "social_security_survivors", "social_security_dependents",
)
_SELF_EMPLOYMENT = (
    "self_employment_income", "sstb_self_employment_income_before_lsr",
    "farm_operations_income", "partnership_se_income", "partnership_self_employment_net_earnings",
)
# Every stated income item of a member, for the note that it is not the head's income
# (each name once, in order: _SELF_EMPLOYMENT and _GROSS_INCOME_NET_ITEMS share names).
_MEMBER_INCOME_KEYS = tuple(dict.fromkeys(
    ("employment_income",) + _SELF_EMPLOYMENT + _GROSS_INCOME_ITEMS + _GROSS_INCOME_NET_ITEMS
    + PARTNERSHIP_INCOME_NAMES + _GAINS + _SOCIAL_SECURITY
    + ("tax_exempt_interest_income", "tax_exempt_ira_distributions",
       "tax_exempt_private_pension_income", "survivor_benefits", "alimony_income")
))
# Retirement distributions, taxable or not, for the saver's credit testing period: plans
# 26 U.S.C. 25B(d)(2)(A) names, by their own names (READINGS["savers_credit"]; a private
# pension's plan is not stated).
_DISTRIBUTIONS = (
    "taxable_ira_distributions", "tax_exempt_ira_distributions",
    "taxable_401k_distributions", "taxable_403b_distributions",
    "taxable_sep_distributions", "tax_exempt_sep_distributions",
)
_PRIVATE_PENSIONS = ("taxable_private_pension_income", "tax_exempt_private_pension_income")
# Taxable distributions from qualified retirement plans (26 U.S.C. 4974(c)) by their names,
# for the additional tax of 72(t) (READINGS["retirement_penalty"]).
_EARLY_DISTRIBUTIONS = (
    "taxable_ira_distributions", "taxable_sep_distributions",
    "taxable_401k_distributions", "taxable_403b_distributions",
)
# Activities a stated fact says the person works in (READINGS["passive_activity"]); every
# other stated trade, business or rental is passive.
_ACTIVE_BUSINESS = ("self_employment_income", "sstb_self_employment_income_before_lsr", "farm_operations_income")
# Readings a member's gross-income test can turn on.
_INCOME_TEST_READINGS = {
    "disability_benefits": "disability_benefits",
    "salt_refund_income": "salt_refund_income",
    "survivor_benefits": "survivor_benefits",
    "educational_assistance": "educational_assistance",
    "financial_assistance": "financial_assistance",
}


def taxable_social_security_unmarried(benefits: float, other_income: float, tax_exempt_interest: float) -> float:
    """26 U.S.C. 86(a)-(c) for an unmarried filer: base amount $25,000, adjusted base $34,000.

    `other_income` is adjusted gross income without the benefits (86(b)(2)(A)); the
    tax-exempt interest is added back (86(b)(2)(B)).
    """
    benefits = max(0.0, benefits)
    if benefits <= 0:
        return 0.0
    base, adjusted = 25_000.0, 34_000.0
    excess = other_income + tax_exempt_interest + 0.5 * benefits - base
    if excess <= 0:
        return 0.0
    first = min(0.5 * benefits, 0.5 * excess)
    over_adjusted = other_income + tax_exempt_interest + 0.5 * benefits - adjusted
    if over_adjusted <= 0:
        return first
    return min(0.85 * over_adjusted + min(first, 0.5 * (adjusted - base)), 0.85 * benefits)


def rentals_qualified(person: dict) -> bool:
    """READINGS["rental_qbi"]: a person's rent and farm rent are qualified business income
    when the person states the unadjusted basis of qualified property (26 U.S.C.
    199A(b)(6)) and no other activity that is a trade or business."""
    if not H.amount(person, "unadjusted_basis_qualified_property"):
        return False
    other_business = any(H.amount(person, key) for key in _ACTIVE_BUSINESS) or partnership_income(person) != 0
    return not other_business


def passive_activities(people: list[dict]) -> dict[str, dict[str, float]]:
    """26 U.S.C. 469 for one return (READINGS["passive_activity"]): each filer's passive
    activities (partnership or S corporation income, rent, farm rent; one net amount each),
    netted together; a net loss is disallowed and carried forward (statute.passive_activity_allowed).
    Returns, per filer name, the stated and allowed amount of each activity, and the
    allowed partner's self-employment earnings: a disallowed loss leaves them too
    (Temp. Reg. 1.469-1T(d)(3)), in the share the activity's loss is disallowed."""
    keys = ("partnership", "rental", "farm_rent")
    stated = []
    for person in people:
        stated.append({
            "partnership": partnership_income(person),
            "rental": H.amount(person, "rental_income"),
            "farm_rent": H.amount(person, "farm_rent_income"),
        })
    flat = [row[key] for row in stated for key in keys]
    allowed_flat = S.passive_activity_allowed(flat)
    out = {}
    for index, person in enumerate(people):
        row = {key: allowed_flat[index * len(keys) + k] for k, key in enumerate(keys)}
        se = partnership_se(person)
        share = row["partnership"] / stated[index]["partnership"] if stated[index]["partnership"] < 0 else 1.0
        row["partnership_se"] = se * share if se < 0 else se
        row.update({f"{key}_stated": stated[index][key] for key in keys})
        out[person["name"]] = row
    return out


def own_gross_income(person: dict, year: int) -> float:
    """A member's gross income for the qualifying-relative test of 26 U.S.C. 152(d)(1)(B).

    Gains count without losses (61(a)(3) counts gains; losses are deductions), wages count
    net of the member's own traditional 401(k) deferral (excluded from gross income), and
    Social Security counts in its taxable part (86), figured for an unmarried filer. The
    board states business and rental income net only, so a positive net amount stands
    for the gross.
    """
    deferral = _deferrals(person, year, [])[0]
    total = max(0.0, H.amount(person, "employment_income") - deferral)
    total += sum(max(0.0, H.amount(person, key)) for key in _GROSS_INCOME_ITEMS)
    total += sum(max(0.0, H.amount(person, key)) for key in _GROSS_INCOME_NET_ITEMS)
    total += max(0.0, partnership_income(person))
    total += sum(max(0.0, H.amount(person, key)) for key in _GAINS)
    benefits = sum(H.amount(person, key) for key in _SOCIAL_SECURITY)
    taxable = taxable_social_security_unmarried(
        benefits, total, H.amount(person, "tax_exempt_interest_income")
    )
    return total + taxable


def _premiums(person: dict) -> float:
    """A person's health insurance premiums for medical expenses: health_insurance_premiums
    where stated, else the premiums without Medicare Part B (READINGS
    ["health_insurance_premiums"]; policyengine-us medical_expense_health_insurance_premiums.py)."""
    direct = H.amount(person, "health_insurance_premiums")
    return direct if direct != 0 else H.amount(person, "health_insurance_premiums_without_medicare_part_b")


def own_earnings(person: dict) -> tuple[float, float]:
    """A person's stated wages and self-employment earnings (every self-employment source)."""
    return (
        H.amount(person, "employment_income"),
        sum(H.amount(person, key) for key in _SELF_EMPLOYMENT),
    )


@dataclass
class Filer:
    name: str
    age: int
    blind: bool
    wages: float                 # gross wages and salaries, tips and overtime included
    deferral: float              # traditional 401(k) deferral after the 402(g) limit and wages
    roth_deferral: float         # Roth 401(k) deferral after the 402(g) limit and wages
    ira_traditional_desired: float
    ira_roth_desired: float
    schedule_c: float            # self-employment income, SSTB included
    sstb: float                  # the SSTB part of schedule_c
    schedule_f: float            # farm operations
    partnership_se: float        # partner's self-employment earnings (K-1 box 14)
    educator_expense: float
    retirement_distributions: float   # IRA, SEP, 401(k) and 403(b) distributions, taxable or not (saver's credit)
    overtime_premium: float
    tips: float
    # Fields added after the first dossiers (zero or false where nothing states them).
    se_pension: float = 0.0          # self-employed pension contribution (READINGS["se_pension"])
    se_health_premiums: float = 0.0  # person-paid premiums of a filer with Schedule C or F earnings, no employer plan
    se_health: float = 0.0           # their 26 U.S.C. 162(l) deduction (READINGS["se_health_insurance"])
    se_health_key: float = 0.0       # the deduction under the key's limit (is_self_employed, Schedule C income)
    se_earned_income: float = 0.0    # 401(c)(2) earned income from the business the plan sits under
    incapable: bool = False          # stated incapable of self-care (26 U.S.C. 21(b)(1)(C))

    @property
    def self_employment(self) -> float:
        return self.schedule_c + self.schedule_f + self.partnership_se

    @property
    def active_participant(self) -> bool:
        # 26 U.S.C. 219(g)(5): a 401(k) deferral or a self-employed plan contribution.
        return self.deferral + self.roth_deferral + self.se_pension > 0


@dataclass
class Unit:
    case_id: str
    year: int
    state: str
    status: str
    head: Filer
    spouse: Filer | None
    dependents: list[dict]
    left_out: list[dict]            # listed members who meet neither dependency test
    amounts: dict[str, float]
    notes: list[tuple[str, str]] = field(default_factory=list)   # (group, text)
    members_with_own_payroll: list[dict] = field(default_factory=list)
    # Notes that can move an answer only when the model itemizes: a runner adds them to
    # its notes for the units its model itemizes in the final pass.
    itemized_notes: list[tuple[str, str]] = field(default_factory=list)
    # Members the is_disabled reading moves: name, age, the class under the reading and
    # the class without it ("qualifying_relative" or "left_out").
    disabled_reading: list[dict] = field(default_factory=list)
    # Qualifying individuals for the child and dependent care credit (26 U.S.C. 21(b)(1)):
    # name, age and why. On the board: the dependents under 13.
    care_individuals: list[dict] = field(default_factory=list)

    @property
    def filers(self) -> list[Filer]:
        return [self.head] + ([self.spouse] if self.spouse else [])

    def count(self, test) -> int:
        return sum(1 for d in self.dependents if test(d))


def _deferrals(person: dict, year: int, notes: list) -> tuple[float, float]:
    """(traditional, Roth) 401(k) deferrals after 26 U.S.C. 402(g) and the person's wages."""
    wages = max(0.0, H.amount(person, "employment_income"))
    traditional = H.amount(person, "traditional_401k_contributions_desired")
    roth = H.amount(person, "roth_401k_contributions_desired")
    age = int(person["age"])
    limit = S.elective_deferral_limit(year, age)
    scaled_traditional, scaled_roth = S.scale_to_limit([traditional, roth], limit)
    if traditional + roth > limit:
        notes.append(("income_tax", f"{person['name']}: desired 401(k) deferrals above the 402(g) limit, scaled in proportion ({READINGS['desired_contributions']})"))
    if scaled_traditional + scaled_roth > wages:
        notes.append(("income_tax", f"{person['name']}: 401(k) deferrals above wages, limited to wages in proportion (reading: {READINGS['deferrals_wages']})"))
        scaled_traditional, scaled_roth = S.scale_to_limit([scaled_traditional, scaled_roth], wages)
    if (year >= 2026 and age >= 50 and scaled_traditional > 0
            and scaled_traditional + scaled_roth > S.AMOUNTS[year]["deferral_limit"]):
        # Catch-up deferrals in use, part of them traditional.
        notes.append(("income_tax", f"reading: {person['name']} makes catch-up deferrals. " + READINGS["roth_catch_up"]))
    return scaled_traditional, scaled_roth


def _filer(person: dict, year: int, notes: list, passive: dict | None = None, employer_plan: bool = False) -> Filer:
    """One filer's facts. `passive` is the filer's row of passive_activities() (the
    allowed partner's self-employment earnings); `employer_plan` is a stated has_esi of
    the filer or the spouse (26 U.S.C. 162(l)(2)(B))."""
    _check_names(person)
    wages = H.amount(person, "employment_income")
    deferral, roth_deferral = _deferrals(person, year, notes)
    schedule_c = H.amount(person, "self_employment_income") + H.amount(
        person, "sstb_self_employment_income_before_lsr"
    )
    distributions = sum(max(0.0, H.amount(person, key)) for key in _DISTRIBUTIONS)
    partner_se = passive["partnership_se"] if passive is not None else partnership_se(person)
    schedule_f = H.amount(person, "farm_operations_income")
    se_pension = S.self_employed_pension_contribution(
        year, H.amount(person, "self_employed_pension_contributions_desired"), schedule_c
    )
    if se_pension:
        _reading(notes, "se_pension")
    # 26 U.S.C. 162(l): person-paid premiums of a filer with Schedule C or F earnings
    # (READINGS["self_employed_health_insurance"], READINGS["se_health_insurance"]).
    premiums = _premiums(person)
    business = schedule_c > 0 or schedule_f > 0
    se_premiums = premiums if business and premiums > 0 and not employer_plan else 0.0
    if business and premiums > 0 and employer_plan:
        notes.append(("income_tax", f"{person['name']}: Schedule C or F earnings and person-paid premiums, but a stated has_esi of the filer or spouse is eligibility for an employer's subsidized plan, which bars the 26 U.S.C. 162(l) deduction (162(l)(2)(B)); the premiums stay in medical expenses"))
    earned = 0.0
    se_health = 0.0
    # policyengine-us: only health_insurance_premiums of a filer stated is_self_employed,
    # up to Schedule C income (self_employed_health_insurance_premiums.py: defined_for
    # is_self_employed; self_employed_health_insurance_ald_person.py).
    key_premiums = H.amount(person, "health_insurance_premiums") if H.flag(person, "is_self_employed") else 0.0
    se_health_key = S.self_employed_health_insurance_deduction(key_premiums, schedule_c)
    if se_premiums > 0 or se_pension > 0:
        # Each business's share of the 164(f) deduction: half the self-employment tax on
        # all the filer's net earnings, shared in proportion to the positive sources.
        sources = [schedule_c, schedule_f, partner_se]
        half_se = 0.5 * S.self_employment_tax(year, sum(sources), wages)
        positive = sum(max(0.0, x) for x in sources)
        half_se_c = half_se * (max(0.0, schedule_c) / positive if positive > 0 else 0.0)
        half_se_f = half_se * (max(0.0, schedule_f) / positive if positive > 0 else 0.0)
        sep_limit = S.sep_deduction_limit(schedule_c, half_se_c)
        if se_pension > sep_limit:
            notes.append(("income_tax", f"{person['name']}: the self-employed pension contribution taken, {se_pension:,.0f}, exceeds what a SEP could deduct ({sep_limit:,.0f}: 26 U.S.C. 404(h)(1)(C) with 401(c)(2)); a solo 401(k)'s elective deferrals could cover the rest (404(n), within 402(g)); the plan type is not stated (reading: {READINGS['se_pension']})"))
        if se_premiums > 0:
            # 401(c)(2)(A)(v)-(vi): the business's income less its share of the 164(f)
            # deduction and, for Schedule C, less the self-employed pension deduction; the
            # plan sits under the business with the larger earned income.
            earned = max(schedule_c - half_se_c - se_pension, schedule_f - half_se_f)
            se_health = S.self_employed_health_insurance_deduction(se_premiums, earned)
            _reading(notes, "self_employed_health_insurance")
            _reading(notes, "se_health_insurance")
    if se_health_key != se_health:
        notes.append(("income_tax", f"{person['name']}: the self-employed health insurance deduction is {se_health:,.0f} under 26 U.S.C. 162(l) (earned income of 401(c)(2) from the business, {earned:,.0f}); policyengine-us allows {se_health_key:,.0f} (it deducts only health_insurance_premiums of a filer stated is_self_employed, up to Schedule C income)"))
    return Filer(
        name=person["name"],
        age=int(person["age"]),
        blind=H.flag(person, "is_blind"),
        wages=wages,
        deferral=deferral,
        roth_deferral=roth_deferral,
        ira_traditional_desired=H.amount(person, "traditional_ira_contributions_desired"),
        ira_roth_desired=H.amount(person, "roth_ira_contributions_desired"),
        schedule_c=schedule_c,
        sstb=H.amount(person, "sstb_self_employment_income_before_lsr"),
        schedule_f=schedule_f,
        partnership_se=partner_se,
        educator_expense=H.amount(person, "educator_expense"),
        retirement_distributions=distributions,
        overtime_premium=H.amount(person, "fsla_overtime_premium"),
        tips=H.amount(person, "tip_income"),
        se_pension=se_pension,
        se_health_premiums=se_premiums,
        se_health=se_health,
        se_health_key=se_health_key,
        se_earned_income=earned,
        incapable=H.flag(person, "is_incapable_of_self_care"),
    )


def deemed_earnings_short(unit: "Unit") -> list[tuple[str, float, float]]:
    """26 U.S.C. 21(d)(2) (sources/uscode/usc26-s21.txt:73-76): a spouse incapable of
    self-care is deemed to earn at least $250 a month ($500 with two or more qualifying
    individuals). For a joint unit with care expenses, each incapable spouse among the care
    individuals whose stated earnings fall short of the deemed amount: (name, stated
    earnings, deemed amount). A model without deemed income limits the credit by the
    stated earnings instead."""
    if unit.status != S.JOINT or not unit.amounts["child_care"]:
        return []
    monthly = DEEMED_MONTHLY_EARNINGS[1 if len(unit.care_individuals) == 1 else 2]
    out = []
    for filer in unit.filers:
        if any(c["name"] == filer.name and c["why"] == "spouse incapable of self-care" for c in unit.care_individuals):
            stated = max(0.0, filer.wages - filer.deferral) + max(0.0, filer.self_employment)
            if stated < 12 * monthly:
                out.append((filer.name, stated, 12.0 * monthly))
    return out


def _reading(notes: list, key: str, prefix: str = "") -> None:
    note = ("income_tax", "reading: " + prefix + READINGS[key])
    if note not in notes:
        notes.append(note)


def build(household: dict, year: int) -> Unit:
    notes: list[tuple[str, str]] = []
    itemized: list[tuple[str, str]] = []
    head_person = H.head(household)
    spouse_person = H.spouse(household)
    filer_people = [head_person] + ([spouse_person] if spouse_person else [])
    passive = passive_activities(filer_people)
    employer_plan = any(H.flag(p, "has_esi") for p in filer_people)
    head = _filer(head_person, year, notes, passive[head_person["name"]], employer_plan)
    spouse = _filer(spouse_person, year, notes, passive[spouse_person["name"]], employer_plan) if spouse_person else None
    everyone = H.people(household)

    limit = QUALIFYING_RELATIVE_INCOME_LIMIT[year]
    dependents, left_out, own_payroll, disabled_reading = [], [], [], []
    for person in H.others(household):
        age = int(person["age"])
        income = own_gross_income(person, year)
        own_wages, own_se = own_earnings(person)
        disabled = H.flag(person, "is_disabled")
        record = {"name": person["name"], "age": age, "gross_income": income,
                  "disabled": disabled,
                  "unmarried_partner": H.flag(person, "is_unmarried_partner_of_household_head"),
                  # Relationship is taken as met unless the household states otherwise
                  # (READINGS["dependents"]; READINGS["unrelated_member"]).
                  "related": person.get("inputs", {}).get("is_related_to_head_or_spouse", True) is not False,
                  "incapable": H.flag(person, "is_incapable_of_self_care")}
        without_reading = None
        if age < 19:
            record["kind"] = "qualifying_child"
        elif disabled and own_wages == 0 and own_se == 0:
            # The is_disabled reading: 152(c)(3)(B) meets the age test at any age.
            record["kind"] = "qualifying_child"
            without_reading = "qualifying_relative" if income < limit else "left_out"
        elif income < limit:
            record["kind"] = "qualifying_relative"
        else:
            record["kind"] = None
        if record["kind"] is None:
            del record["kind"]
            left_out.append(record)
            notes.append(("income_tax", f"{person['name']} (age {age}, gross income {income:,.0f}) meets neither dependency test of 26 U.S.C. 152 on the stated facts and is not claimed"))
        else:
            dependents.append(record)
            if not record["related"] and record["kind"] == "qualifying_child":
                _reading(notes, "unrelated_member", f"{person['name']} (age {age}) is stated not related to the head or spouse. ")
        if without_reading is not None:
            disabled_reading.append({
                "name": person["name"], "age": age, "gross_income": income,
                "with_reading": "qualifying_child", "without_reading": without_reading,
                # Without the reading the gross-income test decides, and it rests on these.
                "income_readings_without": [k for k in _INCOME_TEST_READINGS if H.amount(person, k)],
            })
            _reading(notes, "is_disabled", f"{person['name']} (age {age}) is a qualifying child under this reading, {without_reading.replace('_', ' ')} without it. ")
        elif disabled and age >= 19:
            _reading(notes, "is_disabled", f"{person['name']} (age {age}) is stated disabled but has earnings of their own, so is not read as permanently and totally disabled. ")
        if age >= 19 and without_reading is None:
            # The gross-income test decides this member: name each reading it rests on.
            for key, reading in _INCOME_TEST_READINGS.items():
                if H.amount(person, key):
                    _reading(notes, reading, f"{person['name']}'s gross-income test (26 U.S.C. 152(d)(1)(B)) rests on this reading of their {key}. ")
        if own_wages > 0 or own_se > 0:
            own_payroll.append({"name": person["name"], "age": age, "wages": own_wages, "self_employment": own_se})
            notes.append(("payroll", f"{person['name']} has earnings of their own: their Social Security and Medicare tax counts in the household's payroll line; their income tax return is outside the board's output"))
            if own_se > 0:
                notes.append(("self_employment", f"{person['name']} has self-employment earnings of their own: their self-employment tax counts in the household's line; their income tax return is outside the board's output"))
        stated = [key for key in _MEMBER_INCOME_KEYS if H.amount(person, key)]
        if stated:
            notes.append(("income_tax", f"{person['name']} has income of their own ({', '.join(stated)}), which is not income of the head's return"))

    # 26 U.S.C. 2(a)(1)(B) and 2(b)(3)(B)(i): a dependent only as a member of the household
    # (an unmarried partner, or a qualifying relative stated not related) makes the taxpayer
    # neither a surviving spouse nor a head of household. A qualifying child counts whether
    # or not stated related (READINGS["unrelated_member"]).
    claimants = [
        d for d in dependents
        if not d["unmarried_partner"] and (d["related"] or d["kind"] == "qualifying_child")
    ]
    qualifying_children = [d for d in claimants if d["kind"] == "qualifying_child"]
    if spouse is not None:
        status = S.JOINT
    elif H.flag(head_person, "is_surviving_spouse") and claimants:
        # 26 U.S.C. 2(a)(1)(B): any son or daughter dependent, not only a qualifying child.
        status = S.SURVIVING_SPOUSE
        _reading(notes, "surviving_spouse")
    elif H.flag(head_person, "is_separated"):
        # 26 U.S.C. 7703(b): married and living apart; unmarried only with a qualifying
        # child in the home (policyengine-us head_of_household_eligible.py, experiment E2).
        status = S.HEAD_OF_HOUSEHOLD if qualifying_children else S.SEPARATE
        _reading(notes, "separated")
    elif claimants:
        status = S.HEAD_OF_HOUSEHOLD
    else:
        status = S.SINGLE

    def total(key: str, people=filer_people) -> float:
        return sum(H.amount(p, key) for p in people)

    tax_unit = household.get("tax_unit_inputs", {})
    spm_unit = household.get("spm_unit_inputs", {})
    home = household.get("household_inputs", {})
    for person in H.others(household):
        for key in ("real_estate_taxes", "home_mortgage_interest", "charitable_cash_donations"):
            if H.amount(person, key):
                notes.append(("income_tax", f"{person['name']} states {key}, which is not an expense of the head's return (reading: {READINGS['member_expenses']})"))
        for key in ("investment_interest_expense", "self_employed_pension_contributions_desired"):
            if H.amount(person, key):
                notes.append(("income_tax", f"{person['name']} states {key}, which is not a deduction of the head's return (reading: {READINGS['member_deductions']})"))
    claimed = {d["name"] for d in dependents}
    for person in H.others(household):
        if person["name"] not in claimed and (
            H.amount(person, "other_medical_expenses")
            or H.amount(person, "health_insurance_premiums_without_medicare_part_b")
            or H.amount(person, "health_insurance_premiums")
        ):
            itemized.append(("income_tax", f"{person['name']} is not claimed, and their medical expenses count: " + READINGS["member_expenses"]))
    amounts = {
        "taxable_interest": total("taxable_interest_income"),
        "tax_exempt_interest": total("tax_exempt_interest_income"),
        "qualified_dividends": total("qualified_dividend_income"),
        "non_qualified_dividends": total("non_qualified_dividend_income"),
        "short_term_gains": total("short_term_capital_gains"),
        "long_term_gains": total("long_term_capital_gains"),
        "capital_gain_distributions": sum(max(0.0, H.amount(p, "non_sch_d_capital_gains")) for p in filer_people),
        # A SEP is an IRA (26 U.S.C. 408(k)): its taxable distributions are IRA distributions.
        "taxable_ira_distributions": total("taxable_ira_distributions") + total("taxable_sep_distributions"),
        "taxable_pensions": total("taxable_private_pension_income") + total("taxable_401k_distributions") + total("taxable_403b_distributions"),
        "tax_exempt_pensions": total("tax_exempt_private_pension_income"),
        "social_security": sum(total(k) for k in _SOCIAL_SECURITY),
        "unemployment": total("unemployment_compensation"),
        "salt_refund": total("salt_refund_income"),
        "alimony_received": total("alimony_income"),
        "alimony_paid": total("alimony_expense"),
        # Passive activities after 26 U.S.C. 469 (READINGS["passive_activity"]): the
        # allowed amounts; the stated ones under *_stated.
        "rental": sum(passive[p["name"]]["rental"] for p in filer_people),
        "farm_rent": sum(passive[p["name"]]["farm_rent"] for p in filer_people),
        "partnership_s_corp": sum(passive[p["name"]]["partnership"] for p in filer_people),
        "rental_stated": total("rental_income"),
        "farm_rent_stated": total("farm_rent_income"),
        "partnership_stated": sum(partnership_income(p) for p in filer_people),
        # Allowed rent and farm rent that is qualified business income (READINGS["rental_qbi"]).
        "rental_qbi": sum(passive[p["name"]]["rental"] + passive[p["name"]]["farm_rent"]
                          for p in filer_people if rentals_qualified(p)),
        "estate": total("estate_income"),
        # READINGS["negative_miscellaneous"]: a negative amount enters as 0.
        "miscellaneous": sum(max(0.0, H.amount(p, "miscellaneous_income")) for p in filer_people),
        "educational_assistance": total("educational_assistance"),
        "disability_benefits": total("disability_benefits"),
        "student_loan_interest": total("student_loan_interest"),
        # READINGS["hsa"]: up to the 223(b) limit of the head (self-only coverage).
        "hsa_stated": float(tax_unit.get("health_savings_account_ald", 0.0) or 0.0),
        "hsa_deduction": min(float(tax_unit.get("health_savings_account_ald", 0.0) or 0.0),
                             S.hsa_deduction_limit(year, int(head_person["age"]))),
        "domestic_production": float(tax_unit.get("domestic_production_ald", 0.0) or 0.0),
        # Medical (26 U.S.C. 213(a)): every listed member's stated premiums (without
        # Medicare Part B, or health_insurance_premiums where stated, READINGS
        # ["health_insurance_premiums"]) and other medical costs, less the filers' premiums
        # deducted under 162(l) (162(l)(3)). Over-the-counter health expenses and other
        # health insurance premiums are left out by the readings of those names.
        "medical": sum(H.amount(p, "other_medical_expenses") + _premiums(p) for p in everyone)
        - min(sum(_premiums(p) for p in filer_people), sum(f.se_health for f in (head, spouse) if f)),
        "real_estate_taxes": total("real_estate_taxes"),
        "mortgage_interest": total("home_mortgage_interest"),
        "mortgage_balances": float(tax_unit.get("first_home_mortgage_balance", 0.0) or 0.0)
        + float(tax_unit.get("second_home_mortgage_balance", 0.0) or 0.0),
        "charity_cash": total("charitable_cash_donations"),
        "charity_non_cash": total("charitable_non_cash_donations"),
        "employee_expenses": total("unreimbursed_business_employee_expenses"),
        "child_care": float(spm_unit.get("spm_unit_pre_subsidy_childcare_expenses", 0.0) or 0.0),
        "auto_loan_interest": float(home.get("auto_loan_interest", 0.0) or 0.0),
        "ubia": total("unadjusted_basis_qualified_property"),
        "sstb_ubia": total("sstb_unadjusted_basis_qualified_property"),
        "reit_ptp": total("qualified_reit_and_ptp_income"),
        "survivor_benefits": total("survivor_benefits"),
        # Facts only the larger draw states (zero for every board household).
        "qualified_vehicle_loan_interest": float(home.get("qualified_passenger_vehicle_loan_interest", 0.0) or 0.0),
        "investment_interest": total("investment_interest_expense"),
        "form_4952_election": total("investment_income_elected_form_4952"),
        # Schedule D lines 19 and 18: parts of the long-term gains, never added to them.
        "unrecaptured_1250": float(tax_unit.get("unrecaptured_section_1250_gain", 0.0) or 0.0),
        "collectibles_28": total("long_term_capital_gains_on_collectibles"),
        "qbi_w2_wages": total("w2_wages_from_qualified_business"),
        "sstb_qbi_w2_wages": total("sstb_w2_wages_from_qualified_business"),
        "se_health_insurance": sum(f.se_health for f in (head, spouse) if f),
        "se_pension": sum(f.se_pension for f in (head, spouse) if f),
        "care_expenses_of_incapable": 0.0,   # filled with the care individuals below
        "form_4952_elected": 0.0,            # the election after 163(d)(4)(B)(iii), below
        "investment_interest_allowed": 0.0,  # the deduction after 163(d)(1), below
        "early_distributions": 0.0,          # subject to 72(t), below
    }
    filers = [head] + ([spouse] if spouse else [])

    # Readings of stated facts that bear on the return.
    if amounts["disability_benefits"]:
        _reading(notes, "disability_benefits")
    if amounts["survivor_benefits"]:
        _reading(notes, "survivor_benefits")
    if amounts["educational_assistance"]:
        _reading(notes, "educational_assistance")
    if amounts["salt_refund"]:
        _reading(notes, "salt_refund_income")
    if amounts["alimony_received"] or amounts["alimony_paid"]:
        _reading(notes, "alimony")
    if any(f.tips for f in filers):
        _reading(notes, "tips")
    if amounts["auto_loan_interest"]:
        _reading(notes, "auto_loan_interest")
    if amounts["rental_stated"] or amounts["farm_rent_stated"] or amounts["estate"]:
        _reading(notes, "rental_qbi")
    if amounts["partnership_stated"]:
        _reading(notes, "partnership_qbi")
    # The passive partnership share outside self-employment earnings is net investment
    # income and EITC investment income (READINGS["passive_activity"]).
    passive_partnership = amounts["partnership_s_corp"] - sum(f.partnership_se for f in (head, spouse) if f)
    if abs(passive_partnership) >= 0.005:
        notes.append(("income_tax", f"the maps read {passive_partnership:,.2f} of partnership and S corporation income (beyond partners' self-employment earnings) as passive, so as net investment income (26 U.S.C. 1411(c)(1)(A)(ii), (c)(2)(A)) and EITC investment income (32(i)(2)(D)); policyengine-us counts only passive_partnership_s_corp_income, an input no household states, in both (parameters/gov/irs/investment/income/sources.yaml:13; eitc_relevant_investment_income), so it reads the stated amount as nonpassive"))
    for key in ("financial_assistance", "qualified_bdc_income", "farm_income"):
        if total(key):
            _reading(notes, key)
    # 26 U.S.C. 469 (READINGS["passive_activity"]).
    if amounts["rental_stated"] or amounts["farm_rent_stated"] or amounts["partnership_stated"] or any(
        f.schedule_c < 0 or f.schedule_f < 0 for f in (head, spouse) if f
    ):
        _reading(notes, "passive_activity")
    stated_passive = [(p["name"], k, passive[p["name"]][f"{k}_stated"], passive[p["name"]][k])
                      for p in filer_people for k in ("partnership", "rental", "farm_rent")]
    suspended = sum(s_ - a_ for _, _, s_, a_ in stated_passive)
    if suspended < 0:
        parts = "; ".join(f"{name}'s {k.replace('_', ' ')} {s_:,.2f} allowed {a_:,.2f}"
                          for name, k, s_, a_ in stated_passive if s_ != a_)
        notes.append(("income_tax", f"26 U.S.C. 469: a net passive activity loss of {-suspended:,.2f} is disallowed this year and carries forward (469(b)); {parts}. policyengine-us applies no 469 limit"))
    if any(f.partnership_se != partnership_se(p) for f, p in zip((head, spouse), filer_people) if f):
        notes.append(("self_employment", "a partner's self-employment loss shrinks with the disallowed share of the partnership's loss (Temp. Reg. 1.469-1T(d)(3); READINGS passive_activity)"))
    for person in filer_people:
        misc = H.amount(person, "miscellaneous_income")
        if misc < 0:
            notes.append(("income_tax", f"reading: {person['name']} states miscellaneous income of {misc:,.2f}. " + READINGS["negative_miscellaneous"]))
    if household.get("state") == "AK":
        _reading(notes, "alaska_dividend")
    if any(f.partnership_se for f in filers):
        _reading(notes, "partnership_se")
    if any(f.overtime_premium for f in filers):
        _reading(notes, "overtime_premium")
    if any(f.educator_expense for f in filers):
        _reading(notes, "educator")
    if amounts["hsa_stated"]:
        _reading(notes, "hsa")
        if amounts["hsa_deduction"] < amounts["hsa_stated"]:
            notes.append(("income_tax", f"the stated health savings account deduction of {amounts['hsa_stated']:,.2f} exceeds the 26 U.S.C. 223(b) limit; {amounts['hsa_deduction']:,.0f} is allowed (policyengine-us takes the stated amount)"))
    if any(f.ira_traditional_desired > 0 for f in filers) and any(f.active_participant for f in filers):
        _reading(notes, "active_participant")
    if amounts["investment_interest"] or amounts["form_4952_election"]:
        _reading(notes, "investment_interest")
    # The child and dependent care credit's qualifying individuals (26 U.S.C. 21(b)(1)):
    # dependents under 13, dependents incapable of self-care, members left out only by
    # the gross-income test who are incapable (21(b)(1)(B)), and on a joint return one
    # spouse incapable of self-care ((b)(1)(C); policyengine-us count_cdcc_eligible.py
    # counts at most one).
    care = [dict(name=d["name"], age=d["age"], why="under 13") for d in dependents if d["age"] < 13]
    care += [dict(name=d["name"], age=d["age"], why="dependent incapable of self-care")
             for d in dependents if d["age"] >= 13 and d["incapable"]]
    care += [dict(name=d["name"], age=d["age"], why="incapable of self-care, a dependent but for 152(d)(1)(B)")
             for d in left_out if d["incapable"]]
    if status == S.JOINT:
        incapable_filer = next((f for f in (spouse, head) if f.incapable), None)
        if incapable_filer is not None:
            care.append(dict(name=incapable_filer.name, age=incapable_filer.age, why="spouse incapable of self-care"))
    if any(H.flag(p, "is_incapable_of_self_care") for p in everyone):
        _reading(notes, "incapable")
    care_names = {c["name"] for c in care}
    for person in everyone:
        expense = H.amount(person, "pre_subsidy_care_expenses")
        if not expense:
            continue
        if person["name"] in care_names:
            amounts["care_expenses_of_incapable"] += expense
        else:
            notes.append(("income_tax", f"{person['name']} states care expenses but is not a qualifying individual for the care credit (26 U.S.C. 21(b)(1)); the expenses are left out (policyengine-us adds every member's care expenses)"))
    amounts["child_care"] += amounts["care_expenses_of_incapable"]

    # 26 U.S.C. 163(d): investment interest up to net investment income, which counts the
    # elected qualified dividends and net capital gain (163(d)(4)(B)); capital gain
    # distributions are long-term gains.
    long_term = amounts["long_term_gains"] + amounts["capital_gain_distributions"]
    amounts["form_4952_elected"] = S.elected_investment_income(
        amounts["form_4952_election"], amounts["qualified_dividends"], amounts["short_term_gains"], long_term
    )
    amounts["investment_interest_allowed"] = S.investment_interest_deduction(
        amounts["investment_interest"], amounts["taxable_interest"], amounts["non_qualified_dividends"],
        amounts["qualified_dividends"], amounts["short_term_gains"], long_term, amounts["form_4952_election"],
    )
    if amounts["form_4952_elected"] < amounts["form_4952_election"]:
        notes.append(("income_tax", f"the Form 4952 election of {amounts['form_4952_election']:,.0f} exceeds the qualified dividends and net capital gain; {amounts['form_4952_elected']:,.0f} is taken as elected (26 U.S.C. 163(d)(4)(B)(iii))"))
    if amounts["investment_interest_allowed"] < amounts["investment_interest"]:
        notes.append(("income_tax", f"investment interest of {amounts['investment_interest']:,.0f} exceeds net investment income: 26 U.S.C. 163(d)(1) allows {amounts['investment_interest_allowed']:,.0f} this year (the rest carries forward, 163(d)(2)); policyengine-us deducts all of it for an itemizer"))
    if status == S.SURVIVING_SPOUSE and amounts["qualified_vehicle_loan_interest"]:
        notes.append(("income_tax", "a qualifying surviving spouse states qualified passenger vehicle loan interest: policyengine-us starts its phase-out at $200,000 of modified AGI; 26 U.S.C. 163(h)(4)(C)(ii) gives $200,000 only on a joint return (Schedule 1-A line 26), and Tax-Calculator starts at $100,000"))
    if status == S.SEPARATE:
        notes.append(("income_tax", "married filing separately without a qualifying child: 26 U.S.C. 32(d)(1) allows no earned income credit (the separated-spouse rule of 32(d)(2)(B) needs a qualifying child)"))
    # 26 U.S.C. 72(t) (READINGS["retirement_penalty"]): the tax itself depends on AGI
    # (the medical exception), so each map figures it after its AGI pass.
    for filer, person in zip(filers, filer_people):
        if filer.age > 59:
            continue
        early = sum(max(0.0, H.amount(person, key)) for key in _EARLY_DISTRIBUTIONS)
        pension = sum(max(0.0, H.amount(person, key)) for key in _PRIVATE_PENSIONS)
        disabled = H.flag(person, "is_disabled") and own_earnings(person) == (0.0, 0.0)
        if early and disabled:
            notes.append(("income_tax", f"reading: {filer.name} (age {filer.age}) is stated disabled with no earnings of their own, so is disabled under 26 U.S.C. 72(m)(7) and owes no 72(t) tax. " + READINGS["retirement_penalty"]))
        elif early:
            amounts["early_distributions"] += early
            notes.append(("income_tax", f"reading: {filer.name} (age {filer.age}) takes {early:,.2f} of taxable IRA, SEP, 401(k) or 403(b) distributions. " + READINGS["retirement_penalty"]))
        if pension and not disabled:
            notes.append(("income_tax", f"reading: {filer.name} (age {filer.age}) takes a private pension, which bears no 72(t) tax. " + READINGS["retirement_penalty"]))
    if any(f.age >= 65 for f in filers) and amounts["medical"] > 0:
        _reading(notes, "medicare_part_b")

    # Readings that can move an answer only for an itemizer.
    def itemized_reading(key: str) -> None:
        note = ("income_tax", "reading: " + READINGS[key])
        if note not in itemized:
            itemized.append(note)

    if any(H.amount(p, "other_health_insurance_premiums") for p in everyone):
        itemized_reading("other_health_insurance_premiums")
    if amounts["charity_cash"] or amounts["charity_non_cash"]:
        itemized_reading("charity")
    if any(H.amount(p, "over_the_counter_health_expenses") for p in everyone):
        itemized_reading("over_the_counter")
    debt_limit = S.AMOUNTS[year]["mortgage_debt_limit"]
    if amounts["mortgage_interest"] and amounts["mortgage_balances"] > (
        debt_limit[S.SEPARATE] if status == S.SEPARATE else debt_limit["other"]
    ):
        itemized_reading("mortgage_date")

    return Unit(
        case_id=household["id"], year=year, state=household["state"], status=status,
        head=head, spouse=spouse, dependents=dependents, left_out=left_out,
        amounts=amounts, notes=notes, members_with_own_payroll=own_payroll,
        itemized_notes=itemized, disabled_reading=disabled_reading,
        care_individuals=care,
    )
