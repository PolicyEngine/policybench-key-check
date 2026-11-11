"""Diff the second Tax-Calculator map against the first: engine inputs, then answers.

  envs/tc690/bin/python second_map/taxcalc/compare.py

Reads
  - the first map's committed record for the board at tax year 2026:
    results/taxcalc/board100_tc6.9.0_2026.csv (`in_*` inputs of the main return, `q_*` answers)
    and, for listed members with earnings of their own, the payroll-only return that
    keycheck/map_taxcalc.py `member_row` (commit 9507519) builds, rebuilt here from
    results/dossiers/<case>.json (`return_from_stated_facts` -> `members_with_own_payroll`);
  - the second map's files in this folder: inputs_2026.csv (main pass R5, one row per return),
    inputs_payroll_pass_2026.csv (payroll pass R6), answers_2026.csv, returns_2026.csv;
  - results/answers.csv for the committed key (run pb-reference-2.60.0; for the payroll line,
    which the key does not publish, the engine rerun pe-2.60.0-board-2026, as
    scripts/agreement.py does) and the rerun.

Alignment. Both maps use Tax-Calculator's own input names, so no renaming is needed. A record
is a return: `main` for the household's return, `dependent:<name>` for a listed member's own
return (the second map's name for it; the first map's member returns take the same name).
Tax-Calculator zero-fills every input a row leaves out (taxcalc/data.py:247-262), so an input
one map does not send counts as 0. RECID and FLPDYR are bookkeeping and are left out. The
second map's payroll pass differs from its main pass only in e00200p/s; its inputs enter the
diff only where they differ from the main pass, and there they equal the first map's.

Each differing input gets a cause from the stated facts and the variable (`cause_of`), and
each cause a ruling (RULINGS: class and reason). The program stops on a difference with no
ruling. Classes: `second_map_errs` and `first_map_errs` (that map's input departs from the
law, or from the board's rule that an unlisted fact, boolean or status is false, which
prompts.py:24-26 gives every answerer), `reading` (the maps read a fact the household does not
state differently, the board's rule does not settle it, and both readings are defensible),
`engine_path` (the maps handle a missing engine input differently), `representation` (the
same treatment in different inputs; moves no line).

`moves_a_line` comes from Tax-Calculator runs: the first map's main row with one cause's inputs
set to the second map's values (main pass values for the first three lines, payroll pass
values for the payroll line), under the first map's line formulas and engine settings
(scripts/run_taxcalc.py); "yes" when any line moves by more than $1. The answers diff splits
each household's difference into these per-cause effects, plus the dependents' own returns
the second map adds to its income-tax and refundable-credit lines, plus a residual (input
rounding to cents in the second map's files and interactions among causes).

Writes results/second_map/taxcalc_inputs_diff.csv and results/second_map/taxcalc_answers_diff.csv.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd
from taxcalc import Calculator, Policy, Records

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
YEAR = 2026
INPUT_TOLERANCE = 0.01
ANSWER_TOLERANCE = 1.0
LINES = (
    "federal_income_tax_before_refundable_credits",
    "federal_refundable_credits",
    "self_employment_tax",
    "federal_employee_payroll_tax",
)
FIRST_COLUMNS = {
    "federal_income_tax_before_refundable_credits": "q_fed_tax_before_refundable",
    "federal_refundable_credits": "q_refundable_credits",
    "self_employment_tax": "q_self_employment_tax",
    "federal_employee_payroll_tax": "q_fed_employee_payroll_tax",
}
SHORT = {LINES[0]: "income tax", LINES[1]: "refundable credits", LINES[2]: "SE tax", LINES[3]: "payroll"}
KEY_RUN, RERUN = "pb-reference-2.60.0", "pe-2.60.0-board-2026"
BOOKKEEPING = {"RECID", "FLPDYR"}
WAGES = ("e00200", "e00200p", "e00200s")

RULINGS = {
    "ubi_counts": (
        "representation",
        "The second map sends the counts of people aged 18-20 and 21 or over (n1820, n21); "
        "Tax-Calculator reads them only in its universal basic income (calcfunctions.py:659-708), "
        "zero under current law. The first map leaves them unsent, so 0.",
    ),
    "auto_loan_interest": (
        "second_map_errs",
        "Stated household auto loan interest. The deduction for qualified passenger vehicle loan "
        "interest (26 U.S.C. 163(h)(4)) needs facts the board never states: a new vehicle whose "
        "first use began with the taxpayer, final assembly in the United States, a loan taken "
        "out after 2024. The board's prompt makes every unlisted household fact false "
        "(work/policybench-c7ede86c/policybench/prompts.py:24-26). First map: not qualified; "
        "sends 0. Second map: takes the eligibility facts as met and sends the stated amount, "
        "against that rule: the second map errs.",
    ),
    "disability_under_65": (
        "reading",
        "Employer disability benefits of a filer or member under 65, taxable in both maps "
        "(26 U.S.C. 105(a)). First map: unearned other income (e01200). Second map: Form 1040 "
        "line 1h earned income (e00200; second_map/taxcalc/sources/i1040gi.txt:1536-1541), "
        "taken out of FICA wages in its payroll pass. IRS Pub. 596 (2025), 'Disability Benefits', "
        "makes them earned income until the plan's minimum retirement age and a pension after "
        "it; the board states no minimum retirement age, so both readings are defensible.",
    ),
    "disability_65_plus": (
        "representation",
        "Employer disability benefits of a filer 65 or older, unearned and taxable in both maps: "
        "the first sends them as e01200, the second as a pension (e01500 and e01700, Form 1040 "
        "lines 5a and 5b). Tax-Calculator treats both as unearned income that enters AGI only "
        "(calcfunctions.py:534-544), so no line moves.",
    ),
    "survivor_benefits": (
        "first_map_errs",
        "Stated survivor benefits other than Social Security. Gross income includes a survivor "
        "annuity (26 U.S.C. 61(a), 72); the exclusions need a fact the board does not state "
        "(life insurance proceeds, 101(a); a veterans' benefit, 38 U.S.C. 5301), and the board's "
        "prompt makes unlisted facts false (prompts.py:24-26). Second map: a taxable survivor "
        "annuity (e01500 and e01700). First map: not taxable, following the board's own "
        "reference reading rather than the law: the first map errs.",
    ),
    "deferral_split": (
        "reading",
        "Desired traditional plus Roth 401(k) deferrals above the 26 U.S.C. 402(g) limit. First "
        "map: scales both in proportion to the limit. Second map: traditional deferrals fill the "
        "limit before Roth. The statute caps the total and the board does not state which "
        "deferral stops, so both readings are defensible.",
    ),
    "miscellaneous_income": (
        "engine_path",
        "Stated miscellaneous income (26 CFR 1.61-14; Form 1040 Schedule 1 line 8z). "
        "Tax-Calculator has no line 8z input. First map: sends it as e01200, which enters AGI "
        "and nothing else (calcfunctions.py:534-544; NIIT leaves it out, calcfunctions.py:2715-2724; "
        "so does the EITC investment-income test, calcfunctions.py:3231-3232), which is the "
        "line 8z treatment. Second map: leaves it out of the engine. The first map's path gives "
        "the law's answer; the second map's answer omits gross income.",
    ),
    "disabled_worker_dependency": (
        "second_map_errs",
        "A listed adult stated disabled who earns wages of their own. Second map: a qualifying "
        "child at any age under 26 U.S.C. 152(c)(3)(B), so the main return counts a $500 credit "
        "for other dependents (XTOT) and an EITC child. First map: not permanently and totally "
        "disabled, since 22(e)(3) requires inability to engage in any substantial gainful "
        "activity (second_map/taxcalc/sources/usc26_22.txt:58), and with gross income over "
        "$5,300 not a qualifying relative, so not claimed. Full-time wages of $45,000 are "
        "substantial gainful activity: the second map errs.",
    ),
    "early_distribution_tax": (
        "first_map_errs",
        "Taxable 401(k) distributions of a filer under 59 1/2. Second map: the 26 U.S.C. 72(t)(1) "
        "10% additional tax (e09900), after testing the computable medical exception. First map: "
        "no additional tax, reading 'no exception or its absence is stated'. The board makes "
        "unlisted statuses false, so no exception holds, and 72(t)(1) raises the tax 'under this "
        "chapter' (second_map/taxcalc/sources/usc26_72.txt:516-517), which both maps' income-tax "
        "formula (c09200 - setax - ptax_amc, calcfunctions.py:4514-4529) counts. The first map errs.",
    ),
    "passive_loss": (
        "first_map_errs",
        "A net loss from rentals and farm rent at modified AGI near $199,000. Second map: "
        "suspends it under 26 U.S.C. 469: a rental is a passive activity (469(c)(2), "
        "second_map/taxcalc/sources/usc26_469.txt:24-25) and the $25,000 allowance of 469(i) "
        "falls by half of the excess over $100,000 (usc26_469.txt:164-171), to nothing here; "
        "Schedule E carries 0. First map: deducts the loss (its code applies no section 469 "
        "limit). The first map errs.",
    ),
    "farm_rent_qbi": (
        "first_map_errs",
        "Farm rent with no stated UBIA. Qualified business income comes only from a qualified "
        "trade or business (26 U.S.C. 199A(c)(1), (d)(1)), and whether a farm rental is one goes "
        "unstated, so under the board's rule (prompts.py:24-26) it is not. Second map: counts "
        "farm rent as QBI only beside stated UBIA. First map: sends all farm rent as e27200, "
        "which Tax-Calculator counts as QBI (calcfunctions.py:1796), against its own reading "
        "that rent is not QBI: the first map errs. With no other QBI in these households, no "
        "line moves.",
    ),
    "hsa_limit": (
        "first_map_errs",
        "A stated HSA deduction above every 26 U.S.C. 223(b) limit for the filer's age. Second map: "
        "the self-only limit, $4,400 for 2026 (second_map/taxcalc/sources/rp-25-19.txt:41-45). "
        "First map: the stated amount, unlimited. The family limit ($8,750) also falls below the "
        "stated amount, so the first map errs; the filer owes no income tax either way.",
    ),
    "self_employed_health_insurance": (
        "first_map_errs",
        "Person-paid premiums of a Schedule C filer with no employer coverage. Second map: the "
        "26 U.S.C. 162(l) deduction (e03270), taken out of medical expenses (e17500). First map: "
        "itemized medical expenses, reading the plan's establishment under the business as "
        "unstated. The 2025 Instructions for Form 7206 accept a policy in the individual's own "
        "name for a Schedule C or F business, so the first map errs; no line moves.",
    ),
    "bdc_reit_dividends": (
        "reading",
        "Stated business development company dividends or REIT and PTP income. First map: BDC "
        "dividends sit inside the stated dividends, and REIT/PTP income has no input (no section "
        "199A(b)(1)(B) input), so neither is added. Second map: adds them to ordinary dividends "
        "(e00600). The board does not say whether its stated dividends include them, so both "
        "readings are defensible.",
    ),
    "sstb_loss_flag": (
        "first_map_errs",
        "The filer's only business is a specified service trade or business with a loss. Second "
        "map: PT_SSTB_income 1. First map: 0, because its rule flags an SSTB only when the SSTB "
        "amount is positive (keycheck/map_taxcalc.py: PT_SSTB_income). Section 199A(d)(3) treats "
        "SSTB losses like SSTB income, so the flag errs; this household falls below the section "
        "199A threshold and has no positive QBI, so no line moves.",
    ),
    "sstb_ubia_only": (
        "reading",
        "Stated UBIA allocable to a specified service trade or business, with no SSTB income "
        "stated, beside partnership income. Second map: reads the business as an SSTB and sends "
        "the UBIA. First map: no SSTB (an unlisted status is false) and no UBIA. Both readings "
        "are defensible; the household's income falls below the section 199A threshold, so no "
        "line moves.",
    ),
    "qualified_tips": (
        "second_map_errs",
        "Stated tips, inside the stated wages in both maps. The deduction for qualified tips "
        "(26 U.S.C. 224) needs an occupation that customarily received tips, which the board "
        "does not state and its prompt makes false (prompts.py:24-26). First map: tip_income 0. "
        "Second map: takes the tips as qualified and sends them as tip_income: the second map "
        "errs. The filer owes no income tax either way.",
    ),
    "member_return_counts": (
        "representation",
        "A listed member's own return. The first map builds it for payroll and self-employment "
        "tax only (XTOT 0, no age counts); the second map files it in full and counts the member "
        "(XTOT, n21 or nu18). The counts move no line of that return.",
    ),
    "dependent_own_return": (
        "reading",
        "A dependent whose only income the first map treats as unearned (disability benefits). "
        "Second map: files the dependent's own return, with the disability pay as wages there and "
        "out of its payroll pass. First map: builds no return for the member, since its "
        "income-tax line counts the main return only. The return owes nothing, so no line moves.",
    ),
}
# Answer-level cause with no input of its own: which returns the income-tax line sums.
OWN_RETURNS = (
    "reading",
    "The second map adds the income tax and refundable credits of the returns that listed "
    "dependents with income file themselves; the first map's income-tax line counts the main "
    "return only. The board's prompt puts all listed people 'in one household group for tax and "
    "benefit calculations' and assumes filing 'when required' "
    "(work/policybench-c7ede86c/policybench/prompts.py:15-28), so both readings are defensible.",
)
UBI_COUNTS = ("n21", "n1820", "elderly_dependents")
DEPENDENT_COUNTS = ("XTOT", "EIC", "n24", "nu06", "nu13", "nu18", "f2441")


def num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def amount(person: dict, key: str) -> float:
    if key == "employment_income":
        return num(person.get("employment_income"))
    return num(person.get("inputs", {}).get(key))


def member_row(member: dict) -> dict:
    """keycheck/map_taxcalc.py member_row at commit 9507519."""
    return {
        "MARS": 1, "XTOT": 0, "DSI": 1, "age_head": member["age"],
        "e00200p": member["wages"], "e00200": member["wages"],
        "e00900p": member["self_employment"], "e00900": member["self_employment"],
    }


def load_first():
    rows, answers, facts, members = {}, {}, {}, {}
    with open(ROOT / "results/taxcalc/board100_tc6.9.0_2026.csv", newline="") as handle:
        for record in csv.DictReader(handle):
            case = record["case_id"]
            rows[(case, "main")] = {
                k[3:]: num(v) for k, v in record.items() if k.startswith("in_") and k[3:] not in BOOKKEEPING
            }
            answers[case] = {line: num(record[col]) for line, col in FIRST_COLUMNS.items()}
            members[case] = (num(record["members_fed_employee_payroll_tax"]), num(record["members_self_employment_tax"]))
            dossier = json.loads((ROOT / f"results/dossiers/{case}.json").read_text())
            facts[case] = dossier["stated_facts"]
            for member in dossier["return_from_stated_facts"][str(YEAR)]["members_with_own_payroll"]:
                rows[(case, "dependent:" + member["name"])] = member_row(member)
    return rows, answers, facts, members


def read_rows(name: str) -> dict:
    with open(HERE / name, newline="") as handle:
        return {
            (r["case_id"], r["record"]): {k: num(v) for k, v in r.items() if k not in {"case_id", "record"} | BOOKKEEPING}
            for r in csv.DictReader(handle)
        }


def load_second():
    main_pass = read_rows("inputs_2026.csv")
    payroll_pass = read_rows("inputs_payroll_pass_2026.csv")
    answers: dict = {}
    with open(HERE / "answers_2026.csv", newline="") as handle:
        for r in csv.DictReader(handle):
            answers.setdefault(r["case_id"], {})[r["quantity"]] = num(r["value"])
    return main_pass, payroll_pass, answers


def load_key():
    key, rerun = {}, {}
    with open(ROOT / "results/answers.csv", newline="") as handle:
        for r in csv.DictReader(handle):
            if r["case_set"] != "board-100" or r["period"] != str(YEAR):
                continue
            k = (r["case_id"], r["quantity"])
            if r["run"] == KEY_RUN and r["status"] == "ok":
                key[k] = num(r["value"])
            if r["run"] == RERUN and r["status"] == "ok":
                rerun[k] = num(r["value"])
    return key, rerun


def run(rows: list[dict]) -> list[dict]:
    """Tax-Calculator 6.9.0 at 2026 current law with the first map's settings."""
    frame = pd.DataFrame(rows).fillna(0)
    frame["RECID"] = range(1, len(frame) + 1)
    frame["FLPDYR"] = YEAR
    records = Records(data=frame, start_year=YEAR, gfactors=None, weights=None, exact_calculations=True)
    policy = Policy()
    policy.implement_reform({
        "eitc_claim_prob_scale": {YEAR: 9e99}, "actc_claim_prob_scale": {YEAR: 9e99},
        "eitc_claim_prob_min": {YEAR: 1.0}, "actc_claim_prob_min": {YEAR: 1.0},
    })
    policy.set_year(YEAR)
    calculator = Calculator(policy=policy, records=records)
    if calculator.current_year != YEAR:
        raise SystemExit(f"calculator at {calculator.current_year}")
    calculator.calc_all()
    out = []
    for i in range(len(rows)):
        get = lambda name: float(calculator.array(name)[i])  # noqa: E731
        out.append({
            LINES[0]: get("c09200") - get("setax") - get("ptax_amc"),
            LINES[1]: get("refund"),
            LINES[2]: get("setax"),
            LINES[3]: get("ptax_was") - get("ptax_er_p") - get("ptax_er_s") + get("ptax_amc"),
        })
    return out


def fact_causes(facts: dict) -> dict[str, str]:
    """Input variables that a stated fact leads the two maps to send differently, with the
    cause. A difference in any other variable has no ruling and stops the program."""
    people = facts["adults"] + facts["children"]
    filers = [p for p in people if p["name"] in ("head", "spouse")]
    members = [p for p in people if p["name"] not in ("head", "spouse")]
    causes: dict[str, str] = {v: "ubi_counts" for v in UBI_COUNTS}

    def claim(variables, cause):
        for variable in variables:
            if causes.get(variable, cause) != cause:
                raise SystemExit(f"{facts['id']}: {variable} has two causes, {causes[variable]} and {cause}")
            causes[variable] = cause

    def any_filer(key):
        return any(amount(p, key) for p in filers)

    for person in filers:
        if amount(person, "disability_benefits"):
            if int(person["age"]) < 65:
                claim(WAGES + ("e01200",), "disability_under_65")
            else:
                claim(("e01200", "e01500", "e01700"), "disability_65_plus")
        if amount(person, "survivor_benefits"):
            claim(("e01500", "e01700"), "survivor_benefits")
        if amount(person, "miscellaneous_income"):
            claim(("e01200",), "miscellaneous_income")
        if amount(person, "sstb_self_employment_income_before_lsr") < 0:
            claim(("PT_SSTB_income", "PT_ubia_property"), "sstb_loss_flag")
        elif (amount(person, "sstb_unadjusted_basis_qualified_property")
              and not amount(person, "sstb_self_employment_income_before_lsr")):
            claim(("PT_SSTB_income", "PT_ubia_property"), "sstb_ubia_only")
        if (amount(person, "roth_401k_contributions_desired") > 0
                and amount(person, "traditional_401k_contributions_desired") > 0):
            claim(WAGES + ("pencon_p", "pencon_s"), "deferral_split")
        if int(person["age"]) < 60 and any(amount(person, k) for k in (
                "taxable_401k_distributions", "taxable_403b_distributions",
                "taxable_ira_distributions", "taxable_private_pension_income")):
            claim(("e09900",), "early_distribution_tax")
        self_employed = sum(amount(person, k) for k in (
            "self_employment_income", "sstb_self_employment_income_before_lsr", "farm_operations_income"))
        if self_employed > 0 and (amount(person, "health_insurance_premiums_without_medicare_part_b")
                                  or amount(person, "other_health_insurance_premiums")):
            claim(("e03270", "e17500"), "self_employed_health_insurance")
    if num(facts.get("household_inputs", {}).get("auto_loan_interest")):
        claim(("auto_loan_interest",), "auto_loan_interest")
    if num(facts.get("tax_unit_inputs", {}).get("health_savings_account_ald")):
        claim(("e03290",), "hsa_limit")
    if any_filer("tip_income"):
        claim(("tip_income",), "qualified_tips")
    if any_filer("qualified_bdc_income") or any_filer("qualified_reit_and_ptp_income"):
        claim(("e00600",), "bdc_reit_dividends")
    if sum(amount(p, "rental_income") + amount(p, "farm_rent_income") for p in filers) < 0:
        claim(("e02000",), "passive_loss")
    if any_filer("farm_rent_income") and not any_filer("unadjusted_basis_qualified_property"):
        claim(("e27200",), "farm_rent_qbi")
    if any(p.get("inputs", {}).get("is_disabled") for p in members
           if amount(p, "employment_income") > 0 or amount(p, "self_employment_income") > 0):
        claim(DEPENDENT_COUNTS, "disabled_worker_dependency")
    return causes


def cause_of(case: str, record: str, variable: str, first_rows: dict, from_facts: dict) -> str:
    if record != "main":
        if (case, record) not in first_rows:
            return "dependent_own_return"
        return "member_return_counts" if variable in ("XTOT", "nu18") + UBI_COUNTS else "UNRULED"
    return from_facts.get(variable, "UNRULED")


def fmt(value: float) -> str:
    return f"{value:.2f}"


def effect_text(effect: dict) -> str:
    moved = [f"{SHORT[line]} {effect[line]:+,.2f}" for line in LINES if abs(effect[line]) > 0.005]
    return "moves " + ", ".join(moved) if moved else "moves no line"


def run_text(record: str, cause: str, effect: dict) -> str:
    """What the run behind moves_a_line did, in one sentence."""
    if record == "main":
        return f"Run: the first map's return with this cause's inputs from the second map {effect_text(effect)}."
    if cause == "member_return_counts":
        return f"Run: the second map's return for this member with the first map's counts {effect_text(effect)}."
    owed = [f"{SHORT[line]} {effect[line]:,.2f}" for line in LINES]
    return "Run: the return the second map alone files gives " + ", ".join(owed) + " (payroll from its payroll pass)."


def main() -> None:
    first_rows, first_answers, facts, first_members = load_first()
    second_rows, payroll_rows, second_answers = load_second()
    key, rerun = load_key()
    cases = sorted(first_answers)
    if sorted(second_answers) != cases:
        raise SystemExit("the two maps answer different households")

    # 1. Inputs, record by record and variable by variable.
    diffs = []
    for record_key in sorted(set(first_rows) | set(second_rows)):
        case, record = record_key
        a, b = first_rows.get(record_key), second_rows.get(record_key)
        causes = fact_causes(facts[case])
        variables = sorted(set(a or {}) | set(b or {}))
        for variable in variables:
            x = None if a is None else a.get(variable, 0.0)
            y = None if b is None else b.get(variable, 0.0)
            if a is None or b is None:
                if abs(x or y or 0.0) <= INPUT_TOLERANCE:
                    continue
            elif abs(x - y) <= INPUT_TOLERANCE:
                continue
            diffs.append({"case_id": case, "record": record, "variable": variable, "x": x, "y": y,
                          "cause": cause_of(case, record, variable, first_rows, causes)})
        # Payroll pass: only where it differs from the main pass, and there it must equal the first map.
        if b is not None and record_key in payroll_rows:
            for variable, value in payroll_rows[record_key].items():
                if abs(value - b.get(variable, 0.0)) > INPUT_TOLERANCE and a is not None:
                    if abs(value - a.get(variable, 0.0)) > INPUT_TOLERANCE:
                        raise SystemExit(f"{record_key} {variable}: payroll pass differs from the first map")
    unruled = [d for d in diffs if d["cause"] not in RULINGS]
    if unruled:
        raise SystemExit("no ruling for: " + "; ".join(f"{d['case_id']} {d['record']} {d['variable']}" for d in unruled))

    # 2. Runs: each map's returns as sent (to check both answer files), and each cause's swap.
    batch, tags = [], []

    def add(tag, row):
        batch.append(dict(row)); tags.append(tag)

    for (case, record), row in first_rows.items():
        add(("first", case, record), row)
    for (case, record), row in second_rows.items():
        add(("second", case, record), row)
        add(("second_payroll", case, record), payroll_rows[(case, record)])
    groups: dict = {}
    for d in diffs:
        groups.setdefault((d["case_id"], d["record"], d["cause"]), []).append(d["variable"])
    for (case, record, cause), variables in groups.items():
        if record == "main":
            income_row = dict(first_rows[(case, record)])
            payroll_row = dict(first_rows[(case, record)])
            for variable in variables:
                income_row[variable] = second_rows[(case, record)].get(variable, 0.0)
                payroll_row[variable] = payroll_rows[(case, record)].get(variable, 0.0)
            add(("swap_income", case, record, cause), income_row)
            add(("swap_payroll", case, record, cause), payroll_row)
        elif cause == "member_return_counts":
            row = dict(second_rows[(case, record)])
            payroll_row = dict(payroll_rows[(case, record)])
            for variable in variables:
                row[variable] = first_rows[(case, record)].get(variable, 0.0)
                payroll_row[variable] = first_rows[(case, record)].get(variable, 0.0)
            add(("swap_member", case, record, cause), row)
            add(("swap_member_payroll", case, record, cause), payroll_row)
    results = dict(zip(tags, run(batch)))

    def first_line(case, line):
        main = results[("first", case, "main")][line]
        if line == LINES[2]:
            return main + first_members[case][1]
        if line == LINES[3]:
            return main + first_members[case][0]
        return main

    def second_line(case, line, records_only=None):
        total = 0.0
        for (c, record) in second_rows:
            if c != case or (records_only and record not in records_only):
                continue
            source = ("second_payroll", c, record) if line == LINES[3] else ("second", c, record)
            total += results[source][line]
        return total

    for case in cases:
        member_records = [r for (c, r) in first_rows if c == case and r != "main"]
        payroll = sum(results[("first", case, r)][LINES[3]] for r in member_records)
        setax = sum(results[("first", case, r)][LINES[2]] for r in member_records)
        if abs(payroll - first_members[case][0]) > 0.01 or abs(setax - first_members[case][1]) > 0.01:
            raise SystemExit(f"{case}: rebuilt member returns do not reproduce the first map's member columns")
        for line in LINES:
            if abs(first_line(case, line) - first_answers[case][line]) > 0.01:
                raise SystemExit(f"{case} {line}: first map's inputs do not reproduce its answer")
            if abs(second_line(case, line) - second_answers[case][line]) > 0.01:
                raise SystemExit(f"{case} {line}: second map's inputs do not reproduce its answer")

    effects: dict = {}
    for (case, record, cause), variables in groups.items():
        if record == "main":
            base = results[("first", case, "main")]
            income, payroll = results[("swap_income", case, record, cause)], results[("swap_payroll", case, record, cause)]
            effect = {line: income[line] - base[line] for line in LINES[:3]}
            effect[LINES[3]] = payroll[LINES[3]] - base[LINES[3]]
        elif cause == "member_return_counts":
            sent, swapped = results[("second", case, record)], results[("swap_member", case, record, cause)]
            effect = {line: sent[line] - swapped[line] for line in LINES[:3]}
            effect[LINES[3]] = (results[("second_payroll", case, record)][LINES[3]]
                                - results[("swap_member_payroll", case, record, cause)][LINES[3]])
        else:  # dependent_own_return: the whole return the second map alone files
            effect = {line: results[("second", case, record)][line] for line in LINES[:3]}
            effect[LINES[3]] = results[("second_payroll", case, record)][LINES[3]]
        effects[(case, record, cause)] = effect

    out = ROOT / "results/second_map"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "taxcalc_inputs_diff.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "record", "variable", "first_map", "second_map", "difference",
                         "cause", "class", "moves_a_line", "explanation"])
        for d in diffs:
            effect = effects[(d["case_id"], d["record"], d["cause"])]
            moves = any(abs(v) > ANSWER_TOLERANCE for v in effect.values())
            klass, reason = RULINGS[d["cause"]]
            first_value = "" if d["x"] is None else fmt(d["x"])
            second_value = "" if d["y"] is None else fmt(d["y"])
            difference = (d["y"] or 0.0) - (d["x"] or 0.0)
            absent = " The first map files no such return." if d["x"] is None else ""
            writer.writerow([d["case_id"], d["record"], d["variable"], first_value, second_value, fmt(difference),
                             d["cause"], klass, "yes" if moves else "no",
                             f"{reason}{absent} {run_text(d['record'], d['cause'], effect)}"])

    # 3. Answers.
    with open(out / "taxcalc_answers_diff.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "line", "first_map", "second_map", "difference", "key", "key_run", "rerun",
                         "first_agrees_key", "second_agrees_key", "maps_agree", "class", "components", "explanation"])
        for case in cases:
            dependents = [r for (c, r) in second_rows if c == case and r != "main"]
            for line in LINES:
                a, b = first_answers[case][line], second_answers[case][line]
                k = key.get((case, line))
                key_run = KEY_RUN
                if k is None:
                    k, key_run = rerun[(case, line)], RERUN
                parts = []  # (cause, class, amount)
                for (c, record, cause), effect in effects.items():
                    if c == case and record == "main" and abs(effect[line]) > 0.005:
                        parts.append((cause, RULINGS[cause][0], effect[line]))
                if dependents:
                    if line in LINES[:2]:
                        own = second_line(case, line, dependents)
                        if abs(own) > 0.005:
                            parts.append(("own_returns_in_income_tax", OWN_RETURNS[0], own))
                    else:
                        index = 1 if line == LINES[2] else 0
                        own = second_line(case, line, dependents) - first_members[case][index]
                        if abs(own) > 0.005:
                            parts.append(("member_returns", "representation", own))
                residual = (b - a) - sum(p[2] for p in parts)
                if abs(residual) > ANSWER_TOLERANCE:
                    raise SystemExit(f"{case} {line}: causes leave {residual:.2f} unexplained")
                parts.sort(key=lambda p: -abs(p[2]))
                agree = abs(a - b) <= ANSWER_TOLERANCE
                if agree:
                    klass = "equal"
                else:
                    klass = "+".join(dict.fromkeys(p[1] for p in parts if abs(p[2]) > 0.005))
                components = "; ".join(f"{p[0]} ({p[1]}) {p[2]:+.2f}" for p in parts)
                if abs(residual) > 0.005:
                    components += ("; " if components else "") + f"rounding and interaction {residual:+.2f}"
                if agree:
                    explanation = "The maps agree within $1." + (" Inputs differ, but their effects stay within $1." if parts else "")
                else:
                    reasons = []
                    for cause, _, _ in parts:
                        reason = OWN_RETURNS[1] if cause == "own_returns_in_income_tax" else RULINGS.get(cause, ("", ""))[1]
                        if reason and reason not in reasons:
                            reasons.append(reason)
                    explanation = " ".join(reasons)
                writer.writerow([case, line, fmt(a), fmt(b), fmt(b - a), fmt(k), key_run, fmt(rerun[(case, line)]),
                                 "yes" if abs(a - k) <= ANSWER_TOLERANCE else "no",
                                 "yes" if abs(b - k) <= ANSWER_TOLERANCE else "no",
                                 "yes" if agree else "no", klass, components, explanation])
    print(f"wrote {len(diffs)} input differences and {len(cases) * len(LINES)} answer rows to {out}")


if __name__ == "__main__":
    sys.exit(main())
