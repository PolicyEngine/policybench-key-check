## Causes that would change a scored answer

Two scored outputs hold a committed answer that, on the entries above, the law or the prompt rule does not support. Each proposal gives the answer that would follow; this repo changes nothing on the board, and every entry stays open.

| Case | Line | Committed key | Answer that would follow | Cause | How this repo got the answer |
|---|---|---:|---:|---|---|
| 068 | tax before refundable credits | 1,910.02 | 14,728.38 | `shared-scholarship-not-income` | Tax-Calculator counterfactual run with the $73,000 of educational assistance as ordinary income; this repo did not run policyengine-us on it |
| 082 | tax before refundable credits | 9,579.77 | 9,564.92 | `shared-state-tax-refund-counted-in-full` | Tax-Calculator counterfactual run with the $67.50 refund out of income (67.50 at 22% = 14.85) |

- **068.** The key's answer stands reproduced by a run of another lineage (Tax-Calculator and TAXSIM give it), and this account contests it: every run leaves the scholarship out of income, and the prompt rule makes the exclusion's conditions (degree candidacy, use for tuition) false.
- **082.** The key's answer stands reproduced by a run of another lineage (Tax-Calculator gives it), and this account contests it: the board's own alternative reading for its excluded refund outputs makes none of the refund income, and the board scores 082 on the other reading. TAXSIM, which also counts the refund, would fall by the same 14.85 and still exceed the others by the 154.00 of `taxsim-no-nonitemizer-charitable-deduction`.

### Scored answers that rest on an open reading

No proposal follows for these; each depends on a reading this account leaves open or decides for the key.

- **042** (2,361.96, reproduced by a run of another lineage): if the $70.94 of qualified BDC income sits outside the stated dividends, the answer would be 2,377.71 (`shared-bdc-income-not-added`).
- **076** (19,611.80, resting on one model, and contested between readings): the key and policyengine-us deduct 20% of the rent as qualified business income; Tax-Calculator and TAXSIM, through this repo's map, give 19,803.80. This account's position supports the key, on the stated unadjusted basis of qualified property (`map-rental-not-qualified-business-income`).
- **067** (5,616.24, reproduced by a run of another lineage): both readings of "is disabled" give the key's answer (`shared-disabled-member-qualifying-child`).
- The other scored cells that are not all_agree (000, 037, 046, 049, 055, 064, 070, 089, 091, 099, 110 and 122 on tax before refundable credits; 026, 100, 109 and 119 on refundable credits) hold a key answer reproduced by a run of another lineage (Tax-Calculator), and every entry that explains them supports the key: TAXSIM lacks a provision or departs from the law, or this repo's TAXSIM map cannot express a fact.

### Excluded outputs where an entry disputes the key

The board scores none of these, so no proposal follows; the list shows where the key and the entries part.

| Case | Committed key | Answer the entries support | Causes; what stays open |
|---|---:|---:|---|
| 005 | 106,505.90 | 107,198.34 | `key-ira-deducted-without-219g`; the board's own alternative. Open: `shared-net-investment-income-tax-in-line` |
| 020 | 68,056.71 | 70,332.82 | `pe-divorce-year-default` (no alimony deduction under the prompt rule), `key-sales-tax-table-column-shift`; Tax-Calculator's answer. Open: `shared-net-investment-income-tax-in-line`, on which the board excludes the output |
| 052 | 104,211.41 | 104,225.26 | `key-ira-deducted-without-219g`; the board's own alternative. Open: `shared-net-investment-income-tax-in-line` |
| 093 | 8,628.99 | 9,128.99 | `pe-other-dependent-credit-without-dependency-tests`, for the head's return. Open: `shared-head-return-only`, which would add the member's own return |
| 114 | 10,729.61 | 11,265.27 | `pe-medicare-part-b-premium-default`. Open: `shared-state-income-tax-withholding-estimate` |
| 120 | 40,021.82 | 39,935.35 | `key-ira-deducted-without-219g` (+6.50), `pe-net-investment-income-leaves-out-farm-rent` (-92.97), with the refund out of income as the key already holds it. `shared-state-paid-leave-contributions-not-in-salt` (-198.72) and `shared-passive-rental-loss-allowed` (+124.69) would move it further. Open: `shared-state-income-tax-withholding-estimate` |
| 062 | 0.00 | 4,328.39 | `shared-survivor-benefits-not-taxable`; the board's own alternative |
| 033, 078, 117 | 3,818.15; 24,164.46; 24,961.34 | 3,788.99; 23,772.80; 24,391.80 | `shared-state-tax-refund-counted-in-full`; the board's own alternatives (Tax-Calculator reproduces 117's to the cent) |
| 002, 107, 121 | 0.00 | 0.00 | `shared-disability-benefits-taxable`: the key holds the answer the prompt rule supports, and policyengine-us, Tax-Calculator and TAXSIM contest it |
