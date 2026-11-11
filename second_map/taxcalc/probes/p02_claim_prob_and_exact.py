"""Probe 02: (a) do default settings drop EITC/ACTC at random for hand-built records?
(b) does the reform eitc/actc_claim_prob_scale=9e99 switch that off?
(c) what does exact_calculations change for a CTC phase-out case?
Ten identical records: single parent, 1 child, $40,000 wages (EITC in phase-out, about $1,853)."""
import pandas as pd, numpy as np, taxcalc as tc
rows = []
for i in range(10):
    rows.append(dict(RECID=i+1, MARS=4, e00200=40000., e00200p=40000., age_head=30,
                     EIC=1, n24=1, XTOT=2, nu18=1, n21=1))
# CTC phase-out case: MFJ, AGI 401,234 -> excess 1,234 -> exact rounds to 2,000 ($100 cut) vs $61.70 smooth
rows.append(dict(RECID=11, MARS=2, e00200=401234., e00200p=401234., age_head=40, age_spouse=40,
                 n24=1, XTOT=3, nu18=1, n21=2))
df = pd.DataFrame(rows)
def run(exact, reform):
    pol = tc.Policy()
    if reform:
        pol.implement_reform({'eitc_claim_prob_scale': {2026: 9e99}, 'actc_claim_prob_scale': {2026: 9e99}})
    rec = tc.Records(data=df.copy(), start_year=2026, gfactors=None, weights=None, exact_calculations=exact)
    calc = tc.Calculator(policy=pol, records=rec)
    calc.calc_all()
    return calc.dataframe(['RECID', 'c00100', 'eitc', 'c11070', 'c07220', 'credit_claim_urn'])
for exact in (False, True):
    for reform in (False, True):
        out = run(exact, reform)
        print(f'--- exact={exact} reform(claim always)={reform}')
        print(out.to_string(index=False))
