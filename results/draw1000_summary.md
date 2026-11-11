# The 1,000-household draw: three models compared (tax year 2026)

scripts/draw_summary/summarize.py writes this page and its CSV from the git-ignored local draw files (the board column of the composition table comes from the committed dossiers and board Tax-Calculator run). This summary compares PolicyEngine (policyengine-us 2.60.0 with the board's conventions), Tax-Calculator 6.9.0 and NBER TAXSIM (build cd2026110117) on the 1,000 households of the draw (seed 20261110), for tax year 2026. The input maps are keycheck version 2026-11-11.1. No committed key exists for the draw, so PolicyEngine's own run stands as its answer. Two answers agree when they differ by no more than $1. The record-level files stay out of git; this page and its CSV hold aggregates only.

## Agreement by line

| Line | Households | All agree | PolicyEngine apart | Tax-Calculator apart | TAXSIM apart | All differ |
|---|---:|---:|---:|---:|---:|---:|
| Income tax before refundable credits | 1000 | 501 (50.1%) | 53 (5.3%) | 5 (0.5%) | 273 (27.3%) | 168 (16.8%) |
| Refundable credits | 1000 | 919 (91.9%) | 15 (1.5%) | 0 (0.0%) | 58 (5.8%) | 8 (0.8%) |
| Self-employment tax | 1000 | 987 (98.7%) | 3 (0.3%) | 0 (0.0%) | 10 (1.0%) | 0 (0.0%) |
| Employee payroll tax (federal) | 1000 | 1000 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

## Differences explained in kind

For each household and line where the models do not all agree, this section asks whether the evidence explains the difference in kind. A cell counts as explained when one of these holds for the model that stands apart:

- TAXSIM or Tax-Calculator apart: that model's map carries a note of its own on the line, for a fact the map could not express or a limit of the model (several found by probes of the TAXSIM build); for Tax-Calculator, also the additional tax on early distributions (26 U.S.C. 72(t)), which only its map can send.
- PolicyEngine apart (it carries no notes): both maps carry a note that names PolicyEngine's different treatment (its full deduction of investment interest, its 162(l) deduction, its default divorce year for alimony, its default that rent is qualified business income, its count of care expenses, no passive activity loss limit, the stated HSA deduction taken whole, a scholarship or survivor benefits left out of income, the Alaska dividend it adds); or both maps note a fact that neither Tax-Calculator nor TAXSIM can take, so those two agree without it; or PolicyEngine's own run shows it took the other side of a reading both maps share (it claims a member the maps leave out, it does not count a disabled adult as an EITC child, it files a different status, or its medical expense deduction exceeds the stated amounts' at the same AGI). The run's per-person outputs show which side it took; this unit did not read PolicyEngine's code for why.
- All three differ: any of the above on any model.

A reading both maps share, with no sign of PolicyEngine taking the other side, does not explain why one model stands apart, so it does not count; the table shows how many unexplained cells carry only such notes. Notes say what kind of difference to expect, not its size: this unit traced no dollars, so a cell can count as explained by a note whose effect is smaller than the gap.

| Line | Class | Cells | Explained | Unexplained | Of which only shared notes |
|---|---|---:|---:|---:|---:|
| Income tax before refundable credits | PolicyEngine apart | 53 | 53 | 0 | 0 |
| Income tax before refundable credits | Tax-Calculator apart | 5 | 5 | 0 | 0 |
| Income tax before refundable credits | TAXSIM apart | 273 | 273 | 0 | 0 |
| Income tax before refundable credits | All differ | 168 | 168 | 0 | 0 |
| Refundable credits | PolicyEngine apart | 15 | 15 | 0 | 0 |
| Refundable credits | TAXSIM apart | 58 | 58 | 0 | 0 |
| Refundable credits | All differ | 8 | 8 | 0 | 0 |
| Self-employment tax | PolicyEngine apart | 3 | 3 | 0 | 0 |
| Self-employment tax | TAXSIM apart | 10 | 10 | 0 | 0 |
| All lines | All classes | 593 | 593 | 0 | 0 |

Of 593 cells where the models do not all agree, 593 (100.0%) have evidence that explains the difference in kind and 0 (0.0%) have none. Read literally (any note at all on the line of the model that stands apart, shared readings included, and for PolicyEngine any note both maps carry), 593 cells carry one.

### Note families behind the explained cells

A cell can carry more than one family, so the counts add up to more than the explained cells.

| Line | Class | Model the note concerns | Note family | Cells |
|---|---|---|---|---:|
| Income tax before refundable credits | All differ | TAXSIM | no charitable deduction for non-itemizers | 84 |
| Income tax before refundable credits | All differ | TAXSIM | other taxable income entered as pensions | 54 |
| Income tax before refundable credits | All differ | TAXSIM | adjustments cut earned income (EITC, refundable child credit) | 54 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | reading: rent and farm rent QBI only with a stated basis (PE's default counts all rent) | 49 |
| Income tax before refundable credits | All differ | Tax-Calculator | employee expenses zeroed | 49 |
| Income tax before refundable credits | All differ | TAXSIM | no vehicle loan interest input | 48 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | no REIT/PTP input | 47 |
| Income tax before refundable credits | All differ | Tax-Calculator | no REIT/PTP input | 47 |
| Income tax before refundable credits | All differ | TAXSIM | no REIT/PTP input | 47 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | 72(t) tax: Tax-Calculator computes it; TAXSIM has no input and PolicyEngine holds none | 43 |
| Income tax before refundable credits | All differ | TAXSIM | no 72(t) input (PolicyEngine holds none either) | 43 |
| Income tax before refundable credits | All differ | TAXSIM | no 2026 minimum QBI deduction | 41 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | passive partnership income is NII and EITC investment income (PE reads it as nonpassive) | 40 |
| Income tax before refundable credits | All differ | TAXSIM | no overtime input | 40 |
| Income tax before refundable credits | All differ | TAXSIM | rent that is not QBI and estate income in intrec | 35 |
| Income tax before refundable credits | All differ | TAXSIM | no tax-exempt interest input | 26 |
| Income tax before refundable credits | All differ | TAXSIM | SE health and pension deductions in nonprop (earned income cut, QBI not) | 24 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | 163(d) limit (PE deducts all investment interest) | 23 |
| Income tax before refundable credits | All differ | TAXSIM | no 199A wage or property limit | 23 |
| Income tax before refundable credits | All differ | TAXSIM | no nontaxable pension input | 23 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | reading: scholarship taxable (PE leaves it out) | 20 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | 469 passive loss disallowed (PE applies no 469 limit) | 20 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | HSA deduction capped at 223(b) (PE takes the stated amount) | 15 |
| Income tax before refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine claims a disabled member with earnings of their own (is_disabled reading) | 14 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | 162(l) (PE needs is_self_employed and limits to Schedule C income) | 12 |
| Income tax before refundable credits | All differ | TAXSIM | 2026 zero rate on gains runs past Rev. Proc. 2025-32 (D6) | 12 |
| Income tax before refundable credits | All differ | Tax-Calculator | scholarship through e01200 | 11 |
| Income tax before refundable credits | All differ | TAXSIM | no saver's credit input | 10 |
| Income tax before refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading) | 10 |
| Income tax before refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine's medical expense deduction exceeds the stated amounts' at the same AGI (medical readings) | 10 |
| Income tax before refundable credits | All differ | TAXSIM | 2026 care credit at pre-2026 rates | 9 |
| Income tax before refundable credits | All differ | TAXSIM | no 25%/28% rate gain input | 8 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | care expenses of a non-qualifying person | 7 |
| Income tax before refundable credits | All differ | TAXSIM | no blindness input | 6 |
| Income tax before refundable credits | All differ | Tax-Calculator | 199A(i) floor tests all QBI (the statute: active trades only) | 4 |
| Income tax before refundable credits | All differ | Tax-Calculator | miscellaneous income through e01200 | 4 |
| Income tax before refundable credits | All differ | TAXSIM | care credit counts children under 13 only | 3 |
| Income tax before refundable credits | All differ | Tax-Calculator | disability benefits through e01200 | 2 |
| Income tax before refundable credits | All differ | Tax-Calculator | one SSTB flag per unit | 2 |
| Income tax before refundable credits | All differ | TAXSIM | passive partnership income and qualified rent in scorp | 2 |
| Income tax before refundable credits | All differ | TAXSIM | child credit phase-out without the $1,000 step | 2 |
| Income tax before refundable credits | All differ | Tax-Calculator | charity ceilings differ from 170(b)(1) as read | 1 |
| Income tax before refundable credits | All differ | TAXSIM | a loss in one self-employment box does not offset the other (P7.4, D4) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | domestic production deduction | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | domestic production deduction zeroed | 1 |
| Income tax before refundable credits | All differ | TAXSIM | domestic production deduction left out | 1 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | reading: alimony (PE's default makes it pre-2019) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | alimony no effect | 1 |
| Income tax before refundable credits | All differ | TAXSIM | alimony left out | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | no deemed earned income (21(d)(2)) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | no deemed earned income (21(d)(2)) | 1 |
| Income tax before refundable credits | All differ | TAXSIM | no deemed earned income (21(d)(2)) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | Form 4952 election from dividends only | 1 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: rent and farm rent QBI only with a stated basis (PE's default counts all rent) | 23 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | 163(d) limit (PE deducts all investment interest) | 13 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | passive partnership income is NII and EITC investment income (PE reads it as nonpassive) | 10 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine's medical expense deduction exceeds the stated amounts' at the same AGI (medical readings) | 9 |
| Income tax before refundable credits | PolicyEngine apart | Tax-Calculator and TAXSIM | no REIT/PTP input | 9 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | 469 passive loss disallowed (PE applies no 469 limit) | 7 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a disabled member with earnings of their own (is_disabled reading) | 5 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: scholarship taxable (PE leaves it out) | 5 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | HSA deduction capped at 223(b) (PE takes the stated amount) | 3 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: alimony (PE's default makes it pre-2019) | 2 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | care expenses of a non-qualifying person | 2 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading) | 1 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: no Alaska dividend added (PE adds $1,000 a person) | 1 |
| Income tax before refundable credits | Tax-Calculator apart | Tax-Calculator and TAXSIM | 72(t) tax: Tax-Calculator computes it; TAXSIM has no input and PolicyEngine holds none | 5 |
| Income tax before refundable credits | Tax-Calculator apart | Tax-Calculator | no REIT/PTP input | 2 |
| Income tax before refundable credits | Tax-Calculator apart | Tax-Calculator | domestic production deduction zeroed | 1 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no vehicle loan interest input | 114 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no overtime input | 97 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | adjustments cut earned income (EITC, refundable child credit) | 97 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no charitable deduction for non-itemizers | 82 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no 2026 minimum QBI deduction | 61 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no saver's credit input | 37 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | other taxable income entered as pensions | 35 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no nontaxable pension input | 32 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | SE health and pension deductions in nonprop (earned income cut, QBI not) | 30 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no REIT/PTP input | 23 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | 2026 care credit at pre-2026 rates | 21 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no tax-exempt interest input | 18 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no blindness input | 12 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | 2026 zero rate on gains runs past Rev. Proc. 2025-32 (D6) | 7 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | rent that is not QBI and estate income in intrec | 5 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no 199A wage or property limit | 4 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no 25%/28% rate gain input | 3 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | child credit phase-out without the $1,000 step | 3 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | care credit counts children under 13 only | 1 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | passive partnership income and qualified rent in scorp | 1 |
| Refundable credits | All differ | PolicyEngine (note names it) | reading: scholarship taxable (PE leaves it out) | 5 |
| Refundable credits | All differ | Tax-Calculator | scholarship through e01200 | 5 |
| Refundable credits | All differ | TAXSIM | adjustments cut earned income (EITC, refundable child credit) | 5 |
| Refundable credits | All differ | TAXSIM | no saver's credit input | 5 |
| Refundable credits | All differ | TAXSIM | other taxable income entered as pensions | 5 |
| Refundable credits | All differ | TAXSIM | 2026 care credit at pre-2026 rates | 3 |
| Refundable credits | All differ | TAXSIM | no vehicle loan interest input | 3 |
| Refundable credits | All differ | TAXSIM | SE health and pension deductions in nonprop (earned income cut, QBI not) | 2 |
| Refundable credits | All differ | TAXSIM | no 2026 minimum QBI deduction | 2 |
| Refundable credits | All differ | TAXSIM | no overtime input | 2 |
| Refundable credits | All differ | PolicyEngine (note names it) | 469 passive loss disallowed (PE applies no 469 limit) | 1 |
| Refundable credits | All differ | PolicyEngine (note names it) | 162(l) (PE needs is_self_employed and limits to Schedule C income) | 1 |
| Refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine does not count a disabled adult as an EITC child (is_disabled reading) | 1 |
| Refundable credits | All differ | PolicyEngine (note names it) | 163(d) limit (PE deducts all investment interest) | 1 |
| Refundable credits | All differ | Tax-Calculator | employee expenses zeroed | 1 |
| Refundable credits | All differ | TAXSIM | no charitable deduction for non-itemizers | 1 |
| Refundable credits | All differ | TAXSIM | no nontaxable pension input | 1 |
| Refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine does not count a disabled adult as an EITC child (is_disabled reading) | 8 |
| Refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: scholarship taxable (PE leaves it out) | 6 |
| Refundable credits | PolicyEngine apart | PolicyEngine (note names it) | care expenses of a non-qualifying person | 5 |
| Refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading) | 2 |
| Refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: rent and farm rent QBI only with a stated basis (PE's default counts all rent) | 1 |
| Refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a disabled member with earnings of their own (is_disabled reading) | 1 |
| Refundable credits | TAXSIM apart | TAXSIM | adjustments cut earned income (EITC, refundable child credit) | 23 |
| Refundable credits | TAXSIM apart | TAXSIM | no vehicle loan interest input | 22 |
| Refundable credits | TAXSIM apart | TAXSIM | no saver's credit input | 20 |
| Refundable credits | TAXSIM apart | TAXSIM | no 2026 minimum QBI deduction | 17 |
| Refundable credits | TAXSIM apart | TAXSIM | no overtime input | 16 |
| Refundable credits | TAXSIM apart | TAXSIM | 2026 care credit at pre-2026 rates | 12 |
| Refundable credits | TAXSIM apart | TAXSIM | SE health and pension deductions in nonprop (earned income cut, QBI not) | 8 |
| Refundable credits | TAXSIM apart | TAXSIM | no charitable deduction for non-itemizers | 7 |
| Refundable credits | TAXSIM apart | TAXSIM | other taxable income entered as pensions | 4 |
| Refundable credits | TAXSIM apart | TAXSIM | no nontaxable pension input | 1 |
| Refundable credits | TAXSIM apart | TAXSIM | no blindness input | 1 |
| Refundable credits | TAXSIM apart | TAXSIM | rent that is not QBI and estate income in intrec | 1 |
| Self-employment tax | PolicyEngine apart | PolicyEngine (note names it) | partner's SE loss cut with the disallowed passive loss (PE applies no 469 limit) | 3 |
| Self-employment tax | TAXSIM apart | TAXSIM | no $400 floor on self-employment tax (P10.3) | 9 |
| Self-employment tax | TAXSIM apart | TAXSIM | a loss in one self-employment box does not offset the other (P7.4, D4) | 1 |

## The largest unexplained differences

Only 0 cells have no explaining evidence, so this lists all of them, largest first (at most ten). Size: for one model apart, its distance from the mean of the two that agree; where all differ, the range of the three answers. Stated inputs: every input the household states that can reach a federal line (the inputs named as having no effect are left out). The last column says what the three runs' saved outputs show, without tracing dollars.

| Rank | Line | Class | Size ($) | Stated inputs | What the runs show |
|---:|---|---|---:|---|---|

## The draw beside the board

The draw is a separate sample of 1,000 households (seed 20261110), not the board, and its mix differs from the board's 100. Filing status is the one keycheck derives from the stated facts for 2026; itemizing is Tax-Calculator's own choice in its 2026 run.

| Measure | Board (100) | Draw (1,000) |
|---|---:|---:|
| Filing status: Single | 58 (58.0%) | 199 (19.9%) |
| Filing status: Married filing jointly | 35 (35.0%) | 709 (70.9%) |
| Filing status: Head of household | 7 (7.0%) | 91 (9.1%) |
| Filing status: Surviving spouse | 0 (0.0%) | 1 (0.1%) |
| Households with a member under 18 | 18 (18.0%) | 308 (30.8%) |
| Households with self-employment income | 13 (13.0%) | 274 (27.4%) |
| Households Tax-Calculator itemizes | 8 (8.0%) | 109 (10.9%) |

