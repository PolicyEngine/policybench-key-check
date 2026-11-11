# TAXSIM blind map, tax year 2026

This folder maps PolicyBench's 100 board households to NBER's TAXSIM test build without sight of any other map or answer key, runs the engine, and reports four federal quantities for each household:

- `federal_income_tax_before_refundable_credits`
- `federal_refundable_credits`
- `self_employment_tax`
- `federal_employee_payroll_tax` (employee Social Security, employee Medicare and Additional Medicare Tax only)

`python3 map.py` (standard library, about 2 seconds) regenerates every output from `../input/board/scenarios.csv` and `../input/board/state_and_local_tax_2026.csv`. All 100 households map and run, as 103 engine records: three households add a return for a dependent with income (scenario_067, scenario_093 and scenario_123).

| File | Contents |
|---|---|
| `map.py` | The whole map: 2026 amounts with source lines, readings, statute helpers, engine passes, notes |
| `tsrun.py` | Standard-library runner: writes the CSV on stdin, parses the CSV reply, and raises if the returned `taxsimid`s differ from those sent |
| `inputs_2026.csv` | One row per record and pass (A, B, C): `case_id`, `record`, `pass`, then every engine input |
| `answers_2026.csv` | 400 rows: `case_id`, `quantity`, `value` (to the cent), `formula` |
| `notes.csv` | 600 notes: `case_id`, `quantity_group`, `kind` (`reading`, `computed_from_statute`, `engine_behaviour`, `unexpressed`), `text` |
| `runs/` | Raw engine input and output for every pass of the default run |
| `probes/` | The probe scripts and their inputs and outputs, `probe1` to `probe10` |
| `sources/` | Statutes (Cornell LII) and IRS guidance (irs.gov), as fetched HTML/PDF plus extracted text; every citation below names file and line |
| `PROGRESS.md` | The working log, in the order findings arrived |

## The engine

- Binary: `../input/taxsim/taxsimtest-osx.exe`, Mach-O x86_64, SHA-256 `21d36bac648d4403eb2f4a5c39dc5f6fca5f281b86af52cf418f22e958f1ceb2`. Its strings name the version `2026110117` and the banner "With TCJA and BBB".
- Every record goes in with `year=2026`, `state=0` (no state tax) and `idtl=2` (all detail columns).
- A record the engine rejects stops the whole run, and later records get no output (probe1; doc `taxsimtest_.txt:631-632`). Two rejections met in probing: `depx=0` with `age1>0`, and a nonzero `sage` on a non-joint return. `tsrun.run` therefore checks that every `taxsimid` sent comes back; all 103 records return in every pass.

### Does the build apply 2026 law?

Mostly. The probes found these 2026 amounts applied correctly:

- the standard deduction (16,100 / 24,150 / 32,200), the aged addition (2,050 / 1,650) and the 2026 brackets (probe1);
- the $6,000 senior deduction with its 6% phase-out above 75,000 / 150,000 of MAGI, applied below `v13` (probe1 #12-#16);
- the $2,200 CTC with the $1,700 refundable limit per child, and the $500 credit for other dependents (probe1, probe4);
- the Social Security wage base of 184,500 and Additional Medicare Tax (probe5);
- NIIT (probe5, probe9).

The build departs from 2026 law in the places listed under "Engine behaviours found by probe".

### Passes

The engine takes one wage figure per person for both income tax and FICA, but 401(k) elective deferrals leave W-2 box 1 while remaining FICA wages (26 USC 3121(v)(1)(A), `sources/lii_26usc3121.txt:496-499`). Several deductions also depend on AGI. `map.py` therefore runs six passes over all records:

| Pass | Purpose |
|---|---|
| 0 | AGI before the IRA and student-loan deductions (MAGI for 219(g)) |
| 1 | AGI after the IRA deduction (MAGI for 221) |
| 2 | AGI after the student-loan deduction: the base for the medical floor and charity limits |
| A | Final income-tax pass, with box-1 wages and the itemized amount in `mortgage`; `map.py` checks that AGI did not move between pass 2 and pass A |
| B | Payroll and SE: gross (FICA) wages plus SE income only |
| C | Payroll: gross (FICA) wages only |

### Formulas

Each quantity sums over the household's records, so a dependent's own return counts in the household total.

| Quantity | Formula | Why |
|---|---|---|
| Income tax before refundable credits | `A.fiitax + A.v25 + A.actc` | `fiitax` nets the EITC (`v25`) and the additional CTC (`actc`) out; adding them back leaves tax after nonrefundable credits. `fiitax` includes NIIT and AMT (probe5, probe9) but not Additional Medicare Tax, despite the doc (probe1 #23: single wages 250,000 gives `fiitax` 51,304, the regular tax on 233,900; the 450 of Additional Medicare Tax sits in `tfica`). |
| Refundable credits | `A.v25 + A.actc` | `v22` holds only the nonrefundable CTC/ODC, and `actc` holds the refundable part (probe1 #2, #9-#11). The engine's ACTC follows Form 8812: unused CTC plus ODC, limited by $1,700 per child and the earned-income formula. |
| SE tax | `(B.tfica - B.addmed) - (C.tfica - C.addmed)` | `tfica` holds employee FICA plus Additional Medicare Tax plus the full SECA (probe1, probe5); `fica` above the wage base is not twice employee FICA, so `map.py` does not use it. |
| Employee payroll tax | `(C.tfica - C.addmed) + B.addmed` | Employee Social Security and Medicare on gross wages, plus Additional Medicare Tax. No household has Additional Medicare Tax on SE income (`B.addmed = C.addmed` on all 103 records), so where that piece belongs does not arise. |

The engine rounds `fiitax`, `v25` and `actc` to the cent separately, so the income-tax formula can land a cent below zero when tax before credits is 0. That happened once (scenario_109: -0.01); `map.py` reports 0.00 and says so in a note.

## What each engine input holds

Unless stated, amounts sum over the head and spouse. Doc lines refer to `../input/taxsim/docs/taxsimtest_.txt`.

| Input | Holds | Why |
|---|---|---|
| `mstat` | 2 with a spouse, else 1; 8 on a dependent's own return | Doc lines 89-94. With `mstat=1` and `depx>0` the engine assigns head of household (doc lines 95-97; probe1 #2 gives `v13` 24,150). |
| `page`, `sage` | Ages; `sage` 0 on single returns | Doc lines 100-106; a nonzero `sage` on a single return is fatal (probe8). |
| `depx`, `age1`-`age8` | Dependents, oldest first. Anyone under 19, or `is_disabled` at any age (26 USC 152(c)(3)(B), `lii_26usc152.txt:44`), is a qualifying child; anyone else whose gross income is under 5,300 (`rp-25-32.txt:908-910`) is a qualifying relative; others file their own single return | No household has a qualifying relative, and nobody files separately as a non-dependent. The map codes infants as 1 (doc lines 118-119: "Code infants as 1"; age 0 means "unspecified" and loses the CTC, probe1 #5). The engine treats every coded age 0-17 as a CTC child (probe4), so a 17-year-old keeps their true age and the 17-to-18 recode runs as an alternative. |
| `pwages`, `swages` | Pass A: `employment_income` less the traditional 401(k) deferral allowed under 402(g). Passes B and C: gross `employment_income` | Box 1 versus FICA wages, as above. `tip_income` and `fsla_overtime_premium` already sit inside `employment_income` (glossary: wages "including tips"; the scenario preface: wages include overtime). |
| `psemp`, `ssemp` | `self_employment_income` + `farm_operations_income` + `partnership_se_income`, before SE tax | Doc lines 132-135 and 636-637 (pre-FICA). The engine charges SECA and computes QBI net of the SE-tax deduction (probe10). `farm_income` restates `farm_operations_income` (Schedule J label; equal in both households that carry it) and is not entered twice. |
| `pprofinc`, `sprofinc` | `sstb_self_employment_income_before_lsr`, before SE tax | Doc lines 245-248 (SSTB, subject to SECA). probe10 shows the engine treats it exactly like `psemp` below the threshold, so the doc's request for a "post-FICA" amount (lines 637-638) would take the SE deduction twice; no household reaches the SSTB phase-in. |
| `scorp` | `partnership_s_corp_income` less its `partnership_se_income` part, plus `qualified_reit_and_ptp_income` | Ordinary income with NIIT and a 20% QBI deduction, without SECA (probe5 #24, probe10 #4), which is the law's treatment of a passive partnership share and of qualified REIT dividends (199A(b)(1)(B)). The engine allows `scorp` losses against wages (probe5 #36). |
| `dividends` | `qualified_dividend_income` | Doc lines 138-141. |
| `intrec` | `taxable_interest_income` + `non_qualified_dividend_income` + `qualified_bdc_income` + `estate_income` + the allowed result of rental and farm rental | Doc line 143 (unqualified dividends may go here). The doc's slot for rent and other property income is `otherprop`, but the engine drops `otherprop` from AGI in 2024-2026 (probe7); `intrec` gives the same treatment (ordinary income, NIIT, EITC investment income), under the doc's rule "Any income item not mentioned above can be placed wherever you think Taxsim will treat it most correctly" (lines 308-310). |
| `stcg`, `ltcg` | `short_term_capital_gains`; `long_term_capital_gains` + positive `non_sch_d_capital_gains` | Capital gain distributions are long-term. The engine applies the $3,000 loss limit (probe5). |
| `pensions` | Taxable private pension, IRA, 401(k) and 403(b) distributions, plus `disability_benefits` and `survivor_benefits` under the default readings | Doc line 174. |
| `gssi` | All four Social Security benefit types | Doc line 179; the engine's 26 USC 86 computation matches a hand calculation (probe5). |
| `pui`, `sui` | `unemployment_compensation` | Doc line 182. |
| `nonprop` | `salt_refund_income` (taxable, per the glossary) + `miscellaneous_income` + taxable `educational_assistance`, less the HSA deduction, the educator expense deduction, the SE health insurance deduction, the IRA deduction and the student-loan deduction | Doc lines 161-171 (adjustments as negative income). Each deduction comes from the statute; see the next section. |
| `transfers` | Veterans' benefits, workers' compensation, child support received, financial assistance, tax-exempt pension and IRA amounts | Doc line 188: non-taxable, used only for state rebates. No effect on the four quantities. |
| `rentpaid` | `pre_subsidy_rent` | Doc line 198: state rebates only. |
| `proptax` | `real_estate_taxes` + the household's amount in `state_and_local_tax_2026.csv`, before any cap | The engine applies the SALT cap and the AMT addback only to `proptax` (probe5 #1-#3; probe9 #1 vs #3). The doc's `otheritem` slot for "other state and local taxes" (lines 208-212) is neither capped nor added back (probe5 #2; probe9 #2 vs #5), so the `otheritem` placement runs as an alternative. |
| `otheritem` | 0 (the SALT amount under the alternative) | As above. |
| `childcare` | `spm_unit_pre_subsidy_childcare_expenses` | Doc line 220. The engine's 2026 CDCC is 0 whatever the amount (probe7). |
| `mortgage` | Deductible mortgage interest + deductible charity + medical expenses above the floor, each computed from the statute | Doc lines 223-229: home mortgage interest, deductible medical expenses and charity belong here. The engine applies no floor or limit to this input (probe5), so `map.py` applies them first. |
| Not used | `otherprop` (dropped by the engine), `pbusinc`/`sbusinc` (same as `psemp` here), `age9`-`age10`, `dep*`, `opt*`, `mtr` | |

## Statute computations made before input

The common brief says that where the engine takes an amount the law limits as already limited, the map computes the limit from the statute. Each household's notes (`kind = computed_from_statute`) show the arithmetic.

| Item | Computation | Source |
|---|---|---|
| 401(k) deferrals (24 households) | Traditional plus Roth limited to 24,500, plus 8,000 at 50+ or 11,250 at 60-63, and to wages; traditional takes the room first | 26 USC 402(g); Notice 2025-67 `n-25-67.txt:35-51` |
| Traditional IRA deduction (24 households) | Contribution limited to 7,500 (+1,100 at 50+) and to compensation (combined compensation on a joint return); deduction phased out over 81,000-91,000 single or 129,000-149,000 joint for an active participant, 242,000-252,000 when only the spouse participates; reduction rounded down to $10, $200 minimum | 26 USC 219(b),(c),(g) (`lii_26usc219.txt:102-115`); `n-25-67.txt:162-190` |
| Student-loan interest (4) | Up to 2,500, phased out over MAGI 85,000-100,000 single or 175,000-205,000 joint | 26 USC 221; `rp-25-32.txt:1003-1009` |
| HSA deduction (2) | Stated amount capped at 4,400 self-only or 8,750 family, +1,000 per filer 55+; self-only where the filer has no spouse or dependent to cover | 26 USC 223(b); Rev. Proc. 2025-19 `rp-25-19.txt:41-45` |
| Educator expenses (2) | 350 per educator | `rp-25-32.txt:747-759` |
| SE health insurance (1) | Person-paid premiums of the self-employed filer and family members without ESI, limited to SE earnings less half of SE tax; those premiums then leave the medical total | 26 USC 162(l) |
| Mortgage interest (11) | Interest x 750,000 / balance when acquisition debt exceeds 750,000 | 26 USC 163(h)(3)(F) |
| Charity (17 itemizing candidates) | Non-cash limited to 50% of AGI and cash to 60% less the non-cash allowed, then the 2026 floor of 0.5% of AGI | 26 USC 170(b)(1)(A),(G),(I) (`lii_26usc170.txt:36,88,100`) |
| Medical (84) | `other_medical_expenses` + the larger of the two person-paid premium inputs, less SE health premiums already deducted, above 7.5% of AGI; OTC items excluded by default | 26 USC 213(a),(b) |
| Passive rental losses (2) | Rental and farm rental net together, and 469 suspends a net loss (no active participation stated, no other passive income) | 26 USC 469(c)(2),(i) |
| Section 22 credit (16 returns with tax and a qualified person) | Initial amount less nontaxable Social Security, VA benefits and half of AGI over 7,500 / 10,000; 0 in every case | 26 USC 22(c),(d) (`lii_26usc22.txt:12-51`) |
| QBI W-2 wage and UBIA limit (6 households with UBIA) | Taxable income before the QBI deduction sits below the 2026 threshold (201,750 / 403,500) in all six, so the limit does not apply | 26 USC 199A(b)(2),(3); `rp-25-32.txt:948-958` |

A medical, charity or mortgage amount enters `mortgage` whether or not it beats the standard deduction; the engine chooses.

## Readings and the alternatives they rule out

Each reading has an alternative, and `map.py` reruns the whole pipeline (all six passes) under it. `notes.csv` records every household the alternative moves, as `ALTERNATIVE <key>=<value> moves: ...`.

| Reading (default) | Alternative | Households moved (income tax before refundable credits, default -> alternative) |
|---|---|---|
| `disability_benefits` taxable as employer-financed (26 USC 105(a)); the 104(a)(3) exclusion needs employee-paid premiums, which nobody states | Excluded | 002 (3,428.96 -> 870.80), 067 (6,561.24 -> 5,616.24), 107 (211.23 -> 0), 121 (875.34 -> 0) |
| Non-Social-Security `survivor_benefits` taxable as a survivor annuity | Excluded | 062 (4,443.42 -> 1,029.51) |
| Alimony under the post-2018 rule (instrument date not stated; 215 repealed, `lii_26usc215.txt`): neither income nor deduction | Pre-2019 rule | 020 (70,401.42 -> 68,403.34); 031 and 056 do not move |
| `educational_assistance` taxable (no qualified tuition stated, so the 117 exclusion is 0) | Excluded | 030 (190.00 -> 0), 068 (14,728.38 -> 1,910.02) |
| Net passive rental loss suspended | Allowed in full | 120 (40,454.90 -> 40,330.21) |
| `tip_income` inside `employment_income` | On top of it (also moves payroll) | 088 (0 -> 735.87; payroll 1,421.15 -> 2,155.55) |
| Traditional 401(k) deferrals take the 402(g) room first | Roth first | 005 (107,377.35 -> 109,130.95) |
| HSA deduction capped at the 223(b) limit | As stated | none: under the self-only reading the cap binds for 056 (9,915.44 stated, 4,400 entered), yet the answers do not move because 056 owes no tax either way |
| Qualified REIT/PTP income in `scorp` (20% QBI deduction) | In `intrec` | 081 (26,933.76 -> 26,934.06) |
| Rental is not a 199A trade or business | Rental is QBI (after the 469 netting) | 022 (11,313.77 -> 11,113.57), 076 (20,003.80 -> 19,811.80), 120 (40,454.90 -> 40,358.90) |
| Over-the-counter items are not medical care (213(b)) | Deductible | 114 (11,265.27 -> 10,825.27), 121 (875.34 -> 835.34) |
| True ages coded (a 17-year-old gets the engine's CTC) | Code 17 as 18 | none: the earned-income formula, not the number of children, limits scenario_008's ACTC (4,202.61) |
| A dependent with income files a return, counted in the household totals | Main return only | 067 (6,561.24 -> 5,616.24), 093 (11,848.99 -> 8,628.99; payroll 12,469.50 -> 9,027.00), 123 (8,660.24 -> 5,440.24; payroll 11,092.50 -> 7,650.00) |
| NIIT counted as income tax (`fiitax` includes it) | Excluded | 005 (107,377.35 -> 101,655.37), 020 (-222.64), 052 (-218.44), 120 (-87.40) |
| State and local income-or-sales tax in `proptax` | In `otheritem` (the doc's slot) | 005 (107,377.35 -> 98,821.02), 078 (24,260.46 -> 23,720.06) |

Other readings with no alternative run, each noted per household:

- `is_surviving_spouse` (12 households): 11 live alone with no dependent son or daughter, so the 26 USC 2(a)(1)(B) test fails (`lii_26usc2.txt:7`) and they file single; scenario_111 has a spouse on the return and files jointly.
- `is_unmarried_partner_of_household_head` (020, 056) sits on the only adult, so it creates no spouse or dependent.
- `unreimbursed_business_employee_expenses` (16 households): 26 USC 67(h) allows no miscellaneous itemized deduction after 2017 (`lii_26usc67.txt:75-76`), and nobody has a status that 62(a)(2) carves out, so these households get no deduction.
- `auto_loan_interest` (23 households): the 26 USC 163(h)(4) deduction needs a new, US-assembled vehicle bought after 2024, which no household states, so these households get no deduction.
- `domestic_production_ald` (064): section 199 no longer applies after 2017, so the map does not enter it.
- AOTC flags (4 households) come with no qualified expenses, so the credit is 0.
- `social_security_dependents` stated on an adult counts as that adult's benefit.
- `partnership_se_income` (064) is the SE part of `partnership_s_corp_income`.

## Engine behaviours found by probe

The map reports the engine's answer in every case below and does not correct it. The households' notes give the statutory figure where `map.py` computes one.

| Behaviour | Evidence | Households |
|---|---|---|
| 2026 EITC: the build applies the childless 7.65% phase-in and phase-out rates to every family size, with the right 2026 maximums and thresholds. Example: one child, wages 30,000: engine 2,295, law 3,450.60. The 2023-2025 runs of the same binary use 34% / 40% / 45%, and childless 2026 values match the law | probe2, probe3; probe8 (joint, 2 children, AGI 97,000: engine 2,279.24, law 0) | 13: 008, 012, 026, 028, 032, 038, 046, 054, 064, 086, 100, 109, 119 (008: engine 2,334.58, law about 8,231) |
| CDCC (`v24`) is 0 in 2026 for any childcare amount; it works in 2023-2025 | probe7, `p06_text_otherprop_cdcc.out` | 076, 082, 099, 117, 119 |
| CTC goes to dependents coded 0-17; 24(c)(1) requires the child not to have attained 17 | probe4 | 008 (no effect, see above) |
| EITC child status runs by age to 18, and the engine has no disability input, so a disabled adult child does not count for the EITC (32(c)(3)(A) via 152(c)(3)(B)) | probe4 | 064, 067, 093 (statutory EITC is 0 either way at their incomes) |
| `otherprop` drops out of AGI in 2024-2026 (works in 2023) | probe5, probe7 | none: `map.py` routes property income to `intrec` |
| SALT cap uses the 2025 amounts in 2026: cap 40,000 and phase-down from MAGI 500,000, where 2026 law has 40,400 and 505,000 (164(b)(7), `lii_26usc164.txt:76,88`) | probe5 #5-#6, probe8 #8-#9 | 078 |
| `otheritem` escapes both the SALT cap and the AMT addback, though the doc calls it an AMT preference | probe5 #2-#3, #33; probe9 | handled by putting SALT in `proptax` |
| No 2/37 reduction of itemized deductions in the 37% bracket (26 USC 68) | probe5 #7 | none reaches it |
| SE tax on net earnings under $400 (1402(b)(2) exempts them) | probe8 #1-#3 (`psemp` 300 gives 42.39) | 102 (net earnings 0.92) |
| No 199A(i) $400 minimum QBI deduction | probe1 #31 | none with taxable income |
| No floor on `mortgage`; the doc says it takes deductible medical, so `map.py` applies the 7.5% floor first | probe5 | all itemizers |
| `scorp` losses offset wages with no passive-loss limit, although the doc says that limit applies | probe5 #36 | 004 (partnership loss of 135) |
| A dependent filer (`mstat=8`) gets the 26 USC 63(c)(5) standard deduction, max(1,350, earned + 450), and no EITC | probe1 #35-#37, probe8 | 067, 093, 123 |
| `fiitax` excludes Additional Medicare Tax, contrary to the doc's output list (lines 448-452) | probe1 #23-#24, probe5 #27 | 4 records with wages over the threshold |
| `v22` holds only the nonrefundable CTC/ODC; `actc` holds the refundable part | probe1 | all with children |
| One rejected record aborts every later record | probe1 | none (runner checks) |

## What the engine cannot express

The engine has no input for any of these facts. Following the common brief, the map forces none of them into another input. Each household's note gives the statutory amount the engine leaves out where `map.py` computes one (`kind = unexpressed`).

| Fact | Law | Households |
|---|---|---|
| Blindness (`is_blind`): additional standard deduction 2,050 unmarried or 1,650 married, per person | 26 USC 63(f)(2), `lii_26usc63.txt:99-103`; `rp-25-32.txt:804-810` | 9: 008, 027, 057, 079, 084, 088, 111, 118, 122 |
| Qualified overtime deduction | 26 USC 225 (`lii_26usc225.txt:3-9`): up to 12,500 / 25,000, reduced by $100 per $1,000 of MAGI over 150,000 / 300,000 | 11: 020, 026, 037, 046, 049, 064, 083, 089, 091, 100, 117 |
| Qualified tips deduction, if the occupation qualifies (not stated) | 26 USC 224 | 088 |
| Non-itemizer charitable deduction (up to 1,000 / 2,000 of cash gifts) | 26 USC 170(p), `lii_26usc170.txt:854` | 12 standard-deduction households with cash gifts: 005, 020, 049, 055, 056, 074, 082, 092, 099, 110, 122, 123 |
| Tax-exempt interest in Social Security provisional income | 26 USC 86(b)(2)(B) | 000, 003, 115, 120, 122 (005 and 110 hold it without benefits) |
| 10% additional tax on early distributions | 26 USC 72(t) | 064, 074 (023 qualifies for the disability exception) |
| Saver's credit (no contribution input) | 26 USC 25B; `n-25-67.txt:140-160` | 7: 004, 023, 043, 070, 091, 100, 119 |
| Disabled adult child as an EITC qualifying child | 26 USC 32(c)(3)(A), 152(c)(3)(B) | 064, 067, 093 (no effect at their incomes) |
| QBI W-2 wage and UBIA limitation | 26 USC 199A(b)(2) | none above the threshold |
| Section 22 credit | 26 USC 22 | none positive with tax |
| CDCC in 2026 (engine returns 0) | 26 USC 21 as amended (`lii_26usc21.txt:5-9`) | 076, 082, 099, 117, 119 |

## Facts with no role in the four quantities

The map does not enter these facts. Where it is unclear whether a fact matters, a household note says so.

- `employer_sponsored_insurance_premiums`: employer-paid premiums (glossary), not the person's expense.
- `child_support_expense`: no Code section allows a deduction for it.
- Work-pattern facts: `hourly_wage`, `hours_worked_last_week`, `is_paid_hourly`, `weeks_unemployed`.
- Status flags: `is_pregnant`, `receives_wic`, housing assistance, energy subsidy, and the health-coverage flags (`has_esi` matters only to the SE health deduction).
- Asset balances: `bank_account_assets`, `stock_assets`, `household_vehicles_value`, `auto_loan_balance`. The EITC tests investment income, not assets.
- `pre_subsidy_rent`: entered as `rentpaid`, which feeds state rebates only.

## Results

| Quantity | Households above zero | Sum over 100 |
|---|---|---|
| Income tax before refundable credits | 53 | 767,486.82 |
| Refundable credits | 17 | 51,787.55 |
| SE tax | 9 | 16,376.11 |
| Employee payroll tax | 64 | 355,552.38 |

The engine behaviours above move some answers away from 2026 law. The EITC rates move refundable credits in 13 households, by about 6,000 in scenario_008. The 2026 CDCC moves income tax in up to 5 households, and SE tax on earnings under $400 moves SE tax in scenario_102. The facts the engine cannot express (blindness, overtime, the 170(p) deduction, 72(t), the saver's credit) move income tax in the households listed. The notes give each household's statutory figure, so a reader can tell engine differences from map differences.

## Sources

- TAXSIM docs: `../input/taxsim/docs/taxsimtest_.txt` (fetched 2026-11-10T20:24:43Z, per `fetched_at.txt`).
- IRS:
  - Rev. Proc. 2025-32 (`sources/rp-25-32.pdf`/`.txt`), 2026 inflation-adjusted amounts;
  - Notice 2025-67 (`sources/n-25-67.pdf`/`.txt`), 2026 plan and IRA limits;
  - Rev. Proc. 2025-19 (`sources/rp-25-19.pdf`/`.txt`), 2026 HSA limits.
- Title 26 sections from Cornell LII, saved as `sources/lii_26usc<section>.html`/`.txt`: 2, 21, 22, 24, 25A, 25B, 32, 56, 62, 63, 67, 68, 72, 86, 104, 105, 117, 151, 152, 163, 164, 170, 199A, 213, 215, 219, 221, 223, 224, 225, 402, 469, 1401, 1402, 1411, 3101, 3121.
