"""Run PolicyBench's US households through PolicyEngine-US as the board builds its references.

The board's references (reference_audit/2026-10-22-engine-upgrade/scripts/
build_references_upgrade.py in PolicyEngine/policybench) come from:
  system = CountryTaxBenefitSystem(reform=latest_final.reform)    # the pre-freeze conventions
  situation = sweep.build_situation(scenario)                      # Scenario.to_pe_household + RENAME
  Simulation(tax_benefit_system=system, situation=situation).calculate(pe_variable, 2026)
with each output's PolicyEngine variable and household value taken by
policybench.ground_truth's _pe_variable_for_output and _extract_person_value.
This script does the same, imports those functions from a PolicyBench checkout,
and also writes the parts of each line, so a disagreement can be traced.

  PYTHONPATH=<policybench checkout> envs/pe260/bin/python scripts/run_pe.py \
      --policybench <policybench checkout> --scenarios <scenarios.csv> \
      --conventions board --year 2026 --out results/pe/<name>.csv

--conventions board applies reference_audit/2026-09-28/fixes/latest_final.py from the
checkout (the board's reference system); none runs the engine's current law alone.

Output: one row per household and variable: scenario_id, variable, value (the
household total, which for a board output is the board's own extraction), and
persons (a JSON list of per-person values for person-level variables).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

BOARD_OUTPUTS = (
    "federal_income_tax_before_refundable_credits",
    "federal_refundable_credits",
    "payroll_tax",
    "self_employment_tax",
    "state_income_tax_before_refundable_credits",
)

# Parts of the four lines and the facts that drive them. Names missing from an
# engine release are skipped and listed in the run's sidecar.
TAX_UNIT_VARIABLES = (
    "filing_status",
    "tax_unit_is_joint",
    "adjusted_gross_income",
    "irs_gross_income",
    "above_the_line_deductions",
    "self_employment_tax_ald",
    "self_employed_health_insurance_ald",
    "self_employed_pension_contribution_ald",
    "student_loan_interest_ald",
    "educator_expense_ald",
    "alimony_expense_ald",
    "health_savings_account_ald",
    "domestic_production_ald",
    "traditional_ira_contributions_ald",
    "early_withdrawal_penalty",
    "tax_unit_taxable_social_security",
    "tax_unit_social_security",
    "taxable_income",
    "taxable_income_deductions",
    "standard_deduction",
    "basic_standard_deduction",
    "additional_standard_deduction",
    "tax_unit_itemizes",
    "itemized_taxable_income_deductions",
    "salt_deduction",
    "salt",
    "salt_cap",
    "state_and_local_sales_or_income_tax",
    "real_estate_taxes",
    "medical_expense_deduction",
    "interest_deduction",
    "charitable_deduction",
    "charitable_deduction_for_non_itemizers",
    "casualty_loss_deduction",
    "qualified_business_income_deduction",
    "additional_senior_deduction",
    "tip_income_deduction",
    "overtime_income_deduction",
    "auto_loan_interest_deduction",
    "income_tax_main_rates",
    "capital_gains_tax",
    "alternative_minimum_tax",
    "amt_income",
    "income_tax_before_credits",
    "net_investment_income_tax",
    "net_investment_income",
    "recapture_of_investment_credit",
    "unreported_payroll_tax",
    "qualified_retirement_penalty",
    "income_tax_non_refundable_credits",
    "income_tax_capped_non_refundable_credits",
    "foreign_tax_credit",
    "cdcc",
    "tax_unit_childcare_expenses",
    "elderly_disabled_credit",
    "non_refundable_american_opportunity_credit",
    "lifetime_learning_credit",
    "savers_credit",
    "non_refundable_ctc",
    "ctc",
    "ctc_qualifying_children",
    "income_tax_refundable_credits",
    "eitc",
    "eitc_child_count",
    "eitc_relevant_investment_income",
    "refundable_ctc",
    "refundable_american_opportunity_credit",
    "recovery_rebate_credit",
    "refundable_payroll_tax_credit",
    "income_tax_before_refundable_credits",
    "income_tax",
    "additional_medicare_tax",
    "employee_payroll_tax",
    "employee_state_payroll_tax",
    "tax_unit_dependents",
    "state_withheld_income_tax",
    "local_income_tax",
    "state_sales_tax",
)

PERSON_VARIABLES = (
    "age",
    "is_tax_unit_head",
    "is_tax_unit_spouse",
    "is_tax_unit_dependent",
    "is_full_time_student",
    "is_disabled",
    "is_blind",
    "employment_income",
    "irs_employment_income",
    "payroll_tax_gross_wages",
    "taxable_earnings_for_social_security",
    "employee_social_security_tax",
    "employee_medicare_tax",
    "self_employment_income",
    "taxable_self_employment_income",
    "social_security_taxable_self_employment_income",
    "self_employment_social_security_tax",
    "self_employment_medicare_tax",
    "self_employment_tax",
    "traditional_401k_contributions",
    "traditional_403b_contributions",
    "traditional_ira_contributions",
    "ctc_qualifying_child",
    "is_eitc_qualifying_child",
    "is_child_dependent",
    "fsla_overtime_premium",
    "tip_income",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def as_number(values):
    arr = np.asarray(values)
    if arr.dtype.kind in "biuf":
        return [float(v) for v in arr]
    return [str(v) for v in arr]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policybench", required=True, type=Path)
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--conventions", choices=("board", "none"), default="board")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", nargs="*", help="restrict to these scenario ids")
    args = parser.parse_args(argv)

    root = args.policybench.resolve()
    sys.path.insert(0, str(root))
    from policyengine_us import CountryTaxBenefitSystem, Simulation

    from policybench.ground_truth import _extract_person_value, _pe_variable_for_output
    from policybench.scenarios import scenario_from_dict

    sweep_path = root / "reference_audit/2026-09-28/scripts/sweep.py"
    final_path = root / "reference_audit/2026-09-28/fixes/latest_final.py"
    sweep = load_module("keycheck_sweep", sweep_path)
    pins = {
        "policyengine_us": version("policyengine-us"),
        "policyengine_core": version("policyengine-core"),
        "harness": str(sweep_path.relative_to(root)),
        "harness_sha256": sha256(sweep_path),
        "conventions": args.conventions,
        "year": args.year,
    }
    if args.conventions == "board":
        final = load_module("keycheck_latest_final", final_path)
        system = CountryTaxBenefitSystem(reform=final.reform)
        pins["latest_final_sha256"] = sha256(final_path)
        tables = final_path.with_name("r19_irs_sales_tax_2025.json")
        pins["sales_tax_tables_sha256"] = sha256(tables)
    else:
        system = CountryTaxBenefitSystem()
    known = set(system.variables)
    tax_unit_vars = [v for v in TAX_UNIT_VARIABLES if v in known]
    person_vars = [v for v in PERSON_VARIABLES if v in known]
    pins["skipped_variables"] = sorted(
        set(TAX_UNIT_VARIABLES + PERSON_VARIABLES) - known
    )

    scenarios = pd.read_csv(args.scenarios)
    if args.only:
        scenarios = scenarios[scenarios["scenario_id"].isin(args.only)]
    rows = []
    for _, srow in scenarios.iterrows():
        scenario = scenario_from_dict(json.loads(srow["scenario_json"]))
        situation = sweep.build_situation(scenario)
        if args.year != 2026:
            situation = json.loads(
                json.dumps(situation).replace('"2026"', f'"{args.year}"')
            )
        sim = Simulation(tax_benefit_system=system, situation=situation)
        for output in BOARD_OUTPUTS:
            pe_variable = _pe_variable_for_output(output, "us")
            value = _extract_person_value(
                sim.calculate(pe_variable, args.year), scenario, output
            )
            rows.append(
                {"scenario_id": scenario.id, "variable": f"board:{output}",
                 "value": float(value), "persons": ""}
            )
        for variable in tax_unit_vars:
            result = sim.calculate(variable, args.year)
            values = as_number(result)
            if isinstance(values[0], str):
                rows.append({"scenario_id": scenario.id, "variable": variable,
                             "value": float("nan"), "persons": json.dumps(values)})
            else:
                rows.append({"scenario_id": scenario.id, "variable": variable,
                             "value": float(np.sum(values)), "persons": ""})
        for variable in person_vars:
            values = as_number(sim.calculate(variable, args.year))
            total = float("nan") if isinstance(values[0], str) else float(np.sum(values))
            rows.append({"scenario_id": scenario.id, "variable": variable,
                         "value": total, "persons": json.dumps(values)})
        names = list(situation["people"].keys())
        rows.append({"scenario_id": scenario.id, "variable": "person_names",
                     "value": float(len(names)), "persons": json.dumps(names)})
        print(scenario.id, flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out, index=False)
    args.out.with_suffix(".meta.json").write_text(json.dumps(pins, indent=1) + "\n")
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
