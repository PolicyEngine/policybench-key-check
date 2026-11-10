"""Turn a PolicyBench household into the facts of one federal return, from stated facts only.

The board states people (Head, Spouse, Dependent N, Child N) and their amounts. A tax
model needs a return: who files, in what status, who is a dependent, and each line's
amount. This module derives that once, so the Tax-Calculator and TAXSIM maps start from
the same return. It reads nothing PolicyEngine computed.

Readings of facts the board does not state are named in READINGS and attached to every
unit they touch (Unit.notes), so a disagreement that comes from a reading can be told
from one that comes from a calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import households as H
from . import statute as S

VERSION = "2026-11-10.1"

# 26 U.S.C. 152(d)(1)(B): a qualifying relative's gross income must be under the
# exemption amount (Rev. Proc. 2025-32 sec. 4.19: $5,300 for 2026; Rev. Proc. 2024-40:
# $5,200 for 2025).
QUALIFYING_RELATIVE_INCOME_LIMIT = {2026: 5_300, 2025: 5_200}

READINGS = {
    "dependents": (
        "A listed member other than the head and spouse is a dependent when the stated "
        "facts can meet 26 U.S.C. 152: under 19 at year end (qualifying child; the board "
        "states no student or permanent-disability status), or own gross income under the "
        "exemption amount (qualifying relative). Relationship, residence and support are "
        "taken as met, as the board's 'one household group' says."
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
    "tips": "Stated tip income is qualified tips (received in a tipped occupation); the occupation is not stated.",
    "auto_loan_interest": "Stated auto loan interest is not qualified passenger vehicle loan interest: the loan's date and the vehicle's qualification are not stated.",
    "retirement_penalty": "No additional tax on early retirement distributions (26 U.S.C. 72(t)): no exception or its absence is stated.",
    "medicare_part_b": "Medical expenses are the stated amounts; no Medicare Part B premium is added, since none is stated.",
    "desired_contributions": "Stated 'desired' retirement contributions above a statutory limit are scaled down in proportion, as the board's key does.",
}

# A member's own income items that count as gross income for the qualifying-relative test.
_GROSS_INCOME_ITEMS = (
    "employment_income", "taxable_interest_income", "qualified_dividend_income",
    "non_qualified_dividend_income", "taxable_private_pension_income",
    "taxable_ira_distributions", "taxable_401k_distributions", "taxable_403b_distributions",
    "unemployment_compensation", "miscellaneous_income", "salt_refund_income",
    "disability_benefits", "estate_income",
)
_GROSS_INCOME_NET_ITEMS = (  # counted when positive
    "self_employment_income", "sstb_self_employment_income_before_lsr",
    "farm_operations_income", "rental_income", "farm_rent_income", "partnership_s_corp_income",
)


def own_gross_income(person: dict) -> float:
    total = sum(max(0.0, H.amount(person, key)) for key in _GROSS_INCOME_ITEMS)
    total += sum(max(0.0, H.amount(person, key)) for key in _GROSS_INCOME_NET_ITEMS)
    gains = (
        H.amount(person, "short_term_capital_gains")
        + H.amount(person, "long_term_capital_gains")
        + max(0.0, H.amount(person, "non_sch_d_capital_gains"))
    )
    return total + max(0.0, gains)


@dataclass
class Filer:
    name: str
    age: int
    blind: bool
    wages: float                 # gross wages and salaries, tips and overtime included
    deferral: float              # traditional 401(k) deferral after the 402(g) limit
    roth_deferral: float         # Roth 401(k) deferral after the 402(g) limit
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

    @property
    def filers(self) -> list[Filer]:
        return [self.head] + ([self.spouse] if self.spouse else [])

    def count(self, test) -> int:
        return sum(1 for d in self.dependents if test(d))


def _filer(person: dict, year: int, notes: list) -> Filer:
    wages = H.amount(person, "employment_income")
    traditional = H.amount(person, "traditional_401k_contributions_desired")
    roth = H.amount(person, "roth_401k_contributions_desired")
    limit = S.elective_deferral_limit(year, int(person["age"]))
    scaled_traditional, scaled_roth = S.scale_to_limit([traditional, roth], limit)
    if traditional + roth > limit:
        notes.append(("income_tax", f"{person['name']}: desired 401(k) deferrals above the 402(g) limit, scaled in proportion ({READINGS['desired_contributions']})"))
    if scaled_traditional > wages:
        notes.append(("income_tax", f"{person['name']}: traditional 401(k) deferral above wages, limited to wages"))
        scaled_traditional = max(0.0, wages)
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
        deferral=scaled_traditional,
        roth_deferral=scaled_roth,
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


def build(household: dict, year: int) -> Unit:
    notes: list[tuple[str, str]] = []
    head_person = H.head(household)
    spouse_person = H.spouse(household)
    head = _filer(head_person, year, notes)
    spouse = _filer(spouse_person, year, notes) if spouse_person else None
    filer_people = [head_person] + ([spouse_person] if spouse_person else [])

    limit = QUALIFYING_RELATIVE_INCOME_LIMIT[year]
    dependents, left_out, own_payroll = [], [], []
    for person in H.others(household):
        age = int(person["age"])
        income = own_gross_income(person)
        record = {"name": person["name"], "age": age, "gross_income": income,
                  "disabled": H.flag(person, "is_disabled"),
                  "unmarried_partner": H.flag(person, "is_unmarried_partner_of_household_head")}
        if age < 19:
            record["kind"] = "qualifying_child"
            dependents.append(record)
        elif income < limit:
            record["kind"] = "qualifying_relative"
            dependents.append(record)
        else:
            left_out.append(record)
            notes.append(("income_tax", f"{person['name']} (age {age}, gross income {income:,.0f}) meets neither dependency test of 26 U.S.C. 152 on the stated facts and is not claimed"))
        own_wages = H.amount(person, "employment_income")
        own_se = (
            H.amount(person, "self_employment_income")
            + H.amount(person, "sstb_self_employment_income_before_lsr")
            + H.amount(person, "farm_operations_income")
            + H.amount(person, "partnership_se_income")
        )
        if own_wages > 0 or own_se > 0:
            own_payroll.append({"name": person["name"], "age": age, "wages": own_wages, "self_employment": own_se})
            notes.append(("payroll", f"{person['name']} has earnings of their own: their Social Security and Medicare tax counts in the household's payroll line; their income tax return is outside the board's output"))
        for key in ("taxable_interest_income", "qualified_dividend_income", "long_term_capital_gains",
                    "social_security_retirement", "social_security_disability", "disability_benefits"):
            if H.amount(person, key):
                notes.append(("income_tax", f"{person['name']} has {key} of their own, which is not income of the head's return"))

    if spouse is not None:
        status = S.JOINT
    elif H.flag(head_person, "is_surviving_spouse") and any(d["kind"] == "qualifying_child" for d in dependents):
        status = S.SURVIVING_SPOUSE
    elif any(not d["unmarried_partner"] for d in dependents):
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
    claimed_names = {d["name"] for d in dependents}
    # 26 U.S.C. 213(a): medical care of the taxpayer, the spouse and dependents.
    claimed_people = filer_people + [p for p in H.others(household) if p["name"] in claimed_names]
    for person in H.others(household):
        for key in ("real_estate_taxes", "home_mortgage_interest", "charitable_cash_donations"):
            if H.amount(person, key):
                notes.append(("income_tax", f"{person['name']} states {key}, which is not an expense of the head's return"))
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
        "social_security": sum(total(k) for k in ("social_security_retirement", "social_security_disability", "social_security_survivors", "social_security_dependents")),
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
        # Medical: stated premiums and other medical costs; over-the-counter items are not
        # medical care under 26 U.S.C. 213(b).
        "medical": sum(
            H.amount(p, "other_medical_expenses") + H.amount(p, "health_insurance_premiums_without_medicare_part_b")
            for p in claimed_people
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

    if amounts["disability_benefits"]:
        notes.append(("income_tax", "reading: " + READINGS["disability_benefits"]))
    if amounts["survivor_benefits"]:
        notes.append(("income_tax", "reading: " + READINGS["survivor_benefits"]))
    if amounts["salt_refund"]:
        notes.append(("income_tax", "reading: " + READINGS["salt_refund_income"]))
    if amounts["alimony_received"] or amounts["alimony_paid"]:
        notes.append(("income_tax", "reading: " + READINGS["alimony"]))
    if head.tips or (spouse and spouse.tips):
        notes.append(("income_tax", "reading: " + READINGS["tips"]))
    if amounts["auto_loan_interest"]:
        notes.append(("income_tax", "reading: " + READINGS["auto_loan_interest"]))
    for filer in [head] + ([spouse] if spouse else []):
        if filer.age < 59 and filer.retirement_distributions > 0:
            notes.append(("income_tax", f"reading: {filer.name} is under 59 1/2 with retirement distributions. " + READINGS["retirement_penalty"]))
        if filer.age >= 65 and amounts["medical"] > 0:
            notes.append(("income_tax", "reading: " + READINGS["medicare_part_b"]))
            break
    return Unit(
        case_id=household["id"], year=year, state=household["state"], status=status,
        head=head, spouse=spouse, dependents=dependents, left_out=left_out,
        amounts=amounts, notes=notes, members_with_own_payroll=own_payroll,
    )
