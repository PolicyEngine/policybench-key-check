"""Rerun one board household on PolicyEngine with one fact or parameter changed.

  PYTHONPATH=<policybench checkout> envs/pe260/bin/python scripts/pe_experiment.py \
      --policybench <policybench checkout> --scenarios <scenarios.csv> \
      --case scenario_093 --set dependent1.is_disabled=false \
      --read ctc income_tax_before_refundable_credits

The household is built by the board's own builder and conventions (as scripts/run_pe.py
does). `--set person.input=value` changes or adds a stated input (person names: head,
spouse, dependent1, child1, ...; `tax_unit.`, `spm_unit.` and `household.` for the
entities). `--append-list parameter=name` appends a variable name to a list parameter
for the year. Prints each variable before and after.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from importlib.metadata import version
from pathlib import Path

import pandas as pd

YEAR = 2026


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse(value: str):
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return float(value)
    except ValueError:
        return value


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policybench", required=True, type=Path)
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--append-list", action="append", default=[])
    parser.add_argument("--read", nargs="+", required=True)
    args = parser.parse_args(argv)

    root = args.policybench.resolve()
    sys.path.insert(0, str(root))
    from policyengine_core.reforms import Reform
    from policyengine_us import CountryTaxBenefitSystem, Simulation

    from policybench.scenarios import scenario_from_dict

    sweep = load_module("keycheck_sweep", root / "reference_audit/2026-09-28/scripts/sweep.py")
    final = load_module("keycheck_latest_final", root / "reference_audit/2026-09-28/fixes/latest_final.py")
    appended = [item.split("=", 1) for item in args.append_list]

    class changed(Reform):
        def apply(self):
            final.reform.apply(self)

            def modify(parameters):
                for path, name in appended:
                    node = parameters
                    for part in path.split("."):
                        node = getattr(node, part)
                    current = list(node(f"{YEAR}-01-01"))
                    if name not in current:  # the modifier can run more than once
                        node.update(period=f"year:{YEAR}:1", value=current + [name])
                return parameters

            if appended:
                self.modify_parameters(modify)

    scenarios = pd.read_csv(args.scenarios)
    row = scenarios[scenarios["scenario_id"] == args.case].iloc[0]
    scenario = scenario_from_dict(json.loads(row["scenario_json"]))
    base = sweep.build_situation(scenario)
    after = json.loads(json.dumps(base))
    groups = {"tax_unit": ("tax_units", "tax_unit"), "spm_unit": ("spm_units", "spm_unit"), "household": ("households", "household")}
    for item in args.set:
        target, value = item.split("=", 1)
        owner, name = target.split(".", 1)
        if owner in groups:
            plural, key = groups[owner]
            after[plural][key][name] = {str(YEAR): parse(value)}
        else:
            after["people"][owner][name] = {str(YEAR): parse(value)}

    print(f"policyengine-us {version('policyengine-us')}, {args.case}, board conventions, {YEAR}")
    print(f"change: {args.set or ''} {args.append_list or ''}")
    systems = (CountryTaxBenefitSystem(reform=final.reform), CountryTaxBenefitSystem(reform=changed))
    sims = (Simulation(tax_benefit_system=systems[0], situation=base), Simulation(tax_benefit_system=systems[1], situation=after))
    for name in args.read:
        shown = []
        for sim in sims:
            try:
                values = sim.calculate(name, YEAR)
                values = getattr(values, "decode_to_str", lambda: values)()
                shown.append([v.item() if hasattr(v, "item") else str(v) for v in values])
            except Exception as error:  # noqa: BLE001
                shown.append(f"not available ({type(error).__name__})")
        print(f"   {name}: before {shown[0]} after {shown[1]}")


if __name__ == "__main__":
    main()
