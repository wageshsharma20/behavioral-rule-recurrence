#!/usr/bin/env bash
# Self-consistency check of every Golden-Case / PV1 verification row (see self_consistency.py). Fresh backend per row.
set -u; cd "$(dirname "$0")/../.."; OUT=oracle/wire/out; mkdir -p $OUT; : > $OUT/self_consistency.jsonl
row(){ local C=$1 OP=$2 CL=$3 B=$4 E=$5 X=$6
  [ -x envs/$E/bin/python ] || { echo "SKIP $C $E"; return; }
  if [ "$B" = gcs ]; then lsof -ti:4443 | xargs kill 2>/dev/null; sleep 0.3
    TZ=UTC tools/fgs-1.56.1/fake-gcs-server -scheme http -port 4443 -public-host localhost:4443 -external-url http://localhost:4443 -backend memory >/tmp/fgs.log 2>&1 & P=$!; UPP=4443
  else lsof -ti:5555 | xargs kill 2>/dev/null; sleep 0.3; envs/s3fs-bad/bin/moto_server -p 5555 >/tmp/moto.log 2>&1 & P=$!; UPP=5555; fi
  for i in $(seq 1 40); do nc -z 127.0.0.1 $UPP 2>/dev/null && break; sleep 0.25; done
  R=$(XF_BACKEND=$B XF_S3=http://127.0.0.1:5555 XF_GCS=http://localhost:4443 GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT=false \
      perl -e 'alarm 600; exec @ARGV' envs/$E/bin/python oracle/wire/self_consistency.py $OP $CL 2>/dev/null | tail -1)
  kill $P 2>/dev/null; wait $P 2>/dev/null
  echo "{\"case\":\"$C\",\"env\":\"$E\",\"violating\":$([ $X = false ] && echo true || echo false),\"r\":${R:-null}}" >> $OUT/self_consistency.jsonl
  echo "$C $E viol=$([ $X = false ] && echo Y || echo N) -> ${R:0:230}"
}
row GC1 gc1 pyarrow s3 pyarrow-14.0.1 false
row GC1 gc1 pyarrow s3 pyarrow-14.0.2 true
row GC1 gc1 s3fs s3 s3fs-good false
row GC1 gc1 s3fs s3 s3fs-2026.9.0 true
row GC2a write s3path s3 s3path-0.3.1 false
row GC2a write s3path s3 s3path-0.3.2 true
row GC2a read gcsfs gcs gcsfs-2022.8.2 false
row GC2a read gcsfs gcs gcsfs-2023.1.0 true
row GC2a write obstore s3 obstore-0.6.0 false
row GC2a write obstore s3 obstore-0.8.2 true
row GC2b copy pyarrow s3 pyarrow-4.0.1 false
row GC2b copy pyarrow s3 pyarrow-5.0.0 true
row GC2b copy obstore s3 obstore-0.9.3 false
row GC2b copy obstore s3 obstore-0.9.4 true
row GC3 exists cloudpathlib s3 cloudpathlib-0.9.0 false
row GC3 exists cloudpathlib s3 cloudpathlib-0.10.0 true
row GC3 exists opendal s3 opendal-0.45.9 false
row GC3 exists opendal s3 opendal-0.45.10 true
row PV1 movedir gcsfs gcs gcsfs-2023.6.0 false
row PV1 movedir gcsfs gcs gcsfs-2023.9.0 true
row PV1 movedir s3path s3 s3path-0.6.5 false
