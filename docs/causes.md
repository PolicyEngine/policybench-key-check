# Causes of disagreement on the board's 100 households

This file gives, for every household and line where the committed key, policyengine-us, Tax-Calculator and TAXSIM disagree, the causes of the disagreement, how much each cause moves each answer, what the law says, and which answer the law supports. `results/causes.csv` holds one row per cause, `results/cause_cells.csv` one row per cause, household, line, table and answerer, and `results/cause_positions.csv` one row per cause, household and line where an entry takes a position on the key's answer; this account renders all three. `tests/test_causes.py` checks that the causes account for every difference to the dollar.

Claude Opus 5.5 agents opened every entry: four tracers reconciled each disagreement to its cause (`evidence/traces/trace-pe-a.md`, `trace-pe-b.md`, `trace-taxsim-a.md`, `trace-taxsim-b.md`), reviewers checked the maps (`evidence/traces/verify-*.md`), and a further agent wrote these tables on 2026-11-10. On 2026-11-11 a builder applied the board's rule for unstated facts uniformly to the input maps as map version 2026-11-11.1 (`evidence/traces/builder-2.md`), which moved ten board cells, and another agent brought the entries in line with the new answers and added the positions file. Every entry stays open. The "who is right" line states the entry's position and its grounds in law; it awaits a human reviewer and decides nothing. This repo proposes answers; it changes nothing on the board.

## How to read the entries

**Answerers and tables.** The 2026 table compares four answers: the committed key (`policybench-key`, run `pb-reference-2.60.0`), policyengine-us 2.60.0 under the board's conventions (`pe-2.60.0-board-2026`), Tax-Calculator 6.9.0 (`taxcalc-6.9.0-2026`) and TAXSIM's test build cd2026110117 (`taxsim-cd2026110117-2026`). The 2025 table compares the last three under 2025 law (`pe-2.60.0-board-2025`, `taxcalc-6.9.0-2025`, `taxsim-cd2026110117-2025`). `results/runs.csv` describes each run. The lines are the four in `scripts/agreement.py`; every cause here moves federal tax before refundable credits or federal refundable credits.

**Amounts.** A cell's amount is what the cause adds to that answerer's answer, in dollars, relative to the answer the law supports, or, where the cause turns on a fact the household does not state, the answer the board's prompt rule supports, as the entry reads them. Where the entry takes no side on a household, the amount runs from the answer the input maps give at map version 2026-11-11.1. Each row's `basis` says how the entry got the amount. A cause that lowers a refundable credit has a negative amount on that line. For any two answerers, the difference between their answers equals the difference between the sums of their amounts, within $1; the largest residual is $0.30 (household 081).

**The prompt rule.** The board tells every answerer to treat an unlisted number as 0 and any other unlisted fact, boolean or status as false, to assume filing and take-up when required, and not to infer unlisted income, expenses, assets, benefit receipt, rent or health coverage (`PolicyEngine/policybench@c7ede86c:policybench/prompts.py:15-27`). These entries read the rule one way throughout: a provision that includes or allows something only on a fact does not apply when the household does not state the fact, and a provision that excludes or denies something only on a fact does not apply either. Where the cause is an unstated fact, the entry says that no answer is right until the household states the fact, and then which answer the rule points to.

**Counterfactual runs.** Where an entry cites a counterfactual run, it means Tax-Calculator 6.9.0 or TAXSIM cd2026110117 run on the inputs recorded in `results/dossiers/<case>.json` (the `in_` fields under `other_models`), with the settings of `scripts/run_taxcalc.py` or `keycheck/taxsim.py`, changing only the input the entry names (`scripts/causes/counterfactual_taxcalc.py`). The engine experiments sit in `results/repro/`.

**Positions.** Each row of `results/cause_positions.csv` takes one position from a fixed set on the key's 2026 answer for one household and line. `key_value` repeats the key's answer; `how_computed` says how the entry got any other answer it names. `scripts/make_cell_status.py` reads the file.

| Position | Meaning | Rows |
|---|---|---:|
| `supports_key` | The law or the prompt rule (the `grounds` column) supports the key's answer as far as this cause goes. Where the entry names the answer another reading gives, `other_reading_answer` holds it. | 51 |
| `supports_other_answer` | The law or the prompt rule supports a different answer, which `supported_answer` gives. | 24 |
| `turns_on_unstated_fact` | The answer turns on a fact the board does not state, about the household or about the scope of the line, and the entry takes no side. `other_reading_answer` gives the answer on the reading the key does not take. | 13 |
| `no_effect` | The cause bears on the household but moves no answer on this line. | 16 |

**Cell standing.** Where this account describes a cell's standing it uses three phrases: an answer "reproduced by a run of another lineage" (Tax-Calculator or TAXSIM gives it within $1), "contested" (an entry here says the law or the prompt rule supports a different answer), and "resting on one model" (no run of another lineage gives it).

## Kinds

| Kind | Meaning | Entries |
|---|---|---:|
| `model-law-departure` | A model computes a provision the law gives, but computes it differently from the law. | 6 |
| `model-no-provision` | A model has no input for a stated fact, or no provision for the law of the year, so its answer leaves the provision out. | 8 |
| `pe-default-unstated-fact` | policyengine-us fills a fact the household does not state with a default value, or applies a provision as if a condition the household does not state held, and the default moves the answer. | 4 |
| `key-decided-value` | The committed key holds a value the board decided on an earlier engine release, and that value differs from what the engine gives today. | 2 |
| `map-limit` | This repo's input map cannot express a stated fact in Tax-Calculator or TAXSIM the way the law treats it, or reads a fact differently from policyengine-us. | 1 |
| `shared-reading` | Every answerer, or every answerer but the key, reads a stated or unstated fact the same way. Where all answers in a table move alike the reading leaves no trace in any difference, so the entry lists the households in `households_shared` and writes no cell rows; where the key's frozen value departs from the others, the entry writes rows for the answers it moves. | 13 |
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
- **Positions on the key's 2026 answers:** 026 (refundable credits) `supports_key` on the law; 037 (tax before refundable credits) `supports_key` on the law; 046 (tax before refundable credits) `supports_key` on the law; 049 (tax before refundable credits) `supports_key` on the law; 064 (tax before refundable credits) `supports_key` on the law; 089 (tax before refundable credits) `supports_key` on the law; 091 (tax before refundable credits) `supports_key` on the law; 117 (tax before refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 005 (tax before refundable credits) `supports_key` on the law; 020 (tax before refundable credits) `supports_key` on the law; 049 (tax before refundable credits) `supports_key` on the law; 055 (tax before refundable credits) `supports_key` on the law; 082 (tax before refundable credits) `supports_key` on the law; 099 (tax before refundable credits) `supports_key` on the law; 110 (tax before refundable credits) `supports_key` on the law; 117 (tax before refundable credits) `supports_key` on the law; 122 (tax before refundable credits) `supports_key` on the law; 123 (tax before refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 000 (tax before refundable credits) `supports_key` on the law; 122 (tax before refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 122 (tax before refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 070 (tax before refundable credits) `supports_key` on the law; 091 (tax before refundable credits) `supports_key` on the law; 119 (refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 099 (tax before refundable credits) `supports_key` on the law; 119 (refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 119 (refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 109 (refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 078 (tax before refundable credits) `supports_key` on the law.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 078 | tax before refundable credits | 2026 | `taxsim` | 96.00 |

### `taxsim-no-early-distribution-tax-input`: TAXSIM has no input for the additional tax on early distributions

*Kind* `model-no-provision`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM has no input for the additional tax on early distributions, so its line leaves out the 10% the maps compute for 023 (800.00), 064 (2,000.00) and 074 (38.40). The map names the amount in a note on each answer.

- **Where it holds:** taxsimtest cd2026110117; keycheck 2026-11-11.1 lists the tax in unexpressed (keycheck/map_taxsim.py:401).
- **Law:** 26 U.S.C. 72(t)(1) (the tax under chapter 1 rises by 10% of the includible amount); 26(b)(2)(C). **Figure:** 10% of 8,000 (023), 20,000 (064) and 384 (074).
- **Who is right (this entry's position):** Tax-Calculator on 064, where the law decides; on 023 and 074 the answer turns on 72(m)(7) disability, as pe-early-distribution-tax-not-computed sets out. Either way TAXSIM's line cannot hold the tax.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** keycheck/map_taxsim.py:45-47 (NBER's input list for the test build has no field for it) and :401 (the note); evidence/traces/builder-2.md (item 4: TAXSIM note only); results/answers.csv (the note on 023, 064 and 074).
- **Source:** evidence/traces/builder-2.md.
- **Positions on the key's 2026 answers:** 023 (tax before refundable credits) `turns_on_unstated_fact`, key 643.43, other reading 1,443.43; 064 (tax before refundable credits) `supports_other_answer` on the law, 6,441.46 against the key's 4,441.46; 074 (tax before refundable credits) `turns_on_unstated_fact`, key 0.00, other reading 38.40.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 023 | tax before refundable credits | 2026 | `taxsim` | -800.00 |
| 023 | tax before refundable credits | 2025 | `taxsim` | -800.00 |
| 064 | tax before refundable credits | 2026 | `taxsim` | -2,000.00 |
| 064 | tax before refundable credits | 2025 | `taxsim` | -2,000.00 |
| 074 | tax before refundable credits | 2026 | `taxsim` | -38.40 |
| 074 | tax before refundable credits | 2025 | `taxsim` | -38.40 |

### `map-ira-deduction-in-nonprop-cuts-eitc`: The TAXSIM map's adjustments to AGI lower earned income

*Kind* `map-limit`. *Moves* `taxsim`. *Law years* both. *Entry* open.

TAXSIM has no input for an adjustment that lowers AGI alone, so the map enters each such adjustment as negative nonprop, which this build also subtracts from earned income: for the earned income credit and for the refundable child credit, which uses the same earned income. On 100 the IRA deduction (180.32) costs 40% of itself in the earned income credit's phase-in range. On 038 the self-employed health insurance deduction (100.00, 162(l)) costs 15% of itself in the refundable child credit (TAXSIM's actc falls from 2,909.35 to 2,894.35); its earned income credit does not move.

- **Where it holds:** keycheck 2026-11-11.1 (keycheck/map_taxsim.py: adjustments and the self-employed health insurance and pension deductions go to negative nonprop) on taxsimtest cd2026110117.
- **Law:** 26 U.S.C. 32(c)(2)(A) (earned income: wages and net earnings from self-employment; neither the 219 deduction nor the 162(l) deduction reduces it, 162(l)(4)); 24(d)(1)(B)(i) (the refundable child credit takes 15% of the earned income above $2,500, earned income as section 32 defines it). **Figure:** 40% x 2,055.72 = 822.29 for 100; 15% x 100.00 = 15.00 for 038.
- **Who is right (this entry's position):** policyengine-us and Tax-Calculator. Entering the IRA deduction where it moves only AGI (a negative short-term gain) gives TAXSIM 822.29 on 100. On 038 neither policyengine-us (which allows no 162(l) deduction there: it needs is_self_employed) nor Tax-Calculator (which deducts the 100.00) moves its refundable credits.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-taxsim-b.md (100: TAXSIM with nonprop 0 and stcg -180.32 gives 822.29); evidence/traces/fix-maps.md (kept as a noted limit); evidence/traces/builder-2.md (item 9 and 'For the causes unit' 6: 038's actc 2,909.35 -> 2,894.35); keycheck/map_taxsim.py:297 and :415 (the notes on 038 and on adjustments).
- **Source:** evidence/traces/trace-taxsim-b.md, evidence/traces/builder-2.md.
- **Positions on the key's 2026 answers:** 038 (refundable credits) `supports_key` on the law; 100 (refundable credits) `supports_key` on the law.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 038 | refundable credits | 2026 | `taxsim` | -15.00 |
| 038 | refundable credits | 2025 | `taxsim` | -15.00 |
| 100 | refundable credits | 2026 | `taxsim` | -72.13 |
| 100 | refundable credits | 2025 | `taxsim` | -72.13 |

### `pe-other-dependent-credit-without-dependency-tests`: policyengine-us pays the other-dependent credit without the dependency tests

*Kind* `model-law-departure`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

policyengine-us pays the $500 credit for other dependents for every member of the tax unit who is not the head or spouse, testing only identification. It does not apply the qualifying-relative gross income test or the disability rule that lets an adult be a qualifying child. 093's dependent1 is 27 and earns $45,000 of wages, and the board states that dependent1 is disabled; the engine pays the credit, and pays the same $500 when is_disabled is false.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (ctc_adult_individual_maximum.py identical; is_tax_unit_dependent.py differs only in its docstring).
- **Law:** 26 U.S.C. 24(h)(4) ($500 for each dependent as defined in 152 other than a qualifying child); 152(d)(1)(B) (a qualifying relative's gross income must fall below the exemption amount); 152(c)(3)(B) and 22(e)(3) (a permanently and totally disabled child meets the age test; 22(e)(3) requires inability to engage in any substantial gainful activity). **Figure:** $500; exemption amount $5,300 (2026, Rev. Proc. 2025-32 sec. 4.23) and $5,200 (2025, Rev. Proc. 2024-40 sec. 2.24).
- **Who is right (this entry's position):** Tax-Calculator and TAXSIM, on this entry's position. With $45,000 of wages dependent1 fails the gross income test, and a year of wages at that level is work that 22(e)(3) disability rules out (an inference: this entry did not consult the regulations on substantial gainful activity), so the stated 'is disabled' does not make dependent1 a qualifying child; dependent1 is not the filer's dependent, and no $500 credit follows.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-b.md (093); results/repro/board_experiments.txt (093 on 2.60.0 and 2.116.15: is_disabled false still pays 500); results/repro/repro_pe_2.60.0.txt and repro_pe_2.116.15.txt (credit for other dependents with no gross income test); policyengine_us/variables/gov/irs/credits/ctc/maximum/individual/ctc_adult_individual_maximum.py:13,21-40; policyengine_us/variables/household/demographic/tax_unit/is_tax_unit_dependent.py:10-13.
- **Source:** evidence/traces/trace-pe-b.md.
- **Positions on the key's 2026 answers:** 093 (tax before refundable credits) `supports_other_answer` on the law, 9,128.99 against the key's 8,628.99.

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
- **Positions on the key's 2026 answers:** 020 (tax before refundable credits) `supports_other_answer` on the prompt rule, 70,054.80 against the key's 68,056.71.

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
- **Positions on the key's 2026 answers:** 114 (tax before refundable credits) `supports_other_answer` on the prompt rule, 11,265.27 against the key's 10,729.61.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 114 | tax before refundable credits | 2026 | `policybench-key` | -535.66 |
| 114 | tax before refundable credits | 2026 | `policyengine-us` | -535.66 |
| 114 | tax before refundable credits | 2025 | `policyengine-us` | -488.40 |

### `pe-net-investment-income-leaves-out-farm-rent`: policyengine-us 2.60.0 leaves farm rent out of net investment income

*Kind* `model-law-departure`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

policyengine-us 2.60.0 leaves Form 4835 farm rent out of net investment income, so 120's farm rent loss (2,446.59) does not offset its rent and interest, and the net investment income tax comes to 163.40 (3.8% of 4,300) where adding farm rent to the sources gives 70.43. The amount here is that engine measurement, taken with no 469 limit; the limit's own effect, including its 16.97 of net investment income tax, sits in pe-no-passive-activity-loss-limit. Under the maps, which suspend the net passive loss, the farm rent that 469 allows (-2,000.00) offsets the rent (2,000.00), net investment income is the interest, 2,300.00, and the tax 87.40.

- **Where it holds:** policyengine-us 2.60.0 (and the key's frozen 1.755.4 value). **Fixed in:** policyengine-us 2.116.15 (farm_rent_income in gov.irs.investment.income.sources).
- **Law:** 26 U.S.C. 1411(c)(1)(A)(i) (gross income from rents) and (c)(1)(B) (deductions properly allocable to it). **Figure:** with no 469 limit, 3.8% of net investment income 1,853.41 = 70.43; with the loss suspended, 3.8% of 2,300.00 = 87.40.
- **Who is right (this entry's position):** Tax-Calculator, TAXSIM and policyengine-us 2.116.15 on the sources of net investment income. Adding farm_rent_income to 2.60.0's sources gives 40,330.21, Tax-Calculator's and TAXSIM's answer before the maps applied 469 (keycheck 2026-11-10.2); the rest of the gap at 2026-11-11.1 belongs to pe-no-passive-activity-loss-limit.
- **Existing report:** https://github.com/PolicyEngine/policyengine-us/issues/10075.
- **Evidence:** evidence/traces/trace-pe-b.md (120); results/repro/board_experiment_120_rerun.txt; policyengine_us/parameters/gov/irs/investment/income/sources.yaml:8-27 (2.60.0, no farm_rent_income) and :23 at 2.116.15; PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions[17]: the 1.755.4-to-2.15.17 move for 120 is the IRA and #9122 alone, so the frozen value carries the same omission: inference); results/dossiers/scenario_120.json (Tax-Calculator out_niit 87.40 at keycheck 2026-11-11.1).
- **Source:** evidence/traces/trace-pe-b.md.
- **Positions on the key's 2026 answers:** 120 (tax before refundable credits) `supports_other_answer` on the law, 39,928.85 against the key's 40,021.82.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 120 | tax before refundable credits | 2026 | `policybench-key` | 92.97 |
| 120 | tax before refundable credits | 2026 | `policyengine-us` | 92.97 |
| 120 | tax before refundable credits | 2025 | `policyengine-us` | 92.97 |

### `pe-scholarship-not-income`: policyengine-us leaves a stated scholarship out of income

*Kind* `pe-default-unstated-fact`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

030 and 068 list educational assistance (5,000 and 73,000), which policyengine-us documents as 'Scholarships, grants, and other educational assistance.' policyengine-us leaves it out of gross income whatever else the household states (experiment R1: 5,000 beside 13,000 of wages leaves gross income at 13,000), as if each recipient were a degree candidate who spent it all on qualified tuition and related expenses. The maps count it in full, since the board states neither condition: Tax-Calculator through e01200 and TAXSIM through pensions, so it raises AGI and not earned income. On 030 AGI rises from 13,000 to 18,000 and the tax from 0 to 190.00 (2026) or 225.00 (2025); on 068 the tax rises by 12,818.36 (2026) or 13,045.86 (2025). The earlier entry shared-scholarship-not-income said 030 owed 0 either way; the TAXSIM comparer found that wrong, and these runs agree.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (experiment R1 gives the same result on both); the key's frozen value, which equals the 2.60.0 rerun on both households; Tax-Calculator and TAXSIM count the amount through READINGS educational_assistance (keycheck 2026-11-11.1).
- **Law:** 26 U.S.C. 117(a) and (b) (exclude a qualified scholarship only for a degree candidate and only to the extent it pays qualified tuition and related expenses); 61(a); 127 (excludes educational assistance only under an employer's program). **Figure:** 030: taxable income 1,900 at 10% = 190.00 (2026), 2,250 at 10% = 225.00 (2025).
- **Who is right (this entry's position):** Tax-Calculator and TAXSIM, under the prompt rule: 190.00 for 030 and 14,728.38 for 068. Each exclusion needs a fact the board does not state (degree candidacy and use for tuition under 117, an employer's program under 127), and the rule makes an unstated fact false, so the whole amount is income. The blind second maps split: the second TAXSIM map counts it and its comparer ruled the first map's exclusion an error (docs/second-map-taxsim.md); the second Tax-Calculator map leaves it out, and its comparer lists that as a reading both maps shared without arguing it (docs/second-map-taxcalc.md). This entry reads policyengine-us's documentation of the input (scholarships and grants, not the excluded part of them) as the stated fact, so the engine applies the exclusion on conditions the household does not state.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** results/repro/reading_experiments_pe_2.60.0.txt and results/repro/reading_experiments_pe_2.116.15.txt (R1); policyengine_us/variables/household/income/person/misc/educational_assistance.py:8 (documentation); policyengine_us/parameters/gov/irs/gross_income/sources.yaml:3-47 (no educational_assistance); evidence/traces/builder-2.md (item 1; 'For the causes unit' 2); docs/second-map-taxsim.md (030 +190.00, 068 +12,818.36, first_map_errs); docs/second-map-taxcalc.md (shared readings); keycheck/unit.py:180 READINGS educational_assistance.
- **Source:** evidence/traces/builder-2.md, docs/second-map-taxsim.md, results/repro/reading_experiments_pe_2.60.0.txt.
- **Positions on the key's 2026 answers:** 030 (tax before refundable credits) `supports_other_answer` on the prompt rule, 190.00 against the key's 0.00; 068 (tax before refundable credits) `supports_other_answer` on the prompt rule, 14,728.38 against the key's 1,910.02.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 030 | tax before refundable credits | 2026 | `policybench-key` | -190.00 |
| 030 | tax before refundable credits | 2026 | `policyengine-us` | -190.00 |
| 030 | tax before refundable credits | 2025 | `policyengine-us` | -225.00 |
| 068 | tax before refundable credits | 2026 | `policybench-key` | -12,818.36 |
| 068 | tax before refundable credits | 2026 | `policyengine-us` | -12,818.36 |
| 068 | tax before refundable credits | 2025 | `policyengine-us` | -13,045.86 |

### `pe-survivor-benefits-not-income`: policyengine-us leaves survivor benefits out of income

*Kind* `pe-default-unstated-fact`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

062 lists 28,800 of survivor benefits other than Social Security, and 108 lists 10,392 (policyengine-us documents the input as 'Survivor benefits other than Social Security survivor benefits'). policyengine-us leaves them out of gross income whatever else the household states (experiment R2), as if an exclusion applied. The maps count them as a taxable pension, since the investment in the contract is an unlisted amount and every exclusion needs an unstated fact. 062's AGI rises from 17,322.91 to 63,245.14 (the taxable part of its Social Security rises with it) and its tax from 0 to 4,328.39; 108 owes 0 either way (taxable income stays 0, and at 85 it has no earned income credit).

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (experiment R2 gives the same result on both; #10181 wired military survivor benefit plan payments into gross income and left survivor_benefits out); the key's frozen value; Tax-Calculator and TAXSIM count the amount through READINGS survivor_benefits (keycheck 2026-11-11.1).
- **Law:** 26 U.S.C. 61(a) and 72 (a survivor annuity is gross income); 101(a) (life insurance proceeds paid by reason of death), 104(a)(1) (workers' compensation) and 38 U.S.C. 5301 (veterans' benefits) exclude only on facts the board does not state.
- **Who is right (this entry's position):** Tax-Calculator and TAXSIM, under the prompt rule: 4,328.39 for 062, the board's own alternative for this excluded output. Both blind second maps count the benefits too, and both comparers ruled the first map's earlier exclusion an error (docs/second-map-taxcalc.md, docs/second-map-taxsim.md).
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** results/repro/reading_experiments_pe_2.60.0.txt and results/repro/reading_experiments_pe_2.116.15.txt (R2); policyengine_us/variables/household/income/person/general/survivor_benefits.py:8 (documentation); policyengine_us/parameters/gov/irs/gross_income/sources.yaml:3-47 (no survivor_benefits; military survivor payments enter at :46-47); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json (062: reference_depends_on_unlisted_input, alternative 4,328.39); evidence/traces/builder-2.md (item 2); keycheck/unit.py:80 READINGS survivor_benefits.
- **Source:** evidence/traces/builder-2.md, docs/second-map-taxcalc.md, docs/second-map-taxsim.md, results/repro/reading_experiments_pe_2.60.0.txt.
- **Positions on the key's 2026 answers:** 062 (tax before refundable credits) `supports_other_answer` on the prompt rule, 4,328.39 against the key's 0.00; 108 (tax before refundable credits) `no_effect`.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 062 | tax before refundable credits | 2026 | `policybench-key` | -4,328.39 |
| 062 | tax before refundable credits | 2026 | `policyengine-us` | -4,328.39 |
| 062 | tax before refundable credits | 2025 | `policyengine-us` | -4,385.89 |

### `pe-no-passive-activity-loss-limit`: policyengine-us has no passive activity loss limit

*Kind* `model-no-provision`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

policyengine-us applies no passive activity loss limit. 120 states rent of 2,000 and a farm rent loss of 2,446.59, both rentals, so passive; 469 suspends their net loss of 446.59 at 120's AGI, and the maps add it back (469 allows 2,000 of the farm rent loss, the passive income it can offset). That raises taxable income by 448.82 (24%, 107.72, with 2.23 more from the 0.5% charitable floor) and the net investment income tax by 16.97 in 2026; in 2025, 446.59 at 32% (142.91) and the same 16.97. The maps suspend the losses of 004 (a partnership loss of 135) and 098 (a farm rent loss of 11,100) too, and no line moves. The maps also read partnership income beyond a partner's self-employment earnings as passive, so as net investment income, where policyengine-us counts only the separate input passive_partnership_s_corp_income: on the board that touches 064, 089 and 114 and moves no line (none reaches the 1411 threshold or claims an earned income credit).

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (no 469 variable; experiment R4 deducts a net rental loss at wages of 199,000 on both; issue 5274 asked for the limit, and its maintainers marked it not planned on 2026-07-26); the key's frozen value.
- **Law:** 26 U.S.C. 469(a) (disallows a passive activity loss) and (b) (carries it to the next year); 469(c)(2) (a rental activity is passive whatever the participation); 469(c)(7) (real estate professionals); 469(i)(3)(A) (the $25,000 allowance falls by 50% of modified AGI above $100,000, so to 0 at $150,000). **Figure:** allowance 0 at 120's modified AGI; 446.59 suspended.
- **Who is right (this entry's position):** Tax-Calculator and TAXSIM, on the law (their 40,454.89 also counts the state tax refund the key leaves out; the key less this entry's amount is 40,146.51). A rental is passive by statute; only real estate professional status, which turns on hours the board does not state and the prompt rule makes false, would take it out, and the 469(i) allowance is gone at this AGI whatever the participation. Both blind second maps suspend the loss, and both comparers ruled the first map's earlier deduction an error (docs/second-map-taxcalc.md, docs/second-map-taxsim.md). The board excludes 120; its record puts the limit's effect at +24.75 on 2.15.17, a gap no entry here examines.
- **Existing report:** https://github.com/PolicyEngine/policyengine-us/issues/5274 (maintainers marked it not planned on 2026-07-26).
- **Evidence:** results/repro/reading_experiments_pe_2.60.0.txt and results/repro/reading_experiments_pe_2.116.15.txt (R4); evidence/traces/builder-2.md (item 3; 'For the causes unit' 4, split (a), which leaves pe-net-investment-income-leaves-out-farm-rent at its engine measurement); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (scenario_120: 'the engine's missing 469 limit'); second_map/taxcalc/sources/usc26_469.txt:24-25; keycheck/unit.py:129 READINGS passive_activity; keycheck/statute.py passive_activity_allowed.
- **Source:** evidence/traces/builder-2.md, docs/second-map-taxcalc.md, docs/second-map-taxsim.md, results/repro/reading_experiments_pe_2.60.0.txt.
- **Positions on the key's 2026 answers:** 004 (tax before refundable credits) `no_effect`; 098 (tax before refundable credits) `no_effect`; 120 (tax before refundable credits) `supports_other_answer` on the law, 40,146.51 against the key's 40,021.82.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 120 | tax before refundable credits | 2026 | `policybench-key` | -124.69 |
| 120 | tax before refundable credits | 2026 | `policyengine-us` | -124.69 |
| 120 | tax before refundable credits | 2025 | `policyengine-us` | -159.88 |

### `pe-early-distribution-tax-not-computed`: policyengine-us computes no additional tax on early distributions

*Kind* `model-no-provision`. *Moves* `policyengine-us`, `policybench-key`. *Law years* both. *Entry* open.

policyengine-us computes no additional tax on early distributions: income_tax_before_refundable_credits adds qualified_retirement_penalty, an input with no formula, and the board states none. The maps compute 10% of each filer's taxable IRA, 401(k), 403(b) and SEP distributions before 59 1/2, less the medical exception, and none for a filer the maps read as disabled under 72(m)(7) (stated disabled with no earnings). Three households move: 064's head (48) takes 20,000 from a 401(k), with medical expenses under the floor (2,000.00); 023's head (28, stated disabled, with wages of 17,442.65) takes 8,000 from a 403(b) (800.00); 074's head (54, with Social Security disability benefits and no stated disability) takes 384 from an IRA (38.40).

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (qualified_retirement_penalty is an input with no formula; experiment R3: 0 unless stated, and the line adds it when stated); the key's frozen value; Tax-Calculator gets the tax as e09900 through READINGS retirement_penalty (keycheck 2026-11-11.1).
- **Law:** 26 U.S.C. 72(t)(1) (the tax under chapter 1 rises by 10% of the includible amount received from a qualified retirement plan); 72(t)(2)(A)(iii) and 72(m)(7) (no tax on a distribution attributable to disability: inability to engage in any substantial gainful activity because of an impairment expected to result in death or to be of long-continued and indefinite duration); 72(t)(2)(B) (medical expenses deductible under 213); 26(b)(2)(C) (nonrefundable credits do not offset the tax). **Figure:** 10% of 20,000 = 2,000.00 (064); 10% of 8,000 = 800.00 (023); 10% of 384 = 38.40 (074).
- **Who is right (this entry's position):** For 064, Tax-Calculator: 6,441.45, and the key would be 6,441.46. The line is federal individual income tax, and 72(t)(1) raises the tax under chapter 1, the income tax (26(b)(2)(C) lists it among chapter 1 taxes); policyengine-us's own line adds the input when a household states it; and no 72(t)(2) exception rests on a stated fact. The blind second Tax-Calculator map gives 6,441.45 too, and its comparer calls the key's 064 answer a departure from the law (docs/second-map-taxcalc.md). For 023 and 074 the answer turns on 72(m)(7) disability, which the board does not define: the board states that 023's head is disabled and earns 1,453.55 a month, under the 2026 monthly amount the Social Security Administration treats as substantial gainful activity for a non-blind person ($1,690), and 074's head draws Social Security disability benefits, whose test (42 U.S.C. 423(d)(1)(A): death or at least 12 months) differs from 72(m)(7)'s 'long-continued and indefinite duration.' The maps tax both; the second Tax-Calculator map taxes neither (643.43 and 0.00). This entry takes no side on 023 and 074.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** results/repro/reading_experiments_pe_2.60.0.txt and results/repro/reading_experiments_pe_2.116.15.txt (R3: 5,020 with the input 0, 7,020 with it stated as 2,000); policyengine_us/variables/gov/irs/tax/federal_income/income_tax_before_refundable_credits.py:10,18-28; second_map/taxcalc/sources/usc26_72.txt:289 (72(m)(7)), :517 (72(t)(1)); evidence/traces/builder-2.md (item 4); docs/second-map-taxcalc.md (064 +2,000.00, first_map_errs); second_map/taxcalc/answers_2026.csv (023 643.43, 074 0.00, 064 6,441.45) and second_map/taxcalc/map.py:747-753 (a stated disability, or receipt of Social Security disability benefits, read as 72(m)(7) disability); keycheck/unit.py:152 READINGS retirement_penalty and :57 READINGS is_disabled; Federal Register document 2025-19763 (2026 substantial gainful activity amounts).
- **Source:** evidence/traces/builder-2.md, docs/second-map-taxcalc.md, results/repro/reading_experiments_pe_2.60.0.txt.
- **Positions on the key's 2026 answers:** 023 (tax before refundable credits) `turns_on_unstated_fact`, key 643.43, other reading 1,443.43; 064 (tax before refundable credits) `supports_other_answer` on the law, 6,441.46 against the key's 4,441.46; 074 (tax before refundable credits) `turns_on_unstated_fact`, key 0.00, other reading 38.40.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 023 | tax before refundable credits | 2026 | `policybench-key` | -800.00 |
| 023 | tax before refundable credits | 2026 | `policyengine-us` | -800.00 |
| 023 | tax before refundable credits | 2025 | `policyengine-us` | -800.00 |
| 064 | tax before refundable credits | 2026 | `policybench-key` | -2,000.00 |
| 064 | tax before refundable credits | 2026 | `policyengine-us` | -2,000.00 |
| 064 | tax before refundable credits | 2025 | `policyengine-us` | -2,000.00 |
| 074 | tax before refundable credits | 2026 | `policybench-key` | -38.40 |
| 074 | tax before refundable credits | 2026 | `policyengine-us` | -38.40 |
| 074 | tax before refundable credits | 2025 | `policyengine-us` | -38.40 |

### `key-ira-deducted-without-219g`: The key deducts IRA contributions without the active-participant limit

*Kind* `key-decided-value`. *Moves* `policybench-key`. *Law years* 2026. *Entry* open.

The frozen 1.755.4 values deduct traditional IRA contributions with no active-participant phase-out. Each filer defers wages into a 401(k), so is an active participant, and modified AGI exceeds the range, so the law allows no IRA deduction.

- **Where it holds:** the committed key: policyengine-us 1.755.4 values the board froze on 2026-09-22. **Fixed in:** the engine applies 219(g) by 2.38.6 (the board's recheck gives the corrected value; 2.60.0 has ira_active_participant.py and ira_219g_deductible_limit.py); the key keeps the frozen value.
- **Law:** 26 U.S.C. 219(g) (active-participant phase-out; 219(g)(5)(A) active participant); IRS Notice 2025-67 (2026 ranges). **Figure:** no deduction above $149,000 (joint) or $91,000 (single) of modified AGI in 2026.
- **Who is right (this entry's position):** policyengine-us 2.60.0, Tax-Calculator and TAXSIM. The board excludes these outputs and names the defect in its own records.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/trace-pe-a.md (005, 052: Tax-Calculator with the contribution deducted gives the key); evidence/traces/trace-pe-b.md (120); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_exclusions.json (root cause r02_ira_219g); PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions 17-20).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-pe-b.md.
- **Positions on the key's 2026 answers:** 005 (tax before refundable credits) `supports_other_answer` on the law, 107,198.34 against the key's 106,505.90; 052 (tax before refundable credits) `supports_other_answer` on the law, 104,225.26 against the key's 104,211.41; 120 (tax before refundable credits) `supports_other_answer` on the law, 40,028.32 against the key's 40,021.82.

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
- **Positions on the key's 2026 answers:** 020 (tax before refundable credits) `supports_other_answer` on the law, 68,334.73 against the key's 68,056.71.

| Household | Line | Table | Answerer | Amount |
|---|---|---|---|---:|
| 020 | tax before refundable credits | 2026 | `policybench-key` | -278.02 |

### `shared-state-tax-refund-counted-in-full`: A state tax refund counts in full as income

*Kind* `shared-reading`. *Moves* `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

A listed state or local tax refund counts in full as income in policyengine-us (which documents the input as the taxable refund on Schedule 1, line 1) and, through this repo's reading, in Tax-Calculator and TAXSIM. The key's frozen 1.755.4 values for 005 and 120 never counted the input, so those two cells move three answers and not the key; elsewhere every answer counts it.

- **Where it holds:** policyengine-us 2.15.17 and later (policyengine-us#9422, which fixed issue #9122), and the key's values that the board froze on 2.15.17; Tax-Calculator and TAXSIM through READINGS salt_refund_income (keycheck 2026-11-11.1).
- **Law:** 26 U.S.C. 111(a) (a recovery is income only to the extent the earlier deduction reduced tax).
- **Who is right (this entry's position):** No answer is right until the board states the prior year's facts: whether the household itemized and deducted the refunded tax. The prompt rule makes that unstated fact false, so none of the refund is income (the board's own alternative reading). On that reading the key's frozen values for 005 and 120 hold the refund correctly, and 082's scored answer would fall by 14.85.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** PolicyEngine/policybench@c7ede86c:reference_audit/2026-09-28/fixes/latest_alt_salt_refund_no_prior_benefit.py:1-30; PolicyEngine/policybench@c7ede86c:reference_audit/2026-10-22-engine-upgrade/reference-build/reference_outputs.csv.meta.json (revisions[17]: 005 '+$1,327.26 move is #9122 alone', 120 '+$394.85 move is #9122 alone'); results/repro/board_experiments_2.txt (005 salt_refund_income 0: 107,198.34); counterfactual runs on the inputs in results/dossiers (Tax-Calculator 005 with e00700 0: 107,198.33; 082: 9,564.92; 033: 3,788.99; 078: 23,772.80; 117: 24,391.80, each the board record's alternative to the cent; TAXSIM 005 with pensions less the refund: 107,540.65, above the engine's 107,198.34 by the 170(p) deduction TAXSIM lacks; 120, Tax-Calculator with the refund out and the shared state and local tax lowered by the 113.77 the board records for the engine's Connecticut estimate: 40,060.04 at keycheck 2026-11-11.1, 39,935.35 with the passive loss allowed as before).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/trace-pe-b.md, evidence/traces/trace-taxsim-a.md.
- **Households where every answer moves alike (no cell rows):** 033, 074, 078, 082, 088, 117, 005 (2025 table only), 120 (2025 table only).
- **Positions on the key's 2026 answers:** 005 (tax before refundable credits) `supports_key` on the prompt rule; 033 (tax before refundable credits) `supports_other_answer` on the prompt rule, 3,788.99 against the key's 3,818.15; 074 (tax before refundable credits) `no_effect`; 078 (tax before refundable credits) `supports_other_answer` on the prompt rule, 23,772.80 against the key's 24,164.46; 082 (tax before refundable credits) `supports_other_answer` on the prompt rule, 9,564.92 against the key's 9,579.77; 088 (tax before refundable credits) `no_effect`; 117 (tax before refundable credits) `supports_other_answer` on the prompt rule, 24,391.80 against the key's 24,961.34; 120 (tax before refundable credits) `supports_key` on the prompt rule.

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
- **Positions on the key's 2026 answers:** 002 (tax before refundable credits) `supports_key` on the prompt rule, key 0.00, other reading 1,890.30; 057 (tax before refundable credits) `no_effect`; 067 (tax before refundable credits) `no_effect`; 084 (tax before refundable credits) `no_effect`; 107 (tax before refundable credits) `supports_key` on the prompt rule, key 0.00, other reading 211.23; 121 (tax before refundable credits) `supports_key` on the prompt rule, key 0.00, other reading 875.34.

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
- **Positions on the key's 2026 answers:** 029 (tax before refundable credits) `supports_key` on the law; 030 (tax before refundable credits) `supports_key` on the law; 056 (tax before refundable credits) `supports_key` on the law; 080 (tax before refundable credits) `supports_key` on the law; 090 (tax before refundable credits) `supports_key` on the law; 112 (tax before refundable credits) `supports_key` on the law.

### `shared-disabled-member-qualifying-child`: A member the board calls disabled counts as a qualifying child

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

The board states that 067's dependent1 (23) and 064's dependent1 (27) are disabled, and neither has earnings. The maps read each as permanently and totally disabled, so a qualifying child at any age and a dependent for the $500 credit. policyengine-us claims both as dependents without testing disability.

- **Where it holds:** keycheck 2026-11-11.1 READINGS is_disabled; policyengine-us 2.60.0 claims the member by another route (pe-other-dependent-credit-without-dependency-tests).
- **Law:** 26 U.S.C. 152(c)(3)(B) and 22(e)(3); 152(d)(1)(B); 24(h)(4). **Figure:** $500 credit for other dependents.
- **Who is right (this entry's position):** All four on 067's scored answer (5,616.24), by either reading: as a disabled qualifying child, or, if 'is disabled' falls short of 22(e)(3), as a qualifying relative, since under the prompt rule the member's disability benefits are not income (shared-disability-benefits-taxable), which leaves the member's gross income at 0, below the exemption amount. 064 is a qualifying relative either way; the reading moves only its earned-income-credit child count, and no credit arises at its income.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** evidence/traces/verify-unit-statute.md (F1); evidence/traces/trace-pe-a.md (067); evidence/traces/fix-maps.md (reading 1, 067 moved to all_agree).
- **Source:** evidence/traces/trace-pe-a.md, evidence/traces/verify-unit-statute.md.
- **Households where every answer moves alike (no cell rows):** 064, 067.
- **Positions on the key's 2026 answers:** 064 (tax before refundable credits) `no_effect`; 067 (tax before refundable credits) `supports_key` on the law.

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
- **Positions on the key's 2026 answers:** 005 (tax before refundable credits) `turns_on_unstated_fact`, key 106,505.90, other reading 100,783.92; 020 (tax before refundable credits) `turns_on_unstated_fact`, key 68,056.71, other reading 67,834.07; 052 (tax before refundable credits) `turns_on_unstated_fact`, key 104,211.41, other reading 103,992.99; 120 (tax before refundable credits) `turns_on_unstated_fact`, key 40,021.82, other reading 39,858.42.

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
- **Positions on the key's 2026 answers:** 022 (tax before refundable credits) `supports_other_answer` on the prompt rule, 12,234.66 against the key's 11,113.57; 072 (tax before refundable credits) `no_effect`; 078 (tax before refundable credits) `supports_other_answer` on the prompt rule, 27,290.70 against the key's 24,164.46; 081 (tax before refundable credits) `supports_other_answer` on the prompt rule, 28,763.81 against the key's 26,932.27; 114 (tax before refundable credits) `supports_other_answer` on the prompt rule, 11,783.48 against the key's 10,729.61; 120 (tax before refundable credits) `supports_other_answer` on the prompt rule, 43,263.75 against the key's 40,021.82.

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
- **Positions on the key's 2026 answers:** 120 (tax before refundable credits) `supports_other_answer` on the law, 39,823.10 against the key's 40,021.82.

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
- **Positions on the key's 2026 answers:** 049 (tax before refundable credits) `no_effect`; 120 (tax before refundable credits) `supports_key` on the prompt rule, key 40,021.82, other reading 39,797.18.

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
- **Positions on the key's 2026 answers:** 093 (tax before refundable credits) `turns_on_unstated_fact`, key 8,628.99, other reading 11,848.99; 123 (tax before refundable credits) `turns_on_unstated_fact`, key 5,200.24, other reading 8,420.24.

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
- **Positions on the key's 2026 answers:** 042 (tax before refundable credits) `turns_on_unstated_fact`, key 2,361.96, other reading 2,377.71.

### `shared-rental-with-basis-qualified-business-income`: Rent with a stated basis counts as qualified business income

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

022 (rent 4,550, basis 24,786.06), 076 (rent 4,000, basis 49,921.10), 062 (farm rent 4,792.94, basis 22,440) and 112 (farm rent 1,920, basis 54,381) state rent or farm rent, the unadjusted basis of qualified property, and no other business. Every answer now counts the rent as qualified business income and deducts 20% of it: policyengine-us by default, the maps because the stated basis can only belong to a qualified trade or business. Until map version 2026-11-11.1 the maps read rent (not farm rent) the other way, so this reading moved 022 and 076 then and moves no difference now.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (rental_income_would_be_qualified and farm_rent_income_would_be_qualified default to true; experiment R10); keycheck 2026-11-11.1 READINGS rental_qbi (rent with a stated basis and no other trade or business goes to Tax-Calculator e27200 and TAXSIM scorp).
- **Law:** 26 U.S.C. 199A(c)(1) and (d)(1) (qualified business income comes from a qualified trade or business); Treas. Reg. 1.199A-1(b)(14) (a section 162 trade or business); 199A(b)(6)(A) (qualified property: property the qualified trade or business holds and has available for use). **Figure:** 20% of qualified business income: 910.00 (022), 800.00 (076).
- **Who is right (this entry's position):** Open on 022 and 076; this entry takes no side. Two independent authors, each writing a map blind to the other, read the rent as income from no trade or business: the second Tax-Calculator map gives 19,803.80 on 076 and the second TAXSIM map 11,313.77 on 022, and the first maps read it that way too until this revision (docs/second-map-taxcalc.md, docs/second-map-taxsim.md). The case for the key: a stated basis of qualified property exists only for property held by a qualified trade or business, and the rental is the only activity that could hold it. The case against: the definition runs from the business to the property, so the basis implies a trade or business only by reading a defined term backwards, and the facts that make a rental a section 162 trade or business (regular and continuous involvement, or the 250 hours of Rev. Proc. 2019-38) are unstated, which the prompt rule makes false. On the other reading the answers would be 11,313.77 (022) and 19,803.80 (076). 062 and 112 do not move the key: 062's key is 0 for another cause (pe-survivor-benefits-not-income; under that entry's answer the other reading adds 115.03, the TAXSIM comparer's 'both readings defensible'), and 112 owes 0 either way.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** results/repro/reading_experiments_pe_2.60.0.txt and results/repro/reading_experiments_pe_2.116.15.txt (R10: rent with basis is qualified business income, 0 with rental_income_would_be_qualified false); policyengine_us/variables/household/income/person/misc/rental_income_would_be_qualified.py:13; evidence/traces/builder-2.md (item 8); second_map/taxcalc/answers_2026.csv and second_map/taxsim/answers_2026.csv; docs/second-map-taxsim.md (062 +115.03, both_readings_defensible); Tax-Calculator counterfactual runs on the inputs in results/dossiers with e27200 0: 022 11,313.77, 076 19,803.80, 062 4,443.42, 112 0.00; keycheck/unit.py:107 READINGS rental_qbi.
- **Source:** evidence/traces/builder-2.md, docs/second-map-taxcalc.md, docs/second-map-taxsim.md, results/repro/reading_experiments_pe_2.60.0.txt.
- **Households where every answer moves alike (no cell rows):** 022, 062, 076, 112.
- **Positions on the key's 2026 answers:** 022 (tax before refundable credits) `turns_on_unstated_fact`, key 11,113.57, other reading 11,313.77; 062 (tax before refundable credits) `no_effect`; 076 (tax before refundable credits) `turns_on_unstated_fact`, key 19,611.80, other reading 19,803.80; 112 (tax before refundable credits) `no_effect`.

### `shared-private-pension-no-early-distribution-tax`: A private pension paid before age 59 1/2 carries no additional tax

*Kind* `shared-reading`. *Moves* `policybench-key`, `policyengine-us`, `taxcalc`, `taxsim`. *Law years* both. *Entry* open.

Six households state a taxable private pension paid to a filer under 59 1/2: 007 (56, 35,280), 009 (57, 20,400), 025 (the spouse, 57, 32,200), 036 (56, 59,220), 073 (57, 3,108) and 088 (56, 1,862). No answer adds the 10% additional tax on early distributions to them: the maps tax only IRA, 401(k), 403(b) and SEP distributions, which name their plans.

- **Where it holds:** policyengine-us 2.60.0 and 2.116.15 (no 72(t) formula); keycheck 2026-11-11.1 READINGS retirement_penalty (no 72(t) tax on a private pension); TAXSIM has no input for the tax.
- **Law:** 26 U.S.C. 72(t)(1) (the tax applies to an amount from a qualified retirement plan as 4974(c) defines it); 72(q) (a 10% tax on an annuity contract that is not such a plan); 72(t)(2)(A)(iv) and (v) (no tax on substantially equal payments for life, or after separation from service after 55). **Figure:** 10% of the taxable pension less the medical exception: 3,528.00 (007), 2,040.00 (009), 3,201.94 (025), 5,922.00 (036), 74.11 (073).
- **Who is right (this entry's position):** All four, under the prompt rule. The tax needs a fact the board does not state: that the pension comes from a qualified retirement plan (4974(c)) or an annuity contract (72(q)); and a pension in payment at 56 or 57 may meet an exception (life annuity payments, or separation from service after 55) the board does not state either. The Tax-Calculator comparer's list of fixes would tax the pensions: on that reading 007 would be 7,235.69, 009 10,388.00, 025 10,232.97, 036 10,848.40 and 073 74.11 (Tax-Calculator counterfactual runs with the tax as e09900), all scored; 088's head states a disability and no earnings, which the maps read as 72(m)(7) disability, so 088 stays at 0. The second Tax-Calculator map, written blind, taxes none of them.
- **Existing report:** none found that describes the same behaviour.
- **Evidence:** second_map/taxcalc/sources/usc26_72.txt:405 (72(q)), :517 (72(t)(1)), :527 and :529 (exceptions (iv) and (v)); evidence/traces/builder-2.md (item 4, the comparer's alternative); second_map/taxcalc/answers_2026.csv (equal to the first map's answers on 007, 009, 025, 036, 073 and 088); Tax-Calculator counterfactual runs on the inputs in results/dossiers with e09900 set to keycheck/statute.py early_distribution_tax of the taxable pension; keycheck/unit.py:152 READINGS retirement_penalty.
- **Source:** evidence/traces/builder-2.md, docs/second-map-taxcalc.md.
- **Households where every answer moves alike (no cell rows):** 007, 009, 025, 036, 073, 088.
- **Positions on the key's 2026 answers:** 007 (tax before refundable credits) `supports_key` on the prompt rule, key 3,707.70, other reading 7,235.69; 009 (tax before refundable credits) `supports_key` on the prompt rule, key 8,348.00, other reading 10,388.00; 025 (tax before refundable credits) `supports_key` on the prompt rule, key 7,031.04, other reading 10,232.97; 036 (tax before refundable credits) `supports_key` on the prompt rule, key 4,926.40, other reading 10,848.40; 073 (tax before refundable credits) `supports_key` on the prompt rule, key 0.00, other reading 74.11; 088 (tax before refundable credits) `no_effect`.

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
- **Positions on the key's 2026 answers:** 016 (tax before refundable credits) `no_effect`; 072 (tax before refundable credits) `no_effect`; 114 (tax before refundable credits) `supports_key` on the prompt rule; 121 (tax before refundable credits) `supports_key` on the prompt rule.

## Cells that are not all_agree in the 2026 key table

Each row is a household and line of `results/agreement/board100_2026_key.csv` whose answers differ by more than $1. "Scored" says whether the board scores the output (it excludes the rest). The policyengine-us column comes from the rerun table, `results/agreement/board100_2026_rerun.csv`. The last column lists each cause with the amount it adds to each answer it moves in the 2026 table (key, policyengine-us, Tax-Calculator, TAXSIM).

| Case | Line | Class | Scored | Key | policyengine-us 2.60.0 | Tax-Calculator | TAXSIM | Causes and amounts |
|---|---|---|---|---:|---:|---:|---:|---|
| 000 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 2,906.45 | 2,906.45 | 2,906.45 | 2,337.46 | `taxsim-no-tax-exempt-interest-input` (ts -568.99) |
| 002 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 0.00 | 1,890.30 | 1,890.30 | 1,890.30 | `shared-disability-benefits-taxable` (pe 1,890.30, tc 1,890.30, ts 1,890.30) |
| 005 | federal_income_tax_before_refundable_credits | all_differ | no | 106,505.90 | 108,525.58 | 108,525.58 | 108,867.91 | `taxsim-no-nonitemizer-charitable-deduction` (ts 342.33); `key-ira-deducted-without-219g` (key -692.44); `shared-state-tax-refund-counted-in-full` (pe 1,327.24, tc 1,327.25, ts 1,327.26) |
| 020 | federal_income_tax_before_refundable_credits | all_differ | no | 68,056.71 | 68,334.73 | 70,332.82 | 70,401.42 | `taxsim-no-nonitemizer-charitable-deduction` (ts 68.60); `pe-divorce-year-default` (key -1,998.09, pe -1,998.09); `key-sales-tax-table-column-shift` (key -278.02) |
| 023 | federal_income_tax_before_refundable_credits | two_agree:taxcalc | yes | 643.43 | 643.43 | 1,443.43 | 643.43 | `taxsim-no-early-distribution-tax-input` (ts -800.00); `pe-early-distribution-tax-not-computed` (key -800.00, pe -800.00) |
| 030 | federal_income_tax_before_refundable_credits | two_agree:policyengine | yes | 0.00 | 0.00 | 190.00 | 190.00 | `pe-scholarship-not-income` (key -190.00, pe -190.00) |
| 037 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 1,649.25 | 1,649.25 | 1,649.25 | 2,804.73 | `taxsim-no-overtime-deduction` (ts 1,155.48) |
| 046 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 499.71 | 499.71 | 499.71 | 2,280.36 | `taxsim-no-overtime-deduction` (ts 1,780.65) |
| 049 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 30,702.59 | 30,702.59 | 30,702.59 | 36,330.14 | `taxsim-no-overtime-deduction` (ts 5,500.00); `taxsim-no-nonitemizer-charitable-deduction` (ts 127.55) |
| 052 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 104,211.41 | 104,225.26 | 104,225.25 | 104,225.25 | `key-ira-deducted-without-219g` (key -13.85) |
| 055 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 25,238.58 | 25,238.58 | 25,238.58 | 25,478.58 | `taxsim-no-nonitemizer-charitable-deduction` (ts 240.00) |
| 062 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 0.00 | 0.00 | 4,328.39 | 4,328.39 | `pe-survivor-benefits-not-income` (key -4,328.39, pe -4,328.39) |
| 064 | federal_income_tax_before_refundable_credits | all_differ | yes | 4,441.46 | 4,441.46 | 6,441.45 | 6,109.37 | `taxsim-no-overtime-deduction` (ts 1,667.91); `taxsim-no-early-distribution-tax-input` (ts -2,000.00); `pe-early-distribution-tax-not-computed` (key -2,000.00, pe -2,000.00) |
| 068 | federal_income_tax_before_refundable_credits | two_agree:policyengine | yes | 1,910.02 | 1,910.02 | 14,728.38 | 14,728.38 | `pe-scholarship-not-income` (key -12,818.36, pe -12,818.36) |
| 070 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 1,979.96 | 1,979.96 | 1,979.96 | 2,172.36 | `taxsim-no-savers-credit` (ts 192.40) |
| 074 | federal_income_tax_before_refundable_credits | two_agree:taxcalc | yes | 0.00 | 0.00 | 38.40 | 0.00 | `taxsim-no-early-distribution-tax-input` (ts -38.40); `pe-early-distribution-tax-not-computed` (key -38.40, pe -38.40) |
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
| 120 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 40,021.82 | 40,423.18 | 40,454.89 | 40,454.90 | `pe-net-investment-income-leaves-out-farm-rent` (key 92.97, pe 92.97); `pe-no-passive-activity-loss-limit` (key -124.69, pe -124.69); `key-ira-deducted-without-219g` (key -6.50); `shared-state-tax-refund-counted-in-full` (pe 394.86, tc 394.86, ts 394.86) |
| 121 | federal_income_tax_before_refundable_credits | two_agree:policyengine | no | 0.00 | 875.34 | 875.34 | 875.34 | `shared-disability-benefits-taxable` (pe 875.34, tc 875.34, ts 875.34) |
| 122 | federal_income_tax_before_refundable_credits | two_agree:taxsim | yes | 4,746.66 | 4,746.66 | 4,746.66 | 4,984.17 | `taxsim-no-nonitemizer-charitable-deduction` (ts 120.00); `taxsim-no-tax-exempt-interest-input` (ts -128.49); `taxsim-no-blindness-input` (ts 246.00) |
| 123 | federal_income_tax_before_refundable_credits | two_agree:taxsim | no | 5,200.24 | 5,200.24 | 5,200.24 | 5,440.24 | `taxsim-no-nonitemizer-charitable-deduction` (ts 240.00) |
| 026 | federal_refundable_credits | two_agree:taxsim | yes | 2,013.49 | 2,013.49 | 2,013.49 | 1,083.94 | `taxsim-no-overtime-deduction` (ts -929.55) |
| 038 | federal_refundable_credits | two_agree:taxsim | yes | 10,225.35 | 10,225.35 | 10,225.35 | 10,210.35 | `map-ira-deduction-in-nonprop-cuts-eitc` (ts -15.00) |
| 100 | federal_refundable_credits | two_agree:taxsim | yes | 822.29 | 822.29 | 822.29 | 750.16 | `map-ira-deduction-in-nonprop-cuts-eitc` (ts -72.13) |
| 109 | federal_refundable_credits | two_agree:taxsim | yes | 12,038.09 | 12,038.09 | 12,038.09 | 12,469.86 | `taxsim-three-child-refundable-credit-alternative` (ts 431.77) |
| 119 | federal_refundable_credits | two_agree:taxsim | yes | 3,366.07 | 3,366.07 | 3,366.07 | 2,620.08 | `taxsim-no-savers-credit` (ts -200.00); `taxsim-2026-child-care-credit-old-rates` (ts -234.00); `taxsim-refundable-child-credit-ignores-child-care-credit` (ts -312.00) |

## Causes that would change a scored answer

Four scored outputs hold a committed answer that, on the entries above, the law or the prompt rule does not support. Each proposal gives the answer that would follow and how this repo computed it. This repo changes nothing on the board, and every entry stays open.

| Case | Line | Committed key | Answer that would follow | Change | Cause | Grounds | How this repo got the answer |
|---|---|---:|---:|---:|---|---|---|
| 030 | tax before refundable credits | 0.00 | 190.00 | +190.00 | `pe-scholarship-not-income` | the prompt rule | the key less this entry's amount on the key's run; Tax-Calculator's and TAXSIM's answer |
| 064 | tax before refundable credits | 4,441.46 | 6,441.46 | +2,000.00 | `pe-early-distribution-tax-not-computed` | the law | the key less this entry's amount on the key's run; Tax-Calculator gives 6,441.45. The proposal rests on the line holding the tax: the board's reference engine adds qualified_retirement_penalty to this line when a household states it, and 72(t) is chapter 1 income tax; Form 1040 reports it with the other taxes on Schedule 2, Part II (second_map/taxcalc/sources/i1040gi.txt:90-92), the question shared-net-investment-income-tax-in-line leaves open for the net investment income tax |
| 068 | tax before refundable credits | 1,910.02 | 14,728.38 | +12,818.36 | `pe-scholarship-not-income` | the prompt rule | the key less this entry's amount on the key's run; Tax-Calculator's and TAXSIM's answer |
| 082 | tax before refundable credits | 9,579.77 | 9,564.92 | -14.85 | `shared-state-tax-refund-counted-in-full` | the prompt rule | Tax-Calculator counterfactual run on the inputs in results/dossiers with e00700 0 |

- **030.** Standing of the key's answer: resting on one model; this account contests it. Tax-Calculator and TAXSIM give the answer that would follow, within $1.
- **064.** Standing of the key's answer: resting on one model; this account contests it. Tax-Calculator gives the answer that would follow, within $1.
- **068.** Standing of the key's answer: resting on one model; this account contests it. Tax-Calculator and TAXSIM give the answer that would follow, within $1.
- **082.** Standing of the key's answer: reproduced by a run of another lineage (Tax-Calculator); this account contests it. No run of another lineage gives the answer that would follow.

### Scored answers that rest on an open reading

No proposal follows for these: each turns on a fact the board does not state, and the entry takes no side.

| Case | Line | Committed key | Answer on the other reading | Change | Cause | How this repo got the answer |
|---|---|---:|---:|---:|---|---|
| 023 | tax before refundable credits | 643.43 | 1,443.43 | +800.00 | `pe-early-distribution-tax-not-computed` | Tax-Calculator's answer, with the tax; 72(m)(7) disability: stated disabled, with wages under the 2026 monthly amount for substantial gainful activity; the second Tax-Calculator map reads the stated disability as 72(m)(7) and gives the key's 643.43 |
| 042 | tax before refundable credits | 2,361.96 | 2,377.71 | +15.75 | `shared-bdc-income-not-added` | Tax-Calculator counterfactual run on the inputs in results/dossiers with e00600 raised by 70.94 (its base, 2,361.97, equals the key within $0.01) |
| 074 | tax before refundable credits | 0.00 | 38.40 | +38.40 | `pe-early-distribution-tax-not-computed` | Tax-Calculator's answer, with the tax; 72(m)(7) disability: Social Security disability benefits and no stated disability; the second Tax-Calculator map reads the benefits as 72(m)(7) disability and gives the key's 0.00 |
| 076 | tax before refundable credits | 19,611.80 | 19,803.80 | +192.00 | `shared-rental-with-basis-qualified-business-income` | Tax-Calculator counterfactual run on the inputs in results/dossiers with e27200 0 (its base equals the key); the second Tax-Calculator map, written blind, gives the same answer |

- **023.** Standing of the key's answer: reproduced by a run of another lineage (TAXSIM). TAXSIM's answer carries `taxsim-no-early-distribution-tax-input` (-800.00). Tax-Calculator gives 1,443.43.
- **042.** Standing of the key's answer: reproduced by a run of another lineage (Tax-Calculator and TAXSIM).
- **074.** Standing of the key's answer: reproduced by a run of another lineage (TAXSIM). TAXSIM's answer carries `taxsim-no-early-distribution-tax-input` (-38.40). Tax-Calculator gives 38.40.
- **076.** Standing of the key's answer: reproduced by a run of another lineage (Tax-Calculator and TAXSIM).

### Scored answers the entries support against a named alternative

The entries below support the key's answer but name the answer another reading gives, so a reader can weigh the reading.

| Case | Line | Committed key | Alternative | Change | Cause | Grounds | How this repo got the alternative |
|---|---|---:|---:|---:|---|---|---|
| 007 | tax before refundable credits | 3,707.70 | 7,235.69 | +3,527.99 | `shared-private-pension-no-early-distribution-tax` | the prompt rule | Tax-Calculator counterfactual run on the inputs in results/dossiers with e09900 set to the tax keycheck/statute.py early_distribution_tax gives (its base equals the key) |
| 009 | tax before refundable credits | 8,348.00 | 10,388.00 | +2,040.00 | `shared-private-pension-no-early-distribution-tax` | the prompt rule | Tax-Calculator counterfactual run on the inputs in results/dossiers with e09900 set to the tax keycheck/statute.py early_distribution_tax gives (its base equals the key) |
| 025 | tax before refundable credits | 7,031.04 | 10,232.97 | +3,201.93 | `shared-private-pension-no-early-distribution-tax` | the prompt rule | Tax-Calculator counterfactual run on the inputs in results/dossiers with e09900 set to the tax keycheck/statute.py early_distribution_tax gives (its base equals the key) |
| 036 | tax before refundable credits | 4,926.40 | 10,848.40 | +5,922.00 | `shared-private-pension-no-early-distribution-tax` | the prompt rule | Tax-Calculator counterfactual run on the inputs in results/dossiers with e09900 set to the tax keycheck/statute.py early_distribution_tax gives (its base equals the key) |
| 073 | tax before refundable credits | 0.00 | 74.11 | +74.11 | `shared-private-pension-no-early-distribution-tax` | the prompt rule | Tax-Calculator counterfactual run on the inputs in results/dossiers with e09900 set to the tax keycheck/statute.py early_distribution_tax gives (its base equals the key) |

The other scored cells that are not all_agree (000, 037, 046, 049, 055, 070, 089, 091, 099, 110, 122 on tax before refundable credits; 026, 038, 100, 109, 119 on refundable credits) hold a key answer that every entry explaining them supports: TAXSIM lacks a provision or departs from the law, or this repo's TAXSIM map cannot express a fact.

### Excluded outputs where an entry disputes the key or leaves it open

The board scores none of these, so no proposal follows; the table shows where the key and the entries part. Each row is one entry's position. The last answer column gives the answer the entry supports where it supports a different one, and otherwise the answer the other reading gives.

| Case | Line | Committed key | Cause | Position | Answer the entry names | How this repo got the answer |
|---|---|---:|---|---|---:|---|
| 002 | tax before refundable credits | 0.00 | `shared-disability-benefits-taxable` | supports_key (the prompt rule) | 1,890.30 | the board record's alternative, which policyengine-us 2.60.0, Tax-Calculator and TAXSIM give |
| 005 | tax before refundable credits | 106,505.90 | `key-ira-deducted-without-219g` | supports_other_answer (the law) | 107,198.34 | the key less this entry's amount on the key's run; equal to the board record's alternative |
| 005 | tax before refundable credits | 106,505.90 | `shared-net-investment-income-tax-in-line` | turns_on_unstated_fact | 100,783.92 | the key less policyengine-us 2.60.0's net investment income tax (5,721.98): an inference that the frozen value holds the same tax; the 1411 tax is chapter 2A, not chapter 1 income tax; the board's reference engine puts it in this line, and the board excludes 020 on the question |
| 020 | tax before refundable credits | 68,056.71 | `pe-divorce-year-default` | supports_other_answer (the prompt rule) | 70,054.80 | the key less this entry's amount on the key's run; with key-sales-tax-table-column-shift too: 70,332.82, Tax-Calculator's answer |
| 020 | tax before refundable credits | 68,056.71 | `key-sales-tax-table-column-shift` | supports_other_answer (the law) | 68,334.73 | the key less this entry's amount on the key's run (the board's 2.15.17 value) |
| 020 | tax before refundable credits | 68,056.71 | `shared-net-investment-income-tax-in-line` | turns_on_unstated_fact | 67,834.07 | the key less policyengine-us 2.60.0's net investment income tax (222.64): an inference that the frozen value holds the same tax; the 1411 tax is chapter 2A, not chapter 1 income tax; the board's reference engine puts it in this line, and the board excludes 020 on the question |
| 022 | tax before refundable credits | 11,113.57 | `shared-state-income-tax-withholding-estimate` | supports_other_answer (the prompt rule) | 12,234.66 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e18400 963.00, the engine's sales tax amount (its base equals the key); the board record's alternative reads the engine's state liability: 11,895.23 |
| 022 | tax before refundable credits | 11,113.57 | `shared-rental-with-basis-qualified-business-income` | turns_on_unstated_fact | 11,313.77 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e27200 0 (its base equals the key); the second TAXSIM map, written blind, gives the same answer |
| 033 | tax before refundable credits | 3,818.15 | `shared-state-tax-refund-counted-in-full` | supports_other_answer (the prompt rule) | 3,788.99 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e00700 0; equal to the board record's alternative |
| 052 | tax before refundable credits | 104,211.41 | `key-ira-deducted-without-219g` | supports_other_answer (the law) | 104,225.26 | the key less this entry's amount on the key's run; equal to the board record's alternative |
| 052 | tax before refundable credits | 104,211.41 | `shared-net-investment-income-tax-in-line` | turns_on_unstated_fact | 103,992.99 | the key less policyengine-us 2.60.0's net investment income tax (218.42): an inference that the frozen value holds the same tax; the 1411 tax is chapter 2A, not chapter 1 income tax; the board's reference engine puts it in this line, and the board excludes 020 on the question |
| 062 | tax before refundable credits | 0.00 | `pe-survivor-benefits-not-income` | supports_other_answer (the prompt rule) | 4,328.39 | the key less this entry's amount on the key's run; Tax-Calculator's answer and the board record's alternative |
| 078 | tax before refundable credits | 24,164.46 | `shared-state-tax-refund-counted-in-full` | supports_other_answer (the prompt rule) | 23,772.80 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e00700 0; equal to the board record's alternative |
| 078 | tax before refundable credits | 24,164.46 | `shared-state-income-tax-withholding-estimate` | supports_other_answer (the prompt rule) | 27,290.70 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e18400 914.00 (its base equals the key) |
| 081 | tax before refundable credits | 26,932.27 | `shared-state-income-tax-withholding-estimate` | supports_other_answer (the prompt rule) | 28,763.81 | the key plus the change in a Tax-Calculator counterfactual run on the inputs in results/dossiers with e18400 853.00 (+1,831.54); the board record's alternative reads the engine's state liability: 26,991.31 |
| 093 | tax before refundable credits | 8,628.99 | `pe-other-dependent-credit-without-dependency-tests` | supports_other_answer (the law) | 9,128.99 | the key less this entry's amount on the key's run; for the head's return; shared-head-return-only leaves open whether the line adds the member's own return |
| 093 | tax before refundable credits | 8,628.99 | `shared-head-return-only` | turns_on_unstated_fact | 11,848.99 | the board record's alternative (the member's own return adds 3,220.00) |
| 107 | tax before refundable credits | 0.00 | `shared-disability-benefits-taxable` | supports_key (the prompt rule) | 211.23 | the board record's alternative, which policyengine-us 2.60.0, Tax-Calculator and TAXSIM give |
| 114 | tax before refundable credits | 10,729.61 | `pe-medicare-part-b-premium-default` | supports_other_answer (the prompt rule) | 11,265.27 | the key less this entry's amount on the key's run; policyengine-us with takes_up_medicare_if_eligible false gives the same 11,265.27 |
| 114 | tax before refundable credits | 10,729.61 | `shared-state-income-tax-withholding-estimate` | supports_other_answer (the prompt rule) | 11,783.48 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e18400 577.00 and the key's Medicare Part B premium added to e17500 (which gives the key's 10,729.61 without the change); the board record's alternative reads the engine's state liability: 11,137.31; with pe-medicare-part-b-premium-default's position too, 11,969.81 |
| 117 | tax before refundable credits | 24,961.34 | `shared-state-tax-refund-counted-in-full` | supports_other_answer (the prompt rule) | 24,391.80 | Tax-Calculator counterfactual run on the inputs in results/dossiers with e00700 0; equal to the board record's alternative |
| 120 | tax before refundable credits | 40,021.82 | `pe-net-investment-income-leaves-out-farm-rent` | supports_other_answer (the law) | 39,928.85 | the key less this entry's amount on the key's run |
| 120 | tax before refundable credits | 40,021.82 | `pe-no-passive-activity-loss-limit` | supports_other_answer (the law) | 40,146.51 | the key less this entry's amount on the key's run; the key's other entries move it too; with every entry that moves the key, 40,060.04, which a Tax-Calculator counterfactual run gives with the refund out and the board's state and local tax |
| 120 | tax before refundable credits | 40,021.82 | `key-ira-deducted-without-219g` | supports_other_answer (the law) | 40,028.32 | the key less this entry's amount on the key's run; equal to the board record's alternative |
| 120 | tax before refundable credits | 40,021.82 | `shared-net-investment-income-tax-in-line` | turns_on_unstated_fact | 39,858.42 | the key less policyengine-us 2.60.0's net investment income tax (163.40): an inference that the frozen value holds the same tax; the 1411 tax is chapter 2A, not chapter 1 income tax; the board's reference engine puts it in this line, and the board excludes 020 on the question |
| 120 | tax before refundable credits | 40,021.82 | `shared-state-income-tax-withholding-estimate` | supports_other_answer (the prompt rule) | 43,263.75 | the key plus the change in a Tax-Calculator counterfactual run on the inputs in results/dossiers with e18400 1,197.00 (+3,241.93): an inference that the key's return moves alike |
| 120 | tax before refundable credits | 40,021.82 | `shared-state-paid-leave-contributions-not-in-salt` | supports_other_answer (the law) | 39,823.10 | the key plus the change in a Tax-Calculator counterfactual run on the inputs in results/dossiers with e18400 raised by 827.98 (-198.72): an inference that the key's return moves alike; the board's record gives 40,217.95 on 2.15.17 |
| 120 | tax before refundable credits | 40,021.82 | `shared-mortgage-debt-after-2017` | supports_key (the prompt rule) | 39,797.18 | the key less the 224.64 the board's record gives for older debt |
| 121 | tax before refundable credits | 0.00 | `shared-disability-benefits-taxable` | supports_key (the prompt rule) | 875.34 | the board record's alternative, which policyengine-us 2.60.0, Tax-Calculator and TAXSIM give |
| 123 | tax before refundable credits | 5,200.24 | `shared-head-return-only` | turns_on_unstated_fact | 8,420.24 | the board record's alternative (the member's own return adds 3,220.00) |

Where several entries move one excluded output, their changes need not add: a Tax-Calculator counterfactual run gives the combined answer where an entry's note cites one.

## Entries this pass replaced

Map version 2026-11-11.1 made four earlier entries moot or wrong. Their ids no longer appear in the tables.

- `shared-scholarship-not-income` gave way to `pe-scholarship-not-income`: the maps now count a stated scholarship as income, so only policyengine-us and the key leave it out. The earlier entry said 030 owes 0 either way; it does not: counting the scholarship moves 030 by 190.00 in 2026 and 225.00 in 2025.
- `shared-survivor-benefits-not-taxable` gave way to `pe-survivor-benefits-not-income`: the maps now count stated survivor benefits as income, so only policyengine-us and the key leave them out.
- `shared-passive-rental-loss-allowed` gave way to `pe-no-passive-activity-loss-limit`: the maps now suspend a net passive loss under 26 U.S.C. 469, which policyengine-us does not compute.
- `map-rental-not-qualified-business-income` gave way to `shared-rental-with-basis-qualified-business-income`: the maps now read a rental with a stated basis of qualified property as a qualified trade or business, as policyengine-us does, so no answer differs on it; the reading stays open, since both second maps read the rent the other way.
