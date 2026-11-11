# Coverage of the 2026 answer key

**Every status here is interim.** The statuses rest on this repo's input maps (`keycheck/`);
they stay interim until those maps have had an independent read, and every row of
`results/cell_status.csv` carries `interim` true until then. No status says the key is right:
each cell carries one of three statuses, `reproduced` (reproduced by a run of another lineage),
`contested`, or `resting_on_one_model` (resting on PolicyEngine alone).

This file says what Tax-Calculator and NBER TAXSIM can and cannot reproduce of PolicyBench's
2026 answer key, and gives the count of the key's cells by status.
`scripts/make_cell_status.py` writes it and `results/cell_status.csv`; rerun
`python3 scripts/make_cell_status.py` after any regeneration of the files it reads.

## Status rules

`scripts/make_cell_status.py` assigns every status by the rules below; nobody edits its output by
hand. It reads `results/answers.csv`, `results/runs.csv`, `results/models.csv`,
`results/bindings.csv`, `results/causes.csv`, `results/cause_cells.csv`, the agreement tables in
`results/agreement/`, the dossiers' stated facts and board exclusion records
(`results/dossiers/`), `maps/board_facts.csv`, the `READINGS` of `keycheck/unit.py` and, where
they exist, the second map's answers (`second_map/<engine>/answers_2026.csv`).

**Cells.** One row per board household and quantity for tax year 2026 (500 rows): the
three federal lines (`federal_income_tax_before_refundable_credits`, `federal_refundable_credits`, `self_employment_tax`), the federal part of payroll tax (`federal_employee_payroll_tax`) and the
state part (`state_employee_payroll_tax`). The key's value for the three federal lines comes from the committed key
(`pb-reference-2.60.0`). The committed key publishes only `payroll_tax`, federal and state together, so the
script splits it by the parts of the key engine's rerun (`pe-2.60.0-board-2026`) and checks that the parts sum
to the committed amount within $1 (`key_source`). The board scores or excludes `payroll_tax` as a
whole, so both payroll parts take its `board_scores_it`.

**Lineage.** Two runs count as one lineage where they share an engine (`results/models.csv`
`lineage`), a convention file or an input-map file (`results/runs.csv`). The Tax-Calculator and
TAXSIM runs share `keycheck/unit.py`, so they form one lineage: a cell both reproduce counts once,
and `reproducing_lineages` names that one lineage. The PolicyEngine reruns belong to the key's
lineage and reproduce nothing. An input that one run computed and another takes (the state and
local tax amount) qualifies the cell instead (`shares_with_key_run`, below).

**Agreement.** A run of another lineage gives the key's answer when it answers within $1, the
board's exact-match rule (`agreeing_runs`; `apart_runs` lists the runs that answer and differ).

**Rules, in order.**

1. `resting_on_one_model` with detail `no_other_model_has_quantity`: no run of another lineage
   answers for the quantity (state payroll taxes).
2. `contested`, when any of these holds, whether or not a run agrees. `contested_reasons` lists
   every reason that holds, `status_detail` the first in this order, and `contesting_cause_ids`
   the entries behind them.
   - `key_not_supported_by_law`: an entry in `results/cause_cells.csv` moves the key's own answer
     by more than $1, and its kind is `model-law-departure`, `model-no-provision` or
     `key-decided-value`; or a `shared-reading` entry lists the household and the board's own
     exclusion record for the output holds an alternative more than $1 from the key for a reason
     other than `reference_depends_on_unlisted_input` (such as `reference_engine_defect`). An entry
     of kind `unexplained` takes no position, so it contests nothing; a kind the script does not
     know stops the script.
   - `turns_on_unstated_fact`: an entry of kind `pe-default-unstated-fact`, `shared-reading` or
     `map-limit` moves the key's answer by more than $1; or a `shared-reading` entry lists the
     household (`households_shared`) and its position (`who_is_right`) names the household's
     answer in a sentence that says what the answer would be (the pattern `NNN's answer` or
     `NNN's scored answer` in a sentence with "would"); or a `shared-reading` entry lists the
     household and the board's own exclusion record for the output, of reason
     `reference_depends_on_unlisted_input`, holds an alternative more than $1 from the key; or no
     run of another lineage agrees and an entry that moves a run that stands apart is a
     `shared-reading`, or a `map-limit` whose `release_or_build` names a `READINGS` key.
   - `key_decided_value_unscored`: no run of another lineage agrees, an entry has rows on the cell
     in `results/cause_cells.csv`, the board does not score the output, and the committed key
     differs from the key engine's rerun by more than $1: the key holds a value the board decided
     on an earlier release.
   - `three_answers_differ`: no two of the key, the Tax-Calculator answer and the TAXSIM answer
     agree, and an entry has rows on the cell.
3. `reproduced`: a run of another lineage gives the key's answer within $1 and rule 2 does not
   apply. `status_detail` reads `key_salt_amount_itemized` when every reproducing run itemizes on
   PolicyEngine's state and local tax amount (`results/bindings.csv`
   `input_from_other_run_bears_on_answer`, which the script checks against the answers table's
   note on that input), so a count can leave those cells out; otherwise `no_input_from_key_run`.
4. `resting_on_one_model` otherwise: no run of another lineage agrees and no entry disputes the
   key. The detail reads `no_other_run_takes_a_fact` when every entry that moves the runs that
   stand apart has kind `model-no-provision` or `map-limit`; `other_runs_depart_from_law` when
   some has kind `model-law-departure` and the rest have those kinds; `unexplained` otherwise (no
   entry covers a run that stands apart, or an entry of another kind does).

Every contested cell therefore names at least one entry, and the entry applies to the cell: a row
in `results/cause_cells.csv` for the cell, or a `shared-reading` entry whose `households_shared`
lists the household (for the 2026 table) and whose `quantities` hold the line.

**Within `reproduced`.** `reproduction_scope` reads `both_runs_one_lineage` when both runs give
the key. When one run gives it and the other stands apart, it names why the other stands apart:
that model's own gap or defect (`one_run_other_model_gap`: entries of kind `model-no-provision` or
`model-law-departure`), a limit of this repo's map for that model (`one_run_other_map_limit`),
both (`one_run_other_gap_and_map_limit`), or no entry (`one_run_other_unexplained`); `cause_ids`
names the entries. A cell both runs reproduce rests on two engines that share one input map; a
cell one run reproduces rests on one engine and that map.

**What a reproduction shares with the key's run** (`shares_with_key_run`). For each reproducing
run the script lists `key_salt_amount` (the run itemizes, so PolicyEngine's state and local tax
amount bears on the answer; income tax lines only), `map_computed_amount` (an amount
`keycheck/statute.py` computes because the model takes it as given; `shared_map_computed` names
each) and `reading` (a named reading of a fact the household does not state, from
`keycheck/unit.py` `READINGS`; `shared_readings` names each). The cell reports the reproducing run
that shares least (`shares_measured_on`), ranked first by the state and local tax amount, then by
map-computed amounts, then by readings. `nothing` means that run shares nothing with the key's run
but the household's stated facts. The flags come from the answers table's notes on each cell, so a
reading counts wherever the map applies it to a fact the household lists, whether or not it moves
the answer.

**Zeros** (`trivial`). A cell reads `trivial` when the key's value is 0 and the household states
none of the tax's base: no self-employment, farm or partnership self-employment income for
`self_employment_tax`; no wages on any member for the two payroll parts. The flag leaves the status as the rules
give it and lets a count leave the cell out. The income tax lines carry no such flag: a zero there
comes out of income, deductions and credits that the other models compute.

**Tax year 2025.** For a reproduced cell, `also_agrees_under_2025_law` says whether each
reproducing model's 2025 run also agrees with the key engine's 2025 run (`pe-2.60.0-board-2025`): `yes`,
`partly` or `no`; other cells read `not_applicable`. `agreeing_runs_2025` lists, on every cell, the
2025 runs that agree with that run. The 2025 table tests the engines on these households, not the
2026 key.

**The second map.** A second pair of input maps, written without sight of the first, leaves its
answers in `second_map/<engine>/answers_2026.csv` (`case_id`, `quantity`, `value`). Where that file
exists the script compares each answer with the key itself and fills `second_map_taxcalc` and
`second_map_taxsim`: `agrees` or `differs` (within $1); `second_map_error` where the comparison
(`results/second_map/<engine>_answers_diff.csv`) rules the second map's answer on that line an
error of the second map (a `class` that holds `second_map_errs`, alone or with a reading);
`no_answer` (no value for the cell); or `not_covered` (state payroll). Where the answers file does
not exist the column reads `pending`. A `second_map_error` answer neither reproduces nor contests
anything on its cell. `second_map_taxcalc_class` and `second_map_taxsim_class` copy the
comparison's `class`; the script reads nothing else from the comparison files, whose first-map
columns describe the first map at the commit they name. A second-map run that reproduces the key
differs in lineage from the first map's run of the same engine only in its input map: the two
share the board's stated facts, the state and local tax file and the engine. The second-map
columns stay outside the status rules; they show whether a cell's agreement survives a change of
input map.

## Counts

All cells:

| Quantity | Reproduced | Contested | Resting on PolicyEngine alone | Cells |
|---|---:|---:|---:|---:|
| `federal_income_tax_before_refundable_credits` | 80 | 20 | 0 | 100 |
| `federal_refundable_credits` | 100 | 0 | 0 | 100 |
| `self_employment_tax` | 100 | 0 | 0 | 100 |
| `federal_employee_payroll_tax` | 100 | 0 | 0 | 100 |
| `state_employee_payroll_tax` | 0 | 0 | 100 | 100 |
| All quantities | 380 | 20 | 100 | 500 |

Cells the board scores:

| Quantity | Reproduced | Contested | Resting on PolicyEngine alone | Cells |
|---|---:|---:|---:|---:|
| `federal_income_tax_before_refundable_credits` | 80 | 4 | 0 | 84 |
| `federal_refundable_credits` | 100 | 0 | 0 | 100 |
| `self_employment_tax` | 100 | 0 | 0 | 100 |
| `federal_employee_payroll_tax` | 96 | 0 | 0 | 96 |
| `state_employee_payroll_tax` | 0 | 0 | 96 | 96 |
| All quantities | 376 | 4 | 96 | 476 |

By status detail:

| Status | Detail | All cells | Scored cells |
|---|---|---:|---:|
| `reproduced` | `no_input_from_key_run` | 370 | 366 |
| `reproduced` | `key_salt_amount_itemized` | 10 | 10 |
| `contested` | `key_not_supported_by_law` | 5 | 0 |
| `contested` | `turns_on_unstated_fact` | 15 | 4 |
| `contested` | `key_decided_value_unscored` | 0 | 0 |
| `contested` | `three_answers_differ` | 0 | 0 |
| `resting_on_one_model` | `no_other_model_has_quantity` | 100 | 96 |
| `resting_on_one_model` | `no_other_run_takes_a_fact` | 0 | 0 |
| `resting_on_one_model` | `other_runs_depart_from_law` | 0 | 0 |
| `resting_on_one_model` | `unexplained` | 0 | 0 |

Contested cells by reason (a cell counts under every reason that holds):

| Reason | All cells | Scored cells |
|---|---:|---:|
| `key_not_supported_by_law` | 5 | 0 |
| `turns_on_unstated_fact` | 19 | 4 |
| `key_decided_value_unscored` | 7 | 0 |
| `three_answers_differ` | 2 | 0 |

Reproduced cells by what the reproduction shares with the key's run:

| Shares with the key's run | Cells | Scored cells |
|---|---:|---:|
| `nothing` | 231 | 227 |
| `key_salt_amount;map_computed_amount;reading` | 3 | 3 |
| `key_salt_amount;reading` | 7 | 7 |
| `map_computed_amount;reading` | 38 | 38 |
| `reading` | 101 | 101 |

Reproduced cells by how many runs give the key:

| Reproduction scope | Cells | Scored cells |
|---|---:|---:|
| `both_runs_one_lineage` | 364 | 360 |
| `one_run` | 0 | 0 |
| `one_run_other_model_gap` | 15 | 15 |
| `one_run_other_map_limit` | 1 | 1 |
| `one_run_other_gap_and_map_limit` | 0 | 0 |
| `one_run_other_unexplained` | 0 | 0 |

159 cells read `trivial` (123 reproduced, 36 resting on PolicyEngine alone). 108 reproduced cells (104 scored) are not trivial and share nothing with the key's run but the household's stated facts.

4 cells resting on PolicyEngine alone carry a board exclusion record (032 state payroll, 043 state payroll, 081 state payroll, 082 state payroll). No other model computes the quantity, so no cause entry covers them and the rules leave them resting on PolicyEngine alone; `board_record` gives the record.

The second map against the key, by status (state payroll cells left out; each engine's columns read agrees / differs / second-map error):

| Status | Cells | Tax-Calculator | NBER TAXSIM | Either agrees | Neither agrees |
|---|---:|---:|---:|---:|---:|
| `reproduced` | 380 | 369 / 2 / 9 | 351 / 25 / 4 | 375 | 5 |
| `contested` | 20 | 4 / 13 / 3 | 1 / 16 / 3 | 5 | 15 |

Reproduced cells that no second-map run gives (a `second_map_error` answer counts for neither side; where every second-map answer differs, the first map's agreement does not survive the change of map): 064 income tax (Tax-Calculator differs, NBER TAXSIM differs), 067 income tax (Tax-Calculator second_map_error, NBER TAXSIM differs), 099 income tax (Tax-Calculator second_map_error, NBER TAXSIM differs), 026 refundable credits (Tax-Calculator second_map_error, NBER TAXSIM differs), 028 refundable credits (Tax-Calculator second_map_error, NBER TAXSIM differs).

Cells the rules leave contested or resting on PolicyEngine alone where a second-map run gives the key: 033 income tax (Tax-Calculator second_map_error, NBER TAXSIM agrees), 068 income tax (Tax-Calculator agrees, NBER TAXSIM differs), 078 income tax (Tax-Calculator agrees, NBER TAXSIM differs), 082 income tax (Tax-Calculator agrees, NBER TAXSIM differs), 117 income tax (Tax-Calculator agrees, NBER TAXSIM differs).

The columns read the second map's answers files as they stand when the script runs. Its comparison documents: `docs/second-map-taxcalc.md`, `docs/second-map-taxsim.md`.

Contested cells:

| Case | Line | Scored | Key | Reasons | Entries | Runs that give the key |
|---|---|---|---:|---|---|---|
| 002 | income tax | no | 0.00 | turns_on_unstated_fact, key_decided_value_unscored | `shared-disability-benefits-taxable` | none |
| 005 | income tax | no | 106505.90 | key_not_supported_by_law, turns_on_unstated_fact, key_decided_value_unscored, three_answers_differ | `key-ira-deducted-without-219g`, `shared-net-investment-income-tax-in-line`, `shared-state-tax-refund-counted-in-full`, `taxsim-no-nonitemizer-charitable-deduction` | none |
| 020 | income tax | no | 68056.71 | key_not_supported_by_law, turns_on_unstated_fact, key_decided_value_unscored, three_answers_differ | `pe-divorce-year-default`, `key-sales-tax-table-column-shift`, `shared-net-investment-income-tax-in-line`, `taxsim-no-nonitemizer-charitable-deduction` | none |
| 022 | income tax | no | 11113.57 | turns_on_unstated_fact | `shared-state-income-tax-withholding-estimate`, `map-rental-not-qualified-business-income` | none |
| 033 | income tax | no | 3818.15 | turns_on_unstated_fact | `shared-state-tax-refund-counted-in-full` | taxcalc-6.9.0-2026, taxsim-cd2026110117-2026 |
| 042 | income tax | yes | 2361.96 | turns_on_unstated_fact | `shared-bdc-income-not-added` | taxcalc-6.9.0-2026, taxsim-cd2026110117-2026 |
| 052 | income tax | no | 104211.41 | key_not_supported_by_law, key_decided_value_unscored | `key-ira-deducted-without-219g`, `shared-net-investment-income-tax-in-line` | none |
| 062 | income tax | no | 0.00 | turns_on_unstated_fact | `shared-survivor-benefits-not-taxable` | taxcalc-6.9.0-2026, taxsim-cd2026110117-2026 |
| 068 | income tax | yes | 1910.02 | turns_on_unstated_fact | `shared-scholarship-not-income` | taxcalc-6.9.0-2026, taxsim-cd2026110117-2026 |
| 076 | income tax | yes | 19611.80 | turns_on_unstated_fact | `map-rental-not-qualified-business-income` | none |
| 078 | income tax | no | 24164.46 | turns_on_unstated_fact | `shared-state-tax-refund-counted-in-full`, `shared-state-income-tax-withholding-estimate` | taxcalc-6.9.0-2026 |
| 081 | income tax | no | 26932.27 | turns_on_unstated_fact | `shared-state-income-tax-withholding-estimate` | taxcalc-6.9.0-2026, taxsim-cd2026110117-2026 |
| 082 | income tax | yes | 9579.77 | turns_on_unstated_fact | `shared-state-tax-refund-counted-in-full` | taxcalc-6.9.0-2026 |
| 093 | income tax | no | 8628.99 | key_not_supported_by_law, turns_on_unstated_fact | `pe-other-dependent-credit-without-dependency-tests`, `shared-head-return-only` | none |
| 107 | income tax | no | 0.00 | turns_on_unstated_fact, key_decided_value_unscored | `shared-disability-benefits-taxable` | none |
| 114 | income tax | no | 10729.61 | turns_on_unstated_fact | `pe-medicare-part-b-premium-default`, `shared-state-income-tax-withholding-estimate`, `shared-over-the-counter-not-medical` | none |
| 117 | income tax | no | 24961.34 | turns_on_unstated_fact | `shared-state-tax-refund-counted-in-full` | taxcalc-6.9.0-2026 |
| 120 | income tax | no | 40021.82 | key_not_supported_by_law, turns_on_unstated_fact, key_decided_value_unscored | `pe-net-investment-income-leaves-out-farm-rent`, `key-ira-deducted-without-219g`, `shared-net-investment-income-tax-in-line`, `shared-state-income-tax-withholding-estimate`, `shared-state-paid-leave-contributions-not-in-salt`, `shared-passive-rental-loss-allowed`, `shared-mortgage-debt-after-2017`, `shared-state-tax-refund-counted-in-full` | none |
| 121 | income tax | no | 0.00 | turns_on_unstated_fact, key_decided_value_unscored | `shared-over-the-counter-not-medical`, `shared-disability-benefits-taxable` | none |
| 123 | income tax | no | 5200.24 | turns_on_unstated_fact | `shared-head-return-only` | taxcalc-6.9.0-2026 |

## Tax-Calculator (6.9.0)

### Tax year 2026

- Federal income tax before refundable credits: gives the key's answer within $1 on 89 of 100 households (83 of the 84 the board scores). Entries that move its answer, with households: `map-rental-not-qualified-business-income` (2); `shared-state-tax-refund-counted-in-full` (2); `shared-disability-benefits-taxable` (3).
- Federal refundable credits: gives the key's answer within $1 on 100 of 100 households (100 of the 100 the board scores).
- Self-employment tax: gives the key's answer within $1 on 100 of 100 households (100 of the 100 the board scores).
- Federal employee payroll tax: gives the key's answer within $1 on 100 of 100 households (96 of the 96 the board scores).
- State employee payroll tax: no answer on any household (`results/answers.csv` status `not_covered`).

What it can reproduce, and what it cannot (each claim cites `evidence/taxcalc.md` by item):

- **Tax before refundable credits** (`c09200 - setax - ptax_amc`, `scripts/run_taxcalc.py`; C4).
  It computes the 2026 rate schedules (D10, D15), the standard deduction with the aged and blind
  amounts and the 2026 charitable deduction for non-itemizers (D7), the deductions for tips,
  overtime, car-loan interest and seniors (D2-D5), itemized deductions with the $40,400 state and
  local tax cap and the medical and charitable floors (B11, B13), the 2/37 limit (D6), the
  qualified business income deduction with the 2026 $400 minimum (D9, D14), the AMT (D12), the
  net investment income tax (D13), the child and other-dependent credits (D17) and the 2026 child
  care credit rates (D16).
- It takes as given the IRA deduction, the student loan interest deduction, the educator expense
  limit, mortgage interest under the debt limit and the saver's credit (B2, B12, D22;
  `evidence/law-2026.md` Part G), so `keycheck/statute.py` computes them; agreement on such a cell
  tests this repo's reading of the statute as much as the model (`shared_map_computed`).
- It has no input for qualified REIT dividends and PTP income (D9), no disability path for the
  credit for the elderly or disabled (D21), and no input for a divorce instrument dated before 2019
  (B3). Rent outside `e26270` and `e27200` does not count as qualified business income (D9), so
  the map's reading `rental_qbi` decides two households
  (`map-rental-not-qualified-business-income`).
- It has no state model, so it takes PolicyEngine's state and local tax amount
  (`results/runs.csv`); where it itemizes, agreement tests the federal computation given that
  amount.
- **Refundable credits** (`refund`; C5). It computes the EITC by formula (D19) and the refundable
  child credit with the three-child alternative (D18). The run switches off its claiming lottery
  (A9, A12; `results/runs.csv`). The refundable American opportunity credit needs a tentative
  credit as input (D20).
- **Self-employment tax** (`setax`; C2): per person, on 92.35% of net earnings, with the $400 floor
  (B10) and the Social Security wage base shared with wages.
- **Federal employee payroll tax** (`ptax_was / 2 + ptax_amc`, `scripts/run_taxcalc.py`; C1, C7).
  A record holds the head and spouse only (B35); the map gives a member with earnings of their own
  a record of their own (`scripts/run_taxcalc.py`).
- **State employee payroll tax**: no state model; every cell rests on PolicyEngine alone.

Notes the map leaves on `taxcalc-6.9.0-2026`'s answers, other than named readings and the shared state and local tax amount (`results/answers.csv` `unexpressed_facts`):

| Note | Lines | Households |
|---|---|---:|
| the model has no state payroll taxes | state payroll | 100 |
| Tax-Calculator zeroes unreimbursed employee expenses (e20400; ID_Miscellaneous_hc is 1 in 2025 and 2026) | income tax, refundable credits | 16 |
| no Tax-Calculator input for taxable disability benefits; entered through e01200, which enters AGI only | income tax, refundable credits | 5 |
| Tax-Calculator gives alimony no effect in 2025 or 2026 (every instrument treated as post-2018) | income tax, refundable credits | 3 |
| a member has earnings of their own: their Social Security and Medicare tax counts in the household's payroll line; their income tax return is outside the board's output | federal payroll | 2 |
| a member has income of their own (employment_income), which is not income of the head's return | income tax, refundable credits | 2 |
| Tax-Calculator zeroes the domestic production activities deduction (repealed for years after 2017) | income tax, refundable credits | 1 |
| a member has income of their own (disability_benefits), which is not income of the head's return | income tax, refundable credits | 1 |
| a member meets neither dependency test of 26 U.S.C. 152 on the stated facts and is not claimed | income tax, refundable credits | 1 |
| no Tax-Calculator input for miscellaneous income; entered through e01200, which enters AGI only | income tax, refundable credits | 1 |
| no Tax-Calculator input for qualified REIT dividends and PTP income (26 U.S.C. 199A(b)(1)(B)) | income tax, refundable credits | 1 |

Amounts this repo computes for `taxcalc-6.9.0-2026` because the model takes them as given, or enters another way (`results/answers.csv` `map_computed`):

| Amount | Lines | Households |
|---|---|---:|
| IRA deduction figured under 26 U.S.C. 219(b), (c) and (g) | income tax, refundable credits | 20 |
| traditional 401(k) deferrals limited by 26 U.S.C. 402(g) and, with Roth deferrals, to wages | income tax, refundable credits | 20 |
| saver's credit figured under 26 U.S.C. 25B before the limit to tax (reading: The saver's credit testing period is the tax year only: distributions in the two prior years and in the next year before the return's due date ... | income tax, refundable credits | 4 |
| student loan interest deduction figured under 26 U.S.C. 221 | income tax, refundable credits | 4 |
| educator expenses limited by 26 U.S.C. 62(a)(2)(D) | income tax, refundable credits | 2 |
| mortgage interest limited by 26 U.S.C. 163(h)(3)(F) | income tax, refundable credits | 2 |

### Tax year 2025, where it differs

- Federal income tax before refundable credits: `taxcalc-6.9.0-2025` agrees with `pe-2.60.0-board-2025` on 94 of 100 households (the 2026 run agrees with the 2026 key on 89). Entries that move its 2025 answer, with households: `map-rental-not-qualified-business-income` (2).
- Federal refundable credits: `taxcalc-6.9.0-2025` agrees with `pe-2.60.0-board-2025` on 100 of 100 households (the 2026 run agrees with the 2026 key on 100).
- Self-employment tax: `taxcalc-6.9.0-2025` agrees with `pe-2.60.0-board-2025` on 100 of 100 households (the 2026 run agrees with the 2026 key on 100).
- Federal employee payroll tax: `taxcalc-6.9.0-2025` agrees with `pe-2.60.0-board-2025` on 100 of 100 households (the 2026 run agrees with the 2026 key on 100).

The same code gives 2025 law (`evidence/taxcalc.md` B10, B11, D6, D7, D14, D16;
`evidence/law-2026.md` Part F): the $176,100 wage base, the $40,000 state and local tax cap, no
charitable deduction for non-itemizers, no 2/37 limit, no $400 minimum qualified business income
deduction and the pre-2026 child care credit rates, as the law has them for 2025.

## NBER TAXSIM (taxsimtest cd2026110117)

### Tax year 2026

- Federal income tax before refundable credits: gives the key's answer within $1 on 73 of 100 households (70 of the 84 the board scores). Entries that move its answer, with households: `taxsim-no-overtime-deduction` (7); `taxsim-no-nonitemizer-charitable-deduction` (10); `taxsim-no-tax-exempt-interest-input` (2); `taxsim-no-blindness-input` (1); `taxsim-no-savers-credit` (2); `taxsim-2026-child-care-credit-old-rates` (1); `taxsim-2026-salt-cap-40000` (1); `map-rental-not-qualified-business-income` (2); `shared-state-tax-refund-counted-in-full` (2); `shared-disability-benefits-taxable` (3).
- Federal refundable credits: gives the key's answer within $1 on 96 of 100 households (96 of the 100 the board scores). Entries that move its answer, with households: `taxsim-no-overtime-deduction` (1); `taxsim-no-savers-credit` (1); `taxsim-2026-child-care-credit-old-rates` (1); `taxsim-refundable-child-credit-ignores-child-care-credit` (1); `taxsim-three-child-refundable-credit-alternative` (1); `map-ira-deduction-in-nonprop-cuts-eitc` (1).
- Self-employment tax: gives the key's answer within $1 on 100 of 100 households (100 of the 100 the board scores).
- Federal employee payroll tax: gives the key's answer within $1 on 100 of 100 households (96 of the 96 the board scores).
- State employee payroll tax: no answer on any household (`results/answers.csv` status `not_covered`).

What it can reproduce, and what it cannot (each claim cites `evidence/taxsim.md` by probe or item):

- **Tax before refundable credits** (`fiitax + v25 + actc`, `scripts/run_taxsim.py`; P11.2). The
  build gives the 2026 ordinary brackets (P12.1), the standard deduction with the 65-and-over
  amount (P8.3), the senior deduction (L7, P8.4) and the $2,200 child credit with its phase-out
  (L5, P5.4) as the law has them.
- It has no input for overtime, tips, car-loan interest (P1.2, B2), blindness (P1.2, P8.3),
  tax-exempt interest (P15.5) or pre-tax contributions (P1.2), and no saver's credit
  (`taxsim-no-savers-credit`). For 2026 it has no charitable deduction for non-itemizers (P9.5)
  and no 2/37 limit (P9.6); it caps state and local taxes at 2025's $40,000 (P9.1), pays the child
  care credit at the pre-2026 rates (P5.2), gives no $400 minimum qualified business income
  deduction (P13.4), lacks the 2026 AMT exemption phase-out (P11.4, P13.1) and sets capital gains
  breakpoints about 0.9% above the published ones (P12.2).
- The map enters deductible medical expenses and charitable gifts in `mortgage`, which the build
  deducts uncapped (D6, P9.3), so `keycheck/statute.py` applies the floors first
  (`shared_map_computed`). Adjustments to income enter as negative `nonprop`, which also lowers
  earned income for the EITC (P7.1; `map-ira-deduction-in-nonprop-cuts-eitc`). Like
  Tax-Calculator it takes PolicyEngine's state and local tax amount (`results/runs.csv`).
- **Refundable credits** (`v25 + actc`, `scripts/run_taxsim.py`). The 2026 EITC with children
  matches the law on the dependent-count path the map uses and misses it on the age path (P3.4,
  P4.2). The refundable child credit comes out short by the child care credit (P3.7, P5.3), and the
  three-child alternative counts the whole self-employment tax
  (`taxsim-three-child-refundable-credit-alternative`; `probes/taxsim/actc_3kids_alt.in.csv`). The
  build denies the EITC at investment income equal to the limit (P15.4) and counts `nonprop` as
  earned income (P6.10).
- **Self-employment tax**: the map splits it out of `tfica` with a second run that zeroes the
  self-employment boxes (P10; `scripts/run_taxsim.py`). The build charges self-employment tax
  below $400 of net earnings (P10.3), and a loss in one box does not offset earnings in another
  (P7.4).
- **Federal employee payroll tax** (`tfica` less self-employment tax): matches the law's formula on
  every probe (P10.1, P10.2).
- **State employee payroll tax**: no probe found a column for it (an inference in
  `evidence/taxsim.md`, board facts list); every cell rests on PolicyEngine alone.

Notes the map leaves on `taxsim-cd2026110117-2026`'s answers, other than named readings and the shared state and local tax amount (`results/answers.csv` `unexpressed_facts`):

| Note | Lines | Households |
|---|---|---:|
| the model has no state payroll taxes | state payroll | 100 |
| adjustments to income (IRA, student loan interest, educator expenses, HSA) are entered as negative `nonprop`, which this build also subtracts from EITC earned income (probe P7.1); the law's earned income (26 U.S.C. 32(c) ... | income tax, refundable credits | 19 |
| TAXSIM has no charitable deduction for non-itemizers (26 U.S.C. 170(p), from 2026) | income tax, refundable credits | 17 |
| other taxable income (miscellaneous income, taxable disability benefits, a taxable state refund) is entered as `pensions`: `nonprop` would count as EITC earned income | income tax, refundable credits | 14 |
| TAXSIM has no input for nontaxable pensions (credit for the elderly or disabled) | income tax, refundable credits | 13 |
| TAXSIM has no input for qualified overtime compensation (26 U.S.C. 225) | income tax, refundable credits | 11 |
| TAXSIM has no input for blindness (additional standard deduction, 26 U.S.C. 63(f)(2)) | income tax, refundable credits | 9 |
| this build has no 2026 minimum qualified business income deduction (26 U.S.C. 199A(i)) | income tax, refundable credits | 8 |
| TAXSIM has no input for tax-exempt interest (Social Security provisional income, EITC investment income) | income tax, refundable credits | 7 |
| this build ignores `otherprop` from 2024, so rent and estate income are entered as `intrec` | income tax, refundable credits | 6 |
| partnership, S corporation and farm rent income are entered as `scorp`, which this build counts as net investment income and EITC investment income | income tax, refundable credits | 5 |
| this build computes the 2026 child care credit at the pre-2026 rates (probe P5) | income tax, refundable credits | 5 |
| alimony is left out (treated as a post-2018 instrument) | income tax, refundable credits | 3 |
| partnership, S corporation and farm rent income are entered as `scorp`, which this build counts as net investment income and EITC investment income; a loss there also offsets other investment income in the EITC test and ... | income tax, refundable credits | 3 |
| a member has earnings of their own: their Social Security and Medicare tax counts in the household's payroll line; their income tax return is outside the board's output | federal payroll | 2 |
| a member has income of their own (employment_income), which is not income of the head's return | income tax, refundable credits | 2 |
| TAXSIM has no input for qualified REIT dividends and PTP income | income tax, refundable credits | 1 |
| a member has income of their own (disability_benefits), which is not income of the head's return | income tax, refundable credits | 1 |
| a member meets neither dependency test of 26 U.S.C. 152 on the stated facts and is not claimed | income tax, refundable credits | 1 |
| the domestic production activities deduction is left out (repealed for years after 2017) | income tax, refundable credits | 1 |

Amounts this repo computes for `taxsim-cd2026110117-2026` because the model takes them as given, or enters another way (`results/answers.csv` `map_computed`):

| Amount | Lines | Households |
|---|---|---:|
| medical expenses above 7.5% of AGI (26 U.S.C. 213(a)) entered in `mortgage`, which TAXSIM deducts as given | income tax, refundable credits | 84 |
| IRA deduction figured under 26 U.S.C. 219(b), (c) and (g), entered as negative `nonprop` | income tax, refundable credits | 20 |
| traditional 401(k) deferrals limited by 26 U.S.C. 402(g) and, with Roth deferrals, to wages; TAXSIM has no input for them, so wages are entered gross and the deferrals as negative `nonprop`, which lowers AGI and EITC ear ... | income tax, refundable credits | 20 |
| charitable gifts (above 0.5% of AGI from 2026, 26 U.S.C. 170(b)(1)(I)) entered in `mortgage`; percentage ceilings not applied | income tax, refundable credits | 17 |
| student loan interest deduction figured under 26 U.S.C. 221, entered as negative `nonprop` | income tax, refundable credits | 4 |
| educator expenses limited by 26 U.S.C. 62(a)(2)(D) | income tax, refundable credits | 2 |
| mortgage interest limited by 26 U.S.C. 163(h)(3)(F) | income tax, refundable credits | 2 |
| the EITC comes from a second TAXSIM record with `dep18` = the EITC children (at most three); the tax before refundable credits and the refundable child credit come from the first, with `dep18` = the children under 17 (th ... | income tax, refundable credits | 2 |

### Tax year 2025, where it differs

- Federal income tax before refundable credits: `taxsim-cd2026110117-2025` agrees with `pe-2.60.0-board-2025` on 84 of 100 households (the 2026 run agrees with the 2026 key on 73). Entries that move its 2025 answer, with households: `taxsim-no-overtime-deduction` (7); `taxsim-no-tax-exempt-interest-input` (2); `taxsim-no-blindness-input` (1); `taxsim-no-savers-credit` (2); `map-rental-not-qualified-business-income` (2).
- Federal refundable credits: `taxsim-cd2026110117-2025` agrees with `pe-2.60.0-board-2025` on 96 of 100 households (the 2026 run agrees with the 2026 key on 96). Entries that move its 2025 answer, with households: `taxsim-no-overtime-deduction` (1); `taxsim-no-savers-credit` (1); `taxsim-refundable-child-credit-ignores-child-care-credit` (1); `taxsim-three-child-refundable-credit-alternative` (1); `map-ira-deduction-in-nonprop-cuts-eitc` (1).
- Self-employment tax: `taxsim-cd2026110117-2025` agrees with `pe-2.60.0-board-2025` on 100 of 100 households (the 2026 run agrees with the 2026 key on 100).
- Federal employee payroll tax: `taxsim-cd2026110117-2025` agrees with `pe-2.60.0-board-2025` on 100 of 100 households (the 2026 run agrees with the 2026 key on 100).

The entries `results/causes.csv` limits to 2026 (`law_years`: `taxsim-no-nonitemizer-charitable-deduction`,
`taxsim-2026-child-care-credit-old-rates`, `taxsim-2026-salt-cap-40000`) do not apply at 2025 law.
At 2025 law the state and local tax cap matches the law (P9.1), the EITC matches the law on every
dependent path (P4.1), and for a single filer the qualified business income deduction's phase-in
for a specified service business matches the published numbers (P13.2). The missing inputs (overtime, blindness, tax-exempt interest, pre-tax contributions), the missing
saver's credit and the short refundable child credit (P5.3) stay, and the capital gains
breakpoints sit about 0.2% above the published ones (P12.2).

## Stated facts no model but PolicyEngine takes

From `maps/board_facts.csv`: stated facts with an effect on the four federal lines (federal, or
indirect through the state and local tax deduction) that neither Tax-Calculator nor TAXSIM takes:
neither has a field, the map sends the field as 0, or the field has no effect in 2025 or 2026. On
the income tax lines `results/cell_status.csv` names the federal ones a household states
(`facts_no_other_model_takes`).

| Fact | Households | Effect | Tax-Calculator | TAXSIM | Note |
|---|---:|---|---|---|---|
| `state` | 100 | indirect | none | state (sent as 0) | reaches federal tax only through the state and local tax deduction, which is shared from the key |
| `alimony_expense` | 2 | federal | e03500 (no effect in 2025-2026) | none | the key deducts it: the engine's default divorce year is 2010; the divorce date is not stated |
| `alimony_income` | 1 | federal | e00800 (no effect in 2025-2026) | none | the key taxes it, for the same reason |
| `qualified_reit_and_ptp_income` | 1 | federal | none | none | a component of the qualified business income deduction neither other model has |
| `veterans_benefits` | 8 | indirect | none | none | enters the income that picks the sales tax table amount, for itemizers |
| `workers_compensation` | 2 | indirect | none | none | enters the income that picks the sales tax table amount, for itemizers |

Facts TAXSIM does not take and Tax-Calculator does (a cell that turns on one can still reproduce through Tax-Calculator):

| Fact | Households | Effect | Tax-Calculator | TAXSIM |
|---|---:|---|---|---|
| `fsla_overtime_premium` | 11 | federal | overtime_income | none |
| `is_blind` | 9 | federal | blind_head, blind_spouse | none |
| `is_surviving_spouse` | 12 | federal | MARS 5 when a qualifying child is claimed | none |
| `is_unmarried_partner_of_household_head` | 2 | federal | keeps the head from head of household status | none |
| `roth_401k_contributions_desired` | 24 | federal | e07240 (saver's credit, computed by the map) | none |
| `roth_ira_contributions_desired` | 24 | federal | e07240 (saver's credit, computed by the map) | none |
| `sstb_unadjusted_basis_qualified_property` | 1 | federal | PT_ubia_property (when the unit's business is a specified service trade) | none |
| `tax_exempt_interest_income` | 7 | federal | e00400 | none |
| `tax_exempt_ira_distributions` | 1 | federal | e07240 (reduces the saver's credit, computed by the map) | none |
| `tax_exempt_private_pension_income` | 13 | federal | e01500 above e01700 | none |
| `unadjusted_basis_qualified_property` | 5 | federal | PT_ubia_property | none |

Facts Tax-Calculator does not take and TAXSIM does (a cell that turns on one can still reproduce through TAXSIM):

None.

Beyond the stated facts:

- **State payroll taxes** (`state_employee_payroll_tax`): neither model computes them
  (`results/answers.csv` status `not_covered`), so every such cell rests on PolicyEngine alone,
  and the board's `payroll_tax` holds them.
- **State and local income or sales tax paid** does not appear among the stated facts. Both models
  take PolicyEngine's amount (`results/runs.csv`, `results/bindings.csv`
  `inputs_from_other_runs`); where a model itemizes, its answer rests on that amount
  (`key_salt_amount` in `shares_with_key_run`).
