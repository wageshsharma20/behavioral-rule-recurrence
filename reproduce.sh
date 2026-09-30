#!/usr/bin/env bash
# One-command reproduction of a Golden Case (or all of them) from a clean checkout of this package.
#   ./reproduce.sh GC3        # also: GC1, GC2a, GC2b, PV1, all
# Requires: uv (https://docs.astral.sh/uv/), bash, nc, perl. Builds the needed environments from oracle/env_locks/,
# starts a fresh emulator per run (moto 5.2.3 for S3; fake-gcs-server 1.56.1 for GCS, fetched on demand), and runs the
# case's discriminating assertion on the last violating and first satisfying release of every implementation.
# Expected: every violating row reports got=False, every satisfying row got=True, each marked OK.
set -u; cd "$(dirname "$0")"; CASE=${1:-GC3}; mkdir -p envs tools
command -v uv >/dev/null || { echo "please install uv first: https://docs.astral.sh/uv/"; exit 1; }
HOST="$(uname -s)-$(uname -m)"
mkenv(){ # build envs/<name> from oracle/env_locks/<name>.txt unless it exists
  local E=$1 L=oracle/env_locks/$1.txt PYV ARCH SPEC
  [ -x envs/$E/bin/python ] && return 0
  [ -f "$L" ] || { echo "no lock file for $E"; return 1; }
  read -r _ _ PYV ARCH < <(grep '^# python' "$L"); SPEC=${PYV%.*}
  [ "$ARCH" = x86_64 ] && [ "$HOST" = Darwin-arm64 ] && SPEC="cpython-${SPEC}-macos-x86_64"   # Rosetta, as in the study
  echo "building envs/$E (python $SPEC)"
  uv venv -q -p "$SPEC" envs/$E && grep -v '^#' "$L" | VIRTUAL_ENV=$PWD/envs/$E uv pip install -q -r /dev/stdin \
    || { echo "could not build $E"; rm -rf envs/$E; return 1; }
}
ROWS=$(grep -E '^row ' oracle/verify_golden.sh | { [ "$CASE" = all ] && cat || grep -E "^row $CASE"; })
[ -z "$ROWS" ] && { echo "unknown case $CASE (use GC1, GC2a, GC2b, GC3, PV1 or all)"; exit 1; }
mkenv s3fs-bad || exit 1                                   # provides moto_server (moto 5.2.3)
for E in $(echo "$ROWS" | awk '{print $6}' | sort -u); do mkenv "$E"; done
if echo "$ROWS" | awk '{print $4}' | grep -q gcs && [ ! -x tools/fgs-1.56.1/fake-gcs-server ]; then
  case "$HOST" in Darwin-arm64) A=Darwin_arm64;; Darwin-x86_64) A=Darwin_amd64;; Linux-x86_64) A=Linux_amd64;; Linux-aarch64) A=Linux_arm64;; esac
  echo "fetching fake-gcs-server 1.56.1 ($A)"; mkdir -p tools/fgs-1.56.1
  curl -sSL "https://github.com/fsouza/fake-gcs-server/releases/download/v1.56.1/fake-gcs-server_1.56.1_${A}.tar.gz" \
    | tar -xz -C tools/fgs-1.56.1 fake-gcs-server || echo "could not fetch fake-gcs-server; GCS rows will fail"
fi
shasum -a 256 -c oracle/FROZEN_v1.sha256 >/dev/null && echo "oracle files match the frozen hashes" || echo "WARNING: oracle files differ from the frozen hashes"
CASE=$CASE oracle/verify_golden.sh
