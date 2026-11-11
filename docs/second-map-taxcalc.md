# A second, independent map of the board's households to Tax-Calculator

Every Tax-Calculator answer in `results/` rests on one derivation of each household's return
(`keycheck/unit.py`) and one translation of it into engine inputs (`keycheck/map_taxcalc.py`).
To measure how much of the Tax-Calculator check rests on that derivation, an agent that never saw
the first map wrote a second one. Its sources were Tax-Calculator 6.9.0's own code and
documentation, the board's 100 households as stated, a glossary of the stated facts, and the
law. `second_map/taxcalc/` holds that map as its author left it. This page compares the two maps'
engine inputs and answers at tax year 2026 and rules on every difference.

The second map is complete: it maps and runs all 100 households (103 returns: 100 main returns
and the own returns of three dependents with income, in 067, 093 and 123), and its work log ends
`STATUS: complete`.

## In brief

- **Inputs.** No household gets identical inputs from both maps, but only because the second map
  sends two head counts (`n21`, `n1820`) that Tax-Calculator reads only for a universal basic
  income, which current law sets to zero. Setting those aside, 62 households get identical inputs,
  and 64 differ only in representation.
- **Answers.** 79 households get all four answers equal within $1 from both maps. The other 21
  differ on one line each: 18 on income tax before refundable credits and 3 on refundable credits.
  Self-employment tax and payroll tax agree in all 100.
- **Rulings.** Of the 21 differing lines, the second map's input errs in 11 (one more, 093, mixes
  an error of the second map with a reading), the first map's in 3 (062, 064, 120), one comes
  from a missing engine input that the first map handles as the law does (022), and 5 come from
  readings of unstated facts that the board's rule does not settle.
- **First map.** The comparison finds seven departures in the first map (nine differences in
  eight households) and one documentation gap. Three move a line on the board: 062 (survivor
  benefits, +4,328.39), 064 (the early-distribution tax, +2,000.00) and 120 (a suspended passive
  loss, +124.69). In 062 and 064 the committed key shares the first map's
  answer, so the key's answer there is contested.

## Files and how to rerun

| Path | What it holds |
|---|---|
| `second_map/taxcalc/` | the second map as written: `map.py`, `inputs_2026.csv`, `inputs_payroll_pass_2026.csv`, `passes_2026.csv`, `returns_2026.csv`, `answers_2026.csv`, `variants_2026.csv`, `notes.csv`, `README.md`, `PROGRESS.md`, `probes/`, `sources/` |
| `second_map/taxcalc/compare.py` | the program that writes both diff files |
| `results/second_map/taxcalc_inputs_diff.csv` | one row per household, return and input that differ by more than one cent |
| `results/second_map/taxcalc_answers_diff.csv` | one row per household and line: both maps' answers, the key, the rerun, agreement and class |

The copy in `second_map/taxcalc/` changes nothing in the author's files except private paths:
`INPUT/` stands for the input folder the author read (the board's households as stated, the
glossary, the four output definitions and the shared state and local tax file), `SECOND_MAP/` for
the map's own folder, `REPO/` for a checkout of this repo and `REVIEWS/` for a private working
folder. Four law PDFs over 1 MB stay out (`sources/i1040gi.pdf`, `p525.pdf`, `p590a.pdf`,
`p936.pdf`); their text copies stay in.

Rerun the diff from the repo root with `envs/tc690/bin/python second_map/taxcalc/compare.py`.
Before it diffs anything, the program reruns both maps' inputs through Tax-Calculator and stops
unless each map's inputs reproduce that map's own answers to the cent. It also stops on any
input difference that has no ruling.

## How the two maps line up

- **Names.** Both maps send Tax-Calculator's own input names, so the diff renames nothing.
  Tax-Calculator sets every input a row leaves out to zero (`taxcalc/data.py:247-262` in the
  engine's package), so an input that one map omits counts as 0.
- **Returns.** Each map sends one main return per household. The first map also builds a return
  for each listed member with wages or self-employment earnings, for payroll and
  self-employment tax only (`member_row` in `keycheck/map_taxcalc.py`, commit 9507519);
  `compare.py` rebuilds those returns from `results/dossiers/<case>.json` and checks that they
  reproduce the first map's member columns. The second map files a full return for each
  dependent with income of their own. The diff names a member's return `dependent:<name>` in
  both maps.
- **Passes.** The first map's committed inputs are those of its final pass. The second map's
  `inputs_2026.csv` holds its final income-tax pass; its payroll pass differs only in wages, and
  only in 057, 084, 121 and 067's dependent, where it takes employer disability pay back out of
  FICA wages. In the three main returns the payroll-pass wages equal the first map's wages, and
  067's dependent owes no payroll tax in either map, so the payroll pass adds no difference.
- **Lines.** Both maps take income tax before refundable credits as `c09200 - setax - ptax_amc`,
  refundable credits as `refund` and self-employment tax as `setax`. For payroll tax the first
  map uses `ptax_was / 2 + ptax_amc` and the second `ptax_was - ptax_er_p - ptax_er_s + ptax_amc`;
  `compare.py` reproduces the first map's committed answers with the second formula, so the two
  formulas agree here. Both maps run Tax-Calculator with the credit-claiming lottery off and exact
  phase-outs, at 2026 with no growth factors.
- **Key.** The key's value comes from `results/answers.csv`, run `pb-reference-2.60.0`. The key
  does not publish the federal payroll line, so for that line the diff uses the rerun
  `pe-2.60.0-board-2026`, as `scripts/agreement.py` does, and names the run in `key_run`.

## Classes

Each difference is one cause in one household's return. `compare.py` assigns the cause from the
stated facts and the input, and each cause carries one ruling.

| Class | Meaning |
|---|---|
| `second_map_errs` | The second map's input departs from the law, or from the board's rule that an unlisted fact, boolean or status is false (`work/policybench-c7ede86c/policybench/prompts.py:24-26`). |
| `first_map_errs` | The first map's input departs from the law or from that rule. |
| `reading` | The maps differ on a fact the household does not state; the board's rule does not settle it, and both readings are defensible. |
| `engine_path` | Tax-Calculator has no input for a stated fact, and the maps handle the gap differently. |
| `representation` | The maps express the same treatment through different inputs; no line moves. |

`moves_a_line` comes from a run: the first map's return with only that cause's inputs set to the
second map's values. A cause moves a line when any of the four answers changes by more than $1.
In the answers diff, these per-cause effects plus the dependents' returns that the second map
adds account for every household's difference within $0.01.

## Measures

**Inputs.** 0 of 100 households get identical inputs from both maps. 62 do once one sets aside
the two head counts that feed only Tax-Calculator's universal basic income (`n21`, `n1820`), and
64 differ only in representation (those 62, plus 107 and 123).

**Answers.** 79 of 100 households get all four answers equal within $1 from both maps.

**Agreement with the key, line by line.**

| Line | Both maps agree with the key | Only the first | Only the second | Neither |
|---|---:|---:|---:|---:|
| Income tax before refundable credits | 76 | 13 | 0 | 11 |
| Refundable credits | 97 | 3 | 0 | 0 |
| Self-employment tax | 100 | 0 | 0 | 0 |
| Federal employee payroll tax (key: rerun) | 100 | 0 | 0 | 0 |

**Differences by class.** A difference here is one cause in one household's return; the input
rows column counts rows of `taxcalc_inputs_diff.csv`.

| Class | Differences | Move a line | Input rows |
|---|---:|---:|---:|
| `second_map_errs` | 23 | 13 | 24 |
| `first_map_errs` | 9 | 3 | 12 |
| `reading` | 11 | 6 | 27 |
| `engine_path` | 1 | 1 | 1 |
| `representation` | 104 | 0 | 115 |

The `reading` row includes two differences with no input of their own: in 093 and 123 the second
map adds a dependent's own return to the household's income tax.

## Every difference that moves a line

| Cause | Households and effect on the second map's answer | Class |
|---|---|---|
| Auto loan interest | income tax: 002 -181.65, 003 -110.00, 018 -195.04, 033 -147.00, 053 -160.87, 067 -221.36, 086 -32.98, 093 -120.00, 099 -346.50, 101 -220.00; refundable credits: 026 +45.37, 028 +117.60 | `second_map_errs` |
| A disabled member who works | income tax: 093 -500.00 | `second_map_errs` |
| Survivor benefits | income tax: 062 +4,328.39 | `first_map_errs` |
| Early-distribution tax | income tax: 064 +2,000.00 | `first_map_errs` |
| Passive rental loss | income tax: 120 +124.69 | `first_map_errs` |
| Miscellaneous income | income tax: 022 -773.19 | `engine_path` |
| Dependents' own returns | income tax: 093 +3,220.00, 123 +3,220.00 | `reading` |
| 401(k) deferrals above the limit | income tax: 005 -1,490.56 | `reading` |
| Employer disability pay under 65 | refundable credits: 084 +642.60 | `reading` |
| BDC dividends, REIT and PTP income | income tax: 042 +15.75, 081 +1.49 | `reading` |

**Auto loan interest (second map errs).** Twenty-one households state auto loan interest. The
deduction for qualified passenger vehicle loan interest (26 U.S.C. 163(h)(4)) needs a new vehicle
whose first use began with the taxpayer, final assembly in the United States and a loan taken out
after 2024, and the board states none of these facts. Its prompt makes every unlisted household
fact false, so the deduction does not apply. The first map sends 0; the second takes the
eligibility facts as met and sends the stated interest. Twelve of the 21 households owe enough
tax, or earn in the right range for refundable credits, for the deduction to move a line.

**A disabled member who works (second map errs).** 093's dependent1 is 27, carries the board's
disability flag, and earns $45,000 in wages. The age waiver of 26 U.S.C. 152(c)(3)(B) needs
permanent and total disability, which 22(e)(3) defines as inability to engage in any substantial
gainful activity (`second_map/taxcalc/sources/usc26_22.txt:58`). This page reads $45,000 of wages
in the year as substantial gainful activity (an inference; the board states no sheltered or
impairment-related work). With gross income above the 2026 limit of $5,300
(`second_map/taxcalc/sources/rp-25-32.txt:910`), the member fails the qualifying-relative test
too. The second map counts the member as a qualifying child, so its main return takes a $500
credit for other dependents; its own work log flags the contradiction and keeps the stated flag.
The first map does not claim the member.

**Survivor benefits (first map errs).** 062 states $28,800 of survivor benefits other than Social
Security (108 states $10,392 and owes nothing either way). Gross income includes a survivor
annuity (26 U.S.C. 61(a), 72), and each exclusion needs a fact the board does not state: life
insurance proceeds (101(a)) or a veterans' benefit (38 U.S.C. 5301). The second map taxes the
benefits as a pension; the first map leaves them out, following the board's own reference
reading. `docs/causes.md` (`shared-survivor-benefits-not-taxable`) takes the same position for
the key.

**Early-distribution tax (first map errs).** 064's head is 48 and receives $20,000 of taxable
401(k) distributions. Section 72(t)(1) raises "the taxpayer's tax under this chapter" by 10% of
such a distribution (`second_map/taxcalc/sources/usc26_72.txt:516-517`) unless a 72(t)(2)
exception applies. The board states no exception, its rule makes an unstated status false, and the
one exception the facts let a map compute (medical expenses above 7.5% of AGI) fails here. The
second map sends the $2,000 tax as `e09900`, which both maps' income-tax formula counts
(Tax-Calculator's `c09200` includes it, `calcfunctions.py:4514-4529`). The first map reads "no
exception or its absence is stated" (`keycheck/unit.py:78` at commit 9507519) and sends none.
policyengine-us 2.60.0 takes the same tax as an input with no formula
(`qualified_retirement_penalty`), and the board states none, so the key's 064 answer departs from
the law in the same way: that cell is contested.

**Passive rental loss (first map errs).** 120 nets $2,000 of rent against a $2,446.59 farm rent
loss. A rental is a passive activity (26 U.S.C. 469(c)(2), `usc26_469.txt:24-25`), and the $25,000
allowance of 469(i) falls by half of modified AGI above $100,000 (`usc26_469.txt:164-171`) and
reaches zero at $150,000, far below 120's modified AGI. The second map suspends the $446.59 net
loss; the first map deducts it, since its code applies no section 469 limit. `docs/causes.md`
(`shared-passive-rental-loss-allowed`) takes the same position.

**Miscellaneous income (engine path).** 022 states $3,300 of miscellaneous income (26 CFR
1.61-14), which goes on Schedule 1 line 8z. Tax-Calculator has no line 8z input. The first map
sends the amount as `e01200`, which Tax-Calculator adds to AGI and to nothing else
(`calcfunctions.py:534-544`; the net investment income tax and the EITC investment-income test
leave it out, `calcfunctions.py:2715-2724` and `3231-3232`). That is the line 8z treatment, so the
first map's path gives the law's answer. The second map leaves the amount out of the engine and
lists it as unexpressed, so its answer leaves $3,300 of gross income out.

**Dependents' own returns (reading).** 123's 16-year-old and 093's dependent1 each earn $45,000 and
must file. Each return owes $3,220.00, by either map's construction of it. The second map adds
that tax to the household's line; the first map counts the main return only. The board's prompt
puts every listed person "in one household group for tax and benefit calculations" and assumes
filing "when required", and neither phrase settles which returns the line covers.
`docs/causes.md` (`shared-head-return-only`) reaches the same view. 067's dependent1, whose only
income is disability pay, files a return in the second map that owes nothing.

**401(k) deferrals above the limit (reading).** 005's spouses each want $23,154 of traditional
and $4,086 of Roth deferrals, $27,240 against the $24,500 limit of 26 U.S.C. 402(g). The first map
scales both down in proportion; the second fills the limit with traditional deferrals first. The
statute caps the total, and the board does not say which deferral stops.

**Employer disability pay under 65 (reading).** Both maps tax employer disability benefits (26
U.S.C. 105(a)). IRS Publication 596 (2025, "Disability Benefits",
https://www.irs.gov/pub/irs-pdf/p596.pdf) treats them as earned income until the plan's minimum
retirement age and as a pension after it; the 2025 Form 1040 instructions put the earlier
payments on line 1h (`second_map/taxcalc/sources/i1040gi.txt:1536-1541`). The board states no
minimum retirement age. The second map reads the pay as earned below age 65; the first map treats
it as unearned income at every age. Only 084 moves: at 62, earned income of $8,400 brings an
earned income credit of $642.60.

**BDC dividends, REIT and PTP income (reading).** 042 and 052 state business development company
dividends and 081 states REIT and PTP income, each beside stated dividends. The second map adds
them to ordinary dividends; the first map does not. The board does not say whether its stated
dividends already include them, and its rule does not settle whether one listed amount repeats
another. 052 moves by $0.15.

## Differences that move no line

- **Representation.** The head counts `n21` and `n1820` (every household); employer disability
  pay at 65 or over, which the first map sends as `e01200` and the second as a pension (002,
  107): Tax-Calculator treats both as unearned income in AGI only; the member returns' own head
  counts (093, 123).
- **Second map errs.** 088's tips: the deduction for qualified tips (26 U.S.C. 224) needs a
  tipped occupation the board does not state, and 088 owes no income tax either way.
- **First map errs.** 056's HSA deduction of $9,915.44 exceeds even the 2026 family limit of
  $8,750 (`second_map/taxcalc/sources/rp-25-19.txt:41-45`), and the first map applies no limit;
  038's self-employed health insurance goes to itemized medical expenses, though the 2025
  Instructions for Form 7206 accept a policy in the individual's own name for a Schedule C
  business (https://www.irs.gov/pub/irs-pdf/i7206.pdf); the first map flags 033's only
  business, a specified service trade with a loss, as not a specified service trade; 098's and
  120's farm rent counts as qualified business income with no stated UBIA, against the first
  map's own reading that rent is not. 108's survivor benefits belong to the survivor-benefits error above.
- **Reading.** 057's and 121's employer disability pay under 65; 114's partnership beside stated
  UBIA of a specified service trade (the second map reads the partnership as one); 067's
  dependent's own return; 052's BDC dividends.

## First-map errors and fixes

1. **Early-distribution tax (064, +2,000.00).** Compute the 72(t) tax for a filer under 59 1/2
   with taxable IRA, 401(k), 403(b) or pension distributions, net of any stated or computable
   exception (disability under 72(m)(7), medical expenses above 7.5% of AGI), and send it as
   `e09900` (TAXSIM needs its own route). Replace `READINGS["retirement_penalty"]`.
2. **Survivor benefits (062, +4,328.39; 108).** Send stated survivor benefits as a taxable pension
   (`e01500` and `e01700`). Replace `READINGS["survivor_benefits"]`.
3. **Passive losses (120, +124.69).** Net rent and farm rent; allow a net loss only up to the 469(i)
   allowance, $25,000 less half of modified AGI above $100,000 (469(i)(3)(F) defines that AGI), with
   real estate professional status false.
4. **HSA limit (056).** Cap the stated deduction at the 223(b) limit: $4,400 self-only or $8,750
   family for 2026, plus $1,000 at 55 or over.
5. **Self-employed health insurance (038).** Deduct a Schedule C or F filer's own premiums under
   162(l) (`e03270`), up to the business's earnings less half of self-employment tax, unless the
   filer or spouse has employer coverage, and take them out of `e17500`.
6. **Specified service trade flag (033).** Compare absolute amounts, so that a business whose only
   result is a specified service trade loss keeps `PT_SSTB_income` 1.
7. **Farm rent as qualified business income (098, 120).** Send farm rent as `e27200` only where the
   board states UBIA for that person, or keep it in `e02000` alone, as for rent.
8. **Disability pay (documentation).** `READINGS["disability_benefits"]` should name the
   minimum-retirement-age question that Publication 596 raises; the map's `e01200` path amounts to
   the reading that the plan's minimum retirement age has passed.

## What the comparison shows and what it does not

**It shows** how much of the Tax-Calculator check depends on the first map's derivation of the
return. A second derivation reproduces all four of the first map's answers in 79 households. Where
it does not, the rulings put the error on the second map in 11 lines and on the first in 3 (062,
064, 120); 5 lines rest on readings of facts the board does not state, 093 mixes an error of the
second map with a reading, and 022 turns on a missing engine input that the first map handles as
the law does. In 76 households' income tax, 97 households' refundable credits and all 100
households' self-employment tax, both maps' runs reproduce the key, so each of those answers is
reproduced by a run of another lineage whichever map one trusts. The key publishes no payroll
line; both maps reproduce the policyengine-us rerun's payroll tax in all 100. In six households
(020, 052, 076, 107, 114, 121) both maps give the same income tax and both differ from the key, so
the first map's disagreement there does not come from its own derivation. Of the 16 cells where
only the first map's run reproduces the key, the second map errs in 10, four rest on a reading
(042, 081, 084, 123), and in two (062 and 064) the first map and the key share a departure from
the law, so the key's answer there is contested.

**It does not show** errors the two maps share. Both read the same stated facts and the same
glossary, both take state and local income or sales tax from the same file of policyengine-us
amounts, both run the same engine, and Claude agents wrote both (the trailers of the commits that
wrote the first map and the second map's work log name the models), so a mistake those models tend
to make in both maps leaves no trace here. Some shared readings surfaced along the way: both maps
allow 098's $11,100 farm rent loss under the 469(i) allowance, which needs active participation
the board does not state (a run with the loss suspended moves no line, since 098 owes nothing
either way); both leave over-the-counter expenses out of medical expenses, read a stated
scholarship as excluded, tax employer disability pay, and read a disabled member with no earnings
as a qualifying child. It says nothing about the TAXSIM maps, and nothing about 2025 law.