#!/usr/bin/env bash
# Frozen-oracle full-frame run. Usage: oracle/run_frozen.sh s3|gcs   -> oracle/results_v1/<oracle>__<backend>/<env>.json
set -u; cd "$(dirname "$0")/.."; BE=$1; OUT=oracle/results_v1; mkdir -p $OUT
shasum -a 256 -c oracle/FROZEN_v1.sha256 >/dev/null || { echo "ORACLE FILES CHANGED SINCE FREEZE — abort"; exit 1; }
if [ $BE = s3 ]; then PORT=5570; export XF_S3=http://127.0.0.1:$PORT; FRAME=oracle/frame_s3.txt
else PORT=4450; export XF_GCS=http://localhost:$PORT XF_BACKEND=gcs GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT=false; FRAME=oracle/frame_gcs.txt; fi
start(){ lsof -ti:$PORT | xargs kill 2>/dev/null; sleep 0.3
  if [ $BE = s3 ]; then envs/s3fs-bad/bin/moto_server -p $PORT >/dev/null 2>&1 & else
  TZ=UTC tools/fgs-1.56.1/fake-gcs-server -scheme http -port $PORT -public-host localhost:$PORT -external-url http://localhost:$PORT -backend memory >/dev/null 2>&1 & fi
  P=$!; for i in $(seq 1 60); do nc -z 127.0.0.1 $PORT 2>/dev/null && break; sleep 0.25; done; }
while read E; do
  CL=${E%%-*}; [ $CL = s3fs ] || [ $CL = gcsfs ] || true
  for O in xfam xfam2 f2; do
    [ $O = f2 ] && { [ $BE = gcs ] && continue; case $CL in s3fs|pyarrow|cloudpathlib|opendal) ;; *) continue;; esac; }
    D=$OUT/${O}__$BE; mkdir -p $D; [ -s $D/$E.json ] && continue
    S=oracle/xfam_oracle.py; [ $O = xfam2 ] && S=oracle/xfam2_oracle.py; [ $O = f2 ] && S=oracle/f2_delete_oracle.py
    start; perl -e 'alarm 1200; exec @ARGV' envs/$E/bin/python $S $CL > $D/$E.json 2> $D/$E.err || echo "$E $O FAILED"
    kill $P 2>/dev/null; wait $P 2>/dev/null
  done
done < $FRAME
echo "FROZEN RUN $BE DONE"
