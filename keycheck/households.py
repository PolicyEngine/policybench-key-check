"""Read PolicyBench households as the board publishes them.

A household is the parsed `scenario_json` of one row of the board's scenarios.csv:
adults and children, each with a name (head, spouse, dependentN, childN), an age,
`employment_income` and an `inputs` dict; `tax_unit_inputs`, `spm_unit_inputs` and
`household_inputs`; the state and the tax year. The maps in this package read only
these stated facts, never a value PolicyEngine computed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


def load(path: str | Path) -> list[dict]:
    with open(path, newline="") as handle:
        return [json.loads(row["scenario_json"]) for row in csv.DictReader(handle)]


def people(household: dict) -> list[dict]:
    return list(household["adults"]) + list(household["children"])


def head(household: dict) -> dict:
    return next(p for p in people(household) if p["name"] == "head")


def spouse(household: dict) -> dict | None:
    return next((p for p in people(household) if p["name"] == "spouse"), None)


def others(household: dict) -> list[dict]:
    """Everyone but the head and spouse: the unit's dependents, as the board states them."""
    return [p for p in people(household) if p["name"] not in ("head", "spouse")]


def amount(person: dict | None, key: str) -> float:
    """A person's stated amount; an unlisted amount is 0 (the board's rule)."""
    if person is None:
        return 0.0
    if key == "employment_income":
        return float(person.get("employment_income") or 0.0)
    value = person.get("inputs", {}).get(key, 0.0)
    return float(value or 0.0)


def flag(person: dict | None, key: str) -> bool:
    """A person's stated status; an unlisted status is false (the board's rule)."""
    if person is None:
        return False
    return bool(person.get("inputs", {}).get(key, False))
