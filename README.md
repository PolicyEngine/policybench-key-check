# PolicyBench key check

**Status: interim.** An independent read of the input maps, the cause entries and this page has
not finished. Until it does, every count below can move and every status stays interim.

PolicyBench scores AI models against an answer key that PolicyEngine-US alone computes. This repo
checks the key's four federal tax lines: it runs the board's 100 published households, and a
further draw of 1,000, through two other tax calculators, traces every disagreement on the 100 to
a cause, and gives each cell of the key a status.

This check changes no PolicyBench reference, exclusion or adjudication. Where a cause entry says
the law supports a different answer from the key's, the entry states a position and stays open.

## What ran

| Model | Release | Tax years it computes | Role |
|---|---|---|---|
| PolicyEngine-US | 2.60.0 with PolicyBench's reference conventions | 2025, 2026 | Writes the key |
| PolicyEngine-US | 2.116.15, the newest PyPI release at 21:51 UTC on 2026-11-10 | 2026 | Check that the newest release gives the same key |
| Tax-Calculator | 6.9.0, the newest PyPI release | 2025, 2026 | Second model |
| NBER TAXSIM | test build `cd2026110117` (NBER's own Fortran binary) | through 2026 | Third model |
| NBER TAXSIM | production build `2025Aug23` | through 2024 only | Not used: it stops before the board's year |

TAXSIM here is NBER's binary, not PolicyEngine's TAXSIM emulator, which answers tax years 2021 and
later with PolicyEngine. `scripts/get_taxsim.sh` fetches the binaries from a pinned commit of
PolicyEngine/policyengine-taxsim and checks their SHA-256 sums; this repo does not redistribute
them.

The four lines, for tax year 2026:

| Line | PolicyBench output | PolicyEngine-US | Tax-Calculator | TAXSIM |
|---|---|---|---|---|
| Tax before refundable credits | `federal_income_tax_before_refundable_credits` | `income_tax_before_refundable_credits` | `c09200 - setax - ptax_amc` | `fiitax + v25 + actc` |
| Refundable credits | `federal_refundable_credits` | `income_tax_refundable_credits` | `refund` | `v25 + actc` |
| Self-employment tax | `self_employment_tax` | `self_employment_tax`, every member | `setax` | from two runs: `(tfica - addmed)` with and without self-employment income |
| Federal employee payroll tax | the federal part of `payroll_tax` | `employee_social_security_tax + employee_medicare_tax + additional_medicare_tax` | `ptax_was / 2 + ptax_amc` | `tfica` less self-employment tax |

The board's `payroll_tax` also holds mandatory state payroll taxes. Neither other model has them,
so this check compares the federal part and reports the state part separately
(`state_employee_payroll_tax` in the answers table).

## The board's 100 households

Two answers agree when they differ by no more than $1, the board's own exact-match rule.
`scripts/make_readme_tables.py` fills every table on this page from the committed result files.

Tax year 2026, against the committed key:

<!-- generated:board-2026-key -->
| Line | All three agree | PolicyEngine apart | Tax-Calculator apart | TAXSIM apart | All differ |
|---|---:|---:|---:|---:|---:|
| Tax before refundable credits | 70 | 10 | 2 | 15 | 3 |
| Refundable credits | 95 | 0 | 0 | 5 | 0 |
| Self-employment tax | 100 | 0 | 0 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 | 0 | 0 |
<!-- /generated -->

The committed key holds, for an output the board excludes from scoring, the value the board
decided on, which can differ from what the engine gives today. Against a rerun of the key's engine
(policyengine-us 2.60.0, the board's conventions):

<!-- generated:board-2026-rerun -->
| Line | All three agree | PolicyEngine apart | Tax-Calculator apart | TAXSIM apart | All differ |
|---|---:|---:|---:|---:|---:|
| Tax before refundable credits | 74 | 6 | 2 | 16 | 2 |
| Refundable credits | 95 | 0 | 0 | 5 | 0 |
| Self-employment tax | 100 | 0 | 0 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 | 0 | 0 |
<!-- /generated -->

The rerun equals the committed key on every scored output of the four lines.

The same households under 2025 law (PolicyEngine-US 2.60.0, Tax-Calculator 6.9.0 and TAXSIM, each
at tax year 2025). This table tests the three engines on these households under 2025 law, where
NBER's build is more complete; it does not test the 2026 key:

<!-- generated:board-2025 -->
| Line | All three agree | PolicyEngine apart | Tax-Calculator apart | TAXSIM apart | All differ |
|---|---:|---:|---:|---:|---:|
| Tax before refundable credits | 81 | 7 | 2 | 9 | 1 |
| Refundable credits | 95 | 0 | 0 | 5 | 0 |
| Self-employment tax | 100 | 0 | 0 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 | 0 | 0 |
<!-- /generated -->

policyengine-us 2.116.15 gives the same four lines as 2.60.0 for 98 of the 100 households under
the board's conventions. The two that move (scenario_120 and scenario_121, tax before refundable
credits) are outputs the board already excludes.

Per-household classes: `results/agreement/`. Every model's answer: `results/answers.csv`.
What this check gave each model and what each answered, per household: `results/dossiers/`.

## A status for each cell of the key

Agreement is not the same as support. `scripts/make_cell_status.py` gives each of the key's 500
cells for tax year 2026 (100 households by five quantities: the four lines, with payroll tax split
into its federal and state parts) one of three statuses, by rules it applies mechanically
(`docs/coverage.md` states them):

- **Reproduced by a run of another lineage.** A Tax-Calculator or TAXSIM run gives the key's
  answer within $1 and no cause entry disputes it. Two runs share a lineage where they share an
  engine, a convention file, an input map or an input that another run computed. The
  Tax-Calculator and TAXSIM runs share one input map, so their agreement counts once.
- **Contested.** A cause entry says the law or the board's rule for unstated facts supports a
  different answer, or that the answer turns on a fact the household does not state.
- **Resting on PolicyEngine alone.** No other model produces the quantity, or none agrees and no
  entry disputes the key's answer or leaves it open.

<!-- generated:cell-status -->
| Status | Cells | Of which the board scores | Of which trivial zeros |
|---|---:|---:|---:|
| Reproduced by a run of another lineage | 376 | 372 | 123 |
| Contested | 21 | 8 | 0 |
| Resting on PolicyEngine alone | 103 | 96 | 36 |
| Total | 500 | 476 | 159 |
<!-- /generated -->

A trivial zero is a cell where the key and every agreeing run answer zero, such as the
self-employment tax of a household with no self-employment income: true, and a weak test.

<!-- generated:cell-status-by-quantity -->
| Quantity | Reproduced by a run of another lineage | Contested | Resting on PolicyEngine alone |
|---|---:|---:|---:|
| Tax before refundable credits | 76 | 21 | 3 |
| Refundable credits | 100 | 0 | 0 |
| Self-employment tax | 100 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 |
| State employee payroll tax | 0 | 0 | 100 |
<!-- /generated -->

The scored cells where a cause entry disputes the key's answer or leaves it open
(`results/cause_positions.csv` holds each entry's position on each household):

<!-- generated:scored-positions -->
| Household | Line | Key's answer | Other answer | Position | Cause entries |
|---|---|---:|---:|---|---|
| scenario_023 | Tax before refundable credits | 643.43 | 1,443.43 | The answer turns on a fact the household does not state | `taxsim-no-early-distribution-tax-input`, `pe-early-distribution-tax-not-computed` |
| scenario_030 | Tax before refundable credits | 0.00 | 190.00 | The entry says the board's rule for unstated facts supports another answer | `pe-scholarship-not-income` |
| scenario_042 | Tax before refundable credits | 2,361.96 | 2,377.71 | The answer turns on a fact the household does not state | `shared-bdc-income-not-added` |
| scenario_064 | Tax before refundable credits | 4,441.46 | 6,441.46 | The entry says the law supports another answer | `taxsim-no-early-distribution-tax-input`, `pe-early-distribution-tax-not-computed` |
| scenario_068 | Tax before refundable credits | 1,910.02 | 14,728.38 | The entry says the board's rule for unstated facts supports another answer | `pe-scholarship-not-income` |
| scenario_074 | Tax before refundable credits | 0.00 | 38.40 | The answer turns on a fact the household does not state | `taxsim-no-early-distribution-tax-input`, `pe-early-distribution-tax-not-computed` |
| scenario_076 | Tax before refundable credits | 19,611.80 | 19,803.80 | The answer turns on a fact the household does not state | `shared-rental-with-basis-qualified-business-income` |
| scenario_082 | Tax before refundable credits | 9,579.77 | 9,564.92 | The entry says the board's rule for unstated facts supports another answer | `shared-state-tax-refund-counted-in-full` |
<!-- /generated -->

"Other answer" gives what would follow under the entry's position or under the other reading. This
repo proposes nothing more than that: it changes no reference.

A reproduced cell can still rest on a reading. These scored cells stand reproduced, and an entry
that supports the key's answer names the answer the other reading would give:

<!-- generated:rests-on-readings -->
| Household | Line | Key's answer | Answer under the other reading | Cause entry |
|---|---|---:|---:|---|
| scenario_007 | Tax before refundable credits | 3,707.70 | 7,235.69 | `shared-private-pension-no-early-distribution-tax` |
| scenario_009 | Tax before refundable credits | 8,348.00 | 10,388.00 | `shared-private-pension-no-early-distribution-tax` |
| scenario_025 | Tax before refundable credits | 7,031.04 | 10,232.97 | `shared-private-pension-no-early-distribution-tax` |
| scenario_036 | Tax before refundable credits | 4,926.40 | 10,848.40 | `shared-private-pension-no-early-distribution-tax` |
| scenario_073 | Tax before refundable credits | 0.00 | 74.11 | `shared-private-pension-no-early-distribution-tax` |
<!-- /generated -->

`results/cell_status.csv` holds every cell with the runs that reproduce it, what each reproduction
shares with the key's run, the cause entries that bear on it, and what the second input maps give
(below). `docs/coverage.md` sets out, line by line, what Tax-Calculator and TAXSIM can and cannot
reproduce for 2026 and for 2025.

## Why the answers differ

`results/causes.csv` holds one entry per cause: what happens, in which release or build, the law,
which answer the law supports and why, and any existing report. `results/cause_cells.csv` gives
the dollars each cause adds to each answer, by household, line and run. `tests/test_causes.py`
checks that, for every household, line and pair of answers, the difference between the answers
equals the difference between the sums of their cause amounts within $1.
`results/cause_positions.csv` gives each entry's position on each household's answer. `docs/causes.md`
gives the account in prose, and ends with the scored answers an entry would change.

<!-- generated:causes -->
| Kind of cause | Entries | Household-line-table cells they move |
|---|---:|---:|
| `shared-reading` | 13 | 5 |
| `model-no-provision` | 8 | 37 |
| `model-law-departure` | 6 | 10 |
| `pe-default-unstated-fact` | 4 | 10 |
| `key-decided-value` | 2 | 4 |
| `map-limit` | 1 | 4 |
| Total | 34 | 59 |
<!-- /generated -->

Every entry stays open. Claude Opus 5.5 agents wrote them; the position in each awaits a human
reviewer.

## How far the input maps carry

Tax-Calculator and TAXSIM do not take a household's facts as the board states them. An input map
(`keycheck/`) derives one federal return from the stated facts (who files, in what status, who is
a dependent, each line's amount) and turns it into each model's inputs. A map can hide errors and
silent choices, and two models fed by one map share them. Four things bound that risk:

1. **One rule for unstated facts**, the board's own: a stated fact means what it says, an
   unlisted number is 0, and any other unlisted fact or status is false. `keycheck/unit.py` names
   every reading it applies (`READINGS`), and the answers table lists the readings each answer
   rests on.
2. **Three reviews of the first maps** by agents on another model, one of which rebuilt the
   Tax-Calculator map independently (`evidence/traces/verify-*.md`), and a builder that applied
   their findings (`evidence/traces/fix-maps.md`).
3. **A second pair of maps written blind.** Two agents each wrote a map for all 100 households
   without seeing `keycheck/`, PolicyEngine's code or any answers (`second_map/`). Two more
   agents diffed each against the first map as it then stood and ruled on every difference
   (`docs/second-map-taxcalc.md`, `docs/second-map-taxsim.md`, `results/second_map/`):

<!-- generated:second-map -->
| Engine | Line | Both maps give the key | Only the first | Only the second | Neither |
|---|---|---:|---:|---:|---:|
| Tax-Calculator | Tax before refundable credits | 76 | 13 | 0 | 11 |
| Tax-Calculator | Refundable credits | 97 | 3 | 0 | 0 |
| Tax-Calculator | Self-employment tax | 100 | 0 | 0 | 0 |
| Tax-Calculator | Federal employee payroll tax | 100 | 0 | 0 | 0 |
| TAXSIM | Tax before refundable credits | 66 | 7 | 0 | 27 |
| TAXSIM | Refundable credits | 86 | 10 | 0 | 4 |
| TAXSIM | Self-employment tax | 100 | 0 | 0 | 0 |
| TAXSIM | Federal employee payroll tax | 100 | 0 | 0 | 0 |
<!-- /generated -->

   The second maps never give the key where the first do not. Most of the gap is second-map
   error: the comparers ruled that it took a deduction for vehicle loan interest on facts the
   board does not state, entered TAXSIM dependents on the input path where the test build's 2026
   EITC is wrong, and put non-taxable amounts in a TAXSIM field that raises taxable Social
   Security. The comparison also found places where the first maps left the rule above in ways
   that matched PolicyEngine: a scholarship and survivor benefits left out of income, a passive
   loss deducted, and no additional tax on an early retirement distribution. A further builder
   has applied the rule uniformly since (map version 2026-11-11.1,
   `evidence/traces/builder-2.md`), and the tables above follow that version.
4. **The record of each run.** `results/runs.csv` says who wrote each run's input map and what
   the run shares with other runs; `results/bindings.csv` says, for each household and run, which
   inputs another run computed, which amounts this repo computed from statute, and which stated
   facts the model could not take:

<!-- generated:shared-inputs -->
| Run | Households where the model itemizes on the shared amount | Households with an amount this repo computed from statute | Households with a fact the model could not take or a named reading |
|---|---:|---:|---:|
| `taxcalc-6.9.0-2025` | 10 | 29 | 87 |
| `taxcalc-6.9.0-2026` | 8 | 29 | 87 |
| `taxsim-cd2026110117-2025` | 11 | 87 | 87 |
| `taxsim-cd2026110117-2026` | 9 | 87 | 90 |
<!-- /generated -->

What stays shared between the first and second maps: the board's stated facts, the state and
local tax amount, the engines, and whatever their authors (all Claude models) tend to get wrong
alike.

## The larger draw

`scripts/draw_households.py` draws 1,000 more households with the board's own sampler from the
dataset its reference sidecar names. No committed key exists for them, so PolicyEngine's own run
(2.60.0, the board's conventions) stands as its answer. Tax year 2026:

<!-- generated:draw-1000 -->
| Line | All three agree | PolicyEngine apart | Tax-Calculator apart | TAXSIM apart | All differ |
|---|---:|---:|---:|---:|---:|
| Tax before refundable credits | 501 | 53 | 5 | 273 | 168 |
| Refundable credits | 919 | 15 | 0 | 58 | 8 |
| Self-employment tax | 987 | 3 | 0 | 10 | 0 |
| Federal employee payroll tax | 1000 | 0 | 0 | 0 | 0 |
<!-- /generated -->

The draw states 23 inputs the board's 100 never do, and its mix of households differs from the
board's (`results/draw1000_summary.md` sets the two side by side), so its rates do not transfer
to the board. The summary attributes each cell that does not agree to a kind of cause where a
note supports one, and lists what no note explains; it traces no dollars. The draw's
record-level files stay out of git; `scripts/draw_summary/summarize.py` rebuilds the summary from
local runs.

## What these counts do and do not show

1. **State and local tax paid is not a stated fact.** A household states its state, not the
   state income tax it paid. The key fills the federal deduction with PolicyEngine's estimate.
   Tax-Calculator has no state model and TAXSIM's would be a second estimate, so both took the
   key's amount (`results/shared/`). Where a model itemizes, agreement bears on the federal
   computation given that amount, not on the amount.
2. **Some amounts come from this repo, not from the model.** Tax-Calculator and TAXSIM take
   several deductions and credits as amounts the caller has already limited. `keycheck/statute.py`
   applies the statute; the answers table flags each such cell (`map_computed`). Agreement there
   tests PolicyEngine against this repo's reading of the statute as much as against the model.
3. **NBER's 2026 year is unfinished.** Probes of build `cd2026110117` (`probes/taxsim/`,
   `evidence/taxsim.md`, `docs/causes.md`) show, for tax year 2026: a wrong EITC for one to three
   children when dependents go in by age (right when they go in as counts, which this check
   uses); the child care credit at pre-2026 rates; the 2025 SALT cap; no deduction for overtime;
   no charitable deduction for non-itemizers; no 2/37 limit on itemized deductions; capital
   gains breakpoints above the published ones. The build has no input for blindness, tips,
   overtime, tax-exempt interest or the saver's credit.
4. **Models can share an omission.** Where every model leaves something out, no difference
   shows it. The cause entries of kind `shared-reading` list the ones this check found.
5. **A reproduced cell is not a correct cell.** It says a second model, fed through this repo's
   map, gives the same number.

## What each model can take

`maps/board_facts.csv` and `maps/draw_facts.csv` list every input a household states, whether it
can reach a federal line in the key, and the field each model takes it in:

<!-- generated:facts -->
| Households | Stated inputs | Can reach a federal line | Of those: axiom-oracles concept id | Tax-Calculator field | TAXSIM field | None of the three |
|---|---:|---:|---:|---:|---:|---:|
| The board's 100 households | 97 | 56 | 23 | 55 | 42 | 1 |
| The draw's 1,000 households | 110 | 69 | 25 | 68 | 50 | 1 |
<!-- /generated -->

## The answers table

`results/answers.csv` has one row per household, quantity, model and run.

| Column | Meaning |
|---|---|
| `case_set` | The set of households: `board-100` is the board's published 100 |
| `case_id` | The household's id in that set (`scenario_000` is the board's first) |
| `period` | The tax year the run computed |
| `quantity` | What the row measures, in dollars for the year: the four lines above, plus `state_employee_payroll_tax` and the board's `payroll_tax` (federal plus state) |
| `model` | The model that answered; `results/models.csv` gives its kind, maintainer and lineage |
| `run` | A model at a release under stated conditions; `results/runs.csv` gives the release, the tax year, the conventions, the input map, its author, the inputs another run computed and what the run shares with other runs. The committed key is run `pb-reference-2.60.0`; reruns of PolicyEngine at other releases or years are other runs |
| `value` | The answer, to the cent; empty when there is none |
| `status` | `ok`; `not_published` (the committed key does not hold this quantity); `not_covered` (the model has no such quantity); `error` (the model rejected the household) |
| `unexpressed_facts` | Stated facts the model could not take, or took with a side effect, that bear on this quantity; also the readings of unstated facts the answer rests on |
| `map_computed` | Amounts this repo computed from the statute because the model takes them as given |

Beside it: `results/bindings.csv` (one row per household and run), `results/causes.csv`,
`results/cause_cells.csv` and `results/cause_positions.csv` (the causes), `results/cell_status.csv`
(one row per cell of the key).

## Method

1. `scripts/run_pe.py` rebuilds the key the way the board does: it imports the board's own
   household builder and convention modules from a PolicyBench checkout (commit `c7ede86c`) and
   writes each line with about 100 of its parts.
2. `keycheck/unit.py` derives one federal return from each household's stated facts, reading
   nothing PolicyEngine computed. `keycheck/map_taxcalc.py` and `keycheck/map_taxsim.py` turn the
   return into each model's inputs. `evidence/` holds what each input must hold, from the models'
   code, documentation and probes.
3. Tax-Calculator runs one year with no extrapolation, with stepped phase-outs
   (`exact_calculations=True`) and with its claiming lottery switched off: by default
   Tax-Calculator zeroes some filers' EITC and refundable child credit at random to model
   non-claiming (`eitc_claim_prob_*`, `actc_claim_prob_*`).
4. `scripts/build_answers.py` assembles the answers table; `scripts/agreement.py` classifies each
   household and line; `scripts/make_bindings.py`, `scripts/causes/` and
   `scripts/make_cell_status.py` write the bindings, the causes and the cell statuses.

## Reproduce

Python 3.12 and [uv](https://docs.astral.sh/uv/). `scripts/reproduce.sh` holds every command
below with its full arguments, one step per argument (`setup`, `pe`, `shared`, `engines`, `tables`,
`compare`, `tests`); the first four need the three environments, and the rest read files only.

1. Build the environments (policyengine-us 2.60.0 and 2.116.15 on Python 3.12, taxcalc 6.9.0 on
   Python 3.13), check out PolicyBench at `c7ede86c`, and fetch the TAXSIM binary
   (`scripts/get_taxsim.sh`).
2. Run PolicyEngine (`scripts/run_pe.py`): the key's engine at 2026 and 2025, and 2.116.15 with
   and without the board's conventions.
3. Write the state and local tax files from the PolicyEngine runs (`scripts/make_shared_salt.py`),
   then run Tax-Calculator (`scripts/run_taxcalc.py`) and TAXSIM (`scripts/run_taxsim.py`) at 2026
   and 2025, each with the file of that year.
4. Build the tables: `scripts/build_answers.py`, `scripts/agreement.py` (three tables),
   `scripts/make_bindings.py`, `scripts/make_dossiers.py`, `scripts/causes/build_causes.py` and
   `build_docs.py`, `scripts/make_cell_status.py`, `scripts/make_readme_tables.py`.
5. Run the tests: `uv run --no-project --python 3.12 --with pytest --with hypothesis pytest tests -q`.

The TAXSIM binary this check used runs on macOS; NBER publishes builds for other systems. The
draw takes the same steps on `data/draw/` (`scripts/draw_households.py` rebuilds it).

## Who did what

The session that ran the models and wrote the first input maps ran on Claude Fable 5.2, a model
PolicyBench is about to score. So that no finding rests on it alone, Claude Opus 5.5 agents wrote
the evidence the maps rest on, reviewed and revised the maps, wrote the second maps and their
comparison, traced each disagreement, and wrote the cause entries and the status rules; the
session did the mechanical work of running, tabulating and committing, and never read any AI
model's answers to these households. `evidence/README.md` lists each agent's file.
