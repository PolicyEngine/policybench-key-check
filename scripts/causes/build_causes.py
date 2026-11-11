"""Write results/causes.csv and results/cause_cells.csv, checking the invariant first.

Run with python3 -I from anywhere; it writes into REPO only after every check passes.
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

# ---------------------------------------------------------------- this repo's input map
cause(
    cause_id="map-ira-deduction-in-nonprop-cuts-eitc",
    kind="map-limit",
    answerer="taxsim",
    release_or_build="keycheck 2026-11-10.2 (keycheck/map_taxsim.py) on taxsimtest cd2026110117",
    fixed_in="",
    law_years="both",
    quantities=L2,
    summary="TAXSIM has no input for an adjustment that lowers AGI alone, so the map enters 100's IRA deduction (180.32) as negative nonprop, which this build also subtracts from earned income for the earned income credit. In the phase-in range that costs 40% of the deduction.",
    law="26 U.S.C. 32(c)(2)(A) (earned income: wages and net earnings from self-employment; the 219 deduction does not reduce it)",
    law_figure="40% x 2,055.72 = 822.29 for 100",
    who_is_right="policyengine-us and Tax-Calculator. Entering the deduction where it moves only AGI (a negative short-term gain) gives TAXSIM 822.29 too.",
    existing_report="",
    evidence=f"{T}trace-taxsim-b.md (100: TAXSIM with nonprop 0 and stcg -180.32 gives 822.29); {T}fix-maps.md (kept as a noted limit)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-taxsim-b.md"),
)
cells("map-ira-deduction-in-nonprop-cuts-eitc", both("100", L2, "taxsim", -72.13),
      "trace run: TAXSIM with the deduction moved out of nonprop gives 822.29")

cause(
    cause_id="map-rental-not-qualified-business-income",
    kind="map-limit",
    answerer="taxcalc;taxsim",
    release_or_build="keycheck 2026-11-10.2 (READINGS rental_qbi in keycheck/unit.py; rent to e02000 in Tax-Calculator, to intrec in TAXSIM)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="The maps read stated rent as income that is not qualified business income, so Tax-Calculator and TAXSIM allow no 20% deduction on it. policyengine-us counts rent as qualified business income unless told otherwise (rental_income_would_be_qualified defaults to true) and deducts 20% of it.",
    law="26 U.S.C. 199A(c)(3)(A)(i) and (d)(1) (qualified business income comes from a qualified trade or business); 199A(b)(2)(B)(ii) and (b)(6) (unadjusted basis of qualified property: depreciable property held for use in the qualified trade or business)",
    law_figure="20% of qualified business income: 910.00 (022), 800.00 (076)",
    who_is_right="policyengine-us, on this entry's position. The board does not say outright that either rental is a trade or business, but it states unadjusted basis of qualified property for both filers (24,786.06 for 022, 49,921.10 for 076), a figure that exists only for property of a qualified trade or business, and rent is each filer's only business-type income. A reader who applies the prompt rule (an unstated status is false) to the trade-or-business question without weighing the stated basis would side with Tax-Calculator and TAXSIM.",
    existing_report="",
    evidence=f"{T}trace-pe-a.md (022: Tax-Calculator with the rent in e26270, TAXSIM with it in scorp, each give policyengine-us's answer); {T}trace-pe-b.md (076; the trace does not mention the stated basis); results/repro/board_experiments.txt (076 and results/repro/board_experiments_2.txt 022: rental_income_would_be_qualified false gives Tax-Calculator's answer); {PE}variables/household/income/person/misc/rental_income_would_be_qualified.py:13; {PE}parameters/gov/irs/deductions/qbi/income_definition.yaml:8; {PE}variables/gov/irs/income/taxable_income/deductions/qualified_business_income_deduction/qualified_business_income.py:22-25; results/dossiers/scenario_022.json and scenario_076.json (stated unadjusted_basis_qualified_property)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-a.md, {T}trace-pe-b.md"),
)
cells("map-rental-not-qualified-business-income",
      both("022", L1, "taxcalc", 200.20) + both("022", L1, "taxsim", 200.20)
      + both("076", L1, "taxcalc", 192.00) + both("076", L1, "taxsim", 192.00),
      "engine run (results/repro): rental_income_would_be_qualified false gives the maps' answer; trace runs move Tax-Calculator and TAXSIM to policyengine-us's")

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
    summary="policyengine-us 2.60.0 leaves Form 4835 farm rent out of net investment income, so 120's farm rent loss (2,446.59) does not offset its rent and interest, and the net investment income tax comes to 163.40 in place of 70.43.",
    law="26 U.S.C. 1411(c)(1)(A)(i) (gross income from rents) and (c)(1)(B) (deductions properly allocable to it)",
    law_figure="3.8% of net investment income 1,853.41 = 70.43",
    who_is_right="Tax-Calculator, TAXSIM and policyengine-us 2.116.15. Adding farm_rent_income to 2.60.0's sources gives 40,330.21, their answer.",
    existing_report="https://github.com/PolicyEngine/policyengine-us/issues/10075",
    evidence=f"{T}trace-pe-b.md (120); results/repro/board_experiment_120_rerun.txt; {PE}parameters/gov/irs/investment/income/sources.yaml:8-27 (2.60.0, no farm_rent_income) and :23 at 2.116.15; {META} (revisions[17]: the 1.755.4-to-2.15.17 move for 120 is the IRA and #9122 alone, so the frozen value carries the same omission: inference)",
    households_shared="",
    opened_by=OB.format(f"{T}trace-pe-b.md"),
)
cells("pe-net-investment-income-leaves-out-farm-rent",
      [("120", L1, "2026", "policyengine-us", 92.97), ("120", L1, "2026", "policybench-key", 92.97),
       ("120", L1, "2025", "policyengine-us", 92.97)],
      "engine run (results/repro/board_experiment_120_rerun.txt): farm rent in net investment income gives 40,330.21")

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
    release_or_build="policyengine-us 2.15.17 and later (policyengine-us#9422, which fixed issue #9122), and the key's values that the board froze on 2.15.17; Tax-Calculator and TAXSIM through READINGS salt_refund_income (keycheck 2026-11-10.2)",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="A listed state or local tax refund counts in full as income in policyengine-us (which documents the input as the taxable refund on Schedule 1, line 1) and, through this repo's reading, in Tax-Calculator and TAXSIM. The key's frozen 1.755.4 values for 005 and 120 never counted the input, so those two cells move three answers and not the key; elsewhere every answer counts it.",
    law="26 U.S.C. 111(a) (a recovery is income only to the extent the earlier deduction reduced tax)",
    law_figure="",
    who_is_right="No answer is right until the board states the prior year's facts: whether the household itemized and deducted the refunded tax. The prompt rule makes that unstated fact false, so none of the refund is income (the board's own alternative reading). On that reading the key's frozen values for 005 and 120 hold the refund correctly, and 082's scored answer would fall by 14.85.",
    existing_report="",
    evidence=f"{BOARD}reference_audit/2026-09-28/fixes/latest_alt_salt_refund_no_prior_benefit.py:1-30; {META} (revisions[17]: 005 '+$1,327.26 move is #9122 alone', 120 '+$394.85 move is #9122 alone'); results/repro/board_experiments_2.txt (005 salt_refund_income 0: 107,198.34); counterfactual runs on the inputs in results/dossiers (Tax-Calculator 005 with e00700 0: 107,198.33; 082: 9,564.92; TAXSIM 005 with pensions less the refund: 107,540.65, above the engine's 107,198.34 by the 170(p) deduction TAXSIM lacks; 120, both models with the refund out and the shared state and local tax lowered by the 113.77 the board records for the engine's Connecticut estimate: 39,935.35)",
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
    cause_id="shared-scholarship-not-income",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 (educational_assistance has no federal effect); keycheck READINGS educational_assistance",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="068's filer, 31 and earning $34,083.53, lists $73,000 of educational assistance (scholarships and grants). Every answer leaves it out of income.",
    law="26 U.S.C. 117(a) and (b) (the exclusion covers a qualified scholarship only for a degree candidate and only to the extent the student uses it for qualified tuition and related expenses)",
    law_figure="",
    who_is_right="Under the prompt rule the whole amount is income: degree candidacy and tuition are unstated (the board's prompt cannot list tuition), so the exclusion's conditions are false. On that reading 068's scored answer would be 14,728.38 (Tax-Calculator with the amount as income) in place of 1,910.02. 030's $5,000 changes nothing: its filer owes 0 either way.",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F2); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_068.json with e01400 raised by 73,000: 14,728.38 (2026), 15,007.38 (2025)",
    households_shared="scenario_068;scenario_030",
    opened_by=OB.format(f"{T}verify-unit-statute.md"),
)

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
    release_or_build="keycheck 2026-11-10.2 READINGS is_disabled; policyengine-us 2.60.0 claims the member by another route (pe-other-dependent-credit-without-dependency-tests)",
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
    cause_id="shared-passive-rental-loss-allowed",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="policyengine-us 2.60.0 (no 469 limit), Tax-Calculator 6.9.0, TAXSIM cd2026110117 as mapped",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="120's two rental activities, rent of 2,000 and a Form 4835 farm rent loss of 2,446.59, net to a 446.59 loss, which every answer deducts.",
    law="26 U.S.C. 469(a) (passive activity loss disallowed), 469(c)(2) (a rental activity is passive), 469(i)(3)(A) (the $25,000 allowance falls by 50% of AGI above $100,000)",
    law_figure="allowance 0 at AGI 234,414",
    who_is_right="None of the four: at this AGI the law suspends the net passive loss, absent other passive income or real estate professional status, which the board does not state and the prompt rule makes false. Tax-Calculator with the loss suspended gives 40,454.90 (+124.69, a counterfactual run); the board's record gives +24.75 on 2.15.17, a gap this entry does not examine. The board excludes 120.",
    existing_report="",
    evidence=f"{T}trace-pe-b.md (120, shared points); {META} (scenario_120: 'the engine's missing 469 limit'); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_120.json with e02000 0 and e27200 -2,000 (the rent kept, the loss suspended)",
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
    cause_id="shared-survivor-benefits-not-taxable",
    kind="shared-reading",
    answerer="policybench-key;policyengine-us;taxcalc;taxsim",
    release_or_build="the board's reference reading; keycheck READINGS survivor_benefits",
    fixed_in="",
    law_years="both",
    quantities=L1,
    summary="062 and 108 list survivor benefits other than Social Security (28,800 and 10,392); every answer leaves them out of income.",
    law="26 U.S.C. 61(a) and 72 (a survivor annuity is income); 101(a) (life insurance proceeds paid by reason of death excluded)",
    law_figure="",
    who_is_right="Under the prompt rule the benefits are income: the exclusion needs a fact (life insurance proceeds) that the rule makes false. 062's answer would be 4,328.39, the board's alternative (the board excludes 062); 108 owes 0 either way (Tax-Calculator counterfactual runs).",
    existing_report="",
    evidence=f"{T}verify-unit-statute.md (F12); {EXCL} (062); Tax-Calculator counterfactual runs on the inputs in results/dossiers/scenario_062.json and scenario_108.json with the benefits added to e01500 and e01700",
    households_shared="scenario_062;scenario_108",
    opened_by=OB.format(f"{T}verify-unit-statute.md"),
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


def write():
    worst, bad = check()
    if bad:
        for b in bad:
            print("UNRECONCILED", b)
        sys.exit(1)
    print(f"invariant holds; largest residual {worst:.4f}")
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
    print(len(CAUSES), "causes,", len(CELLS), "cell rows")


if __name__ == "__main__":
    if "--check" in sys.argv:
        worst, bad = check()
        print("largest residual", round(worst, 4), "unreconciled", bad)
    else:
        write()
