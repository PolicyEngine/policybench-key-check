"""Map a PolicyBench household to Tax-Calculator's inputs.

`row(household, year, shared)` returns the first-pass input row for the head's return.
Three amounts Tax-Calculator takes as given depend on its own adjusted gross income
(the IRA deduction, the student loan interest deduction and the saver's credit), so
`after_pass` adds each from the statute once the pass that fixes its income measure has
run: pass 1 gives MAGI for the IRA deduction; pass 2 (with it) gives MAGI for student
loan interest; pass 3 gives AGI for the saver's credit; pass 4 is the answer.

What each input must hold was read from Tax-Calculator 6.9.0's code (records_variables.json,
calcfunctions.py, records.py); the reading is recorded in the run folder
understand-inputs, unit taxcalc. Where Tax-Calculator has no input for a stated fact that
bears on the four lines, or zeroes one the map sends, the fact is listed in the row's
`unexpressed` notes, with the readings of unstated facts the row rests on (keycheck.unit);
where this map computes an amount the model takes as given it is listed in `map_computed`.
Notes that bear only on itemized deductions (`itemizer_notes`) are added by the runner
only for units Tax-Calculator itemizes in the final pass.

Inputs only the larger draw's facts fill (e03270, e03300, e58990, e24515, e24518,
PT_binc_w2_wages) enter a row only when non-zero, so a board row keeps its columns;
Tax-Calculator reads a missing input as zero.
"""

from __future__ import annotations

from . import statute as S
from . import unit as U

VERSION = "2026-11-10.3"

MARS = {S.SINGLE: 1, S.JOINT: 2, S.SEPARATE: 3, S.HEAD_OF_HOUSEHOLD: 4, S.SURVIVING_SPOUSE: 5}

SHARED_SALT_NOTE = (
    "income_tax: shared assumption: state and local income or sales tax paid is not stated; "
    "the amount PolicyEngine's key uses is passed as e18400"
)


def itemizer_notes(unit: U.Unit, shared: dict | None = None) -> list[str]:
    """Notes that can move Tax-Calculator's answer only when it itemizes (final out_c04470
    > 0: taxcalc/calculator.py zeroes c04470 for a unit that takes the standard deduction)."""
    notes = [f"{group}: {text}" for group, text in unit.itemized_notes]
    if shared and "salt_income_or_sales_tax" in shared:
        notes.append(SHARED_SALT_NOTE)
    return notes


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
        computed.append("income_tax: traditional 401(k) deferrals limited by 26 U.S.C. 402(g) and, with Roth deferrals, to wages")

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
    # e19200 holds mortgage and investment interest (Schedule A lines 8 and 9) as given.
    if a["investment_interest"]:
        computed.append("income_tax: investment interest limited to net investment income (26 U.S.C. 163(d)(1), (4)(B)) and entered with mortgage interest in e19200")

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
    # The shared state and local tax note is added by the runner where Tax-Calculator
    # itemizes (itemizer_notes).
    if "salt_income_or_sales_tax" not in shared and (
        a["real_estate_taxes"] or a["mortgage_interest"] or a["charity_cash"] or a["medical"]
    ):
        unexpressed.append("income_tax: state and local income or sales tax paid is not stated; e18400 is 0")
    if a["employee_expenses"]:
        unexpressed.append("income_tax: Tax-Calculator zeroes unreimbursed employee expenses (e20400; ID_Miscellaneous_hc is 1 in 2025 and 2026)")
    # Capital gain distributions: e01100 holds distributions not reported on Schedule D;
    # with any Schedule D item they go on Schedule D line 13 and net with its gains and
    # losses (Schedule D instructions), so they join p23250.
    schedule_d = bool(a["short_term_gains"] or a["long_term_gains"])
    distributions_on_d = a["capital_gain_distributions"] if schedule_d else 0.0
    if distributions_on_d:
        computed.append("income_tax: capital gain distributions entered on Schedule D (p23250) with the unit's other gains and losses")

    children_ctc = unit.count(lambda d: d["kind"] == "qualifying_child" and d["age"] < 17)
    children_eitc = unit.count(lambda d: d["kind"] == "qualifying_child")
    care_persons = unit.count(lambda d: d["age"] < 13)
    # f2441: the care credit's qualifying individuals (26 U.S.C. 21(b)(1); unit.care_individuals),
    # which Tax-Calculator caps at two; on the board, the dependents under 13.
    for name, stated, deemed in U.deemed_earnings_short(unit):
        unexpressed.append(f"income_tax: Tax-Calculator has no deemed earned income for a spouse incapable of self-care (26 U.S.C. 21(d)(2)): it limits the care credit by {name}'s stated earnings, {stated:,.0f}, where the statute deems {deemed:,.0f}")
    if a["se_health_insurance"]:
        computed.append("income_tax: self-employed health insurance deduction limited by 26 U.S.C. 162(l)(2)(A) to earned income of 401(c)(2) from the business, entered as e03270")
    if a["se_pension"]:
        computed.append("income_tax: self-employed pension contributions limited to the 415(c)(1)(A) amount and Schedule C income, as the key does, entered as e03300 (reading: " + U.READINGS["se_pension"] + ")")
    # The Form 4952 election: Tax-Calculator's Schedule D tax worksheet takes it from
    # qualified dividends only (line 4, Form 4952 line 4e, is 0: calcfunctions.py GainsTax).
    elected_gain = max(0.0, a["form_4952_elected"] - a["qualified_dividends"])
    if elected_gain:
        unexpressed.append(f"income_tax: Tax-Calculator takes the Form 4952 election from qualified dividends only (its Schedule D tax worksheet sets line 4, Form 4952 line 4e, to 0): {elected_gain:,.0f} of elected net capital gain keeps the preferential rates (26 U.S.C. 1(h)(3), 163(d)(4)(B)(iii))")
    # 199A(b)(2)(B) wages: Tax-Calculator takes one wage pool for the unit's one kind of
    # business (PT_SSTB_income); policyengine-us splits a person's total by
    # sstb_w2_wages_from_qualified_business only when the person has both kinds.
    if sstb > 0 and other_qbi > 0:
        sstb_selected = sstb >= other_qbi
        w2_wages = a["sstb_qbi_w2_wages"] if sstb_selected else max(0.0, a["qbi_w2_wages"] - a["sstb_qbi_w2_wages"])
        if a["qbi_w2_wages"]:
            computed.append("income_tax: W-2 wages of the qualified businesses (PT_binc_w2_wages) are those of the kind of business PT_SSTB_income selects")
    else:
        w2_wages = a["qbi_w2_wages"]
    out = {
        "MARS": MARS[unit.status],
        "XTOT": len(unit.filers) + len(unit.dependents),
        "n24": children_ctc,
        "EIC": min(3, children_eitc),
        "nu06": unit.count(lambda d: d["age"] < 6),
        "nu13": care_persons,
        "nu18": unit.count(lambda d: d["age"] < 18),
        "f2441": len(unit.care_individuals),
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
        "e01100": a["capital_gain_distributions"] - distributions_on_d,
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
        "p23250": a["long_term_gains"] + distributions_on_d,
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
        "e19200": mortgage + a["investment_interest_allowed"],
        "e19800": a["charity_cash"],
        "e20100": a["charity_non_cash"],
        "e20400": a["employee_expenses"],
        "e32800": a["child_care"],
        "PT_SSTB_income": int(sstb > 0 and sstb >= other_qbi),
        "PT_ubia_property": a["ubia"] + (a["sstb_ubia"] if sstb > 0 else 0.0),
        "overtime_income": sum(f.overtime_premium for f in unit.filers),
        # unit.READINGS["tips"]: stated tips are not qualified tips (occupation unstated).
        "tip_income": 0.0,
        # Qualified passenger vehicle loan interest (26 U.S.C. 163(h)(4)): Tax-Calculator
        # applies the cap and phase-out itself (calcfunctions.py:1003-1017). The board's
        # own auto_loan_interest is not qualified (unit.READINGS["auto_loan_interest"]).
        "auto_loan_interest": a["qualified_vehicle_loan_interest"],
    }
    # Sent only when non-zero (module docstring).
    draw_inputs = {
        "e03270": a["se_health_insurance"],
        "e03300": a["se_pension"],
        "e58990": a["form_4952_elected"],
        "e24515": a["unrecaptured_1250"],
        "e24518": a["collectibles_28"],
        "PT_binc_w2_wages": w2_wages,
    }
    out.update({name: value for name, value in draw_inputs.items() if value})
    return out, unit, unexpressed, computed


def _compensation(filer: U.Filer) -> float:
    """26 U.S.C. 219(f)(1): wages in gross income plus net self-employment earnings less the
    deduction for half of self-employment tax (the wage-base cap is ignored: it cannot bind
    at the amounts where compensation limits a contribution)."""
    net = filer.self_employment
    half_se_tax = 0.5 * 0.153 * 0.9235 * net if net * 0.9235 >= 400 else 0.0
    # 401(c)(2)(A)(v): earned income is also net of the self-employed pension deduction
    # (policyengine-us ira_compensation.py subtracts it too).
    return max(0.0, filer.wages - filer.deferral) + max(0.0, net - half_se_tax - filer.se_pension)


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
        # Self-employed pension contributions count as the key counts them
        # (unit.READINGS["se_pension"]; zero on the board).
        saved = [
            sum(contributions[f.name]) + f.deferral + f.roth_deferral + f.se_pension for f in eligible
        ]
        distributions = [f.retirement_distributions for f in eligible]
        credit = S.savers_credit(unit.year, unit.status, agi, saved, distributions)
        row["e07240"] = credit
        if credit:
            computed.append("income_tax: saver's credit figured under 26 U.S.C. 25B before the limit to tax (reading: " + U.READINGS["savers_credit"] + ")")
    return row


def member_row(member: dict, year: int) -> dict:
    """A separate return for a listed member with earnings of their own, used only for
    that member's Social Security, Medicare and self-employment tax."""
    return {
        "MARS": 1, "XTOT": 0, "DSI": 1, "age_head": member["age"],
        "e00200p": member["wages"], "e00200": member["wages"],
        "e00900p": member["self_employment"], "e00900": member["self_employment"],
    }
