#!/usr/bin/env bash
# Dependency-era sensitivity check (post hoc; the frozen run stays primary).
# The frozen run's environments for 4 s3fs and 8 gcsfs releases resolved some dependencies later than release date + 3 d.
# This script rebuilds those releases with every dependency resolved as of release date + 3 d (`uv --exclude-newer`),
# runs the unchanged frozen oracles (hash-checked) with a fresh emulator per run, and writes oracle/results_era/.
# Compare with: python oracle/compare_era.py
set -u; cd "$(dirname "$0")/.."; OUT=oracle/results_era; mkdir -p $OUT
shasum -a 256 -c oracle/FROZEN_v1.sha256 >/dev/null || { echo "ORACLE FILES CHANGED SINCE FREEZE — abort"; exit 1; }
# client version release-date python
SPECS="s3fs 2021.6.0 2021-06-07 /usr/bin/python3
s3fs 2021.6.1 2021-06-23 /usr/bin/python3
s3fs 2025.10.0 2025-10-30 3.12
s3fs 2025.12.0 2025-12-03 3.12
gcsfs 2022.2.0 2022-02-22 3.10
gcsfs 2022.3.0 2022-04-04 3.10
gcsfs 2022.7.1 2022-07-29 3.10
gcsfs 2022.8.2 2022-09-01 3.10
gcsfs 2023.1.0 2023-01-23 3.11
gcsfs 2023.9.0 2023-09-03 3.11
gcsfs 2024.6.1 2024-06-27 3.11
gcsfs 2026.8.1 2026-09-11 3.11"
echo "$SPECS" | while read CL V D PY; do
  E=$CL-$V-era; LIM=$(date -j -v+3d -f %Y-%m-%d "$D" +%Y-%m-%d)
  if ! envs/$E/bin/python -c "import $CL" 2>/dev/null; then
    rm -rf envs/$E; uv venv -q -p "$PY" envs/$E
    # boto3 serves the oracle's raw S3 API; newer s3fs releases no longer define the [boto3] extra, so it is listed explicitly
    PKGS="$CL==$V"; [ $CL = s3fs ] && PKGS="s3fs[boto3]==$V boto3"
    VIRTUAL_ENV=$PWD/envs/$E uv pip install -q --exclude-newer "${LIM}T23:59:59Z" $PKGS > $OUT/$E.install.log 2>&1 || { echo "$E INSTALL FAILED (see $OUT/$E.install.log)"; continue; }
  fi
  VIRTUAL_ENV=$PWD/envs/$E uv pip freeze > $OUT/$E.freeze.txt 2>/dev/null
  if [ $CL = s3fs ]; then BE=s3; PORT=5580; export XF_S3=http://127.0.0.1:$PORT; unset XF_BACKEND; ORCS="xfam xfam2 f2"
  else BE=gcs; PORT=4470; export XF_GCS=http://localhost:$PORT XF_BACKEND=gcs GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT=false; ORCS="xfam xfam2"; fi
  for O in $ORCS; do
    Dd=$OUT/${O}__$BE; mkdir -p $Dd; [ -s $Dd/$E.json ] && continue
    S=oracle/xfam_oracle.py; [ $O = xfam2 ] && S=oracle/xfam2_oracle.py; [ $O = f2 ] && S=oracle/f2_delete_oracle.py
    lsof -ti:$PORT | xargs kill 2>/dev/null; sleep 0.3
    if [ $BE = s3 ]; then envs/s3fs-bad/bin/moto_server -p $PORT >/dev/null 2>&1 & P=$!
    else TZ=UTC tools/fgs-1.56.1/fake-gcs-server -scheme http -port $PORT -public-host localhost:$PORT -external-url http://localhost:$PORT -backend memory >/dev/null 2>&1 & P=$!; fi
    for i in $(seq 1 60); do nc -z 127.0.0.1 $PORT 2>/dev/null && break; sleep 0.25; done
    perl -e 'alarm 1200; exec @ARGV' envs/$E/bin/python $S $CL > $Dd/$E.json 2> $Dd/$E.err || echo "$E $O FAILED"
    kill $P 2>/dev/null; wait $P 2>/dev/null
  done
  echo "$E done"
done
echo "ERA CHECK DONE"
