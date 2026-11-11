"""TAXSIM cd2026110117 counterfactual from a dossier's final inputs, via keycheck.taxsim.run (idtl 2)."""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from keycheck import taxsim
case, year = sys.argv[1], int(sys.argv[2])
d = json.loads((REPO / f"results/dossiers/{case}.json").read_text())["other_models"][f"taxsim-cd2026110117-{year}"]
rec = {k[3:]: v for k, v in d.items() if k.startswith("in_")}
for a in sys.argv[3:]:
    k, v = a.split("="); rec[k] = float(v)
rec["taxsimid"] = 1
out, stamp = taxsim.run([rec], REPO / "work/nber/taxsimtest-osx.exe")
o = out[0]
print(case, year, sys.argv[3:], {k: o.get(k) for k in ("fiitax", "v10", "v12", "v18", "v25", "actc")})
