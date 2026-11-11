"""Draw more households the way PolicyBench draws its own.

PolicyBench samples households from its certified US dataset with
policybench.scenarios.generate_scenarios: load_certified_us_person_frame() reads every
promptable input for every person, and scenarios_from_cps_frame() keeps households that
are one tax unit, one SPM unit and one family, samples them without replacement with
probability proportional to household weight, and builds each Scenario. This script
calls those two functions unchanged, with a different seed and count.

The only substitution: PolicyBench resolves the dataset through the `policyengine`
package's bundle manifest; here the dataset file is given directly (the same Hugging
Face tag the board's reference sidecar names), so the environment needs only
policyengine-us.

  PYTHONPATH=<policybench checkout> envs/pe260/bin/python scripts/draw_households.py \
      --policybench <policybench checkout> --n 1000 --seed 20261110 \
      --out data/draw/draw1000_seed20261110.csv

The output holds record-level households from the microdata, so it stays out of git
(data/draw/ is ignored); rerun this script to rebuild it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path

REPO_ID = "policyengine/populace-us"
FILENAME = "populace_us_2024.h5"
# The dataset the board's reference sidecar records (reference_outputs.csv.meta.json,
# policyengine_bundles.us.default_dataset_uri and certified_data_artifact_sha256).
REVISION = "populace-us-2024-spm-20260915"
SHA256 = "6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policybench", required=True, type=Path)
    parser.add_argument("--dataset", type=Path, help="local copy of the dataset file")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--prefix", default="draw")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(args.policybench.resolve()))
    dataset = args.dataset
    if dataset is None:
        from huggingface_hub import hf_hub_download

        dataset = Path(
            hf_hub_download(
                repo_id=REPO_ID, filename=FILENAME, revision=REVISION, repo_type="dataset"
            )
        )
    found = sha256(dataset)
    if found != SHA256:
        raise SystemExit(f"{dataset} has sha256 {found}, not the board's {SHA256}")

    import policybench.policyengine_runtime as runtime
    from policyengine_us import Microsimulation

    cache = {}

    def make_us_microsimulation(**kwargs):
        if "sim" not in cache:
            sim = Microsimulation(dataset=str(dataset))
            sim.policyengine_bundle = {"default_dataset": "populace_us_2024"}
            cache["sim"] = sim
        return cache["sim"]

    runtime.make_us_microsimulation = make_us_microsimulation
    from policybench import scenarios as board

    person_df, dataset_year, dataset_label = board.load_certified_us_person_frame()
    drawn = board.scenarios_from_cps_frame(
        person_df,
        n=args.n,
        seed=args.seed,
        year=board.TAX_YEAR,
        dataset_year=dataset_year,
        dataset_label=dataset_label,
    )
    width = len(str(args.n - 1))
    for index, scenario in enumerate(drawn):
        scenario.id = f"{args.prefix}_{index:0{width}d}"
    manifest = board.scenario_manifest(drawn)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.out, index=False)
    meta = {
        "n": args.n,
        "seed": args.seed,
        "dataset": f"hf://{REPO_ID}/{FILENAME}@{REVISION}",
        "dataset_sha256": found,
        "dataset_year": int(dataset_year),
        "persons_in_dataset": int(len(person_df)),
        "policyengine_us": version("policyengine-us"),
        "builder": "policybench.scenarios.load_certified_us_person_frame and scenarios_from_cps_frame",
    }
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
