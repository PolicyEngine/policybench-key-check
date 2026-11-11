#!/usr/bin/env python
"""Blind second input map: PolicyBench's 100 benchmark households -> Tax-Calculator 6.9.0,
tax year 2026.

Run with the engine's interpreter, from any directory:
    REPO/envs/tc690/bin/python map.py

Reads  ../input/board/scenarios.csv and ../input/board/state_and_local_tax_2026.csv
Writes (into this folder):
  inputs_2026.csv               engine inputs of the final main pass (R5), one row per return
  inputs_payroll_pass_2026.csv  engine inputs of the payroll pass (R6); differs only in wages
  passes_2026.csv               what the earlier passes R1-R4 computed, and the limited amounts
  returns_2026.csv              engine outputs per return (main pass R5, payroll pass R6)
  answers_2026.csv              the board's four quantities per household
  notes.csv                     readings, statute computations, unexpressed facts, engine behaviours
  variants_2026.csv             the four quantities under each alternative reading, where they move

Every statutory amount below cites the saved source file and line in sources/.
README.md explains each reading; probes/ holds the engine probes.
"""
import json
import math
import os
import sys
import warnings

import numpy as np
import pandas as pd
import taxcalc as tc

warnings.filterwarnings('ignore')
pd.set_option('display.width', 250)

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.normpath(os.path.join(HERE, '..', 'input', 'board'))
YEAR = 2026

# ---------------------------------------------------------------------------
# 2026 amounts the engine takes as already limited, computed here from statute
# ---------------------------------------------------------------------------
K401_LIMIT = 24500.0          # IRC 402(g)(1)(B) as adjusted; sources/n-25-67.txt:37-41
K401_CATCHUP_50 = 8000.0      # IRC 414(v)(2)(B)(i); n-25-67.txt:46
K401_CATCHUP_60_63 = 11250.0  # IRC 414(v)(2)(E)(i); n-25-67.txt:51
IRA_LIMIT = 7500.0            # IRC 219(b)(5)(A); n-25-67.txt:164
IRA_CATCHUP_50 = 1100.0       # IRC 219(b)(5)(B); n-25-67.txt:166
IRA_PO_SINGLE = (81000.0, 10000.0)         # IRC 219(g)(2)(A)(ii), (g)(3)(B)(ii); n-25-67.txt:168-194
IRA_PO_JOINT_ACTIVE = (129000.0, 20000.0)  # IRC 219(g)(3)(B)(i); n-25-67.txt:171-173,188-190
IRA_PO_SPOUSE_ACTIVE = (242000.0, 10000.0)  # IRC 219(g)(7); n-25-67.txt:177-179,190-192
ROTH_PO = {1: (153000.0, 15000.0), 4: (153000.0, 15000.0),
           2: (242000.0, 10000.0)}         # IRC 408A(c)(3); n-25-67.txt:197-213
SAVERS_TIERS = {2: (48500.0, 52500.0, 80500.0),   # IRC 25B(b); n-25-67.txt:140-145
                4: (36375.0, 39375.0, 60375.0),   # n-25-67.txt:147-153
                1: (24250.0, 26250.0, 40250.0)}   # n-25-67.txt:155-159
SAVERS_CAP = 2000.0           # IRC 25B(a); sources/usc26_25B.txt
SLI_CAP = 2500.0              # IRC 221(b)(1); sources/usc26_221.txt
SLI_PO = {1: (85000.0, 15000.0), 4: (85000.0, 15000.0),
          2: (175000.0, 30000.0)}           # IRC 221(b)(2)(B); rp-25-32.txt:1003-1012
EDUCATOR_CAP = 350.0          # IRC 62(a)(2)(D) as adjusted; rp-25-32.txt:749-759
HSA_SELF = 4400.0             # IRC 223(b)(2)(A); rp-25-19.txt:38-41
HSA_FAMILY = 8750.0           # IRC 223(b)(2)(B); rp-25-19.txt:42-45
HSA_CATCHUP_55 = 1000.0       # IRC 223(b)(3)(B); sources/usc26_223.txt
MORTGAGE_LIMIT = 750000.0     # IRC 163(h)(3)(F)(i)(II); p936.txt:899-952 (Table 1)
MORTGAGE_LIMIT_GRANDFATHERED = 1000000.0  # IRC 163(h)(3)(F)(i)(III) (variant only)
PASSIVE_ALLOWANCE = 25000.0   # IRC 469(i)(2); sources/usc26_469.txt
PASSIVE_PO_START = 100000.0   # IRC 469(i)(3)(A)
EARLY_DIST_RATE = 0.10        # IRC 72(t)(1); sources/usc26_72.txt
MEDICAL_FLOOR = 0.075         # IRC 213(a), used for the 72(t)(2)(B) exception
SE_FRAC = 0.9235              # IRC 1402(a)(12); engine seca_frac, calcfunctions.py:231
SE_FLOOR = 400.0              # IRC 1402(b)(2); engine SECA_Earnings_deminimus (probe p01)
SS_WAGE_BASE = 184500.0       # engine SS_Earnings_c 2026 (probe p01)

# ---------------------------------------------------------------------------
# Readings. MAIN is the map; each VARIANT flips one reading (variants_2026.csv)
# ---------------------------------------------------------------------------
MAIN = dict(
    otc_in_medical=False,             # IRC 213(b): only prescribed drugs/insulin
    auto_loan_qualified=True,         # stated auto loan interest is Sch 1-A qualified interest
    rental_with_ubia_is_qbi=False,    # residential rental QBI has no engine input (unexpressed)
    misc_income_as_e01200=False,      # no engine input for Sch 1 line 8z other income
    ss_dependents_to_child=False,     # SS dependents benefits are income of the person stated on
    alimony_pre2019=False,            # post-2018 instrument: not deductible / not income
    mortgage_grandfathered=False,     # debt incurred after 12/15/2017: $750,000 limit
    hsa_family_coverage=False,        # one-person return -> self-only HSA limit
    educational_assistance_taxable=False,  # IRC 117 qualified scholarship, excluded
    ssdi_is_72t_disability=True,      # SSDI receipt meets IRC 72(m)(7) disability
    passive_active_participation=True,  # IRC 469(i) active participation assumed
    tips_inside_wages=True,           # employment_income includes tips (glossary)
    disability_benefits_fica=False,   # employer disability pay not FICA wages
    k401_pro_rata=False,              # traditional deferrals fill the 402(g) limit first
    disability_unearned=False,        # under 65: line 1h wages (i1040gi.txt:1536-1544), not pension
)
VARIANTS = {
    'otc_in_medical': dict(otc_in_medical=True),
    'auto_loan_not_qualified': dict(auto_loan_qualified=False),
    'rental_with_ubia_is_qbi': dict(rental_with_ubia_is_qbi=True),
    'misc_income_as_e01200': dict(misc_income_as_e01200=True),
    'ss_dependents_to_child': dict(ss_dependents_to_child=True),
    'alimony_pre2019': dict(alimony_pre2019=True),
    'mortgage_grandfathered': dict(mortgage_grandfathered=True),
    'hsa_family_coverage': dict(hsa_family_coverage=True),
    'educational_assistance_taxable': dict(educational_assistance_taxable=True),
    'ssdi_not_72t_disability': dict(ssdi_is_72t_disability=False),
    'no_passive_active_participation': dict(passive_active_participation=False),
    'tips_on_top_of_wages': dict(tips_inside_wages=False),
    'disability_benefits_fica': dict(disability_benefits_fica=True),
    'k401_pro_rata': dict(k401_pro_rata=True),
    'disability_benefits_unearned': dict(disability_unearned=True),
}

# Facts with no federal income or federal payroll tax role, and why (checked per key so that
# no stated fact is dropped silently: an unknown key stops the program).
NO_EFFECT = {
    'bank_account_assets': 'asset, not income',
    'stock_assets': 'asset, not income',
    'household_vehicles_value': 'asset, not income',
    'auto_loan_balance': 'balance; only the interest bears on Sch 1-A',
    'hourly_wage': 'rate; annual wages are stated',
    'hours_worked_last_week': 'hours; annual wages are stated',
    'is_paid_hourly': 'pay basis; annual wages are stated',
    'weeks_unemployed': 'search weeks; no federal tax role',
    'is_pregnant': 'no federal tax role (an unborn child is not a dependent)',
    'pre_subsidy_rent': 'no federal deduction for rent',
    'employer_sponsored_insurance_premiums': 'employer-paid, excluded from income (IRC 106), not the employee\'s medical expense',
    'has_champva_health_coverage_at_interview': 'coverage flag; no premium tax credit in these outputs',
    'has_indian_health_service_coverage_at_interview': 'coverage flag',
    'has_other_means_tested_health_coverage_at_interview': 'coverage flag',
    'receives_wic': 'WIC is excluded general-welfare benefit',
    'receives_housing_assistance': 'housing assistance is excluded general-welfare benefit',
    'spm_unit_energy_subsidy': 'energy assistance is excluded general-welfare benefit',
    'child_support_expense': 'not deductible (IRC 71 repealed; child support never deductible)',
    'child_support_received': 'not income',
    'financial_assistance': 'gift from outside the household, excluded (IRC 102)',
    'veterans_benefits': 'excluded (38 U.S.C. 5301)',
    'workers_compensation': 'excluded (IRC 104(a)(1); sources/usc26_104.txt)',
    'tax_exempt_ira_distributions': 'qualified Roth distribution, excluded (IRC 408A(d)(1))',
    'farm_income': 'Schedule J election amount; duplicates farm_operations_income, which is entered',
    'is_surviving_spouse': 'no flagged surviving spouse has a dependent child, so no IRC 2(a) status',
    'is_unmarried_partner_of_household_head': 'flag on a lone head; files single',
    'is_tax_unit_head': 'used to build the return',
    'is_tax_unit_spouse': 'used to build the return',
    'attends_eligible_educational_institution_for_american_opportunity_credit': 'AOTC needs qualified expenses; none stated',
    'is_enrolled_at_least_half_time_for_american_opportunity_credit': 'AOTC needs qualified expenses; none stated; half-time is not full-time for 25B or 1(g)',
    'is_pursuing_credential_for_american_opportunity_credit': 'AOTC needs qualified expenses; none stated',
    'has_american_opportunity_credit_1098_t_or_exception': 'AOTC needs qualified expenses; none stated',
    'has_american_opportunity_credit_institution_ein': 'AOTC needs qualified expenses; none stated',
    'is_disabled': 'used for qualifying-child age test, 72(t) and Sch R checks',
}
HANDLED_PERSON = {
    'alimony_expense', 'alimony_income', 'charitable_cash_donations', 'charitable_non_cash_donations',
    'disability_benefits', 'educational_assistance', 'educator_expense', 'estate_income',
    'farm_operations_income', 'farm_rent_income', 'fsla_overtime_premium', 'has_esi',
    'health_insurance_premiums_without_medicare_part_b', 'home_mortgage_interest', 'is_blind',
    'long_term_capital_gains', 'miscellaneous_income', 'non_qualified_dividend_income',
    'non_sch_d_capital_gains', 'other_health_insurance_premiums', 'other_medical_expenses',
    'over_the_counter_health_expenses', 'partnership_s_corp_income', 'partnership_se_income',
    'qualified_bdc_income', 'qualified_dividend_income', 'qualified_reit_and_ptp_income',
    'real_estate_taxes', 'rental_income', 'roth_401k_contributions_desired',
    'roth_ira_contributions_desired', 'salt_refund_income', 'self_employment_income',
    'short_term_capital_gains', 'social_security_dependents', 'social_security_disability',
    'social_security_retirement', 'social_security_survivors',
    'sstb_self_employment_income_before_lsr', 'sstb_unadjusted_basis_qualified_property',
    'student_loan_interest', 'survivor_benefits', 'tax_exempt_interest_income',
    'tax_exempt_private_pension_income', 'taxable_401k_distributions', 'taxable_403b_distributions',
    'taxable_interest_income', 'taxable_ira_distributions', 'taxable_private_pension_income',
    'tip_income', 'traditional_401k_contributions_desired', 'traditional_ira_contributions_desired',
    'unadjusted_basis_qualified_property', 'unemployment_compensation',
    'unreimbursed_business_employee_expenses',
}
HANDLED_TU = {'first_home_mortgage_balance', 'second_home_mortgage_balance',
              'first_home_mortgage_interest', 'second_home_mortgage_interest',
              'health_savings_account_ald', 'domestic_production_ald'}
HANDLED_HH = {'auto_loan_interest'}
HANDLED_SPM = {'spm_unit_pre_subsidy_childcare_expenses'}

# engine inputs written for every return (Tax-Calculator names, records_variables.json "read")
INT_VARS = ['RECID', 'MARS', 'DSI', 'XTOT', 'EIC', 'n24', 'nu06', 'nu13', 'nu18', 'n1820', 'n21',
            'elderly_dependents', 'f2441', 'age_head', 'age_spouse', 'blind_head', 'blind_spouse',
            'PT_SSTB_income']
FLOAT_VARS = ['e00200', 'e00200p', 'e00200s', 'pencon_p', 'pencon_s',
              'e00300', 'e00400', 'e00600', 'e00650', 'e00700', 'e00800',
              'e00900', 'e00900p', 'e00900s', 'e01100', 'e01200', 'e01400', 'e01500', 'e01700',
              'e02000', 'e02100', 'e02100p', 'e02100s', 'e02300', 'e02400', 'e26270', 'e27200',
              'k1bx14p', 'k1bx14s', 'p22250', 'p23250',
              'e03150', 'e03210', 'e03220', 'e03240', 'e03270', 'e03290', 'e03500',
              'e07240', 'e09900', 'e17500', 'e18400', 'e18500', 'e19200', 'e19800', 'e20100',
              'e20400', 'e32800', 'PT_ubia_property', 'PT_binc_w2_wages',
              'overtime_income', 'tip_income', 'auto_loan_interest']
OUT_VARS = ['RECID', 'c00100', 'c02500', 'c02900', 'c03260', 'earned', 'setax', 'ptax_was',
            'ptax_er_p', 'ptax_er_s', 'ptax_amc', 'standard', 'c04470', 'c17000', 'c18300',
            'c19200', 'c19700', 'senior_deduction', 'overtime_income_deduction',
            'tip_income_deduction', 'auto_loan_interest_deduction', 'qbided', 'c04800', 'taxbc',
            'c09600', 'c05800', 'c07180', 'c07200', 'c07220', 'odc', 'c07240', 'c07100', 'niit',
            'othertaxes', 'c09200', 'eitc', 'c11070', 'c10960', 'CDCC_refund', 'refund', 'iitax',
            'payrolltax']


def num(d, k):
    v = d.get(k, 0.0)
    if v is None or isinstance(v, bool):
        return 0.0
    return float(v)


def flag(d, k):
    return d.get(k, False) is True


def r2(x):
    return float(np.round(x + 0.0, 2))


class Notes:
    def __init__(self, on):
        self.on = on
        self.rows = []

    def add(self, case, group, kind, text):
        if self.on:
            self.rows.append(dict(case_id=case, quantity_group=group, kind=kind, text=text))


# ---------------------------------------------------------------------------
# persons
# ---------------------------------------------------------------------------
def load_people(j):
    people = []
    for p in j['adults'] + j['children']:
        name = p['name']
        role = ('head' if name == 'head' else 'spouse' if name == 'spouse'
                else 'dependent' if name.startswith('dependent') else 'child')
        f = dict(p.get('inputs', {}))
        people.append(dict(name=name, role=role, age=int(p['age']),
                           emp=float(p.get('employment_income', 0.0) or 0.0), f=f))
    heads = [q for q in people if q['role'] == 'head']
    assert len(heads) == 1 and flag(heads[0]['f'], 'is_tax_unit_head')
    for q in people:
        assert flag(q['f'], 'is_tax_unit_spouse') == (q['role'] == 'spouse'), (j['id'], q['name'])
    return people


def check_keys(j):
    for q in j['adults'] + j['children']:
        for k in q.get('inputs', {}):
            assert k in HANDLED_PERSON or k in NO_EFFECT, ('unhandled person fact', j['id'], k)
    for k in j.get('tax_unit_inputs', {}):
        assert k in HANDLED_TU or k in NO_EFFECT, ('unhandled tax-unit fact', j['id'], k)
    for k in j.get('household_inputs', {}):
        assert k in HANDLED_HH or k in NO_EFFECT, ('unhandled household fact', j['id'], k)
    for k in j.get('spm_unit_inputs', {}):
        assert k in HANDLED_SPM or k in NO_EFFECT, ('unhandled spm fact', j['id'], k)


def se_tax_own(sey, w2_ss_wages):
    """Schedule SE for one person (IRC 1401, 1402): used only to size limits that depend on
    earned income (IRC 162(l)(2)(A), 219(f)(1)/401(c)(2)); the engine computes the tax itself."""
    net = max(0.0, sey * SE_FRAC)
    if net < SE_FLOOR:
        net = 0.0
    ss_room = max(0.0, SS_WAGE_BASE - min(SS_WAGE_BASE, w2_ss_wages))
    return 0.124 * min(net, ss_room) + 0.029 * net


def person_items(q, opts):
    f, age = q['f'], q['age']
    it = {}
    tips = num(f, 'tip_income')
    gross = q['emp'] + (0.0 if opts['tips_inside_wages'] else tips)
    it['gross_wages'] = gross
    # 401(k) elective deferrals: IRC 402(g)(1) limit plus 414(v) catch-up, and never above pay
    lim = K401_LIMIT + (K401_CATCHUP_60_63 if 60 <= age <= 63 else K401_CATCHUP_50 if age >= 50 else 0.0)
    td = num(f, 'traditional_401k_contributions_desired')
    rd = num(f, 'roth_401k_contributions_desired')
    cap = min(lim, gross)
    if opts['k401_pro_rata'] and td + rd > cap:
        t = cap * td / (td + rd)
        r = cap - t
    else:
        t = min(td, cap)
        r = max(0.0, min(rd, cap - t))
    it.update(k401_lim=lim, k401_trad_des=td, k401_roth_des=rd, k401_trad=t, k401_roth=r)
    it['box1_wages'] = gross - t
    it['active_participant'] = (t + r) > 0
    dis = num(f, 'disability_benefits')
    # Form 1040 line 1h before minimum retirement age, lines 5a/5b after it
    # (sources/i1040gi.txt:1536-1544, 1821-1826); 65 stands in for the unstated plan age
    under = age < 65 and not opts['disability_unearned']
    it['dis_wages'] = dis if under else 0.0
    it['dis_pension'] = 0.0 if under else dis
    it['se_nonfarm'] = num(f, 'self_employment_income') + num(f, 'sstb_self_employment_income_before_lsr')
    it['sstb'] = num(f, 'sstb_self_employment_income_before_lsr') != 0 or num(f, 'sstb_unadjusted_basis_qualified_property') > 0
    it['nonsstb_business'] = (num(f, 'self_employment_income') != 0 or num(f, 'farm_operations_income') != 0
                              or num(f, 'unadjusted_basis_qualified_property') > 0)
    it['farm'] = num(f, 'farm_operations_income')
    it['k1bx14'] = num(f, 'partnership_se_income')
    it['partnership'] = num(f, 'partnership_s_corp_income')
    it['rental'] = num(f, 'rental_income')
    it['farmrent'] = num(f, 'farm_rent_income')
    it['estate'] = num(f, 'estate_income')
    it['ubia'] = num(f, 'unadjusted_basis_qualified_property') + num(f, 'sstb_unadjusted_basis_qualified_property')
    it['ubia_nonsstb'] = num(f, 'unadjusted_basis_qualified_property')
    it['interest'] = num(f, 'taxable_interest_income')
    it['xinterest'] = num(f, 'tax_exempt_interest_income')
    it['qdiv'] = num(f, 'qualified_dividend_income')
    it['odiv'] = (num(f, 'qualified_dividend_income') + num(f, 'non_qualified_dividend_income')
                  + num(f, 'qualified_bdc_income') + num(f, 'qualified_reit_and_ptp_income'))
    it['stcg'] = num(f, 'short_term_capital_gains')
    it['ltcg'] = num(f, 'long_term_capital_gains')
    it['cgdist'] = max(0.0, num(f, 'non_sch_d_capital_gains'))
    it['ira_dist'] = num(f, 'taxable_ira_distributions')
    it['plan_dist'] = num(f, 'taxable_401k_distributions') + num(f, 'taxable_403b_distributions')
    it['pens_taxable'] = (num(f, 'taxable_private_pension_income') + it['plan_dist']
                          + it['dis_pension'] + num(f, 'survivor_benefits'))
    it['pens_total'] = it['pens_taxable'] + num(f, 'tax_exempt_private_pension_income')
    it['ss'] = (num(f, 'social_security_retirement') + num(f, 'social_security_disability')
                + num(f, 'social_security_survivors') + num(f, 'social_security_dependents'))
    it['ss_dependents'] = num(f, 'social_security_dependents')
    it['ssdi'] = num(f, 'social_security_disability')
    it['unemp'] = num(f, 'unemployment_compensation')
    it['salt_refund'] = num(f, 'salt_refund_income')
    it['alimony_rec'] = num(f, 'alimony_income')
    it['alimony_paid'] = num(f, 'alimony_expense')
    it['other_income'] = ((num(f, 'miscellaneous_income') if opts['misc_income_as_e01200'] else 0.0)
                          + (num(f, 'educational_assistance') if opts['educational_assistance_taxable'] else 0.0))
    it['sli'] = num(f, 'student_loan_interest')
    it['educator'] = num(f, 'educator_expense')
    it['ube'] = num(f, 'unreimbursed_business_employee_expenses')
    prem_nob = f.get('health_insurance_premiums_without_medicare_part_b')
    it['premiums'] = float(prem_nob) if prem_nob is not None else num(f, 'other_health_insurance_premiums')
    it['medical_other'] = num(f, 'other_medical_expenses')
    it['otc'] = num(f, 'over_the_counter_health_expenses')
    it['re_tax'] = num(f, 'real_estate_taxes')
    it['mort_int'] = num(f, 'home_mortgage_interest')
    it['char_cash'] = num(f, 'charitable_cash_donations')
    it['char_noncash'] = num(f, 'charitable_non_cash_donations')
    it['overtime'] = num(f, 'fsla_overtime_premium')
    it['tips'] = tips
    it['ira_trad_des'] = num(f, 'traditional_ira_contributions_desired')
    it['ira_roth_des'] = num(f, 'roth_ira_contributions_desired')
    it['has_esi'] = flag(f, 'has_esi')
    it['blind'] = flag(f, 'is_blind')
    it['disabled'] = flag(f, 'is_disabled')
    it['misc_income'] = num(f, 'miscellaneous_income')
    it['educ_assist'] = num(f, 'educational_assistance')
    sey = it['se_nonfarm'] + it['farm'] + it['k1bx14']
    it['sey'] = sey
    it['setax_own'] = se_tax_own(sey, gross)
    # IRA compensation, IRC 219(f)(1): box-1 wages plus SE earned income (401(c)(2): net
    # earnings less the 164(f) deduction); a net SE loss does not reduce wages (Pub 590-A).
    it['ira_comp'] = it['box1_wages'] + max(0.0, sey - 0.5 * it['setax_own'])
    own_income = (gross + dis + it['se_nonfarm'] + it['farm'] + it['partnership'] + it['rental']
                  + it['farmrent'] + it['estate'] + it['interest'] + it['xinterest'] + it['odiv']
                  + it['stcg'] + it['ltcg'] + it['cgdist'] + it['ira_dist'] + it['pens_total']
                  + it['ss'] + it['unemp'] + it['salt_refund'] + it['alimony_rec'] + it['misc_income'])
    it['has_income'] = abs(own_income) > 0
    return it


# ---------------------------------------------------------------------------
# returns
# ---------------------------------------------------------------------------
def is_qualifying_child(dep, filers):
    """IRC 152(c): relationship, abode, support and joint-return tests taken as met for every
    listed dependent; age test (c)(3): under 19 and younger than the filer, or permanently and
    totally disabled at any age (sources/usc26_152.txt)."""
    younger = dep['age'] < max(q['age'] for q in filers)
    return (dep['age'] < 19 and younger) or flag(dep['f'], 'is_disabled')


def blank_inputs():
    d = {k: 0 for k in INT_VARS}
    d.update({k: 0.0 for k in FLOAT_VARS})
    return d


def build_return(case, kind, filers, deps, items, hh, opts, notes, main):
    """filers: [primary] or [primary, spouse]; deps: dependents claimed on this return."""
    d = blank_inputs()
    p = filers[0]
    s = filers[1] if len(filers) > 1 else None
    ip = items[p['name']]
    is_ = items[s['name']] if s else None
    d['MARS'] = 2 if s else (4 if deps else 1)
    d['DSI'] = 0 if main else 1
    d['age_head'] = p['age']
    d['age_spouse'] = s['age'] if s else 0
    d['blind_head'] = int(ip['blind'])
    d['blind_spouse'] = int(is_['blind']) if s else 0
    qcs = [x for x in deps if is_qualifying_child(x, filers)]
    assert len(qcs) == len(deps), ('dependent who is not a qualifying child', case)
    d['XTOT'] = len(filers) + len(deps)
    d['EIC'] = min(3, len(qcs))
    d['n24'] = sum(1 for x in qcs if x['age'] < 17)
    d['nu06'] = sum(1 for x in deps if x['age'] < 6)
    d['nu13'] = sum(1 for x in deps if x['age'] < 13)
    everyone = filers + deps
    d['nu18'] = sum(1 for x in everyone if x['age'] < 18)
    d['n1820'] = sum(1 for x in everyone if 18 <= x['age'] <= 20)
    d['n21'] = sum(1 for x in everyone if x['age'] >= 21)
    d['elderly_dependents'] = sum(1 for x in deps if x['age'] >= 65)
    d['f2441'] = sum(1 for x in deps if x['age'] < 13)   # IRC 21(b)(1)(A)

    def tot(key):
        return ip[key] + (is_[key] if s else 0.0)

    # wages net of traditional 401(k) deferrals (records_variables.json e00200p)
    d['pencon_p'] = ip['k401_trad']
    d['pencon_s'] = is_['k401_trad'] if s else 0.0
    d['e00200p'] = ip['box1_wages'] + ip['dis_wages']
    d['e00200s'] = (is_['box1_wages'] + is_['dis_wages']) if s else 0.0
    d['e00900p'] = ip['se_nonfarm']
    d['e00900s'] = is_['se_nonfarm'] if s else 0.0
    d['e02100p'] = ip['farm']
    d['e02100s'] = is_['farm'] if s else 0.0
    d['k1bx14p'] = ip['k1bx14']
    d['k1bx14s'] = is_['k1bx14'] if s else 0.0
    d['e00300'] = tot('interest')
    d['e00400'] = tot('xinterest')
    d['e00600'] = tot('odiv')
    d['e00650'] = tot('qdiv')
    d['e00700'] = tot('salt_refund')
    d['e00800'] = tot('alimony_rec')
    d['e01100'] = tot('cgdist')
    d['e01200'] = tot('other_income')
    d['e01400'] = tot('ira_dist')
    d['e01500'] = tot('pens_total')
    d['e01700'] = tot('pens_taxable')
    d['e02300'] = tot('unemp')
    d['e02400'] = tot('ss')
    d['e26270'] = tot('partnership')
    d['p22250'] = tot('stcg')
    d['p23250'] = tot('ltcg')
    d['e03220'] = sum(min(EDUCATOR_CAP, items[q['name']]['educator']) for q in filers)
    d['e03500'] = tot('alimony_paid')
    d['overtime_income'] = tot('overtime')
    d['tip_income'] = tot('tips')
    biz = [items[q['name']] for q in filers]
    d['PT_SSTB_income'] = int(any(b['sstb'] for b in biz) and not any(b['nonsstb_business'] for b in biz))
    d['PT_ubia_property'] = tot('ubia')
    meta = dict(case=case, record=kind, filers=[q['name'] for q in filers],
                deps=[q['name'] for q in deps])
    # passive activities (rental real estate and farm rental), resolved in the pass loop
    meta['rental'] = tot('rental')
    meta['farmrent'] = tot('farmrent')
    meta['nonpassive_sche'] = tot('estate') + tot('partnership')
    meta['farmrent_qbi'] = sum(items[q['name']]['farmrent'] for q in filers if items[q['name']]['ubia_nonsstb'] > 0)
    meta['rental_qbi'] = (sum(items[q['name']]['rental'] for q in filers if items[q['name']]['ubia_nonsstb'] > 0)
                          if opts['rental_with_ubia_is_qbi'] else 0.0)
    meta['dis_wages_p'] = ip['dis_wages']
    meta['dis_wages_s'] = is_['dis_wages'] if s else 0.0
    if main:
        # household-level deductions and credits sit on the main return
        hp = [items[q['name']] for q in hh['people']]
        # SE health insurance, IRC 162(l): SE person, no employer-subsidised plan for the
        # filer or spouse (has_esi false for both), premiums for filer, spouse and dependents,
        # limited to SE earned income from the business (net profit less half SE tax).
        se_health = 0.0
        se_people = [q for q in filers if items[q['name']]['sey'] > 0]
        if se_people and not any(items[q['name']]['has_esi'] for q in filers):
            prem = sum(x['premiums'] for x in hp)
            limit = sum(max(0.0, items[q['name']]['sey'] - 0.5 * items[q['name']]['setax_own']) for q in se_people)
            se_health = min(prem, limit)
            if se_health > 0:
                notes.add(case, 'income_tax', 'computed_from_statute',
                          f'SE health insurance deduction e03270 = min(premiums {prem:.2f}, SE earned income {limit:.2f}) = {se_health:.2f} (IRC 162(l)(1),(2)(A); no filer or spouse has employer coverage, so 162(l)(2)(B) does not bar it); these premiums leave the medical deduction.')
        d['e03270'] = se_health
        medical = sum(x['medical_other'] + x['premiums'] + (x['otc'] if opts['otc_in_medical'] else 0.0) for x in hp) - se_health
        d['e17500'] = max(0.0, medical)
        d['e18400'] = hh['salt']
        d['e18500'] = sum(x['re_tax'] for x in hp)
        d['e19800'] = sum(x['char_cash'] for x in hp)
        d['e20100'] = sum(x['char_noncash'] for x in hp)
        d['e20400'] = sum(x['ube'] for x in hp)
        d['e32800'] = hh['childcare']
        d['e03240'] = hh['dpad']
        d['auto_loan_interest'] = max(0.0, hh['auto_loan_interest']) if opts['auto_loan_qualified'] else 0.0
        # mortgage interest, IRC 163(h)(3); Pub 936 Table 1 (p936.txt:899-952)
        mi = sum(x['mort_int'] for x in hp)
        mi_tu = hh['first_mi'] + hh['second_mi']
        if mi == 0.0:
            mi = mi_tu
        elif mi_tu > 0:
            assert abs(mi - mi_tu) < 2.0, (case, mi, mi_tu)
        bal = hh['first_bal'] + hh['second_bal']
        lim = MORTGAGE_LIMIT_GRANDFATHERED if opts['mortgage_grandfathered'] else MORTGAGE_LIMIT
        ded = mi
        if mi > 0 and bal > lim:
            frac = round(lim / bal, 3)
            ded = mi * frac
            notes.add(case, 'income_tax', 'computed_from_statute',
                      f'Mortgage interest {mi:.2f} on balances {bal:,.0f} > {lim:,.0f}: deductible = interest x round({lim:,.0f}/{bal:,.0f}, 3) = {mi:.2f} x {frac:.3f} = {ded:.2f} (IRC 163(h)(3)(F); Pub 936 Table 1 lines 11-15, sources/p936.txt:899-952). Stated balance used as the average balance; debt read as acquisition debt incurred after 12/15/2017.')
        d['e19200'] = ded
        # HSA, IRC 223(b): self-only limit when the return has one person, else family
        hsa = hh['hsa']
        if hsa > 0:
            family = opts['hsa_family_coverage'] or len(filers) + len(deps) > 1
            hlim = (HSA_FAMILY if family else HSA_SELF) + sum(HSA_CATCHUP_55 for q in filers if q['age'] >= 55)
            d['e03290'] = min(hsa, hlim)
            if hsa > hlim:
                notes.add(case, 'income_tax', 'computed_from_statute',
                          f'HSA deduction stated {hsa:.2f} exceeds the 2026 {"family" if family else "self-only"} limit {hlim:,.0f} (IRC 223(b)(2); rp-25-19.txt:38-45); e03290 = {hlim:,.0f}. A one-person return can only have self-only coverage.')
        # educator expenses cap
        for q in filers:
            e = items[q['name']]['educator']
            if e > 0:
                notes.add(case, 'income_tax', 'computed_from_statute',
                          f'Educator expenses {e:.2f} for {q["name"]} under the 2026 cap of $350 (IRC 62(a)(2)(D); rp-25-32.txt:749-759); e03220 takes it whole.')
    meta['hsa_used'] = d['e03290']
    return d, meta


def build_household(case, j, salt, opts, notes):
    check_keys(j)
    people = load_people(j)
    if opts['ss_dependents_to_child']:
        head = [q for q in people if q['role'] == 'head'][0]
        kids = [q for q in people if q['role'] in ('child', 'dependent')]
        if num(head['f'], 'social_security_dependents') > 0 and kids:
            youngest = min(kids, key=lambda q: q['age'])
            youngest['f']['social_security_dependents'] = head['f'].pop('social_security_dependents')
    items = {q['name']: person_items(q, opts) for q in people}
    tu = j.get('tax_unit_inputs', {})
    hhin = j.get('household_inputs', {})
    spm = j.get('spm_unit_inputs', {})
    hh = dict(people=people, salt=salt,
              childcare=num(spm, 'spm_unit_pre_subsidy_childcare_expenses'),
              dpad=num(tu, 'domestic_production_ald'),
              hsa=num(tu, 'health_savings_account_ald'),
              auto_loan_interest=num(hhin, 'auto_loan_interest'),
              first_bal=num(tu, 'first_home_mortgage_balance'),
              second_bal=num(tu, 'second_home_mortgage_balance'),
              first_mi=num(tu, 'first_home_mortgage_interest'),
              second_mi=num(tu, 'second_home_mortgage_interest'))
    head = [q for q in people if q['role'] == 'head'][0]
    spouse = [q for q in people if q['role'] == 'spouse']
    deps = [q for q in people if q['role'] in ('child', 'dependent')]
    filers = [head] + spouse
    rets = []
    d, meta = build_return(case, 'main', filers, deps, items, hh, opts, notes, main=True)
    rets.append((d, meta))
    for x in deps:
        if items[x['name']]['has_income']:
            dd, mm = build_return(case, 'dependent:' + x['name'], [x], [], items, hh, opts, notes, main=False)
            rets.append((dd, mm))
    return rets, items, people


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------
def run_engine(rows, opts):
    df = pd.DataFrame([r for r in rows])
    for k in INT_VARS:
        df[k] = df[k].astype(int)
    df['e00200'] = df['e00200p'] + df['e00200s']
    df['e00900'] = df['e00900p'] + df['e00900s']
    df['e02100'] = df['e02100p'] + df['e02100s']
    pol = tc.Policy()
    reform = {'eitc_claim_prob_scale': {YEAR: 9e99}, 'actc_claim_prob_scale': {YEAR: 9e99}}
    if opts['alimony_pre2019']:
        reform.update({'ALD_AlimonyPaid_hc': {YEAR: 0.0}, 'AlimonyReceived_frac_in_AGI': {YEAR: 1.0}})
    pol.implement_reform(reform)
    rec = tc.Records(data=df.copy(), start_year=YEAR, gfactors=None, weights=None,
                     exact_calculations=True)
    calc = tc.Calculator(policy=pol, records=rec, verbose=False)
    assert calc.current_year == YEAR
    calc.calc_all()
    out = calc.dataframe(OUT_VARS)
    out.index = df.index
    return df, out


def ira_reduced_limit(dollar, magi, start, rng):
    """IRC 219(g)(2): reduction = dollar x (MAGI - start)/range, rounded down to $10
    ((g)(2)(C)); a positive limit under $200 is raised to $200 ((g)(2)(B)); usc26_219.txt:104-115."""
    if magi <= start:
        return dollar
    if magi >= start + rng:
        return 0.0
    reduction = math.floor(dollar * (magi - start) / rng / 10.0) * 10.0
    lim = dollar - reduction
    if 0 < lim < 200:
        lim = 200.0
    return max(0.0, lim)


def pipeline(households, opts, notes):
    rets = []
    for case, (rr, items, people) in households.items():
        for d, meta in rr:
            meta['items'] = items
            meta['people'] = {q['name']: q for q in people}
            rets.append((d, meta))
    for i, (d, meta) in enumerate(rets):
        d['RECID'] = i + 1

    def rows_with(stage):
        out = []
        for d, meta in rets:
            r = dict(d)
            r.update(stage(d, meta))
            out.append(r)
        return out

    # ---- R1: MAGI for IRC 469(i)(3)(F): no IRA, student-loan or passive-loss deduction;
    #      taxable Social Security removed after the run
    def st1(d, m):
        net = m['rental'] + m['farmrent']
        return dict(e02000=m['nonpassive_sche'] + max(0.0, net), e27200=0.0, e03150=0.0, e03210=0.0)
    _, o1 = run_engine(rows_with(st1), opts)
    for k, (d, m) in enumerate(rets):
        m['magi_469'] = o1.loc[k, 'c00100'] - o1.loc[k, 'c02500']
        net = m['rental'] + m['farmrent']
        if net >= 0:
            allowed = net
        else:
            if opts['passive_active_participation']:
                allowance = max(0.0, PASSIVE_ALLOWANCE - 0.5 * max(0.0, m['magi_469'] - PASSIVE_PO_START))
            else:
                allowance = 0.0
            allowed = -min(-net, allowance)
            notes.add(m['case'], 'income_tax', 'computed_from_statute',
                      f'Passive rental activities (rental {m["rental"]:.2f}, farm rental {m["farmrent"]:.2f}) net {net:.2f}; '
                      f'IRC 469(i) allowance with active participation = 25,000 - 50% x max(0, MAGI {m["magi_469"]:.2f} - 100,000) '
                      f'= {allowance:.2f}; loss allowed {allowed:.2f}, suspended {net - allowed:.2f} (MAGI excludes taxable Social Security, '
                      f'the IRA and student-loan deductions and the passive loss, 469(i)(3)(F); sources/usc26_469.txt).')
        m['passive_allowed'] = allowed
        # farm rent with stated UBIA is qualified business income (e27200 enters QBI in the engine)
        m['e27200'] = (m['farmrent_qbi'] if net >= 0 else 0.0) + m['rental_qbi']
        m['e02000'] = m['nonpassive_sche'] + allowed

    # ---- R2: MAGI for IRC 219(g)(3)(A): after 86 and 469, without the IRA and student-loan deductions
    def st2(d, m):
        return dict(e02000=m['e02000'], e27200=m['e27200'], e03150=0.0, e03210=0.0)
    _, o2 = run_engine(rows_with(st2), opts)
    for k, (d, m) in enumerate(rets):
        magi = o2.loc[k, 'c00100']
        m['magi_ira'] = magi
        items = m['items']
        filers = [m['people'][n] for n in m['filers']]
        joint = len(filers) == 2
        mars = d['MARS']
        # contributions allowed, IRC 219(b)(1), 219(c) (spousal), 408A(c)(2): traditional first
        order = sorted(filers, key=lambda q: -items[q['name']]['ira_comp'])
        alloc = {}
        prior_left = 0.0
        for idx, q in enumerate(order):
            it = items[q['name']]
            dollar = IRA_LIMIT + (IRA_CATCHUP_50 if q['age'] >= 50 else 0.0)
            comp = it['ira_comp'] + (prior_left if (joint and idx == 1) else 0.0)
            cap = min(dollar, comp)
            trad = min(it['ira_trad_des'], cap)
            roth = max(0.0, min(it['ira_roth_des'], cap - trad))
            # Roth MAGI limit, IRC 408A(c)(3) (same 219(g)(2) mechanics)
            rs, rr = ROTH_PO[mars]
            roth = min(roth, ira_reduced_limit(dollar, magi, rs, rr))
            if idx == 0:
                prior_left = max(0.0, it['ira_comp'] - trad - roth)
            # deduction, IRC 219(g)
            spouse_active = joint and any(items[o['name']]['active_participant'] for o in filers if o is not q)
            if it['active_participant']:
                start, rng = IRA_PO_JOINT_ACTIVE if joint else IRA_PO_SINGLE
                lim = ira_reduced_limit(dollar, magi, start, rng)
            elif spouse_active:
                lim = ira_reduced_limit(dollar, magi, *IRA_PO_SPOUSE_ACTIVE)
            else:
                lim = dollar
            ded = min(trad, lim)
            alloc[q['name']] = dict(trad=trad, roth=roth, ded=ded, comp=comp, dollar=dollar, lim=lim)
            if it['ira_trad_des'] > 0 or it['ira_roth_des'] > 0:
                notes.add(m['case'], 'income_tax', 'computed_from_statute',
                          f'IRA {q["name"]}: desired traditional {it["ira_trad_des"]:.2f}, Roth {it["ira_roth_des"]:.2f}; '
                          f'compensation {comp:.2f} (IRC 219(f)(1){", spousal 219(c)" if joint and idx == 1 else ""}), dollar limit {dollar:,.0f} '
                          f'(n-25-67.txt:164-166); contributed traditional {trad:.2f}, Roth {roth:.2f}; '
                          f'{"active participant" if it["active_participant"] else ("spouse active" if spouse_active else "no plan coverage")}, '
                          f'MAGI {magi:.2f} -> deductible limit {lim:.2f} (IRC 219(g), n-25-67.txt:168-194); e03150 share {ded:.2f}.')
        m['ira'] = alloc
        m['e03150'] = sum(a['ded'] for a in alloc.values())

    # ---- R3: MAGI for IRC 221(b)(2)(C): after 219 and 469, without the student-loan deduction
    def st3(d, m):
        return dict(e02000=m['e02000'], e27200=m['e27200'], e03150=m['e03150'], e03210=0.0)
    _, o3 = run_engine(rows_with(st3), opts)
    for k, (d, m) in enumerate(rets):
        magi = o3.loc[k, 'c00100']
        m['magi_sli'] = magi
        items = m['items']
        paid = sum(items[n]['sli'] for n in m['filers'])
        base = min(SLI_CAP, paid)
        start, rng = SLI_PO[d['MARS']]
        red = 0.0 if magi <= start else min(base, base * (magi - start) / rng)
        m['e03210'] = base - red
        if paid > 0:
            notes.add(m['case'], 'income_tax', 'computed_from_statute',
                      f'Student loan interest paid {paid:.2f}; cap 2,500 (IRC 221(b)(1)); MAGI {magi:.2f} vs phase-out start '
                      f'{start:,.0f} over {rng:,.0f} (rp-25-32.txt:1003-1012) -> e03210 = {m["e03210"]:.2f}.')

    # ---- R4: AGI for IRC 25B(b) and the IRC 72(t)(2)(B) medical exception
    def st4(d, m):
        return dict(e02000=m['e02000'], e27200=m['e27200'], e03150=m['e03150'], e03210=m['e03210'])
    _, o4 = run_engine(rows_with(st4), opts)
    for k, (d, m) in enumerate(rets):
        agi = o4.loc[k, 'c00100']
        m['agi'] = agi
        items = m['items']
        # saver's credit, IRC 25B: eligible individual is 18+, not a dependent, not a full-time
        # student (no one is stated full-time); contributions = 401(k) deferrals + IRA
        # contributions, less plan/IRA distributions of the individual (and, on a joint
        # return, of the spouse) in the year (25B(d)(2)(A),(D)); prior years unstated (0).
        tiers = SAVERS_TIERS[d['MARS']]
        rate = 0.5 if agi <= tiers[0] else 0.2 if agi <= tiers[1] else 0.1 if agi <= tiers[2] else 0.0
        credit = 0.0
        if d['DSI'] == 0:
            # distributions from plans and IRAs (Form 8880 line 4 reading of 25B(d)(2)(A)):
            # IRA (traditional and Roth), 401(k)/403(b), and pensions from qualified plans
            def plan_dists(n):
                f = m['people'][n]['f']
                return sum(num(f, k) for k in ('taxable_ira_distributions', 'tax_exempt_ira_distributions',
                                               'taxable_401k_distributions', 'taxable_403b_distributions',
                                               'taxable_private_pension_income',
                                               'tax_exempt_private_pension_income'))
            dist_all = {n: plan_dists(n) for n in m['filers']}
            for n in m['filers']:
                q = m['people'][n]
                it = items[n]
                a = m['ira'].get(n, dict(trad=0.0, roth=0.0))
                contrib = it['k401_trad'] + it['k401_roth'] + a['trad'] + a['roth']
                if contrib <= 0 or q['age'] < 18:
                    continue
                dist = sum(dist_all.values()) if len(m['filers']) == 2 else dist_all[n]
                qual = min(SAVERS_CAP, max(0.0, contrib - dist))
                credit += rate * qual
                notes.add(m['case'], 'income_tax', 'computed_from_statute',
                          f'Saver\'s credit {n}: contributions {contrib:.2f} (401(k) {it["k401_trad"] + it["k401_roth"]:.2f}, IRA {a["trad"] + a["roth"]:.2f}) '
                          f'less distributions {dist:.2f}, capped at 2,000 -> {qual:.2f}; AGI {agi:.2f} -> rate {rate:.0%} '
                          f'(IRC 25B; n-25-67.txt:140-159); tentative credit {rate * qual:.2f} (the engine limits it by tax).')
        m['e07240'] = round(credit, 2)
        # IRC 72(t) additional tax on early distributions from qualified plans and IRAs
        add = 0.0
        if d['DSI'] == 0:
            early = 0.0
            for n in m['filers']:
                q = m['people'][n]
                it = items[n]
                dist = it['plan_dist'] + it['ira_dist']
                if dist <= 0 or q['age'] >= 60:
                    continue
                if it['disabled']:
                    notes.add(m['case'], 'income_tax', 'reading',
                              f'{n} (age {q["age"]}) has early plan/IRA distributions {dist:.2f} but is stated disabled: IRC 72(t)(2)(A)(iii) exception, no additional tax.')
                    continue
                if it['ssdi'] > 0 and opts['ssdi_is_72t_disability']:
                    notes.add(m['case'], 'income_tax', 'reading',
                              f'{n} (age {q["age"]}) has early IRA/plan distributions {dist:.2f} and receives SSDI {it["ssdi"]:.2f}; SSDI receipt read as IRC 72(m)(7) disability (same test), so no 72(t) additional tax. Alternative: {EARLY_DIST_RATE * dist:.2f} more income tax.')
                    continue
                early += dist
            if early > 0:
                med_ded = max(0.0, d['e17500'] - MEDICAL_FLOOR * agi)
                taxable_early = max(0.0, early - med_ded)
                add = EARLY_DIST_RATE * taxable_early
                notes.add(m['case'], 'income_tax', 'computed_from_statute',
                          f'IRC 72(t): early distributions {early:.2f} before 59 1/2; medical exception 72(t)(2)(B) = max(0, medical {d["e17500"]:.2f} - 7.5% x AGI {agi:.2f}) = {med_ded:.2f}; '
                          f'additional tax e09900 = 10% x {taxable_early:.2f} = {add:.2f} (Schedule 2 line 8).')
        m['e09900'] = round(add, 2)

    # ---- R5: final main pass
    def st5(d, m):
        return dict(e02000=m['e02000'], e27200=m['e27200'], e03150=m['e03150'], e03210=m['e03210'],
                    e07240=m['e07240'], e09900=m['e09900'])
    df5, o5 = run_engine(rows_with(st5), opts)
    assert np.allclose(o5['c00100'].values, o4['c00100'].values), 'AGI moved between R4 and R5'

    # ---- R6: payroll pass: employer disability pay is not FICA wages
    def st6(d, m):
        x = st5(d, m)
        if not opts['disability_benefits_fica']:
            x['e00200p'] = d['e00200p'] - m['dis_wages_p']
            x['e00200s'] = d['e00200s'] - m['dis_wages_s']
        return x
    df6, o6 = run_engine(rows_with(st6), opts)
    assert np.allclose(o5['setax'].values, o6['setax'].values), 'setax differs between passes'

    meta_rows = []
    for k, (d, m) in enumerate(rets):
        meta_rows.append(dict(case_id=m['case'], record=m['record'], RECID=d['RECID'],
                              magi_469=r2(m['magi_469']), passive_net=r2(m['rental'] + m['farmrent']),
                              passive_allowed=r2(m['passive_allowed']), magi_ira=r2(m['magi_ira']),
                              e03150=r2(m['e03150']), magi_sli=r2(m['magi_sli']), e03210=r2(m['e03210']),
                              agi_r4=r2(m['agi']), e07240=m['e07240'], e09900=m['e09900'],
                              e02000=r2(m['e02000']), e27200=r2(m['e27200'])))
    return rets, df5, o5, df6, o6, pd.DataFrame(meta_rows)


QUANTITIES = ['federal_income_tax_before_refundable_credits', 'federal_refundable_credits',
              'self_employment_tax', 'federal_employee_payroll_tax']
FORMULAS = {
    'federal_income_tax_before_refundable_credits':
        'sum over the household\'s returns of (c09200 - setax - ptax_amc - e09800) from the main pass R5 '
        '= Form 1040 line 22 max(0, c05800 - c07100) + niit + e09900 (+ e09700 = 0); c05800 includes AMT c09600',
    'federal_refundable_credits':
        'sum over the household\'s returns of refund from R5 = eitc + c11070 (ACTC) + c10960 (AOTC) + CDCC_refund + recovery_rebate_credit '
        '(the last two are 0 under 2026 law)',
    'self_employment_tax': 'sum over the household\'s returns of setax from R5 (Sch SE line 12, both spouses)',
    'federal_employee_payroll_tax':
        'sum over the household\'s returns of (ptax_was - ptax_er_p - ptax_er_s + ptax_amc) from the payroll pass R6 '
        '= employee OASDI 6.2% + employee HI 1.45% on wages incl. 401(k) deferrals + Additional Medicare Tax (Form 8959, wages and SE)',
}


def household_answers(rets, o5, o6, main_only=False):
    rows = {}
    for k, (d, m) in enumerate(rets):
        case = m['case']
        if case not in rows:
            rows[case] = dict.fromkeys(QUANTITIES, 0.0)
        a = rows[case]
        if not (main_only and m['record'] != 'main'):
            # e09800 (Form 4137/8919 unreported FICA) is never sent, so it is 0 on every record
            a['federal_income_tax_before_refundable_credits'] += (o5.loc[k, 'c09200'] - o5.loc[k, 'setax']
                                                                 - o5.loc[k, 'ptax_amc'])
            a['federal_refundable_credits'] += o5.loc[k, 'refund']
            a['self_employment_tax'] += o5.loc[k, 'setax']
        a['federal_employee_payroll_tax'] += (o6.loc[k, 'ptax_was'] - o6.loc[k, 'ptax_er_p']
                                              - o6.loc[k, 'ptax_er_s'] + o6.loc[k, 'ptax_amc'])
    return {c: {q: r2(v) for q, v in a.items()} for c, a in rows.items()}


def load_inputs():
    s = pd.read_csv(os.path.join(BOARD, 'scenarios.csv'))
    salt = pd.read_csv(os.path.join(BOARD, 'state_and_local_tax_2026.csv'))
    assert set(salt['name']) == {'salt_income_or_sales_tax'}
    assert salt['case_id'].is_unique
    salt_map = dict(zip(salt['case_id'], salt['value'].astype(float)))
    assert len(s) == 100 and s['scenario_id'].is_unique
    return s, salt_map


def build_all(s, salt_map, opts, notes):
    out = {}
    for row in s.itertuples():
        j = json.loads(row.scenario_json)
        assert j['id'] == row.scenario_id and int(j['year']) == YEAR
        out[row.scenario_id] = build_household(row.scenario_id, j, salt_map[row.scenario_id], opts, notes)
    return out


def static_notes(s, notes, households):
    """Readings that apply to every household, and per-household structural readings."""
    A = 'all'
    notes.add(A, 'all', 'engine_behaviour', 'EITC and ACTC are dropped at random by default (eitc_claim_prob_scale 1.03, actc_claim_prob_scale 1.1 in 2026; credit_claim_urn is a seeded uniform draw per record, records.py:197-199; calcfunctions.py:3237-3244, 4342-4350). Every run sets both scales to 9e99 ("always claim"); probe p02 shows 5 of 10 identical $40,000 single-parent records losing a $1,852.62 EITC under defaults and none with the reform.')
    notes.add(A, 'all', 'engine_behaviour', 'Records(..., exact_calculations=True) is used: the default smooths stepped phase-outs. Probe p02: CTC at AGI $401,234 MFJ is $2,100.00 exact (IRC 24(b)(1) $50 per $1,000 or fraction) against $2,138.30 smooth (calcfunctions.py:3348-3352).')
    notes.add(A, 'all', 'engine_behaviour', 'Records(data, start_year=2026, gfactors=None, weights=None) does no growth or extrapolation (records.py:35-37, 142); the Calculator stays in 2026 (asserted each run).')
    notes.add(A, 'all', 'engine_behaviour', 'soi_iitax is False in 2026 (probe p01): iitax excludes setax, ptax_amc and e09800 and payrolltax includes them plus the employer share (calcfunctions.py IITAX). The four answers are therefore built from components, not from iitax or payrolltax.')
    notes.add(A, 'income_tax', 'engine_behaviour', 'The engine computes regular tax from the rate schedules (SchXYZ) for all taxable incomes; the IRS Tax Table (taxable income under $100,000, $50 bands taxed at the band midpoint) can differ by a few dollars. Not adjusted.')
    notes.add(A, 'income_tax', 'engine_behaviour', 'The engine computes the EITC by formula (EITCamount, phase-in rate x earnings, phase-out from max(earnings, AGI)); the IRS EIC Table uses $50 bands and can differ by a few dollars. Not adjusted.')
    notes.add(A, 'income_tax', 'engine_behaviour', 'Inputs the engine takes as already limited (no cap in its code): e03150 IRA deduction, e03210 student loan interest, e03220 educator expenses, e03290 HSA, e03270 SE health insurance (Adj), e19200 mortgage interest (ItemDed), e07240 tentative saver\'s credit (limited by tax in NonrefundableCredits), pencon_p/s 401(k) deferrals, e09900 additional tax. Each is computed from statute in map.py.')
    notes.add(A, 'income_tax', 'engine_behaviour', 'Sch 1-A inputs (overtime_income, tip_income, auto_loan_interest) are "assumed to already represent the form-qualified amounts" (calcfunctions.py:876-878); the engine applies the caps and phase-outs and the senior deduction from age_head/age_spouse.')
    notes.add(A, 'income_tax', 'reading', 'Unlisted numeric facts are 0 and unlisted booleans false (board preface). Eligibility conditions for which the board has no fact at all (valid SSNs, the qualifying-child relationship/support/abode tests, W-2 reporting of overtime, tip occupation, auto-loan vehicle qualification, active participation in a rental) are taken as met; facts that the board states for some people (disabled, blind, student status) are false where unlisted.')
    notes.add(A, 'all', 'reading', 'A household\'s answer sums every federal return its members file: the main return (head, spouse and all listed dependents) and the own return of any dependent with income (093 Dependent 1, 123 Child 1, 067 Dependent 1). Alternative (main return only) is in variants_2026.csv as main_return_only for the two income-tax lines; payroll tax is per worker and always sums all members.')
    notes.add(A, 'income_tax', 'reading', 'federal_income_tax_before_refundable_credits = Form 1040 line 22 plus the Schedule 2 income taxes the engine models besides SE tax and Additional Medicare Tax: NIIT (IRC 1411) and the IRC 72(t) additional tax. Alternative: line 22 alone (variant line22_only).')
    notes.add(A, 'payroll', 'reading', 'Payroll tax is the federal employee share only: 6.2% OASDI to the 2026 base $184,500, 1.45% HI, and Additional Medicare Tax 0.9% over $200,000/$250,000 (Form 8959, which also counts SE income). Traditional 401(k) deferrals are FICA wages (engine adds pencon back, calcfunctions.py:215-216). Employer disability pay is not treated as FICA wages (variant disability_benefits_fica).')
    notes.add(A, 'income_tax', 'reading', 'Medical expenses (e17500) = other_medical_expenses + person-paid premiums for every listed person, on the main return. Premiums = health_insurance_premiums_without_medicare_part_b where stated (the aggregate), else other_health_insurance_premiums, never their sum (the glossary describes the second as a component of the first). Over-the-counter health expenses are excluded (IRC 213(b)); variant otc_in_medical. Employer-paid ESI premiums are excluded (IRC 106).')
    notes.add(A, 'income_tax', 'reading', 'State and local income or sales tax e18400 = the board\'s state_and_local_tax_2026.csv value, before the cap; real estate taxes e18500 = stated real_estate_taxes; the engine applies the 2026 SALT cap ($40,400, reduced 30% of MAGI over $505,000, floor $10,000).')
    notes.add(A, 'income_tax', 'reading', 'Employer disability benefits (disability_benefits) are taxable (IRC 105(a); no employee-paid premiums stated): before 65 as Form 1040 line 1h wages, at 65 or over as pension income (e01500/e01700). The 2025 Form 1040 instructions put disability pensions received before the employer\'s minimum retirement age on line 1h "Other Earned Income" and later ones on lines 5a/5b (sources/i1040gi.txt:1440, 1536-1544, 1821-1826), and the dependent standard deduction worksheet counts line 1z, which includes 1h, as earned income (i1040gi.txt:2313-2315); the plan\'s minimum retirement age is not stated, so 65 stands in for it. As e00200 the benefit is earned income for the engine\'s EITC, ACTC and dependent standard deduction. Alternative: unearned pension income at every age (variant disability_benefits_unearned).')
    notes.add(A, 'income_tax', 'reading', 'survivor_benefits (non-Social-Security survivor benefits) are read as a fully taxable survivor annuity (e01500/e01700). social_security_dependents is Social Security income of the person it is stated on (variant ss_dependents_to_child moves it to the youngest child).')
    notes.add(A, 'income_tax', 'reading', 'Alimony paid/received (020, 031, 056) is entered in e03500/e00800; the engine\'s 2026 law (ALD_AlimonyPaid_hc=1, AlimonyReceived_frac_in_AGI=0) treats it as under a post-2018 instrument, so it has no effect. Variant alimony_pre2019.')
    notes.add(A, 'income_tax', 'reading', 'Unreimbursed employee business expenses go in e20400; miscellaneous itemized deductions are suspended permanently from 2026 (engine ID_Miscellaneous_hc=1), so they have no effect.')
    for case, (rr, items, people) in households.items():
        d, m = rr[0]
        fil = m['filers']
        stat = {1: 'single', 2: 'married filing jointly', 4: 'head of household'}[d['MARS']]
        deps = m['deps']
        txt = f'Main return: {stat} ({", ".join(fil)}); dependents: {", ".join(deps) if deps else "none"}; XTOT {d["XTOT"]}, EIC {d["EIC"]}, n24 {d["n24"]}, f2441 {d["f2441"]}.'
        notes.add(case, 'income_tax', 'reading', txt)
        for x in people:
            if x['role'] == 'dependent':
                notes.add(case, 'income_tax', 'reading',
                          f'{x["name"]} (age {x["age"]}{", disabled" if flag(x["f"], "is_disabled") else ""}) is the head\'s dependent and a qualifying child (IRC 152(c)(3): under 19, or permanently and totally disabled at any age); age 17+ gives the $500 credit for other dependents, not the CTC.')
                if x['age'] >= 19 and flag(x['f'], 'is_disabled') and x['emp'] > 0:
                    notes.add(case, 'income_tax', 'reading',
                              f'{x["name"]} is stated disabled but earns {x["emp"]:,.2f} in wages. The age waiver needs permanent and total disability (IRC 152(c)(3)(B), 22(e)(3): unable to engage in any substantial gainful activity), which full-time work at this pay contradicts; the map follows the stated flag. Alternative: not a qualifying child, and with gross income over the 152(d)(1)(B) limit not a qualifying relative either, so the main return loses the $500 credit for other dependents (income tax +500.00 here, since the return\'s tax exceeds it) and the dependent files as a non-dependent (same $16,100 standard deduction, no EITC at this income).')
            if x['role'] == 'child' and x['emp'] > 0:
                notes.add(case, 'income_tax', 'reading',
                          f'{x["name"]} (age {x["age"]}) earns {x["emp"]:,.2f}; still the head\'s qualifying child (no gross-income test for a qualifying child; support test 152(c)(1)(D) taken as met), so the CTC stays on the main return. No unearned income, so no kiddie tax (IRC 1(g)).')
        if case == 'scenario_033':
            notes.add(case, 'income_tax', 'reading', 'health_savings_account_ald 1,486 is under the 2026 family limit and is entered as stated. Both spouses are 65+ and receive Social Security, which normally means Medicare Part A entitlement and no HSA contributions (IRC 223(b)(7)); Medicare enrolment is not a stated fact, so the stated deduction is kept.')
        headp = [q for q in people if q['role'] == 'head'][0]
        if flag(headp['f'], 'is_surviving_spouse'):
            notes.add(case, 'income_tax', 'reading',
                      'Head is flagged surviving spouse; ' + ('married now, so files jointly.' if d['MARS'] == 2 else 'no dependent child, so no qualifying-surviving-spouse status (IRC 2(a)(1)(B)); files single.'))
        for dd, mm in rr[1:]:
            notes.add(case, 'income_tax', 'reading',
                      f'{mm["filers"][0]} has income of their own and files a separate return as a dependent (DSI=1: dependent standard deduction, no EITC, no credit for themselves).')
        for x in people:
            it = items[x['name']]
            nm = x['name']
            if it['dis_wages'] > 0:
                notes.add(case, 'income_tax', 'reading', f'{nm} disability_benefits {it["dis_wages"]:.2f} under age 65 entered as wages (Form 1040 line 1h) in the main pass and left out of FICA wages in the payroll pass.')
            if it['dis_pension'] > 0:
                notes.add(case, 'income_tax', 'reading', f'{nm} disability_benefits {it["dis_pension"]:.2f} at age {x["age"]} entered as taxable pension (e01700).')
            if it['k401_trad_des'] + it['k401_roth_des'] > 0:
                notes.add(case, 'all', 'computed_from_statute',
                          f'{nm} 401(k): desired traditional {it["k401_trad_des"]:.2f}, Roth {it["k401_roth_des"]:.2f}; limit {it["k401_lim"]:,.0f} (IRC 402(g)(1), 414(v); n-25-67.txt:37-51) and gross wages {it["gross_wages"]:.2f} -> traditional {it["k401_trad"]:.2f} (pencon, out of box-1 wages), Roth {it["k401_roth"]:.2f}.')
            if it['misc_income'] > 0:
                notes.add(case, 'income_tax', 'unexpressed', f'{nm} miscellaneous_income {it["misc_income"]:.2f} (Schedule 1 line 8z other income) has no Tax-Calculator input: records_variables.json has no general other-income variable, and e01200 is Form 4797 gain. Left out; variant misc_income_as_e01200 shows the effect.')
            if it['educ_assist'] > 0:
                notes.add(case, 'income_tax', 'reading', f'{nm} educational_assistance {it["educ_assist"]:.2f} read as a qualified scholarship excluded by IRC 117 (sources/usc26_117.txt); how it was spent is not stated. If taxable it would be Schedule 1 other income, which has no engine input (variant educational_assistance_taxable uses e01200 as a proxy).')
            if num(x['f'], 'qualified_reit_and_ptp_income') > 0:
                notes.add(case, 'income_tax', 'unexpressed', f'{nm} qualified REIT/PTP income {num(x["f"], "qualified_reit_and_ptp_income"):.2f}: entered as ordinary dividends; the 20% IRC 199A(b)(1)(B) component has no engine input (QBI in the engine is business income only).')
            if num(x['f'], 'qualified_bdc_income') > 0:
                notes.add(case, 'income_tax', 'unexpressed', f'{nm} BDC dividend income {num(x["f"], "qualified_bdc_income"):.2f}: entered as ordinary dividends; its 199A deduction component has no engine input.')
            if it['rental'] != 0 and it['ubia_nonsstb'] > 0:
                notes.add(case, 'income_tax', 'unexpressed', f'{nm} rental income {it["rental"]:.2f} with stated UBIA {it["ubia_nonsstb"]:.2f}: the UBIA implies a qualified business, but the engine\'s QBI (e00900, e26270, e02100, e27200) has no input for residential rental QBI. Rental stays in e02000 only; variant rental_with_ubia_is_qbi adds it to e27200 as a proxy.')
            if it['farmrent'] > 0 and it['ubia_nonsstb'] > 0:
                notes.add(case, 'income_tax', 'reading', f'{nm} farm rental income {it["farmrent"]:.2f} with stated UBIA: entered in e27200 (engine QBI) as well as e02000. Farm rent is not SE income (IRC 1402(a)(1)).')
            if it['k1bx14'] > 0:
                notes.add(case, 'all', 'reading', f'{nm} partnership_se_income {it["k1bx14"]:.2f} read as K-1 box 14 SE earnings inside partnership_s_corp_income {it["partnership"]:.2f} (k1bx14 is included in e26270 per records_variables.json).')
            if it['partnership'] != 0 and it['k1bx14'] == 0:
                notes.add(case, 'self_employment', 'reading', f'{nm} partnership/S-corp income {it["partnership"]:.2f} with no partnership_se_income stated: not SE income (limited partner or S-corp share); material participation assumed for passive rules.')
            if it['farm'] != 0:
                notes.add(case, 'all', 'reading', f'{nm} farm_operations_income {it["farm"]:.2f} is Schedule F (e02100); farm_income repeats it as the Schedule J figure and is not entered again.')
            if it['dis_wages'] > 0 and x['age'] < 65 and it['disabled']:
                notes.add(case, 'income_tax', 'unexpressed', f'{nm} is disabled, under 65, with taxable disability income: Schedule R for the under-65 disabled has no engine input (SchR models age 65+ only). Its credit is nonrefundable and the return owes no regular tax, or the AGI/Social Security reductions remove it; effect $0.')
            if it['tips'] > 0:
                notes.add(case, 'all', 'reading', f'{nm} tip_income {it["tips"]:.2f} read as inside employment_income (glossary: wages "including tips"); entered in tip_income for the Sch 1-A deduction. Variant tips_on_top_of_wages.')
            if it['overtime'] > 0:
                notes.add(case, 'income_tax', 'reading', f'{nm} fsla_overtime_premium {it["overtime"]:.2f} is inside employment_income (glossary) and is the qualified overtime premium: overtime_income.')
            if it['ss_dependents'] > 0:
                notes.add(case, 'income_tax', 'reading', f'{nm} social_security_dependents {it["ss_dependents"]:.2f} counted in e02400 of the return it is stated on. Variant ss_dependents_to_child.')
        if d['auto_loan_interest'] > 0:
            notes.add(case, 'income_tax', 'reading', f'auto_loan_interest {d["auto_loan_interest"]:.2f} read as qualified passenger-vehicle loan interest (new US-assembled vehicle, loan after 2024); variant auto_loan_not_qualified.')
        if d['e32800'] > 0:
            notes.add(case, 'income_tax', 'reading', f'Child care expenses {d["e32800"]:.2f} (spm_unit_pre_subsidy_childcare_expenses) entered as e32800 for {d["f2441"]} qualifying person(s) under 13; the engine applies the $3,000/$6,000 cap and the lower-earner limit.')
        if d['e03240'] > 0:
            notes.add(case, 'income_tax', 'reading', f'domestic_production_ald {d["e03240"]:.2f} entered as e03240; IRC 199 was repealed for years after 2017 (engine ALD_DomesticProduction_hc=1), so no deduction.')
        if d['e00800'] > 0 or d['e03500'] > 0:
            notes.add(case, 'income_tax', 'reading', f'Alimony (received {d["e00800"]:.2f}, paid {d["e03500"]:.2f}) has no effect under post-2018 law; variant alimony_pre2019.')
        if d['PT_ubia_property'] > 0 or d['PT_SSTB_income']:
            notes.add(case, 'income_tax', 'reading', f'QBI: PT_SSTB_income={d["PT_SSTB_income"]}, PT_ubia_property={d["PT_ubia_property"]:.2f}, PT_binc_w2_wages=0 (no W-2 wages of the business stated); these bind only above the 199A threshold.')


def main():
    s, salt_map = load_inputs()
    notes = Notes(True)
    hh = build_all(s, salt_map, MAIN, notes)
    rets, df5, o5, df6, o6, passes = pipeline(hh, MAIN, notes)
    static_notes(s, notes, hh)
    ans = household_answers(rets, o5, o6)
    assert len(ans) == 100

    # inputs files
    keyc = pd.DataFrame([dict(case_id=m['case'], record=m['record']) for d, m in rets])
    cols = INT_VARS + FLOAT_VARS
    inp5 = pd.concat([keyc, df5[cols].reset_index(drop=True)], axis=1)
    inp6 = pd.concat([keyc, df6[cols].reset_index(drop=True)], axis=1)
    inp5.to_csv(os.path.join(HERE, 'inputs_2026.csv'), index=False, float_format='%.2f')
    inp6.to_csv(os.path.join(HERE, 'inputs_payroll_pass_2026.csv'), index=False, float_format='%.2f')
    passes.to_csv(os.path.join(HERE, 'passes_2026.csv'), index=False)
    r5 = pd.concat([keyc, o5.reset_index(drop=True).add_prefix('R5_')], axis=1)
    r6 = o6[['ptax_was', 'ptax_er_p', 'ptax_er_s', 'ptax_amc', 'setax']].reset_index(drop=True).add_prefix('R6_')
    pd.concat([r5, r6], axis=1).to_csv(os.path.join(HERE, 'returns_2026.csv'), index=False, float_format='%.2f')

    rows = []
    for case in s['scenario_id']:
        for q in QUANTITIES:
            rows.append(dict(case_id=case, quantity=q, value=f'{ans[case][q]:.2f}', formula=FORMULAS[q]))
    pd.DataFrame(rows).to_csv(os.path.join(HERE, 'answers_2026.csv'), index=False)

    # variants
    vrows = []

    def diff(name, alt):
        for case in s['scenario_id']:
            for q in QUANTITIES:
                a, b = ans[case][q], alt[case][q]
                if abs(a - b) >= 0.005:
                    vrows.append(dict(case_id=case, variant=name, quantity=q, main=f'{a:.2f}',
                                      variant_value=f'{b:.2f}', delta=f'{b - a:.2f}'))
    diff('main_return_only', household_answers(rets, o5, o6, main_only=True))
    line22 = {}
    for k, (d, m) in enumerate(rets):
        c = m['case']
        line22.setdefault(c, dict(ans[c]))
        line22[c]['federal_income_tax_before_refundable_credits'] -= (o5.loc[k, 'niit'] + m['e09900'])
    line22 = {c: {q: r2(v) for q, v in a.items()} for c, a in line22.items()}
    diff('line22_only', line22)
    for name, flip in ({} if '--quick' in sys.argv else VARIANTS).items():
        opts = dict(MAIN)
        opts.update(flip)
        hv = build_all(s, salt_map, opts, Notes(False))
        rv = pipeline(hv, opts, Notes(False))
        diff(name, household_answers(rv[0], rv[2], rv[4]))
        print('variant', name, 'done', flush=True)
    pd.DataFrame(vrows, columns=['case_id', 'variant', 'quantity', 'main', 'variant_value', 'delta']).to_csv(
        os.path.join(HERE, 'variants_2026.csv'), index=False)

    # notes: each alternative reading that moves a household's answer, as a note on that household
    vdf = pd.DataFrame(vrows)
    group = {'federal_income_tax_before_refundable_credits': 'income_tax', 'federal_refundable_credits': 'income_tax',
             'self_employment_tax': 'self_employment', 'federal_employee_payroll_tax': 'payroll'}
    for v in vrows:
        notes.add(v['case_id'], group[v['quantity']], 'reading',
                  f'Alternative reading "{v["variant"]}" (variants_2026.csv) would move {v["quantity"]} from {v["main"]} to {v["variant_value"]} ({v["delta"]}).')
    nd = pd.DataFrame(notes.rows)
    nd.to_csv(os.path.join(HERE, 'notes.csv'), index=False)
    print('returns:', len(rets), 'households:', len(ans), 'notes:', len(nd), 'variant rows:', len(vdf))


if __name__ == '__main__':
    main()
