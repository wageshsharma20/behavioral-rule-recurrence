"""R2 portable oracle — find() populating the directory cache must not change ls().

Golden Case #1. Generalises A2 of c1_oracle.py over the TRIGGERS seen in the
three historical fixes:
  s3fs  #492/#493 (2021): ls(root); invalidate_cache(file); find(file); ls(root)
  gcsfs #488      (2022): cold; find(root); ls(root)
  s3fs  #988/#989 (2025): cold; find(root); ls(root)   [needs placeholder objects]

World: built through the RAW storage API (boto3 / GCS JSON API), identical on
both backends (see c1_oracle.py). C1_WORLD=noph drops placeholder objects.
Every probe: reference = ls(d) with a fully cold cache; observed = ls(d) after
the trigger. Rule holds iff observed == reference for every (trigger, target, d).

Usage: python r2_oracle.py gcs|s3  -> one JSON line
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from c1_oracle import build_world_gcs, build_world_s3, BUCKET, obs, norm

R = BUCKET
TARGETS = {"root": R, "subdir": f"{R}/p", "file": f"{R}/q",
           "nested_file": f"{R}/c/c"}
DIRS = [R, f"{R}/p", f"{R}/c"]


def ls(fs, d):
    v = obs(lambda: fs.ls(d, detail=False))
    return norm(v) if isinstance(v, list) else v


def run(fs):
    ref = {}
    for d in DIRS:
        fs.invalidate_cache()
        ref[d] = ls(fs, d)
    out = {"_reference": ref, "probes": {}}
    for tname, t in TARGETS.items():
        # T1: fully cold cache, then find(t)          (gcsfs #488, s3fs #988)
        fs.invalidate_cache()
        obs(lambda: fs.find(t))
        got1 = {d: ls(fs, d) for d in DIRS}
        # T2: warm ls, invalidate only t, then find(t) (s3fs #492 repro)
        fs.invalidate_cache()
        for d in DIRS:
            ls(fs, d)
        fs.invalidate_cache(t)
        obs(lambda: fs.find(t))
        got2 = {d: ls(fs, d) for d in DIRS}
        for trig, got in (("T1_cold", got1), ("T2_partial", got2)):
            bad = {d: got[d] for d in DIRS if got[d] != ref[d]}
            out["probes"][f"{trig}:{tname}"] = {"pass": not bad, "diff": bad}
    out["VERDICT_rule_holds"] = all(p["pass"] for p in out["probes"].values())
    out["failing"] = sorted(k for k, p in out["probes"].items() if not p["pass"])
    return out


if __name__ == "__main__":
    fs = build_world_gcs() if sys.argv[1] == "gcs" else build_world_s3()
    print(json.dumps(run(fs), default=str))
