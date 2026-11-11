# trace-taxsim-a — Claude Opus 5.5 (claude-opus-5-5) — 2026-11-10

Scratch tools (mine, not in REPO): `<scratch>/tsa/ts.py` reruns TAXSIM cd2026110117 on a dossier's final-pass `in_*` record with changed inputs; `<scratch>/tsa/tc.py` does the same for Tax-Calculator 6.9.0 (same policy settings as `scripts/run_taxcalc.py:80-88`). `<scratch>` = `SCRATCH`.

## scenario_000 (TX, single, head 77, surviving spouse with no child; SS 26,096, pensions/IRA 31,849.41, taxable interest 45, tax-exempt interest 5,578.41)

**Rows.** Line 1 (`federal_income_tax_before_refundable_credits`) in all three tables: 2026 key and rerun PE 2,906.45 = TC 2,906.45, TAXSIM 2,337.46 (diff 568.99); 2025 PE 2,963.95 = TC 2,963.95, TAXSIM 2,394.96 (diff 568.99). Lines 2-4 agree (all 0).

**Reconciliation (2026).** AGI: PE 50,437.11 = TC c00100 50,437.11; TAXSIM v10 45,695.46; gap 4,741.65, all in taxable Social Security (PE `tax_unit_taxable_social_security` 18,542.70 = TC c02500 18,542.70; TAXSIM v12 13,801.05). 4,741.65 = 85% x 5,578.41 tax-exempt interest exactly. Provisional income with it: 31,894.41 + 5,578.41 + 13,048 = 50,520.82 (TC ymod 50,520.82); taxable SS = 85% x (50,520.82 - 34,000) + 4,500 = 18,542.70. Without it: 44,942.41 -> 85% x 10,942.41 + 4,500 = 13,801.05 = TAXSIM v12. Deductions identical in all three (standard 18,150 = 16,100 + 2,050 aged; senior 6,000; itemized 17,587.20 < standard). Taxable income PE 26,287.11, TAXSIM v18 21,545.46; both in the 12% bracket: 12% x 4,741.65 = 569.00 vs observed 568.99 (rounding). Unexplained: $0.01. 2025: same 4,741.65 x 12% = 568.99 (TC/PE TI 26,687.11, TAXSIM 21,945.46).

**Confirmation.** TC with e00400 (tax-exempt interest) set to 0: c02500 13,801.05, c00100 45,695.46, line 1 2,337.46 (2026) and 2,394.96 (2025) = TAXSIM to the cent. TAXSIM with the law's taxable SS entered directly (gssi 0, pensions 31,849.41 + 18,542.70 = 50,392.11): v10 50,437.11, v18 26,287.11, fiitax 2,906.45 = PE and TC.

**Law.** 26 U.S.C. 86(b)(2)(B): modified AGI is "increased by the amount of interest received or accrued by the taxpayer during the taxable year which is exempt from tax" (`sources/uscode/lii-26-86.txt:96-100`, saved this run); base and adjusted base amounts $25,000 / $34,000 single (`:102-114`). The map names the gap: `keycheck/map_taxsim.py:144-145` (no TAXSIM input for tax-exempt interest); the taxsim reader found the same (`understand-inputs/taxsim.md:166, 192`, P15.5).

**Verdict.** (c) the map could not express a stated fact in TAXSIM: `tax_exempt_interest_income` 5,578.41 has no TAXSIM input. PE (2.60.0 and 2.116.15 both give 2,906.45) and TC follow 86(b)(2)(B); TAXSIM as mapped does not see the fact. A possible map workaround (description only; it makes the map compute what TAXSIM should): compute 86 taxable SS in the map and send it as `pensions` with `gssi` 0; that reproduces 2,906.45 here.

cause: tax-exempt interest has no TAXSIM input, so it is left out of SS provisional income (-4,741.65 taxable SS x 12% = -568.99); right: PE and TC.

## scenario_026 (NC, joint 48/45, three children 11, 11, 9; spouse wages 85,208.82 incl. FLSA overtime premium 7,746.26; 401(k) 2,778.48; IRA 129.83)

**Rows.** Line 2 (`federal_refundable_credits`) in all three tables: 2026 key and rerun PE 2,013.49 = TC 2,013.49, TAXSIM 1,083.94 (diff 929.55); 2025 PE 1,910.49 = TC 1,910.49, TAXSIM 980.94 (diff 929.55). Line 1 agrees at 0 in all (CTC absorbs the whole tax); lines 3-4 agree.

**Reconciliation (2026).** AGI agrees: PE 82,300.52, TC 82,300.51, TAXSIM v10 82,300.51. Taxable income PE 42,354.26 = TC 42,354.25; TAXSIM v18 50,100.51. Gap 7,746.25 = the overtime deduction (PE `overtime_income_deduction` 7,746.26 = TC 7,746.26; TAXSIM none). Tax before credits PE/TC 4,586.51, TAXSIM v28 5,516.06: 12% x 7,746.26 = 929.55. CTC 6,600 (3 x 2,200) in all; the nonrefundable part takes the whole tax, so the refundable part = 6,600 - tax (below the 3 x 1,700 cap and 15% x (82,430.34 - 2,500) = 11,989.55): PE 6,600 - 4,586.51 = 2,013.49; TAXSIM 6,600 - 5,516.06 = 1,083.94 (v23 = actc). Diff 929.55, all from the deduction; unexplained 0. 2025: TI 43,054.25 vs 50,800.51, tax 4,689.51 vs 5,619.06, same 929.55.

**Confirmation.** TC with `overtime_income` 0: c04800 50,100.51, c05800 5,516.06, refund 1,083.94 (2026) / 980.94 (2025) = TAXSIM. TAXSIM with the deduction forced in through `nonprop` -7,876.09 (= -129.83 IRA - 7,746.26; AGI moves too, which changes nothing else here: no EITC at this income, CTC phase-out far off): v18 42,354.25, v28 4,586.51, actc 2,013.49 (2026) / 1,910.49 (2025) = PE and TC.

**Law.** 26 U.S.C. 225(a), (b)(1): a deduction equal to qualified overtime compensation, up to $25,000 joint, phased out above $300,000 MAGI joint; 225(c)(1) defines it as FLSA section 7 overtime pay in excess of the regular rate; 225(e) joint return required for married; 225(g) ends after 2028 (`sources/uscode/usc26-s225.txt:31-52`); allowed to non-itemizers by 63(b)(6) (`usc26-s63.txt:40`); effective for years after 2024 (`usc26-s63.txt:235`). Refundable CTC = credit not used against tax, under 26 U.S.C. 24(d)/(h) caps.

**Verdict.** (c) the map could not express a stated fact in TAXSIM: `fsla_overtime_premium` has no TAXSIM input (probe P1.2; `keycheck/map_taxsim.py:140-141` lists it as unexpressed). The 225(d) SSN requirement is not stated by the board; PE and TC both allow the deduction. PE 2.60.0 and 2.116.15 agree (2,013.49).

cause: TAXSIM has no qualified-overtime deduction (7,746.26 x 12% = 929.55 more tax, so 929.55 less refundable CTC); right: PE and TC.

## scenario_037 (NC, single 44, wages 41,943.38 incl. FLSA overtime premium 9,629.03; 401(k) 385.90; IRA 18.03; no dependents)

**Rows.** Line 1 in all three tables: 2026 key and rerun PE 1,649.25 = TC 1,649.25, TAXSIM 2,804.73 (diff -1,155.48); 2025 PE 1,700.75 = TC 1,700.75, TAXSIM 2,856.23 (diff -1,155.48). Lines 2-4 agree.

**Reconciliation (2026).** AGI agrees (PE 41,539.45, TC 41,539.45, TAXSIM v10 41,539.45). Taxable income PE 15,810.43 = TC 15,810.43; TAXSIM v18 25,439.45; gap 9,629.02 = PE/TC `overtime_income_deduction` 9,629.03 (under the $12,500 single cap, MAGI far under $150,000). Tax: PE 1,240 + 12% x 3,410.43 = 1,649.25; TAXSIM 1,240 + 12% x 13,039.45 = 2,804.73; 12% x 9,629.03 = 1,155.48 = the whole gap; unexplained 0. 2025 identical (TI 16,160.43 vs 25,789.45).

**Confirmation.** TC `overtime_income` 0: c04800 25,439.45, line 1 2,804.73 (2026) / 2,856.23 (2025) = TAXSIM. TAXSIM with the deduction forced through `nonprop` -9,647.06 (IRA 18.03 + overtime; no EITC or other AGI-dependent item here): v18 15,810.42, fiitax 1,649.25 (2026) / 1,700.75 (2025) = PE and TC.

**Law.** 26 U.S.C. 225(a)-(c) (`sources/uscode/usc26-s225.txt:31-43`), 63(b)(6) (`usc26-s63.txt:40`), as for scenario_026.

**Verdict.** (c) map could not express `fsla_overtime_premium` in TAXSIM (no input, probe P1.2; `keycheck/map_taxsim.py:140-141`). PE 2.60.0 = 2.116.15.

cause: TAXSIM has no qualified-overtime deduction (9,629.03 x 12% = 1,155.48); right: PE and TC.

## scenario_046 (OK, joint 39/38, children 10 and 9; head wages 92,000 incl. FLSA overtime premium 14,838.71; mortgage interest 12,415; property tax 8,464.50)

**Rows.** Line 1 in all three tables: 2026 key and rerun PE 499.71 = TC 499.71, TAXSIM 2,280.36 (diff -1,780.65); 2025 PE 602.71 = TC 602.71, TAXSIM 2,383.36 (diff -1,780.65). Lines 2-4 agree.

**Reconciliation (2026).** AGI agrees at 92,003.00 in all three. All three take the standard deduction 32,200 (PE itemized 29,948.87 = SALT 12,104.09 + interest 12,415 + medical 5,429.77; TAXSIM v17 0 with proptax 12,104.09 + mortgage 17,844.78 = the same 29,948.87). Taxable income PE 44,964.29 = TC 44,964.29; TAXSIM v18 59,803.00; gap 14,838.71 = PE/TC `overtime_income_deduction` (under the $25,000 joint cap). Tax before credits: PE 2,480 + 12% x 20,164.29 = 4,899.71; TAXSIM 2,480 + 12% x 35,003 = 6,680.36; 12% x 14,838.71 = 1,780.65 = the whole gap. CTC 4,400 nonrefundable in all; line 1 = 499.71 vs 2,280.36. Unexplained 0. 2025 identical (TI 45,664.29 vs 60,503).

**Confirmation.** TC `overtime_income` 0: c04800 59,803, line 1 2,280.36 (2026) / 2,383.36 (2025) = TAXSIM. TAXSIM `nonprop` -14,838.71 (AGI falls too; still standard deduction, no EITC at 77k with two children, no CTC phase-out): v18 44,964.29, fiitax 499.71 (2026) / 602.71 (2025) = PE and TC.

**Law.** 26 U.S.C. 225 (`sources/uscode/usc26-s225.txt:31-52`), 63(b)(6) (`usc26-s63.txt:40`). The head's AOTC student flags are stated but no qualified tuition is, so no AOTC in any model (PE `income_tax_non_refundable_credits` 4,400 = CTC only); not a factor.

**Verdict.** (c) map could not express `fsla_overtime_premium` in TAXSIM. PE 2.60.0 = 2.116.15.

cause: TAXSIM has no qualified-overtime deduction (14,838.71 x 12% = 1,780.65); right: PE and TC.

## scenario_049 (NH, joint 53/52, no dependents; spouse wages 253,000 incl. FLSA overtime premium 44,647.06; 401(k) 15,436; interest 3,501; qualified dividends 6,208; cash gifts 579.76, non-cash 2,758; property tax 20,655; mortgage interest 2,743 on a 1,000,000 balance)

**Rows.** Line 1 in all three tables: 2026 key and rerun PE 30,702.59 = TC 30,702.59, TAXSIM 36,330.14 (diff -5,627.55); 2025 PE 31,388.14 = TC 31,388.14, TAXSIM 36,947.68 (diff -5,559.54). Lines 2-4 agree.

**Reconciliation (2026).** AGI agrees at 247,385 in all three. All take the standard deduction (itemized 24,813.09 < 32,200 in PE; TAXSIM proptax 20,655 + mortgage 4,158.09 = 24,813.09, v17 0). Two below-the-line deductions TAXSIM lacks:
- overtime: PE/TC `overtime_income_deduction` 25,000 (44,647.06 capped at the $25,000 joint limit; MAGI 247,385 < $300,000, no phase-out);
- 2026 non-itemizer charitable deduction: PE `charitable_deduction_for_non_itemizers` 579.76 (cash gifts, under $2,000 joint, no 0.5% floor); TC carries it inside `standard` 32,779.76 = 32,200 + 579.76.
Taxable income PE 189,605.23 = TC 189,605.24; TAXSIM v18 215,185.00; gap 25,579.77. Ordinary part of TI (TI less 6,208 qualified dividends) stays inside the 22% bracket (100,800-211,400 joint, 2026) in both: PE 183,397.23, TAXSIM 208,977. So the gap costs 22% x 25,000 = 5,500.00 (overtime) + 22% x 579.76 = 127.55 (charity) = 5,627.55 = observed; unexplained 0. Check: PE 2,480 + 9,120 + 22% x 82,597.23 + 15% x 6,208 = 30,702.59; TAXSIM 2,480 + 9,120 + 22% x 108,177 + 931.20 = 36,330.14.
2025 (no 170(p) deduction in 2025; TC `standard` 31,500): TI 190,885 vs 215,885, gap 25,000 (overtime only). TAXSIM's ordinary part 209,677 crosses the 2025 24% bracket start (206,700) by 2,977: 22% x 22,023 + 24% x 2,977 = 4,845.06 + 714.48 = 5,559.54 = observed; unexplained 0.

**Confirmation.** TC 2026: `overtime_income` 0 -> line 1 36,202.59 (TI 214,605.24; the 579.76 charity remains); plus `e19800` (cash gifts) 0 -> 36,330.14 = TAXSIM; `e19800` 0 alone -> 30,830.14 (= PE + 127.55). TC 2025 `overtime_income` 0 -> 36,947.68 = TAXSIM. TAXSIM 2026 `nonprop` -25,000 -> 30,830.14; `nonprop` -25,579.76 -> 30,702.59 = PE and TC; 2025 `nonprop` -25,000 -> 31,388.14 = PE and TC. (Lowering AGI in TAXSIM moves nothing else here: standard deduction either way, AGI below the $250,000 NIIT threshold already.)

**Law.** Overtime: 26 U.S.C. 225(a), (b)(1) $25,000 joint cap, (b)(2) phase-out above $300,000 (`sources/uscode/usc26-s225.txt:31-38`). Charity: 26 U.S.C. 170(p) as amended by Pub. L. 119-21: a non-itemizer deducts cash gifts up to $2,000 joint, "determined without regard to subsections (b)(1)(G)(ii), (b)(1)(I), and (d)(1)" (so no 0.5% floor) (`sources/uscode/usc26-170.txt:926`; amendment `:977-978`). The recipient's type (170(b)(1)(A), not a 509(a)(3) organization or donor-advised fund, `:926-930`) is not stated; all three models treat the gift as qualifying.

**Verdict.** (c) twice: TAXSIM has no input for `fsla_overtime_premium` (-5,500.00 in 2026; -5,559.54 in 2025) and no 2026 non-itemizer charitable deduction (-127.55; probe P9.5; `keycheck/map_taxsim.py:162-163`). PE 2.60.0 = 2.116.15 (30,702.59).

cause: TAXSIM has no overtime deduction (25,000 at 22% = 5,500.00) and no 2026 170(p) cash-gift deduction (579.76 at 22% = 127.55); right: PE and TC.

## scenario_055 (FL, single 70; wages 83,635.15, pension 67,760, SS 5,742; cash gifts 15,647.06; property tax 837)

**Rows.** Line 1 in the two 2026 tables only: PE 25,238.58 = TC 25,238.58, TAXSIM 25,478.58 (diff -240.00). 2025: all agree at 25,823.58 (no 170(p) deduction in 2025). Lines 2-4 agree.

**Reconciliation (2026).** AGI agrees (PE 156,275.86; TC/TAXSIM 156,275.85); taxable SS 4,880.70 (85% cap) in all. All take the standard deduction 18,150 (16,100 + 2,050 aged): PE itemized 16,943.48 = SALT 2,077.80 + charity 14,865.68 (15,647.06 less 0.5% x AGI 781.38); TAXSIM proptax 2,077.80 + mortgage 14,865.68 = the same, v17 0. Senior deduction 1,123.45 = 6,000 - 6% x (156,275.86 - 75,000) in PE and TC; TAXSIM's TI implies the same (see below). PE adds `charitable_deduction_for_non_itemizers` 1,000 (cash gifts capped at $1,000 single); TC carries it in `standard` 19,150. TI PE 136,002.41 = TC 136,002.40; TAXSIM v18 137,002.40 = 156,275.85 - 18,150 - 1,123.45; gap 1,000 in the 24% bracket (105,700-201,775 single 2026): 240.00 = observed; unexplained 0.

**Confirmation.** TC `e19800` (cash gifts) 0: c04800 137,002.40, line 1 25,478.58 = TAXSIM. TAXSIM `nonprop` -1,000 (no below-the-line input exists, so this lowers AGI): v18 135,942.40, fiitax 25,224.18 = PE - 14.40, the 14.40 being 24% x 60 more senior deduction (6% x the 1,000 lower AGI); with that accounted for, the 1,000 deduction alone gives PE's 25,238.58.

**Law.** 26 U.S.C. 170(p) as amended by Pub. L. 119-21: non-itemizer deducts cash gifts up to $1,000 single, without the (b)(1)(I) 0.5% floor (`sources/uscode/usc26-170.txt:926`, `:977-978`). 26 U.S.C. 151(d)(5)(C) senior deduction and phase-out (`usc26-151.txt:101-111`), equal in all three. Recipient-organization type unstated (all models treat it as qualifying).

**Verdict.** (c) the map could not express the 2026 non-itemizer charitable deduction in TAXSIM (probe P9.5: the build has none; `keycheck/map_taxsim.py:162-163`). PE 2.60.0 = 2.116.15 (25,238.58).

cause: TAXSIM has no 2026 170(p) cash-gift deduction (1,000 x 24% = 240.00); right: PE and TC.

## scenario_064 (WI, joint 48/47; dependents 27 (disabled, no income), 18, 12; head wages 97,295 incl. FLSA overtime premium 13,899.29, 401(k) 2,315.40, IRA 108.19; partnership income 19,350 of which partner SE earnings 14,000; farm -16,800; LTCG -18,235.41; 401(k) distribution 20,000; repealed DPAD 1,795.50 stated)

**Rows.** Line 1: 2026 key and rerun PE 4,441.46, TC 4,441.45, TAXSIM 4,409.37 (diff +32.09); 2025 PE 4,544.46, TC 4,544.45, TAXSIM 6,212.37 (diff -1,667.91). Lines 2-4 agree (EITC 0 at this AGI; no SE tax on net SE earnings of -2,800). The dossier's three board exclusion records are for `ssi` and two Medicaid outputs, not these lines.

**Reconciliation.** AGI agrees at 114,421.41 in all three (94,979.60 wages net of 401(k) + 20,000 + 19,350 - 16,800 - 3,000 capital-loss limit - 108.19 IRA; DPAD left out by all three: PE's 19,908.19 `above_the_line_deductions` = 16,800 + 3,000 + 108.19, TC zeroes `e03240`, the TAXSIM map drops it). QBID 510 in all three (20% x (19,350 - 16,800)). Standard deduction 32,200 (2026) / 31,500 (2025) in all.
- Cause 1, overtime: PE/TC deduct 13,899.29 (`overtime_income_deduction`); TAXSIM cannot. TI PE 67,812.12 = TC; TAXSIM v18 81,711.41; 12% x 13,899.29 = 1,667.91 more TAXSIM tax (v28 9,309.37 vs 7,641.46). 2025: TI 68,512.12 vs 82,411.41, same 1,667.91.
- Cause 2, 2026 only, the 18-year-old's credit: under law the 18-year-old (and the 27-year-old) get the $500 credit for other dependents, the 12-year-old the $2,200 CTC: 3,200 (PE `ctc` 3,200 with `ctc_qualifying_children` 1; TC c07220 2,200 + odc 1,000). TAXSIM 2026 runs the counts path with dep18 2 (EITC children 18 and 12; `keycheck/map_taxsim.py:116-119`), and the build gives the $2,200 credit to every dep18 child (probe P3.3): v22 4,900 = 2 x 2,200 + 500, i.e. +1,700. 2025 runs the ages path (age1 12, age2 18, age3 27), where 18 gets $500 (P2.2): v22 3,200, no gap.
- 2026 sum: -1,667.91 + 1,700.00 = +32.09 = observed; 2025: -1,667.91 = observed. Unexplained 0 (PE vs TC 0.01 rounding).

**Confirmation.** TAXSIM 2026 with dep18 1 (dep17 1, dep13 1, depx 3): v22 3,200, line 1 6,109.37 (= TC with `overtime_income` 0: 6,109.37); adding `nonprop` -14,007.48 (IRA + overtime): v18 67,812.12, line 1 4,441.45 = PE and TC. TAXSIM 2025 `nonprop` -14,007.48: 4,544.45 = PE and TC; TC 2025 `overtime_income` 0: 6,212.37 = TAXSIM. With dep18 1 the 2026 EITC stays 0 (v25 0), as it is under law at AGI 114,421 with two children.

**Law.** Overtime: 26 U.S.C. 225 (`sources/uscode/usc26-s225.txt:31-52`). CTC: 24(c)(1) qualifying child "has not attained age 17" (`sources/uscode/usc26-24.txt:89`); $500 credit for other dependents (`:146`). EITC qualifying child under 19: 152(c)(3)(A) (not re-read this run; the age test is the board's and unit.py's reading). The 27-year-old is stated disabled; 152(c)(3)(B) would waive the age test for a permanently and totally disabled child, but the relationship is not stated and the EITC is 0 at this income either way, so no line moves.

**Verdict.** Overtime: (c) map could not express `fsla_overtime_premium` in TAXSIM (both years). 18-year-old's credit (2026): (d) the map is wrong for this household. The counts path cannot express "EITC child but not CTC child" in general (`keycheck/map_taxsim.py:112-121` says so), but here no EITC is payable under law, so the map loses nothing by sending dep18 = 1 (children under 17), which gives the law's 3,200. Corrected input: dep18 1, dep17 1, dep13 1, depx 3. A general rule (description): send dep18 = children under 17 whenever a 17- or 18-year-old's EITC-child status cannot change the EITC (AGI and earned income above the phase-out end for both counts), else keep the present rule and flag it. PE 2.60.0 = 2.116.15 (4,441.46).

cause: TAXSIM has no overtime deduction (-1,667.91 both years) and, in 2026, the counts path gives the 18-year-old $2,200 in place of $500 (+1,700); right: PE and TC.
progress: 7 of 10 households written (000, 026, 037, 046, 049, 055, 064); remaining 070, 078, 082

## scenario_070 (IL, single 57; wages 38,000; traditional 401(k) 1,484.94, Roth 401(k) 262.05, traditional IRA 69.39, Roth IRA 107.62; student loan interest 276; interest 100)

**Rows.** Line 1 in all three tables: 2026 key and rerun PE 1,979.96 = TC 1,979.96, TAXSIM 2,172.36 (diff -192.40); 2025 PE 2,031.46 = TC 2,031.46, TAXSIM 2,223.86 (diff -192.40). Lines 2-4 agree.

**Reconciliation (2026).** AGI agrees at 36,269.67 (wages 36,515.06 net of 401(k) + 100 - IRA 69.39 - student loan interest 276). TI 20,169.67 and tax before credits 2,172.36 agree in all three (PE `income_tax_before_credits`, TC c05200, TAXSIM v28). The only difference is the saver's credit: PE `savers_credit` 192.40, TC c07240 192.40 (amount the map computes, `e07240`), TAXSIM none. Single AGI 36,269.67 sits between $26,250 and $40,250, so the rate is 10%; qualified contributions 1,484.94 + 262.05 + 69.39 + 107.62 = 1,924.00 (under the $2,000 cap): 10% x 1,924.00 = 192.40, below the tax. 192.40 = observed; unexplained 0. 2025: same 10% band ($25,500 / $39,500 limits for 2025), same 192.40.

**Confirmation.** TC with `e07240` 0: line 1 2,172.36 (2026) / 2,223.86 (2025) = TAXSIM. TAXSIM's v28 equals PE's tax before credits to the cent, and its v22-v25 are 0.

**Law.** 26 U.S.C. 25B(a), (b), (d) (`sources/uscode/usc26-s25B.txt`); 2026 AGI limits for "all other" filers $24,250 / $26,250 / $40,250 (Notice 2025-67, `sources/irs/n-25-67.txt:156-160`); 2025 $23,750 / $25,500 / $39,500 (`n-25-67.txt:158-160` gives the 2025 figures as the "from" amounts). The testing-period distributions of earlier years are not stated; PE and the map both take them as zero (`keycheck/statute.py:182-186`).

**Verdict.** (c) the map could not express the saver's credit in TAXSIM: the build has no input for it (`keycheck/map_taxsim.py:211-215` computes it and records it as unexpressed). PE 2.60.0 = 2.116.15 (1,979.96).

cause: TAXSIM has no saver's credit (10% x 1,924.00 = 192.40); right: PE and TC.

## scenario_078 (MD, single 19; wages 198,505; state/local tax refund 1,631.91; property tax 26,460; mortgage interest 28,210 on 417,926; employee expenses 2,605.50)

**Rows.** Line 1 in the two 2026 tables: PE 24,164.46 = TC 24,164.46 (= committed key 24,164.46), TAXSIM 24,260.46 (diff -96.00). The board does not score this output (`board_scores_it` "no"). 2025: all agree at 24,509.46. Lines 2-4 agree.

**Reconciliation (2026).** AGI agrees at 200,136.91 (wages + the refund, which all three count in full per the unit reading `salt_refund_income`, `keycheck/unit.py:40`). All itemize. PE itemized 68,610 = SALT 40,400 (capped; uncapped 42,251.66 = property 26,460 + the key's Maryland income-tax amount 15,791.66) + mortgage interest 28,210 (balance under $750,000); TC c04470 68,610 (c18300 40,400). TAXSIM v17 68,210 = 40,000 + 28,210: the build caps SALT at $40,000 in 2026 (probe P9.1). TI 131,526.91 vs 131,926.91: 400 in the 24% bracket (105,700-201,775, single 2026) = 96.00 = observed; unexplained 0. MAGI 200,136.91 is far below the $505,000 phase-down threshold, so the law's cap is the full $40,400. Employee business expenses 2,605.50 are deducted by none of the three (miscellaneous itemized deductions are suspended). 2025: cap 40,000 is the law in 2025, so all three agree.

**Confirmation.** New probe `REPO/probes/taxsim/trace_a_078_saltcap.in.csv` / `.cd2026110117.out.csv` (the household's final record): default -> v17 68,210, fiitax 24,260.46; per-record `opt1` 8, `opt1v` 40400 -> v17 68,610, v18 131,526.91, fiitax 24,164.46 = PE and TC; reset (`opt1` 8, `opt1v` 0) -> 24,260.46 again.

**Law.** 26 U.S.C. 164(b)(7)(A)(ii): applicable limitation $40,400 for taxable years beginning in 2026; (B) phase-down by 30% of MAGI over $505,000 (`sources/uscode/usc26-164.txt:145-163`).

**Board exclusion record.** The board excluded this output (decided 2026-09-29) because whether the refund is income depends on an unstated fact: under 26 U.S.C. 111(a) (`sources/uscode/lii-26-111.txt:72`) a refund is income only to the extent the earlier deduction reduced tax. Frozen value 24,164.457 (= the committed key = PE 2.60.0 and 2.116.15 today); alternative 23,772.80 (refund excluded, on policyengine-us 2.15.17). TC sides with the key's value (24,164.46); TAXSIM sides with neither (24,260.46, the SALT-cap gap above). Neither other model was run on the alternative reading: the map counts the refund in full (`keycheck/unit.py:40`).

**Verdict.** (a) TAXSIM build cd2026110117 departs from the law: its 2026 SALT cap is the 2025 $40,000, not $40,400 (-96.00). PE (2.60.0 and 2.116.15 both 24,164.46) and TC follow 164(b)(7). (e) applies to the output, not to the 96: the committed key equals the engine value and the board does not score it; the refund's taxability is a fact the board does not state (b), and all three models take the board's reading.
Side observation, no dollar effect on any line: PE 2.60.0 `amt_income` 171,926.91 = TAXSIM v26; PE 2.116.15 `amt_income` 170,295.00 = TC c62100 170,295.00. The 1,631.91 gap equals the refund (inference: the newer release and TC subtract the refund in AMT income, as Form 6251 does for a refund of a tax the AMT disallows; Form 6251 not read this run). AMT does not bind here in any model.

cause: TAXSIM's 2026 SALT cap is $40,000, not $40,400 (400 x 24% = 96.00); right: PE and TC. Output excluded from scoring by the board over the refund's taxability (unstated prior-year benefit).

## scenario_082 (NY, head of household 23, child aged 1; wages 100,195; qualified dividends 13,424, non-qualified 7,056; STCG 2,289.18, LTCG -33,000; cash gifts 700; child care 9,600; property tax 9,216.53; state refund 67.50)

**Rows.** Line 1 in the two 2026 tables: PE 9,579.77 = TC 9,579.77 (= committed key), TAXSIM 9,733.77 (diff -154.00). 2025: all agree at 10,123.27 (no 170(p) deduction in 2025). Lines 2-3 agree. Line 4 (federal employee payroll) agrees at 7,664.92 in all tables; the board does not score `payroll_tax` here (see exclusion below).

**Reconciliation (2026).** AGI agrees (PE 117,661.12; TC/TAXSIM 117,661.13). All take the standard deduction 24,150 (HoH): PE itemized 15,229.98 = SALT 15,118.29 + charity 111.69 (700 less 0.5% x AGI); TAXSIM proptax 15,118.29 + mortgage 111.69, v17 0. PE adds `charitable_deduction_for_non_itemizers` 700 (cash, under the $1,000 cap); TC `standard` 24,850 = 24,150 + 700; TAXSIM none. TI PE 92,811.12 = TC 92,811.13; TAXSIM v18 93,511.13. The ordinary part (TI less 13,424 qualified dividends; net capital loss limited to 3,000 in all) is 79,387 vs 80,087, inside the HoH 22% bracket: 700 x 22% = 154.00 = observed. Credits identical: CTC 2,200; child care credit 600 in all three (AGI 117,661 puts the 2026 rate at its 20% floor: 35% less 22 points for 42,661 over $75,000, under the amended 26 U.S.C. 21(a)(2), `sources/uscode/usc26-21.txt:78-82`; TAXSIM's pre-2026 schedule also gives 20% here, so probe P5.2's defect does not bite at this income). Unexplained 0.

**Confirmation.** TC `e19800` 0: c04800 93,511.13, line 1 9,733.77 = TAXSIM. TAXSIM `nonprop` -700 (lowers AGI too; nothing else moves: standard deduction either way, CDCC rate already at the 20% floor, NIIT threshold not reached): v18 92,811.13, fiitax 9,579.77 = PE and TC.

**Law.** 26 U.S.C. 170(p) as amended by Pub. L. 119-21: non-itemizer cash gifts up to $1,000 (not joint), without the 0.5% floor (`sources/uscode/usc26-170.txt:926`, `:977-978`). Recipient type not stated.

**Board exclusion record.** On `payroll_tax`, not on a disagreeing line: frozen 8,108.03 = federal 7,664.92 + New York disability and paid-family-leave employee contributions 443.11 (PE `employee_state_payroll_tax`); alternative 7,664.92 (no NY contribution, since the employer may but need not deduct it). This check's line 4 is the federal part only, on which all three agree; TC and TAXSIM compute no state payroll tax, so they equal the alternative value by construction of the line, not by taking a side.

**Verdict.** (c) the map could not express the 2026 non-itemizer charitable deduction in TAXSIM (probe P9.5; `keycheck/map_taxsim.py:162-163`). PE 2.60.0 = 2.116.15 (9,579.77).
Side observation, no dollar effect (AMT binds in no model): AMT income PE 2.60.0 116,961.12, PE 2.116.15 116,893.62, TC c62100 117,593.63, TAXSIM v26 117,661.13. PE 2.116.15 and TC subtract the 67.50 refund (2.60.0 does not); TC also adds back the 700 170(p) deduction, PE keeps it deducted. Which is right for AMT was not read this run (26 U.S.C. 56(b)(1)(E) and Form 6251 not saved).

cause: TAXSIM has no 2026 170(p) cash-gift deduction (700 x 22% = 154.00); right: PE and TC.
progress: all 10 households written; summary tables next

## Corrections and additions (appended after the household sections)

- scenario_078: "miscellaneous itemized deductions are suspended" is law I did not read this run (26 U.S.C. 67(g) not saved). What is observed: none of the three models deducts the 2,605.50 employee expenses (PE itemized 68,610 = 40,400 + 28,210; TC c04470 68,610; the TAXSIM map sends nothing for them). It moves no line here.
- AMT-income side observations (078, 082), now read in code and law: PE 2.116.15 subtracts head/spouse state and local tax refunds from AMT income, citing 26 U.S.C. 56(b)(1)(C) and Form 6251 line 2b (`REPO/envs/pe211615/lib/python3.12/site-packages/policyengine_us/variables/gov/irs/tax/federal_income/alternative_minimum_tax/income/amt_income_before_separate_addition.py:50-71`); PE 2.60.0's `amt_income` has no such term (`REPO/envs/pe260/.../alternative_minimum_tax/income/amt_income.py:18-47`). Law: "No recovery of any tax to which subparagraph (A)(ii) applied shall be included in gross income for purposes of determining alternative minimum taxable income" (`sources/uscode/lii-26-56.txt:129-130`, saved this run). So 2.60.0 (and TAXSIM, v26) overstate AMTI by the refund; 2.116.15 and TC are right. No line moves in 078 or 082 (AMT binds nowhere). Separately, 56(b)(1)(D) disallows only "the standard deduction under section 63(c)" (`lii-26-56.txt:131-132`); TC's AMTI in 082 (117,593.63 = AGI - refund) adds back the 700 170(p) deduction because TC carries it inside `standard`, while PE keeps it deducted. Reading the statute, PE is right (inference: 170(p) is not a 63(c) amount; no form read); no dollar effect here.

## Summary table (TAXSIM minus PE; PE = TC in every row to within $0.01)

| Household | Line | Tables | Cause | Dollars | Verdict | Right |
|---|---|---|---|---|---|---|
| 000 | 1 | 2026 key, 2026 rerun, 2025 | tax-exempt interest 5,578.41 has no TAXSIM input, so it is left out of SS provisional income (taxable SS -4,741.65 at 12%) | -568.99 (each table) | (c) | PE, TC |
| 026 | 2 | all three | no qualified-overtime deduction in TAXSIM (7,746.26 at 12%), so less tax for the CTC to absorb and less refundable CTC | -929.55 (each) | (c) | PE, TC |
| 037 | 1 | all three | no overtime deduction (9,629.03 at 12%) | +1,155.48 (each) | (c) | PE, TC |
| 046 | 1 | all three | no overtime deduction (14,838.71 at 12%) | +1,780.65 (each) | (c) | PE, TC |
| 049 | 1 | all three | no overtime deduction (25,000 cap; 22% in 2026, 22%/24% in 2025) | +5,500.00 (2026), +5,559.54 (2025) | (c) | PE, TC |
| 049 | 1 | 2026 both | no 2026 170(p) cash-gift deduction (579.76 at 22%) | +127.55 | (c) | PE, TC |
| 055 | 1 | 2026 both | no 2026 170(p) deduction (1,000 at 24%) | +240.00 | (c) | PE, TC |
| 064 | 1 | all three | no overtime deduction (13,899.29 at 12%) | +1,667.91 (each) | (c) | PE, TC |
| 064 | 1 | 2026 both | counts path gives the 18-year-old the $2,200 CTC in place of the $500 ODC (dep18 2) | -1,700.00 | (d) map: send dep18 1 here | PE, TC |
| 070 | 1 | all three | no saver's credit input (10% x 1,924.00) | +192.40 (each) | (c) | PE, TC |
| 078 | 1 | 2026 both (board does not score it) | TAXSIM's 2026 SALT cap is $40,000, not $40,400 (400 at 24%) | +96.00 | (a) TAXSIM cd2026110117; output excluded by the board over the refund's taxability, (b)/(e) | PE, TC |
| 082 | 1 | 2026 both | no 2026 170(p) deduction (700 at 22%) | +154.00 | (c) | PE, TC |

Net per household and table: 000 -568.99; 026 -929.55; 037 +1,155.48; 046 +1,780.65; 049 +5,627.55 (2026) / +5,559.54 (2025); 055 +240.00 (2026); 064 -32.09 (2026) / +1,667.91 (2025); 070 +192.40; 078 +96.00 (2026); 082 +154.00 (2026). Every gap reconciles to within $0.01.

## PolicyEngine defects I would report

None on the four lines in these ten households: PE 2.60.0 and 2.116.15 give the same four lines in every one, and each matches Tax-Calculator and the statute. One no-dollar defect, already fixed in the newest release: PE 2.60.0 leaves state and local tax refunds in AMT income (26 U.S.C. 56(b)(1)(C)); 2.116.15 subtracts them. Smallest household that shows it: scenario_082 (refund 67.50; `amt_income` 116,961.12 on 2.60.0 vs 116,893.62 on 2.116.15); no line moves because the AMT does not bind.

## TAXSIM build defects seen (cd2026110117)

- 2026 SALT cap $40,000 / $500,000 in place of $40,400 / $505,000 (26 U.S.C. 164(b)(7)): scenario_078, +96.00. Confirmed by probe `REPO/probes/taxsim/trace_a_078_saltcap.*`.
- Missing 2025-2028 and 2026 provisions with no input: qualified overtime (026, 037, 046, 049, 064), 170(p) non-itemizer gifts (049, 055, 082), saver's credit (070), tax-exempt interest in SS provisional income (000).

## Map errors and map improvements

1. (Error, scenario_064.) `keycheck/map_taxsim.py:116-119` always counts a 17- or 18-year-old EITC child in `dep18` when there are fewer than three children under 17; the build then gives that child $2,200. Where the EITC is zero for either count (here AGI 114,421 with two EITC children), send dep18 = dep17 = children under 17 and keep depx. Corrected 064 input for 2026: depx 3, dep18 1, dep17 1, dep13 1 (gives v22 3,200, the law's credit). General rule: compute the law's EITC for both counts (or check AGI and earned income against the larger count's phase-out end) and use the lower dep18 when the EITC is the same.
2. (Improvement, scenario_078.) The map can set the law's 2026 SALT limit per record with `opt1` 8, `opt1v` = max(10,000, 40,400 - 30% x max(0, MAGI - 505,000)) (P15.2 shows opt1/opt1v work per record; P15.3 shows they persist, so every record must carry them; `keycheck/taxsim.py:16-22` ORDER and its unknown-name check would need opt1/opt1v added). That removes the 96.00 gap in 078 and the build's SALT-cap defect for every 2026 itemizer.
3. (Optional, scenario_000.) Tax-exempt interest could be carried by computing 26 U.S.C. 86 taxable SS in the map and sending it in `pensions` with `gssi` 0; the confirmation run reproduces PE and TC (2,906.45). This moves the computation from TAXSIM into the map, so it tests less of TAXSIM; leave it unexpressed unless the lead wants TAXSIM's line 1 to stand in.
4. No change recommended for overtime, 170(p) and the saver's credit: the only route is negative `nonprop`, which also lowers AGI (and EITC earned income), so it is exact only where nothing else depends on AGI.

## PolicyEngine experiments requested

None. Every gap is reconciled from PE's own intermediate values in the dossiers and confirmed by Tax-Calculator and TAXSIM counterfactuals.

STATUS: complete
