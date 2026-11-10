# Evidence the input maps rest on

Five readers (Claude Opus 5.5, 2026-11-10) established, from code, documentation and probes, how
each model treats every fact a PolicyBench household states. Each claim cites a file and line, or
a probe's input and output. The maps in `keycheck/` were written from these files.

| File | Establishes |
|---|---|
| `pe-income.md` | How policyengine-us 2.60.0 uses each income-type input in the four federal lines |
| `pe-deductions-credits.md` | The same for deductions, expenses, credits and demographics; filing status and dependents; the board's convention modules |
| `taxcalc.md` | Tax-Calculator 6.9.0: what each input must hold, what it computes and what it takes as given, its outputs, and how to run one year with no extrapolation |
| `taxsim.md` | NBER taxsimtest cd2026110117: inputs and outputs by NBER's pages and by probe (probe files in `probes/taxsim/`) |
| `law-2026.md` | 2026 and 2025 amounts from Rev. Proc. 2025-32, Rev. Proc. 2024-40, the statute and IRS notices, beside each model's values |

Paths: `REPO` is this repository's root; `PE` or `PEU` is the installed policyengine-us 2.60.0
package; `TC` the installed taxcalc 6.9.0 package; `PB` or `FIX` PolicyBench at commit c7ede86c;
`sources/` the folder of saved law texts (IRS and U.S. Code documents named in each citation).
"The lead" is the session that ran the comparison.
