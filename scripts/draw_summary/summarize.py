"""Write results/draw1000_summary.md and .csv: the draw's three-model comparison, aggregates only.

It reads the git-ignored local draw files (data/draw/draw1000_seed20261110.csv, the three
2026 runs under results/pe, results/taxcalc and results/taxsim, results/answers_draw1000.csv
and results/agreement/draw1000_2026.csv) and, for the board column of the composition table,
the committed dossiers and board Tax-Calculator run. No household row reaches the outputs;
--debug writes the case ids of the unexplained cells to a file you name (keep it out of git).

  python3 scripts/draw_summary/summarize.py
  python3 scripts/draw_summary/summarize.py --out-md X.md --out-csv X.csv --debug X.json
"""
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pe_checks as PC
from families import COMMON_MISSING, family
from pe_checks import read_rows

from keycheck import households as H
from keycheck import unit as U

parser = argparse.ArgumentParser()
parser.add_argument("--out-md", type=Path, default=ROOT / "results/draw1000_summary.md")
parser.add_argument("--out-csv", type=Path, default=ROOT / "results/draw1000_summary.csv")
parser.add_argument("--debug", type=Path)
args = parser.parse_args()
REPO = ROOT

LINES = [
    ("federal_income_tax_before_refundable_credits", "Income tax before refundable credits"),
    ("federal_refundable_credits", "Refundable credits"),
    ("self_employment_tax", "Self-employment tax"),
    ("federal_employee_payroll_tax", "Employee payroll tax (federal)"),
]
CLASSES = [("all_agree", "All agree"), ("two_agree:policyengine", "PolicyEngine apart"),
           ("two_agree:taxcalc", "Tax-Calculator apart"), ("two_agree:taxsim", "TAXSIM apart"),
           ("all_differ", "All differ")]
APART = {"two_agree:policyengine": "policyengine", "two_agree:taxcalc": "taxcalc", "two_agree:taxsim": "taxsim"}

agreement = read_rows(REPO / "results/agreement/draw1000_2026.csv")
answers = {}
for r in read_rows(REPO / "results/answers_draw1000.csv"):
    answers[(r["model"], r["case_id"], r["quantity"])] = r
draw = {h["id"]: h for h in H.load(REPO / "data/draw/draw1000_seed20261110.csv")}
assert len(draw) == 1000 and len(agreement) == 4000

def notes_of(model, case, quantity):
    r = answers.get((model, case, quantity))
    return [n for n in ((r or {}).get("unexpressed_facts") or "").split(" || ") if n]

def fams(model, case, quantity):
    return {family(n) for n in notes_of(model, case, quantity)}

PE_RUN = PC.load_pe()
TC_ROWS = {r["case_id"]: r for r in read_rows(REPO / "results/taxcalc/draw1000_tc6.9.0_2026.csv")}
_pe_side = {}
def pe_side(case, quantity):
    """Families where PolicyEngine's own run shows it took the other side of a reading both
    maps share (pe_checks), limited to the lines each can reach."""
    if case not in _pe_side:
        h = draw[case]
        u = U.build(h, 2026)
        found = PC.checks(h, u, PE_RUN[case], TC_ROWS[case])
        found += PC.medical(PE_RUN[case], TC_ROWS[case], " || ".join(notes_of("taxcalc", case, "federal_income_tax_before_refundable_credits")))
        _pe_side[case] = found
    return {("pe-run", f) for f in _pe_side[case] if quantity in PC.LINES_OF.get(f, PC.DEFAULT_LINES)}

def pe_apart(tc, ts, case, quantity):
    """PolicyEngine carries no notes. Three kinds of evidence explain it standing apart in kind:
    a note both maps carry that names PolicyEngine's different treatment; a fact both other
    models lack an input for (both maps note it); PolicyEngine's own run taking the other
    side of a reading both maps share."""
    out = {f for f in tc & ts if f[0] == "pe"}
    for name, (tc_name, ts_name) in COMMON_MISSING.items():
        if ("taxcalc", tc_name) in tc and ("taxsim", ts_name) in ts:
            out.add(("both", name))
    return out | pe_side(case, quantity)

def explanation(cls, case, quantity):
    """(explained families, literal: does the apart model carry any note on the line)."""
    tc, ts = fams("taxcalc", case, quantity), fams("taxsim", case, quantity)
    if cls == "two_agree:taxsim":
        return sorted({f for f in ts if f[0] == "taxsim"}), bool(ts)
    if cls == "two_agree:taxcalc":
        return sorted({f for f in tc if f[0] == "taxcalc"}), bool(tc)
    if cls == "two_agree:policyengine":
        return sorted(pe_apart(tc, ts, case, quantity)), bool(tc & ts)
    if cls == "all_differ":
        return sorted({f for f in tc | ts if f[0] in ("taxsim", "taxcalc")} | pe_apart(tc, ts, case, quantity)), bool(tc | ts)
    return [], False

STATED_SKIP = U.NON_TAX_INPUTS | U.MEMO_INPUTS
def stated_inputs(h):
    names = set()
    for p in H.people(h):
        if H.amount(p, "employment_income"):
            names.add("employment_income")
        names.update(k for k, v in p.get("inputs", {}).items() if v and k not in STATED_SKIP)
    for entity in ("tax_unit", "spm_unit", "household"):
        names.update(k for k, v in h.get(f"{entity}_inputs", {}).items() if v and k not in STATED_SKIP)
    return sorted(names)

csv_rows = []
md = []
md.append("# The 1,000-household draw: three models compared (tax year 2026)")
md.append("")
md.append("scripts/draw_summary/summarize.py writes this page and its CSV from the git-ignored local draw files (the board column of the composition table comes from the committed dossiers and board Tax-Calculator run). "
          "This summary compares PolicyEngine (policyengine-us 2.60.0 with the board's conventions), "
          "Tax-Calculator 6.9.0 and NBER TAXSIM (build cd2026110117) on the 1,000 households of the draw "
          "(seed 20261110), for tax year 2026. The input maps are keycheck version 2026-11-10.3. No committed "
          "key exists for the draw, so PolicyEngine's own run stands as its answer. Two answers agree when they "
          "differ by no more than $1. The record-level files stay out of git; this page and its CSV hold "
          "aggregates only.")
md.append("")
md.append("## Agreement by line")
md.append("")
md.append("| Line | Households | " + " | ".join(label for _, label in CLASSES) + " |")
md.append("|---|---:|" + "---:|" * len(CLASSES))
counts = {q: collections.Counter(r["class"] for r in agreement if r["quantity"] == q) for q, _ in LINES}
for q, label in LINES:
    total = sum(counts[q].values())
    other = set(counts[q]) - {c for c, _ in CLASSES}
    assert not other, other
    cells = []
    for c, clabel in CLASSES:
        n = counts[q].get(c, 0)
        cells.append(f"{n} ({100 * n / total:.1f}%)")
        csv_rows.append({"section": "agreement", "line": q, "class": c, "item": clabel, "count": n, "share": f"{n / total:.4f}"})
    md.append(f"| {label} | {total} | " + " | ".join(cells) + " |")
md.append("")

# Attribution in kind
explained_total = unexplained_total = literal_total = 0
fam_counts = collections.Counter()
per_line = collections.defaultdict(collections.Counter)
unexplained = []
for r in agreement:
    cls = r["class"]
    if cls == "all_agree":
        continue
    fams_found, literal = explanation(cls, r["case_id"], r["quantity"])
    vals = {m: float(r[m]) for m in ("policyengine", "taxcalc", "taxsim")}
    if cls in APART:
        odd = APART[cls]
        rest = [v for m, v in vals.items() if m != odd]
        size = abs(vals[odd] - sum(rest) / 2)
    else:
        size = max(vals.values()) - min(vals.values())
    if fams_found:
        explained_total += 1
        per_line[(r["quantity"], cls)]["explained"] += 1
        for f in fams_found:
            fam_counts[(r["quantity"], cls, f[0], f[1])] += 1
    else:
        unexplained_total += 1
        per_line[(r["quantity"], cls)]["unexplained"] += 1
        if literal:
            per_line[(r["quantity"], cls)]["unexplained_with_shared_notes"] += 1
        unexplained.append((size, r["quantity"], cls, r["case_id"], vals))
    if literal:
        literal_total += 1

md.append("## Differences explained in kind")
md.append("")
md.append("For each household and line where the models do not all agree, this section asks whether the evidence "
          "explains the difference in kind. A cell counts as explained when one of these holds for the model that stands apart:")
md.append("")
md.append("- TAXSIM or Tax-Calculator apart: that model's map carries a note of its own on the line, for a fact the map "
          "could not express or a limit of the model (several found by probes of the TAXSIM build).")
md.append("- PolicyEngine apart (it carries no notes): both maps carry a note that names PolicyEngine's different treatment "
          "(its full deduction of investment interest, its looser 162(l) limit, its default divorce year for alimony, its "
          "default that rent is qualified business income, its count of care expenses); or both maps note a fact that "
          "neither Tax-Calculator nor TAXSIM can take, so those two agree without it; or PolicyEngine's own run shows it "
          "took the other side of a reading both maps share (it claims a member the maps leave out, it does not count a "
          "disabled adult as an EITC child, it files a different status, or its medical expense deduction exceeds the "
          "stated amounts' at the same AGI). The run's per-person outputs show which side it took; this unit did not read "
          "PolicyEngine's code for why.")
md.append("- All three differ: any of the above on any model.")
md.append("")
md.append("A reading both maps share, with no sign of PolicyEngine taking the other side, does not explain why one model "
          "stands apart, so it does not count; the table shows how many unexplained cells carry only such notes. Notes say "
          "what kind of difference to expect, not its size: this unit traced no dollars, so a cell can count as explained "
          "by a note whose effect is smaller than the gap.")
md.append("")
md.append("| Line | Class | Cells | Explained | Unexplained | Of which only shared notes |")
md.append("|---|---|---:|---:|---:|---:|")
for q, label in LINES:
    for c, clabel in CLASSES[1:]:
        pl = per_line[(q, c)]
        n = pl["explained"] + pl["unexplained"]
        if not n:
            continue
        md.append(f"| {label} | {clabel} | {n} | {pl['explained']} | {pl['unexplained']} | {pl['unexplained_with_shared_notes']} |")
        for k in ("explained", "unexplained", "unexplained_with_shared_notes"):
            csv_rows.append({"section": "attribution", "line": q, "class": c, "item": k, "count": pl[k],
                             "share": f"{pl[k] / n:.4f}"})
total_cells = explained_total + unexplained_total
md.append(f"| All lines | All classes | {total_cells} | {explained_total} | {unexplained_total} | "
          f"{sum(per_line[k]['unexplained_with_shared_notes'] for k in per_line)} |")
md.append("")
md.append(f"Of {total_cells} cells where the models do not all agree, {explained_total} "
          f"({100 * explained_total / total_cells:.1f}%) have evidence that explains the difference in kind and "
          f"{unexplained_total} ({100 * unexplained_total / total_cells:.1f}%) have none. Read literally (any note "
          f"at all on the line of the model that stands apart, shared readings included, and for PolicyEngine any note "
          f"both maps carry), {literal_total} cells carry one.")
csv_rows.append({"section": "attribution", "line": "all", "class": "all", "item": "explained", "count": explained_total, "share": f"{explained_total / total_cells:.4f}"})
csv_rows.append({"section": "attribution", "line": "all", "class": "all", "item": "unexplained", "count": unexplained_total, "share": f"{unexplained_total / total_cells:.4f}"})
csv_rows.append({"section": "attribution", "line": "all", "class": "all", "item": "any_note_on_apart_model_literal", "count": literal_total, "share": f"{literal_total / total_cells:.4f}"})
md.append("")
md.append("### Note families behind the explained cells")
md.append("")
md.append("A cell can carry more than one family, so the counts add up to more than the explained cells.")
md.append("")
md.append("| Line | Class | Model the note concerns | Note family | Cells |")
md.append("|---|---|---|---|---:|")
scope_label = {"taxsim": "TAXSIM", "taxcalc": "Tax-Calculator", "pe": "PolicyEngine (note names it)",
               "pe-run": "PolicyEngine (its own run)", "both": "Tax-Calculator and TAXSIM"}
label_of = dict(LINES); class_label = dict(CLASSES)
for (q, c, scope, name), n in sorted(fam_counts.items(), key=lambda kv: ([x for x, _ in LINES].index(kv[0][0]), kv[0][1], -kv[1])):
    md.append(f"| {label_of[q]} | {class_label[c]} | {scope_label[scope]} | {name} | {n} |")
    csv_rows.append({"section": "families", "line": q, "class": c, "item": f"{scope_label[scope]}: {name}", "count": n, "share": ""})
md.append("")

TS_ROWS = {r["case_id"]: r for r in read_rows(REPO / "results/taxsim/draw1000_cd2026110117_2026.csv")}
def observation(case):
    """What the three runs show for one household, from their saved outputs only."""
    pe, tc, ts = PE_RUN[case], TC_ROWS[case], TS_ROWS[case]
    v = lambda name: float(pe[name]["value"])
    agi = {"pe": v("adjusted_gross_income"), "tc": float(tc["out_c00100"]), "ts": float(ts["out_v10"])}
    misc = sum(H.amount(p, "miscellaneous_income") for p in H.people(draw[case]))
    gap = agi["pe"] - agi["tc"]
    if abs(agi["tc"] - agi["ts"]) <= 1 and gap > 1:
        if misc < 0 and abs(gap + misc) <= 1:
            return (f"PolicyEngine's AGI exceeds both maps' by {gap:,.2f}, the size of the stated negative miscellaneous "
                    "income, which both maps subtract (no reading covers a negative amount there)")
        return f"PolicyEngine's AGI exceeds both maps' by {gap:,.2f}; the saved run does not show the source"
    if abs(gap) <= 1 and v("savers_credit") > 0 and float(tc.get("in_e07240") or 0) == 0:
        return (f"AGI and taxable income agree; PolicyEngine's run allows a saver's credit of {v('savers_credit'):,.2f}, "
                "where the maps' statute figure is 0 (the household states taxable pension income)")
    return "AGI and taxable income agree across the three; not traced further"

md.append("## The largest unexplained differences")
md.append("")
md.append(f"Only {unexplained_total} cells have no explaining evidence, so this lists all of them, largest first (at most ten). "
          "Size: for one model apart, its distance from the mean of the two that agree; where all differ, the "
          "range of the three answers. Stated inputs: every input the household states that can reach a federal "
          "line (the inputs named as having no effect are left out). The last column says what the three runs' saved "
          "outputs show, without tracing dollars.")
md.append("")
md.append("| Rank | Line | Class | Size ($) | Stated inputs | What the runs show |")
md.append("|---:|---|---|---:|---|---|")
unexplained.sort(key=lambda x: -x[0])
debug = []
for rank, (size, q, c, case, vals) in enumerate(unexplained[:10], start=1):
    inputs = stated_inputs(draw[case])
    seen = observation(case)
    md.append(f"| {rank} | {label_of[q]} | {class_label[c]} | {size:,.2f} | {', '.join(inputs)} | {seen} |")
    csv_rows.append({"section": "largest_unexplained", "line": q, "class": c, "item": f"rank {rank}: " + "; ".join(inputs) + " | " + seen, "count": f"{size:.2f}", "share": ""})
    debug.append({"rank": rank, "case": case, "line": q, "class": c, "size": size, "values": vals})

# Composition
def composition(households, tc_path):
    units = [U.build(h, 2026) for h in households]
    n = len(units)
    status = collections.Counter(u.status for u in units)
    children = sum(1 for h in households if any(int(p["age"]) < 18 for p in H.people(h)))
    se_keys = ("self_employment_income", "sstb_self_employment_income_before_lsr", "farm_operations_income") + U.PARTNERSHIP_SE_NAMES
    se = sum(1 for h in households if any(H.amount(p, k) for p in H.people(h) for k in se_keys))
    tc = read_rows(tc_path)
    itemize = sum(1 for r in tc if float(r["out_c04470"]) > 0)
    assert len(tc) == n
    return n, status, children, se, itemize

board = [json.loads(p.read_text())["stated_facts"] for p in sorted((REPO / "results/dossiers").glob("scenario_*.json"))]
bn, bstatus, bchildren, bse, bitem = composition(board, REPO / "results/taxcalc/board100_tc6.9.0_2026.csv")
dn, dstatus, dchildren, dse, ditem = composition(list(draw.values()), REPO / "results/taxcalc/draw1000_tc6.9.0_2026.csv")
md.append("")
md.append("## The draw beside the board")
md.append("")
md.append("The draw is a separate sample of 1,000 households (seed 20261110), not the board, and its mix differs from "
          "the board's 100. Filing status is the one keycheck derives from the stated facts for 2026; itemizing is "
          "Tax-Calculator's own choice in its 2026 run.")
md.append("")
md.append("| Measure | Board (100) | Draw (1,000) |")
md.append("|---|---:|---:|")
def pct(k, n):
    return f"{k} ({100 * k / n:.1f}%)"
status_label = {"single": "Single", "joint": "Married filing jointly", "separate": "Married filing separately",
                "head_of_household": "Head of household", "surviving_spouse": "Surviving spouse"}
for s, slabel in status_label.items():
    if bstatus.get(s) or dstatus.get(s):
        md.append(f"| Filing status: {slabel} | {pct(bstatus.get(s, 0), bn)} | {pct(dstatus.get(s, 0), dn)} |")
        csv_rows.append({"section": "composition", "line": "", "class": "", "item": f"filing status: {s}", "count": f"board {bstatus.get(s, 0)}; draw {dstatus.get(s, 0)}", "share": f"board {bstatus.get(s, 0) / bn:.4f}; draw {dstatus.get(s, 0) / dn:.4f}"})
for item, b, d in (("Households with a member under 18", bchildren, dchildren),
                   ("Households with self-employment income", bse, dse),
                   ("Households Tax-Calculator itemizes", bitem, ditem)):
    md.append(f"| {item} | {pct(b, bn)} | {pct(d, dn)} |")
    csv_rows.append({"section": "composition", "line": "", "class": "", "item": item, "count": f"board {b}; draw {d}", "share": f"board {b / bn:.4f}; draw {d / dn:.4f}"})
md.append("")

args.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
with open(args.out_csv, "w", newline="", encoding="utf-8") as h:
    w = csv.DictWriter(h, fieldnames=["section", "line", "class", "item", "count", "share"])
    w.writeheader(); w.writerows(csv_rows)
if args.debug:
    with open(args.debug, "w", encoding="utf-8") as h:
        json.dump({"top_unexplained": debug, "unexplained_all": [(s, q, c, k) for s, q, c, k, _ in unexplained]}, h, indent=1)
print(f"wrote {args.out_md} and {args.out_csv}: {total_cells} cells not all-agree, {explained_total} explained in kind, {unexplained_total} unexplained")
