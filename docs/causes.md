# Causes of disagreement on the board's 100 households

This file gives, for every household and line where the committed key, policyengine-us, Tax-Calculator and TAXSIM disagree, the causes of the disagreement, how much each cause moves each answer, what the law says, and which answer the law supports. `results/causes.csv` holds one row per cause and `results/cause_cells.csv` one row per cause, household, line, table and answerer; this account renders both. `tests/test_causes.py` checks that the causes account for every difference to the dollar.

Claude Opus 5.5 agents opened every entry: four tracers reconciled each disagreement to its cause (`evidence/traces/trace-pe-a.md`, `trace-pe-b.md`, `trace-taxsim-a.md`, `trace-taxsim-b.md`), reviewers checked the maps (`evidence/traces/verify-*.md`), and a further agent wrote these tables on 2026-11-10. Every entry stays open. The "who is right" line states the entry's position and its grounds in law; it awaits a human reviewer and decides nothing. This repo proposes answers; it changes nothing on the board.

## How to read the entries

**Answerers and tables.** The 2026 table compares four answers: the committed key (`policybench-key`, run `pb-reference-2.60.0`), policyengine-us 2.60.0 under the board's conventions (`pe-2.60.0-board-2026`), Tax-Calculator 6.9.0 (`taxcalc-6.9.0-2026`) and TAXSIM's test build cd2026110117 (`taxsim-cd2026110117-2026`). The 2025 table compares the last three under 2025 law (`pe-2.60.0-board-2025`, `taxcalc-6.9.0-2025`, `taxsim-cd2026110117-2025`). `results/runs.csv` describes each run. The lines are the four in `scripts/agreement.py`; every cause here moves federal tax before refundable credits or federal refundable credits.

**Amounts.** A cell's amount is what the cause adds to that answerer's answer, in dollars, relative to the answer the law supports, or, where the cause turns on a fact the household does not state, the answer the board's prompt rule supports. A cause that lowers a refundable credit has a negative amount on that line. For any two answerers, the difference between their answers equals the difference between the sums of their amounts, within $1; the largest residual is $0.30 (081, cents).

**The prompt rule.** The board tells every answerer to treat an unlisted number as 0 and any other unlisted fact, boolean or status as false, to assume filing and take-up when required, and not to infer unlisted income, expenses, assets, benefit receipt, rent or health coverage (`PolicyEngine/policybench@c7ede86c:policybench/prompts.py:15-27`). These entries read the rule one way throughout: a provision that includes or allows something only on a fact does not apply when the household does not state the fact, and a provision that excludes or denies something only on a fact does not apply either. Where the cause is an unstated fact, the entry says that no answer is right until the household states the fact, and then which answer the rule points to.

**Counterfactual runs.** Where an entry cites a counterfactual run, it means Tax-Calculator 6.9.0 or TAXSIM cd2026110117 run on the inputs recorded in `results/dossiers/<case>.json` (the `in_` fields under `other_models`), with the settings of `scripts/run_taxcalc.py` or `keycheck/taxsim.py`, changing only the input the entry names. The engine experiments sit in `results/repro/`.

**Cell standing.** Where this account describes a cell's standing it uses three phrases: an answer "reproduced by a run of another lineage" (Tax-Calculator or TAXSIM gives it within $1), "contested" (an entry here says the law or the prompt rule supports a different answer), and "resting on one model" (no run of another lineage gives it).

## Kinds

| Kind | Meaning | Entries |
|---|---|---:|
| `model-law-departure` | A model computes a provision the law gives, but computes it differently from the law. | 6 |
| `model-no-provision` | A model has no input for a stated fact, or no provision for the law of the year, so its answer leaves the provision out. | 5 |
| `pe-default-unstated-fact` | policyengine-us fills a fact the household does not state with a default value, and the default moves the answer. | 2 |
| `key-decided-value` | The committed key holds a value the board decided on an earlier engine release, and that value differs from what the engine gives today. | 2 |
| `map-limit` | This repo's input map cannot express a stated fact in Tax-Calculator or TAXSIM the way the law treats it, or reads a fact differently from policyengine-us. | 2 |
| `shared-reading` | Every answerer, or every answerer but the key, reads a stated or unstated fact the same way. Where all answers in a table move alike the reading leaves no trace in any difference, so the entry lists the households in `households_shared` and writes no cell rows; where the key's frozen value departs from the others, the entry writes rows for the answers it moves. | 14 |
| `unexplained` | A residual no trace accounts for. No entry has this kind. | 0 |

## Causes

### `taxsim-no-overtime-deduction`: TAXSIM has no overtime deduction

*Kind* `model-no-provision`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM's test build has no input for qualified overtime compensation, so it taxes the overtime premium that policyengine-us and Tax-Calculator deduct. Where the child tax credit absorbs all the tax (026), the higher tax leaves less credit to refund.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 225(a)-(c) (deduction for qualified overtime compensation, taxable years 2025 through 2028); 26 U.S.C. 63(b)(6) (allowed to filers who do not itemize). **Figure:** up to $12,500 ($25,000 joint), reduced by $100 for each $1,000 of modified AGI above $150,000 ($300,000 joint).
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator. The board states an FLSA overtime premium inside wages, which 225(c)(1) makes qualified overtime compensation; the test build cannot take the fact, so its answer leaves out a deduction the law allows.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-a.md (026, 037, 046, 049, 064: Tax-Calculator with overtime_income 0 gives TAXSIM's answer; TAXSIM with the deduction entered as negative nonprop gives policyengine-us's); evidence/traces/trace-taxsim-b.md (089, 091, 117); evidence/taxsim.md (probe P1.2: no input); keycheck/map_taxsim.py (fsla_overtime_premium listed as unexpressed).
- **Source:** evidence/traces/trace-taxsim-a.md, evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 026 | refundable credits | 2026 | `taxsim` | -929.55 |
| 026 | refundable credits | 2025 | `taxsim` | -929.55 |
| 037 | tax before refundable credits | 2026 | `taxsim` | 1,155.48 |
| 037 | tax before refundable credits | 2025 | `taxsim` | 1,155.48 |
| 046 | tax before refundable credits | 2026 | `taxsim` | 1,780.65 |
| 046 | tax before refundable credits | 2025 | `taxsim` | 1,780.65 |
| 049 | tax before refundable credits | 2026 | `taxsim` | 5,500.00 |
| 049 | tax before refundable credits | 2025 | `taxsim` | 5,559.54 |
| 064 | tax before refundable credits | 2026 | `taxsim` | 1,667.91 |
| 064 | tax before refundable credits | 2025 | `taxsim` | 1,667.91 |
| 089 | tax before refundable credits | 2026 | `taxsim` | 416.09 |
| 089 | tax before refundable credits | 2025 | `taxsim` | 416.09 |
| 091 | tax before refundable credits | 2026 | `taxsim` | 75.35 |
| 091 | tax before refundable credits | 2025 | `taxsim` | 75.35 |
| 117 | tax before refundable credits | 2026 | `taxsim` | 5,602.67 |
| 117 | tax before refundable credits | 2025 | `taxsim` | 5,669.02 |

### `taxsim-no-nonitemizer-charitable-deduction`: TAXSIM has no 2026 charitable deduction for filers who do not itemize

*Kind* `model-no-provision`. *Moves* `taxsim`. *Law years* 2026. *Entry* open.

From 2026 a filer who takes the standard deduction also deducts cash gifts to charity up to a cap. TAXSIM's test build has no input or provision for it, so its taxable income keeps the gifts the other models deduct. In 117 TAXSIM itemizes instead (33,830.22), which falls 369.77 short of the standard deduction plus the gifts.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 170(p) as amended by Pub. L. 119-21 sec. 70424 (taxable years after 2025), determined without regard to the 0.5% floor of 170(b)(1)(I); 26 U.S.C. 63(b)(4). **Figure:** cash gifts up to $1,000 ($2,000 joint).
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator. 170(p) counts cash gifts to an organization described in 170(b)(1)(A), other than a supporting organization or a donor-advised fund. This entry reads the stated charitable cash donations as gifts to such an organization; the board does not state the recipient, and the prompt rule makes the two unstated exceptions false, so the gifts qualify.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-a.md (005, 020: Tax-Calculator with STD_charity_ded_nonitemizers_max 0 gives TAXSIM's answer to the cent); evidence/traces/trace-taxsim-a.md (049, 055, 082); evidence/traces/trace-taxsim-b.md (099, 110, 117, 122, 123); evidence/taxsim.md (probe P9.5).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-taxsim-a.md, evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 005 | tax before refundable credits | 2026 | `taxsim` | 342.33 |
| 020 | tax before refundable credits | 2026 | `taxsim` | 68.60 |
| 049 | tax before refundable credits | 2026 | `taxsim` | 127.55 |
| 055 | tax before refundable credits | 2026 | `taxsim` | 240.00 |
| 082 | tax before refundable credits | 2026 | `taxsim` | 154.00 |
| 099 | tax before refundable credits | 2026 | `taxsim` | 440.00 |
| 110 | tax before refundable credits | 2026 | `taxsim` | 92.99 |
| 117 | tax before refundable credits | 2026 | `taxsim` | 88.74 |
| 122 | tax before refundable credits | 2026 | `taxsim` | 120.00 |
| 123 | tax before refundable credits | 2026 | `taxsim` | 240.00 |

### `taxsim-no-tax-exempt-interest-input`: TAXSIM has no input for tax-exempt interest

*Kind* `model-no-provision`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM has no input for tax-exempt interest, so the Social Security taxability test leaves it out of modified AGI and TAXSIM taxes less of the benefits.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 86(b)(2)(B) (modified AGI for taxing Social Security includes tax-exempt interest). **Figure:** base amount $25,000 and adjusted base amount $34,000 (single); 85% cap on the taxable part.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator: the stated tax-exempt interest raises the taxable part of Social Security.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-a.md (000: Tax-Calculator with e00400 0 gives TAXSIM's answer; TAXSIM with the law's taxable benefits entered gives the others'); evidence/traces/trace-taxsim-b.md (122); evidence/taxsim.md (P15.5).
- **Source:** evidence/traces/trace-taxsim-a.md, evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 000 | tax before refundable credits | 2026 | `taxsim` | -568.99 |
| 000 | tax before refundable credits | 2025 | `taxsim` | -568.99 |
| 122 | tax before refundable credits | 2026 | `taxsim` | -128.49 |
| 122 | tax before refundable credits | 2025 | `taxsim` | -128.49 |

### `taxsim-no-blindness-input`: TAXSIM has no input for blindness

*Kind* `model-no-provision`. *Moves* `taxsim`. *Law years* both. *Entry* open.

The board states that 122's filer is blind; TAXSIM has no input for blindness, so its standard deduction lacks the additional amount. In 2025 TAXSIM itemizes instead, which narrows the gap.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 63(f)(2)(A) (additional standard deduction for a blind taxpayer); Rev. Proc. 2025-32 (2026 amount). **Figure:** $2,050 (single, 2026); $2,000 (2025).
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-b.md (122: Tax-Calculator with blind_head 0 moves by the same amount in each year).
- **Source:** evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 122 | tax before refundable credits | 2026 | `taxsim` | 246.00 |
| 122 | tax before refundable credits | 2025 | `taxsim` | 181.18 |

### `taxsim-no-savers-credit`: TAXSIM's test build gives no saver's credit

*Kind* `model-no-provision`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM's test build has no input for the retirement savings contributions credit, so its tax omits the credit. In 119 the missing credit also leaves more tax for the child tax credit to absorb, so less of the child credit is refundable. Tax-Calculator's credit here is this repo's figure (keycheck/statute.py), not Tax-Calculator's own.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 25B(a)-(d); IRS Notice 2025-67 (2026 AGI limits). **Figure:** 10% of up to $2,000 a person at AGI $26,250 to $40,250 (single) or $39,375 to $60,375 (head of household) in 2026.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator. In 091 the credit also turns on full-time student status (25B(c)(2)(B)), which the board does not state; the prompt rule makes an unstated status false, so the credit stands. policyengine-us gives no credit when the head is a full-time student (results/repro/board_experiments.txt).
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-a.md (070); evidence/traces/trace-taxsim-b.md (091, 119: Tax-Calculator with e07240 0); results/repro/board_experiments.txt (091 with the head a full-time student: 1,470.00 in place of 1,350.00).
- **Source:** evidence/traces/trace-taxsim-a.md, evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 070 | tax before refundable credits | 2026 | `taxsim` | 192.40 |
| 070 | tax before refundable credits | 2025 | `taxsim` | 192.40 |
| 091 | tax before refundable credits | 2026 | `taxsim` | 120.00 |
| 091 | tax before refundable credits | 2025 | `taxsim` | 120.00 |
| 119 | refundable credits | 2026 | `taxsim` | -200.00 |
| 119 | refundable credits | 2025 | `taxsim` | -200.00 |

### `taxsim-2026-child-care-credit-old-rates`: TAXSIM applies the pre-2026 child care credit rates to 2026

*Kind* `model-law-departure`. *Moves* `taxsim`. *Law years* 2026. *Entry* open.

For 2026 TAXSIM's test build computes the child and dependent care credit on the schedule in force before 2026 (20% at these incomes), not the amended one. In 119 the smaller credit leaves more tax for the child tax credit to absorb, so less of the child credit is refundable.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 21(a)(2) as amended by Pub. L. 119-21 sec. 70405 (taxable years after 2025). **Figure:** 50%, reduced 1 point per $2,000 of AGI above $15,000 to 35%, then 1 point per $2,000 ($4,000 joint) above $75,000 ($150,000 joint) to 20%: 32% of $6,000 for 099, 35% of $1,560 for 119.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-b.md (099, 119); evidence/taxsim.md (probe P5.2: joint AGI 160,000 gives 1,200 against the law's 1,920).
- **Source:** evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 099 | tax before refundable credits | 2026 | `taxsim` | 720.00 |
| 119 | refundable credits | 2026 | `taxsim` | -234.00 |

### `taxsim-refundable-child-credit-ignores-child-care-credit`: TAXSIM's refundable child credit ignores the child care credit

*Kind* `model-law-departure`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM's refundable child tax credit equals the child credit less the tax before any credit, as if the child care credit had used none of the tax. The law refunds the child credit left over after the child care credit and the other nonrefundable credits take their share.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 24(d)(1) (refundable part limited by the credit left after the section 26(a) limit). **Figure:** 2026: 4,400 - (3,056.23 - 546 - 200) = 2,089.77 refundable for 119.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator.
- **Existing report:** https://github.com/PolicyEngine/policyengine-taxsim/issues/1483.
- **Evidence:** evidence/traces/trace-taxsim-b.md (119: TAXSIM's refundable credit does not move when child care falls to 0; Tax-Calculator ladder); evidence/taxsim.md (probes P3.7, P5.3).
- **Source:** evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 119 | refundable credits | 2026 | `taxsim` | -312.00 |
| 119 | refundable credits | 2025 | `taxsim` | -312.00 |

### `taxsim-three-child-refundable-credit-alternative`: TAXSIM's three-child alternative counts the whole self-employment tax

*Kind* `model-law-departure`. *Moves* `taxsim`. *Law years* both. *Entry* open.

For a family with three or more children the law also allows a refundable child credit equal to the family's social security taxes (half of any self-employment tax) less the earned income credit. TAXSIM's test build counts the whole self-employment tax and does not subtract the earned income credit, so it refunds more than the 15% formula gives.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 24(d)(1)(B)(ii) and 24(d)(2)(A) (social security taxes: employee taxes under 3101 plus 50% of the 1401 tax); 24(h)(6). **Figure:** 15% x (27,880.57 - 2,500) = 3,807.09 for 109; the alternative, 0.5 x 4,238.86 - 8,231, falls below 0.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-b.md (109); probes/taxsim/actc_3kids_alt.in.csv and actc_3kids_alt.cd2026110117.out.csv (ids 1, 4, 11, 12).
- **Source:** evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 109 | refundable credits | 2026 | `taxsim` | 431.77 |
| 109 | refundable credits | 2025 | `taxsim` | 431.77 |

### `taxsim-2026-salt-cap-40000`: TAXSIM caps 2026 state and local taxes at $40,000

*Kind* `model-law-departure`. *Moves* `taxsim`. *Law years* 2026. *Entry* open.

TAXSIM's test build caps the 2026 state and local tax deduction at 2025's $40,000, not the law's $40,400, so an itemizer above the cap deducts $400 less.

- **Where it holds:** taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 164(b)(7)(A)(ii) and (B). **Figure:** $40,400 for 2026, reduced by 30% of modified AGI above $505,000 (not below $10,000).
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-a.md (078); probes/taxsim/trace_a_078_saltcap.in.csv and trace_a_078_saltcap.cd2026110117.out.csv (opt1 8, opt1v 40400 gives 24,164.46).
- **Source:** evidence/traces/trace-taxsim-a.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 078 | tax before refundable credits | 2026 | `taxsim` | 96.00 |

### `map-ira-deduction-in-nonprop-cuts-eitc`: The TAXSIM map's IRA deduction lowers earned income

*Kind* `map-limit`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM has no input for an adjustment that lowers AGI alone, so the map enters 100's IRA deduction (180.32) as negative nonprop, which this build also subtracts from earned income for the earned income credit. In the phase-in range that costs 40% of the deduction.

- **Where it holds:** keycheck 2026-11-10.2 (keycheck/map_taxsim.py) on taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 32(c)(2)(A) (earned income: wages and net earnings from self-employment; the 219 deduction does not reduce it). **Figure:** 40% x 2,055.72 = 822.29 for 100.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator. Entering the deduction where it moves only AGI (a negative short-term gain) gives TAXSIM 822.29 too.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-b.md (100: TAXSIM with nonprop 0 and stcg -180.32 gives 822.29); evidence/traces/fix-maps.md (kept as a noted limit).
- **Source:** evidence/traces/trace-taxsim-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 100 | refundable credits | 2026 | `taxsim` | -72.13 |
| 100 | refundable credits | 2025 | `taxsim` | -72.13 |

### `map-rental-not-qualified-business-income`: The maps treat rent as income outside a trade or business

*Kind* `map-limit`. *Moves* `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

The maps read stated rent as income that is not qualified business income, so Tax-Calculator and TAXSIM allow no 20% deduction on it. policyengine-us counts rent as qualified business income unless told otherwise (rental_income_would_be_qualified defaults to true) and deducts 20% of it.

- **Where it holds:** keycheck 2026-11-10.2 (READINGS rental_qbi in keycheck/unit.py; rent to e02000 in Tax-Calculator, to intrec in TAXSIM).
- **Law:** 26 U.S.C. 199A(c)(3)(A)(i) and (d)(1) (qualified business income comes from a qualified trade or business); 199A(b)(2)(B)(ii) and (b)(6) (unadjusted basis of qualified property: depreciable property held for use in the qualified trade or business). **Figure:** 20% of qualified business income: 910.00 (022), 800.00 (076).
- **Who is right (this entry's position):** policyengine-us, on this entry's position. The board does not say outright that either rental is a trade or business, but it states unadjusted basis of qualified property for both filers (24,786.06 for 022, 49,921.10 for 076), a figure that exists only for property of a qualified trade or business, and rent is each filer's only business-type income. A reader who applies the prompt rule (an unstated status is false) to the trade-or-business question without weighing the stated basis would side with Tax-Calculator and TAXSIM.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-a.md (022: Tax-Calculator with the rent in e26270, TAXSIM with it in scorp, each give policyengine-us's answer); evidence/traces/trace-pe-b.md (076; the trace does not mention the stated basis); results/repro/board_experiments.txt (076 and results/repro/board_experiments_2.txt 022: rental_income_would_be_qualified false gives Tax-Calculator's answer); policyengine_us/variables/household/income/person/misc/rental_income_would_be_qualified.py:13; policyengine_us/parameters/gov/irs/deductions/qbi/income_definition.yaml:8; policyengine_us/variables/gov/irs/income/taxable_income/deductions/qualified_business_income_deduction/qualified_business_income.py:22-25; results/dossiers/scenario_022.json and scenario_076.json (stated unadjusted_basis_qualified_property).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-pe-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 022 | tax before refundable credits | 2026 | `taxcalc` | 200.20 |
| 022 | tax before refundable credits | 2026 | `taxsim` | 200.20 |
| 022 | tax before refundable credits | 2025 | `taxcalc` | 200.20 |
| 022 | tax before refundable credits | 2025 | `taxsim` | 200.20 |
| 076 | tax before refundable credits | 2026 | `taxcalc` | 192.00 |
| 076 | tax before refundable credits | 2026 | `taxsim` | 192.00 |
| 076 | tax before refundable credits | 2025 | `taxcalc` | 192.00 |
| 076 | tax before refundable credits | 2025 | `taxsim` | 192.00 |

### `pe-other-dependent-credit-without-dependency-tests`: policyengine-us pays the other-dependent credit without the dependency tests

*Kind* `model-law-departure`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

policyengine-us pays the $500 credit for other dependents for every member of the tax unit who is not the head or spouse, testing only identification. It does not apply the qualifying-relative gross income test or the disability rule that lets an adult be a qualifying child. 093's dependent1 is 27 and earns $45,000 of wages, and the board states that dependent1 is disabled; the engine pays the credit, and pays the same $500 when is_disabled is false.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (ctc_adult_individual_maximum.py identical; is_tax_unit_dependent.py differs only in its docstring).
- **Law:** 26 U.S.C. 24(h)(4) ($500 for each dependent as defined in 152 other than a qualifying child); 152(d)(1)(B) (a qualifying relative's gross income must fall below the exemption amount); 152(c)(3)(B) and 22(e)(3) (a permanently and totally disabled child meets the age test; 22(e)(3) requires inability to engage in any substantial gainful activity). **Figure:** $500; exemption amount $5,300 (2026, Rev. Proc. 2025-32 sec. 4.23) and $5,200 (2025, Rev. Proc. 2024-40 sec. 2.24).
- **Who is right (this entry's position):** Tax-Calculator and TAXSIM, on this entry's position. With $45,000 of wages dependent1 fails the gross income test, and a year of wages at that level is work that 22(e)(3) disability rules out (an inference: this entry did not consult the regulations on substantial gainful activity), so the stated 'is disabled' does not make dependent1 a qualifying child; dependent1 is not the filer's dependent, and no $500 credit follows.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-b.md (093); results/repro/board_experiments.txt (093 on 2.60.0 and 2.116.15: is_disabled false still pays 500); results/repro/repro_pe_2.60.0.txt and repro_pe_2.116.15.txt (credit for other dependents with no gross income test); policyengine_us/variables/gov/irs/credits/ctc/maximum/individual/ctc_adult_individual_maximum.py:13,21-40; policyengine_us/variables/household/demographic/tax_unit/is_tax_unit_dependent.py:10-13.
- **Source:** evidence/traces/trace-pe-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 093 | tax before refundable credits | 2026 | `policybench-key` | -500.00 |
| 093 | tax before refundable credits | 2026 | `policyengine-us` | -500.00 |
| 093 | tax before refundable credits | 2025 | `policyengine-us` | -500.00 |

### `pe-divorce-year-default`: policyengine-us dates an unstated divorce to 2010

*Kind* `pe-default-unstated-fact`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

020 pays $5,708.82 of alimony; the board does not state when the parties executed the divorce or separation instrument. policyengine-us fills the date with its default divorce year, 2010, and deducts the alimony; Tax-Calculator and TAXSIM treat every instrument as executed after 2018, so neither deducts it.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (divorce_year.py identical); the key's frozen 1.755.4 value.
- **Law:** 26 U.S.C. 215, repealed by Pub. L. 115-97 sec. 11051 for divorce or separation instruments executed after December 31, 2018 (earlier instruments keep the deduction).
- **Who is right (this entry's position):** No answer is right until the board states the instrument's date. The deduction needs a fact (an instrument executed before 2019); the prompt rule makes an unstated fact false, so the rule points to no deduction: Tax-Calculator's and TAXSIM's answers. policyengine-us with divorce_year 2019 gives 70,332.82, Tax-Calculator's answer.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-a.md (020: Tax-Calculator deducting alimony gives policyengine-us's answer); results/repro/board_experiments_2.txt (divorce_year 2019); policyengine_us/variables/household/demographic/person/divorce_year.py:9; policyengine_us/variables/gov/irs/income/taxable_income/adjusted_gross_income/above_the_line_deductions/alimony_expense_ald_person.py:21-24.
- **Source:** evidence/traces/trace-pe-a.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 020 | tax before refundable credits | 2026 | `policybench-key` | -1,998.09 |
| 020 | tax before refundable credits | 2026 | `policyengine-us` | -1,998.09 |
| 020 | tax before refundable credits | 2025 | `policyengine-us` | -1,998.09 |

### `pe-medicare-part-b-premium-default`: policyengine-us adds a Medicare premium the household does not state

*Kind* `pe-default-unstated-fact`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

114's filer is 69 and itemizes medical expenses; the board states no Medicare enrollment or premium. policyengine-us assumes an eligible person takes up Medicare and adds twelve months of the standard Part B premium (2,434.80 in 2026, 2,220.00 in 2025) to medical expenses.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (both give 11,265.27 without the take-up).
- **Law:** 26 U.S.C. 213(a) (medical care paid above 7.5% of AGI) and 213(d)(1)(D) (Part B premiums paid are medical care).
- **Who is right (this entry's position):** No answer is right until the board states Medicare enrollment and the premium paid. The prompt says not to infer unlisted health coverage and to treat an unlisted amount as 0, so the rule points to no premium: Tax-Calculator's and TAXSIM's answers. The prompt also says to assume program take-up when required; this entry reads the specific instruction on health coverage as governing a premium the household would have to pay. policyengine-us with takes_up_medicare_if_eligible false gives 11,265.27 on both releases.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-b.md (114: Tax-Calculator with the premium added gives policyengine-us's answer); results/repro/board_experiments.txt (114, 2.60.0 and 2.116.15); policyengine_us/variables/household/expense/health/medical_expense_health_insurance_premiums.py:25-28; policyengine_us/variables/gov/hhs/medicare/takes_up_medicare_if_eligible.py:9.
- **Source:** evidence/traces/trace-pe-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 114 | tax before refundable credits | 2026 | `policybench-key` | -535.66 |
| 114 | tax before refundable credits | 2026 | `policyengine-us` | -535.66 |
| 114 | tax before refundable credits | 2025 | `policyengine-us` | -488.40 |

### `pe-net-investment-income-leaves-out-farm-rent`: policyengine-us 2.60.0 leaves farm rent out of net investment income

*Kind* `model-law-departure`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

policyengine-us 2.60.0 leaves Form 4835 farm rent out of net investment income, so 120's farm rent loss (2,446.59) does not offset its rent and interest, and the net investment income tax comes to 163.40 in place of 70.43.

- **Where it holds:** policyengine-us 2.60.0 (and the key's frozen 1.755.4 value). **Fixed in:** policyengine-us 2.116.15 (farm_rent_income in gov.irs.investment.income.sources).
- **Law:** 26 U.S.C. 1411(c)(1)(A)(i) (gross income from rents) and (c)(1)(B) (deductions properly allocable to it). **Figure:** 3.8% of net investment income 1,853.41 = 70.43.
- **Who is right (this entry's position):** Tax-Calculator, TAXSIM and policyengine-us 2.116.15. Adding farm_rent_income to 2.60.0's sources gives 40,330.21, their answer.
- **Existing report:** https://github.com/PolicyEngine/policyengine-us/issues/10075.
- **Evidence:** evidence/traces/trace-pe-b.md (120); results/repro/board_experiment_120_rerun.txt; policyengine_us/parameters/gov/irs/investment/income/sources.yaml:8-27 (2.60.0, no farm_rent_income) and :23 at 2.116.15; PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions[17]: the 1.755.4-to-2.15.17 move for 120 is the IRA and #9122 alone, so the frozen value carries the same omission: inference).
- **Source:** evidence/traces/trace-pe-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 120 | tax before refundable credits | 2026 | `policybench-key` | 92.97 |
| 120 | tax before refundable credits | 2026 | `policyengine-us` | 92.97 |
| 120 | tax before refundable credits | 2025 | `policyengine-us` | 92.97 |

### `key-ira-deducted-without-219g`: The key deducts IRA contributions without the active-participant limit

*Kind* `key-decided-value`. *Moves* `policybench-key`. *Law years* 2026. *Entry* open.

The frozen 1.755.4 values deduct traditional IRA contributions with no active-participant phase-out. Each filer defers wages into a 401(k), so is an active participant, and modified AGI exceeds the range, so the law allows no IRA deduction.

- **Where it holds:** the committed key: policyengine-us 1.755.4 values the board froze on 2026-09-22. **Fixed in:** the engine applies 219(g) by 2.38.6 (the board's recheck gives the corrected value; 2.60.0 has ira_active_participant.py and ira_219g_deductible_limit.py); the key keeps the frozen value.
- **Law:** 26 U.S.C. 219(g) (active-participant phase-out; 219(g)(5)(A) active participant); IRS Notice 2025-67 (2026 ranges). **Figure:** no deduction above $149,000 (joint) or $91,000 (single) of modified AGI in 2026.
- **Who is right (this entry's position):** policyengine-us 2.60.0, Tax-Calculator and TAXSIM. The board excludes these outputs and names the defect in its own records.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-a.md (005, 052: Tax-Calculator with the contribution deducted gives the key); evidence/traces/trace-pe-b.md (120); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json (root cause r02_ira_219g); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions 17-20).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-pe-b.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 005 | tax before refundable credits | 2026 | `policybench-key` | -692.44 |
| 052 | tax before refundable credits | 2026 | `policybench-key` | -13.85 |
| 120 | tax before refundable credits | 2026 | `policybench-key` | -6.50 |

### `key-sales-tax-table-column-shift`: The key holds a shifted sales tax table

*Kind* `key-decided-value`. *Moves* `policybench-key`. *Law years* 2026. *Entry* open.

1.755.4's optional sales tax table held a neighbouring state's values (a column shift), so 020's frozen value deducts a different sales tax amount. The board's own recheck attributes the whole 278.02 to the corrected table. Tax-Calculator and TAXSIM take the corrected amount from the engine run.

- **Where it holds:** the committed key: policyengine-us 1.755.4 value. **Fixed in:** policyengine-us #9616 (3f029abf5b, 2026-09-27), in 2.15.17 and later.
- **Law:** 26 U.S.C. 164(b)(5)(A) and (H) (election to deduct general sales taxes; amount under the IRS tables).
- **Who is right (this entry's position):** policyengine-us 2.60.0 (on the shared sales tax amount, which Tax-Calculator and TAXSIM also use). The 1.755.4 sales tax figure is not in the dossier; the size rests on the board's record and the 278.02 difference.
- **Existing report:** https://github.com/PolicyEngine/policyengine-us/issues/9595.
- **Evidence:** evidence/traces/trace-pe-a.md (020, reconciliation C); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions[17], scenario_020: 'comes only from #9616').
- **Source:** evidence/traces/trace-pe-a.md.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 020 | tax before refundable credits | 2026 | `policybench-key` | -278.02 |

### `shared-state-tax-refund-counted-in-full`: A state tax refund counts in full as income

*Kind* `shared-reading`. *Moves* `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

A listed state or local tax refund counts in full as income in policyengine-us (which documents the input as the taxable refund on Schedule 1, line 1) and, through this repo's reading, in Tax-Calculator and TAXSIM. The key's frozen 1.755.4 values for 005 and 120 never counted the input, so those two cells move three answers and not the key; elsewhere every answer counts it.

- **Where it holds:** policyengine-us 2.15.17 and later (policyengine-us#9422, which fixed issue #9122), and the key's values that the board froze on 2.15.17; Tax-Calculator and TAXSIM through READINGS salt_refund_income (keycheck 2026-11-10.2).
- **Law:** 26 U.S.C. 111(a) (a recovery is income only to the extent the earlier deduction reduced tax).
- **Who is right (this entry's position):** No answer is right until the board states the prior year's facts: whether the household itemized and deducted the refunded tax. The prompt rule makes that unstated fact false, so none of the refund is income (the board's own alternative reading). On that reading the key's frozen values for 005 and 120 hold the refund correctly, and 082's scored answer would fall by 14.85.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** PolicyEngine/policybench@c7ede86c:reference_audit/2026-09-28/fixes/latest_alt_salt_refund_no_prior_benefit.py:1-30; PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions[17]: 005 '+$1,327.26 move is #9122 alone', 120 '+$394.85 move is #9122 alone'); results/repro/board_experiments_2.txt (005 salt_refund_income 0: 107,198.34); counterfactual runs on the inputs in results/dossiers (Tax-Calculator 005 with e00700 0: 107,198.33; 082: 9,564.92; TAXSIM 005 with pensions less the refund: 107,540.65, above the engine's 107,198.34 by the 170(p) deduction TAXSIM lacks; 120, both models with the refund out and the shared state and local tax lowered by the 113.77 the board records for the engine's Connecticut estimate: 39,935.35).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-pe-b.md, evidence/traces/trace-taxsim-a.md.
- **Households where every answer moves alike (no cell rows):** 033, 074, 078, 082, 088, 117, 005 (2025 table only), 120 (2025 table only).

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 005 | tax before refundable credits | 2026 | `policyengine-us` | 1,327.24 |
| 005 | tax before refundable credits | 2026 | `taxcalc` | 1,327.25 |
| 005 | tax before refundable credits | 2026 | `taxsim` | 1,327.26 |
| 120 | tax before refundable credits | 2026 | `policyengine-us` | 394.86 |
| 120 | tax before refundable credits | 2026 | `taxcalc` | 394.86 |
| 120 | tax before refundable credits | 2026 | `taxsim` | 394.86 |

### `shared-disability-benefits-taxable`: Disability benefits count as income

*Kind* `shared-reading`. *Moves* `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

policyengine-us, Tax-Calculator and TAXSIM tax stated disability benefits in full. The key's frozen 1.755.4 values for 002, 107 and 121 leave them out, so those three cells move three answers and not the key.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (taxable_disability_benefits in gross income; tax_exempt_disability_benefits defaults to 0); Tax-Calculator and TAXSIM through READINGS disability_benefits.
- **Law:** 26 U.S.C. 104(a)(3) (amounts received through accident or health insurance excluded) and 105(a) (included to the extent attributable to employer contributions not included in the employee's income, or paid by the employer).
- **Who is right (this entry's position):** No answer is right until the board states who paid for the coverage. The law includes the benefits only on a fact (employer contributions or payment); the prompt rule makes that unstated fact false, so 104(a)(3) excludes the benefits: the key's frozen 0.00. The board excludes all three outputs (reference_depends_on_unlisted_input). In 057 and 084 the households owe 0 either way; 067's benefits are a dependent's own.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-a.md (002: Tax-Calculator without the benefits gives 0.00); evidence/traces/trace-pe-b.md (107, 121: Tax-Calculator and TAXSIM without them give 0.00); a TAXSIM counterfactual run on 002 without them: 0.00; policyengine_us/variables/household/income/person/general/taxable_disability_benefits.py:21-24; PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json.
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-pe-b.md.
- **Households where every answer moves alike (no cell rows):** 057, 067, 084, 002 (2025 table only), 107 (2025 table only), 121 (2025 table only).

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 002 | tax before refundable credits | 2026 | `policyengine-us` | 1,890.30 |
| 002 | tax before refundable credits | 2026 | `taxcalc` | 1,890.30 |
| 002 | tax before refundable credits | 2026 | `taxsim` | 1,890.30 |
| 107 | tax before refundable credits | 2026 | `policyengine-us` | 211.23 |
| 107 | tax before refundable credits | 2026 | `taxcalc` | 211.23 |
| 107 | tax before refundable credits | 2026 | `taxsim` | 211.23 |
| 121 | tax before refundable credits | 2026 | `policyengine-us` | 875.34 |
| 121 | tax before refundable credits | 2026 | `taxcalc` | 875.34 |
| 121 | tax before refundable credits | 2026 | `taxsim` | 875.34 |

### `shared-scholarship-not-income`: A stated scholarship stays out of income

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

068's filer, 31 and earning $34,083.53, lists $73,000 of educational assistance (scholarships and grants). Every answer leaves it out of income.

- **Where it holds:** policyengine-us 2.60.0 (educational_assistance has no federal effect); keycheck READINGS educational_assistance.
- **Law:** 26 U.S.C. 117(a) and (b) (the exclusion covers a qualified scholarship only for a degree candidate and only to the extent the student uses it for qualified tuition and related expenses).
- **Who is right (this entry's position):** Under the prompt rule the whole amount is income: degree candidacy and tuition are unstated (the board's prompt cannot list tuition), so the exclusion's conditions are false. On that reading 068's scored answer would be 14,728.38 (Tax-Calculator with the amount as income) in place of 1,910.02. 030's $5,000 changes nothing: its filer owes 0 either way.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F2); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_068.json with e01400 raised by 73,000: 14,728.38 (2026), 15,007.38 (2025).
- **Source:** evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 068, 030.

### `shared-financial-assistance-gift`: Help from outside the household counts as a gift

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

Six households list financial assistance from friends or relatives outside the household; every answer leaves it out of income.

- **Where it holds:** policyengine-us 2.60.0; keycheck READINGS financial_assistance.
- **Law:** 26 U.S.C. 102(a) (gifts excluded from gross income).
- **Who is right (this entry's position):** All four: policyengine-us documents the input as cash assistance from friends or relatives outside the household, which is a gift. No answer moves.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F6); keycheck/unit.py READINGS financial_assistance.
- **Source:** evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 029, 030, 056, 080, 090, 112.

### `shared-disabled-member-qualifying-child`: A member the board calls disabled counts as a qualifying child

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

The board states that 067's dependent1 (23) and 064's dependent1 (27) are disabled, and neither has earnings. The maps read each as permanently and totally disabled, so a qualifying child at any age and a dependent for the $500 credit. policyengine-us claims both as dependents without testing disability.

- **Where it holds:** keycheck 2026-11-10.2 READINGS is_disabled; policyengine-us 2.60.0 claims the member by another route (pe-other-dependent-credit-without-dependency-tests).
- **Law:** 26 U.S.C. 152(c)(3)(B) and 22(e)(3); 152(d)(1)(B); 24(h)(4). **Figure:** $500 credit for other dependents.
- **Who is right (this entry's position):** All four on 067's scored answer (5,616.24), by either reading: as a disabled qualifying child, or, if 'is disabled' falls short of 22(e)(3), as a qualifying relative, since under the prompt rule the member's disability benefits are not income (shared-disability-benefits-taxable), which leaves the member's gross income at 0, below the exemption amount. 064 is a qualifying relative either way; the reading moves only its earned-income-credit child count, and no credit arises at its income.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F1); evidence/traces/trace-pe-a.md (067); evidence/traces/fix-maps.md (reading 1, 067 moved to all_agree).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 064, 067.

### `shared-net-investment-income-tax-in-line`: The line includes the net investment income tax

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

Every answer here includes the 3.8% tax on net investment income in the line 'federal tax before refundable credits'.

- **Where it holds:** policyengine-us income_tax_before_refundable_credits; this repo's line definitions (scripts/run_taxcalc.py, scripts/run_taxsim.py docstrings).
- **Law:** 26 U.S.C. 1411(a)(1) (the net investment income tax).
- **Who is right (this entry's position):** The output's text does not decide it: it reads 'federal individual income tax after nonrefundable credits and before refundable credits' and does not say whether the 1411 tax is in it. The board excludes 020 for this reason (r25) and names it on 005, 052 and 120; no scored output in the board's 100 has a net investment income tax.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** PolicyEngine/policybench@c7ede86c:policybench/benchmark_specs.json (output prompt); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (scenario_020: 'depends on whether federal income tax before refundable credits includes the net investment income tax'); results/dossiers (net_investment_income_tax above 0 only for 005, 020, 052, 120).
- **Source:** evidence/traces/trace-pe-a.md.
- **Households where every answer moves alike (no cell rows):** 005, 020, 052, 120.

### `shared-state-income-tax-withholding-estimate`: State income tax comes from a withholding estimate

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

The board states no state income tax withheld or paid. Every answer here uses the engine's AGI-formula estimate of state income tax withheld as the state income tax part of the state and local tax deduction; the three models share one amount, so they cannot disagree on it. It can move an answer only where the household itemizes and the estimate exceeds the sales tax amount: 022, 072, 078, 081, 114 and 120 in both years, and 117 and 121 in 2025 (policyengine-us's 2.60.0 runs in results/dossiers).

- **Where it holds:** policyengine-us 2.60.0 state_withheld_income_tax (the board's convention), passed to Tax-Calculator (e18400) and TAXSIM (proptax) from results/shared.
- **Law:** 26 U.S.C. 164(a)(3) and (b)(5) (state and local income taxes paid, or general sales taxes in their place); 164(b)(7) (cap).
- **Who is right (this entry's position):** No answer is right until the board states the state income tax paid in the year. The prompt rule would make an unstated amount paid 0, which leaves the election to deduct general sales taxes. The board's exclusion records for 022, 081 and 114 name this reading, and its record for 120 gives the answer under the engine's own Connecticut liability and with no state income tax paid. policyengine-us 2.116.15, which no table here uses, takes a different amount for 121 (549.00 against 2.60.0's 658.80) and gives 886.32 in place of 875.34.
- **Existing report:** https://github.com/PolicyEngine/policyengine-us/issues/9837.
- **Evidence:** PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json (022, 081, 114: 'The prompt lists no state income tax withheld or paid during 2026'); evidence/traces/verify-map-taxsim.md (F13: itemizers); results/shared/.
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/verify-map-taxsim.md.
- **Households where every answer moves alike (no cell rows):** 022, 072, 078, 081, 114, 120, 117 (2025 table only), 121 (2025 table only).

### `shared-state-paid-leave-contributions-not-in-salt`: Connecticut paid leave contributions stay out of the state and local tax deduction

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

120 itemizes, and the engine computes 827.98 of Connecticut paid leave contributions on the stated wages; the shared state and local tax amount leaves them out, so every answer does.

- **Where it holds:** policyengine-us 2.60.0 SALT (employee_state_payroll_tax left out), shared with Tax-Calculator and TAXSIM.
- **Law:** 26 U.S.C. 164(a)(3); Rev. Rul. 2025-4 (mandatory employee contributions to a state paid family and medical leave fund, withheld from wages, are state income taxes deductible under 164(a)(3)).
- **Who is right (this entry's position):** None of the four: the law counts the contributions in the deduction. Tax-Calculator with them added gives 40,131.49, 198.72 less (a counterfactual run); the board's record gives 40,217.95 on 2.15.17. The board excludes 120.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-b.md (120, shared points); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (scenario_120 note); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_120.json with e18400 raised by 827.98.
- **Source:** evidence/traces/trace-pe-b.md.
- **Households where every answer moves alike (no cell rows):** 120.

### `shared-passive-rental-loss-allowed`: A passive rental loss reduces income

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

120's two rental activities, rent of 2,000 and a Form 4835 farm rent loss of 2,446.59, net to a 446.59 loss, which every answer deducts.

- **Where it holds:** policyengine-us 2.60.0 (no 469 limit), Tax-Calculator 6.9.0, TAXSIM cd2026110117 as mapped.
- **Law:** 26 U.S.C. 469(a) (passive activity loss disallowed), 469(c)(2) (a rental activity is passive), 469(i)(3)(A) (the $25,000 allowance falls by 50% of AGI above $100,000). **Figure:** allowance 0 at AGI 234,414.
- **Who is right (this entry's position):** None of the four: at this AGI the law suspends the net passive loss, absent other passive income or real estate professional status, which the board does not state and the prompt rule makes false. Tax-Calculator with the loss suspended gives 40,454.90 (+124.69, a counterfactual run); the board's record gives +24.75 on 2.15.17, a gap this entry does not examine. The board excludes 120.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-b.md (120, shared points); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (scenario_120: 'the engine's missing 469 limit'); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_120.json with e02000 0 and e27200 -2,000 (the rent kept, the loss suspended).
- **Source:** evidence/traces/trace-pe-b.md.
- **Households where every answer moves alike (no cell rows):** 120.

### `shared-mortgage-debt-after-2017`: Mortgage debt counts as incurred after 2017

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

049 and 120 state mortgage balances above $750,000 and no origination date; every answer limits interest to the $750,000 of acquisition debt that applies to debt incurred after December 15, 2017.

- **Where it holds:** policyengine-us 2.60.0; keycheck READINGS mortgage_date.
- **Law:** 26 U.S.C. 163(h)(3)(F)(i)(II) and (IV). **Figure:** $750,000 limit; $1,000,000 for debt incurred on or before December 15, 2017.
- **Who is right (this entry's position):** All four, under the prompt rule: the higher limit needs a fact (debt incurred before December 16, 2017) that the rule makes false. The board's record gives -224.64 for 120 if the debt were older; 049 takes the standard deduction either way.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F8); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (scenario_120 note).
- **Source:** evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 049, 120.

### `shared-head-return-only`: The line covers the head's return only

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

Every answer here computes the return of the head (and spouse). A listed member with income of their own who files their own return (123's 16-year-old with $45,000 of wages; 093's dependent1 under this repo's position on the credit) adds that return's tax only if the line covers every return in the household.

- **Where it holds:** policyengine-us 2.60.0 (one tax unit; dependents' own income stays out of the filer's AGI); keycheck (the head's return only).
- **Law:** the board's output definition (aggregation 'sum' of income_tax_before_refundable_credits; benchmark_specs.json) and prompt ('one household group for tax and benefit calculations', prompts.py:15-27).
- **Who is right (this entry's position):** Neither the output's text nor the stated facts decide it. The board excludes both outputs (household_scope_dependent_returns); its alternative adds 3,220.00 for 123, which a TAXSIM run of the child's own return reproduces.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json (093, 123); evidence/traces/trace-taxsim-b.md (123: TAXSIM of the child's return gives 3,220.00); PolicyEngine/policybench@c7ede86c:policybench/benchmark_specs.json.
- **Source:** evidence/traces/trace-pe-b.md, evidence/traces/trace-taxsim-b.md.
- **Households where every answer moves alike (no cell rows):** 093, 123.

### `shared-bdc-income-not-added`: BDC income stays out of income

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

042 lists 70.94 of 'qualified BDC income' beside its stated dividends. No answer adds it to income.

- **Where it holds:** policyengine-us 2.60.0 (qualified_bdc_income read by no formula); keycheck READINGS qualified_bdc_income.
- **Law:** 26 U.S.C. 61(a)(7) (dividends are gross income).
- **Who is right (this entry's position):** No answer is right until the board says whether the amount sits inside the stated dividends; the prompt rule does not decide whether one listed amount repeats another. As extra ordinary dividends it would raise 042's scored answer to 2,377.71 (Tax-Calculator counterfactual run; +15.74).
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F6); evidence/traces/fix-maps.md (no formula reads qualified_bdc_income); Tax-Calculator counterfactual run on the inputs in results/dossiers/scenario_042.json with e00600 raised by 70.94.
- **Source:** evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 042.

### `shared-survivor-benefits-not-taxable`: Survivor benefits stay out of income

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

062 and 108 list survivor benefits other than Social Security (28,800 and 10,392); every answer leaves them out of income.

- **Where it holds:** the board's reference reading; keycheck READINGS survivor_benefits.
- **Law:** 26 U.S.C. 61(a) and 72 (a survivor annuity is income); 101(a) (life insurance proceeds paid by reason of death excluded).
- **Who is right (this entry's position):** Under the prompt rule the benefits are income: the exclusion needs a fact (life insurance proceeds) that the rule makes false. 062's answer would be 4,328.39, the board's alternative (the board excludes 062); 108 owes 0 either way (Tax-Calculator counterfactual runs).
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F12); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json (062); Tax-Calculator counterfactual runs on the inputs in results/dossiers/scenario_062.json and scenario_108.json with the benefits added to e01500 and e01700.
- **Source:** evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 062, 108.

### `shared-over-the-counter-not-medical`: Over-the-counter expenses stay out of medical expenses

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

Households list over-the-counter health expenses; every answer leaves them out of itemized medical expenses. The reading can move an answer only for a household that itemizes, has medical expenses above 7.5% of AGI and owes tax: 114 and 121 (016 and 072 itemize such expenses and owe 0 either way).

- **Where it holds:** policyengine-us 2.60.0; keycheck READINGS over_the_counter.
- **Law:** 26 U.S.C. 213(b) (a medicine or drug counts only if prescribed or insulin) and 213(d)(1).
- **Who is right (this entry's position):** All four, under the prompt rule: the board does not describe the amounts as prescribed drugs, insulin or other medical care. The board excludes 114 and 121.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F10); keycheck/unit.py READINGS over_the_counter.
- **Source:** evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 016, 072, 114, 121.

## Cells that are not all_agree in the 2026 key table

Each row is a household and line of `results/agreement/board100_2026_key.csv` whose answers differ by more than $1. "Scored" says whether the board scores the output (it excludes the rest). The policyengine-us column comes from the rerun table, `results/agreement/board100_2026_rerun.csv`. The last column lists each cause with the amount it adds to each answer it moves in the 2026 table (key, policyengine-us, Tax-Calculator, TAXSIM).

| Case | Line | Class | Scored | Key | policyengine-us 2.60.0 | Tax-Calculator | TAXSIM | Causes and amounts |
|---|---|---|---|---:|---:|---:|---:|---|
| 000 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 2,906.45 | 2,906.45 | 2,906.45 | 2,337.46 | `taxsim-no-tax-exempt-interest-input` (ts -568.99) |
| 002 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 0.00 | 1,890.30 | 1,890.30 | 1,890.30 | `shared-disability-benefits-taxable` (pe 1,890.30, tc 1,890.30, ts 1,890.30) |
| 005 | federal_income_tax_before_refundable_credits | all_differ | no | 106,505.90 | 108,525.58 | 108,525.58 | 108,867.91 | `taxsim-no-nonitemizer-charitable-deduction` (ts 342.33); `key-ira-deducted-without-219g` (key -692.44); `shared-state-tax-refund-counted-in-full` (pe 1,327.24, tc 1,327.25, ts 1,327.26) |
| 020 | federal_income_tax_before_refundable_credits | all_differ | no | 68,056.71 | 68,334.73 | 70,332.82 | 70,401.42 | `taxsim-no-nonitemizer-charitable-deduction` (ts 68.60); `pe-divorce-year-default` (key -1,998.09, pe -1,998.09); `key-sales-tax-table-column-shift` (key -278.02) |
| 022 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 11,113.57 | 11,113.57 | 11,313.77 | 11,313.77 | `map-rental-not-qualified-business-income` (tc 200.20, ts 200.20) |
| 037 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 1,649.25 | 1,649.25 | 1,649.25 | 2,804.73 | `taxsim-no-overtime-deduction` (ts 1,155.48) |
| 046 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 499.71 | 499.71 | 499.71 | 2,280.36 | `taxsim-no-overtime-deduction` (ts 1,780.65) |
| 049 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 30,702.59 | 30,702.59 | 30,702.59 | 36,330.14 | `taxsim-no-overtime-deduction` (ts 5,500.00); `taxsim-no-nonitemizer-charitable-deduction` (ts 127.55) |
| 052 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 104,211.41 | 104,225.26 | 104,225.25 | 104,225.25 | `key-ira-deducted-without-219g` (key -13.85) |
| 055 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 25,238.58 | 25,238.58 | 25,238.58 | 25,478.58 | `taxsim-no-nonitemizer-charitable-deduction` (ts 240.00) |
| 064 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 4,441.46 | 4,441.46 | 4,441.45 | 6,109.37 | `taxsim-no-overtime-deduction` (ts 1,667.91) |
| 070 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 1,979.96 | 1,979.96 | 1,979.96 | 2,172.36 | `taxsim-no-savers-credit` (ts 192.40) |
| 076 | federal_income_tax_before_refundable_credits | two_agree:policyengine | yes | 19,611.80 | 19,611.80 | 19,803.80 | 19,803.80 | `map-rental-not-qualified-business-income` (tc 192.00, ts 192.00) |
| 078 | federal_income_tax_before_refundable_credits | two_agree:taxsim | no | 24,164.46 | 24,164.46 | 24,164.46 | 24,260.46 | `taxsim-2026-salt-cap-40000` (ts 96.00) |
| 082 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 9,579.77 | 9,579.77 | 9,579.77 | 9,733.77 | `taxsim-no-nonitemizer-charitable-deduction` (ts 154.00) |
| 089 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 6,819.71 | 6,819.71 | 6,819.71 | 7,235.80 | `taxsim-no-overtime-deduction` (ts 416.09) |
| 091 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 1,350.00 | 1,350.00 | 1,350.00 | 1,545.35 | `taxsim-no-overtime-deduction` (ts 75.35); `taxsim-no-savers-credit` (ts 120.00) |
| 093 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 8,628.99 | 8,628.99 | 9,128.99 | 9,128.99 | `pe-other-dependent-credit-without-dependency-tests` (key -500.00, pe -500.00) |
| 099 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 10,711.48 | 10,711.48 | 10,711.49 | 11,871.49 | `taxsim-no-nonitemizer-charitable-deduction` (ts 440.00); `taxsim-2026-child-care-credit-old-rates` (ts 720.00) |
| 107 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 0.00 | 211.23 | 211.23 | 211.23 | `shared-disability-benefits-taxable` (pe 211.23, tc 211.23, ts 211.23) |
| 110 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 25,747.77 | 25,747.77 | 25,747.77 | 25,840.76 | `taxsim-no-nonitemizer-charitable-deduction` (ts 92.99) |
| 114 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 10,729.61 | 10,729.61 | 11,265.27 | 11,265.27 | `pe-medicare-part-b-premium-default` (key -535.66, pe -535.66) |
| 117 | federal_income_tax_before_refundable_credits | two_agree:taxsim | no | 24,961.34 | 24,961.34 | 24,961.34 | 30,652.75 | `taxsim-no-overtime-deduction` (ts 5,602.67); `taxsim-no-nonitemizer-charitable-deduction` (ts 88.74) |
| 120 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 40,021.82 | 40,423.18 | 40,330.21 | 40,330.21 | `pe-net-investment-income-leaves-out-farm-rent` (key 92.97, pe 92.97); `key-ira-deducted-without-219g` (key -6.50); `shared-state-tax-refund-counted-in-full` (pe 394.86, tc 394.86, ts 394.86) |
| 121 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 0.00 | 875.34 | 875.34 | 875.34 | `shared-disability-benefits-taxable` (pe 875.34, tc 875.34, ts 875.34) |
| 122 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 4,746.66 | 4,746.66 | 4,746.66 | 4,984.17 | `taxsim-no-nonitemizer-charitable-deduction` (ts 120.00); `taxsim-no-tax-exempt-interest-input` (ts -128.49); `taxsim-no-blindness-input` (ts 246.00) |
| 123 | federal_income_tax_before_refundable_credits | two_agree:taxsim | no | 5,200.24 | 5,200.24 | 5,200.24 | 5,440.24 | `taxsim-no-nonitemizer-charitable-deduction` (ts 240.00) |
| 026 | federal_refundable_credits | two_agree:taxsim | yes | 2,013.49 | 2,013.49 | 2,013.49 | 1,083.94 | `taxsim-no-overtime-deduction` (ts -929.55) |
| 100 | federal_refundable_credits | two_agree:taxsim | yes | 822.29 | 822.29 | 822.29 | 750.16 | `map-ira-deduction-in-nonprop-cuts-eitc` (ts -72.13) |
| 109 | federal_refundable_credits | two_agree:taxsim | yes | 12,038.09 | 12,038.09 | 12,038.09 | 12,469.86 | `taxsim-three-child-refundable-credit-alternative` (ts 431.77) |
| 119 | federal_refundable_credits | two_agree:taxsim | yes | 3,366.07 | 3,366.07 | 3,366.07 | 2,620.08 | `taxsim-no-savers-credit` (ts -200.00); `taxsim-2026-child-care-credit-old-rates` (ts -234.00); `taxsim-refundable-child-credit-ignores-child-care-credit` (ts -312.00) |

## Causes that would change a scored answer

Two scored outputs hold a committed answer that, on the entries above, the law or the prompt rule does not support. Each proposal gives the answer that would follow; this repo changes nothing on the board, and every entry stays open.

| Case | Line | Committed key | Answer that would follow | Cause | How this repo got the answer |
|---|---|---:|---:|---|---|
| 068 | tax before refundable credits | 1,910.02 | 14,728.38 | `shared-scholarship-not-income` | Tax-Calculator counterfactual run with the $73,000 of educational assistance as ordinary income; this repo did not run policyengine-us on it |
| 082 | tax before refundable credits | 9,579.77 | 9,564.92 | `shared-state-tax-refund-counted-in-full` | Tax-Calculator counterfactual run with the $67.50 refund out of income (67.50 at 22% = 14.85) |

- **068.** The key's answer stands reproduced by a run of another lineage (Tax-Calculator and TAXSIM give it), and this account contests it: every run leaves the scholarship out of income, and the prompt rule makes the exclusion's conditions (degree candidacy, use for tuition) false.
- **082.** The key's answer stands reproduced by a run of another lineage (Tax-Calculator gives it), and this account contests it: the board's own alternative reading for its excluded refund outputs makes none of the refund income, and the board scores 082 on the other reading. TAXSIM, which also counts the refund, would fall by the same 14.85 and still exceed the others by the 154.00 of `taxsim-no-nonitemizer-charitable-deduction`.

### Scored answers that rest on an open reading

No proposal follows for these; each depends on a reading this account leaves open or decides for the key.

- **042** (2,361.96, reproduced by a run of another lineage): if the $70.94 of qualified BDC income sits outside the stated dividends, the answer would be 2,377.71 (`shared-bdc-income-not-added`).
- **076** (19,611.80, resting on one model, and contested between readings): the key and policyengine-us deduct 20% of the rent as qualified business income; Tax-Calculator and TAXSIM, through this repo's map, give 19,803.80. This account's position supports the key, on the stated unadjusted basis of qualified property (`map-rental-not-qualified-business-income`).
- **067** (5,616.24, reproduced by a run of another lineage): both readings of "is disabled" give the key's answer (`shared-disabled-member-qualifying-child`).
- The other scored cells that are not all_agree (000, 037, 046, 049, 055, 064, 070, 089, 091, 099, 110 and 122 on tax before refundable credits; 026, 100, 109 and 119 on refundable credits) hold a key answer reproduced by a run of another lineage (Tax-Calculator), and every entry that explains them supports the key: TAXSIM lacks a provision or departs from the law, or this repo's TAXSIM map cannot express a fact.

### Excluded outputs where an entry disputes the key

The board scores none of these, so no proposal follows; the list shows where the key and the entries part.

| Case | Committed key | Answer the entries support | Causes; what stays open |
|---|---:|---:|---|
| 005 | 106,505.90 | 107,198.34 | `key-ira-deducted-without-219g`; the board's own alternative. Open: `shared-net-investment-income-tax-in-line` |
| 020 | 68,056.71 | 70,332.82 | `pe-divorce-year-default` (no alimony deduction under the prompt rule), `key-sales-tax-table-column-shift`; Tax-Calculator's answer. Open: `shared-net-investment-income-tax-in-line`, on which the board excludes the output |
| 052 | 104,211.41 | 104,225.26 | `key-ira-deducted-without-219g`; the board's own alternative. Open: `shared-net-investment-income-tax-in-line` |
| 093 | 8,628.99 | 9,128.99 | `pe-other-dependent-credit-without-dependency-tests`, for the head's return. Open: `shared-head-return-only`, which would add the member's own return |
| 114 | 10,729.61 | 11,265.27 | `pe-medicare-part-b-premium-default`. Open: `shared-state-income-tax-withholding-estimate` |
| 120 | 40,021.82 | 39,935.35 | `key-ira-deducted-without-219g` (+6.50), `pe-net-investment-income-leaves-out-farm-rent` (-92.97), with the refund out of income as the key already holds it. `shared-state-paid-leave-contributions-not-in-salt` (-198.72) and `shared-passive-rental-loss-allowed` (+124.69) would move it further. Open: `shared-state-income-tax-withholding-estimate` |
| 062 | 0.00 | 4,328.39 | `shared-survivor-benefits-not-taxable`; the board's own alternative |
| 033, 078, 117 | 3,818.15; 24,164.46; 24,961.34 | 3,788.99; 23,772.80; 24,391.80 | `shared-state-tax-refund-counted-in-full`; the board's own alternatives (Tax-Calculator reproduces 117's to the cent) |
| 002, 107, 121 | 0.00 | 0.00 | `shared-disability-benefits-taxable`: the key holds the answer the prompt rule supports, and policyengine-us, Tax-Calculator and TAXSIM contest it |
