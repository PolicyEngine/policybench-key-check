# The 1,000-household draw: three models compared (tax year 2026)

This summary compares PolicyEngine (policyengine-us 2.60.0 with the board's conventions), Tax-Calculator 6.9.0 and NBER TAXSIM (build cd2026110117) on the 1,000 households of the draw (seed 20261110), for tax year 2026. The input maps are keycheck version 2026-11-10.3. No committed key exists for the draw, so PolicyEngine's own run stands as its answer. Two answers agree when they differ by no more than $1. The record-level files stay out of git; this page and its CSV hold aggregates only.

## Agreement by line

| Line | Households | All agree | PolicyEngine apart | Tax-Calculator apart | TAXSIM apart | All differ |
|---|---:|---:|---:|---:|---:|---:|
| Income tax before refundable credits | 1000 | 516 (51.6%) | 47 (4.7%) | 0 (0.0%) | 328 (32.8%) | 109 (10.9%) |
| Refundable credits | 1000 | 923 (92.3%) | 11 (1.1%) | 0 (0.0%) | 64 (6.4%) | 2 (0.2%) |
| Self-employment tax | 1000 | 989 (98.9%) | 0 (0.0%) | 0 (0.0%) | 11 (1.1%) | 0 (0.0%) |
| Employee payroll tax (federal) | 1000 | 1000 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

## Differences explained in kind

For each household and line where the models do not all agree, this section asks whether the evidence explains the difference in kind. A cell counts as explained when one of these holds for the model that stands apart:

- TAXSIM or Tax-Calculator apart: that model's map carries a note of its own on the line, for a fact the map could not express or a limit of the model (several found by probes of the TAXSIM build).
- PolicyEngine apart (it carries no notes): both maps carry a note that names PolicyEngine's different treatment (its full deduction of investment interest, its looser 162(l) limit, its default divorce year for alimony, its default that rent is qualified business income, its count of care expenses); or both maps note a fact that neither Tax-Calculator nor TAXSIM can take, so those two agree without it; or PolicyEngine's own run shows it took the other side of a reading both maps share (it claims a member the maps leave out, it does not count a disabled adult as an EITC child, it files a different status, or its medical expense deduction exceeds the stated amounts' at the same AGI). The run's per-person outputs show which side it took; this unit did not read PolicyEngine's code for why.
- All three differ: any of the above on any model.

A reading both maps share, with no sign of PolicyEngine taking the other side, does not explain why one model stands apart, so it does not count; the table shows how many unexplained cells carry only such notes. Notes say what kind of difference to expect, not its size: this unit traced no dollars, so a cell can count as explained by a note whose effect is smaller than the gap.

| Line | Class | Cells | Explained | Unexplained | Of which only shared notes |
|---|---|---:|---:|---:|---:|
| Income tax before refundable credits | PolicyEngine apart | 47 | 43 | 4 | 4 |
| Income tax before refundable credits | TAXSIM apart | 328 | 327 | 1 | 1 |
| Income tax before refundable credits | All differ | 109 | 109 | 0 | 0 |
| Refundable credits | PolicyEngine apart | 11 | 11 | 0 | 0 |
| Refundable credits | TAXSIM apart | 64 | 64 | 0 | 0 |
| Refundable credits | All differ | 2 | 2 | 0 | 0 |
| Self-employment tax | TAXSIM apart | 11 | 11 | 0 | 0 |
| All lines | All classes | 572 | 567 | 5 | 5 |

Of 572 cells where the models do not all agree, 567 (99.1%) have evidence that explains the difference in kind and 5 (0.9%) have none. Read literally (any note at all on the line of the model that stands apart, shared readings included, and for PolicyEngine any note both maps carry), 572 cells carry one.

### Note families behind the explained cells

A cell can carry more than one family, so the counts add up to more than the explained cells.

| Line | Class | Model the note concerns | Note family | Cells |
|---|---|---|---|---:|
| Income tax before refundable credits | All differ | TAXSIM | no charitable deduction for non-itemizers | 62 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | reading: rent and estate income not QBI (PE's default counts rent) | 41 |
| Income tax before refundable credits | All differ | TAXSIM | partnership and farm rent in scorp | 41 |
| Income tax before refundable credits | All differ | TAXSIM | rent and estate income in intrec | 41 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | no REIT/PTP input | 40 |
| Income tax before refundable credits | All differ | Tax-Calculator | employee expenses zeroed | 40 |
| Income tax before refundable credits | All differ | Tax-Calculator | no REIT/PTP input | 40 |
| Income tax before refundable credits | All differ | TAXSIM | no REIT/PTP input | 40 |
| Income tax before refundable credits | All differ | TAXSIM | other taxable income entered as pensions | 38 |
| Income tax before refundable credits | All differ | TAXSIM | adjustments cut EITC earned income | 34 |
| Income tax before refundable credits | All differ | TAXSIM | no tax-exempt interest input | 28 |
| Income tax before refundable credits | All differ | TAXSIM | no overtime input | 26 |
| Income tax before refundable credits | All differ | TAXSIM | no vehicle loan interest input | 25 |
| Income tax before refundable credits | All differ | TAXSIM | no 2026 minimum QBI deduction | 21 |
| Income tax before refundable credits | All differ | TAXSIM | no nontaxable pension input | 17 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | 163(d) limit (PE deducts all investment interest) | 16 |
| Income tax before refundable credits | All differ | TAXSIM | no 199A wage or property limit | 16 |
| Income tax before refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine claims a disabled member with earnings of their own (is_disabled reading) | 13 |
| Income tax before refundable credits | All differ | Tax-Calculator | miscellaneous income through e01200 | 11 |
| Income tax before refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine's medical expense deduction exceeds the stated amounts' at the same AGI (medical readings) | 10 |
| Income tax before refundable credits | All differ | PolicyEngine (its own run) | PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading) | 9 |
| Income tax before refundable credits | All differ | TAXSIM | no 25%/28% rate gain input | 9 |
| Income tax before refundable credits | All differ | TAXSIM | SE health and pension deductions in nonprop (EITC, QBI) | 8 |
| Income tax before refundable credits | All differ | TAXSIM | 2026 zero rate on gains runs past Rev. Proc. 2025-32 (D6) | 8 |
| Income tax before refundable credits | All differ | TAXSIM | no saver's credit input | 7 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | care expenses of a non-qualifying person | 6 |
| Income tax before refundable credits | All differ | TAXSIM | 2026 care credit at pre-2026 rates | 5 |
| Income tax before refundable credits | All differ | TAXSIM | no blindness input | 4 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | 162(l) limit (PE limits to Schedule C income) | 3 |
| Income tax before refundable credits | All differ | Tax-Calculator | disability benefits through e01200 | 2 |
| Income tax before refundable credits | All differ | PolicyEngine (note names it) | reading: alimony (PE's default makes it pre-2019) | 2 |
| Income tax before refundable credits | All differ | Tax-Calculator | alimony no effect | 2 |
| Income tax before refundable credits | All differ | TAXSIM | alimony left out | 2 |
| Income tax before refundable credits | All differ | TAXSIM | care credit counts children under 13 only | 2 |
| Income tax before refundable credits | All differ | Tax-Calculator | one SSTB flag per unit | 1 |
| Income tax before refundable credits | All differ | TAXSIM | a loss in one self-employment box does not offset the other (P7.4, D4) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | domestic production deduction | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | domestic production deduction zeroed | 1 |
| Income tax before refundable credits | All differ | TAXSIM | domestic production deduction left out | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator and TAXSIM | no deemed earned income (21(d)(2)) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | no deemed earned income (21(d)(2)) | 1 |
| Income tax before refundable credits | All differ | TAXSIM | no deemed earned income (21(d)(2)) | 1 |
| Income tax before refundable credits | All differ | Tax-Calculator | Form 4952 election from dividends only | 1 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: rent and estate income not QBI (PE's default counts rent) | 22 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | 163(d) limit (PE deducts all investment interest) | 12 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine's medical expense deduction exceeds the stated amounts' at the same AGI (medical readings) | 11 |
| Income tax before refundable credits | PolicyEngine apart | Tax-Calculator and TAXSIM | no REIT/PTP input | 7 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a disabled member with earnings of their own (is_disabled reading) | 6 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | care expenses of a non-qualifying person | 3 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading) | 1 |
| Income tax before refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: alimony (PE's default makes it pre-2019) | 1 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no vehicle loan interest input | 135 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | adjustments cut EITC earned income | 115 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no overtime input | 111 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no charitable deduction for non-itemizers | 107 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no 2026 minimum QBI deduction | 77 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | other taxable income entered as pensions | 51 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | SE health and pension deductions in nonprop (EITC, QBI) | 37 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no saver's credit input | 37 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no nontaxable pension input | 33 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no REIT/PTP input | 31 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | partnership and farm rent in scorp | 31 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | 2026 care credit at pre-2026 rates | 26 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no tax-exempt interest input | 19 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no blindness input | 14 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | rent and estate income in intrec | 13 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | 2026 zero rate on gains runs past Rev. Proc. 2025-32 (D6) | 10 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no 199A wage or property limit | 10 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | care credit counts children under 13 only | 2 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | no 25%/28% rate gain input | 2 |
| Income tax before refundable credits | TAXSIM apart | TAXSIM | a loss in one self-employment box does not offset the other (P7.4, D4) | 1 |
| Refundable credits | All differ | PolicyEngine (note names it) | 163(d) limit (PE deducts all investment interest) | 1 |
| Refundable credits | All differ | Tax-Calculator | employee expenses zeroed | 1 |
| Refundable credits | All differ | TAXSIM | adjustments cut EITC earned income | 1 |
| Refundable credits | All differ | TAXSIM | no charitable deduction for non-itemizers | 1 |
| Refundable credits | All differ | TAXSIM | no saver's credit input | 1 |
| Refundable credits | All differ | PolicyEngine (note names it) | reading: rent and estate income not QBI (PE's default counts rent) | 1 |
| Refundable credits | All differ | TAXSIM | no vehicle loan interest input | 1 |
| Refundable credits | All differ | TAXSIM | rent and estate income in intrec | 1 |
| Refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine does not count a disabled adult as an EITC child (is_disabled reading) | 9 |
| Refundable credits | PolicyEngine apart | PolicyEngine (note names it) | care expenses of a non-qualifying person | 5 |
| Refundable credits | PolicyEngine apart | PolicyEngine (note names it) | reading: rent and estate income not QBI (PE's default counts rent) | 1 |
| Refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a disabled member with earnings of their own (is_disabled reading) | 1 |
| Refundable credits | PolicyEngine apart | PolicyEngine (its own run) | PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading) | 1 |
| Refundable credits | TAXSIM apart | TAXSIM | adjustments cut EITC earned income | 28 |
| Refundable credits | TAXSIM apart | TAXSIM | no saver's credit input | 25 |
| Refundable credits | TAXSIM apart | TAXSIM | no vehicle loan interest input | 24 |
| Refundable credits | TAXSIM apart | TAXSIM | no 2026 minimum QBI deduction | 18 |
| Refundable credits | TAXSIM apart | TAXSIM | no overtime input | 18 |
| Refundable credits | TAXSIM apart | TAXSIM | 2026 care credit at pre-2026 rates | 15 |
| Refundable credits | TAXSIM apart | TAXSIM | SE health and pension deductions in nonprop (EITC, QBI) | 9 |
| Refundable credits | TAXSIM apart | TAXSIM | no charitable deduction for non-itemizers | 8 |
| Refundable credits | TAXSIM apart | TAXSIM | other taxable income entered as pensions | 4 |
| Refundable credits | TAXSIM apart | TAXSIM | partnership and farm rent in scorp | 3 |
| Refundable credits | TAXSIM apart | TAXSIM | no nontaxable pension input | 2 |
| Refundable credits | TAXSIM apart | TAXSIM | no blindness input | 1 |
| Refundable credits | TAXSIM apart | TAXSIM | rent and estate income in intrec | 1 |
| Self-employment tax | TAXSIM apart | TAXSIM | no $400 floor on self-employment tax (P10.3) | 9 |
| Self-employment tax | TAXSIM apart | TAXSIM | a loss in one self-employment box does not offset the other (P7.4, D4) | 2 |

## The largest unexplained differences

Only 5 cells have no explaining evidence, so this lists all of them, largest first (at most ten). Size: for one model apart, its distance from the mean of the two that agree; where all differ, the range of the three answers. Stated inputs: every input the household states that can reach a federal line (the inputs named as having no effect are left out). The last column says what the three runs' saved outputs show, without tracing dollars.

| Rank | Line | Class | Size ($) | Stated inputs | What the runs show |
|---:|---|---|---:|---|---|
| 1 | Income tax before refundable credits | PolicyEngine apart | 143.45 | auto_loan_interest, health_insurance_premiums_without_medicare_part_b, miscellaneous_income, other_health_insurance_premiums, other_medical_expenses, over_the_counter_health_expenses, qualified_passenger_vehicle_loan_interest, taxable_ira_distributions, taxable_private_pension_income | PolicyEngine's AGI exceeds both maps' by 25,150.50, the size of the stated negative miscellaneous income, which both maps subtract (no reading covers a negative amount there) |
| 2 | Income tax before refundable credits | PolicyEngine apart | 120.00 | employment_income, other_medical_expenses, over_the_counter_health_expenses, student_loan_interest | PolicyEngine's AGI exceeds both maps' by 1,000.00; the saved run does not show the source |
| 3 | Income tax before refundable credits | PolicyEngine apart | 15.39 | employment_income, health_insurance_premiums_without_medicare_part_b, is_self_employed, other_health_insurance_premiums, other_medical_expenses, over_the_counter_health_expenses, roth_401k_contributions_desired, roth_ira_contributions_desired, self_employment_income, tax_exempt_private_pension_income, taxable_interest_income, taxable_private_pension_income, traditional_401k_contributions_desired, traditional_ira_contributions_desired | AGI and taxable income agree; PolicyEngine's run allows a saver's credit of 15.40, where the maps' statute figure is 0 (the household states taxable pension income) |
| 4 | Income tax before refundable credits | TAXSIM apart | 2.97 | auto_loan_interest, employment_income, health_insurance_premiums_without_medicare_part_b, long_term_capital_gains, non_qualified_dividend_income, other_health_insurance_premiums, other_medical_expenses, over_the_counter_health_expenses, qualified_dividend_income, qualified_passenger_vehicle_loan_interest, roth_401k_contributions_desired, roth_ira_contributions_desired, short_term_capital_gains, taxable_interest_income, traditional_401k_contributions_desired, traditional_ira_contributions_desired | AGI and taxable income agree across the three; not traced further |
| 5 | Income tax before refundable credits | PolicyEngine apart | 1.63 | first_home_mortgage_balance, home_mortgage_interest, investment_interest_expense, is_disabled, miscellaneous_income, other_medical_expenses, over_the_counter_health_expenses, real_estate_taxes, salt_refund_income, tax_exempt_private_pension_income, taxable_interest_income, taxable_private_pension_income | PolicyEngine's AGI exceeds both maps' by 13.56, the size of the stated negative miscellaneous income, which both maps subtract (no reading covers a negative amount there) |

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

