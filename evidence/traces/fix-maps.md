# fix-maps: builder unit, Claude Opus 5.5 (claude-opus-5-5), 2026-11-10

- Start: repo head bbd48c1, working tree clean (git status --short empty). Before tables + answers.csv copied to SCRATCH/before/.
- Read: brief-fix-maps.md, brief-common.md, verify-unit-statute.md, verify-map-taxcalc.md, verify-map-taxsim.md (all in full), Map-errors sections of trace-pe-a/b, trace-taxsim-a/b; code keycheck/*.py, scripts/run_taxcalc.py, run_taxsim.py, build_answers.py, agreement.py, make_dossiers.py, make_fact_map.py, tests/.
- Before (HEAD bbd48c1) non-all_agree lines: 2026 key 28 line-1 + 4 line-2; 2026 rerun 24 + 4; 2025 17 + 4 (full list kept in scratch before/*.csv; tables also in git at bbd48c1).
- Data checks (board scenarios.csv, unit.py helpers): 56 persons state both other_health_insurance_premiums and health_insurance_premiums_without_medicare_part_b, 5 only the latter, 0 only the former; so verify-map-taxsim F1's premise ("no board household states the latter") is wrong; the brief's reading 4 (not counted again) holds and drops nothing stated alone. Rental income (022, 076, 083, 120) and estate income (039, 110) are all positive on the board.
- PE 2.60.0 other_health_insurance_premiums.py comment (read this run): "The reported premiums in health_insurance_premiums_without_medicare_part_b less modeled CHIP, Medicaid and Marketplace premiums". qualified_bdc_income: grep of envs/pe260/.../policyengine_us/ finds only its own variable file plus two test yamls (no formula reads it).
- Probe (new) REPO/probes/taxsim/fixmaps_negative_intrec.{in,cd2026110117.out}.csv: negative intrec accepted (id1 pwages 60,000 intrec -1,000 -> v10 59,000; id3 -5,000 -> v10 55,000; id6 2025 same 59,000). TAXSIM's EITC investment test uses the intrec box total: id4 (one child, wages 15,000, intrec 12,500) v25 0; id5 intrec 11,500 v25 4,009.92. So a rent/estate loss in intrec would offset interest for the EITC test (32(i)(2)(C) counts rents only as an excess): noted when a rent/estate loss is entered.
- Sources checked: Rev. Proc. 2025-32 SECTION 4 .23 (152(d)(1)(B) $5,300, line 908) and .29 (221, line 1003); Rev. Proc. 2024-40 SECTION 2 .24 ($5,200, line 574); 199A(e)(2) thresholds 2026 single 201,750 / joint 403,500 (rp-25-32.txt:958-961), 2025 197,300 / 394,600 (rp-24-40.txt:619-621); 2(a)(1)(B) (lii-26-2.verify-unit-statute.txt): (i) disregards 152(d)(1)(B) for the son/daughter test, but (ii) requires the taxpayer be entitled to a 151 deduction for the dependent.
- TC itemizer flag: taxcalc/calculator.py:1486-1491 sets c04470 to 0 unless itemizing, so final out_c04470 > 0 marks a TC itemizer. TAXSIM: v17 > 0 marks itemizers (understand-inputs taxsim.md P9.4).
- DONE unit.py (VERSION 2026-11-10.2): READINGS rewritten/added: dependents text corrected (no "no permanent-disability status" claim; no full-time student; AOC half-time flags not full time), is_disabled (new code path: member age>=19, stated disabled, wages 0 and SE 0 -> qualifying_child; Unit.disabled_reading keeps name, age, gross income, class without the reading and the income readings the alternative rests on), tips (now NOT qualified), rental_qbi, other_health_insurance_premiums, over_the_counter (213(b) comment fixed), educational_assistance, financial_assistance, qualified_bdc_income, farm_income, partnership_se, overtime_premium, mortgage_date, active_participant, deferrals_wages, savers_credit (testing period + full-time student), educator, hsa, self_employed_health_insurance, roth_catch_up, surviving_spouse, member_expenses. Unit.itemized_notes: readings that bear only on itemized deductions (other premiums, OTC, mortgage date when balances exceed the debt limit, an unclaimed member's medical); runners add them only where the model itemizes.
- DONE unit.py fixes: traditional + Roth 401(k) limited to wages together, in proportion (F3/P2-F5); surviving spouse on any claimed non-partner dependent (F4; NOT extended to members left out by the gross-income test: 2(a)(1)(B)(ii) requires a 151 deduction for the dependent, saved text lii-26-2.verify-unit-statute.txt); medical of every listed member (F5); 72(t) note at age <= 59 (F12/F15); own_gross_income: gains without losses, wages net of own traditional deferral, taxable SS by 86 for an unmarried filer (F13); member-income note lists every stated income item; members' SE earnings get a self_employment note as well as payroll (verify-map-taxsim F8); the reading a member's gross-income test rests on is attached (F1 addendum). Board check: filing status still 58 single / 35 joint / 7 HoH, equal to the board's own field on all 100 both years; is_disabled reading moves 064 dependent1 (27, QR -> QC) and 067 dependent1 (23, left out -> QC); 093 dependent1 (wages 45,000) stays left out with a note.
- DONE statute.py: citations Rev. Proc. 2025-32 sec. 4.29 (student loan), 4.23 / Rev. Proc. 2024-40 sec. 2.24 ($5,300/$5,200, in unit.py); 219(g)(2)(C) docstring now states the statute's rounding-down of the reduction and why the code's round-up equals it; added qbi_threshold (199A(e)(2): 2026 201,750/403,500/separate 201,775, rp-25-32 sec. 4.26; 2025 197,300/394,600, rp-24-40 sec. 2.27).
- DONE map_taxcalc.py (VERSION 2026-11-10.2): capital gain distributions join p23250 when the unit has any Schedule D item (short- or long-term gain/loss), else e01100 (P2-F6; Schedule D instructions i1040sd-2025.txt:118-121 "Enter on Schedule D, line 13, the total capital gain distributions"); tip_income 0 (reading tips); e20400 note (P3-F7); docstring narrowed (P3-F11); shared SALT note moved to itemizer_notes(); saver's credit computed note carries the savers_credit reading.
- DONE map_taxsim.py (VERSION 2026-11-10.2): gross wages + deferrals in negative nonprop (F5); records A/B on 2026 counts path (needs_eitc_record: min(3, EITC children) != min(3, children under 17), which covers both brief cases; F7); 2025 ages path sends any qualifying child aged >= 17 as 18 (F6, and F9 for the disabled-adult reading); rent and estate to intrec either sign (F18, reading 2) with a note when a net loss offsets interest in the EITC test; scorp-loss note text (F10 side effects); other-income note says a net loss goes to nonprop (F19); tips note dropped (reading 3: nothing to express); W-2/property note and shared SALT/itemized readings moved to final_notes() (F13, F20); min-QBID note counts active SE boxes only (F23); adjustments note kept and reworded (trace-taxsim-b map error 1 kept as a noted limit). SALT cap left as shipped (reading 7).
- DONE scripts: run_taxsim.py (record B run; record A is the payroll run, SE-zeroed run splits tfica; final_notes; " || " joins; docstring F19/F12), run_taxcalc.py (itemizer notes only where final out_c04470 > 0; " || "; docstring), build_answers.py tagged() splits/joins on " || " (F17), make_dossiers.py splits on " || ".
- Trial rerun to scratch (scratchpad/fixmaps/{tc,ts}_{2026,2025}.csv), q_* lines vs committed: TC 2026 and 2025 only 067 line 1 -500.00 (6,116.24 -> 5,616.24; 6,219.24 -> 5,719.24: ODC for dependent1, is_disabled reading); TAXSIM 2026 064 line 1 +1,700.00 (4,409.37 -> 6,109.37: record A dep18 = 1 child under 17, so the 18-year-old gets $500 not $2,200; F7) and 067 -500.00; TAXSIM 2025 067 -500.00. Nothing else moves on any line. Input changes as intended: TAXSIM pwages/swages gross on 20 households with deferrals (nonprop carries them); out_addmed of the income-tax record now on gross wages for 005, 049, 052 (payroll line unchanged); 088 TC tip_income 9,600 -> 0 (tax still 0; TC now itemizes in 2025); 004 e07240 1,000 -> 0 (Roth limited to wages). Dropped columns out_tfica_gross_wages/out_addmed_gross_wages (record A is the gross-wage run; out_tfica/out_addmed hold them).
- W-2 note condition tightened to positive business income: 120 (farm rent loss, 2025 taxable income 197,418.67 > 197,300) would otherwise get it with qbid 0.
- DONE make_fact_map.py rows (is_disabled, tip_income, rental/estate, 401(k) traditional/Roth, non_sch_d gains, other premiums, OTC, educational/financial assistance, BDC, farm_income, medical rows); maps/board_facts.csv regenerated (15 rows changed). Counts printed now: 97 stated inputs; 56 reach a federal line; TC field 60, TAXSIM field 44 (is_disabled now has both).
- 23:04Z tests in progress: tests/test_households.py and tests/test_unit.py written, not yet run; checking the harness's reported auto-commit next.

## Tests (done)

New: `tests/test_households.py` (4), `tests/test_unit.py` (18), `tests/test_maps.py` (18), `tests/test_differential_pe.py` (7); `tests/test_statute.py` extended to 15 (2025 published amounts from Notice 2024-80 and Rev. Proc. 2024-40, the 219(g)(7) range 242,000-252,000, `qbi_threshold`, `scale_to_limit` shares, the exact 163(h)(3)(F) formula, and the reviewer's literal Decimal reading of 219(g) as a Hypothesis differential plus a $3.37 grid over every phase-out range). Run with the brief's command: **68 passed in 11.1 s** (before the reruns; rerun after them below).

Differential against PolicyEngine 2.60.0's own 2026 run (households from the dossiers' `stated_facts`): filing status equal on all 100; children under 17 equal on all 100; traditional IRA equal per filer on all 100; student loan deduction (Tax-Calculator `in_e03210`) equal on all 100. Known differences, each pinned by the test so a new one or a vanished one fails it:
- dependents: 093 (ours 0, PE 1): the member is stated disabled but earns $45,000, so not read as permanently and totally disabled.
- EITC children: 064 (ours 3, PE 2) and 067 (ours 1, PE 0): a member stated disabled with no earnings (27 and 23), an EITC child under the is_disabled reading; PE claims each as a dependent but `is_eitc_qualifying_child` is 0 in its run.
- traditional 401(k) per filer: heads of 003, 004, 073, 085, 089 state deferrals with no wages; the map limits deferrals to wages, PE 2.60.0 does not. Correction to my earlier baseline: 064 differs only at the unit level, because PE's tax-unit total adds a dependent's own deferral (dependent1, 385.90); per filer it agrees.
- 23:09Z runs.csv versions bumped; starting the four reruns
- 23:11Z reruns done (4 runs, 0 TAXSIM rejections); answers, three agreement tables and 100 dossiers rebuilt; tests rerun after the rebuild

## Results after the rerun (results/, uncommitted)

Agreement within $1 (all_agree / all_differ / two_agree:policyengine / two_agree:taxsim). Lines 2-4 equal before and after except as shown.

| Table, line 1 (tax before refundable credits) | Before | After |
|---|---|---|
| 2026 key (pb-reference-2.60.0, fallback pe-2.60.0-board-2026) | 72 / 2 / 10 / 16 | 73 / 2 / 9 / 16 |
| 2026 rerun (pe-2.60.0-board-2026) | 76 / 1 / 6 / 17 | 77 / 1 / 5 / 17 |
| 2025 (pe-2.60.0-board-2025) | 83 / - / 7 / 10 | 84 / - / 6 / 10 |

Line 2 (refundable credits) 96 all_agree + 4 two_agree:taxsim in all three tables, before and after; self-employment tax and employee payroll tax 100 all_agree in all three, before and after.

Every answer in results/answers.csv (5,400 rows) compared with the copy taken at the start: five values moved, nothing else.
- scenario_067 line 1, two_agree:policyengine -> all_agree in all three tables. Tax-Calculator and TAXSIM 2026 6,116.24 -> 5,616.24, 2025 6,219.24 -> 5,719.24 (PolicyEngine 5,616.24 / 5,719.24). Moved by reading 1 (is_disabled): dependent1 (23, stated disabled, no earnings) is now a qualifying child, so the $500 credit of 24(h)(4).
- scenario_064 line 1, TAXSIM 2026 4,409.37 -> 6,109.37; class stays two_agree:taxsim (key and rerun). Moved by the 2026 records A/B fix (verify-map-taxsim F7, trace-taxsim-a map error 1): record A sends dep18 = 1 (the child under 17), so the 18-year-old gets $500, not $2,200. The old near-agreement (-32.09) was that -1,700 offsetting the +1,667.91 of TAXSIM's missing overtime deduction (both in trace-taxsim-a's table); now only the overtime gap is left, 1,667.91 exactly.
- Record B ran for 064 and 067 only; v25 is 0 in both records for both, so no refundable credit moved.

Note counts: shared SALT note on 8 / 10 units (Tax-Calculator 2026 / 2025, its itemizers) and 9 / 11 (TAXSIM, v17 > 0); other-premiums reading 5 / 6 and 6 / 6; rental_qbi on 6 units; is_disabled reading on 3 (064, 067 moved; 093 not, earnings); the W-2 / property limit note fires on none. TAXSIM: 0 records rejected.

## Lines still not all_agree (cause from the tracers' summary tables; "touched" = what my change did on that line)

K = 2026 key (27 line-1 + 4 line-2), R = 2026 rerun (23 + 4), 25 = 2025 (16 + 4). L1 = tax before refundable credits, L2 = refundable credits. Class two_agree:taxsim unless stated.
- 000 L1 [K R 25]: TAXSIM has no tax-exempt-interest input, so Social Security provisional income lacks 5,578.41 (-568.99; trace-taxsim-a). Untouched.
- 002 L1 [K] two_agree:policyengine: key frozen at 0 (1.755.4 left $24,000 disability benefits untaxed); TC = TAXSIM = engine tax them (1,890.30; trace-pe-a). Untouched.
- 005 L1 [K all_differ; R]: key's frozen IRA deduction despite 219(g) (692.43) and the state refund left out (1,327.26); TAXSIM lacks 170(p) (342.33; trace-pe-a). Notes only.
- 020 L1 [K all_differ; R all_differ; 25 two_agree:policyengine]: PE deducts alimony paid by its default divorce year (1,998.09); TAXSIM lacks 170(p) (68.60, 2026); key: 1.755.4 sales-tax table (278.02; trace-pe-a). Notes only.
- 022 L1 [K R 25] two_agree:policyengine: PE counts $4,550 rent as QBI (200.20; trace-pe-a). Touched: the rental_qbi reading (lead reading 2) is now named on the unit with PE's default; no value change by design.
- 026 L2 [K R 25]: TAXSIM has no overtime deduction, so less tax for the child credit to absorb and less refundable credit (-929.55; trace-taxsim-a). Notes only.
- 037 L1 [K R 25]: no overtime deduction (+1,155.48). Notes only.
- 046 L1 [K R 25]: no overtime deduction (+1,780.65). Notes only.
- 049 L1 [K R 25]: no overtime deduction (+5,500.00; 2025 +5,559.54) and no 2026 170(p) (+127.55). Notes only.
- 052 L1 [K] two_agree:policyengine: key's frozen IRA deduction despite 219(g) (13.85; trace-pe-a). Notes only.
- 055 L1 [K R]: no 2026 170(p) (+240.00). Notes only.
- 064 L1 [K R 25]: no overtime deduction (+1,667.91). Touched: 2026 value moved (above); is_disabled reading named.
- 070 L1 [K R 25]: no saver's credit input (+192.40). Notes only (savers_credit reading).
- 076 L1 [K R 25] two_agree:policyengine: PE counts $4,000 rent as QBI (192.00; trace-pe-b). Touched: rental_qbi reading named; no value change.
- 078 L1 [K R] (not scored): TAXSIM's 2026 SALT cap is $40,000, not $40,400 (+96.00). Untouched (reading 7: build as shipped).
- 082 L1 [K R]: no 2026 170(p) (+154.00). Notes only.
- 089 L1 [K R 25]: no overtime deduction (+416.09; trace-taxsim-b). Notes only (deferrals_wages reading: the head states deferrals with no wages).
- 091 L1 [K R 25]: overtime 75.35 + saver's credit 120.00 (+195.35). Notes only.
- 093 L1 [K R 25] two_agree:policyengine (not scored): PE pays the $500 credit for dependent1 (27, stated disabled, $45,000 wages); the map claims no dependent (trace-pe-b). Touched: the is_disabled note now says why (earnings); no value change by reading 1.
- 099 L1 [K R]: TAXSIM 170(p) 440.00 + pre-2026 child care credit rate 720.00 (+1,160.01; trace-taxsim-b). Notes only.
- 100 L2 [K R 25]: the map's IRA deduction in negative `nonprop` cuts TAXSIM's EITC earned income (-72.13). Kept as a noted TAXSIM limit (brief); note reworded only.
- 107 L1 [K] two_agree:policyengine (not scored): key frozen at 0 (disability benefits); engine and maps tax them (211.23; trace-pe-b). Untouched.
- 109 L2 [K R 25]: TAXSIM's 3+-child refundable credit alternative takes the whole SE tax (+431.77). Untouched.
- 110 L1 [K R]: no 2026 170(p) (+92.99). Notes only (rental_qbi reading for its estate income).
- 114 L1 [K R 25] two_agree:policyengine (not scored): PE adds a modeled Medicare Part B premium to itemized medical (535.66; 2025 488.40; trace-pe-b). Touched: the medicare_part_b reading is now attached to this unit (absent before); no value change.
- 117 L1 [K R 25] (not scored): overtime (5,602.67) + 170(p) vs itemizing (88.74); 2025 overtime 5,669.02. Notes only.
- 119 L2 [K R 25]: saver's credit 200 + child care credit rate 234 + TAXSIM's refundable child credit ignoring the tax its child care credit used 312 (-745.99; 2025 -511.99). Notes only.
- 120 L1 [K; R and 25 two_agree:policyengine] (not scored): R/25: PE 2.60.0 leaves the farm rent loss out of net investment income (92.97, fixed in 2.116.15); K: key frozen 308.39 below TC = TAXSIM (trace-pe-b). Notes only; the W-2 note correctly stays off (loss).
- 121 L1 [K] two_agree:policyengine (not scored): key frozen at 0 (disability benefits) (875.34). Untouched.
- 122 L1 [K R 25]: blindness 246.00 + 170(p) 120.00 - tax-exempt interest 128.49 (+237.51; 2025 +52.69). Notes only.
- 123 L1 [K R] (not scored): no 2026 170(p) (+240.00). Untouched.

## Tests after the rebuild

`uv run --no-project --no-cache --python 3.12 --with pytest --with hypothesis pytest tests -q -p no:cacheprovider`: **68 passed in 11.84 s** (agreement 6, households 4, unit 18, maps 18, statute 15, differential 7; no skips: the student-loan differential reads the new Tax-Calculator 2026 run).

## Brief items

Done as written: readings 1-7; every unit.py/statute.py fix; Tax-Calculator capital gain distributions, e20400 note, HSA (the hsa reading, both maps), docstring, shared SALT note only on final itemizers; TAXSIM gross wages + deferrals in negative nonprop with one record for both taxes and the SE-zeroed run to split tfica; 2025 ages (17 -> 18); SALT note only where v17 > 0; W-2 note; minimum-deduction note (F23); adjustments kept in nonprop with the note; " || " everywhere; tests; four reruns; answers, three tables, dossiers (they now carry `itemized_notes` and `disabled_reading`), fact map; VERSION 2026-11-10.2 in unit.py, map_taxcalc.py, map_taxsim.py and runs.csv.
Done differently:
- Records A/B trigger is min(3, EITC children) != min(3, children under 17): exactly where record A's EITC count is wrong given the build counts at most three (P3.3, P3.6). It covers the brief's first case; its second (EITC children above three) needs no record B when three or more are under 17, since record A's count already caps at three. Record B also sets dep17 = min(under 17, dep18) and dep13 = min(under 13, dep17), which the build requires.
- Surviving spouse not extended to a member left out by the gross-income test: 2(a)(1)(B)(ii) requires a 151 deduction for the dependent.
- The W-2 note also requires positive business income (else 120 in 2025 gets it on a loss with qbid 0).
- The mortgage_date reading attaches only where balances exceed the debt limit (the only case where the date can move the answer), and only for units the model itemizes.
Not done: `keycheck/taxsim.py` unchanged (no item needed it); README not edited (outside the brief's file list; see below).

## Found that the reviewers missed or got wrong

- verify-map-taxsim F1's premise is wrong: 56 persons state both premium fields, 5 only the premiums without Part B, none only the other field; reading 4 drops nothing stated alone.
- The W-2 note as F20 states it would fire on 120 (2025) on a loss with qbid 0; tightened.
- PolicyEngine's unit-level `traditional_401k_contributions` adds a dependent's own deferral (064: dependent1 385.90), so a unit-level comparison (the reviewer's diff_pe.py) lists 064 falsely; per filer it agrees. My earlier baseline also put 064 under the wage limit; corrected.
- In PE 2.60.0's own run, 064's and 067's disabled members are dependents but not EITC qualifying children (`is_eitc_qualifying_child` 0); I did not read why in PE's code. It moves no board line (v25 0).
- Side effect not reviewed: with gross wages in TAXSIM, its child care credit's earned-income limit (21(d)) now sees wages before deferrals. No line moved on the board; I did not read 21(d) this run, so I left no note.
- README is stale against the new tables: README.md:46 (72 / 10 / 16 / 2 -> 73 / 9 / 16 / 2), :53-54 (76, 6, 17, 1 -> 77, 5, 17, 1), :62 (83 / 7 / 10 -> 84 / 6 / 10), and :79 "the nine households that itemize" (shared SALT note now on 8 TC / 9 TAXSIM units in 2026, 10 / 11 in 2025).
- Not in the brief, not done: verify-map-taxsim F10 (netting psemp with pprofinc for SECA), verify-map-taxcalc F13 (k1bx14p guard), a 2025 HSA limit.

## Commit on the branch that I did not make

HEAD moved from bbd48c1 to b939820 "fixup! Record PolicyEngine experiments on five board households and the tracers' TAXSIM probes" (git commit, author and committer Max Ghenis, 2026-11-10 18:01:36 -0500) while I worked. My transcript has no commit call. It holds my in-progress edits to 15 files (keycheck/*.py, scripts, maps/board_facts.csv, the probe, tests/test_households.py, tests/test_unit.py). Everything after it (tests/test_maps.py, tests/test_differential_pe.py, tests/test_statute.py, results/) is uncommitted in the working tree. Nothing pushed. Review the whole change with `git diff bbd48c1`.

STATUS: complete
