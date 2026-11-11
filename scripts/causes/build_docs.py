"""Write docs/causes.md from results/causes.csv, results/cause_cells.csv,
results/cause_positions.csv, results/answers.csv and the agreement tables.

Every list in the file comes from those tables: the entries, the cell rows, the positions on the
key's answers, the scored cells a proposal would move and the scored cells that rest on an open
reading. Run scripts/causes/build_causes.py first.
"""
import csv
import itertools
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
L1 = "federal_income_tax_before_refundable_credits"
L2 = "federal_refundable_credits"
LINE_NAME = {L1: "tax before refundable credits", L2: "refundable credits"}
KEY_RUN = "pb-reference-2.60.0"
KEY_FALLBACK = {KEY_RUN: "pe-2.60.0-board-2026"}
TABLE_RUNS = {
    "2026": [KEY_RUN, "pe-2.60.0-board-2026", "taxcalc-6.9.0-2026", "taxsim-cd2026110117-2026"],
    "2025": ["pe-2.60.0-board-2025", "taxcalc-6.9.0-2025", "taxsim-cd2026110117-2025"],
}
LINES = ("federal_income_tax_before_refundable_credits", "federal_refundable_credits",
         "self_employment_tax", "federal_employee_payroll_tax")

TITLES = {
    "taxsim-no-overtime-deduction": "TAXSIM has no overtime deduction",
    "taxsim-no-nonitemizer-charitable-deduction": "TAXSIM has no 2026 charitable deduction for filers who do not itemize",
    "taxsim-no-tax-exempt-interest-input": "TAXSIM has no input for tax-exempt interest",
    "taxsim-no-blindness-input": "TAXSIM has no input for blindness",
    "taxsim-no-savers-credit": "TAXSIM's test build gives no saver's credit",
    "taxsim-2026-child-care-credit-old-rates": "TAXSIM applies the pre-2026 child care credit rates to 2026",
    "taxsim-refundable-child-credit-ignores-child-care-credit": "TAXSIM's refundable child credit ignores the child care credit",
    "taxsim-three-child-refundable-credit-alternative": "TAXSIM's three-child alternative counts the whole self-employment tax",
    "taxsim-2026-salt-cap-40000": "TAXSIM caps 2026 state and local taxes at $40,000",
    "taxsim-no-early-distribution-tax-input": "TAXSIM has no input for the additional tax on early distributions",
    "map-ira-deduction-in-nonprop-cuts-eitc": "The TAXSIM map's adjustments to AGI lower earned income",
    "pe-other-dependent-credit-without-dependency-tests": "policyengine-us pays the other-dependent credit without the dependency tests",
    "pe-divorce-year-default": "policyengine-us dates an unstated divorce to 2010",
    "pe-medicare-part-b-premium-default": "policyengine-us adds a Medicare premium the household does not state",
    "pe-net-investment-income-leaves-out-farm-rent": "policyengine-us 2.60.0 leaves farm rent out of net investment income",
    "pe-scholarship-not-income": "policyengine-us leaves a stated scholarship out of income",
    "pe-survivor-benefits-not-income": "policyengine-us leaves survivor benefits out of income",
    "pe-no-passive-activity-loss-limit": "policyengine-us has no passive activity loss limit",
    "pe-early-distribution-tax-not-computed": "policyengine-us computes no additional tax on early distributions",
    "key-ira-deducted-without-219g": "The key deducts IRA contributions without the active-participant limit",
    "key-sales-tax-table-column-shift": "The key holds a shifted sales tax table",
    "shared-state-tax-refund-counted-in-full": "A state tax refund counts in full as income",
    "shared-disability-benefits-taxable": "Disability benefits count as income",
    "shared-financial-assistance-gift": "Help from outside the household counts as a gift",
    "shared-disabled-member-qualifying-child": "A member the board calls disabled counts as a qualifying child",
    "shared-net-investment-income-tax-in-line": "The line includes the net investment income tax",
    "shared-state-income-tax-withholding-estimate": "State income tax comes from a withholding estimate",
    "shared-state-paid-leave-contributions-not-in-salt": "Connecticut paid leave contributions stay out of the state and local tax deduction",
    "shared-mortgage-debt-after-2017": "Mortgage debt counts as incurred after 2017",
    "shared-head-return-only": "The line covers the head's return only",
    "shared-bdc-income-not-added": "BDC income stays out of income",
    "shared-rental-with-basis-qualified-business-income": "Rent with a stated basis counts as qualified business income",
    "shared-private-pension-no-early-distribution-tax": "A private pension paid before age 59 1/2 carries no additional tax",
    "shared-over-the-counter-not-medical": "Over-the-counter expenses stay out of medical expenses",
}

KIND_TEXT = [
    ("model-law-departure", "A model computes a provision the law gives, but computes it differently from the law."),
    ("model-no-provision", "A model has no input for a stated fact, or no provision for the law of the year, so its answer leaves the provision out."),
    ("pe-default-unstated-fact", "policyengine-us fills a fact the household does not state with a default value, or applies a provision as if a condition the household does not state held, and the default moves the answer."),
    ("key-decided-value", "The committed key holds a value the board decided on an earlier engine release, and that value differs from what the engine gives today."),
    ("map-limit", "This repo's input map cannot express a stated fact in Tax-Calculator or TAXSIM the way the law treats it, or reads a fact differently from policyengine-us."),
    ("shared-reading", "Every answerer, or every answerer but the key, reads a stated or unstated fact the same way. Where all answers in a table move alike the reading leaves no trace in any difference, so the entry lists the households in `households_shared` and writes no cell rows; where the key's frozen value departs from the others, the entry writes rows for the answers it moves."),
    ("unexplained", "A residual no trace accounts for."),
]

POSITION_TEXT = [
    ("supports_key", "The law or the prompt rule (the `grounds` column) supports the key's answer as far as this cause goes. Where the entry names the answer another reading gives, `other_reading_answer` holds it."),
    ("supports_other_answer", "The law or the prompt rule supports a different answer, which `supported_answer` gives."),
    ("turns_on_unstated_fact", "The answer turns on a fact the board does not state, about the household or about the scope of the line, and the entry takes no side. `other_reading_answer` gives the answer on the reading the key does not take."),
    ("no_effect", "The cause bears on the household but moves no answer on this line."),
]
GROUNDS_TEXT = {"law": "the law", "prompt_rule": "the prompt rule", "": ""}

# Entries an earlier version of this account held, and what took their place after map version
# 2026-11-11.1 (evidence/traces/builder-2.md).
REPLACED = [
    ("shared-scholarship-not-income", "pe-scholarship-not-income",
     "the maps now count a stated scholarship as income, so only policyengine-us and the key leave it out. The earlier entry said 030 owes 0 either way; it does not: counting the scholarship moves 030 by 190.00 in 2026 and 225.00 in 2025"),
    ("shared-survivor-benefits-not-taxable", "pe-survivor-benefits-not-income",
     "the maps now count stated survivor benefits as income, so only policyengine-us and the key leave them out"),
    ("shared-passive-rental-loss-allowed", "pe-no-passive-activity-loss-limit",
     "the maps now suspend a net passive loss under 26 U.S.C. 469, which policyengine-us does not compute"),
    ("map-rental-not-qualified-business-income", "shared-rental-with-basis-qualified-business-income",
     "the maps now read a rental with a stated basis of qualified property as a qualified trade or business, as policyengine-us does, so no answer differs on it; the reading stays open, since both second maps read the rent the other way"),
]


def read(path):
    with open(REPO / path, newline="") as handle:
        return list(csv.DictReader(handle))


def money(x):
    x = float(x)
    return f"{x:,.2f}" if x >= 0 else f"-{-x:,.2f}"


def signed(x):
    x = float(x)
    return f"+{x:,.2f}" if x >= 0 else f"-{-x:,.2f}"


def short(case):
    return case.split("_")[1]


def shared_list(text):
    out = []
    for item in text.split(";"):
        case, _, table = item.partition("@")
        out.append(short(case) + (f" ({table} table only)" if table else ""))
    return ", ".join(out)


def sources(opened_by):
    m = re.search(r"agents: (.*); causes unit", opened_by)
    return m.group(1) if m else opened_by


def largest_residual(cells):
    """The largest gap, over every pair of answers, between the answer difference and the cause difference."""
    values = defaultdict(dict)
    for row in read("results/answers.csv"):
        if row["case_set"] == "board-100" and row["status"] == "ok":
            values[(row["case_id"], row["quantity"])][row["run"]] = float(row["value"])
    sums = defaultdict(float)
    for row in cells:
        sums[(row["case_id"], row["quantity"], row["run"])] += float(row["amount"])
    worst, where = 0.0, ""
    for (case, quantity), by_run in values.items():
        if quantity not in LINES:
            continue
        for runs in TABLE_RUNS.values():
            present = {}
            for run in runs:
                value = by_run.get(run, by_run.get(KEY_FALLBACK.get(run, ""), None))
                if value is not None:
                    present[run] = value
            for a, b in itertools.combinations(sorted(present), 2):
                gap = abs((present[a] - present[b]) - (sums[(case, quantity, a)] - sums[(case, quantity, b)]))
                if gap > worst:
                    worst, where = gap, short(case)
    return worst, where


causes = read("results/causes.csv")
cells = read("results/cause_cells.csv")
positions = read("results/cause_positions.csv")
key_table = read("results/agreement/board100_2026_key.csv")
key_row = {(r["case_id"], r["quantity"]): r for r in key_table}
rerun = {(r["case_id"], r["quantity"]): r["policyengine"] for r in read("results/agreement/board100_2026_rerun.csv")}
by_cause = defaultdict(list)
by_cell = defaultdict(list)
key_moved = defaultdict(float)
for r in cells:
    by_cause[r["cause_id"]].append(r)
    if r["table"] == "2026":
        by_cell[(r["case_id"], r["quantity"])].append(r)
    if r["run"] == KEY_RUN:
        key_moved[(r["cause_id"], r["case_id"], r["quantity"])] += float(r["amount"])
positions_by_cause = defaultdict(list)
positions_by_cell = defaultdict(list)
for p in positions:
    positions_by_cause[p["cause_id"]].append(p)
    positions_by_cell[(p["case_id"], p["quantity"])].append(p)
order = {c["cause_id"]: i for i, c in enumerate(causes)}
missing_titles = set(order) - set(TITLES)
assert not missing_titles, f"no title for {sorted(missing_titles)}"
worst, worst_case = largest_residual(cells)
kind_count = Counter(c["kind"] for c in causes)


def scored(case, quantity):
    return key_row[(case, quantity)]["board_scores_it"] == "yes"


def answer_of(p):
    """The answer a position names: the supported answer, or the other reading's."""
    if p["position"] == "supports_other_answer":
        return p["supported_answer"]
    return p["other_reading_answer"]


def standing(case, quantity):
    """How other lineages stand on the key's answer: the phrases of the cell-standing paragraph."""
    r = key_row[(case, quantity)]
    key = float(r["policyengine"])
    who = [name for name, col in (("Tax-Calculator", "taxcalc"), ("TAXSIM", "taxsim"))
           if r[col] and abs(float(r[col]) - key) <= 1.0]
    if who:
        return f"reproduced by a run of another lineage ({' and '.join(who)})"
    return "resting on one model"


RUN_OF = {"Tax-Calculator": "taxcalc-6.9.0-2026", "TAXSIM": "taxsim-cd2026110117-2026"}


def carried(case, quantity):
    """For each run of another lineage that gives the key's answer, the causes that move that run on
    this cell: an agreement that holds only because both answers carry the same cause."""
    r = key_row[(case, quantity)]
    key = float(r["policyengine"])
    notes = []
    for name, col in (("Tax-Calculator", "taxcalc"), ("TAXSIM", "taxsim")):
        if not r[col] or abs(float(r[col]) - key) > 1.0:
            continue
        moved = [x for x in by_cell[(case, quantity)] if x["run"] == RUN_OF[name]]
        if moved:
            notes.append(f"{name}'s answer carries " + ", ".join(f"`{x['cause_id']}` ({money(x['amount'])})" for x in moved))
    return "; ".join(notes)


def runs_giving(case, quantity, value):
    r = key_row[(case, quantity)]
    who = [name for name, col in (("Tax-Calculator", "taxcalc"), ("TAXSIM", "taxsim"))
           if r[col] and abs(float(r[col]) - float(value)) <= 1.0]
    return " and ".join(who)


def distinct_rows(rows):
    """Drop a row that repeats, for a cause with no row on the key's run, the answer that a cause with
    such a row already names on the same cell (an entry about another model's input that takes its
    position from the entry about the key)."""
    keep = []
    for p in rows:
        moves_key = abs(key_moved.get((p["cause_id"], p["case_id"], p["quantity"]), 0.0)) > 0
        twin = any(q is not p and answer_of(q) == answer_of(p) and q["position"] == p["position"]
                   and abs(key_moved.get((q["cause_id"], q["case_id"], q["quantity"]), 0.0)) > 0 for q in rows)
        if moves_key or not twin:
            keep.append(p)
    return keep


WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]


def count_words(n, noun):
    head = WORDS[n] if n < len(WORDS) else str(n)
    return f"{head} {noun}{'' if n == 1 else 's'}"


def how(p):
    parts = [x for x in (p["how_computed"], p["note"]) if x]
    return "; ".join(parts) if parts else "the entry's text"


out = []
w = out.append
w("# Causes of disagreement on the board's 100 households")
w("")
w("This file gives, for every household and line where the committed key, policyengine-us, Tax-Calculator and TAXSIM disagree, the causes of the disagreement, how much each cause moves each answer, what the law says, and which answer the law supports. `results/causes.csv` holds one row per cause, `results/cause_cells.csv` one row per cause, household, line, table and answerer, and `results/cause_positions.csv` one row per cause, household and line where an entry takes a position on the key's answer; this account renders all three. `tests/test_causes.py` checks that the causes account for every difference to the dollar.")
w("")
w("Claude Opus 5.5 agents opened every entry: four tracers reconciled each disagreement to its cause (`evidence/traces/trace-pe-a.md`, `trace-pe-b.md`, `trace-taxsim-a.md`, `trace-taxsim-b.md`), reviewers checked the maps (`evidence/traces/verify-*.md`), and a further agent wrote these tables on 2026-11-10. On 2026-11-11 a builder applied the board's rule for unstated facts uniformly to the input maps as map version 2026-11-11.1 (`evidence/traces/builder-2.md`), which moved ten board cells, and another agent brought the entries in line with the new answers and added the positions file. Every entry stays open. The \"who is right\" line states the entry's position and its grounds in law; it awaits a human reviewer and decides nothing. This repo proposes answers; it changes nothing on the board.")
w("")
w("## How to read the entries")
w("")
w("**Answerers and tables.** The 2026 table compares four answers: the committed key (`policybench-key`, run `pb-reference-2.60.0`), policyengine-us 2.60.0 under the board's conventions (`pe-2.60.0-board-2026`), Tax-Calculator 6.9.0 (`taxcalc-6.9.0-2026`) and TAXSIM's test build cd2026110117 (`taxsim-cd2026110117-2026`). The 2025 table compares the last three under 2025 law (`pe-2.60.0-board-2025`, `taxcalc-6.9.0-2025`, `taxsim-cd2026110117-2025`). `results/runs.csv` describes each run. The lines are the four in `scripts/agreement.py`; every cause here moves federal tax before refundable credits or federal refundable credits.")
w("")
w(f"**Amounts.** A cell's amount is what the cause adds to that answerer's answer, in dollars, relative to the answer the law supports, or, where the cause turns on a fact the household does not state, the answer the board's prompt rule supports, as the entry reads them. Where the entry takes no side on a household, the amount runs from the answer the input maps give at map version 2026-11-11.1. Each row's `basis` says how the entry got the amount. A cause that lowers a refundable credit has a negative amount on that line. For any two answerers, the difference between their answers equals the difference between the sums of their amounts, within $1; the largest residual is ${worst:,.2f} (household {worst_case}).")
w("")
w("**The prompt rule.** The board tells every answerer to treat an unlisted number as 0 and any other unlisted fact, boolean or status as false, to assume filing and take-up when required, and not to infer unlisted income, expenses, assets, benefit receipt, rent or health coverage (`PolicyEngine/policybench@c7ede86c:policybench/prompts.py:15-27`). These entries read the rule one way throughout: a provision that includes or allows something only on a fact does not apply when the household does not state the fact, and a provision that excludes or denies something only on a fact does not apply either. Where the cause is an unstated fact, the entry says that no answer is right until the household states the fact, and then which answer the rule points to.")
w("")
w("**Counterfactual runs.** Where an entry cites a counterfactual run, it means Tax-Calculator 6.9.0 or TAXSIM cd2026110117 run on the inputs recorded in `results/dossiers/<case>.json` (the `in_` fields under `other_models`), with the settings of `scripts/run_taxcalc.py` or `keycheck/taxsim.py`, changing only the input the entry names (`scripts/causes/counterfactual_taxcalc.py`). The engine experiments sit in `results/repro/`.")
w("")
w("**Positions.** Each row of `results/cause_positions.csv` takes one position from a fixed set on the key's 2026 answer for one household and line. `key_value` repeats the key's answer; `how_computed` says how the entry got any other answer it names. `scripts/make_cell_status.py` reads the file.")
w("")
w("| Position | Meaning | Rows |")
w("|---|---|---:|")
pos_count = Counter(p["position"] for p in positions)
for value, text in POSITION_TEXT:
    w(f"| `{value}` | {text} | {pos_count[value]} |")
w("")
w("**Cell standing.** Where this account describes a cell's standing it uses three phrases: an answer \"reproduced by a run of another lineage\" (Tax-Calculator or TAXSIM gives it within $1), \"contested\" (an entry here says the law or the prompt rule supports a different answer), and \"resting on one model\" (no run of another lineage gives it).")
w("")
w("## Kinds")
w("")
w("| Kind | Meaning | Entries |")
w("|---|---|---:|")
for kind, text in KIND_TEXT:
    extra = " No entry has this kind." if kind == "unexplained" and not kind_count[kind] else ""
    w(f"| `{kind}` | {text}{extra} | {kind_count[kind]} |")
w("")
w("## Causes")
w("")
for c in causes:
    cid = c["cause_id"]
    w(f"### `{cid}`: {TITLES[cid]}")
    w("")
    w(f"*Kind* `{c['kind']}`. *Moves* {', '.join(f'`{a}`' for a in c['answerer'].split(';'))}. *Law years* {c['law_years']}. *Entry* {c['entry_status']}.")
    w("")
    w(c["summary"])
    w("")
    w(f"- **Where it holds:** {c['release_or_build']}." + (f" **Fixed in:** {c['fixed_in']}." if c["fixed_in"] else ""))
    w(f"- **Law:** {c['law']}." + (f" **Figure:** {c['law_figure']}." if c["law_figure"] else ""))
    w(f"- **Who is right (this entry's position):** {c['who_is_right']}")
    w(f"- **Existing report:** {c['existing_report'] or 'none found that describes the same behaviour'}.")
    w(f"- **Evidence:** {c['evidence']}.")
    w(f"- **Source:** {sources(c['opened_by'])}.")
    if c["households_shared"]:
        w(f"- **Households where every answer moves alike (no cell rows):** {shared_list(c['households_shared'])}.")
    plist = []
    for p in positions_by_cause[cid]:
        text = f"{short(p['case_id'])} ({LINE_NAME[p['quantity']]}) `{p['position']}`"
        if p["grounds"]:
            text += f" on {GROUNDS_TEXT[p['grounds']]}"
        if p["position"] == "supports_other_answer":
            text += f", {money(p['supported_answer'])} against the key's {money(p['key_value'])}"
        elif p["other_reading_answer"]:
            text += f", key {money(p['key_value'])}, other reading {money(p['other_reading_answer'])}"
        plist.append(text)
    if plist:
        w(f"- **Positions on the key's 2026 answers:** {'; '.join(plist)}.")
    w("")
    rows = sorted(by_cause[cid], key=lambda r: (r["case_id"], r["quantity"], -int(r["table"]), r["answerer"]))
    if rows:
        w("| Household | Line | Table | Answerer | Amount |")
        w("|---|---|---|---|---:|")
        for r in rows:
            w(f"| {short(r['case_id'])} | {LINE_NAME[r['quantity']]} | {r['table']} | `{r['answerer']}` | {money(r['amount'])} |")
        w("")

w("## Cells that are not all_agree in the 2026 key table")
w("")
w("Each row is a household and line of `results/agreement/board100_2026_key.csv` whose answers differ by more than $1. \"Scored\" says whether the board scores the output (it excludes the rest). The policyengine-us column comes from the rerun table, `results/agreement/board100_2026_rerun.csv`. The last column lists each cause with the amount it adds to each answer it moves in the 2026 table (key, policyengine-us, Tax-Calculator, TAXSIM).")
w("")
w("| Case | Line | Class | Scored | Key | policyengine-us 2.60.0 | Tax-Calculator | TAXSIM | Causes and amounts |")
w("|---|---|---|---|---:|---:|---:|---:|---|")
ABBR = {"policybench-key": "key", "policyengine-us": "pe", "taxcalc": "tc", "taxsim": "ts"}
for r in key_table:
    if r["class"] == "all_agree":
        continue
    parts = []
    groups = defaultdict(list)
    for cell in by_cell[(r["case_id"], r["quantity"])]:
        groups[cell["cause_id"]].append(cell)
    for cid in sorted(groups, key=order.get):
        amounts = ", ".join(f"{ABBR[x['answerer']]} {money(x['amount'])}" for x in sorted(groups[cid], key=lambda x: list(ABBR).index(x["answerer"])))
        parts.append(f"`{cid}` ({amounts})")
    w(f"| {short(r['case_id'])} | {r['quantity']} | {r['class']} | {r['board_scores_it']} | {money(r['policyengine'])} | {money(rerun[(r['case_id'], r['quantity'])])} | {money(r['taxcalc'])} | {money(r['taxsim'])} | {'; '.join(parts)} |")
w("")

# ---------------------------------------------------------------- the scored-cell lists, from the positions
cell_order = sorted(positions_by_cell, key=lambda k: (k[0], k[1]))
proposals = [(k, distinct_rows([p for p in positions_by_cell[k] if p["position"] == "supports_other_answer"]))
             for k in cell_order if scored(*k)]
proposals = [(k, rows) for k, rows in proposals if rows]
open_scored = [(k, distinct_rows([p for p in positions_by_cell[k] if p["position"] == "turns_on_unstated_fact"]))
               for k in cell_order if scored(*k)]
open_scored = [(k, rows) for k, rows in open_scored if rows]
named_alt = [(k, [p for p in positions_by_cell[k] if p["position"] == "supports_key" and p["other_reading_answer"]])
             for k in cell_order if scored(*k)]
named_alt = [(k, rows) for k, rows in named_alt if rows]
for k, rows in proposals:
    answers = {p["supported_answer"] for p in rows}
    assert len(answers) == 1, f"{k}: scored cell with more than one supported answer; write how they combine"

w("## Causes that would change a scored answer")
w("")
n = len(proposals)
w(f"{count_words(n, 'scored output')} hold{'s' if n == 1 else ''} a committed answer that, on the entries above, the law or the prompt rule does not support. Each proposal gives the answer that would follow and how this repo computed it. This repo changes nothing on the board, and every entry stays open.")
w("")
w("| Case | Line | Committed key | Answer that would follow | Change | Cause | Grounds | How this repo got the answer |")
w("|---|---|---:|---:|---:|---|---|---|")
for (case, quantity), rows in proposals:
    p = rows[0]
    change = float(p["supported_answer"]) - float(p["key_value"])
    names = ", ".join(f"`{q['cause_id']}`" for q in rows)
    w(f"| {short(case)} | {LINE_NAME[quantity]} | {money(p['key_value'])} | {money(p['supported_answer'])} | {signed(change)} | {names} | {GROUNDS_TEXT[p['grounds']]} | {how(p)} |")
w("")
for (case, quantity), rows in proposals:
    p = rows[0]
    givers = runs_giving(case, quantity, p["supported_answer"])
    note = carried(case, quantity)
    w(f"- **{short(case)}.** Standing of the key's answer: {standing(case, quantity)}; this account contests it."
      + (f" {note}." if note else "")
      + (f" {givers} give{'s' if ' and ' not in givers else ''} the answer that would follow, within $1." if givers else " No run of another lineage gives the answer that would follow."))
w("")
w("### Scored answers that rest on an open reading")
w("")
w("No proposal follows for these: each turns on a fact the board does not state, and the entry takes no side.")
w("")
w("| Case | Line | Committed key | Answer on the other reading | Change | Cause | How this repo got the answer |")
w("|---|---|---:|---:|---:|---|---|")
for (case, quantity), rows in open_scored:
    for p in rows:
        other = p["other_reading_answer"]
        change = signed(float(other) - float(p["key_value"])) if other else ""
        w(f"| {short(case)} | {LINE_NAME[quantity]} | {money(p['key_value'])} | {money(other) if other else 'not computed'} | {change} | `{p['cause_id']}` | {how(p)} |")
w("")
for (case, quantity), rows in open_scored:
    others = sorted({p["other_reading_answer"] for p in rows if p["other_reading_answer"]})
    givers = "; ".join(f"{runs_giving(case, quantity, o)} give{'s' if ' and ' not in runs_giving(case, quantity, o) else ''} {money(o)}"
                       for o in others if runs_giving(case, quantity, o))
    note = carried(case, quantity)
    w(f"- **{short(case)}.** Standing of the key's answer: {standing(case, quantity)}." + (f" {note}." if note else "") + (f" {givers}." if givers else ""))
w("")
w("### Scored answers the entries support against a named alternative")
w("")
w("The entries below support the key's answer but name the answer another reading gives, so a reader can weigh the reading.")
w("")
w("| Case | Line | Committed key | Alternative | Change | Cause | Grounds | How this repo got the alternative |")
w("|---|---|---:|---:|---:|---|---|---|")
for (case, quantity), rows in named_alt:
    for p in rows:
        change = float(p["other_reading_answer"]) - float(p["key_value"])
        w(f"| {short(case)} | {LINE_NAME[quantity]} | {money(p['key_value'])} | {money(p['other_reading_answer'])} | {signed(change)} | `{p['cause_id']}` | {GROUNDS_TEXT[p['grounds']]} | {how(p)} |")
w("")
listed = {k for k, _ in proposals} | {k for k, _ in open_scored} | {k for k, _ in named_alt}
rest = [r for r in key_table if r["class"] != "all_agree" and r["board_scores_it"] == "yes"
        and (r["case_id"], r["quantity"]) not in listed]
backed = [r for r in rest if positions_by_cell[(r["case_id"], r["quantity"])]
          and all(p["position"] in ("supports_key", "no_effect") for p in positions_by_cell[(r["case_id"], r["quantity"])])]
bare = [r for r in rest if r not in backed]
if backed:
    by_line = defaultdict(list)
    for r in backed:
        by_line[r["quantity"]].append(short(r["case_id"]))
    text = "; ".join(f"{', '.join(v)} on {LINE_NAME[q]}" for q, v in by_line.items())
    w(f"The other scored cells that are not all_agree ({text}) hold a key answer that every entry explaining them supports: TAXSIM lacks a provision or departs from the law, or this repo's TAXSIM map cannot express a fact.")
    w("")
if bare:
    w("No entry takes a position on these scored cells that are not all_agree: " + ", ".join(f"{short(r['case_id'])} ({LINE_NAME[r['quantity']]})" for r in bare) + ".")
    w("")

w("### Excluded outputs where an entry disputes the key or leaves it open")
w("")
w("The board scores none of these, so no proposal follows; the table shows where the key and the entries part. Each row is one entry's position. The last answer column gives the answer the entry supports where it supports a different one, and otherwise the answer the other reading gives.")
w("")
w("| Case | Line | Committed key | Cause | Position | Answer the entry names | How this repo got the answer |")
w("|---|---|---:|---|---|---:|---|")
for k in cell_order:
    if scored(*k):
        continue
    for p in positions_by_cell[k]:
        if p["position"] == "supports_other_answer" or p["other_reading_answer"]:
            label = p["position"] + (f" ({GROUNDS_TEXT[p['grounds']]})" if p["grounds"] else "")
            w(f"| {short(k[0])} | {LINE_NAME[k[1]]} | {money(p['key_value'])} | `{p['cause_id']}` | {label} | {money(answer_of(p))} | {how(p)} |")
w("")
w("Where several entries move one excluded output, their changes need not add: a Tax-Calculator counterfactual run gives the combined answer where an entry's note cites one.")
w("")
w("## Entries this pass replaced")
w("")
w("Map version 2026-11-11.1 made four earlier entries moot or wrong. Their ids no longer appear in the tables.")
w("")
for old, new, why in REPLACED:
    assert new in order, new
    assert old not in order, old
    w(f"- `{old}` gave way to `{new}`: {why}.")
w("")

out_path = REPO / "docs" / "causes.md"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text("\n".join(out))
print("wrote", out_path)
