# PolicyBench key check

**Status: draft.** The counts below are first results. Reviewers are still tracing causes and
checking the input maps; a number here can still move.

PolicyBench scores AI models against an answer key that is PolicyEngine-US's output alone. This
repo checks the key's four federal tax lines by running the board's 100 published households
through two other tax calculators and comparing the answers household by household.

## What ran

| Model | Release | Tax years it computes | Role |
|---|---|---|---|
| PolicyEngine-US | 2.60.0 with PolicyBench's reference conventions | 2025, 2026 | Writes the key |
| PolicyEngine-US | 2.116.15, the newest PyPI release at 21:51 UTC on 2026-11-10 | 2026 | Check that the newest release gives the same key |
| Tax-Calculator | 6.9.0, the newest PyPI release | 2025, 2026 | Second implementation |
| NBER TAXSIM | test build `cd2026110117` (NBER's own Fortran binary) | through 2026 | Third implementation |
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

## First results: the board's 100 households

Two answers agree when they differ by no more than $1, the board's own exact-match rule.

Tax year 2026, against the committed key:

| Line | All three agree | PolicyEngine apart, other two agree | TAXSIM apart, other two agree | All differ |
|---|---:|---:|---:|---:|
| Tax before refundable credits | 72 | 10 | 16 | 2 |
| Refundable credits | 96 | 0 | 4 | 0 |
| Self-employment tax | 100 | 0 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 | 0 |

The committed key holds, for an output the board excludes from scoring, the value the board
decided on, which can differ from what the engine gives today. Against a rerun of the key's engine
(policyengine-us 2.60.0, the board's conventions), tax before refundable credits reads 76 all
agree, 6 PolicyEngine apart, 17 TAXSIM apart and 1 all differ; the other three lines are
unchanged. The rerun equals the committed key on every scored output of the four lines.

The same households under 2025 law (PolicyEngine-US 2.60.0, Tax-Calculator 6.9.0 and TAXSIM, each
at tax year 2025), where NBER's build is more complete:

| Line | All three agree | PolicyEngine apart | TAXSIM apart |
|---|---:|---:|---:|
| Tax before refundable credits | 83 | 7 | 10 |
| Refundable credits | 96 | 0 | 4 |
| Self-employment tax | 100 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 |

policyengine-us 2.116.15 gives the same four lines as 2.60.0 for 98 of the 100 households under
the board's conventions. The two that move (scenario_120 and scenario_121, tax before refundable
credits) are outputs the board already excludes.

Per-household classes: `results/agreement/`. Every model's answer: `results/answers.csv`.
Everything each model was given and answered, per household: `results/dossiers/`.

## What these counts do and do not show

1. **State and local tax paid is not a stated fact.** A household states its state, not the
   state income tax it paid. The key fills the federal deduction with PolicyEngine's estimate.
   Tax-Calculator has no state model and TAXSIM's would be a second estimate, so both were given
   the key's amount (`results/shared/`). For the nine households that itemize, agreement confirms
   the federal computation given that amount, not the amount.
2. **Tax-Calculator and TAXSIM share one derivation of the return.** `keycheck/unit.py` turns a
   household's stated facts into a return (who files, in what status, who is a dependent, each
   line's amount) and both maps start from it. Where the two agree against PolicyEngine, the cause
   can be a reading of a fact the board does not state. `keycheck/unit.py` names each reading.
3. **Some amounts come from this repo, not from the model.** Tax-Calculator and TAXSIM take the
   IRA deduction, the student loan interest deduction, the educator expense limit, the mortgage
   debt limit and (Tax-Calculator) the saver's credit as amounts the caller has already limited.
   `keycheck/statute.py` applies the statute; the answers table flags each such cell
   (`map_computed`).
4. **NBER's 2026 year is unfinished.** Probes of build `cd2026110117` (`probes/taxsim/`,
   `evidence/taxsim.md`) show, for tax year 2026: a wrong EITC for one to three children when
   dependents are entered by age (right when entered as counts, which this check uses); the child
   care credit at pre-2026 rates; the 2025 SALT cap and threshold; no $400 minimum qualified
   business income deduction; no charitable deduction for non-itemizers; no 2/37 limit on
   itemized deductions; capital gains breakpoints about 0.9% above the published ones. The build
   has no input for blindness, tips, overtime, tax-exempt interest, pre-tax contributions or the
   saver's credit. The answers table lists, for each household and line, the facts a model could
   not take (`unexpressed_facts`).
5. **Agreement is not correctness.** Three models can share an omission. None computes the
   additional tax on early retirement distributions (26 U.S.C. 72(t)) from an age and a
   distribution, and none applies the passive loss rules to a stated rental loss.

## Causes of each disagreement

In progress. Reviewers are reconciling each household-line where the models differ to the dollar,
with the statute, form line or instruction that decides it.

## The answers table

`results/answers.csv` has one row per household, quantity, model and run.

| Column | Meaning |
|---|---|
| `case_set` | The set of households: `board-100` is the board's published 100 |
| `case_id` | The household's id in that set (`scenario_000` is the board's first) |
| `period` | The tax year the run computed |
| `quantity` | What is measured, in dollars for the year: the four lines above, plus `state_employee_payroll_tax` and the board's `payroll_tax` (federal plus state) |
| `model` | The model that answered; `results/models.csv` gives its kind, maintainer and lineage (models that share an engine or a convention file do not confirm each other) |
| `run` | A model at a release under stated conditions; `results/runs.csv` gives the release, the tax year, the conventions imposed, the input map and the source file. The committed key is run `pb-reference-2.60.0`; reruns of PolicyEngine at other releases or years are other runs |
| `value` | The answer, to the cent; empty when there is none |
| `status` | `ok`; `not_published` (the committed key does not hold this quantity); `not_covered` (the model has no such quantity); `error` (the model rejected the household) |
| `unexpressed_facts` | Stated facts the model could not take, or took with a side effect, that bear on this quantity; also the readings of unstated facts the answer rests on |
| `map_computed` | Amounts this repo computed from the statute because the model takes them as given |

## Method

1. `scripts/run_pe.py` rebuilds the key the way the board does: it imports the board's own
   household builder and convention modules from a PolicyBench checkout (commit `c7ede86c`) and
   writes each line with about 100 of its parts.
2. `keycheck/unit.py` derives one federal return from each household's stated facts, reading
   nothing PolicyEngine computed. `keycheck/map_taxcalc.py` and `keycheck/map_taxsim.py` turn the
   return into each model's inputs. What each input must hold was established from the models'
   code, documentation and probes (`evidence/`).
3. Tax-Calculator runs one year with no extrapolation, with stepped phase-outs
   (`exact_calculations=True`) and with its claiming lottery switched off: by default
   Tax-Calculator zeroes some filers' EITC and refundable child credit at random to model
   non-claiming (`eitc_claim_prob_*`, `actc_claim_prob_*`).
4. `scripts/build_answers.py` assembles the answers table; `scripts/agreement.py` classifies each
   household and line.

## A larger draw

`scripts/draw_households.py` draws 1,000 more households with the board's own sampler from the
dataset its reference sidecar names. Those households state 23 inputs the board's 100 never do,
so the maps do not carry them yet and this README reports no agreement rate for the draw.

## Reproduce

```bash
scripts/get_taxsim.sh
```

then build the three environments (policyengine-us 2.60.0 on Python 3.12, policyengine-us
2.116.15 on Python 3.12, taxcalc 6.9.0 on Python 3.13), export PolicyBench at `c7ede86c` to
`work/policybench-c7ede86c`, and run `scripts/run_pe.py`, `scripts/run_taxcalc.py`,
`scripts/run_taxsim.py`, `scripts/build_answers.py` and `scripts/agreement.py` with the arguments
recorded in `results/runs.csv` and each result's `.meta.json`.

## Who did what

The session that wrote the maps and ran the models ran on Claude Fable 5.2, a model PolicyBench
is about to score. So that no finding rests on it alone: the evidence the maps rest on, the
tracing of each disagreement and the review of the maps come from Claude Opus 5.5 agents, and the
session never read any AI model's answers to these households.

This check changes no PolicyBench reference, exclusion or adjudication.
