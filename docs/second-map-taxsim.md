# A second TAXSIM map, compared with the first

The TAXSIM answers in this repo rest on one input map: `keycheck/` turns each household's stated facts into TAXSIM's inputs. A map can hide errors and silent choices, so a second agent wrote a second map for the same 100 households without seeing the first. It worked from NBER's documentation for the test build, its own runs of the binary, the board's households as the board states them, and the law. This page compares the two maps input by input and answer by answer, and rules on every difference.

- The second map: `second_map/taxsim/` (`map.py`, `inputs_2026.csv`, `answers_2026.csv`, `notes.csv`, `README.md`, `PROGRESS.md`, `probes/`, `runs/`, `sources/`). Its progress file ends `STATUS: complete`: the map covers all 100 households, as 103 engine records. The folder holds the map as its author left it. Private paths in it now read `INPUT/` (the input folder the author worked from: the board's households as the board states them, which a script drew from PolicyEngine/policybench@c7ede86c, a glossary of the stated facts, the four outputs' definitions, NBER's pages and binary, and a state and local tax file byte-identical to `results/shared/board100_salt_from_pe2.60.0_2026.csv`), `SECOND_MAP/` (the folder itself), `SCRATCH/`, `TRANSCRIPT.jsonl` and `PE_CHECKOUTS/`.
- The first map: the committed record for the board, `results/taxsim/board100_cd2026110117_2026.csv` and `results/dossiers/`, which `keycheck/` wrote as it stood at commit 9507519.
- The comparison: `second_map/taxsim/compare.py` writes `results/second_map/taxsim_inputs_diff.csv` (one row per household, record and input that differs by more than a cent) and `results/second_map/taxsim_answers_diff.csv` (one row per household and line).

## How the two files line up

The maps use the engine differently. The first map sends one record per household with gross wages, carries the traditional 401(k) deferral as negative `nonprop`, enters dependents as counts (`dep13`, `dep17`, `dep18`) and adds a second record for the EITC where the EITC children differ in number from the children under 17. The second map runs three final passes (income tax on box-1 wages; payroll with and without self-employment income), enters dependents by age (`age1`...), and files a return of their own for three dependents with income.

`compare.py` brings both to one layout:

- Wages compare gross, as FICA wages: the first map's `pwages`, the second map's payroll pass. Each filer's traditional deferral compares as its own variable (`p_deferral`, `s_deferral`): the first map's derived return against the second map's gross less box-1 wages. `nonprop` compares without the deferral.
- Every other income, deduction and expense input compares as the second map's income-tax pass against the first map's record.
- Dependents compare as counts. The second map's ages give `dep13` (under 13), `dep17` (ages 0 to 17, which the build's child credit uses on the ages path) and `dep18` (ages 0 to 18, at most three, which its EITC uses); the first map's `dep17` comes from its main record and its `dep18` from the EITC record where it runs one. A row `dependents_path` names each map's way in.
- A member's own return compares with the first map's payroll-only record for that member; `income_tax_return` says whether the record's income tax counts in the household's line.

To say whether a difference moves a line, `compare.py` reruns the second map's records (they give its answers to the cent in all 100 households), sets each group of differing inputs to the first map's values, and reruns. With every group set at once, the records give the first map's four answers to the cent in all 100 households, so the layout misses no difference that moves a line. A group "moves a line" when it changes one of the four answers by more than $1.

## Classes

| Class | Meaning |
|---|---|
| `second_map_errs` | The second map's input departs from the law or the board's rule, or from what the engine does with it. |
| `first_map_errs` | The first map's input departs from the law or the board's rule. |
| `both_readings_defensible` | The maps read something the household does not state differently, and each reading fits the stated facts and the law. |
| `engine_limit_handled_differently` | The maps handle a limit or defect of the engine differently, for example by entering dependents through a different input path. |
| `representation_moves_no_line` | The maps say the same thing in different inputs, or one sends an input the engine uses for nothing federal; no line moves. |

"The board's rule" means the board's preface: an unlisted amount is 0 and an unlisted fact or status is false (PolicyEngine/policybench@c7ede86c:policybench/prompts.py:15-27). Like `docs/causes.md`, these rulings read it to mean that a provision which excludes or allows something only on a fact does not apply when the household does not state the fact.

## Results

- **Inputs:** 30 of the 100 households have every engine input equal. The other 70 differ in 138 inputs, which fall into 116 differences (a household and a group of inputs that carry one choice).
- **Answers:** 69 households have all four answers equal within $1. The other 31 each differ on one line: 17 on tax before refundable credits and 14 on refundable credits. Self-employment tax and federal employee payroll tax agree in all 100.

Agreement with the key, household by household. The key publishes no federal employee payroll line; as `scripts/agreement.py` does, the comparison uses the policyengine-us 2.60.0 rerun for that line.

| Line | Both maps agree with the key | Only the first | Only the second | Neither |
|---|---:|---:|---:|---:|
| Tax before refundable credits | 66 | 7 | 0 | 27 |
| Refundable credits | 86 | 10 | 0 | 4 |
| Self-employment tax | 100 | 0 | 0 | 0 |
| Federal employee payroll tax | 100 | 0 | 0 | 0 |

Differences by class:

| Class | Differences | That move a line | Input rows |
|---|---:|---:|---:|
| `second_map_errs` | 21 | 7 | 23 |
| `first_map_errs` | 13 | 4 | 14 |
| `both_readings_defensible` | 10 | 8 | 18 |
| `engine_limit_handled_differently` | 19 | 16 | 22 |
| `representation_moves_no_line` | 53 | 0 | 61 |
| All | 116 | 35 | 138 |

## The 35 differences that move a line

The amount is the second map's answer less the answer its records give with that group set to the first map's values. "Key" says which map's answer the key holds within $1. `results/second_map/taxsim_inputs_diff.csv` gives each ruling in full.

| Household | Line | Group | Amount | Class | Ruling | Key |
|---|---|---|---:|---|---|---|
| 000 | tax | `transfers` | +1,005.66 | `second_map_errs` | The second map puts 48,000 of veterans' benefits in `transfers`. The build adds `transfers` to the Social Security test (probe P1), which 26 U.S.C. 86(b)(2) does not. | neither |
| 002 | tax | `transfers` | +1,538.66 | `second_map_errs` | The same, 48,000 of veterans' benefits. | neither |
| 007 | tax | `transfers` | +28.98 | `second_map_errs` | The same, 284.12 of tax-exempt pension. | first |
| 042 | tax | `transfers` | +479.40 | `second_map_errs` | The same, 4,700 of tax-exempt Roth IRA distributions. | first |
| 122 | tax | `transfers` | +6.12 | `second_map_errs` | The same, 60 of tax-exempt pension. | neither |
| 074 | refundable | placement | +231.46 | `second_map_errs` | The second map puts a 3,025.59 state tax refund in `nonprop`, which the build counts as EITC earned income (P2); 074 has no wages or self-employment income, so 32(c)(2)(A) gives no EITC. | first |
| 093 | tax | dependents | -500.00 | `second_map_errs` | The second map claims dependent1 (27, disabled, 45,000 of wages) as a qualifying child. A year of 45,000 of wages rules out the 22(e)(3) disability that 152(c)(3)(B) needs (an inference: the comparison did not read the regulations on substantial gainful activity), and the gross income fails 152(d)(1)(B). The key pays the 500 credit too (`docs/causes.md`, pe-other-dependent-credit-without-dependency-tests). | neither |
| 030 | tax | scholarship | +190.00 | `first_map_errs` | 5,000 of educational assistance with no tuition stated: 117(a)-(b) excludes only what pays qualified tuition, which the board's rule makes 0, so the whole amount is income. | first |
| 068 | tax | scholarship | +12,818.36 | `first_map_errs` | The same, 73,000. | first |
| 062 | tax | survivor benefits | +4,443.42 | `first_map_errs` | 28,800 of survivor benefits other than Social Security are income (61(a), 72); each exclusion needs an unstated fact. | first |
| 120 | tax | passive loss | +124.15 | `first_map_errs` | Rent of 2,000 and a farm rental loss of 2,446.59 net to a passive loss (469(c)(2)) that 469(a) disallows; the 469(i) allowance needs active participation, which the household does not state. | neither |
| 005 | tax | deferral order | -1,490.56 | `both_readings_defensible` | Each spouse wants 27,240 of 401(k) deferrals against a 24,500 limit. The first map scales traditional and Roth down in proportion; the second gives the traditional deferrals the room first. | neither |
| 038 | refundable | 162(l) deduction | -22.65 | `both_readings_defensible` | The second map deducts the self-employed head's 100 of premiums under 162(l); the first counts them as medical expenses. The amount comes from a side effect of negative `nonprop` on the build's EITC earned income. | first |
| 042 | tax | BDC income | +15.74 | `both_readings_defensible` | Whether 70.94 of BDC income sits inside the stated dividends; the household does not say. | first |
| 062 | tax | farm rent | +115.03 | `both_readings_defensible` | Farm rent as qualified business income (the first map; the household states unadjusted basis of qualified property) or as rent from no trade or business (the second map; the board's rule). | first |
| 081 | tax | REIT/PTP income | +1.19 | `both_readings_defensible` | Whether 6.22 of REIT/PTP income sits inside the stated dividends (the first map adds nothing) or comes on top of them (the second map enters it in `scorp`). | first |
| 067 | tax | member's return | +945.00 | `both_readings_defensible` | The second map adds the income tax on a dependent's own return to the household's line; the first counts the head's return only. Neither the output's text nor the board's preface decides it. | first |
| 093 | tax | member's return | +3,220.00 | `both_readings_defensible` | The same. | neither |
| 123 | tax | member's return | +3,220.00 | `both_readings_defensible` | The same. | neither |
| 008 | refundable | dependents | -5,896.42 | `engine_limit_handled_differently` | On the ages path the build's 2026 EITC uses the childless rates for every family size (P3); the counts path gives the Rev. Proc. 2025-32 EITC. | first |
| 012 | refundable | dependents | -2,744.00 | `engine_limit_handled_differently` | The same. | first |
| 026 | refundable | dependents | +4,318.75 | `engine_limit_handled_differently` | The same. | neither |
| 028 | refundable | dependents | +3,965.87 | `engine_limit_handled_differently` | The same. | first |
| 032 | refundable | dependents | -2,208.50 | `engine_limit_handled_differently` | The same. | first |
| 038 | refundable | dependents | -5,648.63 | `engine_limit_handled_differently` | The same. | first |
| 046 | refundable | dependents | +2,661.51 | `engine_limit_handled_differently` | The same: the ages path pays an EITC where the law pays none. | first |
| 054 | refundable | dependents | -5,141.04 | `engine_limit_handled_differently` | The same. | first |
| 064 | refundable | dependents | +946.50 | `engine_limit_handled_differently` | The same. | first |
| 086 | refundable | dependents | +703.52 | `engine_limit_handled_differently` | The same. | first |
| 100 | refundable | dependents | -606.69 | `engine_limit_handled_differently` | The same. | neither |
| 109 | refundable | dependents | -6,098.14 | `engine_limit_handled_differently` | The same. | neither |
| 119 | refundable | dependents | +2,683.99 | `engine_limit_handled_differently` | The same. | neither |
| 076 | tax | dependents | +200.00 | `engine_limit_handled_differently` | On the ages path the build's 2026 child care credit is 0; on the counts path it uses the pre-2026 rates (P4). 26 U.S.C. 21(a)(2) as amended gives more than either. | neither |
| 082 | tax | dependents | +600.00 | `engine_limit_handled_differently` | The same. | neither |
| 099 | tax | dependents | +1,200.00 | `engine_limit_handled_differently` | The same. | neither |

The probes P1 to P4 come from `python3 second_map/taxsim/compare.py --probes`:

- P1: a single filer of 70 with 30,000 of Social Security and 30,000 of pension has 13,850 of taxable benefits; 5,000 of `transfers` raises that to 18,100 (0.85 of 5,000) and the tax from 2,116 to 2,626. With wages and no benefits, 10,000 of `transfers` moves nothing.
- P2: 3,025.59 in `nonprop`, and nothing else, gives a single filer of 54 an EITC of 231.46; the same amount in `pensions` gives 0.
- P3: a single filer with 30,000 of wages and one child gets an EITC of 2,295.00 on the ages path and 3,450.62 on the counts path, the law's figure; with two children, 2,295.00 and 6,029.23 (the law's).
- P4: a joint return with 100,000 of wages, two children and 8,000 of child care gets no child care credit and an EITC of 2,049.74 on the ages path (the law gives no EITC); the counts path gives a 1,200 child care credit at the pre-2026 rate, against the law's 2,100, and no EITC.

## The 81 differences that move no line

- `rentpaid` (28 households): the second map sends the stated rent, which the build uses only for state renter credits; with `state` 0 it does nothing. Representation.
- `transfers` in 17 households without Social Security: representation (P1). In 10 more households with Social Security the input errs as above but moves no line at their incomes.
- Placement of a state tax refund (8 households): the first map enters it in `pensions`, the second in `nonprop`; none of the 8 gets an EITC either way, and no line moves. Representation.
- Dependents (3 households: 067, 117, 123): the ages path changes nothing at their incomes. (In 008, whose line the EITC moves, the ages path also gives the 17-year-old the 2,200 child credit, which 26 U.S.C. 24(c)(1) denies; recoding that child as 18 alone moves nothing, and the second map's README traces that to the earned-income limit on the refundable credit.)
- Itemized amounts in `mortgage` (10 households), each a consequence of a choice above or one of these: the first map enters cash gifts with no 170(b)(1)(G) ceiling (056, 074); the second map's medical floor turns negative on a negative AGI and enters 27.50 of medical deduction for 056, which states no medical expense (`second_map/taxsim/map.py:557`); the rest follow from AGI differences that `transfers`, the scholarship, the survivor benefits or the passive losses make. No household's itemizing changes.
- The HSA deduction for 056: the first map takes the stated 9,915.44; 26 U.S.C. 223(b)(2) caps it at 4,400 for self-only coverage (Rev. Proc. 2025-19). First map errs; 056's income tax comes to 0 either way.
- 098's farm rental loss of 11,100 and 108's survivor benefits of 10,392: first map errs, as for 120 and 062; both households' income tax comes to 0 either way.
- 052's 0.40 of BDC income and 112's farm rent: the same readings as 042 and 062.

## Errors this comparison finds

In the first map (`keycheck` at 9507519), each with the fix the lead can apply:

1. Educational assistance stays out of income (`READINGS["educational_assistance"]`). Fix: count it as income, in TAXSIM's `pensions` so that it does not reach EITC earned income. Moves 030 by +190.00 and 068 by +12,818.36. `docs/causes.md` (shared-scholarship-not-income) takes the same position but says 030 owes 0 either way; TAXSIM gives 190.00 (AGI 18,000 less the 16,100 standard deduction, at 10%).
2. Survivor benefits other than Social Security stay out of income (`READINGS["survivor_benefits"]`). Fix: add them to `pensions`. Moves 062 by +4,443.42 on the second map's other inputs; with the first map's farm-rent entry it gives 4,328.39, the board's own alternative.
3. Passive rental and farm-rental losses reduce income. Fix: net a return's rent and farm rent and suspend a net loss under 469(a), since no household states active participation. Moves 120 by +124.15; 098 does not move. The same reading would suspend 004's partnership loss of 135, which both maps deduct.
4. Cash and non-cash gifts carry no 170(b)(1) percentage ceiling. Fix: apply the ceilings before the 0.5% floor. No line moves on the board (056, 074).
5. The HSA deduction carries no 223(b) limit (`READINGS["hsa"]`). Fix: cap it at the limit for the coverage the household can have. No line moves on the board (056).

The first map also sends rent to `intrec` (no 20% deduction) but farm rent to `scorp` (20% deduction). The households with farm rent state unadjusted basis of qualified property, which supports the farm-rent entry; the comparison rules the difference defensible either way.

In the second map: `transfers` raises taxable Social Security in this build, against its README's statement that the input has no effect on the four lines; `nonprop` gives 074 an EITC on a state tax refund; it claims 093's adult earner as a dependent; and its medical floor goes negative on a negative AGI.

## What the comparison shows and what it does not

It shows that a second map, which its author wrote without sight of the first, gives the same four answers in 69 households, and that every difference in the other 31 has a named cause. Taking the group that moves each of the 31 cells most:

- the engine's input path for dependents accounts for 16;
- errors in the second map for 6 (000, 002, 007, 042, 074, 122);
- the board's rule, which the second map applies and the first map does not, for 4 (030, 062, 068, 120); `docs/causes.md` already argues for the same answers, and by its account the board excludes 062's and 120's outputs and scores 068's, so 068's scored answer stands contested;
- readings of facts the household does not state for 5 (005's deferral order, 081's REIT income, and the members' own returns in 067, 093 and 123; 093 also carries the second map's dependent claim).

The second map never agrees with the key where the first map does not. Where only the first map agrees (17 cells), the second map's answer comes from the ages path's EITC (9: 008, 012, 028, 032, 038, 046, 054, 064, 086), one of its errors (3: 007, 042, 074), the board's rule (3: 030, 062, 068) or a defensible reading (2: 067, 081).

It does not show that the first map's answers are right where the two agree. Both maps share:

- the board's stated facts and its preface;
- the state and local income or sales tax amounts (`results/shared/board100_salt_from_pe2.60.0_2026.csv`);
- the engine, TAXSIM test build cd2026110117, with its departures from 2026 law that neither map can avoid: the child care credit at old rates or none, no overtime, tips or non-itemizer charity deduction, no blindness input, no tax-exempt interest in the Social Security test, and no saver's credit;
- readings both maps made alike: disability benefits taxable, a state tax refund taxable in full, the net investment income tax inside the line, over-the-counter items outside medical expenses, alimony under the post-2018 rule, surviving spouses without a dependent child filing single, no deduction for auto loan interest, and 004's partnership loss deducted;
- whatever both authors' models tend to get wrong in the same way: Claude agents wrote both maps.

Agreement between the two maps therefore tests the map, not the engine and not the key. A cell that both maps give and the key holds stays "reproduced by a run of another lineage" only through TAXSIM itself; the second map adds no new lineage.

## Rerun

```
scripts/get_taxsim.sh          # fetches the binary into work/nber/
python3 second_map/taxsim/compare.py --probes
```

`compare.py` needs only Python's standard library and the binary. It stops if the second map's records no longer give its answers, if the groups together no longer give the first map's answers, or if a difference has no ruling; it warns if a difference classed as moving no line moves one.
