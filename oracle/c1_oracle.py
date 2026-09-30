"""C1 portable oracle - placeholder directories vs. directory-cache state.

Candidate rule (subsumes gcsfs #459 and s3fs #989):
    When explicit placeholder objects (keys ending in "/") coexist with other
    objects, what the filesystem reports must NOT depend on whether its
    directory cache is cold or has been populated (e.g. by find()).

World - created IDENTICALLY on both backends through the RAW storage API
(boto3 for S3, the GCS JSON API for fake-gcs-server), so no gcsfs/s3fs
version influences how the state is built:
    p/        empty placeholder object WITH a child
    p/inner   file
    e/        empty placeholder object, no children
    c/c       file under an implicit directory (no placeholder)   [control]
    q         plain file                                          [control]

Assertions use ONLY the generic fsspec API (the oracle).
  A1  find(root) has no duplicate entries (after stripping trailing "/")
  A2  ls(root) is identical with a cold cache and after find() warmed it
      -> transcribes s3fs test_find_ls_fail
  A3  info(root/p) and info(root/p/) are "directory", identical cold/warm,
      and repeated cold calls agree  -> transcribes gcsfs test_dir_marker
  A4  (OBSERVATIONAL, not in verdict) info(root/e) cold == warm

Usage:  python c1_oracle.py gcs|s3   ->  prints one JSON line
"""
import json
import sys
import urllib.request

BUCKET = "c1-oracle"
import os
# C1_WORLD=noph drops the explicit placeholder objects (p/, e/) to test whether
# placeholders are ESSENTIAL to the rule or merely one trigger of it.
_FULL = {"p/": b"", "p/inner": b"data", "e/": b"", "c/c": b"data", "q": b"data"}
KEYS = ({k: v for k, v in _FULL.items() if not k.endswith("/")}
        if os.environ.get("C1_WORLD") == "noph" else _FULL)
GCS_HOST = "http://localhost:4443"
S3_URL = "http://127.0.0.1:5555/"


def build_world_gcs():
    def call(method, url, data=None, ctype="application/json"):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": ctype})
        return urllib.request.urlopen(req, timeout=20).read()
    call("POST", f"{GCS_HOST}/storage/v1/b?project=test",
         json.dumps({"name": BUCKET}).encode())
    for k, v in KEYS.items():
        call("POST", f"{GCS_HOST}/upload/storage/v1/b/{BUCKET}/o"
                     f"?uploadType=media&name={urllib.request.quote(k, safe='')}",
             v, "application/octet-stream")
    import gcsfs
    return gcsfs.GCSFileSystem(endpoint_url=GCS_HOST, token="anon",
                               skip_instance_cache=True)


def build_world_s3():
    import boto3
    c = boto3.client("s3", endpoint_url=S3_URL, region_name="us-east-1",
                     aws_access_key_id="x", aws_secret_access_key="x")
    c.create_bucket(Bucket=BUCKET)
    for k, v in KEYS.items():
        c.put_object(Bucket=BUCKET, Key=k, Body=v)
    import s3fs
    return s3fs.S3FileSystem(key="x", secret="x", skip_instance_cache=True,
                             client_kwargs={"endpoint_url": S3_URL,
                                            "region_name": "us-east-1"})


def norm(paths):
    return sorted(p.rstrip("/") for p in paths)


def check(name, fn, out):
    try:
        ok, detail = fn()
    except Exception as e:  # an exception is a failure of the behaviour
        ok, detail = False, f"{type(e).__name__}: {e}"
    out[name] = {"pass": bool(ok), "detail": detail}


def obs(fn):
    """Every observation is guarded: an exception is RECORDED as the observed
    behaviour (e.g. 'EXC:FileNotFoundError'), never allowed to abort the run."""
    try:
        return fn()
    except Exception as e:
        return f"EXC:{type(e).__name__}"


def run(fs):
    r, R = {}, BUCKET
    info = lambda p: obs(lambda: fs.info(p)["type"])
    # ---- cold cache ----
    fs.invalidate_cache()
    ls_cold = obs(lambda: fs.ls(R, detail=False))
    fs.invalidate_cache()
    ip1 = info(f"{R}/p")
    fs.invalidate_cache()
    ip2 = info(f"{R}/p")
    fs.invalidate_cache()
    ips_cold = info(f"{R}/p/")
    fs.invalidate_cache()
    ie_cold = info(f"{R}/e")
    # ---- warm the cache ----
    fs.invalidate_cache()
    found = obs(lambda: fs.find(R))
    ls_warm = obs(lambda: fs.ls(R, detail=False))
    ip_warm = info(f"{R}/p")
    ie_warm = info(f"{R}/e")
    r["_observed"] = {"ls_cold": ls_cold, "ls_warm": ls_warm, "find": found,
                      "info_p": [ip1, ip2, ips_cold, ip_warm],
                      "info_e": [ie_cold, ie_warm]}

    check("A1_find_no_duplicates",
          lambda: (isinstance(found, list)
                   and len(norm(found)) == len(set(norm(found))), found), r)
    check("A2_ls_cold_equals_warm",
          lambda: (isinstance(ls_cold, list) and isinstance(ls_warm, list)
                   and norm(ls_cold) == norm(ls_warm),
                   {"cold": ls_cold, "warm": ls_warm}), r)
    check("A3_placeholder_is_stable_directory",
          lambda: (ip1 == ip2 == ips_cold == ip_warm == "directory",
                   {"cold1": ip1, "cold2": ip2, "cold_slash": ips_cold,
                    "warm": ip_warm}), r)
    check("A4_observational_empty_placeholder",
          lambda: (ie_cold == ie_warm, {"cold": ie_cold, "warm": ie_warm}), r)
    r["VERDICT_rule_holds"] = all(r[k]["pass"] for k in
                                  ("A1_find_no_duplicates",
                                   "A2_ls_cold_equals_warm",
                                   "A3_placeholder_is_stable_directory"))
    return r


if __name__ == "__main__":
    backend = sys.argv[1]
    fs = build_world_gcs() if backend == "gcs" else build_world_s3()
    print(json.dumps(run(fs), default=str))
