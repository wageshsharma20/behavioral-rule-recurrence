#!/usr/bin/env bash
# mk_s3env.sh <s3fs-version> <release-date YYYY-MM-DD> : era-matched env (deps resolved as of release date)
set -u; cd "$(dirname "$0")/../envs"; V=$1; D=$(date -j -v+3d -f %Y-%m-%d "$2" +%Y-%m-%d); E=s3fs-$V
envs_ok(){ $E/bin/python -c "import s3fs,boto3" 2>/dev/null; }
envs_ok && exit 0
rm -rf $E; uv venv -q -p /usr/bin/python3 $E
VIRTUAL_ENV=$PWD/$E uv pip install -q --exclude-newer "${D}T23:59:59Z" "s3fs[boto3]==$V" >/dev/null 2>&1
envs_ok || { echo "INSTALL FAILED $V" >&2; exit 1; }
