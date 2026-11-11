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

## Traces and reviews

`traces/` holds the working files of the agents that traced the disagreements and reviewed the
maps (Claude Opus 5.5, 2026-11-10), as they wrote them. Where a later file corrects an earlier
one, the later file says so; `docs/causes.md` gives the settled account.

| File | Holds |
|---|---|
| `traces/trace-pe-a.md`, `traces/trace-pe-b.md` | Every household and line where PolicyEngine stands apart from the other two models, or all three differ, reconciled to the dollar |
| `traces/trace-taxsim-a.md`, `traces/trace-taxsim-b.md` | Every household and line where TAXSIM stands apart, reconciled to the dollar, with probes of the build |
| `traces/verify-unit-statute.md` | Review of `keycheck/unit.py` and `keycheck/statute.py` against the statute and the published amounts |
| `traces/verify-map-taxcalc.md`, `traces/verify-map-taxsim.md` | Review of each input map; the Tax-Calculator reviewer rebuilt the map independently and reproduced all four lines |
| `traces/fix-maps.md` | What the builder changed in the maps after those reviews, and what moved |
| `traces/draw-inputs.md` | What each of the 23 inputs that only the larger draw states does in each model |
| `traces/draw-maps.md` | What the builder changed to carry those inputs, each choice it made with the alternative, the proof that the board's 100 households did not move, and the draw's unexplained cells |
| `traces/builder-2.md` | What a second builder changed after the blind second maps' comparison (map version 2026-11-11.1): each choice with its alternative, and every board answer, input and note that moved |

In these files `SCRATCH` is an agent's scratch directory (not kept), and "the lead" is the session
that ran the comparison.
