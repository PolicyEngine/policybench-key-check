#!/usr/bin/env python3
"""Blind input map: PolicyBench's 100 board households -> NBER TAXSIM test build, tax year 2026.

Run with plain python3 (standard library only):  python3 map.py
Reads   ../input/board/scenarios.csv and ../input/board/state_and_local_tax_2026.csv
Writes  inputs_2026.csv, answers_2026.csv, notes.csv, runs/*.csv (raw engine replies)

Engine: ../input/taxsim/taxsimtest-osx.exe, called through tsrun.py (one process per pass).
Every 2026 dollar amount below cites the saved source in sources/ (file:line).
"""
import copy
import csv
import json
import math
from pathlib import Path

import tsrun

HERE = Path(__file__).resolve().parent
BOARD = HERE.parent / "input" / "board"
RUNS = HERE / "runs"
YEAR = 2026

# ---------------------------------------------------------------- 2026 law amounts (sources/)
LAW = dict(
    # Notice 2025-67 (sources/n-25-67.txt)
    k402g=24500.0,          # n-25-67.txt:35-37
    k402g_catchup50=8000.0,  # n-25-67.txt:43-46
    k402g_catchup60_63=11250.0,  # n-25-67.txt:46-51
    ira_limit=7500.0,       # n-25-67.txt:162-164
    ira_catchup50=1100.0,   # n-25-67.txt:164-166
    ira_po_active_single=(81000.0, 91000.0),   # n-25-67.txt:182-185
    ira_po_active_joint=(129000.0, 149000.0),  # n-25-67.txt:185-187
    ira_po_spouse_active=(242000.0, 252000.0),  # n-25-67.txt:187-190
    savers_agi_joint=(48500.0, 52500.0, 80500.0),   # n-25-67.txt:140-145
    savers_agi_hoh=(36375.0, 39375.0, 60375.0),     # n-25-67.txt:149-154
    savers_agi_other=(24250.0, 26250.0, 40250.0),   # n-25-67.txt:156-160
    # Rev. Proc. 2025-32 (sources/rp-25-32.txt)
    sli_max=2500.0,                       # rp-25-32.txt:1003-1009
    sli_po_single=(85000.0, 100000.0),    # rp-25-32.txt:1003-1009
    sli_po_joint=(175000.0, 205000.0),    # rp-25-32.txt:1003-1009
    educator_max=350.0,                   # rp-25-32.txt:747-759
    qr_gross_income=5300.0,               # rp-25-32.txt:908-910
    std_single=16100.0, std_hoh=24150.0, std_joint=32200.0,  # rp-25-32.txt:779-792
    addl_aged_blind_married=1650.0, addl_aged_blind_unmarried=2050.0,  # rp-25-32.txt:804-810
    eitc=dict(  # rp-25-32.txt:634-655 ; rates from 26 USC 32(b)(1) (lii_26usc32.txt:20-30)
        e_amt={0: 8680.0, 1: 13020.0, 2: 18290.0, 3: 18290.0},
        max={0: 664.0, 1: 4427.0, 2: 7316.0, 3: 8231.0},
        po_joint={0: 18140.0, 1: 31160.0, 2: 31160.0, 3: 31160.0},
        po_other={0: 10860.0, 1: 23890.0, 2: 23890.0, 3: 23890.0},
        rate_in={0: 0.0765, 1: 0.34, 2: 0.40, 3: 0.45},
        rate_out={0: 0.0765, 1: 0.1598, 2: 0.2106, 3: 0.2106},
        inv_limit=12200.0,  # rp-25-32.txt:662-666
    ),
    # Rev. Proc. 2025-19 (sources/rp-25-19.txt:41-45); 26 USC 223(b)(3) catch-up 1,000 (lii_26usc223.txt:12-18)
    hsa_self=4400.0, hsa_family=8750.0, hsa_catchup55=1000.0,
    # 26 USC 163(h)(3)(F) acquisition debt limit (lii_26usc163.txt)
    mortgage_debt_limit=750000.0,
    # 26 USC 213(a): 7.5% floor (lii_26usc213.txt)
    medical_floor=0.075,
    # 26 USC 170(b)(1)(I) 0.5% floor (lii_26usc170.txt:100); 170(b)(1)(G) 60% cash, (A) 50% (lii_26usc170.txt:36,88)
    charity_floor=0.005, charity_cash_pct=0.60, charity_other_pct=0.50,
    charity_nonitemizer=(1000.0, 2000.0),  # 170(p) (lii_26usc170.txt:854)
    # 26 USC 164(b)(7) (lii_26usc164.txt:71-92)
    salt_cap_2026=40400.0, salt_threshold_2026=505000.0, salt_floor=10000.0,
    # 26 USC 225 (lii_26usc225.txt:3-9)
    ot_max=(12500.0, 25000.0), ot_po=(150000.0, 300000.0),
    # 26 USC 224 qualified tips (lii_26usc224.txt)
    tips_max=25000.0, tips_po=(150000.0, 300000.0),
    # 26 USC 199A(i) minimum deduction (lii_26usc199A.txt:280-290)
    qbi_min=400.0, qbi_min_threshold=1000.0,
    # 26 USC 1402(b)(2): no SE tax if net earnings < 400 (lii_26usc1402.txt)
    se_floor=400.0,
)

# ---------------------------------------------------------------- readings (defaults; each has a re-run alternative)
DEFAULT_READINGS = dict(
    disability_taxable=True,      # disability_benefits -> taxable pension (26 USC 105(a)); alt: excluded (104(a)(3))
    survivor_taxable=True,        # survivor_benefits -> taxable pension/annuity; alt: excluded
    alimony_post2018=True,        # instrument date unstated -> post-2018 rule: neither deductible nor income; alt: pre-2019 rule
    scholarship_taxable=True,     # no qualified tuition stated -> 117 exclusion is 0; alt: fully excluded
    rental_loss_suspended=True,   # 469: rental losses passive, no active participation stated; alt: allowed in full
    tips_inside_wages=True,       # tip_income is a part of employment_income (glossary: wages "including tips"); alt: on top
    k402g_order="trad_first",     # traditional deferrals take the 402(g) room first; alt: roth_first
    hsa_cap=True,                 # cap the stated HSA ALD at the 223(b) limit; alt: as stated
    reit_in_scorp=True,           # qualified REIT/PTP income -> scorp (ordinary + NIIT + 20% QBID, no SECA); alt: intrec
    rental_is_qbi=False,          # rental not a trade or business; alt: rental income -> scorp (QBID)
    otc_medical=False,            # OTC health expenses not deductible (213(b)); alt: deductible
    code_age17_as_18=False,       # code true ages; alt: code a 17-year-old as 18 so the engine's CTC test matches 24(c)(1)
    dependents_file=True,         # dependents with income file their own return, counted in household totals; alt: main return only
    niit_in_income_tax=True,      # NIIT counted in income tax (fiitax includes it); alt: excluded (Form 1040 line 22)
    salt_slot="proptax",          # state/local income-or-sales tax (CSV) in proptax with real estate tax, where the engine applies
                                  # the 164(b)(6)/(7) cap and the AMT addback (probe5 #1-3, probe9); alt: otheritem, the doc's slot for
                                  # "other state and local taxes", which this build neither caps nor adds back (probe5 #2, probe9 #2)
)

ALTERNATIVES = [
    ("disability_taxable", False),
    ("survivor_taxable", False),
    ("alimony_post2018", False),
    ("scholarship_taxable", False),
    ("rental_loss_suspended", False),
    ("tips_inside_wages", False),
    ("k402g_order", "roth_first"),
    ("hsa_cap", False),
    ("reit_in_scorp", False),
    ("rental_is_qbi", True),
    ("otc_medical", True),
    ("code_age17_as_18", True),
    ("dependents_file", False),
    ("niit_in_income_tax", False),
    ("salt_slot", "otheritem"),
]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def r2(x):
    return round(x + 0.0, 2)


class Person:
    def __init__(self, d, kind):
        self.name = d["name"]
        self.kind = kind  # adult / child
        self.age = int(round(f(d["age"])))
        self.wages = f(d["employment_income"])
        self.inp = d.get("inputs", {}) or {}

    def g(self, k):
        v = self.inp.get(k, 0)
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        return f(v)

    def b(self, k):
        return bool(self.inp.get(k, False))


def load_households():
    csv.field_size_limit(10**9)
    salt = {}
    with open(BOARD / "state_and_local_tax_2026.csv") as fh:
        for row in csv.DictReader(fh):
            salt[row["case_id"]] = f(row["value"])
    hh = []
    with open(BOARD / "scenarios.csv") as fh:
        for row in csv.DictReader(fh):
            j = json.loads(row["scenario_json"])
            persons = [Person(a, "adult") for a in j["adults"]] + [Person(c, "child") for c in j["children"]]
            hh.append(dict(id=j["id"], state=j["state"], j=j, persons=persons,
                           tu=j.get("tax_unit_inputs", {}) or {}, hhi=j.get("household_inputs", {}) or {},
                           spm=j.get("spm_unit_inputs", {}) or {}, salt=salt.get(j["id"])))
    return hh


# ---------------------------------------------------------------- statute helpers
def k401_limits(p, order):
    """Elective deferrals allowed under 402(g) (Notice 2025-67), traditional and Roth sharing one limit, capped at wages."""
    trad_d, roth_d = p.g("traditional_401k_contributions_desired"), p.g("roth_401k_contributions_desired")
    if p.wages <= 0:
        return 0.0, 0.0
    lim = LAW["k402g"]
    if 60 <= p.age <= 63:
        lim += LAW["k402g_catchup60_63"]
    elif p.age >= 50:
        lim += LAW["k402g_catchup50"]
    lim = min(lim, p.wages)
    if order == "trad_first":
        trad = min(trad_d, lim)
        roth = min(roth_d, lim - trad)
    else:
        roth = min(roth_d, lim)
        trad = min(trad_d, lim - roth)
    return trad, roth


def ira_deduction(people, joint, magi, comp, k401):
    """Traditional IRA deduction per 219(b),(c),(g). people: list of (Person); comp: compensation per person;
    k401: (trad, roth) allowed 401(k) per person (active participation). Returns dict name->(trad_contrib, deduction, detail)."""
    out = {}
    total_comp = sum(comp.values())
    used = {}
    active = {p.name: (k401[p.name][0] + k401[p.name][1]) > 0 for p in people}
    for p in people:
        lim = LAW["ira_limit"] + (LAW["ira_catchup50"] if p.age >= 50 else 0.0)
        if joint:
            other = [q for q in people if q.name != p.name]
            other_used = sum(used.get(q.name, 0.0) for q in other)
            avail = max(0.0, total_comp - other_used)  # 219(c): combined compensation less the spouse's contributions
        else:
            avail = comp[p.name]
        lim = min(lim, avail)
        trad = min(p.g("traditional_ira_contributions_desired"), lim)
        roth = min(p.g("roth_ira_contributions_desired"), lim - trad)
        used[p.name] = trad + roth
        # phase-out 219(g)
        spouse_active = joint and any(active[q.name] for q in people if q.name != p.name)
        rng = None
        if active[p.name]:
            rng = LAW["ira_po_active_joint"] if joint else LAW["ira_po_active_single"]
        elif spouse_active:
            rng = LAW["ira_po_spouse_active"]
        ded_lim = LAW["ira_limit"] + (LAW["ira_catchup50"] if p.age >= 50 else 0.0)
        detail = f"active={active[p.name]} spouse_active={spouse_active} MAGI={magi:.2f}"
        if rng is not None and magi > rng[0]:
            red = ded_lim * (magi - rng[0]) / (rng[1] - rng[0])
            red = math.floor(red / 10.0) * 10.0  # 219(g)(2) last sentence: round to next lowest $10
            new = max(0.0, ded_lim - red)
            if 0 < new < 200:
                new = 200.0  # 219(g)(2)(B)
            ded_lim = new
            detail += f" phase-out range {rng} -> deductible limit {ded_lim:.2f}"
        ded = min(trad, ded_lim)
        out[p.name] = (trad, ded, detail)
    return out


def sli_deduction(paid, magi, joint):
    if paid <= 0:
        return 0.0, ""
    base = min(paid, LAW["sli_max"])
    lo, hi = LAW["sli_po_joint"] if joint else LAW["sli_po_single"]
    frac = 0.0 if magi <= lo else min(1.0, (magi - lo) / (hi - lo))
    return base * (1 - frac), f"min(paid {paid:.2f}, 2,500) x (1 - phase-out {frac:.4f}) at MAGI {magi:.2f}"


def statutory_eitc(n_kids, earned, agi, joint, inv_income):
    if inv_income > LAW["eitc"]["inv_limit"]:
        return 0.0
    e = LAW["eitc"]
    k = min(n_kids, 3)
    po = (e["po_joint"] if joint else e["po_other"])[k]
    cred = min(e["rate_in"][k] * earned, e["max"][k])
    inc = max(agi, earned)
    if inc > po:
        cred = max(0.0, cred - e["rate_out"][k] * (inc - po))
    return cred


def cdcc_rate_2026(agi, joint):
    """26 USC 21(a)(2) as amended for 2026 (lii_26usc21.txt:5-9)."""
    rate = 50
    if agi > 15000:
        rate -= math.ceil((agi - 15000) / 2000.0)
    rate = max(rate, 35)
    thr, step = (150000, 4000) if joint else (75000, 2000)
    if agi > thr:
        rate -= math.ceil((agi - thr) / step)
        rate = max(rate, 20)
    return rate / 100.0


# ---------------------------------------------------------------- household -> engine records
def derive(h, R):
    """Return a dict describing the filers of household h under readings R (no engine calls)."""
    notes = []
    cid = h["id"]

    def note(group, kind, text):
        notes.append(dict(case_id=cid, quantity_group=group, kind=kind, text=text))

    persons = h["persons"]
    head = [p for p in persons if p.b("is_tax_unit_head")]
    spouse = [p for p in persons if p.b("is_tax_unit_spouse")]
    assert len(head) == 1, cid
    head = head[0]
    spouse = spouse[0] if spouse else None
    others = [p for p in persons if p is not head and p is not spouse]
    joint = spouse is not None
    filers_main = [head] + ([spouse] if spouse else [])

    # --- dependents (26 USC 152): qualifying child if under 19 or permanently and totally disabled (is_disabled);
    #     otherwise a qualifying relative if gross income < 5,300.
    deps, separate = [], []
    for p in others:
        gross = p.wages + p.g("taxable_interest_income") + p.g("disability_benefits") + p.g("taxable_private_pension_income")
        if p.age < 19 or p.b("is_disabled"):
            deps.append(p)
            if p.age >= 19:
                note("income_tax", "reading", f"{p.name} (age {p.age}, is_disabled) treated as a qualifying child of any age under 26 USC 152(c)(3)(B) (is_disabled read as permanently and totally disabled; support test assumed met): counted in depx with true age, so the engine gives the $500 credit for other dependents.")
        elif gross < LAW["qr_gross_income"]:
            deps.append(p)
            note("income_tax", "reading", f"{p.name} (age {p.age}) treated as a qualifying relative (gross income {gross:.2f} < 5,300).")
        else:
            separate.append(p)
            note("income_tax", "reading", f"{p.name} (age {p.age}) is not a dependent; files a separate single return.")

    # --- 401(k) deferrals: box-1 wages = gross wages less allowed traditional deferrals (402(g)); FICA wages stay gross
    k401 = {}
    for p in persons:
        t, r = k401_limits(p, R["k402g_order"])
        k401[p.name] = (t, r)
        td, rd = p.g("traditional_401k_contributions_desired"), p.g("roth_401k_contributions_desired")
        if td or rd:
            note("income_tax", "computed_from_statute",
                 f"{p.name}: 401(k) desired traditional {td:.2f}, Roth {rd:.2f}; allowed under 26 USC 402(g) "
                 f"(limit 24,500 + age catch-up, capped at wages {p.wages:.2f}; Notice 2025-67, n-25-67.txt:35-51; order {R['k402g_order']}): "
                 f"traditional {t:.2f}, Roth {r:.2f}. pwages/swages carry wages less the traditional amount; payroll passes carry gross wages.")

    # --- tips
    tips = {p.name: p.g("tip_income") for p in persons}
    if any(tips.values()):
        if R["tips_inside_wages"]:
            note("all", "reading", "tip_income read as part of employment_income (glossary: wages 'including tips and commissions'); not added again.")
        else:
            note("all", "reading", "ALT run: tip_income added on top of employment_income (wages and FICA wages).")

    def gross_wages(p):
        w = p.wages
        if not R["tips_inside_wages"]:
            w += tips[p.name]
        return w

    # --- SE pieces per person
    def se_parts(p):
        sched_c = p.g("self_employment_income")
        farm = p.g("farm_operations_income")
        pship_se = p.g("partnership_se_income")
        sstb = p.g("sstb_self_employment_income_before_lsr")
        return sched_c + farm + pship_se, sstb

    # --- income items on the main return (head + spouse)
    def S(key, people=filers_main):
        return sum(p.g(key) for p in people)

    interest = S("taxable_interest_income")
    nq_div = S("non_qualified_dividend_income") + S("qualified_bdc_income")
    q_div = S("qualified_dividend_income")
    estate = S("estate_income")
    rental = S("rental_income")
    farm_rent = S("farm_rent_income")
    reit = S("qualified_reit_and_ptp_income")
    pship_total = S("partnership_s_corp_income")
    pship_se = S("partnership_se_income")
    scorp = pship_total - pship_se
    if pship_se:
        note("self_employment", "reading", f"partnership_se_income {pship_se:.2f} read as the self-employment part of partnership_s_corp_income {pship_total:.2f}: the SE part goes to psemp, the rest {scorp:.2f} to scorp.")
    if pship_total:
        note("income_tax", "reading", f"partnership/S-corp income (non-SE part {scorp:.2f}) -> scorp: ordinary income, QBI without SSTB phase-out, NIIT, no SECA (engine behaviour by probe5 #24). The engine allows scorp losses against other income (probe5 #36) although the doc says passive-loss limited.")
    if reit:
        if R["reit_in_scorp"]:
            scorp += reit
            note("income_tax", "reading", f"qualified REIT/PTP income {reit:.2f} -> scorp (ordinary income + NIIT + 20% QBI deduction, no SECA), the engine input whose treatment matches 26 USC 199A(b)(1)(B).")
        else:
            interest += reit
    # 26 USC 469: rental and farm rental are passive activities netted together; a net loss is suspended
    passive_rent = rental + farm_rent
    allowed_passive = passive_rent
    if passive_rent < 0 and R["rental_loss_suspended"]:
        allowed_passive = 0.0
        note("income_tax", "computed_from_statute",
             f"net rental/farm-rental loss {passive_rent:.2f} (rental {rental:.2f}, farm rent {farm_rent:.2f}) is a passive activity loss (26 USC 469(c)(2)); no other passive income and active participation is not stated (preface: unlisted facts false), so the 469(i) $25,000 allowance is not taken and the loss is suspended: 0 enters income.")
    elif passive_rent < 0:
        note("income_tax", "reading", f"ALT run: net rental loss {passive_rent:.2f} allowed in full.")
    rent_to_intrec = allowed_passive
    if R["rental_is_qbi"] and rental:
        # 199A status does not change 469 status: the rental stays in the passive netting above, and only the
        # part of it that enters taxable income becomes QBI (scorp); the rest of the allowed result stays in intrec.
        if rental >= 0:
            q_rent = rental
        elif farm_rent > 0:
            q_rent = allowed_passive - farm_rent
        else:
            q_rent = rental if allowed_passive != 0 else 0.0
        scorp += q_rent
        rent_to_intrec = allowed_passive - q_rent
        note("income_tax", "reading", f"ALT run: rental {rental:.2f} treated as a qualified trade or business for 26 USC 199A; after the 469 netting {q_rent:.2f} of it enters income as QBI (scorp) and {rent_to_intrec:.2f} of the allowed passive result stays in intrec.")
    if farm_rent or rental or estate:
        note("income_tax", "engine_behaviour", f"rental {rental:.2f}, farm rental {farm_rent:.2f}, estate/trust {estate:.2f} go to intrec, not otherprop: the engine drops otherprop from AGI in 2024-2026 (probe7). intrec gives the same law treatment (ordinary income, NIIT, EITC investment income); doc: 'Any income item not mentioned above can be placed wherever you think Taxsim will treat it most correctly'.")
    if S("farm_income"):
        if abs(S("farm_income") - S("farm_operations_income")) > 0.005:
            raise ValueError(f"{cid}: farm_income differs from farm_operations_income; the duplicate reading does not hold")
        note("income_tax", "reading", f"farm_income {S('farm_income'):.2f} (Schedule J label) equals farm_operations_income here and is read as the same Schedule F result, not extra income; only farm_operations_income is entered (psemp, SE income under 26 USC 1402(a)).")

    pensions = (S("taxable_private_pension_income") + S("taxable_ira_distributions") + S("taxable_401k_distributions")
                + S("taxable_403b_distributions"))
    dis = S("disability_benefits")
    if dis:
        if R["disability_taxable"]:
            pensions += dis
            note("income_tax", "reading", f"disability_benefits {dis:.2f} (employment-based, 'includes both the taxable and the tax-exempt part', split unstated) read as taxable under 26 USC 105(a) because the 104(a)(3) exclusion needs employee-paid premiums, which are not stated; entered as pensions.")
    surv = S("survivor_benefits")
    if surv:
        if R["survivor_taxable"]:
            pensions += surv
            note("income_tax", "reading", f"survivor_benefits {surv:.2f} (non-Social-Security) read as a taxable survivor annuity; entered as pensions.")
    gssi = S("social_security_retirement") + S("social_security_disability") + S("social_security_survivors") + S("social_security_dependents")
    if S("social_security_dependents"):
        note("income_tax", "reading", f"social_security_dependents {S('social_security_dependents'):.2f} is stated on the filer, so it is treated as the filer's benefit (gssi), not a child's.")
    ui_p = head.g("unemployment_compensation")
    ui_s = spouse.g("unemployment_compensation") if spouse else 0.0

    nonprop = 0.0
    salt_ref = S("salt_refund_income")
    misc = S("miscellaneous_income")
    nonprop += salt_ref + misc
    sch = S("educational_assistance")
    if sch:
        if R["scholarship_taxable"]:
            nonprop += sch
            note("income_tax", "reading", f"educational_assistance {sch:.2f}: no qualified tuition is stated (preface: unlisted expenses are 0), so the 26 USC 117 exclusion is 0 and the amount is taxable non-wage income (nonprop).")
    alim_in, alim_out = S("alimony_income"), S("alimony_expense")
    if alim_in or alim_out:
        if R["alimony_post2018"]:
            note("income_tax", "reading", f"alimony (received {alim_in:.2f}, paid {alim_out:.2f}): the divorce instrument date is not stated (preface: unlisted facts false), so the post-2018 rule applies (Pub. L. 115-97 sec. 11051; 26 USC 215 repealed, lii_26usc215.txt): neither income nor deduction.")
        else:
            nonprop += alim_in - alim_out
    hsa_stated = f(h["tu"].get("health_savings_account_ald", 0))
    hsa = hsa_stated
    if hsa_stated:
        coverage_family = joint or bool(deps)
        lim = LAW["hsa_family"] if coverage_family else LAW["hsa_self"]
        lim += sum(LAW["hsa_catchup55"] for p in filers_main if p.age >= 55)
        if R["hsa_cap"]:
            hsa = min(hsa_stated, lim)
        note("income_tax", "computed_from_statute", f"HSA ALD stated {hsa_stated:.2f}; 26 USC 223(b) limit {'family' if coverage_family else 'self-only (no spouse or dependent to cover)'} {lim:.2f} (Rev. Proc. 2025-19, rp-25-19.txt:41-45, + 1,000 per filer 55+); entered {hsa:.2f} as negative nonprop.")
    nonprop -= hsa
    edu = sum(min(p.g("educator_expense"), LAW["educator_max"]) for p in filers_main)
    if edu:
        note("income_tax", "computed_from_statute", f"educator expenses {S('educator_expense'):.2f} capped at 350 per educator (Rev. Proc. 2025-32, rp-25-32.txt:747-759): {edu:.2f} as negative nonprop.")
    nonprop -= edu
    if f(h["tu"].get("domestic_production_ald", 0)):
        note("income_tax", "reading", f"domestic_production_ald {f(h['tu']['domestic_production_ald']):.2f}: the 26 USC 199 deduction was repealed for years after 2017; not entered.")

    # SE health insurance deduction 162(l): SE person without ESI, premiums of filer/spouse/dependents without ESI
    se_health = 0.0
    for p in filers_main:
        se_net, sstb = se_parts(p)
        net = se_net + sstb
        if net > 0 and not p.b("has_esi"):
            prem = sum(max(q.g("health_insurance_premiums_without_medicare_part_b"), q.g("other_health_insurance_premiums"))
                       for q in [p] + [q for q in filers_main + deps if q is not p and not q.b("has_esi")])
            lim = net - 0.5 * 0.153 * 0.9235 * net
            d = min(prem, lim)
            if d > 0:
                se_health += d
                note("income_tax", "computed_from_statute", f"{p.name}: self-employed health insurance deduction (26 USC 162(l)) {d:.2f} = premiums {prem:.2f} limited to SE earnings; negative nonprop; these premiums are not counted again as medical expenses.")
    nonprop -= se_health

    real_estate = sum(p.g("real_estate_taxes") for p in persons)
    salt_csv = h["salt"] or 0.0
    if R["salt_slot"] == "proptax":
        proptax, otheritem = real_estate + salt_csv, 0.0
        if salt_csv or real_estate:
            note("income_tax", "reading", f"state and local income-or-sales tax {salt_csv:.2f} (state_and_local_tax_2026.csv, before any cap) + real estate taxes {real_estate:.2f} -> proptax {proptax:.2f}: the engine applies the SALT cap (26 USC 164(b)(6),(7)) and the AMT addback (26 USC 56(b)(1)(A)(ii), lii_26usc56.txt:44-45) only to proptax (probe5 #1-#3, probe9 #1 vs #3); the doc's otheritem slot for other state and local taxes is neither capped nor added back by this build (probe5 #2, probe9 #2 vs #5), so the alternative salt_slot=otheritem is rerun.")
    else:
        proptax, otheritem = real_estate, salt_csv

    childcare = f(h["spm"].get("spm_unit_pre_subsidy_childcare_expenses", 0))
    rentpaid = sum(p.g("pre_subsidy_rent") for p in persons)
    transfers = sum(p.g(k) for p in filers_main for k in (
        "veterans_benefits", "workers_compensation", "child_support_received", "financial_assistance",
        "tax_exempt_private_pension_income", "tax_exempt_ira_distributions"))
    if not R["disability_taxable"]:
        transfers += dis
    if not R["survivor_taxable"]:
        transfers += surv
    if not R["scholarship_taxable"]:
        transfers += sch

    se_p, sstb_p = se_parts(head)
    se_s, sstb_s = se_parts(spouse) if spouse else (0.0, 0.0)

    # ages of dependents: infants coded 1 (doc: "Code infants as 1"; age 0 reads as unspecified -> 10, probe1 #5)
    ages = []
    for p in sorted(deps, key=lambda q: -q.age):
        a = p.age
        if a == 0:
            a = 1
            note("income_tax", "reading", f"{p.name} age 0 coded as 1 (TAXSIM doc: 'Code infants as 1'; age 0 means unspecified).")
        if a == 17 and R["code_age17_as_18"]:
            a = 18
        ages.append(a)
    if len(ages) > 8:
        raise ValueError(f"{cid}: more than 8 dependents")

    main = dict(
        role="main", people=filers_main, joint=joint,
        rec=dict(mstat=2 if joint else 1, page=head.age, sage=spouse.age if spouse else 0, depx=len(ages),
                 pwages=gross_wages(head) - k401[head.name][0],
                 swages=(gross_wages(spouse) - k401[spouse.name][0]) if spouse else 0.0,
                 psemp=se_p, ssemp=se_s, pprofinc=sstb_p, sprofinc=sstb_s, scorp=scorp,
                 dividends=q_div, intrec=interest + nq_div + estate + rent_to_intrec,
                 stcg=S("short_term_capital_gains"),
                 ltcg=S("long_term_capital_gains") + max(0.0, S("non_sch_d_capital_gains")),
                 nonprop=nonprop, pensions=pensions, gssi=gssi, pui=ui_p, sui=ui_s, transfers=transfers,
                 rentpaid=rentpaid, proptax=proptax, otheritem=otheritem, childcare=childcare, mortgage=0.0),
        fica_wages=(gross_wages(head), gross_wages(spouse) if spouse else 0.0),
    )
    for i, a in enumerate(ages):
        main["rec"][f"age{i+1}"] = a

    # dependents and others with income: own returns
    extra = []
    for p in deps + separate:
        dis_p = p.g("disability_benefits") if R["disability_taxable"] else 0.0
        inc = (gross_wages(p) + p.g("taxable_interest_income") + dis_p + p.g("taxable_private_pension_income"))
        if inc <= 0:
            continue
        t401 = k401[p.name][0]
        rec = dict(mstat=8 if p in deps else 1, page=p.age, sage=0, depx=0,
                   pwages=gross_wages(p) - t401, intrec=p.g("taxable_interest_income"),
                   pensions=dis_p + p.g("taxable_private_pension_income"))
        extra.append(dict(role=f"dep_{p.name}" if p in deps else f"sep_{p.name}", people=[p], joint=False, rec=rec,
                          fica_wages=(gross_wages(p), 0.0)))
        note("all", "reading", f"{p.name} (age {p.age}) has income {inc:.2f} and files its own return "
             f"({'dependent filer, mstat 8' if p in deps else 'single'}); its income tax and payroll tax count in the household totals.")

    return dict(main=main, extra=extra, notes=notes, k401=k401, deps=deps, head=head, spouse=spouse, joint=joint,
                se_health_used=se_health,
                comp_wages={p.name: gross_wages(p) - k401[p.name][0] for p in filers_main},
                se_by_person={p.name: sum(se_parts(p)) for p in filers_main})


def itemized(h, d, agi, R):
    """Amounts for TAXSIM `mortgage` (deductions that are not AMT preferences), computed from the statute."""
    notes = []
    cid = h["id"]
    persons = h["persons"]
    tu = h["tu"]
    # mortgage interest
    tu_int = f(tu.get("first_home_mortgage_interest", 0)) + f(tu.get("second_home_mortgage_interest", 0))
    p_int = sum(p.g("home_mortgage_interest") for p in persons)
    interest = tu_int if tu_int > 0 else p_int
    bal = f(tu.get("first_home_mortgage_balance", 0)) + f(tu.get("second_home_mortgage_balance", 0))
    mint = interest
    if interest > 0 and bal > LAW["mortgage_debt_limit"]:
        mint = interest * LAW["mortgage_debt_limit"] / bal
    if interest > 0:
        notes.append(("computed_from_statute", f"home mortgage interest {interest:.2f} (tax-unit first+second split used when stated; person-level total otherwise); acquisition debt {bal:.2f}; 26 USC 163(h)(3)(F) $750,000 limit -> deductible {mint:.2f}" + (" (interest x 750,000/balance, Pub. 936 ratio with the stated balance as the average balance)" if mint < interest else " (balance within the limit)")))
    # charity
    cash = sum(p.g("charitable_cash_donations") for p in persons)
    noncash = sum(p.g("charitable_non_cash_donations") for p in persons)
    char = 0.0
    if cash or noncash:
        nc_allowed = min(noncash, LAW["charity_other_pct"] * agi)
        cash_allowed = min(cash, max(0.0, LAW["charity_cash_pct"] * agi - nc_allowed))
        before = nc_allowed + cash_allowed
        char = max(0.0, before - LAW["charity_floor"] * max(agi, 0.0))
        notes.append(("computed_from_statute", f"charitable cash {cash:.2f} + non-cash {noncash:.2f}: 60%/50% AGI limits (26 USC 170(b)(1)(G),(A)) give {before:.2f}; 2026 0.5% floor (170(b)(1)(I), lii_26usc170.txt:100) on AGI {agi:.2f} -> {char:.2f} entered in mortgage (only used if the engine itemizes)"))
    # medical
    med = 0.0
    se_prem_used = set()
    for p in persons:
        prem = max(p.g("health_insurance_premiums_without_medicare_part_b"), p.g("other_health_insurance_premiums"))
        med += p.g("other_medical_expenses") + prem
        if R["otc_medical"]:
            med += p.g("over_the_counter_health_expenses")
    se_health = d.get("se_health_used", 0.0)
    med -= se_health
    med_ded = max(0.0, med - LAW["medical_floor"] * agi)
    otc = sum(p.g("over_the_counter_health_expenses") for p in persons)
    if med > 0:
        notes.append(("computed_from_statute", f"medical expenses {med:.2f} (other_medical_expenses + person-paid premiums health_insurance_premiums_without_medicare_part_b, all household members{'; OTC included (ALT)' if R['otc_medical'] else '; OTC ' + format(otc, '.2f') + ' excluded under 26 USC 213(b)'}) less 7.5% of AGI {agi:.2f} -> {med_ded:.2f} in mortgage"))
    return mint + char + med_ded, notes, dict(mortgage_interest=mint, charity=char, medical=med_ded, cash=cash)


# ---------------------------------------------------------------- engine passes
def base_record(cid_num, rec):
    r = dict(taxsimid=cid_num, year=YEAR, state=0)
    r.update(rec)
    return r


def run_pass(records, tag):
    res = tsrun.run(records, idtl=2)
    RUNS.mkdir(exist_ok=True)
    with open(RUNS / f"{tag}_in.csv", "w") as fh:
        fh.write(tsrun.to_csv(records))
    with open(RUNS / f"{tag}_out.csv", "w", newline="") as fh:
        keys = [k for k in res[0].keys() if not k.startswith("_")]
        w = csv.writer(fh)
        w.writerow(keys)
        for r in res:
            w.writerow([r.get(k) for k in keys])
    return res


def pipeline(hh, R, tag, write_runs=True):
    """Run all passes for all households under readings R. Returns per-household results."""
    D = {}
    filers = []  # (cid, filer dict)
    for h in hh:
        d = derive(h, R)
        D[h["id"]] = d
        filers.append((h["id"], d["main"]))
        for e in d["extra"]:
            filers.append((h["id"], e))
    ids = list(range(1, len(filers) + 1))

    def records(stage):
        out = []
        for i, (cid, fl) in zip(ids, filers):
            out.append(base_record(i, fl["rec"]))
        return out

    run = (lambda recs, name: run_pass(recs, f"{tag}_{name}")) if write_runs else (lambda recs, name: tsrun.run(recs))

    # pass 0: AGI before IRA and student-loan deductions
    res0 = run(records(0), "pass0")
    agi0 = {}
    for (cid, fl), r in zip(filers, res0):
        fl["agi0"] = r["v10"]
    # IRA deduction (main returns)
    for h in hh:
        d = D[h["id"]]
        m = d["main"]
        people = m["people"]
        comp = {p.name: max(0.0, d["comp_wages"][p.name]) + max(0.0, d["se_by_person"][p.name]) for p in people}
        ira = ira_deduction(people, m["joint"], m["agi0"], comp, d["k401"])
        total = 0.0
        m["ira_contrib"] = {}
        for p in people:
            trad, ded, detail = ira[p.name]
            m["ira_contrib"][p.name] = trad + min(p.g("roth_ira_contributions_desired"), max(0.0, LAW["ira_limit"] + (LAW["ira_catchup50"] if p.age >= 50 else 0.0) - trad)) if comp[p.name] > 0 or m["joint"] else 0.0
            want = p.g("traditional_ira_contributions_desired")
            if want or p.g("roth_ira_contributions_desired"):
                d["notes"].append(dict(case_id=h["id"], quantity_group="income_tax", kind="computed_from_statute",
                                       text=f"{p.name}: traditional IRA desired {want:.2f}; contribution allowed {trad:.2f} (26 USC 219(b),(c): 7,500 +1,100 at 50+, Notice 2025-67 n-25-67.txt:162-166, limited by compensation {comp[p.name]:.2f}{' and spousal combined compensation' if m['joint'] else ''}; traditional before Roth); deductible {ded:.2f} ({detail}; 219(g) ranges n-25-67.txt:182-190); negative nonprop."))
            total += ded
        m["ira_ded"] = total
        m["rec"]["nonprop"] -= total
    # pass 1
    res1 = run(records(1), "pass1")
    for (cid, fl), r in zip(filers, res1):
        fl["agi1"] = r["v10"]
    for h in hh:
        d = D[h["id"]]
        m = d["main"]
        paid = sum(p.g("student_loan_interest") for p in m["people"])
        ded, detail = sli_deduction(paid, m["agi1"], m["joint"])
        if paid:
            d["notes"].append(dict(case_id=h["id"], quantity_group="income_tax", kind="computed_from_statute",
                                   text=f"student loan interest deduction (26 USC 221; Rev. Proc. 2025-32 rp-25-32.txt:1003-1009): {detail} = {ded:.2f}; negative nonprop."))
        m["sli_ded"] = ded
        m["rec"]["nonprop"] -= ded
    # pass 2: final AGI before itemized amounts
    res2 = run(records(2), "pass2")
    for (cid, fl), r in zip(filers, res2):
        fl["agi2"] = r["v10"]
    for h in hh:
        d = D[h["id"]]
        m = d["main"]
        amt, nts, parts = itemized(h, d, m["agi2"], R)
        m["rec"]["mortgage"] = amt
        m["item_parts"] = parts
        for kind, text in nts:
            d["notes"].append(dict(case_id=h["id"], quantity_group="income_tax", kind=kind, text=text))
    # pass A: final income-tax pass
    resA = run(records(3), "passA")
    for (cid, fl), r in zip(filers, resA):
        fl["A"] = r
        if abs(r["v10"] - fl["agi2"]) > 0.01:
            raise RuntimeError(f"{cid} {fl['role']}: AGI moved between pass 2 and pass A")
    # pass B (gross wages + SE) and pass C (gross wages only) for payroll and SE tax
    recB, recC = [], []
    for i, (cid, fl) in zip(ids, filers):
        rec = fl["rec"]
        b = dict(mstat=rec["mstat"], page=rec["page"], sage=rec.get("sage", 0),
                 pwages=fl["fica_wages"][0], swages=fl["fica_wages"][1],
                 psemp=rec.get("psemp", 0.0), ssemp=rec.get("ssemp", 0.0),
                 pprofinc=rec.get("pprofinc", 0.0), sprofinc=rec.get("sprofinc", 0.0))
        c = dict(mstat=rec["mstat"], page=rec["page"], sage=rec.get("sage", 0),
                 pwages=fl["fica_wages"][0], swages=fl["fica_wages"][1])
        recB.append(base_record(i, b))
        recC.append(base_record(i, c))
        fl["recB"], fl["recC"] = b, c
    resB = run(recB, "passB")
    resC = run(recC, "passC")
    for (cid, fl), rb, rc in zip(filers, resB, resC):
        fl["B"], fl["C"] = rb, rc
    return D, filers


def answers_from(D, filers, R):
    out = {}
    for cid, d in D.items():
        rows = [fl for c, fl in filers if c == cid]
        if not R["dependents_file"]:
            rows = [fl for fl in rows if fl["role"] == "main"]
        it = rf = se = pay = niit = 0.0
        for fl in rows:
            A, B, C = fl["A"], fl["B"], fl["C"]
            it += A["fiitax"] + A["v25"] + A["actc"] - (0.0 if R["niit_in_income_tax"] else A["niit"])
            rf += A["v25"] + A["actc"]
            se += (B["tfica"] - B["addmed"]) - (C["tfica"] - C["addmed"])
            pay += (C["tfica"] - C["addmed"]) + B["addmed"]
            niit += A["niit"]
        res = dict(federal_income_tax_before_refundable_credits=r2(it), federal_refundable_credits=r2(rf),
                   self_employment_tax=r2(se), federal_employee_payroll_tax=r2(pay))
        # The engine rounds fiitax, v25 and actc to the cent separately, so fiitax + v25 + actc can come
        # out a cent below zero when tax before credits is 0. A tax line cannot be negative; such a
        # residual (> -0.05) is set to 0 and recorded in CLAMPED for a note.
        for q, v in list(res.items()):
            if -0.05 < v < 0:
                CLAMPED.setdefault(R.get("_tag", "default"), {})[(cid, q)] = v
                res[q] = 0.0
            elif v == 0:
                res[q] = 0.0  # drop a signed zero (-0.0) from rounding
        out[cid] = res
    return out


CLAMPED = {}


FORMULAS = dict(
    federal_income_tax_before_refundable_credits="sum over the household's records of passA.fiitax + passA.v25 (EITC) + passA.actc (ACTC); fiitax includes NIIT and AMT, excludes Additional Medicare Tax (probe1 #23)",
    federal_refundable_credits="sum over records of passA.v25 (EITC) + passA.actc (additional CTC)",
    self_employment_tax="sum over records of (passB.tfica - passB.addmed) - (passC.tfica - passC.addmed); passB = gross wages + SE income, passC = gross wages only",
    federal_employee_payroll_tax="sum over records of (passC.tfica - passC.addmed) + passB.addmed (employee SS + Medicare on gross wages, plus Additional Medicare Tax on wages and SE income)",
)

INPUT_COLS = ["mstat", "page", "sage", "depx", "age1", "age2", "age3", "age4", "age5", "age6", "age7", "age8",
              "pwages", "swages", "psemp", "ssemp", "pprofinc", "sprofinc", "scorp", "dividends", "intrec", "stcg",
              "ltcg", "nonprop", "pensions", "gssi", "pui", "sui", "transfers", "rentpaid", "proptax", "otheritem",
              "childcare", "mortgage"]


def unexpressed_and_engine_notes(h, d, R):
    """Notes on facts the engine cannot take and on engine behaviours, per household (default run only)."""
    cid = h["id"]
    out = []
    m = d["main"]
    A = m["A"]
    joint = m["joint"]
    persons = h["persons"]
    filers_main = m["people"]
    agi = A["v10"]

    def add(group, kind, text):
        out.append(dict(case_id=cid, quantity_group=group, kind=kind, text=text))

    # blindness
    blind = [p for p in filers_main if p.b("is_blind")]
    if blind:
        amt = (LAW["addl_aged_blind_married"] if joint else LAW["addl_aged_blind_unmarried"]) * len(blind)
        add("income_tax", "unexpressed", f"is_blind ({', '.join(p.name for p in blind)}): the engine has no blindness input; the additional standard deduction of {amt:.2f} (26 USC 63(f)(2), lii_26usc63.txt:99-103; Rev. Proc. 2025-32 rp-25-32.txt:804-810) is not applied. Engine v13 = {A['v13']:.2f}, itemized v17 = {A['v17']:.2f}.")
    # overtime 225
    ot = sum(p.g("fsla_overtime_premium") for p in filers_main)
    if ot:
        mx = LAW["ot_max"][1] if joint else LAW["ot_max"][0]
        po = LAW["ot_po"][1] if joint else LAW["ot_po"][0]
        ded = min(ot, mx)
        if agi > po:
            ded = max(0.0, ded - 100.0 * math.ceil((agi - po) / 1000.0))
        add("income_tax", "unexpressed", f"fsla_overtime_premium {ot:.2f}: the engine has no input for the 26 USC 225 qualified overtime deduction (lii_26usc225.txt:3-9); statutory deduction at AGI {agi:.2f} would be {ded:.2f} (cap {mx:.0f}, $100 per $1,000 over {po:.0f}).")
    tips = sum(p.g("tip_income") for p in filers_main)
    if tips:
        po = LAW["tips_po"][1] if joint else LAW["tips_po"][0]
        ded = min(tips, LAW["tips_max"])
        if agi > po:
            ded = max(0.0, ded - 100.0 * math.ceil((agi - po) / 1000.0))
        add("income_tax", "unexpressed", f"tip_income {tips:.2f}: the engine has no input for the 26 USC 224 qualified tips deduction; if the tips qualify (occupation not stated) the statutory deduction at AGI {agi:.2f} would be {ded:.2f}.")
    car = f(h["hhi"].get("auto_loan_interest", 0))
    if car:
        add("income_tax", "reading", f"auto_loan_interest {car:.2f}: the 26 USC 163(h)(4) deduction needs a new, US-assembled personal vehicle bought after 2024, none of which is stated (preface: unlisted facts false); no deduction, and the engine has no input for it anyway.")
    # tax-exempt interest and SS / EITC
    tei = sum(p.g("tax_exempt_interest_income") for p in filers_main)
    if tei and m["rec"]["gssi"]:
        add("income_tax", "unexpressed", f"tax_exempt_interest_income {tei:.2f}: the engine has no tax-exempt interest input, so it is left out of Social Security provisional income (26 USC 86(b)(2)(B)); engine taxable SS v12 = {A['v12']:.2f} of gssi {m['rec']['gssi']:.2f}.")
    elif tei:
        add("income_tax", "unexpressed", f"tax_exempt_interest_income {tei:.2f}: no engine input; it bears on no line here (no Social Security, EITC investment-income test not reached).")
    # non-itemizer charitable 170(p)
    cash = m["item_parts"]["cash"]
    itemizes = A["v17"] > 0
    if cash and not itemizes:
        cap = LAW["charity_nonitemizer"][1] if joint else LAW["charity_nonitemizer"][0]
        add("income_tax", "unexpressed", f"charitable cash {cash:.2f} with the standard deduction: the 2026 non-itemizer deduction (26 USC 170(p), lii_26usc170.txt:854) of {min(cash, cap):.2f} has no engine input (the engine's only charity slot is the itemized `mortgage`).")
    # 72(t)
    for p in filers_main:
        early = p.g("taxable_ira_distributions") + p.g("taxable_401k_distributions") + p.g("taxable_403b_distributions")
        if early > 0 and p.age <= 59:
            if p.b("is_disabled"):
                add("income_tax", "reading", f"{p.name} (age {p.age}) early retirement distributions {early:.2f}: is_disabled -> 26 USC 72(t)(2)(A)(iii) exception; no 10% additional tax.")
            else:
                add("income_tax", "unexpressed", f"{p.name} (age {p.age}) early retirement distributions {early:.2f}: the 10% additional tax of 26 USC 72(t) ({0.1*early:.2f}, Schedule 2 line 8) has no engine computation; not in the engine's income tax.")
    # saver's credit
    contrib = 0.0
    for p in filers_main:
        t, r = d["k401"][p.name]
        contrib += min(2000.0, t + r + m.get("ira_contrib", {}).get(p.name, 0.0))
    if contrib > 0 and not any(p.age < 18 for p in filers_main):
        lims = LAW["savers_agi_joint"] if joint else (LAW["savers_agi_hoh"] if m["rec"]["depx"] else LAW["savers_agi_other"])
        if agi <= lims[2]:
            add("income_tax", "unexpressed", f"retirement contributions with AGI {agi:.2f} at or below the 26 USC 25B limit {lims[2]:.0f} (Notice 2025-67 n-25-67.txt:140-160): the saver's credit has no engine input (no contribution variable); not in the engine's answer.")
    # AOTC flags
    if any(p.b("attends_eligible_educational_institution_for_american_opportunity_credit") for p in persons):
        add("income_tax", "reading", "AOTC eligibility flags are stated but no qualified tuition or related expenses (preface: unlisted expenses are 0): American opportunity credit 0; the engine has no AOTC input in any case.")
    # CDCC
    if h["spm"].get("spm_unit_pre_subsidy_childcare_expenses"):
        kids13 = [p for p in d["deps"] if p.age < 13]
        exp = f(h["spm"]["spm_unit_pre_subsidy_childcare_expenses"])
        cap = 3000.0 if len(kids13) == 1 else (6000.0 if len(kids13) >= 2 else 0.0)
        earned = [max(0.0, d["comp_wages"][p.name] + d["se_by_person"][p.name]) for p in filers_main]
        lim = min([exp, cap] + earned)
        rate = cdcc_rate_2026(agi, joint)
        add("income_tax", "engine_behaviour", f"childcare {exp:.2f} with {len(kids13)} child(ren) under 13: the engine's 2026 CDCC is 0 for any input (probe7); statute (26 USC 21, 2026 rates lii_26usc21.txt:5-9): {rate:.0%} x min(expenses, cap {cap:.0f}, lower earner's earned income) = {rate*lim:.2f} before the tax-liability limit. Engine answer kept.")
    # EITC
    n_kids = sum(1 for p in d["deps"] if p.age < 19 or p.b("is_disabled"))
    dis_adult = [p for p in d["deps"] if p.age >= 19 and p.b("is_disabled")]
    earned = sum(max(0.0, d["comp_wages"][p.name]) for p in filers_main) + sum(d["se_by_person"][p.name] for p in filers_main)
    inv = m["rec"]["intrec"] + m["rec"]["dividends"] + max(0.0, m["rec"]["ltcg"] + m["rec"]["stcg"])
    if dis_adult:
        with_d = statutory_eitc(n_kids, max(0.0, earned), agi, joint, inv)
        without_d = statutory_eitc(n_kids - len(dis_adult), max(0.0, earned), agi, joint, inv)
        if abs(with_d - without_d) >= 0.005:
            add("income_tax", "unexpressed", f"disabled dependent(s) aged 19+ ({', '.join(f'{p.name} age {p.age}' for p in dis_adult)}): a permanently and totally disabled child is an EITC qualifying child at any age (26 USC 32(c)(3)(A), lii_26usc32.txt:94, via 152(c)(3)(B), lii_26usc152.txt:44), but the engine has no disability input and counts EITC children by age (to 18, probe4). Statutory EITC with this child ~{with_d:.2f}, without ~{without_d:.2f}. Engine answer kept.")
        else:
            add("income_tax", "unexpressed", f"disabled dependent(s) aged 19+ ({', '.join(f'{p.name} age {p.age}' for p in dis_adult)}): EITC qualifying child at any age under 26 USC 32(c)(3)(A) and 152(c)(3)(B) (lii_26usc152.txt:44); the engine has no disability input, but at this income the statutory EITC is the same either way ({with_d:.2f}).")
    if A["v25"] > 0 or n_kids:
        law = statutory_eitc(n_kids, max(0.0, earned), agi, joint, inv)
        if n_kids and (A["v25"] > 0 or law > 0):
            add("income_tax", "engine_behaviour", f"EITC: engine v25 = {A['v25']:.2f}; the 2026 build applies 7.65% phase-in and phase-out rates to every family size (probe2/probe3). Rev. Proc. 2025-32 schedule (rp-25-32.txt:634-655, 32(b)(1) rates) with {min(n_kids,3)} qualifying child(ren), earned income ~{earned:.2f} (before the SE-tax deduction) and AGI {agi:.2f}: ~{law:.2f}. Engine answer kept.")
    # 17-year-old CTC
    if any(p.age == 17 for p in d["deps"]):
        add("income_tax", "engine_behaviour", "a dependent aged 17: the engine gives the full $2,200 CTC to ages 0-17 (probe4); 26 USC 24(c)(1) requires the child not to have attained 17. Engine answer kept; see the code_age17_as_18 alternative below.")
    # SALT cap parameters
    if m["rec"]["proptax"] > 10000 and (m["rec"]["proptax"] > 40000 or agi > 500000) and itemizes:
        add("income_tax", "engine_behaviour", f"SALT {m['rec']['proptax']:.2f} at AGI {agi:.2f}: the engine caps proptax with the 2025 amounts (40,000; phase-down from 500,000; probe5/probe8); 2026 law is 40,400 and 505,000 (26 USC 164(b)(7), lii_26usc164.txt:76,88).")
    # 37% bracket haircut
    thr37 = 768700.0 if joint else 640600.0
    if itemizes and A["v18"] > thr37:
        add("income_tax", "engine_behaviour", "itemizer in the 37% bracket: the engine does not apply the 2026 2/37 reduction of 26 USC 68 (probe5 #7).")
    # SE tax below 400 and QBI minimum
    se_net_total = sum(d["se_by_person"][p.name] for p in filers_main)
    for p in filers_main:
        net = d["se_by_person"][p.name]
        if 0 < net * 0.9235 < LAW["se_floor"]:
            add("self_employment", "engine_behaviour", f"{p.name}: net earnings from self-employment {net*0.9235:.2f} are under $400, so 26 USC 1402(b)(2) gives no SE tax; the engine still charges 15.3% (probe8 #1-3). Engine answer kept.")
    if se_net_total >= LAW["qbi_min_threshold"] and A["qbid"] < LAW["qbi_min"] and A["v18"] > 0:
        add("income_tax", "unexpressed", f"QBI deduction: engine qbid {A['qbid']:.2f} is below the 2026 $400 minimum of 26 USC 199A(i) for active QBI of at least $1,000 (lii_26usc199A.txt:280-290); material participation is not stated, so whether 199A(i) applies is itself open; the engine does not apply it.")
    # section 22 credit for the elderly and the permanently and totally disabled (lii_26usc22.txt)
    q22 = [p for p in filers_main if p.age >= 65 or (p.b("is_disabled") and R["disability_taxable"] and p.g("disability_benefits") > 0)]
    if q22:
        init = 7500.0 if (joint and len(q22) == 2) else 5000.0  # 22(c)(2)(A), lines 14-17
        under = [p for p in q22 if p.age < 65]
        if under:  # 22(c)(2)(B), lines 20-28: cap at disability income
            dis_inc = sum(p.g("disability_benefits") for p in under)
            init = min(init, 5000.0 + dis_inc) if (joint and len(q22) == 2 and len(under) == 1) else min(init, dis_inc)
        nontax_ss = max(0.0, m["rec"]["gssi"] - A["v12"])
        va = sum(p.g("veterans_benefits") for p in filers_main)
        agi_red = 0.5 * max(0.0, agi - (10000.0 if joint else 7500.0))  # 22(d), lines 44-51
        amt22 = max(0.0, init - nontax_ss - va - agi_red)  # 22(c)(3), lines 30-40
        cr22 = 0.15 * amt22
        if cr22 > 0 and A["v28"] > 0:
            add("income_tax", "unexpressed", f"section 22 credit: qualified {', '.join(p.name for p in q22)}; initial amount {init:.2f} less nontaxable Social Security {nontax_ss:.2f}, VA benefits {va:.2f} and half of AGI over the limit {agi_red:.2f} = {amt22:.2f}; credit 15% = {cr22:.2f} against tax {A['v28']:.2f}. The engine has no disability input and no section 22 line; not in its answer.")
        elif A["v28"] > 0:
            add("income_tax", "computed_from_statute", f"section 22 credit: qualified {', '.join(p.name for p in q22)}; initial amount {init:.2f} less nontaxable Social Security {nontax_ss:.2f}, VA benefits {va:.2f} and half of AGI over {'10,000' if joint else '7,500'} ({agi_red:.2f}) leaves 0 (26 USC 22(c),(d), lii_26usc22.txt:12-51): no credit.")
    # filing-status facts that change nothing
    for p in filers_main:
        if p.b("is_surviving_spouse"):
            if joint:
                add("income_tax", "reading", f"{p.name} is_surviving_spouse with a spouse on the return: read as remarried; joint return (mstat 2).")
            elif any(q.age < 19 or q.b("is_disabled") for q in d["deps"]):
                add("income_tax", "reading", f"{p.name} is_surviving_spouse with a dependent child: the year of the spouse's death is not stated, so the 26 USC 2(a) surviving-spouse status (lii_26usc2.txt:2-7) is not taken; the engine assigns head of household (doc: unmarried with dependents).")
            else:
                add("income_tax", "reading", f"{p.name} is_surviving_spouse: no dependent son or daughter lives in the household, so the 26 USC 2(a)(1)(B) test (lii_26usc2.txt:7) fails; single return (mstat 1).")
        if p.b("is_unmarried_partner_of_household_head") and p is d["head"]:
            add("income_tax", "reading", f"{p.name} carries is_unmarried_partner_of_household_head but is the only adult and the tax-unit head; no spouse or dependent follows from it; single return.")
    ube = sum(p.g("unreimbursed_business_employee_expenses") for p in persons)
    if ube:
        add("income_tax", "reading", f"unreimbursed_business_employee_expenses {ube:.2f}: miscellaneous itemized deductions are disallowed for years after 2017 (26 USC 67(h), lii_26usc67.txt:75-76), and no reservist, performing-artist, fee-basis-official or educator status is stated for the above-the-line exceptions of 62(a)(2); no deduction, not entered.")
    ubia = sum(max(p.g("unadjusted_basis_qualified_property"), p.g("sstb_unadjusted_basis_qualified_property")) for p in filers_main)
    if ubia:
        thr = 403500.0 if joint else 201750.0
        ti_before = A["v18"] + A["qbid"]
        if ti_before <= thr:
            add("income_tax", "computed_from_statute", f"unadjusted_basis_qualified_property {ubia:.2f}: the W-2 wage and UBIA limitation of 26 USC 199A(b)(2)(B) applies only above the 2026 threshold {thr:.0f} (rp-25-32.txt:948-958; 199A(b)(3)); taxable income before the QBI deduction {ti_before:.2f} is below it, so UBIA has no effect (the engine has no UBIA input).")
        else:
            add("income_tax", "unexpressed", f"unadjusted_basis_qualified_property {ubia:.2f}: taxable income before the QBI deduction {ti_before:.2f} exceeds the 2026 threshold {thr:.0f}, where the W-2 wage and UBIA limitation of 26 USC 199A(b)(2)(B) applies; the engine has no input for business W-2 wages or UBIA.")
    return out


def main():
    hh = load_households()
    R = dict(DEFAULT_READINGS)
    D, filers = pipeline(hh, R, "default")
    ans = answers_from(D, filers, R)

    # ---- alternatives: rerun the whole pipeline under each alternative reading
    alt_results = {}
    for key, val in ALTERNATIVES:
        R2 = dict(DEFAULT_READINGS)
        R2[key] = val
        R2["_tag"] = f"alt_{key}"
        if key in ("niit_in_income_tax", "dependents_file"):
            alt_results[(key, val)] = answers_from(D, filers, R2)
        else:
            D2, f2 = pipeline(hh, R2, f"alt_{key}", write_runs=False)
            alt_results[(key, val)] = answers_from(D2, f2, R2)

    # ---- write inputs_2026.csv
    with open(HERE / "inputs_2026.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case_id", "record", "pass", "taxsimid", "year", "state"] + INPUT_COLS)
        tid = 0
        for cid, fl in filers:
            tid += 1
            rec = fl["rec"]
            w.writerow([cid, fl["role"], "A_income_tax", tid, YEAR, 0] + [r2(f(rec.get(c, 0))) for c in INPUT_COLS])
            w.writerow([cid, fl["role"], "B_payroll_wages_and_se", tid, YEAR, 0] + [r2(f(fl["recB"].get(c, 0))) for c in INPUT_COLS])
            w.writerow([cid, fl["role"], "C_payroll_wages_only", tid, YEAR, 0] + [r2(f(fl["recC"].get(c, 0))) for c in INPUT_COLS])

    # ---- answers
    with open(HERE / "answers_2026.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case_id", "quantity", "value", "formula"])
        for h in hh:
            for q, v in ans[h["id"]].items():
                w.writerow([h["id"], q, f"{v:.2f}", FORMULAS[q]])

    # ---- notes
    notes = []
    for h in hh:
        d = D[h["id"]]
        notes.extend(d["notes"])
        notes.extend(unexpressed_and_engine_notes(h, d, R))
        for (c, q), v in CLAMPED.get("default", {}).items():
            if c == h["id"]:
                notes.append(dict(case_id=c, quantity_group="income_tax" if q.startswith("federal_income") else "all",
                                  kind="engine_behaviour",
                                  text=f"{q}: the formula gives {v:.2f}, a cent-rounding residual (the engine rounds fiitax, v25 and actc to the cent separately; tax before credits v28 is 0). Reported as 0.00."))
        for (key, val), alt in alt_results.items():
            base = ans[h["id"]]
            a = alt[h["id"]]
            diffs = {q: (base[q], a[q]) for q in base if abs(base[q] - a[q]) >= 0.005}
            if diffs:
                txt = "; ".join(f"{q}: {b:.2f} -> {x:.2f}" for q, (b, x) in diffs.items())
                notes.append(dict(case_id=h["id"], quantity_group="all", kind="reading",
                                  text=f"ALTERNATIVE {key}={val} (default {DEFAULT_READINGS[key]}) moves: {txt}"))
        # engine per-record summary
        for c, fl in filers:
            if c != h["id"]:
                continue
            A = fl["A"]
            notes.append(dict(case_id=h["id"], quantity_group="all", kind="engine_behaviour",
                              text=f"record {fl['role']}: AGI v10 {A['v10']:.2f}; std/zero-bracket v13 {A['v13']:.2f}; itemized v17 {A['v17']:.2f}; taxable v18 {A['v18']:.2f}; tax before credits v28 {A['v28']:.2f}; AMT v27 {A['v27']:.2f}; CTC/ODC nonref v22 {A['v22']:.2f}; ACTC {A['actc']:.2f}; EITC v25 {A['v25']:.2f}; QBID {A['qbid']:.2f}; NIIT {A['niit']:.2f}; fiitax {A['fiitax']:.2f}; passB tfica {fl['B']['tfica']:.2f} addmed {fl['B']['addmed']:.2f}; passC tfica {fl['C']['tfica']:.2f} addmed {fl['C']['addmed']:.2f}"))
    with open(HERE / "notes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["case_id", "quantity_group", "kind", "text"])
        w.writeheader()
        for n in notes:
            w.writerow(n)
    print(f"households {len(hh)}; records {len(filers)}; answers {sum(len(v) for v in ans.values())}; notes {len(notes)}")


if __name__ == "__main__":
    main()
