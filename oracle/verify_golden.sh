#!/usr/bin/env bash
# Re-verify every Golden Case: run the discriminating assertion on BAD and GOOD envs; print one table.
# Expected: every BAD row = False (violated), every GOOD row = True, OPEN rows = False.
set -u; cd "$(dirname "$0")/.."
row(){ # case client backend oracle env assertion expect
  local C=$1 CL=$2 B=$3 O=$4 E=$5 A=$6 X=$7 OUT
  [ -n "${CASE:-}" ] && [ "$CASE" != all ] && [[ "$C" != "$CASE"* ]] && return 0   # run one case: CASE=GC3 oracle/verify_golden.sh
  [ -x envs/$E/bin/python ] || { printf "%-30s %-22s SKIPPED (environment missing; run ./reproduce.sh)\n" "$C" "$E"; return 0; }
  if [ "$B" = gcs ]; then
    lsof -ti:4443 | xargs kill 2>/dev/null; sleep 0.3
    TZ=UTC tools/fgs-1.56.1/fake-gcs-server -scheme http -port 4443 -public-host localhost:4443 -external-url http://localhost:4443 -backend memory >/tmp/fgs.log 2>&1 & P=$!
    for i in $(seq 1 40); do nc -z 127.0.0.1 4443 2>/dev/null && break; sleep 0.25; done
  else
    lsof -ti:5555 | xargs kill 2>/dev/null; sleep 0.3
    envs/s3fs-bad/bin/moto_server -p 5555 >/tmp/moto.log 2>&1 & P=$!
    for i in $(seq 1 40); do nc -z 127.0.0.1 5555 2>/dev/null && break; sleep 0.25; done
  fi
  OUT=$(XF_BACKEND=$B GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT=false perl -e 'alarm 900; exec @ARGV' envs/$E/bin/python oracle/$O $CL 2>/dev/null)
  kill $P 2>/dev/null; wait $P 2>/dev/null
  printf '%s' "$OUT" | python3 -c "
import json,sys
try:
    r=json.load(sys.stdin); A='$A'
    if 'variants' in r:  # f2_delete_oracle
        v,a=A.split(':'); got=r['variants'][v][a]
    else: got=r['probes'][A]['pass']
except Exception as e: got='ERR'
ok = (str(got)=='$X')
print(f\"{'$C':30s} {'$E':22s} {'$A':44s} got={str(got):5s} expect=$X  {'OK' if ok else '<<< MISMATCH'}\")"
}
row GC1-delete-markers   pyarrow s3  f2_delete_oracle.py pyarrow-14.0.1  v-nested:A_nothing_under_d False
row GC1-delete-markers   pyarrow s3  f2_delete_oracle.py pyarrow-14.0.2  v-nested:A_nothing_under_d True
row GC1-delete-markers   s3fs    s3  f2_delete_oracle.py s3fs-good       v-nested:A_nothing_under_d False
row GC1-delete-markers   s3fs    s3  f2_delete_oracle.py s3fs-2026.9.0   v-nested:A_nothing_under_d True
row GC2a-key-putget      s3path  s3  xfam_oracle.py s3path-0.3.1    "F3_write_key_exact[café]" False
row GC2a-key-putget      s3path  s3  xfam_oracle.py s3path-0.3.2    "F3_write_key_exact[café]" True
row GC2a-key-putget      gcsfs   gcs xfam_oracle.py gcsfs-2022.8.2  "F3_read[hash#]" False
row GC2a-key-putget      gcsfs   gcs xfam_oracle.py gcsfs-2023.1.0  "F3_read[hash#]" True
row GC2a-key-putget      obstore s3  xfam_oracle.py obstore-0.6.0   "F3_write_key_exact[café]" False
row GC2a-key-putget      obstore s3  xfam_oracle.py obstore-0.8.2   "F3_write_key_exact[café]" True
row GC2b-key-copy        pyarrow s3  xfam_oracle.py pyarrow-4.0.1   "F3b_copy[café]" False
row GC2b-key-copy        pyarrow s3  xfam_oracle.py pyarrow-5.0.0   "F3b_copy[café]" True
row GC2b-key-copy        obstore s3  xfam_oracle.py obstore-0.9.3   "F3b_copy[café]" False
row GC2b-key-copy        obstore s3  xfam_oracle.py obstore-0.9.4   "F3b_copy[café]" True
row GC3-exists-boundary  cloudpathlib s3 xfam_oracle.py cloudpathlib-0.9.0  "F1_stat_string_prefix_notfound[very/similar/prefix]" False
row GC3-exists-boundary  cloudpathlib s3 xfam_oracle.py cloudpathlib-0.10.0 "F1_stat_string_prefix_notfound[very/similar/prefix]" True
row GC3-exists-boundary  opendal s3  xfam_oracle.py opendal-0.45.9  "F1_stat_string_prefix_notfound[very/similar/prefix]" False
row GC3-exists-boundary  opendal s3  xfam_oracle.py opendal-0.45.10 "F1_stat_string_prefix_notfound[very/similar/prefix]" True
row PV1-move-boundary    gcsfs   gcs xfam2_oracle.py gcsfs-2023.6.0 "F15b_move_dir_sibling_untouched[implicit]" False
row PV1-move-boundary    gcsfs   gcs xfam2_oracle.py gcsfs-2023.9.0 "F15b_move_dir_sibling_untouched[implicit]" True
row PV1-move-boundary    s3path  s3  xfam2_oracle.py s3path-0.6.5  "F15b_move_dir_sibling_untouched[implicit]" False
