#!/usr/bin/env bash
# Prospective case PV1: run oracle/pv1_oracle.py on s3path 0.6.5, released and patched (rq3/pv1_fix.patch), on both of
# its code paths (Python < 3.12: old_versions.py; Python >= 3.12: accessor.py). A fresh moto server per run.
# Environments: envs/s3path-0.6.5 (py3.10), envs/s3path-0.6.5-py312, envs/s3path-pv1 (py3.10, patched),
# envs/s3path-pv1-py312 (patched). Output: oracle/pv1_results.json
set -u; cd "$(dirname "$0")/.."; PORT=5573; export XF_S3=http://127.0.0.1:$PORT; OUT=oracle/pv1_results.json
echo "{" > $OUT; first=1
for spec in "released_py310:s3path-0.6.5" "released_py312:s3path-0.6.5-py312" "patched_py310:s3path-pv1" "patched_py312:s3path-pv1-py312"; do
  name=${spec%%:*}; env=${spec#*:}
  lsof -ti:$PORT | xargs kill 2>/dev/null; sleep 0.3
  envs/s3fs-bad/bin/moto_server -p $PORT >/dev/null 2>&1 & M=$!
  for i in $(seq 1 60); do nc -z 127.0.0.1 $PORT 2>/dev/null && break; sleep 0.25; done
  res=$(envs/$env/bin/python oracle/pv1_oracle.py 2>/dev/null); kill $M 2>/dev/null; wait $M 2>/dev/null
  py=$(envs/$env/bin/python -c 'import sys; print(sys.version.split()[0])')
  [ $first = 1 ] || echo "," >> $OUT; first=0
  printf '"%s": {"python": "%s", "env": "%s", "result": %s}' "$name" "$py" "$env" "${res:-null}" >> $OUT
done
echo "}" >> $OUT
python3 -c "
import json; d = json.load(open('$OUT'))
for k, v in d.items():
    r = v['result']; print(f\"{k:15s} py{v['python']:8s} rule holds: {r['VERDICT_rule_holds']}  control: {r['A4_control']['pass']}\")"
