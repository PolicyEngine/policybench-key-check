"""Print PolicyEngine-US parameter values at given dates, with and without the board's conventions.

  PYTHONPATH=<policybench checkout> envs/pe260/bin/python scripts/dump_pe_params.py \
      --policybench <policybench checkout> --conventions board \
      --dates 2025-01-01 2026-01-01 --out results/pe/params_<release>_board.json

Writes every leaf under gov.irs and gov.simulation: a number, a list, a boolean, or for a
bracket scale its thresholds with rates or amounts. The file says what the engine uses on
each date; whether a value is listed in the YAML or uprated from an earlier year is read
from the YAML itself.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from importlib.metadata import version
from pathlib import Path

ROOTS = ("gov.irs", "gov.simulation")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def plain(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (int, float, bool, str)) or value is None:
        return value
    return str(value)


def scale_at(scale, date):
    at = scale(date)
    out = {}
    for field in ("thresholds", "rates", "amounts"):
        if hasattr(at, field):
            try:
                out[field] = plain(list(getattr(at, field)))
            except Exception as exc:  # noqa: BLE001
                out[field] = f"unreadable: {exc}"
    return out


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policybench", required=True, type=Path)
    parser.add_argument("--conventions", choices=("board", "none"), default="board")
    parser.add_argument("--dates", nargs="+", default=["2025-01-01", "2026-01-01"])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    root = args.policybench.resolve()
    sys.path.insert(0, str(root))
    from policyengine_core.parameters import Parameter, ParameterScale
    from policyengine_us import CountryTaxBenefitSystem

    if args.conventions == "board":
        final = load_module(
            "keycheck_latest_final",
            root / "reference_audit/2026-09-28/fixes/latest_final.py",
        )
        system = CountryTaxBenefitSystem(reform=final.reform)
    else:
        system = CountryTaxBenefitSystem()

    values = {}
    for root_name in ROOTS:
        node = system.parameters
        for part in root_name.split("."):
            node = getattr(node, part)
        for descendant in node.get_descendants():
            name = descendant.name
            if isinstance(descendant, ParameterScale):
                values[name] = {date: scale_at(descendant, date) for date in args.dates}
            elif isinstance(descendant, Parameter):
                row = {}
                for date in args.dates:
                    try:
                        row[date] = plain(descendant(date))
                    except Exception as exc:  # noqa: BLE001
                        row[date] = f"unreadable: {exc}"
                values[name] = row
    doc = {
        "policyengine_us": version("policyengine-us"),
        "policyengine_core": version("policyengine-core"),
        "conventions": args.conventions,
        "dates": args.dates,
        "values": values,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(values)} parameters to {args.out}")


if __name__ == "__main__":
    main()
