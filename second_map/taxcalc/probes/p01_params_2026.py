"""Probe 01: print the Tax-Calculator 6.9.0 current-law parameter values for 2026
that bear on the four board outputs."""
import taxcalc as tc
pol = tc.Policy()
pol.set_year(2026)
names = """STD STD_Aged STD_Dep STD_Dep_earned_add STD_charity_ded_nonitemizers_max
II_rt1 II_rt2 II_rt3 II_rt4 II_rt5 II_rt6 II_rt7 II_rt8 II_brk1 II_brk2 II_brk3 II_brk4 II_brk5 II_brk6 II_brk7
CG_rt1 CG_rt2 CG_rt3 CG_brk1 CG_brk2 CG_brk3
CTC_c CTC_ps CTC_prt ODC_c ACTC_c ACTC_rt ACTC_Income_thd ACTC_ChildNum CTC_is_refundable CTC_include17 CTC_c_under6_bonus
EITC_c EITC_rt EITC_prt EITC_ps EITC_ps_addon_MarriedJ EITC_MinEligAge EITC_MaxEligAge EITC_InvestIncome_c EITC_excess_InvestIncome_rt EITC_indiv EITC_sep_filers_elig EITC_basic_frac
eitc_claim_prob_min eitc_claim_prob_scale actc_claim_prob_min actc_claim_prob_scale soi_iitax
SS_Earnings_c SS_Earnings_thd FICA_ss_trt_employee FICA_ss_trt_employer FICA_mc_trt_employee FICA_mc_trt_employer SECA_Earnings_deminimus AMEDT_ec AMEDT_rt
SS_thd1 SS_thd2 SS_percentage1 SS_percentage2 SS_all_in_agi
ID_AllTaxes_c ID_AllTaxes_c_ps ID_AllTaxes_c_po_rate ID_AllTaxes_c_po_floor ID_Medical_frt ID_Charity_frt ID_Charity_f ID_Charity_crt_all ID_Charity_crt_noncash ID_reduction_rate ID_Miscellaneous_hc ID_InterestPaid_hc ID_ps ID_prt ID_c ID_StateLocalTax_hc ID_RealEstate_hc
SeniorDed_c SeniorDed_ps SeniorDed_prt OvertimeIncomeDed_c OvertimeIncomeDed_ps OvertimeIncomeDed_po_step_size OvertimeIncomeDed_po_rate_per_step TipIncomeDed_c TipIncomeDed_ps TipIncomeDed_po_step_size TipIncomeDed_po_rate_per_step AutoLoanInterestDed_c AutoLoanInterestDed_ps AutoLoanInterestDed_po_step_size AutoLoanInterestDed_po_rate_per_step
CDCC_c CDCC_ps1 CDCC_ps2 CDCC_po1_rate_max CDCC_po1_rate_min CDCC_po2_rate_min CDCC_po1_step_size CDCC_po2_step_size CDCC_po_rate_per_step CDCC_refundable
PT_qbid_rt PT_qbid_taxinc_thd PT_qbid_taxinc_gap PT_qbid_min_ded PT_qbid_min_qbi PT_qbid_limited PT_qbid_ps PT_qbid_prt
AMT_em AMT_em_ps AMT_prt AMT_brk1 AMT_rt1 AMT_rt2_addon AMT_child_em AMT_child_em_c_age AMT_CG_brk1 AMT_CG_brk2
NIIT_thd NIIT_rt NIIT_PT_taxed Capital_loss_limitation
ALD_StudentLoan_hc ALD_EducatorExpenses_hc ALD_HSADeduction_hc ALD_AlimonyPaid_hc ALD_IRAContributions_hc ALD_SelfEmploymentTax_hc ALD_Tuition_hc ALD_DomesticProduction_hc ALD_BusinessLosses_c AlimonyReceived_frac_in_AGI
LLC_Expense_c ETC_pe_Single ETC_pe_Married CR_SchR_hc II_em UI_em UI_thd""".split()
for n in names:
    try:
        v = pol.to_array(n) if False else getattr(pol, n)
        print(n, v.tolist() if hasattr(v, 'tolist') else v)
    except Exception as e:
        print(n, 'ERROR', e)
