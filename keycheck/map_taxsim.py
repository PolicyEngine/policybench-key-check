"""Map a PolicyBench household to NBER TAXSIM's inputs (build cd2026110117).

NBER publishes no source, so what each input does was established from NBER's pages and
by probing the binary (run folder understand-inputs, unit taxsim; probe files under
probes/taxsim/). The facts this map rests on, each with its probe:

- Dependents. With `age1..` the build's 2026 EITC is wrong for one to three children and
  its 2026 child care credit is zero; with counts (`depx`, `dep13`, `dep17`, `dep18`) the
  2026 EITC matches Rev. Proc. 2025-32 (probes P3, P4). So 2026 uses counts and 2025 uses
  ages. On the counts path the child tax credit goes to `dep18` children, so a 17- or
  18-year-old gets $2,200, not $500; on the ages path a 17-year-old does (P2, P3).
- `otherprop` is ignored from 2024 on (P6.1), so rent and estate income go to `intrec`,
  which is ordinary income, net investment income and EITC investment income.
- `nonprop` counts as earned income for the EITC (P6.8, P7.1), so other taxable income
  goes to `pensions` (ordinary income and nothing else); adjustments to income have no
  other home and go to `nonprop` as negative amounts, as NBER's page says.
- `psemp` carries self-employment tax and gets the qualified business income deduction
  (P6.4, P6.5); `scorp` gets the deduction with no self-employment tax; `pprofinc` is a
  specified service business.
- Only `proptax` (and TAXSIM's own state tax) is held to the SALT cap; `otheritem` is
  not (P9.2). `mortgage` is deducted as given (P9.3). With `state` 0 the build itemizes
  when itemized deductions exceed the standard deduction (P9.4).
- No input exists for blindness, a qualifying surviving spouse, pre-tax contributions,
  tips, overtime, vehicle-loan interest, tax-exempt interest, charitable gifts by a
  non-itemizer, or the saver's credit (P1); each is listed in `unexpressed` when the
  household states it.

`rows(household, year, shared)` returns the first-pass record. Like the Tax-Calculator
map, later passes add the amounts that depend on TAXSIM's own adjusted gross income.
"""

from __future__ import annotations

from . import map_taxcalc
from . import statute as S
from . import unit as U

VERSION = "2026-11-10.1"

# 26 U.S.C. 213(a): medical expenses above 7.5% of AGI. 26 U.S.C. 170(b)(1)(I): from
# 2026 charitable gifts count only above 0.5% of AGI.
MEDICAL_FLOOR = 0.075
CHARITY_FLOOR = {2026: 0.005, 2025: 0.0}


def first_pass(household: dict, year: int, shared: dict | None = None):
    """Return (record, unit, unexpressed, map_computed)."""
    shared = shared or {}
    unit = U.build(household, year)
    a = unit.amounts
    head, spouse = unit.head, unit.spouse
    unexpressed = [f"{group}: {text}" for group, text in unit.notes]
    computed: list[str] = []

    def per_filer(get):
        return get(head), (get(spouse) if spouse else 0.0)

    wages_p, wages_s = per_filer(lambda f: max(0.0, f.wages - f.deferral))
    # A partner's self-employment earnings are part of the partnership income, not more
    # income: they move from `scorp` to the self-employment box.
    se_p, se_s = per_filer(lambda f: f.schedule_c - f.sstb + f.schedule_f + f.partnership_se)
    sstb_p, sstb_s = per_filer(lambda f: f.sstb)
    partnership_se = sum(f.partnership_se for f in unit.filers)
    passive_business = a["partnership_s_corp"] - partnership_se + a["farm_rent"]
    # Rent and estate income; a net loss cannot be entered as negative interest, so it
    # joins `scorp`, where the build allows a loss in full (P7.3).
    property_income = a["rental"] + a["estate"]
    passive_business += min(0.0, property_income)
    educator = S.educator_expense_deduction(year, [f.educator_expense for f in unit.filers])
    if any(f.educator_expense for f in unit.filers):
        computed.append("income_tax: educator expenses limited by 26 U.S.C. 62(a)(2)(D)")
    # Other taxable income goes to `pensions`; TAXSIM rejects a negative pension, so a net
    # loss there goes to `nonprop`.
    other_income = a["miscellaneous"] + a["disability_benefits"] + a["salt_refund"]
    if head.deferral or (spouse and spouse.deferral):
        computed.append("income_tax: traditional 401(k) deferrals limited by 26 U.S.C. 402(g) and to wages; TAXSIM has no input for them, so wages are entered net for income tax and gross for payroll tax")

    record = {
        "year": year,
        "state": 0,
        "mstat": 2 if unit.status == S.JOINT else 1,
        "page": head.age,
        "sage": spouse.age if spouse else 0,
        "pwages": wages_p, "swages": wages_s,
        "psemp": se_p, "ssemp": se_s,
        "pprofinc": sstb_p, "sprofinc": sstb_s,
        "scorp": passive_business,
        "dividends": a["qualified_dividends"],
        "intrec": a["taxable_interest"] + a["non_qualified_dividends"] + max(0.0, property_income),
        "stcg": a["short_term_gains"],
        "ltcg": a["long_term_gains"] + a["capital_gain_distributions"],
        "pensions": a["taxable_pensions"] + a["taxable_ira_distributions"] + max(0.0, other_income),
        "gssi": a["social_security"],
        "pui": a["unemployment"],
        # Adjustments that do not depend on AGI; the IRA and student loan deductions join
        # them in later passes.
        "nonprop": -(educator + a["hsa_deduction"]) + min(0.0, other_income),
        "proptax": a["real_estate_taxes"] + float(shared.get("salt_income_or_sales_tax", 0.0)),
        "mortgage": 0.0,
        "childcare": a["child_care"],
    }
    if spouse is None:
        for name in ("swages", "ssemp", "sprofinc", "sage"):
            record[name] = 0

    # Dependents.
    children_ctc = unit.count(lambda d: d["kind"] == "qualifying_child" and d["age"] < 17)
    children_eitc = unit.count(lambda d: d["kind"] == "qualifying_child")
    children_care = unit.count(lambda d: d["age"] < 13)
    record["depx"] = len(unit.dependents)
    if year >= 2026:
        # The build gives the $2,200 credit to `dep18` children and counts at most three
        # for the EITC (probes P3, P16). With three or more children under 17, sending
        # that number gets both credits right; with fewer, a 17- or 18-year-old cannot
        # be an EITC child without also getting the $2,200 credit.
        eitc_count = children_ctc if children_ctc >= 3 else children_eitc
        record["dep13"] = min(children_care, eitc_count)
        record["dep17"] = min(children_ctc, eitc_count)
        record["dep18"] = eitc_count
        if eitc_count > children_ctc:
            unexpressed.append("income_tax: TAXSIM's counts path gives the $2,200 child credit to every EITC child, so a 17- or 18-year-old gets it in place of the $500 credit")
        if a["child_care"] and children_care:
            unexpressed.append("income_tax: this build computes the 2026 child care credit at the pre-2026 rates (probe P5)")
    else:
        ages = sorted((max(1, d["age"]) for d in unit.dependents))[:10]
        for index, age in enumerate(ages, start=1):
            record[f"age{index}"] = age
        if any(d["age"] == 17 for d in unit.dependents):
            unexpressed.append("income_tax: TAXSIM's ages path gives a 17-year-old the $2,200 child credit in place of the $500 credit (probe P2)")
        if len(unit.dependents) > 10:
            unexpressed.append("income_tax: more than ten dependents; TAXSIM takes ten ages")

    # Facts with no TAXSIM input.
    if unit.status == S.SURVIVING_SPOUSE:
        unexpressed.append("income_tax: TAXSIM has no qualifying surviving spouse status; filed as head of household")
    if unit.status == S.SINGLE and unit.dependents:
        unexpressed.append("income_tax: TAXSIM files every unmarried taxpayer with a dependent as head of household")
    if head.blind or (spouse and spouse.blind):
        unexpressed.append("income_tax: TAXSIM has no input for blindness (additional standard deduction, 26 U.S.C. 63(f)(2))")
    if any(f.overtime_premium for f in unit.filers):
        unexpressed.append("income_tax: TAXSIM has no input for qualified overtime compensation (26 U.S.C. 225)")
    if any(f.tips for f in unit.filers):
        unexpressed.append("income_tax: TAXSIM has no input for qualified tips (26 U.S.C. 224)")
    if a["tax_exempt_interest"]:
        unexpressed.append("income_tax: TAXSIM has no input for tax-exempt interest (Social Security provisional income, EITC investment income)")
    if a["tax_exempt_pensions"]:
        unexpressed.append("income_tax: TAXSIM has no input for nontaxable pensions (credit for the elderly or disabled)")
    if a["reit_ptp"]:
        unexpressed.append("income_tax: TAXSIM has no input for qualified REIT dividends and PTP income")
    if a["ubia"] or a["sstb_ubia"]:
        unexpressed.append("income_tax: TAXSIM applies no W-2 wage or property limit to the qualified business income deduction")
    if a["rental"] or a["estate"]:
        unexpressed.append("income_tax: this build ignores `otherprop` from 2024, so rent and estate income are entered as `intrec`")
    if passive_business:
        unexpressed.append("income_tax: partnership, S corporation and farm rent income are entered as `scorp`, which this build counts as net investment income and EITC investment income")
    if a["miscellaneous"] or a["disability_benefits"] or a["salt_refund"]:
        unexpressed.append("income_tax: other taxable income (miscellaneous income, taxable disability benefits, a taxable state refund) is entered as `pensions`: `nonprop` would count as EITC earned income")
    if a["alimony_received"] or a["alimony_paid"]:
        unexpressed.append("income_tax: alimony is left out (treated as a post-2018 instrument)")
    if a["domestic_production"]:
        unexpressed.append("income_tax: the domestic production activities deduction is left out (repealed for years after 2017)")
    if year >= 2026 and a["charity_cash"]:
        unexpressed.append("income_tax: TAXSIM has no charitable deduction for non-itemizers (26 U.S.C. 170(p), from 2026)")
    if "salt_income_or_sales_tax" in shared:
        unexpressed.append("income_tax: shared assumption: state and local income or sales tax paid is not stated; the amount PolicyEngine's key uses is entered with real estate taxes in `proptax`, and TAXSIM's own state calculation is off (`state` 0)")
    qbi = se_p + se_s + sstb_p + sstb_s + passive_business
    if year >= 2026 and qbi >= 1_000:
        unexpressed.append("income_tax: this build has no 2026 minimum qualified business income deduction (26 U.S.C. 199A(i))")
    return record, unit, unexpressed, computed


def after_pass(pass_number: int, record: dict, unit: U.Unit, agi: float, computed: list[str],
               unexpressed: list[str], state: dict) -> dict:
    """Add what the pass just made computable. `state` carries amounts between passes."""
    record = dict(record)
    a = unit.amounts
    year = unit.year
    contributions = map_taxcalc.ira_contributions(unit)
    educator = S.educator_expense_deduction(year, [f.educator_expense for f in unit.filers])
    if pass_number == 1:
        deduction = 0.0
        for filer in unit.filers:
            traditional, _ = contributions[filer.name]
            if traditional <= 0:
                continue
            other = [f for f in unit.filers if f is not filer]
            limit = S.ira_deductible_limit(
                year, unit.status, filer.age, agi,
                filer.active_participant, bool(other and other[0].active_participant),
            )
            deduction += min(traditional, limit)
        state["ira"] = deduction
        if any(c[0] > 0 for c in contributions.values()):
            computed.append("income_tax: IRA deduction figured under 26 U.S.C. 219(b), (c) and (g), entered as negative `nonprop`")
    elif pass_number == 2:
        interest = a["student_loan_interest"]
        state["student_loan"] = S.student_loan_interest_deduction(year, unit.status, interest, agi)
        if interest:
            computed.append("income_tax: student loan interest deduction figured under 26 U.S.C. 221, entered as negative `nonprop`")
    elif pass_number == 3:
        medical = max(0.0, a["medical"] - MEDICAL_FLOOR * max(0.0, agi))
        charity = max(0.0, a["charity_cash"] + a["charity_non_cash"] - CHARITY_FLOOR[year] * max(0.0, agi))
        mortgage = S.deductible_mortgage_interest(year, unit.status, a["mortgage_interest"], a["mortgage_balances"])
        record["mortgage"] = mortgage + charity + medical
        if a["medical"]:
            computed.append("income_tax: medical expenses above 7.5% of AGI (26 U.S.C. 213(a)) entered in `mortgage`, which TAXSIM deducts as given")
        if a["charity_cash"] + a["charity_non_cash"]:
            computed.append("income_tax: charitable gifts (above 0.5% of AGI from 2026, 26 U.S.C. 170(b)(1)(I)) entered in `mortgage`; percentage ceilings not applied")
        if a["mortgage_interest"] and mortgage != a["mortgage_interest"]:
            computed.append("income_tax: mortgage interest limited by 26 U.S.C. 163(h)(3)(F)")
        eligible = [f for f in unit.filers if f.age >= 18]
        saved = [sum(contributions[f.name]) + f.deferral + f.roth_deferral for f in eligible]
        credit = S.savers_credit(year, unit.status, agi, saved, [f.retirement_distributions for f in eligible])
        if credit:
            unexpressed.append(f"income_tax: TAXSIM has no input for the saver's credit (26 U.S.C. 25B); the statute gives up to {credit:,.0f} before the limit to tax")
    adjustments = state.get("ira", 0.0) + state.get("student_loan", 0.0) + educator + a["hsa_deduction"]
    other_income = a["miscellaneous"] + a["disability_benefits"] + a["salt_refund"]
    record["nonprop"] = -adjustments + min(0.0, other_income)
    if adjustments and pass_number == 3:
        unexpressed.append("income_tax: adjustments to income are entered as negative `nonprop`, which this build also subtracts from EITC earned income")
    return record


def payroll_records(record: dict, unit: U.Unit) -> tuple[dict, dict]:
    """The record with gross wages (pre-tax deferrals are FICA wages, 26 U.S.C. 3121(v)(1)(A)),
    and the same with every self-employment box zeroed: the pair splits `tfica`."""
    full = dict(record)
    full["pwages"] = unit.head.wages
    full["swages"] = unit.spouse.wages if unit.spouse else 0
    without = dict(full)
    for name in ("psemp", "ssemp", "pprofinc", "sprofinc", "pbusinc", "sbusinc"):
        if name in without:
            without[name] = 0
    return full, without


def member_records(member: dict, year: int) -> tuple[dict, dict]:
    """A listed member with earnings of their own, for payroll and self-employment tax only."""
    full = {"year": year, "state": 0, "mstat": 1, "page": max(1, member["age"]),
            "pwages": member["wages"], "psemp": member["self_employment"]}
    without = dict(full, psemp=0)
    return full, without
