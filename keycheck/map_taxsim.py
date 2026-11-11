"""Map a PolicyBench household to NBER TAXSIM's inputs (build cd2026110117).

NBER publishes no source, so what each input does was established from NBER's pages and
by probing the binary (run folder understand-inputs, unit taxsim; probe files under
probes/taxsim/). The facts this map rests on, each with its probe:

- Dependents. With `age1..` the build's 2026 EITC is wrong for one to three children and
  its 2026 child care credit is zero; with counts (`depx`, `dep13`, `dep17`, `dep18`) the
  2026 EITC matches Rev. Proc. 2025-32 (probes P3, P4). So 2026 uses counts and 2025 uses
  ages. On the counts path the child tax credit goes to every `dep18` child and the EITC
  counts at most three (P3.3, P3.6); the EITC depends on `dep18` only and the child,
  other-dependent and child care credits not on the EITC (verify-map-taxsim F7). So the
  first record sends `dep18` = the children under 17 (the law's $2,200 and $500 split) and,
  where the EITC children differ in number (a qualifying child aged 17 or over, with
  fewer than three under 17), a second record sends `dep18` = the EITC children for the
  EITC alone (`eitc_record`). On the ages path a 17-year-old gets $2,200 and an 18-year-old
  the $500 credit and EITC-child treatment (P2.2, P2.4), so a qualifying child aged 17 or
  over is sent as 18 (probe vmt_age17_as_18_2025).
- `otherprop` is ignored from 2024 on (P6.1), so rent and estate income go to `intrec`,
  either sign (a negative amount is accepted: probes vmt_negative_intrec and
  fixmaps_negative_intrec), which is ordinary income, net investment income and EITC
  investment income; rent is not qualified business income (unit.READINGS["rental_qbi"]).
- `nonprop` counts as earned income for the EITC (P6.8, P7.1), so other taxable income
  goes to `pensions` (ordinary income and nothing else); adjustments to income have no
  other home and go to `nonprop` as negative amounts, as NBER's page says.
- Wages are entered gross (FICA wages, 26 U.S.C. 3121(v)(1)(A)), so self-employment tax
  and the wage base see them as the law does, and traditional 401(k) deferrals enter as
  negative `nonprop`, which lowers AGI and EITC earned income (deferrals are not
  includible in gross income, 32(c)(2)(A)(i)) but not FICA (probe vmt_deferral_wage_base).
  One record then gives income tax and payroll tax; a second, with the self-employment
  boxes zeroed, splits `tfica` (`payroll_records`).
- `psemp` carries self-employment tax and gets the qualified business income deduction
  (P6.4, P6.5); `scorp` gets the deduction with no self-employment tax; `pprofinc` is a
  specified service business.
- Only `proptax` (and TAXSIM's own state tax) is held to the SALT cap; `otheritem` is
  not (P9.2). `mortgage` is deducted as given (P9.3). With `state` 0 the build itemizes
  when itemized deductions exceed the standard deduction, and v17 > 0 marks an
  itemizer (P9.4). The SALT cap is the build's own; the map does not set it by option.
- No input exists for blindness, a qualifying surviving spouse, pre-tax contributions,
  overtime, vehicle-loan interest, tax-exempt interest, charitable gifts by a
  non-itemizer, or the saver's credit (P1); each is listed in `unexpressed` when the
  household states it.
- Facts only the larger draw states (run causes-and-draw, unit draw-maps, with its probes
  D1-D3 of build cd2026110117): the self-employed health insurance and pension deductions
  go to negative `nonprop`, which this build subtracts from EITC earned income (D1b) but
  not from qualified business income (D1c); investment interest after 163(d) goes to
  `mortgage`; a Form 4952 election moves the elected net capital gain, then qualified
  dividends, to `intrec`. No input exists for the 25% and 28% rate gains, a care
  qualifying individual aged 13 or over, or the deemed earned income of an incapable
  spouse. `mstat` 6 (married filing separately) takes the separate schedule (D2b) but
  files a separate filer with a dependent as head of household (D2c-D2d). The ages path
  counts `age9` and `age10` (D3: ten children get ten child credits in 2025). A loss in
  `psemp` does not offset earnings in `pprofinc` for self-employment tax, nor the reverse
  (D4, as P7.4 found for `pbusinc`); AGI does net them. Three draw filers, and no board
  filer, have opposite signs there; each gets a note. The build has no $400 floor on
  self-employment tax (P10.3); a filer or member whose net earnings fall under it gets a
  note when the build's charge would reach the $1 tolerance. The build's 2026 zero rate on
  long-term gains and qualified dividends runs past Rev. Proc. 2025-32's end (D6a, D6g;
  `ZERO_RATE_END_2026`); a single or joint unit with gains in between gets a note.

`first_pass(household, year, shared)` returns the first-pass record. Like the
Tax-Calculator map, later passes add the amounts that depend on TAXSIM's own adjusted
gross income. `final_notes` adds the notes that depend on TAXSIM's final answer
(itemizing, taxable income above the 199A threshold).
"""

from __future__ import annotations

from . import map_taxcalc
from . import statute as S
from . import unit as U

VERSION = "2026-11-10.3"

# 26 U.S.C. 213(a): medical expenses above 7.5% of AGI. 26 U.S.C. 170(b)(1)(I): from
# 2026 charitable gifts count only above 0.5% of AGI.
MEDICAL_FLOOR = 0.075
CHARITY_FLOOR = {2026: 0.005, 2025: 0.0}

# The 2026 zero rate on net capital gain and qualified dividends (26 U.S.C. 1(h), 1(j)(5)):
# Rev. Proc. 2025-32 ends it at 49,450 for a single filer and 98,900 on a joint return
# (sources/irs/rp-25-32.txt:547, :554); this build ends it at 49,899.33 and 99,798.6
# (probes D6a: taxable income 50,000 of long-term gain gives 15.10; D6g: 100,000 joint gives
# 30.21). Heads of household are not probed and get no note.
ZERO_RATE_END_2026 = {S.SINGLE: (49_450.0, 49_899.33), S.JOINT: (98_900.0, 99_798.6)}

SHARED_SALT_NOTE = (
    "income_tax: shared assumption: state and local income or sales tax paid is not stated; "
    "the amount PolicyEngine's key uses is entered with real estate taxes in `proptax`, and "
    "TAXSIM's own state calculation is off (`state` 0)"
)


def credit_counts(unit: U.Unit) -> tuple[int, int, int]:
    """(children under 17, EITC qualifying children, children under 13)."""
    return (
        unit.count(lambda d: d["kind"] == "qualifying_child" and d["age"] < 17),
        unit.count(lambda d: d["kind"] == "qualifying_child"),
        unit.count(lambda d: d["age"] < 13),
    )


def needs_eitc_record(unit: U.Unit) -> bool:
    """2026 counts path: does the EITC need its own record? It does when the EITC children
    (at most three count) differ in number from the children under 17, which the first
    record sends in `dep18` for the child credit: a qualifying child aged 17 or over with
    fewer than three children under 17."""
    if unit.year < 2026:
        return False
    ctc, eitc, _ = credit_counts(unit)
    return min(3, eitc) != min(3, ctc)


def eitc_record(record: dict, unit: U.Unit) -> dict:
    """The second final record: `dep18` = the EITC children (at most three), for the EITC
    (v25) alone. TAXSIM's EITC depends on `dep18` only (verify-map-taxsim F7)."""
    ctc, eitc, care = credit_counts(unit)
    second = dict(record)
    second["dep18"] = min(3, eitc)
    second["dep17"] = min(ctc, second["dep18"])
    second["dep13"] = min(care, second["dep17"])   # the build requires dep13 <= dep17 <= dep18
    return second


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

    # Gross wages; the deferrals ride in negative `nonprop` (module docstring).
    wages_p, wages_s = per_filer(lambda f: f.wages)
    deferrals = sum(f.deferral for f in unit.filers)
    # A partner's self-employment earnings are part of the partnership income, not more
    # income: they move from `scorp` to the self-employment box.
    se_p, se_s = per_filer(lambda f: f.schedule_c - f.sstb + f.schedule_f + f.partnership_se)
    sstb_p, sstb_s = per_filer(lambda f: f.sstb)
    # A loss in one self-employment box does not offset earnings in the other (probes
    # P7.4 and D4); no board filer has opposite signs there, some draw filers do.
    for filer, se, sstb in ((head, se_p, sstb_p), (spouse, se_s, sstb_s)):
        if filer is not None and (se < 0 < sstb or sstb < 0 < se):
            loss, gain = min(se, sstb), max(se, sstb)
            where = "`psemp` or `ssemp`" if se < 0 else "`pprofinc` or `sprofinc`"
            unexpressed.append(
                f"self_employment: {filer.name}'s self-employment loss of {loss:,.0f} goes to {where} and their earnings of {gain:,.0f} to the other box; "
                "this build does not net a loss in one box against earnings in the other for self-employment tax (probes P7.4 and D4: "
                "`psemp` -10,000 beside `pprofinc` 20,000 gives the self-employment tax of 20,000), where the law's net earnings from "
                "self-employment combine the individual's businesses and a partner's distributive share of income or loss (26 U.S.C. 1402(a))")
            unexpressed.append(
                f"income_tax: {filer.name}'s self-employment loss in one TAXSIM box does not offset earnings in the other for self-employment tax "
                "(probes P7.4 and D4), so the deduction for half of it (26 U.S.C. 164(f)) is too large and AGI too small (probe D4: AGI 8,587.05 "
                "for `psemp` -10,000 beside `pprofinc` 20,000, against 9,293.52 for `psemp` 10,000 alone)")
    # Net earnings under $400 bear no self-employment tax (26 U.S.C. 1402(b)(2)); this build
    # has no such floor (probe P10.3). The note fires where the build's charge at the full
    # 15.3% would reach the $1 tolerance; below that the lines agree (one board head states
    # $1 of self-employment income, a charge of 0.14, and gets no note).
    under_floor = [(f.name, se + sstb) for f, se, sstb in ((head, se_p, sstb_p), (spouse, se_s, sstb_s))
                   if f is not None and se >= 0 and sstb >= 0]
    under_floor += [(m["name"], m["self_employment"]) for m in unit.members_with_own_payroll]
    for name, profit in under_floor:
        earnings = S.SE_NET_EARNINGS_SHARE * profit
        if earnings < S.SE_FLOOR and earnings * (S.SE_OASDI_RATE + S.SE_HI_RATE) >= 1:
            unexpressed.append(
                f"self_employment: {name}'s net earnings from self-employment ({earnings:,.2f}) are under $400, so the law charges "
                "no self-employment tax on them (26 U.S.C. 1402(b)(2)); this build has no $400 floor and charges it (probe P10.3: "
                "`psemp` 300 gives 42.39, 15.3% of 277.05)")
    partnership_se = sum(f.partnership_se for f in unit.filers)
    passive_business = a["partnership_s_corp"] - partnership_se + a["farm_rent"]
    # Rent and estate income, either sign, to `intrec`: not qualified business income
    # (unit.READINGS["rental_qbi"]); the build accepts a negative amount there.
    property_income = a["rental"] + a["estate"]
    educator = S.educator_expense_deduction(year, [f.educator_expense for f in unit.filers])
    if any(f.educator_expense for f in unit.filers):
        computed.append("income_tax: educator expenses limited by 26 U.S.C. 62(a)(2)(D)")
    # Other taxable income goes to `pensions`; TAXSIM rejects a negative pension, so a net
    # loss there goes to `nonprop`.
    other_income = a["miscellaneous"] + a["disability_benefits"] + a["salt_refund"]
    if deferrals:
        computed.append("income_tax: traditional 401(k) deferrals limited by 26 U.S.C. 402(g) and, with Roth deferrals, to wages; TAXSIM has no input for them, so wages are entered gross and the deferrals as negative `nonprop`, which lowers AGI and EITC earned income (deferrals are not includible in gross income)")

    # 26 U.S.C. 163(d)(4)(B): the elected net capital gain, then qualified dividends (the
    # order policyengine-us's net_capital_gain uses), become ordinary income.
    long_term = a["long_term_gains"] + a["capital_gain_distributions"]
    elected = a["form_4952_elected"]
    elected_gain = min(elected, S.net_capital_gain(a["short_term_gains"], long_term))
    elected_dividends = elected - elected_gain
    if elected:
        computed.append("income_tax: the Form 4952 election (26 U.S.C. 163(d)(4)(B)) is entered by moving the elected net capital gain, then qualified dividends, to `intrec`, ordinary income: TAXSIM has no input for it")
    se_adjustments = a["se_health_insurance"] + a["se_pension"]

    record = {
        "year": year,
        "state": 0,
        "mstat": {S.JOINT: 2, S.SEPARATE: 6}.get(unit.status, 1),
        "page": head.age,
        "sage": spouse.age if spouse else 0,
        "pwages": wages_p, "swages": wages_s,
        "psemp": se_p, "ssemp": se_s,
        "pprofinc": sstb_p, "sprofinc": sstb_s,
        "scorp": passive_business,
        "dividends": a["qualified_dividends"] - elected_dividends,
        "intrec": a["taxable_interest"] + a["non_qualified_dividends"] + property_income + elected,
        "stcg": a["short_term_gains"],
        "ltcg": long_term - elected_gain,
        "pensions": a["taxable_pensions"] + a["taxable_ira_distributions"] + max(0.0, other_income),
        "gssi": a["social_security"],
        "pui": a["unemployment"],
        # Deferrals and the adjustments that do not depend on AGI; the IRA and student
        # loan deductions join them in later passes.
        "nonprop": -(deferrals + educator + a["hsa_deduction"] + se_adjustments) + min(0.0, other_income),
        "proptax": a["real_estate_taxes"] + float(shared.get("salt_income_or_sales_tax", 0.0)),
        "mortgage": 0.0,
        "childcare": a["child_care"],
    }
    if spouse is None:
        for name in ("swages", "ssemp", "sprofinc", "sage"):
            record[name] = 0

    # Dependents.
    children_ctc, children_eitc, children_care = credit_counts(unit)
    record["depx"] = len(unit.dependents)
    if year >= 2026:
        # The build gives the $2,200 credit to `dep18` children (P3.3): this record sends
        # the children under 17 there; the EITC, where its children differ, comes from
        # eitc_record.
        record["dep13"] = min(children_care, children_ctc)
        record["dep17"] = children_ctc
        record["dep18"] = children_ctc
        if needs_eitc_record(unit):
            computed.append("income_tax: the EITC comes from a second TAXSIM record with `dep18` = the EITC children (at most three); the tax before refundable credits and the refundable child credit come from the first, with `dep18` = the children under 17 (this build gives the $2,200 credit to every `dep18` child)")
        if a["child_care"] and children_care:
            unexpressed.append("income_tax: this build computes the 2026 child care credit at the pre-2026 rates (probe P5)")
    else:
        # A qualifying child aged 17 or over (a 17- or 18-year-old, or a disabled adult
        # under unit.READINGS["is_disabled"]) is sent as 18: the build gives an 18-year-old
        # the $500 credit and EITC-child treatment, the law's treatment (24(c)(1),
        # 152(c)(3)); a 17-year-old would get $2,200 (probes P2.2, P2.4, vmt_age17_as_18_2025).
        ages = sorted(
            18 if d["kind"] == "qualifying_child" and d["age"] >= 17 else max(1, d["age"])
            for d in unit.dependents
        )[:10]
        for index, age in enumerate(ages, start=1):
            record[f"age{index}"] = age
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
    if a["tax_exempt_interest"]:
        unexpressed.append("income_tax: TAXSIM has no input for tax-exempt interest (Social Security provisional income, EITC investment income)")
    if a["tax_exempt_pensions"]:
        unexpressed.append("income_tax: TAXSIM has no input for nontaxable pensions (credit for the elderly or disabled)")
    if a["reit_ptp"]:
        unexpressed.append("income_tax: TAXSIM has no input for qualified REIT dividends and PTP income")
    if a["rental"] or a["estate"]:
        text = "income_tax: this build ignores `otherprop` from 2024, so rent and estate income are entered as `intrec`"
        if property_income < 0:
            text += "; a net loss there also offsets interest in this build's EITC investment-income test (probe fixmaps_negative_intrec), where the law counts rents only as an excess (26 U.S.C. 32(i)(2)(C))"
        unexpressed.append(text)
    if passive_business:
        text = "income_tax: partnership, S corporation and farm rent income are entered as `scorp`, which this build counts as net investment income and EITC investment income"
        if passive_business < 0:
            text += "; a loss there also offsets other investment income in the EITC test and other qualified business income (probe vmt_box_side_effects ids 7, 12)"
        unexpressed.append(text)
    if a["miscellaneous"] or a["disability_benefits"] or a["salt_refund"]:
        text = "income_tax: other taxable income (miscellaneous income, taxable disability benefits, a taxable state refund) is entered as `pensions`: `nonprop` would count as EITC earned income"
        if other_income < 0:
            text += "; a net loss goes to `nonprop`, which also lowers EITC earned income"
        unexpressed.append(text)
    if a["alimony_received"] or a["alimony_paid"]:
        unexpressed.append("income_tax: alimony is left out (treated as a post-2018 instrument)")
    if unit.status == S.SEPARATE and unit.dependents:
        unexpressed.append("income_tax: this build files a separate filer (`mstat` 6) with a dependent as head of household (draw-maps probes D2c-D2d)")
    if se_adjustments:
        unexpressed.append("income_tax: the self-employed health insurance and pension deductions are entered as negative `nonprop`; this build also subtracts them from EITC earned income (probes P7.1, D1b), which is net earnings from self-employment in the law (26 U.S.C. 32(c)(2)(A)(ii); 162(l)(4) for the health deduction; for the pension deduction as read here, since it is not a deduction of the business), and does not subtract them from qualified business income (probe D1c), as Tax-Calculator and policyengine-us do")
    if a["unrecaptured_1250"] or a["collectibles_28"]:
        unexpressed.append("income_tax: TAXSIM has no input for unrecaptured section 1250 gain or 28-percent rate gain (26 U.S.C. 1(h)(1)(E)-(F), (h)(4), (h)(6)); the whole long-term gain gets the 0, 15 and 20 percent rates")
    adults_in_care = [c["name"] for c in unit.care_individuals if c["why"] != "under 13"]
    if a["child_care"] and adults_in_care:
        unexpressed.append(f"income_tax: TAXSIM counts only children under 13 for the care credit; {', '.join(adults_in_care)} (a qualifying individual incapable of self-care, 26 U.S.C. 21(b)(1)(B)-(C)) cannot be entered")
    for name, stated, deemed in U.deemed_earnings_short(unit):
        unexpressed.append(f"income_tax: TAXSIM has no deemed earned income for a spouse incapable of self-care (26 U.S.C. 21(d)(2)): {name}'s stated earnings are {stated:,.0f}, where the statute deems {deemed:,.0f}")
    if a["domestic_production"]:
        unexpressed.append("income_tax: the domestic production activities deduction is left out (repealed for years after 2017)")
    if year >= 2026 and a["charity_cash"]:
        unexpressed.append("income_tax: TAXSIM has no charitable deduction for non-itemizers (26 U.S.C. 170(p), from 2026)")
    # 26 U.S.C. 199A(i): the 2026 minimum deduction needs $1,000 of qualified business
    # income from active trades in which the taxpayer materially participates; `scorp`
    # (passive partnership, S corporation and farm rent income) is left out of the test.
    active_qbi = se_p + se_s + sstb_p + sstb_s
    if year >= 2026 and active_qbi >= 1_000:
        unexpressed.append("income_tax: this build has no 2026 minimum qualified business income deduction (26 U.S.C. 199A(i))")
    return record, unit, unexpressed, computed


def final_notes(record: dict, unit: U.Unit, out: dict, shared: dict | None = None) -> list[str]:
    """Notes that depend on TAXSIM's final answer `out` for this unit."""
    notes = []
    if out.get("v17", 0.0) > 0:   # TAXSIM itemizes (P9.4)
        notes += [f"{group}: {text}" for group, text in unit.itemized_notes]
        if shared and "salt_income_or_sales_tax" in shared:
            notes.append(SHARED_SALT_NOTE)
    # The W-2 wage and property limit can only cut a deduction on positive business income.
    business = sum(record.get(k, 0.0) for k in ("psemp", "ssemp", "pprofinc", "sprofinc", "scorp"))
    before_qbid = out.get("v18", 0.0) + out.get("qbid", 0.0)
    if business > 0 and before_qbid > S.qbi_threshold(unit.year, unit.status):
        notes.append("income_tax: TAXSIM applies no W-2 wage or property limit to the qualified business income deduction (26 U.S.C. 199A(b)(2)(B)); this unit's taxable income before the deduction passes the 199A(e)(2) threshold")
    # A joint return, or a single filer TAXSIM files as single (no dependent sent), in 2026.
    if unit.year == 2026 and (unit.status == S.JOINT or (unit.status == S.SINGLE and not record.get("depx"))):
        law, build = ZERO_RATE_END_2026[unit.status]
        taxable = out.get("v18", 0.0)
        preferred = max(0.0, record.get("dividends", 0.0)) + S.net_capital_gain(record.get("stcg", 0.0), record.get("ltcg", 0.0))
        ordinary = taxable - min(preferred, taxable)
        band = min(build, taxable) - max(law, ordinary)
        if preferred > 0 and 0.15 * band >= 1:
            notes.append(f"income_tax: this build's 2026 zero rate on net capital gain and qualified dividends runs to {build:,.2f} of taxable income, where Rev. Proc. 2025-32 ends it at {law:,.0f} (26 U.S.C. 1(h), 1(j)(5); probes D6a and D6g); {band:,.2f} of this unit's gains and dividends fall between the two")
    return notes


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
        record["mortgage"] = mortgage + charity + medical + a["investment_interest_allowed"]
        if a["investment_interest"]:
            computed.append("income_tax: investment interest limited to net investment income (26 U.S.C. 163(d)(1), (4)(B)) and entered in `mortgage`, which TAXSIM deducts as given")
        if a["qualified_vehicle_loan_interest"]:
            vehicle = S.vehicle_loan_interest_deduction(unit.status, a["qualified_vehicle_loan_interest"], agi)
            if vehicle > 0:
                unexpressed.append(f"income_tax: TAXSIM has no input for qualified passenger vehicle loan interest (26 U.S.C. 163(h)(4)); the deduction the statute allows at TAXSIM's AGI, {vehicle:,.0f}, is left out")
        if a["medical"]:
            computed.append("income_tax: medical expenses above 7.5% of AGI (26 U.S.C. 213(a)) entered in `mortgage`, which TAXSIM deducts as given")
        if a["charity_cash"] + a["charity_non_cash"]:
            computed.append("income_tax: charitable gifts (above 0.5% of AGI from 2026, 26 U.S.C. 170(b)(1)(I)) entered in `mortgage`; percentage ceilings not applied")
        if a["mortgage_interest"] and mortgage != a["mortgage_interest"]:
            computed.append("income_tax: mortgage interest limited by 26 U.S.C. 163(h)(3)(F)")
        eligible = [f for f in unit.filers if f.age >= 18]
        saved = [sum(contributions[f.name]) + f.deferral + f.roth_deferral + f.se_pension for f in eligible]
        credit = S.savers_credit(year, unit.status, agi, saved, [f.retirement_distributions for f in eligible])
        if credit:
            unexpressed.append(f"income_tax: TAXSIM has no input for the saver's credit (26 U.S.C. 25B), which the statute puts at up to {credit:,.0f} before the limit to tax (reading: " + U.READINGS["savers_credit"] + ")")
    deferrals = sum(f.deferral for f in unit.filers)
    adjustments = state.get("ira", 0.0) + state.get("student_loan", 0.0) + educator + a["hsa_deduction"]
    other_income = a["miscellaneous"] + a["disability_benefits"] + a["salt_refund"]
    se_adjustments = a["se_health_insurance"] + a["se_pension"]
    record["nonprop"] = -(deferrals + adjustments + se_adjustments) + min(0.0, other_income)
    if adjustments and pass_number == 3:
        unexpressed.append("income_tax: adjustments to income (IRA, student loan interest, educator expenses, HSA) are entered as negative `nonprop`, which this build also subtracts from EITC earned income (probe P7.1); the law's earned income (26 U.S.C. 32(c)(2)) is not reduced by them")
    return record


def payroll_records(record: dict, unit: U.Unit) -> dict:
    """The final record with every self-employment box zeroed. The final record carries
    gross wages (pre-tax deferrals are FICA wages, 26 U.S.C. 3121(v)(1)(A)) and the
    deferrals in `nonprop`, which does not reach FICA (probe vmt_deferral_wage_base), so
    its `tfica` is the payroll run; this one splits it: self-employment tax =
    (tfica - addmed) - (tfica0 - addmed0)."""
    without = dict(record)
    for name in ("psemp", "ssemp", "pprofinc", "sprofinc", "pbusinc", "sbusinc"):
        if name in without:
            without[name] = 0
    return without


def member_records(member: dict, year: int) -> tuple[dict, dict]:
    """A listed member with earnings of their own, for payroll and self-employment tax only."""
    full = {"year": year, "state": 0, "mstat": 1, "page": max(1, member["age"]),
            "pwages": member["wages"], "psemp": member["self_employment"]}
    without = dict(full, psemp=0)
    return full, without
