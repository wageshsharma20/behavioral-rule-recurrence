"""Compare every probe verdict of the dependency-era check (oracle/results_era) with the frozen run (oracle/results_v1).
Output: oracle/era_comparison.json and a printed summary."""
import json, os, glob, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FROZEN_NAME = {"s3fs-2025.10.0": "s3fs-bad", "s3fs-2025.12.0": "s3fs-good"}
def verdicts(path):
    r = json.load(open(path))
    if "variants" in r:
        return {f"{v}:{a}": x[a] for v, x in r["variants"].items() for a in ("A_nothing_under_d", "B_sibling_prefix_survives")}
    return {k: p["pass"] for k, p in r["probes"].items()}
out = {"envs": {}, "total_compared": 0, "total_differ": 0}
for f in sorted(glob.glob("oracle/results_era/*__*/*-era.json")):
    orc_be = os.path.basename(os.path.dirname(f)); env = os.path.basename(f)[:-len("-era.json")]
    fz = f"oracle/results_v1/{orc_be}/{FROZEN_NAME.get(env, env)}.json"
    try: a, b = verdicts(fz), verdicts(f)
    except Exception as e:
        out["envs"][f"{orc_be}/{env}"] = {"error": repr(e)[:200]}; continue
    common = [k for k in a if k in b and a[k] is not None and b[k] is not None]
    diff = {k: {"frozen": a[k], "era": b[k]} for k in common if a[k] != b[k]}
    out["envs"][f"{orc_be}/{env}"] = {"compared": len(common), "differ": diff,
                                      "only_frozen": sorted(set(a) - set(b)), "only_era": sorted(set(b) - set(a))}
    out["total_compared"] += len(common); out["total_differ"] += len(diff)
json.dump(out, open("oracle/era_comparison.json", "w"), indent=1)
print(f"verdicts compared: {out['total_compared']}  differing: {out['total_differ']}")
for k, v in out["envs"].items():
    if "error" in v or v["differ"] or v["only_frozen"] or v["only_era"]: print(" ", k, json.dumps(v)[:300])
