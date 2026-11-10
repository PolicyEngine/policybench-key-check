# PolicyBench key check

Work in progress. This repo checks PolicyBench's US answer key for four federal tax
outputs by running the board's households through three independent tax calculators
and comparing the results:

1. **PolicyEngine-US**, which writes the key: policyengine-us 2.60.0 with the board's
   reference conventions (the version the published references use), and the newest
   PyPI release.
2. **Tax-Calculator** (PSLmodels/Tax-Calculator), at its own current-law settings.
3. **NBER TAXSIM**, NBER's own Fortran binaries. This is not PolicyEngine's TAXSIM
   emulator: policyengine-taxsim answers tax years 2021 and later with PolicyEngine,
   so its output is not a third implementation.

The four outputs:

| PolicyBench output | PolicyEngine-US variable |
|---|---|
| `federal_income_tax_before_refundable_credits` | `income_tax_before_refundable_credits` |
| `federal_refundable_credits` | `income_tax_refundable_credits` |
| `self_employment_tax` | `self_employment_tax` |
| federal part of `payroll_tax` | `employee_social_security_tax` + `employee_medicare_tax` + `additional_medicare_tax` (the board's `spm_unit_payroll_tax` also adds `employee_state_payroll_tax`, which this check reports separately) |

Households: the board's 100 published US households
(`paper/snapshot/20260501/runs/us_full_run_20260612_policyengine_4_16_1_populace/` in
PolicyEngine/policybench), then a larger draw built the way the board builds its own.
The board's tax year is 2026.

This check changes no PolicyBench reference. Where it finds a defect in an
implementation, the README names the statute, form line or instruction that decides it.

## Status

Scaffold only. Method, results and the agreement tables land here as the work proceeds.
