"""Compare the second TAXSIM map with the first, input by input and answer by answer.

    python3 second_map/taxsim/compare.py [--binary work/nber/taxsimtest-osx.exe] [--probes]

Reads the first map's committed record for the board (results/taxsim/board100_cd2026110117_2026.csv
and results/dossiers/<case>.json), the second map's files (second_map/taxsim/inputs_2026.csv and
answers_2026.csv) and the answer table (results/answers.csv), and writes

    results/second_map/taxsim_inputs_diff.csv   one row per household, record and input that differs
    results/second_map/taxsim_answers_diff.csv  one row per household and line

Standard library only. It runs NBER's TAXSIM test build (scripts/get_taxsim.sh fetches it into
work/nber/) to say whether each input difference moves a line: it reruns the second map's own
records, checks that they give the second map's answers to the cent, then sets each group of
differing inputs to the first map's values and reruns. With every group set, the records must give
the first map's four answers; the script stops if they do not. `--probes` also prints the four
small probes the rulings cite (P1-P4).

How the two files come to one layout (the second map runs three passes and sends dependents by
age; the first map runs one record, sends dependents as counts and adds an EITC record where the
EITC children differ in number):

- Wages compare gross (FICA wages): the first map's `pwages`, the second map's pass C `pwages`.
  The traditional 401(k) deferral compares as its own variable per filer (`p_deferral`,
  `s_deferral`): the first map's derived return (dossier head/spouse `deferral`), the second
  map's pass C less pass A wages. `nonprop` compares without the deferral, which the first map
  carries in it.
- Every other income, deduction and expense input compares as the second map's pass A against
  the first map's record.
- Dependents compare as counts: the second map's ages give `dep13` (under 13), `dep17` (ages 0-17,
  the ages-path child credit) and `dep18` (ages 0-18, at most three, the ages-path EITC); the
  first map's `dep17` is its record's `dep18` (children under 17) and its `dep18` is the EITC
  record's `dep18` where it runs one. `dependents_path` names each map's way of entering them.
- A member's own return (the second map's `dep_<name>` records) compares with the first map's
  payroll-only record for the same member, where it runs one; `income_tax_return` says whether
  the record's income tax counts in the household's line.

The class of each difference and its explanation come from RULINGS below and from the rules in
rule_groups() that cover many households alike (`transfers`, `rentpaid`, dependents, a member's
own return, a `pensions`/`nonprop` pair that moves one amount). The script stops on a difference
that no ruling covers, and warns when a difference classed as moving no line moves one.
docs/second-map-taxsim.md gives the classes and the results.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# The comparison rules on the first map as it stood at this commit; the first map has moved
# since, so every first-map file comes from the commit, not from the working tree.
FIRST_MAP_COMMIT = "1336819184eda68c1f6461115f09ccad2e0c885a"


def committed(path: str) -> str:
    """The text of a repo file as committed at FIRST_MAP_COMMIT."""
    import subprocess as _subprocess
    return _subprocess.run(
        ["git", "-C", str(REPO), "show", f"{FIRST_MAP_COMMIT}:{path}"],
        check=True, capture_output=True, text=True,
    ).stdout

FIRST_CSV = "results/taxsim/board100_cd2026110117_2026.csv"
DOSSIERS = "results/dossiers"
ANSWERS = "results/answers.csv"
SECOND_INPUTS = HERE / "inputs_2026.csv"
SECOND_ANSWERS = HERE / "answers_2026.csv"
OUT = REPO / "results/second_map"
BINARY = REPO / "work/nber/taxsimtest-osx.exe"

KEY_RUN, KEY_FALLBACK = "pb-reference-2.60.0", "pe-2.60.0-board-2026"
RERUN = "pe-2.60.0-board-2026"
LINES = (
    "federal_income_tax_before_refundable_credits",
    "federal_refundable_credits",
    "self_employment_tax",
    "federal_employee_payroll_tax",
)
SHORT = dict(zip(LINES, ("income_tax", "refundable", "se_tax", "payroll")))
FIRST_Q = dict(zip(LINES, ("q_fed_tax_before_refundable", "q_refundable_credits",
                           "q_self_employment_tax", "q_fed_employee_payroll_tax")))
TOL = 1.0

CLASSES = {
    "second_map_errs": "the second map errs: its input departs from the law or the board's rule, or from what the engine does with it",
    "first_map_errs": "the first map errs: its input departs from the law or the board's rule",
    "both_readings_defensible": "the maps read something the household does not state differently, and both readings are defensible",
    "engine_limit_handled_differently": "the maps handle an engine limit or defect differently (for example which input path they use)",
    "representation_moves_no_line": "a difference of representation that moves no line",
}

# Aligned variables, in output order.
VARS = ["mstat", "page", "sage", "depx", "dep13", "dep17", "dep18", "dependents_path",
        "pwages", "swages", "p_deferral", "s_deferral", "psemp", "ssemp", "pprofinc", "sprofinc",
        "scorp", "dividends", "intrec", "stcg", "ltcg", "pensions", "gssi", "pui", "sui", "nonprop",
        "transfers", "rentpaid", "proptax", "otheritem", "childcare", "mortgage", "income_tax_return"]
DEP_VARS = {"depx", "dep13", "dep17", "dep18", "dependents_path"}
DIRECT = ["mstat", "page", "sage", "psemp", "ssemp", "pprofinc", "sprofinc", "scorp", "dividends",
          "intrec", "stcg", "ltcg", "nonprop", "pensions", "gssi", "pui", "sui", "transfers",
          "rentpaid", "proptax", "otheritem", "childcare", "mortgage"]
ENGINE_COLS = ["mstat", "page", "sage", "depx", "age1", "age2", "age3", "age4", "age5", "age6",
               "age7", "age8", "pwages", "swages", "psemp", "ssemp", "pprofinc", "sprofinc", "scorp",
               "dividends", "intrec", "stcg", "ltcg", "nonprop", "pensions", "gssi", "pui", "sui",
               "transfers", "rentpaid", "proptax", "otheritem", "childcare", "mortgage"]
# Inputs the second map sends in `transfers` (second_map/taxsim/map.py:457-459).
TRANSFER_ITEMS = ("veterans_benefits", "workers_compensation", "child_support_received",
                  "financial_assistance", "tax_exempt_private_pension_income",
                  "tax_exempt_ira_distributions")
PLACEMENT_ITEMS = ("salt_refund_income", "miscellaneous_income")

# --------------------------------------------------------------------------------------------
# Rulings. Each entry: group name -> (aligned variables on the main record, class, explanation).
# Groups not listed here come from the rules in rule_groups(): `transfers`, `rentpaid`, the
# dependents, a member's own return, and `pensions`/`nonprop` pairs that move one amount.

TRANSFERS_SS = (
    "The second map enters {items} ({amount}) in `transfers`, which NBER's page describes as "
    "non-taxable income used for state rebates, and its README says the input has no effect on "
    "the four lines. This build adds `transfers` to the income that decides how much Social "
    "Security is taxable (compare.py --probes, P1: 0.85 of the amount when benefits sit in the "
    "85% range), which 26 U.S.C. 86(b)(2) does not: modified AGI there is AGI figured without "
    "sections 85(c), 135, 137, 221, 911, 931 and 933, plus tax-exempt interest, and none of these "
    "items is in it."
)
TRANSFERS_NO_SS = (
    "The second map enters {items} ({amount}) in `transfers`; the first map enters nothing. The "
    "household has no Social Security, and without benefits the build gives `transfers` no "
    "federal effect (compare.py --probes, P1)."
)
RENTPAID = (
    "The second map enters the stated rent paid in `rentpaid`, which NBER's page uses for state "
    "renter credits only; the first map enters nothing. With `state` 0 the input moves no "
    "federal amount."
)
PLACEMENT = (
    "Both maps enter {items} ({amount}) as ordinary income: the first map in `pensions`, the "
    "second in `nonprop`. The build also counts `nonprop` as earned income for the EITC "
    "(compare.py --probes, P2), where 26 U.S.C. 32(c)(2)(A) counts only wages and "
    "self-employment earnings; this household gets no EITC either way, so the placement moves "
    "no line."
)
DEPENDENTS = (
    "The second map enters dependents by age ({ages}); the first map enters counts (`dep13`, "
    "`dep17`, `dep18`) and, where the EITC children differ in number from the children under "
    "17, a second record for the EITC. In this build the 2026 EITC on the ages path uses the "
    "childless phase-in and phase-out rates for every family size and the 2026 child care "
    "credit on the ages path is 0; the counts path gives the Rev. Proc. 2025-32 EITC and a child "
    "care credit at the pre-2026 rates, which also departs from 26 U.S.C. 21(a)(2) as amended "
    "(compare.py --probes, P3 and P4; the second map's README records the same EITC and child "
    "care behaviour and keeps the engine's answer)."
)
MEMBER_RETURN = (
    "The second map files {name}'s own return (`mstat` {mstat}, {income}) and adds its income "
    "tax ({tax}) to the household's line; the first map counts the head's return only and runs "
    "{name} for payroll tax alone{payroll_note}. The output sums over the household and the "
    "board puts every listed person in 'one household group for tax and benefit "
    "calculations'; neither settles whether a member's own return counts (the repo's cause "
    "shared-head-return-only says the same)."
)

SCHOLARSHIP = (
    "The household lists {amount} of educational assistance (scholarships and grants) and no "
    "tuition. 26 U.S.C. 117(a)-(b) excludes a scholarship only for a degree candidate and only "
    "to the extent it pays qualified tuition and related expenses; the board's rule makes an "
    "unstated fact false, so the whole amount is income. The second map enters it in "
    "`nonprop`; the first map leaves it out (keycheck READINGS['educational_assistance']). The "
    "repo's cause shared-scholarship-not-income takes the second map's position."
)
SURVIVOR = (
    "The household lists {amount} of survivor benefits other than Social Security. They are "
    "gross income (26 U.S.C. 61(a); 72 for a survivor annuity) unless an exclusion applies, and "
    "each exclusion (life insurance proceeds, 101(a); workers' compensation, 104(a)(1); "
    "veterans' dependency compensation, 38 U.S.C. 5301) needs a fact the household does not "
    "state, which the board's rule makes false. The second map taxes them (`pensions`); the "
    "first map leaves them out (keycheck READINGS['survivor_benefits']). The repo's cause "
    "shared-survivor-benefits-not-taxable takes the second map's position."
)
FARM_RENT_QBI = (
    "The household states {amount} of farm rental income and {ubia} of unadjusted basis of "
    "qualified property. The first map enters the farm rent in `scorp`, which gets the 20% "
    "deduction of 26 U.S.C. 199A; the second map enters it in `intrec` and gives no deduction, "
    "reading a rental as no trade or business (199A(d)(1)) when the household does not say it "
    "is one. The stated basis, a figure that exists only for property of a qualified business, "
    "supports the first reading; the board's rule that an unstated status is false supports the "
    "second. (The first map sends rent to `intrec` under READINGS['rental_qbi'] but farm rent to "
    "`scorp`.)"
)
BDC = (
    "The household lists {amount} of qualified BDC income beside its stated dividends. The "
    "second map adds it to `intrec` as more ordinary income; the first map reads it as part of "
    "the stated dividends and adds nothing (keycheck READINGS['qualified_bdc_income']). The "
    "household does not say whether the amount repeats the dividends; the repo's cause "
    "shared-bdc-income-not-added says the same."
)

RULINGS: dict[str, dict[str, tuple[list[str], str, str]]] = {
    "scenario_005": {
        "deferral_order": (["p_deferral", "s_deferral"], "both_readings_defensible",
            "Each spouse states desired traditional 401(k) deferrals of 23,154 and Roth deferrals "
            "of 4,086, together 27,240, above the 2026 limit of 24,500 (26 U.S.C. 402(g)(1); "
            "Notice 2025-67). The first map scales both down in proportion (20,825 traditional; "
            "keycheck READINGS['desired_contributions']); the second gives the traditional "
            "deferrals the room first (23,154). The household does not say which deferrals the "
            "plan honours first."),
    },
    "scenario_030": {
        "scholarship": (["nonprop"], "first_map_errs", SCHOLARSHIP.format(amount="5,000")),
        "itemized": (["mortgage"], "first_map_errs",
            "Follows from the scholarship: 5,000 more AGI raises the 7.5% medical floor "
            "(26 U.S.C. 213(a)) by 375. 030 takes the standard deduction either way."),
    },
    "scenario_038": {
        "se_health_insurance": (["nonprop"], "both_readings_defensible",
            "The head has 15,525 of self-employment income, no stated employer coverage and 100 "
            "of premiums. The second map deducts the premiums under 26 U.S.C. 162(l) (negative "
            "`nonprop`); the first map counts them as itemized medical expenses because the "
            "household does not say the plan was established under the business (keycheck "
            "READINGS['self_employed_health_insurance']). In this build negative `nonprop` also "
            "lowers EITC earned income, which 32(c)(2)(A) and 162(l)(4) do not allow (the repo's "
            "cause map-ira-deduction-in-nonprop-cuts-eitc), so the 162(l) entry moves refundable "
            "credits through an engine side effect."),
    },
    "scenario_042": {
        "bdc_income": (["intrec"], "both_readings_defensible", BDC.format(amount="70.94")),
    },
    "scenario_052": {
        "bdc_income": (["intrec"], "both_readings_defensible", BDC.format(amount="0.40")),
    },
    "scenario_056": {
        "hsa_limit": (["nonprop"], "first_map_errs",
            "056 states an HSA deduction of 9,915.44 for a single 20-year-old with no one else in "
            "the household. 26 U.S.C. 223(b)(2) caps the deduction at 4,400 for self-only "
            "coverage in 2026 (Rev. Proc. 2025-19; family coverage, which needs another covered "
            "person, caps it at 8,750, still below the stated amount). The second map caps it; "
            "the first map takes the stated amount (keycheck READINGS['hsa']). 056 owes 0 either "
            "way."),
        "itemized": (["mortgage"], "first_map_errs",
            "The first map enters 056's 1,428 of cash gifts in full; 26 U.S.C. 170(b)(1)(G) "
            "limits cash gifts to 60% of the contribution base, which is below zero here (AGI "
            "-366.61 in the second map's run), so none is deductible this year. The second map "
            "applies the limit and enters 0, but it also enters 27.50 of medical deduction with "
            "no medical expense stated: its floor, 7.5% of a negative AGI, turns negative "
            "(second_map/taxsim/map.py:557). Both maps err on this input; 056 takes the standard "
            "deduction and owes 0 either way."),
    },
    "scenario_060": {
        "itemized": (["mortgage"], "second_map_errs",
            "Follows from `transfers`: the build adds 060's veterans' benefits to the Social "
            "Security test, which makes 11,985.07 more of the benefits taxable and raises the 7.5% "
            "medical floor (26 U.S.C. 213(a)) by 898.88. 060 owes 0 either way."),
    },
    "scenario_062": {
        "farm_rent_qbi": (["scorp", "intrec"], "both_readings_defensible",
            FARM_RENT_QBI.format(amount="4,792.94", ubia="22,440.45")),
        "survivor_benefits": (["pensions"], "first_map_errs", SURVIVOR.format(amount="28,800")),
        "itemized": (["mortgage"], "first_map_errs",
            "Follows from the survivor benefits: the higher AGI lifts the 7.5% medical floor "
            "above 062's 4,000 of premiums in the second map's run. 062 takes the standard "
            "deduction either way."),
    },
    "scenario_068": {
        "scholarship": (["nonprop"], "first_map_errs", SCHOLARSHIP.format(amount="73,000")),
    },
    "scenario_072": {
        "itemized": (["mortgage"], "second_map_errs",
            "Follows from `transfers`: the build adds 072's veterans' benefits to the Social "
            "Security test, which makes 14,034.53 more of the benefits taxable and raises the "
            "7.5% medical floor by 1,052.59. 072 owes 0 either way."),
    },
    "scenario_074": {
        "placement": (["pensions", "nonprop"], "second_map_errs",
            "074 states no wages and no self-employment income, so its EITC is 0 (26 U.S.C. "
            "32(c)(2)(A)). The second map enters the 3,025.59 state tax refund in `nonprop`, "
            "which this build counts as EITC earned income (compare.py --probes, P2), and the "
            "build pays an EITC of 231.46; with the refund in `pensions`, as the first map "
            "enters it, the EITC is 0."),
        "itemized": (["mortgage"], "first_map_errs",
            "The first map enters 074's 12,329.88 of cash gifts less the 0.5% floor (12,312.83) "
            "with no ceiling; 26 U.S.C. 170(b)(1)(G) caps cash gifts at 60% of AGI, 2,045.75 at "
            "the first map's AGI of 3,409.59. The second map applies the ceiling (3,949.84 at its "
            "AGI of 6,638.39, which its `transfers` entry raises through taxable Social "
            "Security). 074 takes the standard deduction either way."),
    },
    "scenario_081": {
        "reit_ptp": (["scorp"], "both_readings_defensible",
            "081 states 6.22 of qualified REIT and PTP income beside 110.12 of non-qualified "
            "dividends. The second map enters it in `scorp`, which adds it to income and gives "
            "it the 20% deduction (26 U.S.C. 199A(b)(1)(B)); the first map enters it nowhere and "
            "lists its deduction as one TAXSIM cannot express, which is right if the amount sits "
            "inside the stated dividends. The household does not say whether it does."),
    },
    "scenario_093": {
        "dependents": (["depx", "dependents_path"], "second_map_errs",
            "The second map claims dependent1 (27, disabled, 45,000 of wages) as a qualifying "
            "child under 26 U.S.C. 152(c)(3)(B), which needs permanent and total disability as "
            "22(e)(3) defines it: inability to engage in any substantial gainful activity. A year "
            "of 45,000 of wages is such activity (an inference: this comparison did not read the "
            "regulations on substantial gainful activity), and with 45,000 of gross income "
            "dependent1 is no qualifying relative either (152(d)(1)(B): 5,300 for 2026). The "
            "claim adds the 500 credit for other dependents (24(h)(4)). The first map claims no "
            "dependent; the repo's cause pe-other-dependent-credit-without-dependency-tests "
            "takes the first map's position, and the key pays the 500 credit."),
    },
    "scenario_098": {
        "passive_loss": (["scorp"], "first_map_errs",
            "098 states a farm rental loss of 11,100 and no other passive income. A farm rental "
            "is a rental activity, passive under 26 U.S.C. 469(c)(2); 469(a) disallows the net "
            "passive loss, and the 25,000 allowance of 469(i) needs active participation, which "
            "the household does not state and the board's rule makes false. The second map "
            "suspends the loss; the first map deducts it in `scorp`. 098 owes 0 either way."),
        "itemized": (["mortgage"], "first_map_errs",
            "Follows from the passive loss: with the loss suspended, AGI rises and the 7.5% "
            "medical floor passes 098's 436 of medical expenses. 098 takes the standard "
            "deduction either way."),
    },
    "scenario_104": {
        "itemized": (["mortgage"], "second_map_errs",
            "Follows from `transfers`: the build adds 104's veterans' benefits to the Social "
            "Security test, which makes 1,284 more of the benefits taxable and raises the 7.5% "
            "medical floor by 96.30. 104 owes 0 either way."),
    },
    "scenario_108": {
        "survivor_benefits": (["pensions"], "first_map_errs", SURVIVOR.format(amount="10,392")),
    },
    "scenario_112": {
        "farm_rent_qbi": (["scorp", "intrec"], "both_readings_defensible",
            FARM_RENT_QBI.format(amount="1,920", ubia="54,380.77")),
    },
    "scenario_120": {
        "passive_loss": (["scorp", "intrec"], "first_map_errs",
            "120 states rent of 2,000 and a farm rental loss of 2,446.59: two rental activities, "
            "passive under 26 U.S.C. 469(c)(2), that net to a 446.59 loss. 469(a) disallows it; "
            "the 469(i) allowance needs active participation (unstated, so false) and is gone "
            "above 150,000 of AGI in any case. The second map nets the two and suspends the "
            "loss, entering neither; the first map enters the rent in `intrec` and the loss in "
            "`scorp`. The repo's cause shared-passive-rental-loss-allowed takes the second map's "
            "position."),
        "itemized": (["mortgage"], "first_map_errs",
            "Follows from the passive loss: the first map's AGI is 446.59 lower, which lowers the "
            "0.5% charity floor (26 U.S.C. 170(b)(1)(I)) by 2.24."),
    },
    "scenario_122": {
        "itemized": (["mortgage"], "second_map_errs",
            "Follows from `transfers`: the build adds 122's 60 of tax-exempt pension to the "
            "Social Security test, which makes 51 more of the benefits taxable and raises the "
            "0.5% charity floor by 0.25."),
    },
}

# Extra words for the dependents rule, by household.
DEPENDENT_NOTES = {
    "scenario_008": " On the ages path the build also gives the 17-year-old the 2,200 child credit, which 26 U.S.C. 24(c)(1) denies (a child under 17 only); the earned-income limit on the refundable credit keeps it from moving 008's line.",
    "scenario_064": " dependent1 (27, disabled, no earnings) counts as an EITC child on the first map's counts path; the ages path has no way to say so. 064 gets no EITC at its income under the law.",
    "scenario_067": " dependent1 (23, disabled, no earnings) counts as an EITC child on the first map's counts path; the ages path has no way to say so. 067 gets no EITC at its income under the law.",
}


# --------------------------------------------------------------------------------------------
# TAXSIM runner (standard library).

ORDER = ("taxsimid", "year", "state", "mstat", "page", "sage", "depx", "dep13", "dep17", "dep18",
         "age1", "age2", "age3", "age4", "age5", "age6", "age7", "age8", "pwages", "swages",
         "psemp", "ssemp", "dividends", "intrec", "stcg", "ltcg", "nonprop", "pensions", "gssi",
         "pui", "sui", "transfers", "rentpaid", "proptax", "otheritem", "childcare", "mortgage",
         "scorp", "pprofinc", "sprofinc", "idtl")
WHOLE = {"taxsimid", "year", "state", "mstat", "page", "sage", "depx", "dep13", "dep17", "dep18", "idtl"}


def taxsim(rows: list[dict], binary: Path) -> list[dict]:
    """Run one file of records; ages and dependent counts cannot share a file."""
    names = [n for n in ORDER if n == "idtl" or any(n in r for r in rows)]
    lines = [",".join(names)]
    for i, row in enumerate(rows, start=1):
        vals = []
        for n in names:
            v = 2 if n == "idtl" else (i if n == "taxsimid" else row.get(n, 0))
            vals.append(str(int(v)) if (n in WHOLE or n.startswith("age")) else repr(round(float(v), 2)))
        lines.append(",".join(vals))
    done = subprocess.run([str(binary)], input="\n".join(lines) + "\n", capture_output=True, text=True)
    data = [ln for ln in done.stdout.splitlines() if ln and not ln.startswith(" TAXSIM")]
    reader = list(csv.reader(io.StringIO("\n".join(data))))
    header = [h.strip() for h in reader[0]]
    out = [{h: float(v) for h, v in zip(header[:-1], f)} for f in reader[1:]]
    if len(out) != len(rows):
        raise RuntimeError(f"TAXSIM answered {len(out)} of {len(rows)} records:\n{done.stdout[-2000:]}")
    return out


def run_jobs(jobs: list[tuple], binary: Path) -> dict:
    """jobs: (tag, record). Records on the ages path and the counts path go in separate files."""
    out = {}
    counts = [(t, r) for t, r in jobs if any(k in r for k in ("dep13", "dep17", "dep18"))]
    ages = [(t, r) for t, r in jobs if not any(k in r for k in ("dep13", "dep17", "dep18"))]
    for group in (ages, counts):
        if group:
            for (t, _), o in zip(group, taxsim([r for _, r in group], binary)):
                out[t] = o
    return out


def lines_of(records: dict, eitc: float | None = None) -> list[float]:
    """The four lines summed over a household's records ({role: {'A','B','C'}}), as both maps
    define them: income tax = fiitax + v25 + actc (pass A), refundable = v25 + actc, SE tax and
    payroll from the payroll passes. `eitc` replaces the main record's v25 (the first map's
    EITC record). A role whose 'A' is None files no income tax return."""
    it = rf = se = pay = 0.0
    for role, o in records.items():
        if o["A"] is not None:
            v25 = eitc if (role == "main" and eitc is not None) else o["A"]["v25"]
            it += o["A"]["fiitax"] + o["A"]["v25"] + o["A"]["actc"]
            rf += v25 + o["A"]["actc"]
        se += (o["B"]["tfica"] - o["B"]["addmed"]) - (o["C"]["tfica"] - o["C"]["addmed"])
        pay += (o["C"]["tfica"] - o["C"]["addmed"]) + o["B"]["addmed"]
    it = 0.0 if -0.05 < it < 0 else it   # the engine's cent rounding (both maps report 0.00)
    return [round(it, 2), round(rf, 2), round(se, 2), round(pay, 2)]


# --------------------------------------------------------------------------------------------
# Loading and aligning.

def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def load_first() -> dict:
    """{case: {record: {aligned variable: value}}} from the committed first-map record."""
    out = {}
    with io.StringIO(committed(FIRST_CSV), newline="") as fh:
        for r in csv.DictReader(fh):
            cid = r["case_id"]
            u = json.loads(committed(f"{DOSSIERS}/{cid}.json"))["return_from_stated_facts"]["2026"]
            pdef = u["head"]["deferral"]
            sdef = u["spouse"]["deferral"] if u["spouse"] else 0.0
            rec = {k: num(r.get("in_" + k)) for k in VARS if k not in ("p_deferral", "s_deferral", "dependents_path", "income_tax_return")}
            rec["transfers"] = rec["rentpaid"] = rec["otheritem"] = 0.0   # the first map sends none
            rec["p_deferral"], rec["s_deferral"] = pdef, sdef
            rec["nonprop"] = num(r["in_nonprop"]) + pdef + sdef
            rec["dep17"] = num(r["in_dep18"])     # its record sends dep18 = children under 17
            rec["dep18"] = min(3.0, num(r["in_b_dep18"]) if r.get("in_b_dep18") else num(r["in_dep18"]))
            rec["dependents_path"] = "counts" if rec["depx"] else ""
            rec["income_tax_return"] = 1.0
            recs = {"main": rec}
            for m in u["members_with_own_payroll"]:
                recs["member_" + m["name"]] = {"mstat": 1.0, "page": float(max(1, m["age"])),
                                               "pwages": m["wages"], "psemp": m["self_employment"],
                                               "intrec": 0.0, "pensions": 0.0, "income_tax_return": 0.0}
            out[cid] = {"records": recs, "row": r, "eitc_record": bool(r.get("in_b_dep18"))}
    return out


def load_second() -> dict:
    """{case: {'passes': {role: {'A','B','C': engine record}}, 'records': aligned}}."""
    raw = {}
    with open(SECOND_INPUTS, newline="") as fh:
        for r in csv.DictReader(fh):
            raw.setdefault(r["case_id"], {}).setdefault(r["record"], {})[r["pass"][0]] = {c: num(r[c]) for c in ENGINE_COLS}
    out = {}
    for cid, roles in raw.items():
        aligned = {}
        for role, p in roles.items():
            A, C = p["A"], p["C"]
            ages = [int(A[f"age{i}"]) for i in range(1, 9) if A[f"age{i}"] > 0]
            rec = {k: A[k] for k in DIRECT}
            rec["depx"] = A["depx"]
            rec["pwages"], rec["swages"] = C["pwages"], C["swages"]
            rec["p_deferral"] = C["pwages"] - A["pwages"]
            rec["s_deferral"] = C["swages"] - A["swages"]
            rec["dep13"] = float(sum(a < 13 for a in ages))
            rec["dep17"] = float(sum(a <= 17 for a in ages))
            rec["dep18"] = float(min(3, sum(a <= 18 for a in ages)))
            rec["dependents_path"] = ("ages " + "/".join(map(str, ages))) if ages else ""
            rec["income_tax_return"] = 1.0
            if role == "main":
                aligned["main"] = rec
            else:
                name = "member_" + role.split("_", 1)[1]
                aligned[name] = {k: rec[k] for k in ("mstat", "page", "pwages", "psemp", "intrec", "pensions", "income_tax_return")}
        out[cid] = {"passes": roles, "records": aligned}
    return out


def stated(cid: str) -> dict:
    return json.loads(committed(f"{DOSSIERS}/{cid}.json"))["stated_facts"]


def stated_sum(cid: str, keys, filers_only=True) -> dict:
    facts = stated(cid)
    people = [p for p in facts["adults"] if p["inputs"].get("is_tax_unit_head") or p["inputs"].get("is_tax_unit_spouse") or not filers_only]
    sums = {}
    for k in keys:
        v = sum(num(p["inputs"].get(k)) for p in people)
        if v:
            sums[k] = v
    return sums


def describe(sums: dict) -> tuple[str, str]:
    if not sums:
        return "amounts", "0.00"
    names = [k.replace("_", " ") for k in sums]
    text = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return text, f"{sum(sums.values()):,.2f}"


# --------------------------------------------------------------------------------------------
# Differences, groups and rulings.

def differences(first: dict, second: dict) -> list[dict]:
    rows = []
    for cid in sorted(first):
        F, S = first[cid]["records"], second[cid]["records"]
        for rec in sorted(set(F) | set(S), key=lambda r: (r != "main", r)):
            a, b = F.get(rec), S.get(rec)
            for v in VARS:
                if a is not None and v not in a and (b is None or v not in b):
                    continue
                if a is None and (b is None or v not in b):
                    continue
                x = a.get(v) if a is not None else None
                y = b.get(v) if b is not None else None
                if v == "dependents_path":
                    if (x or "") != (y or ""):
                        rows.append(dict(case_id=cid, record=rec, variable=v, first_map=x or "(none)",
                                         second_map=y or "(none)", difference=""))
                    continue
                xf, yf = num(x), num(y)
                if abs(xf - yf) > 0.01:
                    rows.append(dict(case_id=cid, record=rec, variable=v,
                                     first_map=f"{xf:.2f}" if x is not None else "(no record)",
                                     second_map=f"{yf:.2f}" if y is not None else "(no record)",
                                     difference=f"{yf - xf:.2f}"))
    return rows


def rule_groups(cid: str, rows: list[dict], second: dict) -> dict:
    """{group: {'vars': [(record, variable)], 'class', 'explanation'}} for one household."""
    groups = {}
    explicit = RULINGS.get(cid, {})
    claimed = set()
    for g, (vs, cls, text) in explicit.items():
        groups[g] = {"vars": [("main", v) for v in vs], "class": cls, "explanation": text}
        claimed |= {("main", v) for v in vs}
    main = second[cid]["passes"]["main"]["A"]
    has_ss = main["gssi"] > 0
    left = [r for r in rows if (r["record"], r["variable"]) not in claimed]
    for r in left:
        rec, v = r["record"], r["variable"]
        if rec != "main":
            g = "member_return_" + rec.split("_", 1)[1]
            if g not in groups:
                name = rec.split("_", 1)[1]
                role = second[cid]["passes"]["dep_" + name]["A"]
                income = ", ".join(f"{k} {role[k]:,.2f}" for k in ("pwages", "pensions", "intrec") if role[k])
                groups[g] = {"vars": [], "class": "both_readings_defensible", "explanation": None,
                             "member": name, "mstat": int(role["mstat"]), "income": income}
            groups[g]["vars"].append((rec, v))
        elif v == "transfers":
            items, amount = describe(stated_sum(cid, TRANSFER_ITEMS))
            text = (TRANSFERS_SS if has_ss else TRANSFERS_NO_SS).format(items=items, amount=amount)
            groups["transfers"] = {"vars": [(rec, v)], "explanation": text,
                                   "class": "second_map_errs" if has_ss else "representation_moves_no_line"}
        elif v == "rentpaid":
            groups["rentpaid"] = {"vars": [(rec, v)], "class": "representation_moves_no_line", "explanation": RENTPAID}
        elif v in DEP_VARS:
            g = groups.setdefault("dependents", {"vars": [], "class": "engine_limit_handled_differently",
                                                 "explanation": None})
            g["vars"].append((rec, v))
        elif v in ("pensions", "nonprop"):
            d = {x["variable"]: num(x["difference"]) for x in left if x["record"] == "main"}
            if abs(d.get("pensions", 0) + d.get("nonprop", 0)) < 0.02:
                items, amount = describe(stated_sum(cid, PLACEMENT_ITEMS))
                g = groups.setdefault("placement", {"vars": [], "class": "representation_moves_no_line",
                                                    "explanation": PLACEMENT.format(items=items, amount=amount)})
                g["vars"].append((rec, v))
            else:
                groups.setdefault("unruled_" + v, {"vars": [(rec, v)], "class": "unruled", "explanation": "no ruling"})
        else:
            groups.setdefault("unruled_" + v, {"vars": [(rec, v)], "class": "unruled", "explanation": "no ruling"})
    if "dependents" in groups and groups["dependents"]["explanation"] is None:
        S = second[cid]["records"]["main"]
        ages = S["dependents_path"].replace("ages ", "ages ") or "none"
        groups["dependents"]["explanation"] = DEPENDENTS.format(ages=ages) + DEPENDENT_NOTES.get(cid, "")
    return groups


def apply(group: dict, passes: dict, first: dict, second_aligned: dict) -> tuple[dict, dict | None]:
    """Set a group's variables in the second map's records to the first map's values.
    Returns (records by role, the EITC record or None)."""
    recs = {role: {k: dict(v) for k, v in p.items()} for role, p in passes.items()}
    fm, sm = first["records"]["main"], second_aligned["main"]
    eitc = None
    A, B, C = recs["main"]["A"], recs["main"]["B"], recs["main"]["C"]
    vars_ = [v for r, v in group["vars"] if r == "main"]
    if any(r != "main" for r, _ in group["vars"]):
        for r, _ in group["vars"]:
            if r != "main":
                recs["dep_" + r.split("_", 1)[1]]["A"] = None   # the first map files no return for the member
    if DEP_VARS & set(vars_):
        for i in range(1, 9):
            A.pop(f"age{i}", None)
        A["depx"] = fm["depx"]
        if fm["depx"]:
            A["dep13"], A["dep17"], A["dep18"] = fm["dep13"], fm["dep17"], fm["dep17"]
            eitc = dict(A, dep18=fm["dep18"], dep17=min(fm["dep17"], fm["dep18"]),
                        dep13=min(fm["dep13"], fm["dep17"], fm["dep18"]))
    for v in vars_:
        if v in DIRECT:
            A[v] = fm[v]
        elif v in ("p_deferral", "s_deferral"):
            w = "pwages" if v == "p_deferral" else "swages"
            A[w] = C[w] - fm[v]
        elif v in ("pwages", "swages"):
            d = "p_deferral" if v == "pwages" else "s_deferral"
            A[v] = fm[v] - sm[d]
            B[v] = C[v] = fm[v]
    return recs, eitc


def clean(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if not (k.startswith("age") and v == 0)}


def evaluate(cid: str, groups: dict, first: dict, second: dict, binary: Path) -> dict:
    """Lines for the second map's records, for each group set to the first map, and for all."""
    passes = second[cid]["passes"]
    variants = {"base": (passes, None)}
    for g, spec in groups.items():
        variants[g] = apply(spec, passes, first[cid], second[cid]["records"])
    allspec = {"vars": [v for spec in groups.values() for v in spec["vars"]]}
    variants["ALL"] = apply(allspec, passes, first[cid], second[cid]["records"])
    jobs = []
    for name, (recs, eitc) in variants.items():
        for role, p in recs.items():
            for ps in "ABC":
                if p[ps] is not None:
                    jobs.append(((name, role, ps), dict(clean(p[ps]), year=2026, state=0)))
        if eitc is not None:
            jobs.append(((name, "main", "E"), dict(clean(eitc), year=2026, state=0)))
    out = run_jobs(jobs, binary)
    result = {}
    for name, (recs, eitc) in variants.items():
        ran = {role: {ps: (out[(name, role, ps)] if p[ps] is not None else None) for ps in "ABC"} for role, p in recs.items()}
        e = out[(name, "main", "E")]["v25"] if eitc is not None else None
        result[name] = lines_of(ran, e)
    return result


# --------------------------------------------------------------------------------------------

def probes(binary: Path) -> None:
    """The four probes the rulings cite. Each prints the inputs that change and the outputs."""
    def show(title, cases):
        print(title)
        res = run_jobs([(i, dict(r, year=2026, state=0)) for i, (_, r) in enumerate(cases)], binary)
        for i, (label, _) in enumerate(cases):
            o = res[i]
            print(f"  {label:58s} AGI v10 {o['v10']:>10,.2f}  taxable SS v12 {o['v12']:>10,.2f}  "
                  f"fiitax {o['fiitax']:>9,.2f}  EITC v25 {o['v25']:>8,.2f}  CDCC v24 {o['v24']:>8,.2f}  "
                  f"ACTC {o['actc']:>8,.2f}")
    base = dict(mstat=1, page=70, gssi=30000, pensions=30000)
    show("P1. `transfers` and Social Security (single, 70):", [
        ("benefits 30,000, pension 30,000, transfers 0", dict(base)),
        ("benefits 30,000, pension 30,000, transfers 5,000", dict(base, transfers=5000)),
        ("no benefits, wages 30,000, age 40, transfers 0", dict(mstat=1, page=40, pwages=30000)),
        ("no benefits, wages 30,000, age 40, transfers 10,000", dict(mstat=1, page=40, pwages=30000, transfers=10000)),
    ])
    show("P2. `nonprop` as EITC earned income (single, 54, nothing else):", [
        ("nonprop 3,025.59", dict(mstat=1, page=54, nonprop=3025.59)),
        ("pensions 3,025.59", dict(mstat=1, page=54, pensions=3025.59)),
    ])
    w = dict(mstat=1, page=30, pwages=30000)
    show("P3. 2026 EITC by dependents path (single, 30, wages 30,000):", [
        ("ages: one child aged 5", dict(w, depx=1, age1=5)),
        ("counts: one child (dep13=dep17=dep18=1)", dict(w, depx=1, dep13=1, dep17=1, dep18=1)),
        ("ages: two children aged 5 and 8", dict(w, depx=2, age1=8, age2=5)),
        ("counts: two children", dict(w, depx=2, dep13=2, dep17=2, dep18=2)),
    ])
    j = dict(mstat=2, page=35, sage=35, pwages=60000, swages=40000, childcare=8000)
    show("P4. 2026 child care credit by path (joint, wages 60,000 + 40,000, care 8,000):", [
        ("ages: two children aged 5 and 8", dict(j, depx=2, age1=8, age2=5)),
        ("counts: two children", dict(j, depx=2, dep13=2, dep17=2, dep18=2)),
    ])
    print("Law, 2026 (Rev. Proc. 2025-32; 26 U.S.C. 21(a)(2) as amended): EITC one child at 30,000 "
          "= 4,427 - 15.98% x (30,000 - 23,890) = 3,450.62; two children = 7,316 - 21.06% x 6,110 "
          "= 6,029.23; childless at 30,000 = 0. Child care credit at joint AGI 100,000: 35% x 6,000 "
          "= 2,100.")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", type=Path, default=BINARY)
    ap.add_argument("--probes", action="store_true")
    args = ap.parse_args(argv)
    if not args.binary.exists():
        sys.exit(f"TAXSIM binary not found at {args.binary}: run scripts/get_taxsim.sh")
    if args.probes:
        probes(args.binary)

    first, second = load_first(), load_second()
    assert set(first) == set(second), "the two maps cover different households"
    second_ans = {}
    with open(SECOND_ANSWERS, newline="") as fh:
        for r in csv.DictReader(fh):
            second_ans.setdefault(r["case_id"], {})[r["quantity"]] = num(r["value"])
    key, rerun, key_status = {}, {}, {}
    with io.StringIO(committed(ANSWERS), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["case_set"] != "board-100" or r["period"] != "2026" or r["quantity"] not in LINES:
                continue
            k = (r["case_id"], r["quantity"])
            if r["run"] == KEY_RUN:
                key_status[k] = r["status"]
                if r["status"] == "ok":
                    key[k] = num(r["value"])
            if r["run"] == RERUN:
                rerun[k] = num(r["value"])
    for k in list(key_status):
        if k not in key:
            key[k] = rerun[k]   # the key publishes no federal payroll line; scripts/agreement.py falls back the same way

    rows = differences(first, second)
    by_case = {}
    for r in rows:
        by_case.setdefault(r["case_id"], []).append(r)

    input_rows, effects = [], {}
    for cid in sorted(first):
        groups = rule_groups(cid, by_case.get(cid, []), second) if cid in by_case else {}
        lines = evaluate(cid, groups, first, second, args.binary)
        s = [second_ans[cid][q] for q in LINES]
        f = [round(num(first[cid]["row"][FIRST_Q[q]]), 2) for q in LINES]
        if any(abs(x - y) > 0.011 for x, y in zip(lines["base"], s)):
            sys.exit(f"{cid}: the second map's records give {lines['base']}, its answers say {s}")
        if any(abs(x - y) > 0.011 for x, y in zip(lines["ALL"], f)):
            sys.exit(f"{cid}: with every difference set to the first map, the records give {lines['ALL']}, the first map says {f}")
        effects[cid] = {}
        for g, spec in groups.items():
            delta = [round(b - a, 2) for a, b in zip(lines[g], lines["base"])]   # second map minus first map's value of the group
            moved = {SHORT[q]: d for q, d in zip(LINES, delta) if abs(d) > TOL}
            effects[cid][g] = (spec, moved)
            if spec["class"] == "unruled":
                sys.exit(f"{cid} {g}: no ruling covers this difference ({spec['vars']}); it moves {moved or 'nothing'}")
            if spec["class"] == "representation_moves_no_line" and moved:
                print(f"WARNING {cid} {g}: class {spec['class']} but it moves {moved}", file=sys.stderr)
            if spec.get("member"):
                tax = lines["base"][0] - lines[g][0]
                pay = ""
                if any(r["record"] == "member_" + spec["member"] and r["variable"] == "mstat" and r["first_map"] == "(no record)"
                       for r in by_case[cid]):
                    pay = " (it runs no record for this member, who has no earnings)"
                spec["explanation"] = MEMBER_RETURN.format(name=spec["member"], mstat=spec["mstat"], income=spec["income"],
                                                           tax=f"{tax:,.2f}", payroll_note=pay)
            moves = "; ".join(f"{k} {v:+,.2f}" for k, v in moved.items()) if moved else "no"
            for rec, v in spec["vars"]:
                for r in by_case[cid]:
                    if r["record"] == rec and r["variable"] == v:
                        input_rows.append(dict(r, group=g, **{"class": spec["class"]},
                                               moves_a_line=("yes: " + moves) if moved else "no",
                                               explanation=spec["explanation"]))
    covered = {(r["case_id"], r["record"], r["variable"]) for r in input_rows}
    missing = [r for r in rows if (r["case_id"], r["record"], r["variable"]) not in covered]
    if missing:
        sys.exit(f"differences with no group: {missing[:5]}")
    order = {v: i for i, v in enumerate(VARS)}
    input_rows.sort(key=lambda r: (r["case_id"], r["record"] != "main", r["record"], order[r["variable"]]))

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["case_id", "record", "variable", "first_map", "second_map", "difference", "class",
            "moves_a_line", "group", "explanation"]
    with open(OUT / "taxsim_inputs_diff.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in input_rows:
            w.writerow({c: r[c] for c in cols})

    answer_rows = []
    for cid in sorted(first):
        for i, q in enumerate(LINES):
            f = round(num(first[cid]["row"][FIRST_Q[q]]), 2)
            s = round(second_ans[cid][q], 2)
            k, pe = key[(cid, q)], rerun[(cid, q)]
            movers = sorted(((g, spec, moved[SHORT[q]]) for g, (spec, moved) in effects[cid].items() if SHORT[q] in moved),
                            key=lambda t: -abs(t[2]))
            if abs(f - s) <= TOL:
                cls, why = "equal", ""
            else:
                cls = "; ".join(dict.fromkeys(spec["class"] for _, spec, _ in movers)) or "interaction"
                why = "; ".join(f"{g} {d:+,.2f}" for g, _, d in movers)
            answer_rows.append(dict(
                case_id=cid, line=q, first_map=f"{f:.2f}", second_map=f"{s:.2f}", difference=f"{s - f:.2f}",
                key=f"{k:.2f}", key_source=KEY_RUN if key_status[(cid, q)] == "ok" else KEY_FALLBACK,
                policyengine_rerun=f"{pe:.2f}",
                first_agrees_key="yes" if abs(f - k) <= TOL else "no",
                second_agrees_key="yes" if abs(s - k) <= TOL else "no",
                **{"class": cls}, input_groups=why))
    cols = ["case_id", "line", "first_map", "second_map", "difference", "key", "key_source",
            "policyengine_rerun", "first_agrees_key", "second_agrees_key", "class", "input_groups"]
    with open(OUT / "taxsim_answers_diff.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(answer_rows)

    # Summary on standard output.
    cases_with_diff = {r["case_id"] for r in input_rows}
    print(f"households with every input equal: {100 - len(cases_with_diff)}")
    same = {cid for cid in first if all(abs(num(a["first_map"]) - num(a["second_map"])) <= TOL
                                        for a in answer_rows if a["case_id"] == cid)}
    print(f"households with all four answers equal within $1: {len(same)}")
    for q in LINES:
        rs = [a for a in answer_rows if a["line"] == q]
        both = sum(a["first_agrees_key"] == "yes" and a["second_agrees_key"] == "yes" for a in rs)
        f_only = sum(a["first_agrees_key"] == "yes" and a["second_agrees_key"] == "no" for a in rs)
        s_only = sum(a["first_agrees_key"] == "no" and a["second_agrees_key"] == "yes" for a in rs)
        neither = sum(a["first_agrees_key"] == "no" and a["second_agrees_key"] == "no" for a in rs)
        print(f"{q}: both {both}, first only {f_only}, second only {s_only}, neither {neither}")
    from collections import Counter
    print("input rows by class:", dict(Counter(r["class"] for r in input_rows)))
    seen = {}
    for cid, gs in effects.items():
        for g, (spec, moved) in gs.items():
            seen[(cid, g)] = (spec["class"], moved)
    print("differences (household x group) by class:", dict(Counter(c for c, _ in seen.values())))
    print("that move a line:", dict(Counter(c for c, m in seen.values() if m)))


if __name__ == "__main__":
    main()
