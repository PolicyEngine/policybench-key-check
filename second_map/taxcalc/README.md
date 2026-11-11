# Blind second input map: PolicyBench's 100 households in Tax-Calculator 6.9.0, tax year 2026

This folder holds an independent map from the board's 100 benchmark households to
Tax-Calculator 6.9.0 inputs, the engine runs, and the four answers per household. It was
written without sight of any other map to this engine or to TAXSIM, of PolicyEngine-US code,
or of any answer for these households (blindness rules in `brief-blind-common.md`).

- All 100 households are mapped and run. They make 103 engine records: 100 main returns and
  the own returns of three dependents with income (067 Dependent 1, 093 Dependent 1,
  123 Child 1).
- Regenerate everything with
  `REPO/envs/tc690/bin/python map.py`
  (about 75 s with the 15 alternative readings; add `--quick` to skip them).

| File | What it holds |
|---|---|
| `map.py` | the program: reads `../input/board/scenarios.csv` and `state_and_local_tax_2026.csv`, writes all files below |
| `inputs_2026.csv` | engine inputs of the final main pass R5, one row per return (`case_id`, `record`, engine names) |
| `inputs_payroll_pass_2026.csv` | inputs of the payroll pass R6 (differs from R5 only in `e00200p/s`, see below) |
| `passes_2026.csv` | what passes R1-R4 computed: MAGIs, allowed passive loss, `e03150`, `e03210`, `e07240`, `e09900` |
| `returns_2026.csv` | engine outputs per return (R5 prefix `R5_`, payroll pass `R6_`) |
| `answers_2026.csv` | `case_id`, `quantity`, `value`, `formula`: 400 rows |
| `notes.csv` | 358 notes: `reading`, `computed_from_statute`, `unexpressed`, `engine_behaviour` |
| `variants_2026.csv` | each alternative reading that moves an answer, with the moved value |
| `probes/` | engine probes p01-p03 (`.py` and `.out`) |
| `sources/` | the law, fetched from irs.gov and law.cornell.edu, as PDF/HTML plus text |
| `PROGRESS.md` | the work log |

## 1. Running the engine for one year on hand-built records

Each point below comes from the engine's code or from a probe.

- **No growth, no weights.** `Records(data=df, start_year=2026, gfactors=None, weights=None)`
  takes the data as given (records.py:35-37, 126-142). `Calculator` advances records only
  while `records.current_year < policy.current_year` (calculator.py:117-119). So the policy
  is left at 2026 and `map.py` asserts `calc.current_year == 2026` on every run.
- **Randomness: EITC and ACTC are dropped at random by default.** `EITC` and
  `AdditionalCTC` zero the credit when `credit_claim_urn >= prob`, where
  `prob = *_claim_prob_scale x max(*_claim_prob_min, credit/max)`
  (calcfunctions.py:3237-3244, 4342-4350). `credit_claim_urn` is a seeded uniform draw per
  record (records.py:197-199). The 2026 defaults are `eitc_claim_prob_scale` 1.03 and
  `actc_claim_prob_scale` 1.1 (probe p01).
  - Probe p02: ten identical single parents with $40,000 of wages get an EITC of $1,852.62
    or $0 depending on the draw, and five of the ten lose it.
  - Every run sets both scales to 9e99. The code comment calls this "always claim"
    (calcfunctions.py:3240, 4345), and probe p02 shows all ten getting $1,852.62 under it.
- **Approximation: smoothed phase-outs by default.** With `exact_calculations=False`
  (records.py:129, 142) the engine smooths stepped phase-outs: the CTC's $50 per $1,000,
  the CDCC's 1 point per $2,000, and the Sch 1-A overtime, tip and auto-loan steps.
  Probe p02: a married couple's CTC at AGI $401,234 is $2,138.30 smoothed and $2,100.00
  exact (IRC 24(b)(1)). Every run uses `exact_calculations=True`.
- **`soi_iitax` is False in 2026** (probe p01). So `iitax` excludes `setax`, `e09800` and
  `ptax_amc`, and `payrolltax` includes them plus the employer share
  (calcfunctions.py:4895-4910). The four answers are therefore built from components, not
  from `iitax` or `payrolltax`.

## 2. The four answers (`answers_2026.csv`)

Each answer sums every return the household files (main return plus any dependent's own
return).

| Quantity | Formula | Engine source |
|---|---|---|
| `federal_income_tax_before_refundable_credits` | `c09200 - setax - ptax_amc` (with `e09800` = 0) = Form 1040 line 22 `max(0, c05800 - c07100)` + `niit` + `e09900` | `c09200 = line22 + e09700 + e09800 + e09900 + niit + setax + ptax_amc` (calcfunctions.py:4514-4529); `c05800` includes AMT |
| `federal_refundable_credits` | `refund` = `eitc + c11070 (ACTC) + c10960 (AOTC) + CDCC_refund + recovery_rebate_credit` (the last two are 0 in 2026) | calcfunctions.py:4881-4890 |
| `self_employment_tax` | `setax` (Sch SE, both spouses) | EI_PayrollTax, calcfunctions.py:229-260 |
| `federal_employee_payroll_tax` | `ptax_was - ptax_er_p - ptax_er_s + ptax_amc` from the payroll pass R6 | `ptax_was` is employee plus employer FICA on `e00200p/s + pencon_p/s` (calcfunctions.py:213-227) |

Readings in these formulas:

- The income-tax line counts NIIT (IRC 1411) and the IRC 72(t) additional tax, both
  Schedule 2 income taxes. Alternative: line 22 alone (variant `line22_only`: 005, 020, 052,
  064 and 120 move; see section 6).
- Additional Medicare Tax is all in payroll tax, including the part Form 8959 levies on SE
  income. The board's payroll definition names Additional Medicare Tax, and its SE tax
  definition excludes it.

## 3. Passes

Several limits depend on a MAGI that itself depends on other limited deductions. Each pass
is a full engine run of all 103 records.

| Pass | Purpose | What it sends differently |
|---|---|---|
| R1 | MAGI for the IRC 469(i) rental allowance: AGI less taxable Social Security, without IRA, student-loan or passive-loss deductions (469(i)(3)(F)) | rental and farm-rent net counted only if positive; `e03150 = e03210 = 0` |
| R2 | MAGI for IRC 219(g) (IRA deduction) and 408A(c)(3) (Roth): after 86 and 469, without 219 and 221 | allowed passive result; `e03150 = e03210 = 0` |
| R3 | MAGI for IRC 221(b)(2)(C) (student loan interest) | adds `e03150` |
| R4 | AGI for IRC 25B (saver's credit) and the 72(t)(2)(B) medical exception | adds `e03210` |
| R5 | final main pass; source of the income-tax, refundable-credit and SE-tax answers | adds `e07240`, `e09900`; AGI asserted equal to R4 |
| R6 | payroll pass | `e00200p/s` less employer disability pay under 65 (not FICA wages); `setax` asserted equal to R5 |

## 4. Who files, in what status, and who is whose dependent

- **Head and spouse.** The head and a listed spouse file jointly (`MARS` 2). A head without
  a spouse files single (`MARS` 1), or head of household (`MARS` 4) when any child or
  dependent is listed. Every listed child and dependent passes the qualifying-child test
  (`map.py` asserts it).
- **Surviving spouses.** Twelve people are flagged as surviving spouses. None has a
  dependent child, so none gets qualifying-surviving-spouse status (IRC 2(a)(1)(B),
  sources/usc26_2.txt). Those still married file jointly; the rest file single.
- **Unmarried partners.** The two people flagged "unmarried partner of household head"
  (020, 056) are themselves lone heads, and they file single.
- **Qualifying children.** Every listed child and dependent is a qualifying child of the
  head (IRC 152(c), sources/usc26_152.txt):
  - Age test (c)(3): under 19, or permanently and totally disabled at any age. The waiver in
    (c)(3)(B) also covers the "younger than the taxpayer" test.
  - Relationship, abode, support and joint-return tests are taken as met: the board states
    no fact about them.
  - Adult dependents: 064 Dependent 1 (27, disabled), 064 Dependent 2 (18), 067 Dependent 1
    (23, disabled) and 093 Dependent 1 (27, disabled).
- **Credit counts:**
  - `n24`: qualifying children under 17 (CTC).
  - `XTOT - n24 - filers`: the engine's $500 credit for other dependents (ODC).
  - `EIC`: up to 3 qualifying children.
  - `f2441`: dependents under 13 (IRC 21(b)(1)(A)).
- **A dependent with income of their own files a separate return** as a dependent (`DSI` 1:
  dependent standard deduction, no EITC, no personal credits). This applies to 067
  Dependent 1, 093 Dependent 1 and 123 Child 1. The household answer adds that return.
  Alternative: main return only (variant `main_return_only`; 093 and 123 each move
  -3,220.00). Payroll tax always counts every worker.
- **093 Dependent 1 is stated disabled but earns $45,000 in wages.** Permanent and total
  disability means being unable to engage in any substantial gainful activity (IRC 22(e)(3),
  sources/usc26_22.txt). Full-time work at this pay contradicts that, but the map follows the
  stated flag. Alternative: not a dependent, so the main return loses the $500 ODC (income
  tax +500.00) and the worker files as a non-dependent with the same $16,100 standard
  deduction.

## 5. Engine inputs: what each holds and why

The input names are Tax-Calculator's, from `records_variables.json` (section "read").

**Return structure**

| Input | Holds |
|---|---|
| `MARS`, `DSI`, `XTOT`, `EIC`, `n24`, `nu06`, `nu13`, `nu18`, `n1820`, `n21`, `elderly_dependents`, `f2441` | return structure (section 4) |
| `age_head`, `age_spouse`, `blind_head`, `blind_spouse` | stated age and `is_blind`; the engine applies the additional standard deduction, the senior deduction (SeniorDed_c 6,000, 6% phase-out over 75,000/150,000, probe p01), the EITC age band and Schedule R from these |

**Wages and pensions**

| Input | Holds |
|---|---|
| `e00200p`, `e00200s` | Form W-2 box 1 wages: `employment_income` less traditional 401(k) deferrals. The engine documents them as wages net of deferrals, and EI_PayrollTax adds `pencon` back for FICA (calcfunctions.py:215-216). Employer disability pay under 65 is added here as Form 1040 line 1h income (see readings) and removed in the payroll pass. Tips and the FLSA overtime premium are already inside `employment_income`, which the glossary describes as "including tips"; the premium is "included in employment_income". |
| `pencon_p`, `pencon_s` | traditional 401(k) deferrals, limited by IRC 402(g)(1) $24,500 plus 414(v) catch-up $8,000 at 50+ or $11,250 at 60-63 (sources/n-25-67.txt:37-51), and never above gross pay. Traditional deferrals fill the limit before Roth deferrals; alternative `k401_pro_rata`. |
| `e01400` | `taxable_ira_distributions` |
| `e01500`, `e01700` | total and taxable pensions. Total = taxable private pension + tax-exempt private pension + 401(k) and 403(b) distributions + disability benefits at 65 or over + `survivor_benefits`. Taxable = the same without the tax-exempt pension. |
| `e02400` | all Social Security benefits of the return's people (retirement, SSDI, survivors, dependents) |
| `e02300` | unemployment compensation |

**Investment income**

| Input | Holds |
|---|---|
| `e00300` | taxable interest |
| `e00400` | tax-exempt interest (enters the Social Security worksheet and the EITC investment-income test) |
| `e00600` | ordinary dividends = qualified + non-qualified + BDC + REIT/PTP income |
| `e00650` | qualified dividends |
| `p22250`, `p23250` | net short- and long-term capital gains (negative = loss); the engine limits a net loss to $3,000 |
| `e01100` | capital gain distributions (`non_sch_d_capital_gains`), floored at 0 per the glossary |

**Business, rental and other income**

| Input | Holds |
|---|---|
| `e00900p`, `e00900s` | Schedule C: `self_employment_income` + `sstb_self_employment_income_before_lsr` |
| `e02100p`, `e02100s` | Schedule F: `farm_operations_income`. `farm_income` is the Schedule J figure for the same farm and is not entered again. |
| `k1bx14p`, `k1bx14s` | `partnership_se_income`, read as K-1 box 14 SE earnings inside `partnership_s_corp_income` |
| `e26270` | partnership and S-corp income (includes `k1bx14`, per records_variables.json) |
| `e02000` | Schedule E total: partnership/S-corp + estate/trust + rental and farm rent after IRC 469 (R1) |
| `e27200` | farm rent that is qualified business income: farm rent of a person with stated non-SSTB UBIA. `e27200` is inside `e02000` and enters the engine's QBI (calcfunctions.py:1796). |
| `e00700` | `salt_refund_income` |
| `e00800` | alimony received (no effect under the engine's post-2018 law) |
| `e01200` | 0. It is Form 4797 gain, and only the variants use it as a proxy for other income. |
| `PT_SSTB_income` | 1 when the return's only business is an SSTB |
| `PT_ubia_property` | stated UBIA (SSTB and non-SSTB) |
| `PT_binc_w2_wages` | 0 (no business W-2 wages stated) |

**Adjustments to income**

| Input | Holds |
|---|---|
| `e03150` | IRA deduction (statute, R2) |
| `e03210` | student loan interest deduction (statute, R3) |
| `e03220` | educator expenses up to $350 per educator (rp-25-32.txt:749-759) |
| `e03270` | SE health insurance (IRC 162(l)) |
| `e03290` | HSA deduction (IRC 223(b)) |
| `e03500` | alimony paid (no effect under post-2018 law) |
| `e03240` | `domestic_production_ald`: IRC 199 is repealed; the engine's haircut is 1 |

**Itemized deductions** (all on the main return, summed over every listed person)

| Input | Holds |
|---|---|
| `e17500` | medical expenses before the 7.5% floor: `other_medical_expenses` + person-paid premiums, less any SE health insurance deduction |
| `e18400` | the board's state and local income or sales tax for the household, before the cap |
| `e18500` | real estate taxes |
| `e19200` | mortgage interest after the IRC 163(h)(3)(F) limit |
| `e19800` | cash gifts to charity |
| `e20100` | non-cash gifts to charity |
| `e20400` | unreimbursed employee expenses (suspended in 2026, `ID_Miscellaneous_hc` 1) |

The engine applies the 2026 SALT cap ($40,400, reduced by 30% of MAGI over $505,000, floor
$10,000), the 0.5% charity floor, the non-itemizer charity deduction, the 7.5% medical floor
and the itemized-deduction reduction (probe p01).

**Credits and other taxes**

| Input | Holds |
|---|---|
| `e32800` | `spm_unit_pre_subsidy_childcare_expenses`. The engine applies the $3,000/$6,000 cap and the earned-income limit. |
| `e07240` | tentative saver's credit (statute, R4). The engine limits it by tax after CDCC and education credits (calcfunctions.py:4175-4187). |
| `e09900` | IRC 72(t) additional tax (statute, R4) |

**Schedule 1-A**

| Input | Holds |
|---|---|
| `overtime_income` | `fsla_overtime_premium` |
| `tip_income` | `tip_income` |
| `auto_loan_interest` | the household's `auto_loan_interest` |

The engine takes all three "to already represent the form-qualified amounts"
(calcfunctions.py:872-878) and applies the caps and phase-outs.

### Inputs the engine takes as already limited

These inputs have no cap in the engine's code:

- In `Adj` (calcfunctions.py:370-383): `e03150`, `e03210`, `e03220`, `e03290` and `e03270`.
- `e19200`, "pre-aggregated" (calcfunctions.py:1278-1283).
- `e07240`.
- `pencon_p/s`.
- `e09900`.

`map.py` computes each from statute:

- **401(k) deferrals** (IRC 402(g), 414(v)), 24 households: limited by the dollar limit and
  by pay (064 Dependent 1 has no pay, so 0).
- **IRA contributions and deduction**, 24 households:
  - Contributions are limited by compensation (IRC 219(b)(1), 219(f)(1); SE earned income is
    net profit less half SE tax), with spousal compensation (219(c)) and the dollar limit
    $7,500 + $1,100 at 50+ (n-25-67.txt:162-166).
  - The Roth MAGI limit follows 408A(c)(3) (n-25-67.txt:197-213).
  - The deductible limit follows 219(g): the active-participant ranges 81,000-91,000 single
    and 129,000-149,000 joint, and 242,000-252,000 when only the spouse is covered
    (n-25-67.txt:168-194). The reduction is rounded down to $10 with a $200 floor
    (sources/usc26_219.txt:104-115).
  - Active participant = makes 401(k) deferrals.
  - Probe p03 checks this against Pub 590-A Worksheet 1-2 (sources/p590a.txt) with zero
    disagreements on a 2026 grid. No household falls inside a phase-out range.
- **Student loan interest** (IRC 221): $2,500 cap and the phase-out 85,000-100,000 /
  175,000-205,000 (rp-25-32.txt:1003-1012). Touches 016 and 093 (capped at 2,500), and 070
  and 071 (taken whole).
- **Saver's credit** (IRC 25B): AGI tiers MFJ 48,500/52,500/80,500, HoH
  36,375/39,375/60,375, other 24,250/26,250/40,250 (n-25-67.txt:140-159).
  - Qualifying contributions: 401(k) and IRA contributions, less the year's plan and IRA
    distributions (25B(d)(2)), capped at $2,000 per person.
  - An eligible individual is 18 or older, not a dependent and not a full-time student (none
    is stated full-time).
  - Nonzero tentative credits: 070 (192.40), 091 (120.00), 100 (1,000.00, then limited to
    $0 by tax) and 119 (200.00). In 023 and 043, distributions exceed contributions.
- **Mortgage interest** (IRC 163(h)(3)(F), $750,000 limit; Pub 936 Table 1 lines 11-15,
  sources/p936.txt:899-952).
  - 049: 2,743.00 x 0.750 = 2,057.25. 120: 3,744.00 x 0.750 = 2,808.00.
  - The stated balance stands in for the average balance, and the debt is read as incurred
    after 12/15/2017. Alternative `mortgage_grandfathered` ($1,000,000) moves 120 by -224.64.
- **Passive rental loss** (IRC 469(i)): $25,000 allowance less 50% of MAGI over $100,000,
  with active participation assumed.
  - 098: farm rent loss of -11,100 allowed in full.
  - 120: the net -446.59 is suspended at MAGI 199,245.80.
  - Alternative `no_passive_active_participation` moves no answer.
- **HSA** (IRC 223(b)): 056 states $9,915.44 on a one-person return. The self-only limit
  is $4,400 (rp-25-19.txt:38-45), so `e03290` = 4,400.
- **SE health insurance** (IRC 162(l)): 038 deducts its premiums of 100.00, limited to SE
  earned income of 14,428.19. No filer or spouse has employer coverage.
- **IRC 72(t)**: 064 has early 401(k) distributions of $20,000 at age 48.
  - Medical exception 72(t)(2)(B): medical 8,340.00 less 7.5% of AGI 114,421.41 is below 0.
  - Additional tax = 2,000.00.
  - The 72(t) exceptions for disability apply to 057, 067 and 084: none of them owes the tax
    (see readings).
- **Educator expenses** (086, 099): under the $350 cap, entered whole.

## 6. Readings and the alternative each rules out

Each reading is applied uniformly. `variants_2026.csv` records every one that moves an
answer.

| Reading (main map) | Alternative | Households moved (delta) |
|---|---|---|
| A household's answer sums every return its members file | main return only | 093, 123 income tax -3,220.00 each |
| Income tax includes NIIT and the 72(t) additional tax | Form 1040 line 22 only | 005 -5,721.98; 020 -222.64; 052 -218.44; 064 -2,000.00; 120 -87.40 |
| Over-the-counter health expenses are not medical expenses: IRC 213(b) allows only prescribed drugs and insulin (sources/usc26_213.txt) | include them | 064 -75.84; 114 -440.00; 121 -40.00 |
| Stated `auto_loan_interest` is Sch 1-A qualified interest (new US-assembled vehicle, loan after 2024: the board states nothing against it) | not qualified | 12 households: 10 move income tax by +32.98 to +346.50 (002, 003, 018, 033, 053, 067, 086, 093, 099, 101); 026 and 028 move refundable credits by -45.37 and -117.60 |
| Residential rental with stated UBIA is not QBI: the engine has no input for rental QBI (unexpressed) | proxy through `e27200` | 022 -200.20; 076 -192.00 |
| `miscellaneous_income` (Sch 1 line 8z) has no engine input (unexpressed) | proxy through `e01200` | 022 +773.19 |
| `social_security_dependents` is income of the person it is stated on | the youngest child's | 086 -1,308.05 |
| Alimony falls under post-2018 law: not deductible, not income | pre-2019 instrument | 020 -1,998.08 (031 and 056 do not move) |
| Mortgage debt incurred after 12/15/2017 ($750,000 limit) | grandfathered $1,000,000 | 120 -224.64 |
| A one-person return's HSA coverage is self-only | family | none |
| `educational_assistance` is a qualified scholarship, excluded (IRC 117, sources/usc26_117.txt) | taxable, proxied through `e01200` | 030 +190.00; 068 +12,818.36 |
| SSDI receipt meets the IRC 72(m)(7) disability test, so 72(t) does not apply | not disability for 72(t) | 074 +38.40 |
| Active participation in rentals (IRC 469(i)) | none | none |
| `tip_income` lies inside `employment_income` (glossary: "including tips") | on top of wages | 088 payroll +734.40 |
| Employer disability pay is not FICA wages | FICA wages | 057 +2.91; 067 +826.20; 084 +642.60; 121 +997.87 (payroll) |
| Traditional 401(k) deferrals fill the 402(g) limit before Roth | pro rata | 005 income tax +1,490.56 |
| Employer disability benefits under 65 are Form 1040 line 1h earned income | unearned pension at every age | 067 income tax +945.00 (Dependent 1's own return loses the earned-income dependent standard deduction); 084 refundable credits -642.60 (no EITC) |

Readings that move no answer, or that have no variant:

- **Unlisted facts.** An unlisted number is 0 and an unlisted boolean is false (board
  preface). Eligibility facts the board never states (valid SSNs, the qualifying-child
  relationship, abode and support tests, W-2 reporting of overtime, tip occupation,
  vehicle qualification, rental participation) are taken as met. Facts the board states for
  some people (disabled, blind, student) are false where unlisted.
- **Premiums.**
  - Premiums = `health_insurance_premiums_without_medicare_part_b` where stated, else
    `other_health_insurance_premiums`, never their sum. The glossary calls the first "the
    non-Medicare component of the medical expense premium aggregate", and the second
    excludes Marketplace, CHIP and Medicaid premiums, so it is a part of the first. Where
    both are stated, the first is never smaller (001: 20 and 20; 067: 10,260 and 3,909).
  - Employer-paid ESI premiums are excluded from income and are not the employee's medical
    expense (IRC 106).
- **Disability benefits.**
  - Taxable under IRC 105(a) (sources/usc26_105.txt), since no employee-paid premium is
    stated.
  - The 2025 Form 1040 instructions put disability pensions received before the employer's
    minimum retirement age on line 1h "Other Earned Income", and later ones on lines 5a/5b
    (sources/i1040gi.txt:1440, 1536-1544, 1821-1826).
  - The dependent standard deduction worksheet counts line 1z, which includes 1h, as earned
    income (i1040gi.txt:2313-2315).
  - The plan's minimum retirement age is not stated; 65 stands in for it.
- **Survivor benefits.** `survivor_benefits` (non-Social-Security) is a fully taxable survivor
  annuity.
- **Farm rent.**
  - Farm rent is a rental activity under IRC 469 and is not SE income (IRC 1402(a)(1)).
  - With stated UBIA it is QBI (`e27200`); without UBIA it is not (098 is a loss and has no
    other QBI, so this does not matter there).
- **Partnership income.** Partnership/S-corp income with no `partnership_se_income` is not
  SE income, and material participation is assumed for the passive rules.
- **REIT, PTP and BDC income** enter as ordinary dividends (not qualified). Their IRC
  199A(b)(1)(B) component has no engine input (section 8).
- **Excluded income.**
  - Veterans' benefits (38 U.S.C. 5301), workers' compensation (IRC 104(a)(1)),
    `financial_assistance` (gifts, IRC 102), child support received, WIC, housing and
    energy assistance, and qualified Roth IRA distributions (IRC 408A(d)(1)) are excluded
    from income.
  - Child support paid is not deductible.
  - Assets, hours, hourly rates, rent and pregnancy have no federal income or payroll tax
    role. `map.py` lists each such fact with its reason (`NO_EFFECT`) and stops on any
    unknown fact.
- **AOTC.** The AOTC flags appear in four people's facts, but no qualified tuition expense is
  stated, so no AOTC. Half-time enrolment does not make anyone a full-time student for 25B
  or the kiddie tax.
- **033 HSA.** Both spouses are 65+ and receive Social Security, which usually means Medicare
  enrolment and no HSA eligibility (IRC 223(b)(7)). Enrolment is not a stated fact, so the
  stated $1,486 deduction, under the family limit, is kept.
- **Children with wages.** 123 Child 1 (16) earns $45,000 and stays the head's qualifying
  child: there is no gross-income test for a qualifying child, and the support test is taken
  as met. With no unearned income there is no kiddie tax.

## 7. Engine behaviours found by probe or code reading

- **Claim probabilities and exact calculations:** section 1, probes p01 and p02.
- **Parameter values:** probe p01 dumps every 2026 value the map relies on. Examples:
  - Standard deductions 16,100/32,200/24,150.
  - Brackets.
  - CTC 2,200, ACTC 1,700, ODC 500.
  - EITC maxima 664/4,427/7,316/8,231.
  - SS wage base 184,500.
  - AMT exemption 90,100/140,200.
  - Senior deduction, overtime, tip and auto-loan deduction parameters.
- **Schedule SE:** probe p03 checks `map.se_tax_own` (used only to size the IRA
  compensation and SE health limits) against the engine's `setax` on six cases, including
  the $400 floor and the OASDI base shared with wages. All six match.
- **Hand checks against form arithmetic, all of which agree:**
  - 054: EITC 6,356.80 + ACTC 2,008.80.
  - 008: ACTC Part II-A 4,202.61 with EITC 8,231.
  - 119: CDCC 35% x 1,560, CTC limited to tax, ACTC 2,089.77, EITC 1,276.30.
  - 099: CDCC 32% x 6,000 = 1,920.
  - 022: senior deduction 6,000 - 6% x 30,849 = 4,149.05.
  - 120: NIIT 3.8% x 2,300 = 87.40.
  - 005, 020, 049, 052: Additional Medicare Tax.
  - 093: Dependent 1's return has a $16,100 standard deduction and $3,220 of tax.
  - 123: Child 1's return has $3,220 of tax on $28,900 taxable.
- **Tax tables.** The engine taxes by the rate schedules and computes the EITC by formula.
  The IRS Tax Table and EIC Table use $50 bands and can differ by a few dollars below
  $100,000. Not adjusted.
- **Schedule R models age 65+ only.** The engine's docstring says boxes 2/4/5/6/9
  (disability under 65) are unreachable (calcfunctions.py:3644-3647).
- **Nonrefundable credit order.** The engine applies FTC, CDCC, education credits and the
  saver's credit before CTC/ODC (calcfunctions.py:4175-4190), as Schedule 8812's Credit
  Limit Worksheet A does.
- **Non-itemizer charity deduction.** The engine adds it to `standard`: for example 005's
  `standard` is 32,200 + 1,069.76.

## 8. What could not be expressed

| Household | Fact | Line | Effect |
|---|---|---|---|
| 022 | `miscellaneous_income` 3,300 (Sch 1 line 8z): no general other-income input; `e01200` is Form 4797 gain | income tax | variant +773.19 if it were taxed as ordinary income |
| 022, 076 | rental income with stated UBIA (an implied qualified rental business): no input for rental-real-estate QBI | income tax | variant -200.20, -192.00 |
| 042, 052 | BDC dividends 70.94 and 0.40: no 199A input for them | income tax | at most 20% x amount x marginal rate (under $3) |
| 081 | REIT/PTP income 6.22: the 20% 199A(b)(1)(B) component has no input | income tax | under $1 |
| 057 (both), 067 Dep. 1, 084, 121 | Schedule R for the disabled under 65 (taxable disability income): the engine models age 65+ only | income tax | $0 in each, checked per return (below) |

The Schedule R check behind the last row:

- 057, 067 Dependent 1 and 084 owe no regular tax (`c05800` = 0).
- 121 (single): line 17 = 0.5 x (38,709 - 7,500) = 15,604.50, more than the $5,000 base,
  so the credit is 0.

Every household is mapped and answered; none was dropped.

## Sources

**Law**, in `sources/` as fetched files plus `pdftotext -layout` text:

- Rev. Proc. 2025-32 (2026 inflation adjustments): `rp-25-32`.
- Notice 2025-67 (2026 retirement plan limits): `n-25-67`.
- Rev. Proc. 2025-19 (2026 HSA limits): `rp-25-19`.
- Pub 936, Pub 525, Pub 590-A (2025): `p936`, `p525`, `p590a`.
- 2025 Instructions for Form 1040: `i1040gi`.
- 24 sections of title 26 from law.cornell.edu (`usc26_<section>`): 2, 21, 22, 24, 25A, 25B,
  32, 72, 104, 105, 117, 152, 162, 163, 199A, 213, 219, 221, 223, 402, 414, 469, 1402, 1411.

**Engine:** `records_variables.json`, `records.py`, `calcfunctions.py`, `calculator.py`,
`policy.py`, and the 2026 parameter values read through `Policy` (probe p01).
