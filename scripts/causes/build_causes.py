"""Write results/causes.csv, results/cause_cells.csv and results/cause_positions.csv, checking first.

Run with python3 -I from anywhere; it writes into REPO only after every check passes:
the invariant (every pairwise answer difference equals the difference of cause amounts within
$1, in both tables) and the positions (one row per cause, household and line where an entry
takes a position on the key's 2026 answer; every cell row on the key's run has one, and so does
every household a shared reading lists for the 2026 table).
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
L1 = "federal_income_tax_before_refundable_credits"
L2 = "federal_refundable_credits"
LINES = (L1, L2, "self_employment_tax", "federal_employee_payroll_tax")
RUNS = {
    ("2026", "policybench-key"): "pb-reference-2.60.0",
    ("2026", "policyengine-us"): "pe-2.60.0-board-2026",
    ("2026", "taxcalc"): "taxcalc-6.9.0-2026",
    ("2026", "taxsim"): "taxsim-cd2026110117-2026",
    ("2025", "policyengine-us"): "pe-2.60.0-board-2025",
    ("2025", "taxcalc"): "taxcalc-6.9.0-2025",
    ("2025", "taxsim"): "taxsim-cd2026110117-2025",
}
T = "evidence/traces/"
OB = "Claude Opus 5.5 agents: {}; causes unit, 2026-11-10"
OB2 = "Claude Opus 5.5 agents: {}; causes unit, second pass for map version 2026-11-11.1, 2026-11-11"
V = "keycheck 2026-11-11.1"
B2 = f"{T}builder-2.md"
RX26 = "results/repro/reading_experiments_pe_2.60.0.txt"
RX116 = "results/repro/reading_experiments_pe_2.116.15.txt"
U = "keycheck/unit.py"
SM_TC = "docs/second-map-taxcalc.md"
SM_TS = "docs/second-map-taxsim.md"
PE = "policyengine_us/"  # cited at 2.60.0 unless marked
BOARD = "PolicyEngine/policybench@c7ede86c:"
META = BOARD + "reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json"
EXCL = BOARD + "reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json"
PROMPT = BOARD + "policybench/prompts.py:15-27"

CAUSES = []
CELLS = []


def cause(**row):
    CAUSES.append(row)


def cells(cause_id, rows, basis):
    """rows: (case, quantity, table, answerer, amount)."""
    for case, quantity, table, answerer, amount in rows:
        CELLS.append(dict(cause_id=cause_id, case_id=f"scenario_{case}", quantity=quantity,
                          table=table, answerer=answerer, run=RUNS[(table, answerer)],
                          amount=f"{amount:.2f}", basis=basis))


def both(case, quantity, answerer, a26, a25=None):
    return [(case, quantity, "2026", answerer, a26), (case, quantity, "2025", answerer, a26 if a25 is None else a25)]


# ---------------------------------------------------------------- TAXSIM's test build
cause(
    cause_id="taxsim-no-overtime-deduction",
    kind="model-no-provision",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=f"{L1};{L2}",
    summary="TAXSIM's test build has no input for qualified overtime compensation, so it taxes the overtime premium that policyengine-us and Tax-Calculator deduct. Where the child tax credit absorbs all the tax (026), the higher tax leaves less credit to refund.",
    law="26 U.S.C. 225(a)-(c) (deduction for qualified overtime compensation, taxable years 2025 through 2028); 26 U.S.C. 63(b)(6) (allowed to filers who do not itemize)",
    law_figure="up to $12,500 ($25,000 joint), reduced by $100 for each $1,000 of modified AGI above $150,000 ($300,000 joint)",
    who_is_right="policyengine-us and Tax-Calculator. The board states an FLSA overtime premium inside wages, which 225(c)(1) makes qualified overtime compensation; the test build cannot take the fact, so its answer leaves out a deduction the law allows.",
    existing_report="",
    evidence=f"{T}trace-taxsim-a.md (026, 037, 046, 049, 064: Tax-Calculator with overtime_income 0 gives TAXSIM's answer; TAXSIM with the deduction entered as negative nonprop gives policyengine-us's); {T}trace-taxsim-b.md (089, 091, 117); evidence/taxsim.md (probe P1.2: no input); keycheck/map_taxsim.py (fsla_overtime_premium listed as unexpressed)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-a.md, {T}trace-taxsim-b.md"),
)
B = "trace run: Tax-Calculator with the provision removed gives TAXSIM's answer, and TAXSIM with the deduction entered gives the others'"
cells("taxsim-no-overtime-deduction",
      both("026", L2, "taxsim", -929.55) + both("037", L1, "taxsim", 1155.48) + both("046", L1, "taxsim", 1780.65)
      + both("049", L1, "taxsim", 5500.00, 5559.54) + both("064", L1, "taxsim", 1667.91) + both("089", L1, "taxsim", 416.09)
      + both("091", L1, "taxsim", 75.35) + both("117", L1, "taxsim", 5602.67, 5669.02),
      B)

cause(
    cause_id="taxsim-no-nonitemizer-charitable-deduction",
    kind="model-no-provision",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="2026",
    quantities=L1,
    summary="From 2026 a filer who takes the standard deduction also deducts cash gifts to charity up to a cap. TAXSIM's test build has no input or provision for it, so its taxable income keeps the gifts the other models deduct. In 117 TAXSIM itemizes instead (33,830.22), which falls 369.77 short of the standard deduction plus the gifts.",
    law="26 U.S.C. 170(p) as amended by Pub. L. 119-21 sec. 70424 (taxable years after 2025), determined without regard to the 0.5% floor of 170(b)(1)(I); 26 U.S.C. 63(b)(4)",
    law_figure="cash gifts up to $1,000 ($2,000 joint)",
    who_is_right="policyengine-us and Tax-Calculator. 170(p) counts cash gifts to an organization described in 170(b)(1)(A), other than a supporting organization or a donor-advised fund. This entry reads the stated charitable cash donations as gifts to such an organization; the board does not state the recipient, and the prompt rule makes the two unstated exceptions false, so the gifts qualify.",
    existing_report="",
    evidence=f"{T}trace-pe-a.md (005, 020: Tax-Calculator with STD_charity_ded_nonitemizers_max 0 gives TAXSIM's answer to the cent); {T}trace-taxsim-a.md (049, 055, 082); {T}trace-taxsim-b.md (099, 110, 117, 122, 123); evidence/taxsim.md (probe P9.5)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}trace-taxsim-a.md, {T}trace-taxsim-b.md"),
)
cells("taxsim-no-nonitemizer-charitable-deduction",
      [(c, L1, "2026", "taxsim", a) for c, a in (("005", 342.33), ("020", 68.60), ("049", 127.55), ("055", 240.00),
                                                ("082", 154.00), ("099", 440.00), ("110", 92.99), ("117", 88.74),
                                                ("122", 120.00), ("123", 240.00))],
      "trace run: Tax-Calculator with the cash gifts (or the 170(p) cap) set to 0 gives TAXSIM's answer")

cause(
    cause_id="taxsim-no-tax-exempt-interest-input",
    kind="model-no-provision",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="TAXSIM has no input for tax-exempt interest, so the Social Security taxability test leaves it out of modified AGI and TAXSIM taxes less of the benefits.",
    law="26 U.S.C. 86(b)(2)(B) (modified AGI for taxing Social Security includes tax-exempt interest)",
    law_figure="base amount $25,000 and adjusted base amount $34,000 (single); 85% cap on the taxable part",
    who_is_right="policyengine-us and Tax-Calculator: the stated tax-exempt interest raises the taxable part of Social Security.",
    existing_report="",
    evidence=f"{T}trace-taxsim-a.md (000: Tax-Calculator with e00400 0 gives TAXSIM's answer; TAXSIM with the law's taxable benefits entered gives the others'); {T}trace-taxsim-b.md (122); evidence/taxsim.md (P15.5)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-a.md, {T}trace-taxsim-b.md"),
)
cells("taxsim-no-tax-exempt-interest-input",
      both("000", L1, "taxsim", -568.99) + both("122", L1, "taxsim", -128.49),
      "trace run: Tax-Calculator with e00400 0 gives TAXSIM's taxable benefits")

cause(
    cause_id="taxsim-no-blindness-input",
    kind="model-no-provision",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="The board states that 122's filer is blind; TAXSIM has no input for blindness, so its standard deduction lacks the additional amount. In 2025 TAXSIM itemizes instead, which narrows the gap.",
    law="26 U.S.C. 63(f)(2)(A) (additional standard deduction for a blind taxpayer); Rev. Proc. 2025-32 (2026 amount)",
    law_figure="$2,050 (single, 2026); $2,000 (2025)",
    who_is_right="policyengine-us and Tax-Calculator.",
    existing_report="",
    evidence=f"{T}trace-taxsim-b.md (122: Tax-Calculator with blind_head 0 moves by the same amount in each year)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-b.md"),
)
cells("taxsim-no-blindness-input", both("122", L1, "taxsim", 246.00, 181.18),
      "trace run: Tax-Calculator with blind_head 0")

cause(
    cause_id="taxsim-no-savers-credit",
    kind="model-no-provision",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=f"{L1};{L2}",
    summary="TAXSIM's test build has no input for the retirement savings contributions credit, so its tax omits the credit. In 119 the missing credit also leaves more tax for the child tax credit to absorb, so less of the child credit is refundable. Tax-Calculator's credit here is this repo's figure (keycheck/statute.py), not Tax-Calculator's own.",
    law="26 U.S.C. 25B(a)-(d); IRS Notice 2025-67 (2026 AGI limits)",
    law_figure="10% of up to $2,000 a person at AGI $26,250 to $40,250 (single) or $39,375 to $60,375 (head of household) in 2026",
    who_is_right="policyengine-us and Tax-Calculator. In 091 the credit also turns on full-time student status (25B(c)(2)(B)), which the board does not state; the prompt rule makes an unstated status false, so the credit stands. policyengine-us gives no credit when the head is a full-time student (results/repro/board_experiments.txt).",
    existing_report="",
    evidence=f"{T}trace-taxsim-a.md (070); {T}trace-taxsim-b.md (091, 119: Tax-Calculator with e07240 0); results/repro/board_experiments.txt (091 with the head a full-time student: 1,470.00 in place of 1,350.00)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-a.md, {T}trace-taxsim-b.md"),
)
cells("taxsim-no-savers-credit",
      both("070", L1, "taxsim", 192.40) + both("091", L1, "taxsim", 120.00) + both("119", L2, "taxsim", -200.00),
      "trace run: Tax-Calculator with e07240 0 gives TAXSIM's answer")

cause(
    cause_id="taxsim-2026-child-care-credit-old-rates",
    kind="model-law-departure",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="2026",
    quantities=f"{L1};{L2}",
    summary="For 2026 TAXSIM's test build computes the child and dependent care credit on the schedule in force before 2026 (20% at these incomes), not the amended one. In 119 the smaller credit leaves more tax for the child tax credit to absorb, so less of the child credit is refundable.",
    law="26 U.S.C. 21(a)(2) as amended by Pub. L. 119-21 sec. 70405 (taxable years after 2025)",
    law_figure="50%, reduced 1 point per $2,000 of AGI above $15,000 to 35%, then 1 point per $2,000 ($4,000 joint) above $75,000 ($150,000 joint) to 20%: 32% of $6,000 for 099, 35% of $1,560 for 119",
    who_is_right="policyengine-us and Tax-Calculator.",
    existing_report="",
    evidence=f"{T}trace-taxsim-b.md (099, 119); evidence/taxsim.md (probe P5.2: joint AGI 160,000 gives 1,200 against the law's 1,920)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-b.md"),
)
cells("taxsim-2026-child-care-credit-old-rates",
      [("099", L1, "2026", "taxsim", 720.00), ("119", L2, "2026", "taxsim", -234.00)],
      "trace arithmetic and probe: TAXSIM's credit 20% against the law's 32% (099) or 35% (119); Tax-Calculator ladder for 119")

cause(
    cause_id="taxsim-refundable-child-credit-ignores-child-care-credit",
    kind="model-law-departure",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=L2,
    summary="TAXSIM's refundable child tax credit equals the child credit less the tax before any credit, as if the child care credit had used none of the tax. The law refunds the child credit left over after the child care credit and the other nonrefundable credits take their share.",
    law="26 U.S.C. 24(d)(1) (refundable part limited by the credit left after the section 26(a) limit)",
    law_figure="2026: 4,400 - (3,056.23 - 546 - 200) = 2,089.77 refundable for 119",
    who_is_right="policyengine-us and Tax-Calculator.",
    existing_report="https://github.com/PolicyEngine/policyengine-taxsim/issues/1483",
    evidence=f"{T}trace-taxsim-b.md (119: TAXSIM's refundable credit does not move when child care falls to 0; Tax-Calculator ladder); evidence/taxsim.md (probes P3.7, P5.3)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-b.md"),
)
cells("taxsim-refundable-child-credit-ignores-child-care-credit", both("119", L2, "taxsim", -312.00),
      "trace run: Tax-Calculator ladder, and TAXSIM with childcare 0 leaves actc unchanged")

cause(
    cause_id="taxsim-three-child-refundable-credit-alternative",
    kind="model-law-departure",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=L2,
    summary="For a family with three or more children the law also allows a refundable child credit equal to the family's social security taxes (half of any self-employment tax) less the earned income credit. TAXSIM's test build counts the whole self-employment tax and does not subtract the earned income credit, so it refunds more than the 15% formula gives.",
    law="26 U.S.C. 24(d)(1)(B)(ii) and 24(d)(2)(A) (social security taxes: employee taxes under 3101 plus 50% of the 1401 tax); 24(h)(6)",
    law_figure="15% x (27,880.57 - 2,500) = 3,807.09 for 109; the alternative, 0.5 x 4,238.86 - 8,231, falls below 0",
    who_is_right="policyengine-us and Tax-Calculator.",
    existing_report="",
    evidence=f"{T}trace-taxsim-b.md (109); probes/taxsim/actc_3kids_alt.in.csv and actc_3kids_alt.cd2026110117.out.csv (ids 1, 4, 11, 12)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-b.md"),
)
cells("taxsim-three-child-refundable-credit-alternative", both("109", L2, "taxsim", 431.77),
      "trace probe: TAXSIM's actc equals its tfica (4,238.86) against the law's 3,807.09")

cause(
    cause_id="taxsim-2026-salt-cap-40000",
    kind="model-law-departure",
    answerer="taxsim",
    release_or_build="taxsimtest cd2026110117",
    fixed_in="",
    law_years="2026",
    quantities=L1,
    summary="TAXSIM's test build caps the 2026 state and local tax deduction at 2025's $40,000, not the law's $40,400, so an itemizer above the cap deducts $400 less.",
    law="26 U.S.C. 164(b)(7)(A)(ii) and (B)",
    law_figure="$40,400 for 2026, reduced by 30% of modified AGI above $505,000 (not below $10,000)",
    who_is_right="policyengine-us and Tax-Calculator.",
    existing_report="",
    evidence=f"{T}trace-taxsim-a.md (078); probes/taxsim/trace_a_078_saltcap.in.csv and trace_a_078_saltcap.cd2026110117.out.csv (opt1 8, opt1v 40400 gives 24,164.46)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-a.md"),
)
cells("taxsim-2026-salt-cap-40000", [("078", L1, "2026", "taxsim", 96.00)],
      "trace probe: TAXSIM with the cap set to 40,400 per record gives the others' answer")

cause(
    cause_id="taxsim-no-early-distribution-tax-input",
    kind="model-no-provision",
    answerer="taxsim",
    release_or_build=f"taxsimtest cd2026110117; {V} lists the tax in unexpressed (keycheck/map_taxsim.py:401)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="TAXSIM has no input for the additional tax on early distributions, so its line leaves out the 10% the maps compute for 023 (800.00), 064 (2,000.00) and 074 (38.40). The map names the amount in a note on each answer.",
    law="26 U.S.C. 72(t)(1) (the tax under chapter 1 rises by 10% of the includible amount); 26(b)(2)(C)",
    law_figure="10% of 8,000 (023), 20,000 (064) and 384 (074)",
    who_is_right="Tax-Calculator on 064, where the law decides; on 023 and 074 the answer turns on 72(m)(7) disability, as pe-early-distribution-tax-not-computed sets out. Either way TAXSIM's line cannot hold the tax.",
    existing_report="",
    evidence=f"keycheck/map_taxsim.py:45-47 (NBER's input list for the test build has no field for it) and :401 (the note); {B2} (item 4: TAXSIM note only); results/answers.csv (the note on 023, 064 and 074)",
    households_shared="",
    opened_by=OB2.format(f"{B2}"),
)
cells("taxsim-no-early-distribution-tax-input",
      both("023", L1, "taxsim", -800.00) + both("064", L1, "taxsim", -2000.00) + both("074", L1, "taxsim", -38.40),
      "map note: the statute's amount at TAXSIM's AGI, which the line leaves out")

# ---------------------------------------------------------------- this repo's input map
cause(
    cause_id="map-ira-deduction-in-nonprop-cuts-eitc",
    kind="map-limit",
    answerer="taxsim",
    release_or_build=f"{V} (keycheck/map_taxsim.py: adjustments and the self-employed health insurance and pension deductions go to negative nonprop) on taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=L2,
    summary="TAXSIM has no input for an adjustment that lowers AGI alone, so the map enters each such adjustment as negative nonprop, which this build also subtracts from earned income: for the earned income credit and for the refundable child credit, which uses the same earned income. On 100 the IRA deduction (180.32) costs 40% of itself in the earned income credit's phase-in range. On 038 the self-employed health insurance deduction (100.00, 162(l)) costs 15% of itself in the refundable child credit (TAXSIM's actc falls from 2,909.35 to 2,894.35); its earned income credit does not move.",
    law="26 U.S.C. 32(c)(2)(A) (earned income: wages and net earnings from self-employment; neither the 219 deduction nor the 162(l) deduction reduces it, 162(l)(4)); 24(d)(1)(B)(i) (the refundable child credit takes 15% of the earned income above $2,500, earned income as section 32 defines it)",
    law_figure="40% x 2,055.72 = 822.29 for 100; 15% x 100.00 = 15.00 for 038",
    who_is_right="policyengine-us and Tax-Calculator. Entering the IRA deduction where it moves only AGI (a negative short-term gain) gives TAXSIM 822.29 on 100. On 038 neither policyengine-us (which allows no 162(l) deduction there: it needs is_self_employed) nor Tax-Calculator (which deducts the 100.00) moves its refundable credits.",
    existing_report="",
    evidence=f"{T}trace-taxsim-b.md (100: TAXSIM with nonprop 0 and stcg -180.32 gives 822.29); {T}fix-maps.md (kept as a noted limit); {B2} (item 9 and 'For the causes unit' 6: 038's actc 2,909.35 -> 2,894.35); keycheck/map_taxsim.py:297 and :415 (the notes on 038 and on adjustments)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-b.md, {B2}"),
)
cells("map-ira-deduction-in-nonprop-cuts-eitc",
      both("100", L2, "taxsim", -72.13) + both("038", L2, "taxsim", -15.00),
      "trace run: TAXSIM with the deduction moved out of nonprop gives 822.29 (100); builder rerun: 038's actc falls by 15% of the 100.00 entered as nonprop")

# ---------------------------------------------------------------- PolicyEngine
cause(
    cause_id="pe-other-dependent-credit-without-dependency-tests",
    kind="model-law-departure",
    answerer="policyengine-us;policybench-key",
    release_or_build="policyengine-us 2.60.0 and 2.116.15 (ctc_adult_individual_maximum.py identical; is_tax_unit_dependent.py differs only in its docstring)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="policyengine-us pays the $500 credit for other dependents for every member of the tax unit who is not the head or spouse, testing only identification. It does not apply the qualifying-relative gross income test or the disability rule that lets an adult be a qualifying child. 093's dependent1 is 27 and earns $45,000 of wages, and the board states that dependent1 is disabled; the engine pays the credit, and pays the same $500 when is_disabled is false.",
    law="26 U.S.C. 24(h)(4) ($500 for each dependent as defined in 152 other than a qualifying child); 152(d)(1)(B) (a qualifying relative's gross income must fall below the exemption amount); 152(c)(3)(B) and 22(e)(3) (a permanently and totally disabled child meets the age test; 22(e)(3) requires inability to engage in any substantial gainful activity)",
    law_figure="$500; exemption amount $5,300 (2026, Rev. Proc. 2025-32 sec. 4.23) and $5,200 (2025, Rev. Proc. 2024-40 sec. 2.24)",
    who_is_right="Tax-Calculator and TAXSIM, on this entry's position. With $45,000 of wages dependent1 fails the gross income test, and a year of wages at that level is work that 22(e)(3) disability rules out (an inference: this entry did not consult the regulations on substantial gainful activity), so the stated 'is disabled' does not make dependent1 a qualifying child; dependent1 is not the filer's dependent, and no $500 credit follows.",
    existing_report="",
    evidence=f"{T}trace-pe-b.md (093); results/repro/board_experiments.txt (093 on 2.60.0 and 2.116.15: is_disabled false still pays 500); results/repro/repro_pe_2.60.0.txt and repro_pe_2.116.15.txt (credit for other dependents with no gross income test); {PE}variables/gov/irs/credits/ctc/maximum/individual/ctc_adult_individual_maximum.py:13,21-40; {PE}variables/household/demographic/tax_unit/is_tax_unit_dependent.py:10-13",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-b.md"),
)
cells("pe-other-dependent-credit-without-dependency-tests",
      [("093", L1, "2026", "policyengine-us", -500.00), ("093", L1, "2026", "policybench-key", -500.00),
       ("093", L1, "2025", "policyengine-us", -500.00)],
      "trace runs: Tax-Calculator with XTOT 3 and TAXSIM with depx 1 give policyengine-us's answer")

cause(
    cause_id="pe-divorce-year-default",
    kind="pe-default-unstated-fact",
    answerer="policyengine-us;policybench-key",
    release_or_build="policyengine-us 2.60.0 and 2.116.15 (divorce_year.py identical); the key's frozen 1.755.4 value",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="020 pays $5,708.82 of alimony; the board does not state when the parties executed the divorce or separation instrument. policyengine-us fills the date with its default divorce year, 2010, and deducts the alimony; Tax-Calculator and TAXSIM treat every instrument as executed after 2018, so neither deducts it.",
    law="26 U.S.C. 215, repealed by Pub. L. 115-97 sec. 11051 for divorce or separation instruments executed after December 31, 2018 (earlier instruments keep the deduction)",
    law_figure="",
    who_is_right="No answer is right until the board states the instrument's date. The deduction needs a fact (an instrument executed before 2019); the prompt rule makes an unstated fact false, so the rule points to no deduction: Tax-Calculator's and TAXSIM's answers. policyengine-us with divorce_year 2019 gives 70,332.82, Tax-Calculator's answer.",
    existing_report="",
    evidence=f"{T}trace-pe-a.md (020: Tax-Calculator deducting alimony gives policyengine-us's answer); results/repro/board_experiments_2.txt (divorce_year 2019); {PE}variables/household/demographic/person/divorce_year.py:9; {PE}variables/gov/irs/income/taxable_income/adjusted_gross_income/above_the_line_deductions/alimony_expense_ald_person.py:21-24",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-a.md"),
)
cells("pe-divorce-year-default",
      [("020", L1, "2026", "policyengine-us", -1998.09), ("020", L1, "2026", "policybench-key", -1998.09),
       ("020", L1, "2025", "policyengine-us", -1998.09)],
      "engine run (results/repro/board_experiments_2.txt): divorce_year 2019 gives 70,332.82; the key's 1.755.4 value carries the same deduction (the board's recheck attributes its whole move to the sales tax table)")

cause(
    cause_id="pe-medicare-part-b-premium-default",
    kind="pe-default-unstated-fact",
    answerer="policyengine-us;policybench-key",
    release_or_build="policyengine-us 2.60.0 and 2.116.15 (both give 11,265.27 without the take-up)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="114's filer is 69 and itemizes medical expenses; the board states no Medicare enrollment or premium. policyengine-us assumes an eligible person takes up Medicare and adds twelve months of the standard Part B premium (2,434.80 in 2026, 2,220.00 in 2025) to medical expenses.",
    law="26 U.S.C. 213(a) (medical care paid above 7.5% of AGI) and 213(d)(1)(D) (Part B premiums paid are medical care)",
    law_figure="",
    who_is_right="No answer is right until the board states Medicare enrollment and the premium paid. The prompt says not to infer unlisted health coverage and to treat an unlisted amount as 0, so the rule points to no premium: Tax-Calculator's and TAXSIM's answers. The prompt also says to assume program take-up when required; this entry reads the specific instruction on health coverage as governing a premium the household would have to pay. policyengine-us with takes_up_medicare_if_eligible false gives 11,265.27 on both releases.",
    existing_report="",
    evidence=f"{T}trace-pe-b.md (114: Tax-Calculator with the premium added gives policyengine-us's answer); results/repro/board_experiments.txt (114, 2.60.0 and 2.116.15); {PE}variables/household/expense/health/medical_expense_health_insurance_premiums.py:25-28; {PE}variables/gov/hhs/medicare/takes_up_medicare_if_eligible.py:9",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-b.md"),
)
cells("pe-medicare-part-b-premium-default",
      [("114", L1, "2026", "policyengine-us", -535.66), ("114", L1, "2026", "policybench-key", -535.66),
       ("114", L1, "2025", "policyengine-us", -488.40)],
      "engine run (results/repro/board_experiments.txt): no Medicare take-up gives 11,265.27")

cause(
    cause_id="pe-net-investment-income-leaves-out-farm-rent",
    kind="model-law-departure",
    answerer="policyengine-us;policybench-key",
    release_or_build="policyengine-us 2.60.0 (and the key's frozen 1.755.4 value)",
    fixed_in="policyengine-us 2.116.15 (farm_rent_income in gov.irs.investment.income.sources)",
    law_years="both",
    quantities=L1,
    summary="policyengine-us 2.60.0 leaves Form 4835 farm rent out of net investment income, so 120's farm rent loss (2,446.59) does not offset its rent and interest, and the net investment income tax comes to 163.40 (3.8% of 4,300) where adding farm rent to the sources gives 70.43. The amount here is that engine measurement, taken with no 469 limit; the limit's own effect, including its 16.97 of net investment income tax, sits in pe-no-passive-activity-loss-limit. Under the maps, which suspend the net passive loss, the farm rent that 469 allows (-2,000.00) offsets the rent (2,000.00), net investment income is the interest, 2,300.00, and the tax 87.40.",
    law="26 U.S.C. 1411(c)(1)(A)(i) (gross income from rents) and (c)(1)(B) (deductions properly allocable to it)",
    law_figure="with no 469 limit, 3.8% of net investment income 1,853.41 = 70.43; with the loss suspended, 3.8% of 2,300.00 = 87.40",
    who_is_right="Tax-Calculator, TAXSIM and policyengine-us 2.116.15 on the sources of net investment income. Adding farm_rent_income to 2.60.0's sources gives 40,330.21, Tax-Calculator's and TAXSIM's answer before the maps applied 469 (keycheck 2026-11-10.2); the rest of the gap at 2026-11-11.1 belongs to pe-no-passive-activity-loss-limit.",
    existing_report="https://github.com/PolicyEngine/policyengine-us/issues/10075",
    evidence=f"{T}trace-pe-b.md (120); results/repro/board_experiment_120_rerun.txt; {PE}parameters/gov/irs/investment/income/sources.yaml:8-27 (2.60.0, no farm_rent_income) and :23 at 2.116.15; {META} (revisions[17]: the 1.755.4-to-2.15.17 move for 120 is the IRA and #9122 alone, so the frozen value carries the same omission: inference); results/dossiers/scenario_120.json (Tax-Calculator out_niit 87.40 at {V})",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-b.md"),
)
cells("pe-net-investment-income-leaves-out-farm-rent",
      [("120", L1, "2026", "policyengine-us", 92.97), ("120", L1, "2026", "policybench-key", 92.97),
       ("120", L1, "2025", "policyengine-us", 92.97)],
      "engine run (results/repro/board_experiment_120_rerun.txt): farm rent in net investment income gives 40,330.21")

cause(
    cause_id="pe-scholarship-not-income",
    kind="pe-default-unstated-fact",
    answerer="policyengine-us;policybench-key",
    release_or_build=f"policyengine-us 2.60.0 and 2.116.15 (experiment R1 gives the same result on both); the key's frozen value, which equals the 2.60.0 rerun on both households; Tax-Calculator and TAXSIM count the amount through READINGS educational_assistance ({V})",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="030 and 068 list educational assistance (5,000 and 73,000), which policyengine-us documents as 'Scholarships, grants, and other educational assistance.' policyengine-us leaves it out of gross income whatever else the household states (experiment R1: 5,000 beside 13,000 of wages leaves gross income at 13,000), as if each recipient were a degree candidate who spent it all on qualified tuition and related expenses. The maps count it in full, since the board states neither condition: Tax-Calculator through e01200 and TAXSIM through pensions, so it raises AGI and not earned income. On 030 AGI rises from 13,000 to 18,000 and the tax from 0 to 190.00 (2026) or 225.00 (2025); on 068 the tax rises by 12,818.36 (2026) or 13,045.86 (2025). The earlier entry shared-scholarship-not-income said 030 owed 0 either way; the TAXSIM comparer found that wrong, and these runs agree.",
    law="26 U.S.C. 117(a) and (b) (exclude a qualified scholarship only for a degree candidate and only to the extent it pays qualified tuition and related expenses); 61(a); 127 (excludes educational assistance only under an employer's program)",
    law_figure="030: taxable income 1,900 at 10% = 190.00 (2026), 2,250 at 10% = 225.00 (2025)",
    who_is_right=f"Tax-Calculator and TAXSIM, under the prompt rule: 190.00 for 030 and 14,728.38 for 068. Each exclusion needs a fact the board does not state (degree candidacy and use for tuition under 117, an employer's program under 127), and the rule makes an unstated fact false, so the whole amount is income. The blind second maps split: the second TAXSIM map counts it and its comparer ruled the first map's exclusion an error ({SM_TS}); the second Tax-Calculator map leaves it out, and its comparer lists that as a reading both maps shared without arguing it ({SM_TC}). This entry reads policyengine-us's documentation of the input (scholarships and grants, not the excluded part of them) as the stated fact, so the engine applies the exclusion on conditions the household does not state.",
    existing_report="",
    evidence=f"{RX26} and {RX116} (R1); {PE}variables/household/income/person/misc/educational_assistance.py:8 (documentation); {PE}parameters/gov/irs/gross_income/sources.yaml:3-47 (no educational_assistance); {B2} (item 1; 'For the causes unit' 2); {SM_TS} (030 +190.00, 068 +12,818.36, first_map_errs); {SM_TC} (shared readings); {U}:180 READINGS educational_assistance",
    households_shared="",
    opened_by=OB2.format(f"{B2}, {SM_TS}, {RX26}"),
)
cells("pe-scholarship-not-income",
      [("030", L1, "2026", "policybench-key", -190.00), ("030", L1, "2026", "policyengine-us", -190.00),
       ("030", L1, "2025", "policyengine-us", -225.00),
       ("068", L1, "2026", "policybench-key", -12818.36), ("068", L1, "2026", "policyengine-us", -12818.36),
       ("068", L1, "2025", "policyengine-us", -13045.86)],
      "map runs: Tax-Calculator and TAXSIM with the amount counted give 190.00 / 225.00 (030) and 14,728.38 / 15,007.38 (068); engine experiment R1 leaves it out")

cause(
    cause_id="pe-survivor-benefits-not-income",
    kind="pe-default-unstated-fact",
    answerer="policyengine-us;policybench-key",
    release_or_build=f"policyengine-us 2.60.0 and 2.116.15 (experiment R2 gives the same result on both; #10181 wired military survivor benefit plan payments into gross income and left survivor_benefits out); the key's frozen value; Tax-Calculator and TAXSIM count the amount through READINGS survivor_benefits ({V})",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="062 lists 28,800 of survivor benefits other than Social Security, and 108 lists 10,392 (policyengine-us documents the input as 'Survivor benefits other than Social Security survivor benefits'). policyengine-us leaves them out of gross income whatever else the household states (experiment R2), as if an exclusion applied. The maps count them as a taxable pension, since the investment in the contract is an unlisted amount and every exclusion needs an unstated fact. 062's AGI rises from 17,322.91 to 63,245.14 (the taxable part of its Social Security rises with it) and its tax from 0 to 4,328.39; 108 owes 0 either way (taxable income stays 0, and at 85 it has no earned income credit).",
    law="26 U.S.C. 61(a) and 72 (a survivor annuity is gross income); 101(a) (life insurance proceeds paid by reason of death), 104(a)(1) (workers' compensation) and 38 U.S.C. 5301 (veterans' benefits) exclude only on facts the board does not state",
    law_figure="",
    who_is_right=f"Tax-Calculator and TAXSIM, under the prompt rule: 4,328.39 for 062, the board's own alternative for this excluded output. Both blind second maps count the benefits too, and both comparers ruled the first map's earlier exclusion an error ({SM_TC}, {SM_TS}).",
    existing_report="",
    evidence=f"{RX26} and {RX116} (R2); {PE}variables/household/income/person/general/survivor_benefits.py:8 (documentation); {PE}parameters/gov/irs/gross_income/sources.yaml:3-47 (no survivor_benefits; military survivor payments enter at :46-47); {EXCL} (062: reference_depends_on_unlisted_input, alternative 4,328.39); {B2} (item 2); {U}:80 READINGS survivor_benefits",
    households_shared="",
    opened_by=OB2.format(f"{B2}, {SM_TC}, {SM_TS}, {RX26}"),
)
cells("pe-survivor-benefits-not-income",
      [("062", L1, "2026", "policybench-key", -4328.39), ("062", L1, "2026", "policyengine-us", -4328.39),
       ("062", L1, "2025", "policyengine-us", -4385.89)],
      "map runs: Tax-Calculator and TAXSIM with the benefits as a taxable pension give 4,328.39 (2026) and 4,385.89 (2025); engine experiment R2 leaves them out")

cause(
    cause_id="pe-no-passive-activity-loss-limit",
    kind="model-no-provision",
    answerer="policyengine-us;policybench-key",
    release_or_build="policyengine-us 2.60.0 and 2.116.15 (no 469 variable; experiment R4 deducts a net rental loss at wages of 199,000 on both; issue 5274 asked for the limit, and its maintainers marked it not planned on 2026-07-26); the key's frozen value",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="policyengine-us applies no passive activity loss limit. 120 states rent of 2,000 and a farm rent loss of 2,446.59, both rentals, so passive; 469 suspends their net loss of 446.59 at 120's AGI, and the maps add it back (469 allows 2,000 of the farm rent loss, the passive income it can offset). That raises taxable income by 448.82 (24%, 107.72, with 2.23 more from the 0.5% charitable floor) and the net investment income tax by 16.97 in 2026; in 2025, 446.59 at 32% (142.91) and the same 16.97. The maps suspend the losses of 004 (a partnership loss of 135) and 098 (a farm rent loss of 11,100) too, and no line moves. The maps also read partnership income beyond a partner's self-employment earnings as passive, so as net investment income, where policyengine-us counts only the separate input passive_partnership_s_corp_income: on the board that touches 064, 089 and 114 and moves no line (none reaches the 1411 threshold or claims an earned income credit).",
    law="26 U.S.C. 469(a) (disallows a passive activity loss) and (b) (carries it to the next year); 469(c)(2) (a rental activity is passive whatever the participation); 469(c)(7) (real estate professionals); 469(i)(3)(A) (the $25,000 allowance falls by 50% of modified AGI above $100,000, so to 0 at $150,000)",
    law_figure="allowance 0 at 120's modified AGI; 446.59 suspended",
    who_is_right=f"Tax-Calculator and TAXSIM, on the law (their 40,454.89 also counts the state tax refund the key leaves out; the key less this entry's amount is 40,146.51). A rental is passive by statute; only real estate professional status, which turns on hours the board does not state and the prompt rule makes false, would take it out, and the 469(i) allowance is gone at this AGI whatever the participation. Both blind second maps suspend the loss, and both comparers ruled the first map's earlier deduction an error ({SM_TC}, {SM_TS}). The board excludes 120; its record puts the limit's effect at +24.75 on 2.15.17, a gap no entry here examines.",
    existing_report="https://github.com/PolicyEngine/policyengine-us/issues/5274 (maintainers marked it not planned on 2026-07-26)",
    evidence=f"{RX26} and {RX116} (R4); {B2} (item 3; 'For the causes unit' 4, split (a), which leaves pe-net-investment-income-leaves-out-farm-rent at its engine measurement); {META} (scenario_120: 'the engine's missing 469 limit'); second_map/taxcalc/sources/usc26_469.txt:24-25; {U}:129 READINGS passive_activity; keycheck/statute.py passive_activity_allowed",
    households_shared="",
    opened_by=OB2.format(f"{B2}, {SM_TC}, {SM_TS}, {RX26}"),
)
cells("pe-no-passive-activity-loss-limit",
      [("120", L1, "2026", "policybench-key", -124.69), ("120", L1, "2026", "policyengine-us", -124.69),
       ("120", L1, "2025", "policyengine-us", -159.88)],
      "map runs: Tax-Calculator and TAXSIM rise by 124.69 (2026) and 159.88 (2025) when the maps suspend the loss; a Tax-Calculator counterfactual run with the refund out and the board's state and local tax gives 40,060.04, and 39,935.35 with the loss allowed again")

cause(
    cause_id="pe-early-distribution-tax-not-computed",
    kind="model-no-provision",
    answerer="policyengine-us;policybench-key",
    release_or_build=f"policyengine-us 2.60.0 and 2.116.15 (qualified_retirement_penalty is an input with no formula; experiment R3: 0 unless stated, and the line adds it when stated); the key's frozen value; Tax-Calculator gets the tax as e09900 through READINGS retirement_penalty ({V})",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="policyengine-us computes no additional tax on early distributions: income_tax_before_refundable_credits adds qualified_retirement_penalty, an input with no formula, and the board states none. The maps compute 10% of each filer's taxable IRA, 401(k), 403(b) and SEP distributions before 59 1/2, less the medical exception, and none for a filer the maps read as disabled under 72(m)(7) (stated disabled with no earnings). Three households move: 064's head (48) takes 20,000 from a 401(k), with medical expenses under the floor (2,000.00); 023's head (28, stated disabled, with wages of 17,442.65) takes 8,000 from a 403(b) (800.00); 074's head (54, with Social Security disability benefits and no stated disability) takes 384 from an IRA (38.40).",
    law="26 U.S.C. 72(t)(1) (the tax under chapter 1 rises by 10% of the includible amount received from a qualified retirement plan); 72(t)(2)(A)(iii) and 72(m)(7) (no tax on a distribution attributable to disability: inability to engage in any substantial gainful activity because of an impairment expected to result in death or to be of long-continued and indefinite duration); 72(t)(2)(B) (medical expenses deductible under 213); 26(b)(2)(C) (nonrefundable credits do not offset the tax)",
    law_figure="10% of 20,000 = 2,000.00 (064); 10% of 8,000 = 800.00 (023); 10% of 384 = 38.40 (074)",
    who_is_right=f"For 064, Tax-Calculator: 6,441.45, and the key would be 6,441.46. The line is federal individual income tax, and 72(t)(1) raises the tax under chapter 1, the income tax (26(b)(2)(C) lists it among chapter 1 taxes); policyengine-us's own line adds the input when a household states it; and no 72(t)(2) exception rests on a stated fact. The blind second Tax-Calculator map gives 6,441.45 too, and its comparer calls the key's 064 answer a departure from the law ({SM_TC}). For 023 and 074 the answer turns on 72(m)(7) disability, which the board does not define: the board states that 023's head is disabled and earns 1,453.55 a month, under the 2026 monthly amount the Social Security Administration treats as substantial gainful activity for a non-blind person ($1,690), and 074's head draws Social Security disability benefits, whose test (42 U.S.C. 423(d)(1)(A): death or at least 12 months) differs from 72(m)(7)'s 'long-continued and indefinite duration.' The maps tax both; the second Tax-Calculator map taxes neither (643.43 and 0.00). This entry takes no side on 023 and 074.",
    existing_report="",
    evidence=f"{RX26} and {RX116} (R3: 5,020 with the input 0, 7,020 with it stated as 2,000); {PE}variables/gov/irs/tax/federal_income/income_tax_before_refundable_credits.py:10,18-28; second_map/taxcalc/sources/usc26_72.txt:289 (72(m)(7)), :517 (72(t)(1)); {B2} (item 4); {SM_TC} (064 +2,000.00, first_map_errs); second_map/taxcalc/answers_2026.csv (023 643.43, 074 0.00, 064 6,441.45) and second_map/taxcalc/map.py:747-753 (a stated disability, or receipt of Social Security disability benefits, read as 72(m)(7) disability); {U}:152 READINGS retirement_penalty and :57 READINGS is_disabled; Federal Register document 2025-19763 (2026 substantial gainful activity amounts)",
    households_shared="",
    opened_by=OB2.format(f"{B2}, {SM_TC}, {RX26}"),
)
cells("pe-early-distribution-tax-not-computed",
      [(c, L1, t, a, v) for c, v in (("023", -800.00), ("064", -2000.00), ("074", -38.40))
       for t, a in (("2026", "policybench-key"), ("2026", "policyengine-us"), ("2025", "policyengine-us"))],
      "map runs: Tax-Calculator with the tax as e09900 rises by 800.00, 2,000.00 and 38.40 in both years; engine experiment R3 holds 0 unless the input is stated")

# ---------------------------------------------------------------- the committed key
cause(
    cause_id="key-ira-deducted-without-219g",
    kind="key-decided-value",
    answerer="policybench-key",
    release_or_build="the committed key: policyengine-us 1.755.4 values the board froze on 2026-09-22",
    fixed_in="the engine applies 219(g) by 2.38.6 (the board's recheck gives the corrected value; 2.60.0 has ira_active_participant.py and ira_219g_deductible_limit.py); the key keeps the frozen value",
    law_years="2026",
    quantities=L1,
    summary="The frozen 1.755.4 values deduct traditional IRA contributions with no active-participant phase-out. Each filer defers wages into a 401(k), so is an active participant, and modified AGI exceeds the range, so the law allows no IRA deduction.",
    law="26 U.S.C. 219(g) (active-participant phase-out; 219(g)(5)(A) active participant); IRS Notice 2025-67 (2026 ranges)",
    law_figure="no deduction above $149,000 (joint) or $91,000 (single) of modified AGI in 2026",
    who_is_right="policyengine-us 2.60.0, Tax-Calculator and TAXSIM. The board excludes these outputs and names the defect in its own records.",
    existing_report="",
    evidence=f"{T}trace-pe-a.md (005, 052: Tax-Calculator with the contribution deducted gives the key); {T}trace-pe-b.md (120); {EXCL} (root cause r02_ira_219g); {META} (revisions 17-20)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}trace-pe-b.md"),
)
cells("key-ira-deducted-without-219g",
      [("005", L1, "2026", "policybench-key", -692.44), ("052", L1, "2026", "policybench-key", -13.85),
       ("120", L1, "2026", "policybench-key", -6.50)],
      "board record: alternative value minus frozen value (005: 107,198.34 - 106,505.90; 052: 104,225.26 - 104,211.41; 120: 40,028.32 - 40,021.82)")

cause(
    cause_id="key-sales-tax-table-column-shift",
    kind="key-decided-value",
    answerer="policybench-key",
    release_or_build="the committed key: policyengine-us 1.755.4 value",
    fixed_in="policyengine-us #9616 (3f029abf5b, 2026-09-27), in 2.15.17 and later",
    law_years="2026",
    quantities=L1,
    summary="1.755.4's optional sales tax table held a neighbouring state's values (a column shift), so 020's frozen value deducts a different sales tax amount. The board's own recheck attributes the whole 278.02 to the corrected table. Tax-Calculator and TAXSIM take the corrected amount from the engine run.",
    law="26 U.S.C. 164(b)(5)(A) and (H) (election to deduct general sales taxes; amount under the IRS tables)",
    law_figure="",
    who_is_right="policyengine-us 2.60.0 (on the shared sales tax amount, which Tax-Calculator and TAXSIM also use). The 1.755.4 sales tax figure is not in the dossier; the size rests on the board's record and the 278.02 difference.",
    existing_report="https://github.com/PolicyEngine/policyengine-us/issues/9595",
    evidence=f"{T}trace-pe-a.md (020, reconciliation C); {META} (revisions[17], scenario_020: 'comes only from #9616')",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-a.md"),
)
cells("key-sales-tax-table-column-shift", [("020", L1, "2026", "policybench-key", -278.02)],
      "board record: 2.15.17 value 68,334.73 minus frozen value 68,056.71")

# ---------------------------------------------------------------- readings the models share
cause(
    cause_id="shared-state-tax-refund-counted-in-full",
    kind="shared-reading",
    answerer="policyengine-us;taxcalc;taxsim",
    release_or_build=f"policyengine-us 2.15.17 and later (policyengine-us#9422, which fixed issue #9122), and the key's values that the board froze on 2.15.17; Tax-Calculator and TAXSIM through READINGS salt_refund_income ({V})",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="A listed state or local tax refund counts in full as income in policyengine-us (which documents the input as the taxable refund on Schedule 1, line 1) and, through this repo's reading, in Tax-Calculator and TAXSIM. The key's frozen 1.755.4 values for 005 and 120 never counted the input, so those two cells move three answers and not the key; elsewhere every answer counts it.",
    law="26 U.S.C. 111(a) (a recovery is income only to the extent the earlier deduction reduced tax)",
    law_figure="",
    who_is_right="No answer is right until the board states the prior year's facts: whether the household itemized and deducted the refunded tax. The prompt rule makes that unstated fact false, so none of the refund is income (the board's own alternative reading). On that reading the key's frozen values for 005 and 120 hold the refund correctly, and 082's scored answer would fall by 14.85.",
    existing_report="",
    evidence=f"{BOARD}reference_audit/2026-09-28/fixes/latest_alt_salt_refund_no_prior_benefit.py:1-30; {META} (revisions[17]: 005 '+$1,327.26 move is #9122 alone', 120 '+$394.85 move is #9122 alone'); results/repro/board_experiments_2.txt (005 salt_refund_income 0: 107,198.34); counterfactual runs on the inputs in results/dossiers (Tax-Calculator 005 with e00700 0: 107,198.33; 082: 9,564.92; 033: 3,788.99; 078: 23,772.80; 117: 24,391.80, each the board record's alternative to the cent; TAXSIM 005 with pensions less the refund: 107,540.65, above the engine's 107,198.34 by the 170(p) deduction TAXSIM lacks; 120, Tax-Calculator with the refund out and the shared state and local tax lowered by the 113.77 the board records for the engine's Connecticut estimate: 40,060.04 at {V}, 39,935.35 with the passive loss allowed as before)",
    households_shared="scenario_033;scenario_074;scenario_078;scenario_082;scenario_088;scenario_117;scenario_005@2025;scenario_120@2025",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}trace-pe-b.md, {T}trace-taxsim-a.md") ,
)
cells("shared-state-tax-refund-counted-in-full",
      [("005", L1, "2026", "policyengine-us", 1327.24), ("005", L1, "2026", "taxcalc", 1327.25),
       ("005", L1, "2026", "taxsim", 1327.26),
       ("120", L1, "2026", "policyengine-us", 394.86), ("120", L1, "2026", "taxcalc", 394.86),
       ("120", L1, "2026", "taxsim", 394.86)],
      "runs: engine 005 with salt_refund_income 0 (results/repro/board_experiments_2.txt); engine 120 from the board record (2.15.17 with the IRA fix gives 40,423.18, the 2.60.0 rerun; the refund alone moves 1.755.4 to 2.15.17); Tax-Calculator and TAXSIM counterfactual runs with the refund out of income")

cause(
    cause_id="shared-disability-benefits-taxable",
    kind="shared-reading",
    answerer="policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 and 2.116.15 (taxable_disability_benefits in gross income; tax_exempt_disability_benefits defaults to 0); Tax-Calculator and TAXSIM through READINGS disability_benefits",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="policyengine-us, Tax-Calculator and TAXSIM tax stated disability benefits in full. The key's frozen 1.755.4 values for 002, 107 and 121 leave them out, so those three cells move three answers and not the key.",
    law="26 U.S.C. 104(a)(3) (amounts received through accident or health insurance excluded) and 105(a) (included to the extent attributable to employer contributions not included in the employee's income, or paid by the employer)",
    law_figure="",
    who_is_right="No answer is right until the board states who paid for the coverage. The law includes the benefits only on a fact (employer contributions or payment); the prompt rule makes that unstated fact false, so 104(a)(3) excludes the benefits: the key's frozen 0.00. The board excludes all three outputs (reference_depends_on_unlisted_input). In 057 and 084 the households owe 0 either way; 067's benefits are a dependent's own.",
    existing_report="",
    evidence=f"{T}trace-pe-a.md (002: Tax-Calculator without the benefits gives 0.00); {T}trace-pe-b.md (107, 121: Tax-Calculator and TAXSIM without them give 0.00); a TAXSIM counterfactual run on 002 without them: 0.00; {PE}variables/household/income/person/general/taxable_disability_benefits.py:21-24; {EXCL}",
    households_shared="scenario_057;scenario_067;scenario_084;scenario_002@2025;scenario_107@2025;scenario_121@2025",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}trace-pe-b.md"),
)
cells("shared-disability-benefits-taxable",
      [(c, L1, "2026", a, v) for c, v in (("002", 1890.30), ("107", 211.23), ("121", 875.34))
       for a in ("policyengine-us", "taxcalc", "taxsim")],
      "runs: Tax-Calculator and TAXSIM without the benefits give the key's 0.00 (traces; TAXSIM 002 counterfactual run)")

cause(
    cause_id="shared-financial-assistance-gift",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0; keycheck READINGS financial_assistance",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="Six households list financial assistance from friends or relatives outside the household; every answer leaves it out of income.",
    law="26 U.S.C. 102(a) (gifts excluded from gross income)",
    law_figure="",
    who_is_right="All four: policyengine-us documents the input as cash assistance from friends or relatives outside the household, which is a gift. No answer moves.",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F6); keycheck/unit.py READINGS financial_assistance",
    households_shared="scenario_029;scenario_030;scenario_056;scenario_080;scenario_090;scenario_112",
    opened_by=OB.format(f"{T}verify-unit-statute.md"),
)

cause(
    cause_id="shared-disabled-member-qualifying-child",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build=f"{V} READINGS is_disabled; policyengine-us 2.60.0 claims the member by another route (pe-other-dependent-credit-without-dependency-tests)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="The board states that 067's dependent1 (23) and 064's dependent1 (27) are disabled, and neither has earnings. The maps read each as permanently and totally disabled, so a qualifying child at any age and a dependent for the $500 credit. policyengine-us claims both as dependents without testing disability.",
    law="26 U.S.C. 152(c)(3)(B) and 22(e)(3); 152(d)(1)(B); 24(h)(4)",
    law_figure="$500 credit for other dependents",
    who_is_right="All four on 067's scored answer (5,616.24), by either reading: as a disabled qualifying child, or, if 'is disabled' falls short of 22(e)(3), as a qualifying relative, since under the prompt rule the member's disability benefits are not income (shared-disability-benefits-taxable), which leaves the member's gross income at 0, below the exemption amount. 064 is a qualifying relative either way; the reading moves only its earned-income-credit child count, and no credit arises at its income.",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F1); {T}trace-pe-a.md (067); {T}fix-maps.md (reading 1, 067 moved to all_agree)",
    households_shared="scenario_064;scenario_067",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}verify-unit-statute.md"),
)

cause(
    cause_id="shared-net-investment-income-tax-in-line",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us income_tax_before_refundable_credits; this repo's line definitions (scripts/run_taxcalc.py, scripts/run_taxsim.py docstrings)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="Every answer here includes the 3.8% tax on net investment income in the line 'federal tax before refundable credits'.",
    law="26 U.S.C. 1411(a)(1) (the net investment income tax)",
    law_figure="",
    who_is_right="The output's text does not decide it: it reads 'federal individual income tax after nonrefundable credits and before refundable credits' and does not say whether the 1411 tax is in it. The board excludes 020 for this reason (r25) and names it on 005, 052 and 120; no scored output in the board's 100 has a net investment income tax.",
    existing_report="",
    evidence=f"{BOARD}policybench/benchmark_specs.json (output prompt); {META} (scenario_020: 'depends on whether federal income tax before refundable credits includes the net investment income tax'); results/dossiers (net_investment_income_tax above 0 only for 005, 020, 052, 120)",
    households_shared="scenario_005;scenario_020;scenario_052;scenario_120",
    opened_by=OB.format(f"{T}trace-pe-a.md"),
)

cause(
    cause_id="shared-state-income-tax-withholding-estimate",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 state_withheld_income_tax (the board's convention), passed to Tax-Calculator (e18400) and TAXSIM (proptax) from results/shared",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="The board states no state income tax withheld or paid. Every answer here uses the engine's AGI-formula estimate of state income tax withheld as the state income tax part of the state and local tax deduction; the three models share one amount, so they cannot disagree on it. It can move an answer only where the household itemizes and the estimate exceeds the sales tax amount: 022, 072, 078, 081, 114 and 120 in both years, and 117 and 121 in 2025 (policyengine-us's 2.60.0 runs in results/dossiers).",
    law="26 U.S.C. 164(a)(3) and (b)(5) (state and local income taxes paid, or general sales taxes in their place); 164(b)(7) (cap)",
    law_figure="",
    who_is_right="No answer is right until the board states the state income tax paid in the year. The prompt rule would make an unstated amount paid 0, which leaves the election to deduct general sales taxes. The board's exclusion records for 022, 081 and 114 name this reading, and its record for 120 gives the answer under the engine's own Connecticut liability and with no state income tax paid. policyengine-us 2.116.15, which no table here uses, takes a different amount for 121 (549.00 against 2.60.0's 658.80) and gives 886.32 in place of 875.34.",
    existing_report="https://github.com/PolicyEngine/policyengine-us/issues/9837",
    evidence=f"{EXCL} (022, 081, 114: 'The prompt lists no state income tax withheld or paid during 2026'); {T}verify-map-taxsim.md (F13: itemizers); results/shared/",
    households_shared="scenario_022;scenario_072;scenario_078;scenario_081;scenario_114;scenario_120;scenario_117@2025;scenario_121@2025",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}verify-map-taxsim.md"),
)

cause(
    cause_id="shared-state-paid-leave-contributions-not-in-salt",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 SALT (employee_state_payroll_tax left out), shared with Tax-Calculator and TAXSIM",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="120 itemizes, and the engine computes 827.98 of Connecticut paid leave contributions on the stated wages; the shared state and local tax amount leaves them out, so every answer does.",
    law="26 U.S.C. 164(a)(3); Rev. Rul. 2025-4 (mandatory employee contributions to a state paid family and medical leave fund, withheld from wages, are state income taxes deductible under 164(a)(3))",
    law_figure="",
    who_is_right="None of the four: the law counts the contributions in the deduction. Tax-Calculator with them added gives 40,131.49, 198.72 less (a counterfactual run); the board's record gives 40,217.95 on 2.15.17. The board excludes 120.",
    existing_report="",
    evidence=f"{T}trace-pe-b.md (120, shared points); {META} (scenario_120 note); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_120.json with e18400 raised by 827.98",
    households_shared="scenario_120",
    opened_by=OB.format(f"{T}trace-pe-b.md"),
)

cause(
    cause_id="shared-mortgage-debt-after-2017",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0; keycheck READINGS mortgage_date",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="049 and 120 state mortgage balances above $750,000 and no origination date; every answer limits interest to the $750,000 of acquisition debt that applies to debt incurred after December 15, 2017.",
    law="26 U.S.C. 163(h)(3)(F)(i)(II) and (IV)",
    law_figure="$750,000 limit; $1,000,000 for debt incurred on or before December 15, 2017",
    who_is_right="All four, under the prompt rule: the higher limit needs a fact (debt incurred before December 16, 2017) that the rule makes false. The board's record gives -224.64 for 120 if the debt were older; 049 takes the standard deduction either way.",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F8); {META} (scenario_120 note)",
    households_shared="scenario_049;scenario_120",
    opened_by=OB.format(f"{T}verify-unit-statute.md"),
)

cause(
    cause_id="shared-head-return-only",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 (one tax unit; dependents' own income stays out of the filer's AGI); keycheck (the head's return only)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="Every answer here computes the return of the head (and spouse). A listed member with income of their own who files their own return (123's 16-year-old with $45,000 of wages; 093's dependent1 under this repo's position on the credit) adds that return's tax only if the line covers every return in the household.",
    law="the board's output definition (aggregation 'sum' of income_tax_before_refundable_credits; benchmark_specs.json) and prompt ('one household group for tax and benefit calculations', prompts.py:15-27)",
    law_figure="",
    who_is_right="Neither the output's text nor the stated facts decide it. The board excludes both outputs (household_scope_dependent_returns); its alternative adds 3,220.00 for 123, which a TAXSIM run of the child's own return reproduces.",
    existing_report="",
    evidence=f"{EXCL} (093, 123); {T}trace-taxsim-b.md (123: TAXSIM of the child's return gives 3,220.00); {BOARD}policybench/benchmark_specs.json",
    households_shared="scenario_093;scenario_123",
    opened_by=OB.format(f"{T}trace-pe-b.md, {T}trace-taxsim-b.md"),
)

cause(
    cause_id="shared-bdc-income-not-added",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 (qualified_bdc_income read by no formula); keycheck READINGS qualified_bdc_income",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="042 lists 70.94 of 'qualified BDC income' beside its stated dividends. No answer adds it to income.",
    law="26 U.S.C. 61(a)(7) (dividends are gross income)",
    law_figure="",
    who_is_right="No answer is right until the board says whether the amount sits inside the stated dividends; the prompt rule does not decide whether one listed amount repeats another. As extra ordinary dividends it would raise 042's scored answer to 2,377.71 (Tax-Calculator counterfactual run; +15.74).",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F6); {T}fix-maps.md (no formula reads qualified_bdc_income); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_042.json with e00600 raised by 70.94",
    households_shared="scenario_042",
    opened_by=OB.format(f"{T}verify-unit-statute.md"),
)

cause(
    cause_id="shared-rental-with-basis-qualified-business-income",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build=f"policyengine-us 2.60.0 and 2.116.15 (rental_income_would_be_qualified and farm_rent_income_would_be_qualified default to true; experiment R10); {V} READINGS rental_qbi (rent with a stated basis and no other trade or business goes to Tax-Calculator e27200 and TAXSIM scorp)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="022 (rent 4,550, basis 24,786.06), 076 (rent 4,000, basis 49,921.10), 062 (farm rent 4,792.94, basis 22,440) and 112 (farm rent 1,920, basis 54,381) state rent or farm rent, the unadjusted basis of qualified property, and no other business. Every answer now counts the rent as qualified business income and deducts 20% of it: policyengine-us by default, the maps because the stated basis can only belong to a qualified trade or business. Until map version 2026-11-11.1 the maps read rent (not farm rent) the other way, so this reading moved 022 and 076 then and moves no difference now.",
    law="26 U.S.C. 199A(c)(1) and (d)(1) (qualified business income comes from a qualified trade or business); Treas. Reg. 1.199A-1(b)(14) (a section 162 trade or business); 199A(b)(6)(A) (qualified property: property the qualified trade or business holds and has available for use)",
    law_figure="20% of qualified business income: 910.00 (022), 800.00 (076)",
    who_is_right=f"Open on 022 and 076; this entry takes no side. Two independent authors, each writing a map blind to the other, read the rent as income from no trade or business: the second Tax-Calculator map gives 19,803.80 on 076 and the second TAXSIM map 11,313.77 on 022, and the first maps read it that way too until this revision ({SM_TC}, {SM_TS}). The case for the key: a stated basis of qualified property exists only for property held by a qualified trade or business, and the rental is the only activity that could hold it. The case against: the definition runs from the business to the property, so the basis implies a trade or business only by reading a defined term backwards, and the facts that make a rental a section 162 trade or business (regular and continuous involvement, or the 250 hours of Rev. Proc. 2019-38) are unstated, which the prompt rule makes false. On the other reading the answers would be 11,313.77 (022) and 19,803.80 (076). 062 and 112 do not move the key: 062's key is 0 for another cause (pe-survivor-benefits-not-income; under that entry's answer the other reading adds 115.03, the TAXSIM comparer's 'both readings defensible'), and 112 owes 0 either way.",
    existing_report="",
    evidence=f"{RX26} and {RX116} (R10: rent with basis is qualified business income, 0 with rental_income_would_be_qualified false); {PE}variables/household/income/person/misc/rental_income_would_be_qualified.py:13; {B2} (item 8); second_map/taxcalc/answers_2026.csv and second_map/taxsim/answers_2026.csv; {SM_TS} (062 +115.03, both_readings_defensible); Tax-Calculator counterfactual runs on the inputs in results/dossiers with e27200 0: 022 11,313.77, 076 19,803.80, 062 4,443.42, 112 0.00; {U}:107 READINGS rental_qbi",
    households_shared="scenario_022;scenario_062;scenario_076;scenario_112",
    opened_by=OB2.format(f"{B2}, {SM_TC}, {SM_TS}, {RX26}"),
)

cause(
    cause_id="shared-private-pension-no-early-distribution-tax",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build=f"policyengine-us 2.60.0 and 2.116.15 (no 72(t) formula); {V} READINGS retirement_penalty (no 72(t) tax on a private pension); TAXSIM has no input for the tax",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="Six households state a taxable private pension paid to a filer under 59 1/2: 007 (56, 35,280), 009 (57, 20,400), 025 (the spouse, 57, 32,200), 036 (56, 59,220), 073 (57, 3,108) and 088 (56, 1,862). No answer adds the 10% additional tax on early distributions to them: the maps tax only IRA, 401(k), 403(b) and SEP distributions, which name their plans.",
    law="26 U.S.C. 72(t)(1) (the tax applies to an amount from a qualified retirement plan as 4974(c) defines it); 72(q) (a 10% tax on an annuity contract that is not such a plan); 72(t)(2)(A)(iv) and (v) (no tax on substantially equal payments for life, or after separation from service after 55)",
    law_figure="10% of the taxable pension less the medical exception: 3,528.00 (007), 2,040.00 (009), 3,201.94 (025), 5,922.00 (036), 74.11 (073)",
    who_is_right="All four, under the prompt rule. The tax needs a fact the board does not state: that the pension comes from a qualified retirement plan (4974(c)) or an annuity contract (72(q)); and a pension in payment at 56 or 57 may meet an exception (life annuity payments, or separation from service after 55) the board does not state either. The Tax-Calculator comparer's list of fixes would tax the pensions: on that reading 007 would be 7,235.69, 009 10,388.00, 025 10,232.97, 036 10,848.40 and 073 74.11 (Tax-Calculator counterfactual runs with the tax as e09900), all scored; 088's head states a disability and no earnings, which the maps read as 72(m)(7) disability, so 088 stays at 0. The second Tax-Calculator map, written blind, taxes none of them.",
    existing_report="",
    evidence=f"second_map/taxcalc/sources/usc26_72.txt:405 (72(q)), :517 (72(t)(1)), :527 and :529 (exceptions (iv) and (v)); {B2} (item 4, the comparer's alternative); second_map/taxcalc/answers_2026.csv (equal to the first map's answers on 007, 009, 025, 036, 073 and 088); Tax-Calculator counterfactual runs on the inputs in results/dossiers with e09900 set to keycheck/statute.py early_distribution_tax of the taxable pension; {U}:152 READINGS retirement_penalty",
    households_shared="scenario_007;scenario_009;scenario_025;scenario_036;scenario_073;scenario_088",
    opened_by=OB2.format(f"{B2}, {SM_TC}"),
)

cause(
    cause_id="shared-over-the-counter-not-medical",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0; keycheck READINGS over_the_counter",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="Households list over-the-counter health expenses; every answer leaves them out of itemized medical expenses. The reading can move an answer only for a household that itemizes, has medical expenses above 7.5% of AGI and owes tax: 114 and 121 (016 and 072 itemize such expenses and owe 0 either way).",
    law="26 U.S.C. 213(b) (a medicine or drug counts only if prescribed or insulin) and 213(d)(1)",
    law_figure="",
    who_is_right="All four, under the prompt rule: the board does not describe the amounts as prescribed drugs, insulin or other medical care. The board excludes 114 and 121.",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F10); keycheck/unit.py READINGS over_the_counter",
    households_shared="scenario_016;scenario_072;scenario_114;scenario_121",
    opened_by=OB.format(f"{T}verify-unit-statute.md"),
)

# ---------------------------------------------------------------- positions on the key's 2026 answers
# One row per cause, household and line where the entry takes a position on the committed key's
# 2026 answer. results/cause_positions.csv holds them; scripts/make_cell_status.py reads them.
POSITION_VALUES = {
    "supports_key": "the law or the prompt rule, as the entry reads them, supports the key's answer as far as this cause goes",
    "supports_other_answer": "the law or the prompt rule supports a different answer; `supported_answer` gives it where computed",
    "turns_on_unstated_fact": "the answer turns on a fact the board does not state (about the household, or the scope of the line), and the entry takes no side; `other_reading_answer` gives the answer on the reading the key does not take",
    "no_effect": "the cause bears on the household but moves no answer on this line",
}
GROUNDS = {
    "law": "the statute decides on the stated facts",
    "prompt_rule": "the board's rule for unstated facts decides",
    "": "no grounds: the entry takes no side, or the cause moves nothing",
}
POSITION_FIELDS = ["cause_id", "case_id", "quantity", "position", "grounds", "key_value", "supported_answer",
                   "other_reading_answer", "how_computed", "note"]
POS = {}
DEFAULT_POSITION = {}
KEY_RUN = RUNS[("2026", "policybench-key")]


def position(cause_id, case, pos, grounds="", supported=None, other=None, how="", note="", quantity=L1):
    POS[(cause_id, f"scenario_{case}", quantity)] = dict(position=pos, grounds=grounds, supported=supported,
                                                        other=other, how=how, note=note)


# Entries that move another answer only, and say the key's answer is the one the law gives.
for cid in ("taxsim-no-overtime-deduction", "taxsim-no-nonitemizer-charitable-deduction",
            "taxsim-no-tax-exempt-interest-input", "taxsim-no-blindness-input", "taxsim-no-savers-credit",
            "taxsim-2026-child-care-credit-old-rates", "taxsim-refundable-child-credit-ignores-child-care-credit",
            "taxsim-three-child-refundable-credit-alternative", "taxsim-2026-salt-cap-40000",
            "map-ira-deduction-in-nonprop-cuts-eitc"):
    DEFAULT_POSITION[cid] = ("supports_key", "law", "the entry moves another answer and gives the key's answer as the law's")

KEY_LESS = "the key less this entry's amount on the key's run"
TCCF = "Tax-Calculator counterfactual run on the inputs in results/dossiers"

# The key's own rows: each entry's answer is the key less its amount.
for c in ("005", "052", "120"):
    position("key-ira-deducted-without-219g", c, "supports_other_answer", "law", how=f"{KEY_LESS}; equal to the board record's alternative")
position("key-sales-tax-table-column-shift", "020", "supports_other_answer", "law", how=f"{KEY_LESS} (the board's 2.15.17 value)")
position("pe-other-dependent-credit-without-dependency-tests", "093", "supports_other_answer", "law", how=KEY_LESS,
         note="for the head's return; shared-head-return-only leaves open whether the line adds the member's own return")
position("pe-divorce-year-default", "020", "supports_other_answer", "prompt_rule", how=KEY_LESS,
         note="with key-sales-tax-table-column-shift too: 70,332.82, Tax-Calculator's answer")
position("pe-medicare-part-b-premium-default", "114", "supports_other_answer", "prompt_rule", how=KEY_LESS,
         note="policyengine-us with takes_up_medicare_if_eligible false gives the same 11,265.27")
position("pe-net-investment-income-leaves-out-farm-rent", "120", "supports_other_answer", "law", how=KEY_LESS)
position("pe-scholarship-not-income", "030", "supports_other_answer", "prompt_rule", how=KEY_LESS,
         note="Tax-Calculator's and TAXSIM's answer")
position("pe-scholarship-not-income", "068", "supports_other_answer", "prompt_rule", how=KEY_LESS,
         note="Tax-Calculator's and TAXSIM's answer")
position("pe-survivor-benefits-not-income", "062", "supports_other_answer", "prompt_rule", how=KEY_LESS,
         note="Tax-Calculator's answer and the board record's alternative")
position("pe-survivor-benefits-not-income", "108", "no_effect",
         note="taxable income stays 0 with the benefits counted (Tax-Calculator and TAXSIM)")
position("pe-no-passive-activity-loss-limit", "120", "supports_other_answer", "law", how=KEY_LESS,
         note="the key's other entries move it too; with every entry that moves the key, 40,060.04, which a Tax-Calculator counterfactual run gives with the refund out and the board's state and local tax")
for c, why in (("004", "a partnership loss of 135 suspended"), ("098", "a farm rent loss of 11,100 suspended")):
    position("pe-no-passive-activity-loss-limit", c, "no_effect", note=f"{why}; taxable income stays 0")
position("pe-early-distribution-tax-not-computed", "064", "supports_other_answer", "law", how=KEY_LESS,
         note="Tax-Calculator gives 6,441.45. The proposal rests on the line holding the tax: the board's reference engine adds qualified_retirement_penalty to this line when a household states it, and 72(t) is chapter 1 income tax; Form 1040 reports it with the other taxes on Schedule 2, Part II (second_map/taxcalc/sources/i1040gi.txt:90-92), the question shared-net-investment-income-tax-in-line leaves open for the net investment income tax")
position("pe-early-distribution-tax-not-computed", "023", "turns_on_unstated_fact", other=1443.43,
         how="Tax-Calculator's answer, with the tax", note="72(m)(7) disability: stated disabled, with wages under the 2026 monthly amount for substantial gainful activity; the second Tax-Calculator map reads the stated disability as 72(m)(7) and gives the key's 643.43")
position("pe-early-distribution-tax-not-computed", "074", "turns_on_unstated_fact", other=38.40,
         how="Tax-Calculator's answer, with the tax", note="72(m)(7) disability: Social Security disability benefits and no stated disability; the second Tax-Calculator map reads the benefits as 72(m)(7) disability and gives the key's 0.00")
position("taxsim-no-early-distribution-tax-input", "064", "supports_other_answer", "law", supported=6441.46,
         how="as pe-early-distribution-tax-not-computed: the key plus 2,000.00")
for c, other in (("023", 1443.43), ("074", 38.40)):
    position("taxsim-no-early-distribution-tax-input", c, "turns_on_unstated_fact", other=other,
             how="Tax-Calculator's answer, with the tax", note="as pe-early-distribution-tax-not-computed")

# Shared readings, and the cells where the key's frozen value departs from the other answers.
for c in ("005", "120"):
    position("shared-state-tax-refund-counted-in-full", c, "supports_key", "prompt_rule",
             note="the key's frozen value leaves the refund out, as the prompt rule supports; the other three answers count it")
for c, v, extra in (("033", 3788.99, "; equal to the board record's alternative"), ("078", 23772.80, "; equal to the board record's alternative"),
                    ("082", 9564.92, ""), ("117", 24391.80, "; equal to the board record's alternative")):
    position("shared-state-tax-refund-counted-in-full", c, "supports_other_answer", "prompt_rule", supported=v,
             how=f"{TCCF} with e00700 0{extra}")
for c in ("074", "088"):
    position("shared-state-tax-refund-counted-in-full", c, "no_effect", how=f"{TCCF} with e00700 0 gives the same answer")
for c, alt in (("002", 1890.30), ("107", 211.23), ("121", 875.34)):
    position("shared-disability-benefits-taxable", c, "supports_key", "prompt_rule", other=alt,
             how="the board record's alternative, which policyengine-us 2.60.0, Tax-Calculator and TAXSIM give")
for c, why in (("057", "owes 0 either way"), ("084", "owes 0 either way"), ("067", "the benefits are a dependent's own, outside the head's return")):
    position("shared-disability-benefits-taxable", c, "no_effect", note=why)
for c in ("029", "030", "056", "080", "090", "112"):
    position("shared-financial-assistance-gift", c, "supports_key", "law", note="26 U.S.C. 102(a)")
position("shared-disabled-member-qualifying-child", "067", "supports_key", "law", note="by either reading of 'is disabled'")
position("shared-disabled-member-qualifying-child", "064", "no_effect", note="a qualifying relative either way; no earned income credit at its income")
for c, niit in (("005", 5721.98), ("020", 222.64), ("052", 218.42), ("120", 163.40)):
    position("shared-net-investment-income-tax-in-line", c, "turns_on_unstated_fact", other=("key", -niit),
             how=f"the key less policyengine-us 2.60.0's net investment income tax ({niit:,.2f}): an inference that the frozen value holds the same tax",
             note="the 1411 tax is chapter 2A, not chapter 1 income tax; the board's reference engine puts it in this line, and the board excludes 020 on the question")
for c, v, how in (("022", 12234.66, f"{TCCF} with e18400 963.00, the engine's sales tax amount (its base equals the key)"),
                  ("078", 27290.70, f"{TCCF} with e18400 914.00 (its base equals the key)"),
                  ("081", 28763.81, f"the key plus the change in a {TCCF} with e18400 853.00 (+1,831.54)"),
                  ("114", 11783.48, f"{TCCF} with e18400 577.00 and the key's Medicare Part B premium added to e17500 (which gives the key's 10,729.61 without the change)"),
                  ("120", 43263.75, f"the key plus the change in a {TCCF} with e18400 1,197.00 (+3,241.93): an inference that the key's return moves alike")):
    position("shared-state-income-tax-withholding-estimate", c, "supports_other_answer", "prompt_rule", supported=v, how=how,
             note={"022": "the board record's alternative reads the engine's state liability: 11,895.23",
                   "081": "the board record's alternative reads the engine's state liability: 26,991.31",
                   "114": "the board record's alternative reads the engine's state liability: 11,137.31; with pe-medicare-part-b-premium-default's position too, 11,969.81"}.get(c, ""))
position("shared-state-income-tax-withholding-estimate", "072", "no_effect", how=f"{TCCF} with e18400 814.00 gives 0.00")
position("shared-state-paid-leave-contributions-not-in-salt", "120", "supports_other_answer", "law", supported=39823.10,
         how=f"the key plus the change in a {TCCF} with e18400 raised by 827.98 (-198.72): an inference that the key's return moves alike",
         note="the board's record gives 40,217.95 on 2.15.17")
position("shared-mortgage-debt-after-2017", "120", "supports_key", "prompt_rule", other=("key", -224.64),
         how="the key less the 224.64 the board's record gives for older debt")
position("shared-mortgage-debt-after-2017", "049", "no_effect", note="takes the standard deduction either way")
for c, alt in (("093", 11848.99), ("123", 8420.24)):
    position("shared-head-return-only", c, "turns_on_unstated_fact", other=alt,
             how="the board record's alternative (the member's own return adds 3,220.00)")
position("shared-bdc-income-not-added", "042", "turns_on_unstated_fact", other=2377.71,
         how=f"{TCCF} with e00600 raised by 70.94 (its base, 2,361.97, equals the key within $0.01)")
for c, alt, second in (("022", 11313.77, "TAXSIM"), ("076", 19803.80, "Tax-Calculator")):
    position("shared-rental-with-basis-qualified-business-income", c, "turns_on_unstated_fact", other=alt,
             how=f"{TCCF} with e27200 0 (its base equals the key); the second {second} map, written blind, gives the same answer")
position("shared-rental-with-basis-qualified-business-income", "062", "no_effect",
         note="the key's 0 does not move; under pe-survivor-benefits-not-income's answer the other reading adds 115.03")
position("shared-rental-with-basis-qualified-business-income", "112", "no_effect", note="owes 0 either way")
for c, alt in (("007", 7235.69), ("009", 10388.00), ("025", 10232.97), ("036", 10848.40), ("073", 74.11)):
    position("shared-private-pension-no-early-distribution-tax", c, "supports_key", "prompt_rule", other=alt,
             how=f"{TCCF} with e09900 set to the tax keycheck/statute.py early_distribution_tax gives (its base equals the key)")
position("shared-private-pension-no-early-distribution-tax", "088", "no_effect",
         note="stated disabled with no earnings, which the maps read as 72(m)(7) disability: no tax on either reading of the pension")
for c in ("114", "121"):
    position("shared-over-the-counter-not-medical", c, "supports_key", "prompt_rule", note="26 U.S.C. 213(b)")
for c in ("016", "072"):
    position("shared-over-the-counter-not-medical", c, "no_effect", note="owes 0 either way")


# ---------------------------------------------------------------- checks
KINDS = {"model-law-departure", "model-no-provision", "pe-default-unstated-fact", "key-decided-value",
         "map-limit", "shared-reading", "unexplained"}
ANSWERERS = {"policybench-key", "policyengine-us", "taxcalc", "taxsim"}
FIELDS = ["cause_id", "kind", "answerer", "release_or_build", "fixed_in", "law_years", "quantities", "summary",
          "law", "law_figure", "who_is_right", "existing_report", "evidence", "households", "households_shared",
          "opened_by", "entry_status"]
CELL_FIELDS = ["cause_id", "case_id", "quantity", "table", "answerer", "run", "amount", "basis"]


def load_answers():
    values = defaultdict(dict)
    with open(REPO / "results/answers.csv", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["case_set"] == "board-100" and row["status"] == "ok":
                values[(row["case_id"], row["quantity"])][row["run"]] = float(row["value"])
    return values


def check():
    ids = [c["cause_id"] for c in CAUSES]
    assert len(ids) == len(set(ids)), "duplicate cause_id"
    for c in CAUSES:
        assert c["kind"] in KINDS, c
        assert set(c["answerer"].split(";")) <= ANSWERERS, c
        assert c["law"] and c["who_is_right"], c
    assert {r["cause_id"] for r in CELLS} <= set(ids)
    answers = load_answers()
    sums = defaultdict(float)
    for r in CELLS:
        sums[(r["case_id"], r["quantity"], r["run"])] += float(r["amount"])
    worst, bad = 0.0, []
    tables = {"2026": [RUNS[("2026", a)] for a in ("policybench-key", "policyengine-us", "taxcalc", "taxsim")],
              "2025": [RUNS[("2025", a)] for a in ("policyengine-us", "taxcalc", "taxsim")]}
    for (case, quantity), by_run in answers.items():
        if quantity not in LINES:
            continue
        for table, runs in tables.items():
            vals = {}
            for run in runs:
                v = by_run.get(run)
                if v is None and run == "pb-reference-2.60.0":
                    v = by_run.get("pe-2.60.0-board-2026")
                if v is not None:
                    vals[run] = v
            names = list(vals)
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    gap = (vals[a] - vals[b]) - (sums[(case, quantity, a)] - sums[(case, quantity, b)])
                    worst = max(worst, abs(gap))
                    if abs(gap) > 1.0:
                        bad.append((case, quantity, table, a, b, round(gap, 2)))
    return worst, bad


def shared_tokens_2026(field):
    """households_shared tokens that apply to the 2026 table (no suffix, or @2026)."""
    out = []
    for token in filter(None, field.split(";")):
        case, _, table = token.partition("@")
        if table in ("", "2026"):
            out.append(case)
    return out


def money(x):
    return f"{x:.2f}"


def build_positions():
    """The rows of results/cause_positions.csv, with every check the file promises."""
    answers = load_answers()
    by_id = {c["cause_id"]: c for c in CAUSES}
    key_amount = defaultdict(float)
    on_cell = set()
    for r in CELLS:
        if r["table"] == "2026":
            on_cell.add((r["cause_id"], r["case_id"], r["quantity"]))
        if r["run"] == KEY_RUN:
            key_amount[(r["cause_id"], r["case_id"], r["quantity"])] += float(r["amount"])
    wanted = set(on_cell)
    for c in CAUSES:
        if c["kind"] == "shared-reading":
            for case in shared_tokens_2026(c["households_shared"]):
                for quantity in c["quantities"].split(";"):
                    wanted.add((c["cause_id"], case, quantity))
    stray = set(POS) - wanted
    for cid, case, quantity in stray:  # an explicit position off the entry's cells: the cause must name the household
        assert cid in by_id, cid
        assert quantity in by_id[cid]["quantities"].split(";"), (cid, case, quantity)
        assert case.split("_")[1] in by_id[cid]["summary"], (cid, case, "the summary does not name the household")
    rows = []
    order = {c["cause_id"]: i for i, c in enumerate(CAUSES)}
    for cid, case, quantity in sorted(wanted | set(POS), key=lambda k: (order[k[0]], k[1], k[2])):
        assert cid in by_id, cid
        key = answers.get((case, quantity), {}).get(KEY_RUN)
        assert key is not None, (cid, case, quantity, "no key answer")
        if (cid, case, quantity) in POS:
            p = dict(POS[(cid, case, quantity)])
        elif cid in DEFAULT_POSITION:
            pos, grounds, how = DEFAULT_POSITION[cid]
            p = dict(position=pos, grounds=grounds, supported=None, other=None, how=how, note="")
        else:
            raise AssertionError(f"no position for {cid} on {case} {quantity}")
        assert p["position"] in POSITION_VALUES, p
        assert p["grounds"] in GROUNDS, p
        if p["position"] in ("supports_key", "supports_other_answer"):
            assert p["grounds"] in ("law", "prompt_rule"), (cid, case, p)
        else:
            assert p["grounds"] == "", (cid, case, p)
        moved = key_amount.get((cid, case, quantity), 0.0)
        supported = p["supported"]
        if p["position"] in ("supports_key", "no_effect"):
            assert supported is None and abs(moved) <= 1.0, (cid, case, "a position for the key cannot move the key")
            supported = key
        elif p["position"] == "supports_other_answer":
            if supported is None:
                assert abs(moved) > 1.0, (cid, case, "no answer given and no row on the key's run")
                supported = key - moved
            elif abs(moved) > 1.0:
                assert abs(supported - (key - moved)) <= 1.0, (cid, case, supported, key - moved)
            assert abs(supported - key) > 1.0, (cid, case, "a different answer must differ from the key")
        else:
            assert supported is None, (cid, case, "an open reading supports no answer")
        other = p["other"]
        if isinstance(other, tuple):
            other = key + other[1]
        rows.append(dict(cause_id=cid, case_id=case, quantity=quantity, position=p["position"], grounds=p["grounds"],
                         key_value=money(key), supported_answer="" if supported is None else money(supported),
                         other_reading_answer="" if other is None else money(other), how_computed=p["how"],
                         note=p["note"]))
    # every row on the key's run with a non-zero amount has a position
    for (cid, case, quantity), amount in key_amount.items():
        if abs(amount) > 0:
            assert any(r["cause_id"] == cid and r["case_id"] == case and r["quantity"] == quantity for r in rows), (cid, case)
    return rows


def write():
    worst, bad = check()
    if bad:
        for b in bad:
            print("UNRECONCILED", b)
        sys.exit(1)
    print(f"invariant holds; largest residual {worst:.4f}")
    positions = build_positions()
    by_cause = defaultdict(set)
    for r in CELLS:
        by_cause[r["cause_id"]].add(r["case_id"].split("_")[1])
    with open(REPO / "results/causes.csv", "w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=FIELDS)
        w.writeheader()
        for c in CAUSES:
            row = dict(c)
            row["households"] = ";".join(f"scenario_{h}" for h in sorted(by_cause.get(c["cause_id"], ())))
            row["entry_status"] = "open"
            w.writerow(row)
    order = {c["cause_id"]: i for i, c in enumerate(CAUSES)}
    rows = sorted(CELLS, key=lambda r: (order[r["cause_id"]], r["case_id"], r["quantity"], -int(r["table"]), r["answerer"]))
    with open(REPO / "results/cause_cells.csv", "w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=CELL_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(REPO / "results/cause_positions.csv", "w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=POSITION_FIELDS)
        w.writeheader()
        w.writerows(positions)
    print(len(CAUSES), "causes,", len(CELLS), "cell rows,", len(positions), "positions")


if __name__ == "__main__":
    if "--check" in sys.argv:
        worst, bad = check()
        print("largest residual", round(worst, 4), "unreconciled", bad)
        print(len(build_positions()), "positions")
    else:
        write()
