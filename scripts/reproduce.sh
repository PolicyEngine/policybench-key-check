#!/usr/bin/env bash
# Rebuild every committed result of this check, step by step.
#
#   scripts/reproduce.sh setup      # environments, PolicyBench at the pinned commit, TAXSIM binary
#   scripts/reproduce.sh pe         # PolicyEngine runs (the heavy step: about 2 GB of memory each)
#   scripts/reproduce.sh shared     # state and local tax paid, taken from the PolicyEngine runs
#   scripts/reproduce.sh engines    # Tax-Calculator and TAXSIM runs
#   scripts/reproduce.sh tables     # answers, agreement, bindings, dossiers, causes, statuses, README
#   scripts/reproduce.sh compare    # the second input maps against the first
#   scripts/reproduce.sh tests
#   scripts/reproduce.sh all
#
# Steps after `engines` read files only. PB names the PolicyBench checkout
# (default work/policybench-c7ede86c, which `setup` creates).
set -euo pipefail
cd "$(dirname "$0")/.."

PB="${PB:-work/policybench-c7ede86c}"
PB_COMMIT=c7ede86c
BOARD="$PB/paper/snapshot/20260501/runs/us_full_run_20260612_policyengine_4_16_1_populace"
TAXSIM=work/nber/taxsimtest-osx.exe

setup() {
  uv venv --python 3.12 envs/pe260 && uv pip install --python envs/pe260/bin/python policyengine-us==2.60.0
  uv venv --python 3.12 envs/pe211615 && uv pip install --python envs/pe211615/bin/python policyengine-us==2.116.15
  uv venv --python 3.13 envs/tc690 && uv pip install --python envs/tc690/bin/python taxcalc==6.9.0
  if [ ! -d "$PB" ]; then
    git clone https://github.com/PolicyEngine/policybench "$PB" && git -C "$PB" checkout "$PB_COMMIT"
  fi
  scripts/get_taxsim.sh
}

pe() {
  run_pe() {  # environment, conventions, year, output
    PYTHONPATH="$PB" "envs/$1/bin/python" scripts/run_pe.py --policybench "$PB" \
      --scenarios "$BOARD/scenarios.csv" --conventions "$2" --year "$3" --out "$4"
  }
  run_pe pe260 board 2026 results/pe/board100_pe2.60.0_board_2026.csv
  run_pe pe260 board 2025 results/pe/board100_pe2.60.0_board_2025.csv
  run_pe pe211615 board 2026 results/pe/board100_pe2.116.15_board_2026.csv
  run_pe pe211615 none 2026 results/pe/board100_pe2.116.15_none_2026.csv
  PYTHONPATH="$PB" envs/pe260/bin/python scripts/dump_pe_params.py --policybench "$PB" \
    --conventions board --dates 2025-01-01 2026-01-01 --out results/pe/params_2.60.0_board.json
  envs/pe260/bin/python scripts/repro_pe.py > results/repro/repro_pe_2.60.0.txt
  envs/pe211615/bin/python scripts/repro_pe.py > results/repro/repro_pe_2.116.15.txt
  envs/pe260/bin/python scripts/repro_pe_draw.py > results/repro/draw_experiments_pe_2.60.0.txt
  envs/pe211615/bin/python scripts/repro_pe_draw.py > results/repro/draw_experiments_pe_2.116.15.txt
  envs/pe260/bin/python scripts/repro_pe_readings.py > results/repro/reading_experiments_pe_2.60.0.txt
  envs/pe211615/bin/python scripts/repro_pe_readings.py > results/repro/reading_experiments_pe_2.116.15.txt
}

shared() {
  python3 scripts/make_shared_salt.py --pe-run results/pe/board100_pe2.60.0_board_2026.csv \
    --label "policyengine-us 2.60.0, board conventions" --out results/shared/board100_salt_from_pe2.60.0_2026.csv
  python3 scripts/make_shared_salt.py --pe-run results/pe/board100_pe2.60.0_board_2025.csv \
    --label "policyengine-us 2.60.0, board conventions, tax year 2025" --out results/shared/board100_salt_from_pe2.60.0_2025.csv
}

engines() {
  for year in 2026 2025; do
    envs/tc690/bin/python scripts/run_taxcalc.py --scenarios "$BOARD/scenarios.csv" --year "$year" \
      --shared "results/shared/board100_salt_from_pe2.60.0_$year.csv" --out "results/taxcalc/board100_tc6.9.0_$year.csv"
    python3 scripts/run_taxsim.py --scenarios "$BOARD/scenarios.csv" --year "$year" --binary "$TAXSIM" \
      --shared "results/shared/board100_salt_from_pe2.60.0_$year.csv" --out "results/taxsim/board100_cd2026110117_$year.csv"
  done
}

tables() {
  python3 scripts/build_answers.py --case-set board-100 --runs results/runs.csv \
    --reference "pb-reference-2.60.0=$BOARD/reference_outputs.csv" \
    --pe pe-2.60.0-board-2026=results/pe/board100_pe2.60.0_board_2026.csv \
    --pe pe-2.60.0-board-2025=results/pe/board100_pe2.60.0_board_2025.csv \
    --pe pe-2.116.15-board-2026=results/pe/board100_pe2.116.15_board_2026.csv \
    --pe pe-2.116.15-none-2026=results/pe/board100_pe2.116.15_none_2026.csv \
    --taxcalc taxcalc-6.9.0-2026=results/taxcalc/board100_tc6.9.0_2026.csv \
    --taxcalc taxcalc-6.9.0-2025=results/taxcalc/board100_tc6.9.0_2025.csv \
    --taxsim taxsim-cd2026110117-2026=results/taxsim/board100_cd2026110117_2026.csv \
    --taxsim taxsim-cd2026110117-2025=results/taxsim/board100_cd2026110117_2025.csv \
    --out results/answers.csv
  python3 scripts/agreement.py --answers results/answers.csv --case-set board-100 \
    --key pb-reference-2.60.0 --key-fallback pe-2.60.0-board-2026 \
    --others taxcalc-6.9.0-2026 taxsim-cd2026110117-2026 \
    --exclusions "$BOARD/reference_exclusions.json" --out-prefix results/agreement/board100_2026_key
  python3 scripts/agreement.py --answers results/answers.csv --case-set board-100 \
    --key pe-2.60.0-board-2026 --others taxcalc-6.9.0-2026 taxsim-cd2026110117-2026 \
    --exclusions "$BOARD/reference_exclusions.json" --out-prefix results/agreement/board100_2026_rerun
  python3 scripts/agreement.py --answers results/answers.csv --case-set board-100 \
    --key pe-2.60.0-board-2025 --others taxcalc-6.9.0-2025 taxsim-cd2026110117-2025 \
    --exclusions "$BOARD/reference_exclusions.json" --out-prefix results/agreement/board100_2025
  python3 scripts/make_bindings.py --runs results/runs.csv --out results/bindings.csv
  python3 scripts/make_dossiers.py --scenarios "$BOARD/scenarios.csv" --reference "$BOARD/reference_outputs.csv" \
    --exclusions "$BOARD/reference_exclusions.json" --out results/dossiers
  python3 scripts/make_fact_map.py --scenarios "$BOARD/scenarios.csv" --out maps/board_facts.csv
  python3 -I scripts/causes/build_causes.py
  python3 -I scripts/causes/build_docs.py
  python3 scripts/make_cell_status.py
  python3 scripts/make_readme_tables.py
}

compare() {
  python3 second_map/taxsim/compare.py
  envs/tc690/bin/python second_map/taxcalc/compare.py
}

tests() {
  uv run --no-project --python 3.12 --with pytest --with hypothesis pytest tests -q
}

case "${1:-}" in
  setup|pe|shared|engines|tables|compare|tests) "$1" ;;
  all) setup; pe; shared; engines; tables; compare; tests ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
