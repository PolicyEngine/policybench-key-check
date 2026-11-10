"""Map a PolicyBench household to Tax-Calculator's inputs.

`row(household, year, shared)` returns the first-pass input row for the head's return.
Three amounts Tax-Calculator takes as given depend on its own adjusted gross income
(the IRA deduction, the student loan interest deduction and the saver's credit), so
`after_pass` adds each from the statute once the pass that fixes its income measure has
run: pass 1 gives MAGI for the IRA deduction; pass 2 (with it) gives MAGI for student
loan interest; pass 3 gives AGI for the saver's credit; pass 4 is the answer.

What each input must hold was read from Tax-Calculator 6.9.0's code (records_variables.json,
calcfunctions.py, records.py); the reading is recorded in the run folder
understand-inputs, unit taxcalc. Where Tax-Calculator has no input for a stated fact the
fact is listed in the row's `unexpressed` notes; where this map computes an amount the
model takes as given it is listed in `map_computed`.
"""

from __future__ import annotations

from . import statute as S
from . import unit as U

VERSION = "2026-11-10.1"

MARS = {S.SINGLE: 1, S.JOINT: 2, S.SEPARATE: 3, S.HEAD_OF_HOUSEHOLD: 4, S.SURVIVING_SPOUSE: 5}


def row(household: dict, year: int, shared: dict | None = None):
    """Return (row, unit, unexpressed, map_computed) for the first pass."""
    shared = shared or {}
    unit = U.build(household, year)
    a = unit.amounts
    head, spouse = unit.head, unit.spouse
    unexpressed = [f"{group}: {text}" for group, text in unit.notes]
    computed: list[str] = []

    def per_filer(get):
        return get(head), (get(spouse) if spouse else 0.0)

    # Wages: e00200 is box 1 wages (net of pre-tax deferrals); pencon is the deferral,
    # which Tax-Calculator adds back for FICA and Additional Medicare Tax only.
    wages_p, wages_s = per_filer(lambda f: max(0.0, f.wages - f.deferral))
    pencon_p, pencon_s = per_filer(lambda f: f.deferral)
    sched_c_p, sched_c_s = per_filer(lambda f: f.schedule_c)
    sched_f_p, sched_f_s = per_filer(lambda f: f.schedule_f)
    k1_p, k1_s = per_filer(lambda f: f.partnership_se)
    if head.deferral or (spouse and spouse.deferral):
        computed.append("income_tax: traditional 401(k) deferrals limited by 26 U.S.C. 402(g) and to wages")

    dividends = a["qualified_dividends"] + a["non_qualified_dividends"]
    taxable_pensions = a["taxable_pensions"]
    # Tax-Calculator has no line for other taxable income. e01200 (Form 4797 gains) enters
    # adjusted gross income and nothing else, so it carries the two stated items that are
    # taxable and belong to no other input.
    other_income = a["miscellaneous"] + a["disability_benefits"]
    if a["miscellaneous"]:
        unexpressed.append("income_tax: no Tax-Calculator input for miscellaneous income; entered through e01200, which enters AGI only")
    if a["disability_benefits"]:
        unexpressed.append("income_tax: no Tax-Calculator input for taxable disability benefits; entered through e01200, which enters AGI only")
    schedule_e = a["rental"] + a["farm_rent"] + a["partnership_s_corp"] + a["estate"]

    educator = S.educator_expense_deduction(year, [f.educator_expense for f in unit.filers])
    if any(f.educator_expense for f in unit.filers):
        computed.append("income_tax: educator expenses limited by 26 U.S.C. 62(a)(2)(D)")
    mortgage = S.deductible_mortgage_interest(year, unit.status, a["mortgage_interest"], a["mortgage_balances"])
    if a["mortgage_interest"] and mortgage != a["mortgage_interest"]:
        computed.append("income_tax: mortgage interest limited by 26 U.S.C. 163(h)(3)(F)")

    sstb = sum(f.sstb for f in unit.filers)
    other_qbi = (
        sum(f.schedule_c - f.sstb + f.schedule_f for f in unit.filers)
        + a["partnership_s_corp"] + a["farm_rent"]
    )
    if sstb > 0 and other_qbi > 0:
        unexpressed.append("income_tax: Tax-Calculator marks all of a unit's business income as a specified service trade or not; this unit has both")
    if a["reit_ptp"]:
        unexpressed.append("income_tax: no Tax-Calculator input for qualified REIT dividends and PTP income (26 U.S.C. 199A(b)(1)(B))")
    if a["alimony_received"] or a["alimony_paid"]:
        unexpressed.append("income_tax: Tax-Calculator gives alimony no effect in 2025 or 2026 (every instrument treated as post-2018)")
    if a["domestic_production"]:
        unexpressed.append("income_tax: Tax-Calculator zeroes the domestic production activities deduction (repealed for years after 2017)")
    if "salt_income_or_sales_tax" in shared:
        unexpressed.append("income_tax: shared assumption: state and local income or sales tax paid is not stated; the amount PolicyEngine's key uses is passed as e18400")
    elif a["real_estate_taxes"] or a["mortgage_interest"] or a["charity_cash"] or a["medical"]:
        unexpressed.append("income_tax: state and local income or sales tax paid is not stated; e18400 is 0")

    children_ctc = unit.count(lambda d: d["kind"] == "qualifying_child" and d["age"] < 17)
    children_eitc = unit.count(lambda d: d["kind"] == "qualifying_child")
    care_persons = unit.count(lambda d: d["age"] < 13)
    out = {
        "MARS": MARS[unit.status],
        "XTOT": len(unit.filers) + len(unit.dependents),
        "n24": children_ctc,
        "EIC": min(3, children_eitc),
        "nu06": unit.count(lambda d: d["age"] < 6),
        "nu13": care_persons,
        "nu18": unit.count(lambda d: d["age"] < 18),
        "f2441": care_persons,
        "DSI": 0,
        "age_head": head.age,
        "age_spouse": spouse.age if spouse else 0,
        "blind_head": int(head.blind),
        "blind_spouse": int(spouse.blind) if spouse else 0,
        "e00200p": wages_p, "e00200s": wages_s, "e00200": wages_p + wages_s,
        "pencon_p": pencon_p, "pencon_s": pencon_s,
        "e00300": a["taxable_interest"],
        "e00400": a["tax_exempt_interest"],
        "e00600": dividends,
        "e00650": a["qualified_dividends"],
        "e00700": a["salt_refund"],
        "e00800": a["alimony_received"],
        "e00900p": sched_c_p, "e00900s": sched_c_s, "e00900": sched_c_p + sched_c_s,
        "e01100": a["capital_gain_distributions"],
        "e01200": other_income,
        "e01400": a["taxable_ira_distributions"],
        "e01500": taxable_pensions + a["tax_exempt_pensions"],
        "e01700": taxable_pensions,
        "e02000": schedule_e,
        "e26270": a["partnership_s_corp"],
        "e27200": a["farm_rent"],
        "k1bx14p": k1_p, "k1bx14s": k1_s,
        "e02100p": sched_f_p, "e02100s": sched_f_s, "e02100": sched_f_p + sched_f_s,
        "e02300": a["unemployment"],
        "e02400": a["social_security"],
        "p22250": a["short_term_gains"],
        "p23250": a["long_term_gains"],
        "e03150": 0.0,
        "e03210": 0.0,
        "e03220": educator,
        "e03240": a["domestic_production"],
        "e03290": a["hsa_deduction"],
        "e03500": a["alimony_paid"],
        "e07240": 0.0,
        "e17500": a["medical"],
        "e18400": float(shared.get("salt_income_or_sales_tax", 0.0)),
        "e18500": a["real_estate_taxes"],
        "e19200": mortgage,
        "e19800": a["charity_cash"],
        "e20100": a["charity_non_cash"],
        "e20400": a["employee_expenses"],
        "e32800": a["child_care"],
        "PT_SSTB_income": int(sstb > 0 and sstb >= other_qbi),
        "PT_ubia_property": a["ubia"] + (a["sstb_ubia"] if sstb > 0 else 0.0),
        "overtime_income": sum(f.overtime_premium for f in unit.filers),
        "tip_income": sum(f.tips for f in unit.filers),
        "auto_loan_interest": 0.0,
    }
    return out, unit, unexpressed, computed


def _compensation(filer: U.Filer) -> float:
    """26 U.S.C. 219(f)(1): wages in gross income plus net self-employment earnings less the
    deduction for half of self-employment tax (the wage-base cap is ignored: it cannot bind
    at the amounts where compensation limits a contribution)."""
    net = filer.self_employment
    half_se_tax = 0.5 * 0.153 * 0.9235 * net if net * 0.9235 >= 400 else 0.0
    return max(0.0, filer.wages - filer.deferral) + max(0.0, net - half_se_tax)


def ira_contributions(unit: U.Unit) -> dict[str, tuple[float, float]]:
    """Each filer's (traditional, Roth) IRA contribution after 26 U.S.C. 219(b) and (c)."""
    comp = {f.name: _compensation(f) for f in unit.filers}
    out = {}
    # The higher earner first, so the lower earner's spousal limit can use what is left.
    ordered = sorted(unit.filers, key=lambda f: -comp[f.name])
    used = 0.0
    for index, filer in enumerate(ordered):
        available = comp[filer.name]
        if unit.status == S.JOINT and index == 1:
            # 219(c): the lower earner may use the couple's compensation less the other
            # spouse's contributions.
            available = max(available, comp[ordered[0].name] + comp[filer.name] - used)
        limit = S.ira_contribution_limit(unit.year, filer.age, available)
        traditional, roth = S.scale_to_limit([filer.ira_traditional_desired, filer.ira_roth_desired], limit)
        out[filer.name] = (traditional, roth)
        used += traditional + roth
    return out


def after_pass(pass_number: int, row: dict, unit: U.Unit, agi: float, computed: list[str]) -> dict:
    """Add the amount whose income measure the pass just fixed. Returns the next row."""
    row = dict(row)
    contributions = ira_contributions(unit)
    if pass_number == 1:
        # 26 U.S.C. 219(g)(3)(A): MAGI is AGI without the IRA deduction and the student
        # loan interest deduction; taxable Social Security is figured without them too.
        deduction = 0.0
        for filer in unit.filers:
            traditional, _ = contributions[filer.name]
            if traditional <= 0:
                continue
            other = [f for f in unit.filers if f is not filer]
            limit = S.ira_deductible_limit(
                unit.year, unit.status, filer.age, agi, filer.active_participant,
                bool(other and other[0].active_participant),
            )
            deduction += min(traditional, limit)
        row["e03150"] = deduction
        if any(c[0] > 0 for c in contributions.values()):
            computed.append("income_tax: IRA deduction figured under 26 U.S.C. 219(b), (c) and (g)")
    elif pass_number == 2:
        # 26 U.S.C. 221(b)(2)(C): MAGI is AGI without the student loan interest deduction.
        interest = unit.amounts["student_loan_interest"]
        row["e03210"] = S.student_loan_interest_deduction(unit.year, unit.status, interest, agi)
        if interest:
            computed.append("income_tax: student loan interest deduction figured under 26 U.S.C. 221")
    elif pass_number == 3:
        eligible = [f for f in unit.filers if f.age >= 18]
        saved = [
            sum(contributions[f.name]) + f.deferral + f.roth_deferral for f in eligible
        ]
        distributions = [f.retirement_distributions for f in eligible]
        credit = S.savers_credit(unit.year, unit.status, agi, saved, distributions)
        row["e07240"] = credit
        if credit:
            computed.append("income_tax: saver's credit figured under 26 U.S.C. 25B before the limit to tax")
    return row


def member_row(member: dict, year: int) -> dict:
    """A separate return for a listed member with earnings of their own, used only for
    that member's Social Security, Medicare and self-employment tax."""
    return {
        "MARS": 1, "XTOT": 0, "DSI": 1, "age_head": member["age"],
        "e00200p": member["wages"], "e00200": member["wages"],
        "e00900p": member["self_employment"], "e00900": member["self_employment"],
    }
