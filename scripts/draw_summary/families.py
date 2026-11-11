"""Note families for the draw summary (scripts/draw_summary/summarize.py): each note on a
model's line maps to one family with a scope: 'taxsim' or 'taxcalc' (a limit of that model or
its map), 'pe' (a note that says policyengine-us treats the fact differently from the statute
or the maps), or 'shared' (a reading or fact note both maps carry for the household)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from keycheck import unit as U

RULES = [
    # TAXSIM
    ("taxsim", "no vehicle loan interest input", r"TAXSIM has no input for qualified passenger vehicle loan interest"),
    ("taxsim", "no charitable deduction for non-itemizers", r"TAXSIM has no charitable deduction for non-itemizers"),
    ("taxsim", "adjustments cut EITC earned income", r"adjustments to income \(IRA, student loan interest"),
    ("taxsim", "SE health and pension deductions in nonprop (EITC, QBI)", r"self-employed health insurance and pension deductions are entered as negative"),
    ("taxsim", "no overtime input", r"TAXSIM has no input for qualified overtime"),
    ("taxsim", "no 2026 minimum QBI deduction", r"minimum qualified business income deduction"),
    ("taxsim", "other taxable income entered as pensions", r"other taxable income .*entered as `pensions`"),
    ("taxsim", "rent and estate income in intrec", r"ignores `otherprop`"),
    ("taxsim", "partnership and farm rent in scorp", r"entered as `scorp`"),
    ("taxsim", "no REIT/PTP input", r"TAXSIM has no input for qualified REIT"),
    ("taxsim", "no saver's credit input", r"TAXSIM has no input for the saver's credit"),
    ("taxsim", "no nontaxable pension input", r"TAXSIM has no input for nontaxable pensions"),
    ("taxsim", "no tax-exempt interest input", r"TAXSIM has no input for tax-exempt interest"),
    ("taxsim", "2026 care credit at pre-2026 rates", r"child care credit at the pre-2026 rates"),
    ("taxsim", "no 199A wage or property limit", r"TAXSIM applies no W-2 wage or property limit"),
    ("taxsim", "no blindness input", r"TAXSIM has no input for blindness"),
    ("taxsim", "no 25%/28% rate gain input", r"unrecaptured section 1250 gain or 28-percent"),
    ("taxsim", "care credit counts children under 13 only", r"TAXSIM counts only children under 13"),
    ("taxsim", "no deemed earned income (21(d)(2))", r"TAXSIM has no deemed earned income"),
    ("taxsim", "no surviving spouse status", r"TAXSIM has no qualifying surviving spouse status"),
    ("taxsim", "any dependent makes head of household", r"TAXSIM files every unmarried taxpayer with a dependent"),
    ("taxsim", "alimony left out", r"^alimony is left out"),
    ("taxsim", "domestic production deduction left out", r"^the domestic production activities deduction is left out"),
    ("taxsim", "separate filer with a dependent", r"files a separate filer"),
    ("taxsim", "ten ages", r"TAXSIM takes ten ages"),
    ("taxsim", "2026 zero rate on gains runs past Rev. Proc. 2025-32 (D6)", r"this build's 2026 zero rate on net capital gain"),
    ("taxsim", "no $400 floor on self-employment tax (P10.3)", r"this build has no \$400 floor"),
    ("taxsim", "a loss in one self-employment box does not offset the other (P7.4, D4)", r"does not net a loss in one box|loss in one TAXSIM box does not offset"),
    # Tax-Calculator
    ("taxcalc", "employee expenses zeroed", r"Tax-Calculator zeroes unreimbursed employee expenses"),
    ("taxcalc", "no REIT/PTP input", r"no Tax-Calculator input for qualified REIT"),
    ("taxcalc", "miscellaneous income through e01200", r"no Tax-Calculator input for miscellaneous income"),
    ("taxcalc", "disability benefits through e01200", r"no Tax-Calculator input for taxable disability benefits"),
    ("taxcalc", "one SSTB flag per unit", r"marks all of a unit's business income as a specified service"),
    ("taxcalc", "alimony no effect", r"Tax-Calculator gives alimony no effect"),
    ("taxcalc", "domestic production deduction zeroed", r"Tax-Calculator zeroes the domestic production"),
    ("taxcalc", "no deemed earned income (21(d)(2))", r"Tax-Calculator has no deemed earned income"),
    ("taxcalc", "Form 4952 election from dividends only", r"Tax-Calculator takes the Form 4952 election"),
    ("taxcalc", "e18400 is 0", r"e18400 is 0"),
    # PolicyEngine's treatment differs (named in the note)
    ("pe", "163(d) limit (PE deducts all investment interest)", r"policyengine-us deducts all of it"),
    ("pe", "162(l) limit (PE limits to Schedule C income)", r"policyengine-us allows .*Schedule C income"),
    ("pe", "vehicle phase-out start for a surviving spouse", r"policyengine-us starts its phase-out at \$200,000"),
    ("pe", "care expenses of a non-qualifying person", r"policyengine-us adds every member's"),
    ("pe", "reading: alimony (PE's default makes it pre-2019)", re.escape(U.READINGS["alimony"])),
    ("pe", "reading: rent and estate income not QBI (PE's default counts rent)", re.escape(U.READINGS["rental_qbi"])),
    # Shared notes
    ("shared", "shared SALT assumption", r"shared assumption: state and local income or sales tax"),
    ("shared", "member's own income", r"has income of their own"),
    ("shared", "member's own expense or deduction", r"which is not (an expense|a deduction) of the head's return"),
    ("shared", "member meets neither dependency test", r"meets neither dependency test"),
    ("shared", "member's own payroll or SE tax", r"has (self-employment )?earnings of their own"),
    ("shared", "member not claimed: medical counts", r"is not claimed, and their medical expenses count"),
    ("shared", "401(k) deferrals scaled", r"401\(k\) deferrals (above|.*scaled)"),
    ("shared", "163(d) election cut", r"the Form 4952 election of"),
    ("shared", "SEP limit below the pension taken", r"exceeds what a SEP could deduct"),
    ("shared", "married filing separately: no EITC", r"32\(d\)\(1\) allows no earned income credit"),
]
COMPILED = [(scope, name, re.compile(rx)) for scope, name, rx in RULES]
READING_TEXT = sorted(U.READINGS.items(), key=lambda kv: -len(kv[1]))


def family(note: str) -> tuple[str, str]:
    for scope, name, rx in COMPILED:
        if rx.search(note):
            return scope, name
    for key, text in READING_TEXT:
        if text in note:
            return "shared", f"reading: {key}"
    return "unknown", note[:80]


# A fact neither Tax-Calculator nor TAXSIM can take: when both maps note it, the two agree
# without it and PolicyEngine, which takes it, stands apart.
COMMON_MISSING = {
    "no REIT/PTP input": ("no REIT/PTP input", "no REIT/PTP input"),
    "no deemed earned income (21(d)(2))": ("no deemed earned income (21(d)(2))", "no deemed earned income (21(d)(2))"),
    "domestic production deduction": ("domestic production deduction zeroed", "domestic production deduction left out"),
}
