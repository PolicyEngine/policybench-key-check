"""Write docs/causes.md from results/causes.csv, results/cause_cells.csv and the agreement table."""
import csv
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
L1 = "federal_income_tax_before_refundable_credits"
L2 = "federal_refundable_credits"
LINE_NAME = {L1: "tax before refundable credits", L2: "refundable credits"}

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
    "map-ira-deduction-in-nonprop-cuts-eitc": "The TAXSIM map's IRA deduction lowers earned income",
    "map-rental-not-qualified-business-income": "The maps treat rent as income outside a trade or business",
    "pe-other-dependent-credit-without-dependency-tests": "policyengine-us pays the other-dependent credit without the dependency tests",
    "pe-divorce-year-default": "policyengine-us dates an unstated divorce to 2010",
    "pe-medicare-part-b-premium-default": "policyengine-us adds a Medicare premium the household does not state",
    "pe-net-investment-income-leaves-out-farm-rent": "policyengine-us 2.60.0 leaves farm rent out of net investment income",
    "key-ira-deducted-without-219g": "The key deducts IRA contributions without the active-participant limit",
    "key-sales-tax-table-column-shift": "The key holds a shifted sales tax table",
    "shared-state-tax-refund-counted-in-full": "A state tax refund counts in full as income",
    "shared-disability-benefits-taxable": "Disability benefits count as income",
    "shared-scholarship-not-income": "A stated scholarship stays out of income",
    "shared-financial-assistance-gift": "Help from outside the household counts as a gift",
    "shared-disabled-member-qualifying-child": "A member the board calls disabled counts as a qualifying child",
    "shared-net-investment-income-tax-in-line": "The line includes the net investment income tax",
    "shared-state-income-tax-withholding-estimate": "State income tax comes from a withholding estimate",
    "shared-state-paid-leave-contributions-not-in-salt": "Connecticut paid leave contributions stay out of the state and local tax deduction",
    "shared-passive-rental-loss-allowed": "A passive rental loss reduces income",
    "shared-mortgage-debt-after-2017": "Mortgage debt counts as incurred after 2017",
    "shared-head-return-only": "The line covers the head's return only",
    "shared-bdc-income-not-added": "BDC income stays out of income",
    "shared-survivor-benefits-not-taxable": "Survivor benefits stay out of income",
    "shared-over-the-counter-not-medical": "Over-the-counter expenses stay out of medical expenses",
}

KIND_TEXT = [
    ("model-law-departure", "A model computes a provision the law gives, but computes it differently from the law."),
    ("model-no-provision", "A model has no input for a stated fact, or no provision for the law of the year, so its answer leaves the provision out."),
    ("pe-default-unstated-fact", "policyengine-us fills a fact the household does not state with a default value, and the default moves the answer."),
    ("key-decided-value", "The committed key holds a value the board decided on an earlier engine release, and that value differs from what the engine gives today."),
    ("map-limit", "This repo's input map cannot express a stated fact in Tax-Calculator or TAXSIM the way the law treats it, or reads a fact differently from policyengine-us."),
    ("shared-reading", "Every answerer, or every answerer but the key, reads a stated or unstated fact the same way. Where all answers in a table move alike the reading leaves no trace in any difference, so the entry lists the households in `households_shared` and writes no cell rows; where the key's frozen value departs from the others, the entry writes rows for the answers it moves."),
    ("unexplained", "A residual no trace accounts for. No entry has this kind."),
]


def read(path):
    with open(REPO / path, newline="") as handle:
        return list(csv.DictReader(handle))


def money(x):
    x = float(x)
    return f"{x:,.2f}" if x >= 0 else f"-{-x:,.2f}"


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


causes = read("results/causes.csv")
cells = read("results/cause_cells.csv")
key_table = read("results/agreement/board100_2026_key.csv")
rerun = {(r["case_id"], r["quantity"]): r["policyengine"] for r in read("results/agreement/board100_2026_rerun.csv")}
by_cause = defaultdict(list)
by_cell = defaultdict(list)
for r in cells:
    by_cause[r["cause_id"]].append(r)
    if r["table"] == "2026":
        by_cell[(r["case_id"], r["quantity"])].append(r)
order = {c["cause_id"]: i for i, c in enumerate(causes)}

out = []
w = out.append
w("# Causes of disagreement on the board's 100 households")
w("")
w("This file gives, for every household and line where the committed key, policyengine-us, Tax-Calculator and TAXSIM disagree, the causes of the disagreement, how much each cause moves each answer, what the law says, and which answer the law supports. `results/causes.csv` holds one row per cause and `results/cause_cells.csv` one row per cause, household, line, table and answerer; this account renders both. `tests/test_causes.py` checks that the causes account for every difference to the dollar.")
w("")
w("Claude Opus 5.5 agents opened every entry: four tracers reconciled each disagreement to its cause (`evidence/traces/trace-pe-a.md`, `trace-pe-b.md`, `trace-taxsim-a.md`, `trace-taxsim-b.md`), reviewers checked the maps (`evidence/traces/verify-*.md`), and a further agent wrote these tables on 2026-11-10. Every entry stays open. The \"who is right\" line states the entry's position and its grounds in law; it awaits a human reviewer and decides nothing. This repo proposes answers; it changes nothing on the board.")
w("")
w("## How to read the entries")
w("")
w("**Answerers and tables.** The 2026 table compares four answers: the committed key (`policybench-key`, run `pb-reference-2.60.0`), policyengine-us 2.60.0 under the board's conventions (`pe-2.60.0-board-2026`), Tax-Calculator 6.9.0 (`taxcalc-6.9.0-2026`) and TAXSIM's test build cd2026110117 (`taxsim-cd2026110117-2026`). The 2025 table compares the last three under 2025 law (`pe-2.60.0-board-2025`, `taxcalc-6.9.0-2025`, `taxsim-cd2026110117-2025`). `results/runs.csv` describes each run. The lines are the four in `scripts/agreement.py`; every cause here moves federal tax before refundable credits or federal refundable credits.")
w("")
w("**Amounts.** A cell's amount is what the cause adds to that answerer's answer, in dollars, relative to the answer the law supports, or, where the cause turns on a fact the household does not state, the answer the board's prompt rule supports. A cause that lowers a refundable credit has a negative amount on that line. For any two answerers, the difference between their answers equals the difference between the sums of their amounts, within $1; the largest residual is $0.30 (081, cents).")
w("")
w("**The prompt rule.** The board tells every answerer to treat an unlisted number as 0 and any other unlisted fact, boolean or status as false, to assume filing and take-up when required, and not to infer unlisted income, expenses, assets, benefit receipt, rent or health coverage (`PolicyEngine/policybench@c7ede86c:policybench/prompts.py:15-27`). These entries read the rule one way throughout: a provision that includes or allows something only on a fact does not apply when the household does not state the fact, and a provision that excludes or denies something only on a fact does not apply either. Where the cause is an unstated fact, the entry says that no answer is right until the household states the fact, and then which answer the rule points to.")
w("")
w("**Counterfactual runs.** Where an entry cites a counterfactual run, it means Tax-Calculator 6.9.0 or TAXSIM cd2026110117 run on the inputs recorded in `results/dossiers/<case>.json` (the `in_` fields under `other_models`), with the settings of `scripts/run_taxcalc.py` or `keycheck/taxsim.py`, changing only the input the entry names. The engine experiments sit in `results/repro/`.")
w("")
w("**Cell standing.** Where this account describes a cell's standing it uses three phrases: an answer \"reproduced by a run of another lineage\" (Tax-Calculator or TAXSIM gives it within $1), \"contested\" (an entry here says the law or the prompt rule supports a different answer), and \"resting on one model\" (no run of another lineage gives it).")
w("")
w("## Kinds")
w("")
w("| Kind | Meaning | Entries |")
w("|---|---|---:|")
for kind, text in KIND_TEXT:
    n = sum(1 for c in causes if c["kind"] == kind)
    w(f"| `{kind}` | {text} | {n} |")
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
out_path = REPO / "docs" / "causes.md"
out_path.parent.mkdir(exist_ok=True)
tail = (Path(__file__).parent / "docs_tail.md").read_text()
out_path.write_text("\n".join(out) + "\n" + tail)
print("wrote", out_path)
