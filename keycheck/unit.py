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

VERSION = "2026-11-10.2"

# 26 U.S.C. 152(d)(1)(B): a qualifying relative's gross income must be under the
# exemption amount (Rev. Proc. 2025-32 sec. 4.23: $5,300 for 2026; Rev. Proc. 2024-40
# sec. 2.24: $5,200 for 2025).
QUALIFYING_RELATIVE_INCOME_LIMIT = {2026: 5_300, 2025: 5_200}

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
        "Employment disability benefits are taxable and are not wages (an employer-paid "
        "plan, 26 U.S.C. 105(a)). The board does not state who paid for the coverage."
    ),
    "survivor_benefits": "Survivor benefits other than Social Security are not taxable (the board's reference reading; taxability is not stated).",
    "salt_refund_income": "A stated state or local tax refund is taxable in full (the board's reference reading; the prior-year tax benefit is not stated).",
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
        "Stated rental income and estate income are not qualified business income: whether "
        "a rental is a section 162 trade or business (26 U.S.C. 199A(d)(1)) is not stated. "
        "Tax-Calculator gets rent in e02000 only (not e26270 or e27200); TAXSIM gets rent "
        "and estate income in `intrec`, either sign. PolicyEngine's default counts rent as "
        "qualified business income (rental_income_would_be_qualified defaults to true) and "
        "estate income not."
    ),
    "retirement_penalty": "No additional tax on early retirement distributions (26 U.S.C. 72(t)): no exception or its absence is stated.",
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
        "Stated educational assistance (scholarships and grants) is not taxable: it is read "
        "as a qualified scholarship (26 U.S.C. 117(a)); whether it exceeded tuition and "
        "related expenses (117(b)) is not stated, and the board cannot state tuition."
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
        "25B(d)(2)(B)) are not stated and are taken as zero; tax-exempt IRA and pension "
        "distributions count. A filer is not a full-time student (25B(c)(2)(B)) unless "
        "stated; the American opportunity enrollment flags (at least half time) are not "
        "read as full time."
    ),
    "educator": "A stated educator expense is an eligible educator's (26 U.S.C. 62(d)(1)): hours worked in a school are not stated.",
    "hsa": "The stated health savings account deduction is the allowed deduction (the board states it as a deduction); no 26 U.S.C. 223(b) limit is applied.",
    "self_employed_health_insurance": (
        "A self-employed filer's stated premiums go to itemized medical expenses, not the "
        "26 U.S.C. 162(l) deduction: whether the plan was established under the business is "
        "not stated."
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
}

# A member's own income items that count as gross income for the qualifying-relative test.
_GROSS_INCOME_ITEMS = (
    "taxable_interest_income", "qualified_dividend_income",
    "non_qualified_dividend_income", "taxable_private_pension_income",
    "taxable_ira_distributions", "taxable_401k_distributions", "taxable_403b_distributions",
    "unemployment_compensation", "miscellaneous_income", "salt_refund_income",
    "disability_benefits", "estate_income",
)
_GROSS_INCOME_NET_ITEMS = (  # counted when positive: the board states net amounts only
    "self_employment_income", "sstb_self_employment_income_before_lsr",
    "farm_operations_income", "rental_income", "farm_rent_income", "partnership_s_corp_income",
)
_GAINS = ("short_term_capital_gains", "long_term_capital_gains", "non_sch_d_capital_gains")
_SOCIAL_SECURITY = (
    "social_security_retirement", "social_security_disability",
    "social_security_survivors", "social_security_dependents",
)
_SELF_EMPLOYMENT = (
    "self_employment_income", "sstb_self_employment_income_before_lsr",
    "farm_operations_income", "partnership_se_income",
)
# Every stated income item of a member, for the note that it is not the head's income.
_MEMBER_INCOME_KEYS = (
    ("employment_income",) + _SELF_EMPLOYMENT + _GROSS_INCOME_ITEMS + _GROSS_INCOME_NET_ITEMS
    + _GAINS + _SOCIAL_SECURITY
    + ("tax_exempt_interest_income", "tax_exempt_ira_distributions",
       "tax_exempt_private_pension_income", "survivor_benefits", "alimony_income")
)
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
    total += sum(max(0.0, H.amount(person, key)) for key in _GAINS)
    benefits = sum(H.amount(person, key) for key in _SOCIAL_SECURITY)
    taxable = taxable_social_security_unmarried(
        benefits, total, H.amount(person, "tax_exempt_interest_income")
    )
    return total + taxable


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
    retirement_distributions: float   # IRA, 401(k), 403(b) and pension distributions, taxable or not
    overtime_premium: float
    tips: float

    @property
    def self_employment(self) -> float:
        return self.schedule_c + self.schedule_f + self.partnership_se

    @property
    def active_participant(self) -> bool:
        return self.deferral + self.roth_deferral > 0


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


def _filer(person: dict, year: int, notes: list) -> Filer:
    wages = H.amount(person, "employment_income")
    deferral, roth_deferral = _deferrals(person, year, notes)
    schedule_c = H.amount(person, "self_employment_income") + H.amount(
        person, "sstb_self_employment_income_before_lsr"
    )
    distributions = sum(
        max(0.0, H.amount(person, key))
        for key in (
            "taxable_ira_distributions", "tax_exempt_ira_distributions",
            "taxable_401k_distributions", "taxable_403b_distributions",
            "taxable_private_pension_income", "tax_exempt_private_pension_income",
        )
    )
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
        schedule_f=H.amount(person, "farm_operations_income"),
        partnership_se=H.amount(person, "partnership_se_income"),
        educator_expense=H.amount(person, "educator_expense"),
        retirement_distributions=distributions,
        overtime_premium=H.amount(person, "fsla_overtime_premium"),
        tips=H.amount(person, "tip_income"),
    )


def _reading(notes: list, key: str, prefix: str = "") -> None:
    note = ("income_tax", "reading: " + prefix + READINGS[key])
    if note not in notes:
        notes.append(note)


def build(household: dict, year: int) -> Unit:
    notes: list[tuple[str, str]] = []
    itemized: list[tuple[str, str]] = []
    head_person = H.head(household)
    spouse_person = H.spouse(household)
    head = _filer(head_person, year, notes)
    spouse = _filer(spouse_person, year, notes) if spouse_person else None
    filer_people = [head_person] + ([spouse_person] if spouse_person else [])
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
                  "unmarried_partner": H.flag(person, "is_unmarried_partner_of_household_head")}
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

    claimants = [d for d in dependents if not d["unmarried_partner"]]
    if spouse is not None:
        status = S.JOINT
    elif H.flag(head_person, "is_surviving_spouse") and claimants:
        # 26 U.S.C. 2(a)(1)(B): any son or daughter dependent, not only a qualifying child.
        status = S.SURVIVING_SPOUSE
        _reading(notes, "surviving_spouse")
    elif claimants:
        # 26 U.S.C. 2(b)(3)(B)(i): a dependent only as a member of the household (an
        # unmarried partner) does not make the taxpayer a head of household.
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
    claimed = {d["name"] for d in dependents}
    for person in H.others(household):
        if person["name"] not in claimed and (
            H.amount(person, "other_medical_expenses")
            or H.amount(person, "health_insurance_premiums_without_medicare_part_b")
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
        "taxable_ira_distributions": total("taxable_ira_distributions"),
        "taxable_pensions": total("taxable_private_pension_income") + total("taxable_401k_distributions") + total("taxable_403b_distributions"),
        "tax_exempt_pensions": total("tax_exempt_private_pension_income"),
        "social_security": sum(total(k) for k in _SOCIAL_SECURITY),
        "unemployment": total("unemployment_compensation"),
        "salt_refund": total("salt_refund_income"),
        "alimony_received": total("alimony_income"),
        "alimony_paid": total("alimony_expense"),
        "rental": total("rental_income"),
        "farm_rent": total("farm_rent_income"),
        "partnership_s_corp": total("partnership_s_corp_income"),
        "estate": total("estate_income"),
        "miscellaneous": total("miscellaneous_income"),
        "disability_benefits": total("disability_benefits"),
        "student_loan_interest": total("student_loan_interest"),
        "hsa_deduction": float(tax_unit.get("health_savings_account_ald", 0.0) or 0.0),
        "domestic_production": float(tax_unit.get("domestic_production_ald", 0.0) or 0.0),
        # Medical (26 U.S.C. 213(a)): every listed member's stated premiums (without
        # Medicare Part B) and other medical costs. Over-the-counter health expenses and
        # other health insurance premiums are left out by the readings of those names.
        "medical": sum(
            H.amount(p, "other_medical_expenses") + H.amount(p, "health_insurance_premiums_without_medicare_part_b")
            for p in everyone
        ),
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
    }
    filers = [head] + ([spouse] if spouse else [])

    # Readings of stated facts that bear on the return.
    if amounts["disability_benefits"]:
        _reading(notes, "disability_benefits")
    if amounts["survivor_benefits"]:
        _reading(notes, "survivor_benefits")
    if amounts["salt_refund"]:
        _reading(notes, "salt_refund_income")
    if amounts["alimony_received"] or amounts["alimony_paid"]:
        _reading(notes, "alimony")
    if any(f.tips for f in filers):
        _reading(notes, "tips")
    if amounts["auto_loan_interest"]:
        _reading(notes, "auto_loan_interest")
    if amounts["rental"] or amounts["estate"]:
        _reading(notes, "rental_qbi")
    for key in ("educational_assistance", "financial_assistance", "qualified_bdc_income", "farm_income"):
        if total(key):
            _reading(notes, key)
    if any(f.partnership_se for f in filers):
        _reading(notes, "partnership_se")
    if any(f.overtime_premium for f in filers):
        _reading(notes, "overtime_premium")
    if any(f.educator_expense for f in filers):
        _reading(notes, "educator")
    if amounts["hsa_deduction"]:
        _reading(notes, "hsa")
    if any(f.ira_traditional_desired > 0 for f in filers) and any(f.active_participant for f in filers):
        _reading(notes, "active_participant")
    if any(
        f.self_employment > 0 and (
            H.amount(p, "health_insurance_premiums_without_medicare_part_b")
            or H.amount(p, "other_health_insurance_premiums")
        )
        for f, p in zip(filers, filer_people)
    ):
        _reading(notes, "self_employed_health_insurance")
    for filer in filers:
        if filer.age <= 59 and filer.retirement_distributions > 0:
            # Age at year end; a filer aged 59 can be under 59 1/2 when paid.
            under = "is under" if filer.age < 59 else "may be under"
            notes.append(("income_tax", f"reading: {filer.name} {under} 59 1/2 with retirement distributions. " + READINGS["retirement_penalty"]))
    if any(f.age >= 65 for f in filers) and amounts["medical"] > 0:
        _reading(notes, "medicare_part_b")

    # Readings that can move an answer only for an itemizer.
    def itemized_reading(key: str) -> None:
        note = ("income_tax", "reading: " + READINGS[key])
        if note not in itemized:
            itemized.append(note)

    if any(H.amount(p, "other_health_insurance_premiums") for p in everyone):
        itemized_reading("other_health_insurance_premiums")
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
    )
