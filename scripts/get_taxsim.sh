#!/usr/bin/env bash
# Fetch NBER's TAXSIM binaries as PolicyEngine/policyengine-taxsim bundles them,
# at a pinned commit, and check their SHA-256 sums. This repo does not
# redistribute NBER's binaries.
#
#   scripts/get_taxsim.sh            # download from GitHub at the pinned commit
#   PE_TAXSIM_REPO=~/PolicyEngine/pe-taxsim scripts/get_taxsim.sh   # read a local clone
#
# Writes work/nber/<name>. macOS builds only; the Linux test build is
# resources/taxsimtest/taxsimtest-linux.exe at the same commit.
set -euo pipefail
COMMIT=253cf3f2393e9d3cd486f6e2051b526e89304f64   # policyengine-taxsim main, 2026-11-03
OUT="$(cd "$(dirname "$0")/.." && pwd)/work/nber"
mkdir -p "$OUT"
# name|path in the repo|sha256|NBER build stamp
FILES=(
  "taxsimtest-osx.exe|resources/taxsimtest/taxsimtest-osx.exe|21d36bac648d4403eb2f4a5c39dc5f6fca5f281b86af52cf418f22e958f1ceb2|cd2026110117"
  "taxsim35-osx.exe|resources/taxsim35/taxsim35-osx.exe|0c879416a3bb96f9903cd21aab84108402fd760c4bf280f68aad331f7b57ff1e|cdate-2025Aug23"
)
for entry in "${FILES[@]}"; do
  IFS='|' read -r name path sum stamp <<<"$entry"
  if [[ -n "${PE_TAXSIM_REPO:-}" ]]; then
    git -C "$PE_TAXSIM_REPO" show "$COMMIT:$path" >"$OUT/$name"
  else
    curl -fsSL "https://raw.githubusercontent.com/PolicyEngine/policyengine-taxsim/$COMMIT/$path" -o "$OUT/$name"
  fi
  got=$(shasum -a 256 "$OUT/$name" | cut -d' ' -f1)
  if [[ "$got" != "$sum" ]]; then
    echo "checksum mismatch for $name: $got" >&2
    exit 1
  fi
  chmod +x "$OUT/$name"
  echo "$name $stamp $sum"
done
