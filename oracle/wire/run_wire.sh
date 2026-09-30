#!/usr/bin/env bash
# Request-level check of every Golden-Case verification row (and PV1): fresh backend per row, client traffic
# recorded by tap.py, then analyzed by wire_check.py against the services' documented API semantics.
set -u; cd "$(dirname "$0")/../.."; OUT=oracle/wire/out; mkdir -p $OUT; : > $OUT/rows.jsonl
row(){ # case op client backend env expect
  local C=$1 OP=$2 CL=$3 B=$4 E=$5 X=$6 LOG=$OUT/$1__$5.log
  [ -x envs/$E/bin/python ] || { echo "SKIP $C $E"; return; }
  : > $LOG
  if [ "$B" = gcs ]; then
    lsof -ti:4443 | xargs kill 2>/dev/null; sleep 0.3
    TZ=UTC tools/fgs-1.56.1/fake-gcs-server -scheme http -port 4443 -public-host localhost:4443 -external-url http://localhost:4443 -backend memory >/tmp/fgs.log 2>&1 & P=$!; UPP=4443; TP=4444
  else
    lsof -ti:5555 | xargs kill 2>/dev/null; sleep 0.3
    envs/s3fs-bad/bin/moto_server -p 5555 >/tmp/moto.log 2>&1 & P=$!; UPP=5555; TP=5556
  fi
  lsof -ti:$TP | xargs kill 2>/dev/null
  /usr/bin/python3 oracle/wire/tap.py $TP $UPP $LOG & T=$!
  for i in $(seq 1 40); do nc -z 127.0.0.1 $UPP 2>/dev/null && nc -z 127.0.0.1 $TP 2>/dev/null && break; sleep 0.25; done
  R=$(WIRE_LOG=$LOG XF_BACKEND=$B XF_S3_UP=http://127.0.0.1:5555 XF_S3_TAP=http://127.0.0.1:5556 \
      XF_GCS_UP=http://localhost:4443 XF_GCS_TAP=http://localhost:4444 GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT=false \
      perl -e 'alarm 600; exec @ARGV' envs/$E/bin/python oracle/wire/wire_trace.py $OP $CL 2>$OUT/$1__$5.err | tail -1)
  kill $T $P 2>/dev/null; wait $T $P 2>/dev/null
  echo "{\"case\":\"$C\",\"env\":\"$E\",\"backend\":\"$B\",\"expect\":$X,\"logfile\":\"$LOG\",\"trace\":${R:-null}}" >> $OUT/rows.jsonl
  echo "$C $E -> ${R:0:160}"
}
row GC1  gc1     pyarrow      s3  pyarrow-14.0.1       false
row GC1  gc1     pyarrow      s3  pyarrow-14.0.2       true
row GC1  gc1     s3fs         s3  s3fs-good            false
row GC1  gc1     s3fs         s3  s3fs-2026.9.0        true
row GC2a write   s3path       s3  s3path-0.3.1         false
row GC2a write   s3path       s3  s3path-0.3.2         true
row GC2a read    gcsfs        gcs gcsfs-2022.8.2       false
row GC2a read    gcsfs        gcs gcsfs-2023.1.0       true
row GC2a write   obstore      s3  obstore-0.6.0        false
row GC2a write   obstore      s3  obstore-0.8.2        true
row GC2b copy    pyarrow      s3  pyarrow-4.0.1        false
row GC2b copy    pyarrow      s3  pyarrow-5.0.0        true
row GC2b copy    obstore      s3  obstore-0.9.3        false
row GC2b copy    obstore      s3  obstore-0.9.4        true
row GC3  exists  cloudpathlib s3  cloudpathlib-0.9.0   false
row GC3  exists  cloudpathlib s3  cloudpathlib-0.10.0  true
row GC3  exists  opendal      s3  opendal-0.45.9       false
row GC3  exists  opendal      s3  opendal-0.45.10      true
row PV1  movedir gcsfs        gcs gcsfs-2023.6.0       false
row PV1  movedir gcsfs        gcs gcsfs-2023.9.0       true
row PV1  movedir s3path       s3  s3path-0.6.5         false
