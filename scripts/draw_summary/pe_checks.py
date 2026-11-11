"""Checks on PolicyEngine's own draw run that show where it took the other side of a reading
the maps share (scripts/draw_summary/summarize.py uses them). Each returns a list of family
names for one household (empty: no sign). They read the run's saved outputs only; they say
which side PolicyEngine took, not why."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from keycheck import households as H
from keycheck import unit as U

PE_STATUS = {"0.0": "single", "1.0": "joint", "3.0": "head_of_household"}  # observed codes (draw counts)

def read_rows(path):
    """The rows of a CSV file as dicts."""
    with open(path, newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))

def load_pe(path=ROOT / "results/pe/draw1000_pe2.60.0_board_2026.csv"):
    pe = {}
    for r in read_rows(path):
        pe.setdefault(r["scenario_id"], {})[r["variable"]] = r
    return pe

def persons(row):
    return json.loads(row["persons"]) if row and row["persons"] else []

def checks(household, unit, pe_case, tc_row):
    out = []
    pe_names = persons(pe_case["person_names"])
    assert sorted(pe_names) == sorted(p["name"] for p in H.people(household))
    dep = dict(zip(pe_names, persons(pe_case["is_tax_unit_dependent"])))
    eitc_qc = dict(zip(pe_names, persons(pe_case["is_eitc_qualifying_child"])))
    ours_dep = {d["name"] for d in unit.dependents}
    ours_eitc = {d["name"] for d in unit.dependents if d["kind"] == "qualifying_child"}
    reading_names = {d["name"] for d in unit.disabled_reading}
    for name, flag in dep.items():
        if name in (unit.head.name, unit.spouse.name if unit.spouse else None):
            continue
        member = next(p for p in H.people(household) if p["name"] == name)
        disabled = H.flag(member, "is_disabled")
        if flag >= 0.5 and name not in ours_dep:
            out.append("PolicyEngine claims a disabled member with earnings of their own (is_disabled reading)" if disabled
                       else "PolicyEngine claims a member who meets neither dependency test on the stated facts (dependents reading)")
        elif flag < 0.5 and name in ours_dep:
            out.append("PolicyEngine does not claim a member the maps claim (dependents reading)")
    for name, flag in eitc_qc.items():
        if flag < 0.5 and name in ours_eitc:
            out.append("PolicyEngine does not count a disabled adult as an EITC child (is_disabled reading)" if name in reading_names
                       else "PolicyEngine does not count a member the maps count as an EITC child")
        elif flag >= 0.5 and name not in ours_eitc and name in dep:
            out.append("PolicyEngine counts an EITC child the maps do not")
    pe_status = PE_STATUS.get(pe_case["filing_status"]["value"])
    if pe_status != unit.status:
        out.append(f"PolicyEngine files {pe_status or pe_case['filing_status']['value']} where the maps file {unit.status.replace('_', ' ')}")
    return sorted(set(out))

MEDICAL_READINGS = ("medicare_part_b", "other_health_insurance_premiums", "over_the_counter", "health_insurance_premiums")

def medical(pe_case, tc_row, tc_notes):
    """PolicyEngine's medical expense deduction exceeds Tax-Calculator's (the stated amounts
    after the medical readings) at the same AGI, in a household that carries a medical reading."""
    if not any(U.READINGS[k] in tc_notes for k in MEDICAL_READINGS):
        return []
    pe_agi = float(pe_case["adjusted_gross_income"]["value"])
    if abs(pe_agi - float(tc_row["out_c00100"])) > 1:
        return []
    if float(pe_case["medical_expense_deduction"]["value"]) - float(tc_row["out_c17000"]) > 1:
        return ["PolicyEngine's medical expense deduction exceeds the stated amounts' at the same AGI (medical readings)"]
    return []

# The lines each PolicyEngine-side family can reach.
LINES_OF = {
    "PolicyEngine does not count a disabled adult as an EITC child (is_disabled reading)": {"federal_refundable_credits"},
    "PolicyEngine does not count a member the maps count as an EITC child": {"federal_refundable_credits"},
    "PolicyEngine counts an EITC child the maps do not": {"federal_refundable_credits"},
    "PolicyEngine's medical expense deduction exceeds the stated amounts' at the same AGI (medical readings)": {"federal_income_tax_before_refundable_credits"},
}
DEFAULT_LINES = {"federal_income_tax_before_refundable_credits", "federal_refundable_credits"}
