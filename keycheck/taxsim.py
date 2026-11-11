"""Run NBER's TAXSIM binary on rows of inputs.

The binary reads a CSV on standard input (a header of TAXSIM's input names, one record
per line) and writes a CSV on standard output: a header, one line per record, and, when
it stops on a record, lines that begin " TAXSIM:" naming it. `idtl` 2 asks for the
detail columns. The build stamp is the last field of the output header.
"""

from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path

ORDER = (
    "taxsimid", "year", "state", "mstat", "page", "sage", "depx",
    "dep13", "dep17", "dep18",
    "age1", "age2", "age3", "age4", "age5", "age6", "age7", "age8", "age9", "age10",
    "pwages", "swages", "psemp", "ssemp", "dividends", "intrec", "stcg", "ltcg",
    "otherprop", "nonprop", "pensions", "gssi", "pui", "sui", "transfers", "rentpaid",
    "proptax", "otheritem", "childcare", "mortgage", "scorp", "pbusinc", "pprofinc",
    "sbusinc", "sprofinc", "idtl",
)


WHOLE = {"taxsimid", "year", "state", "mstat", "page", "sage", "depx", "dep13", "dep17", "dep18", "idtl"}
# The build stops a whole file when ages and dependent counts share a header (probe P3).


class TaxsimError(RuntimeError):
    pass


def run(rows: list[dict], binary: str | Path, idtl: int = 2) -> tuple[list[dict], str]:
    """Return one dict of floats per input row, and the build stamp."""
    if not rows:
        return [], ""
    names = [n for n in ORDER if n == "idtl" or any(n in r for r in rows)]
    if any(n.startswith("age") for n in names) and any(n in names for n in ("dep13", "dep17", "dep18")):
        raise TaxsimError("ages and dependent counts cannot share a file")
    unknown = sorted({k for r in rows for k in r} - set(ORDER))
    if unknown:
        raise TaxsimError(f"not TAXSIM input names: {unknown}")
    lines = [",".join(names)]
    for row in rows:
        values = []
        for name in names:
            value = idtl if name == "idtl" else row.get(name, 0)
            whole = name in WHOLE or name.startswith("age")
            values.append(str(int(value)) if whole else repr(round(float(value), 2)))
        lines.append(",".join(values))
    done = subprocess.run(
        [str(binary)], input="\n".join(lines) + "\n", capture_output=True, text=True, check=False
    )
    text = done.stdout
    data = [line for line in text.splitlines() if line and not line.startswith(" TAXSIM")]
    reader = list(csv.reader(io.StringIO("\n".join(data))))
    notes = "\n".join(line for line in text.splitlines() if line.startswith(" TAXSIM"))
    if not reader:
        raise TaxsimError(
            f"TAXSIM answered no record of {len(rows)} (exit {done.returncode}):\n{notes}\n{done.stderr}"
        )
    header = [h.strip() for h in reader[0]]
    stamp = header[-1].strip('"')
    out = []
    for fields in reader[1:]:
        record = {}
        for name, field in zip(header[:-1], fields):
            record[name] = float(field)
        out.append(record)
    if len(out) != len(rows):
        raise TaxsimError(
            f"TAXSIM answered {len(out)} of {len(rows)} records (exit {done.returncode}):\n{notes}\n{done.stderr}"
        )
    for row, record in zip(rows, out):
        if int(record["taxsimid"]) != int(row["taxsimid"]):
            raise TaxsimError(f"record order changed at taxsimid {row['taxsimid']}")
    return out, stamp
