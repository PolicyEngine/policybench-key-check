"""Probe 03: check map.py's statute computations against the IRS's own worked lines.

(a) IRC 219(g) reduced IRA limit (map.ira_reduced_limit) against Pub 590-A (2025)
    Worksheet 1-2 Examples 1 and 2 (sources/p590a.txt:1143-1150, 1216-1275, 1127-1136, 1281-1330),
    using the 2025 ranges printed there, and against the worksheet's own procedure on a grid.
(b) Schedule SE for one person (map.se_tax_own) against the engine's setax for a one-person
    SE record, and the 162(l) limit for household 038.
(c) Pub 936 Table 1 lines 11-15 for 049 and 120.
"""
import math
import os
import sys

import numpy as np
import pandas as pd
import taxcalc as tc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map as M  # noqa: E402


def worksheet_1_2(dollar, magi, start, rng, pct):
    """Pub 590-A Worksheet 1-2 lines 1-4: line 3 = top - MAGI; line 4 = line 3 x pct,
    rounded UP to the next multiple of $10, at least $200."""
    top = start + rng
    if magi >= top:
        return 0.0
    line3 = top - magi
    if line3 >= rng:
        return dollar
    line4 = math.ceil(round(line3 * pct, 6) / 10.0) * 10.0
    return max(200.0, line4)


print('(a) IRC 219(g) reduced limit vs Pub 590-A Worksheet 1-2')
ex2 = M.ira_reduced_limit(7000.0, 238500.0, 236000.0, 10000.0)
print(f'  Example 2 (spouse covered, 2025 range 236,000-246,000, MAGI 238,500): map {ex2:.2f}; '
      f'printed line 4 = 5,250 -> {"MATCH" if ex2 == 5250 else "DIFF"}')
ex1 = M.ira_reduced_limit(7000.0, 126500.0, 126000.0, 20000.0)
ws1 = worksheet_1_2(7000.0, 126500.0, 126000.0, 20000.0, 0.35)
print(f'  Example 1 (covered, MFJ, 2025 range 126,000-146,000, MAGI 126,500): map {ex1:.2f}; '
      f'worksheet rule (19,500 x 35% = 6,825, "not a multiple of $10" -> round up) {ws1:.2f}; '
      f'printed example line 4 = 6,825 (the illustration does not apply its own rounding rule; '
      f'statute 219(g)(2)(C): reduction 175 rounded down to 170 -> 6,830)')
# grid: statute form (dollar - floor10(reduction)) == worksheet form (ceil10(remaining x pct)), 2026 amounts
bad = 0
for dollar, (start, rng) in [(7500.0, M.IRA_PO_SINGLE), (8600.0, M.IRA_PO_SINGLE),
                             (7500.0, M.IRA_PO_JOINT_ACTIVE), (8600.0, M.IRA_PO_JOINT_ACTIVE),
                             (7500.0, M.IRA_PO_SPOUSE_ACTIVE), (8600.0, M.IRA_PO_SPOUSE_ACTIVE)]:
    pct = dollar / rng
    for magi in np.arange(start - 50, start + rng + 50, 7.31):
        a = M.ira_reduced_limit(dollar, float(magi), start, rng)
        b = worksheet_1_2(dollar, float(magi), start, rng, pct)
        if abs(a - b) > 0.005:
            bad += 1
print(f'  2026 grid, statute form vs worksheet form: {bad} disagreements')

print('(b) Schedule SE: map.se_tax_own vs engine setax')
rows = []
for i, sey in enumerate([15525.0, 433.0, 432.0, 4198.0, 200000.0]):
    rows.append(dict(RECID=i + 1, MARS=1, age_head=40, e00900=sey, e00900p=sey))
rows.append(dict(RECID=9, MARS=1, age_head=40, e00900=50000.0, e00900p=50000.0,
                 e00200=150000.0, e00200p=150000.0))
df = pd.DataFrame(rows).fillna(0.0)
pol = tc.Policy()
rec = tc.Records(data=df, start_year=2026, gfactors=None, weights=None, exact_calculations=True)
calc = tc.Calculator(policy=pol, records=rec)
calc.calc_all()
out = calc.dataframe(['RECID', 'setax', 'c03260'])
for r, o in zip(rows, out.itertuples()):
    own = M.se_tax_own(r['e00900p'], r.get('e00200p', 0.0))
    print(f'  SE profit {r["e00900p"]:>10,.2f} wages {r.get("e00200p", 0.0):>10,.0f}: engine setax {o.setax:10.2f}  map {own:10.2f}  '
          f'{"MATCH" if abs(own - o.setax) < 0.01 else "DIFF"}')
lim = 15525.0 - 0.5 * M.se_tax_own(15525.0, 7468.0)
print(f'  038 IRC 162(l)(2)(A) limit: 15,525 - half SE tax = {lim:.2f}; premiums 100 -> deduction 100')

print('(c) Pub 936 Table 1 (p936.txt:899-952)')
for case, interest, bal in [('049', 2743.0, 1000000.0), ('120', 3744.0, 794797.0 + 205202.0)]:
    line11 = 750000.0
    line12 = bal
    line13 = round(line11 / line12, 3)
    print(f'  {case}: line 11 {line11:,.0f}; line 12 (average balance) {line12:,.0f}; line 13 = {line13:.3f}; '
          f'line 14 (interest) {interest:,.2f}; line 15 deductible = {interest * line13:,.2f}')
