"""Classification of every fix/regression event of the frozen run (Table 5 of the paper).

Input: oracle/frozen_stats.json (written by oracle/frozen_stats.py from oracle/results_v1 only).
Every event must be classified exactly once; the script fails if an event is missing or unknown.
It also lists, for every event, the exception types observed on its failing side, so that failures
unrelated to the probe's rule can be recognized (see UNRELATED below).
Output: oracle/event_classification.json and a printed summary.
"""
import json, collections, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
R = "oracle/results_v1"
st = json.load(open("oracle/frozen_stats.json"))

# (client, backend, from, to, direction) -> (category, case or None, note)
C = {
 # --- Golden Cases -----------------------------------------------------------------------------
 ("pyarrow", "s3", "13.0.0", "14.0.0", "P->F"): ("golden", "GC1", "Arrow regression: batch delete names d/sub instead of marker d/sub/"),
 ("pyarrow", "s3", "14.0.1", "14.0.2", "F->P"): ("golden", "GC1", "Arrow repair (GH-38618 / PR 38845)"),
 ("s3fs", "s3", "2025.12.0", "2026.9.0", "F->P"): ("golden", "GC1", "s3fs fix (issue 918 / PR 1005)"),
 ("s3path", "s3", "0.3.1", "0.3.2", "F->P"): ("golden", "GC2a", "s3path fix (issue 77 / PR 78): as_uri() encoding removed; "
   "the same window also changes the contested rule (listing excludes the directory's own marker; commit 33e6d17, PR 81)"),
 ("s3path", "s3", "0.3.2", "0.3.3", "F->P"): ("golden", "GC2a", "s3path: '?' in keys no longer dropped"),
 ("gcsfs", "gcs", "2022.8.2", "2023.1.0", "F->P"): ("golden", "GC2a", "gcsfs fix (issue 447 / PR 502): '#' and '?' escaped in URLs"),
 ("obstore", "s3", "0.6.0", "0.8.2", "F->P"): ("golden", "GC2a", "obstore fix (issue 496 / PR 524): Path::from -> Path::parse"),
 ("pyarrow", "s3", "4.0.1", "5.0.0", "F->P"): ("golden", "GC2b", "Arrow fix (GH-28758 / PR 10526): copy source no longer double-encoded"),
 ("obstore", "s3", "0.9.3", "0.9.4", "F->P"): ("golden", "GC2b", "obstore fix (issue 671 / PR 672): copy/rename source not percent-encoded"),
 ("cloudpathlib", "s3", "0.9.0", "0.10.0", "F->P"): ("golden", "GC3", "cloudpathlib fix (issue 208 / PR 244): prefix listing keeps separator"),
 ("opendal", "s3", "0.45.9", "0.45.10", "F->P"): ("golden", "GC3", "OpenDAL change (PR 4959): list(path) keeps separator"),
 # --- rule interaction ---------------------------------------------------------------------------
 ("gcsfs", "gcs", "2022.7.1", "2022.8.2", "P->F"): ("interaction", None, "gcsfs find() rewrite lists by string prefix: copy/move/delete cross the segment boundary"),
 ("gcsfs", "gcs", "2023.6.0", "2023.9.0", "F->P"): ("interaction", None, "gcsfs repair of the segment boundary (attributed at commit level)"),
 # --- contested rule (listing includes the directory's own marker?) ------------------------------
 ("opendal", "s3", "0.45.9", "0.45.10", "P->F"): ("contested", None, "OpenDAL changes towards including the marker"),
 ("cloudpathlib", "s3", "0.10.0", "0.11.0", "F->P"): ("contested", None, "cloudpathlib changes towards excluding the marker"),
 # --- glob semantics, excluded --------------------------------------------------------------------
 ("cloudpathlib", "s3", "0.12.0", "0.12.1", "F->P"): ("glob_excluded", None, "glob"),
 ("s3fs", "s3", "2023.4.0", "2023.9.0", "F->P"): ("glob_excluded", None, "glob; flip in inherited fsspec code"),
 ("s3path", "s3", "0.3.4", "0.4.1", "P->F"): ("glob_excluded", None, "glob; 44-commit refactoring"),
 ("s3path", "s3", "0.4.1", "0.5.0", "F->P"): ("glob_excluded", None, "glob; 44-commit refactoring"),
 # --- single-implementation events --------------------------------------------------------------
 ("cloudpathlib", "s3", "0.11.0", "0.12.0", "P->F"): ("single", None, "trailing slash on a file"),
 ("gcsfs", "gcs", "2022.2.0", "2022.3.0", "F->P"): ("single", None, "trailing slash on a file"),
 ("gcsfs", "gcs", "2024.6.1", "2026.8.1", "P->F"): ("single", None, "trailing slash on a file"),
 ("gcsfs", "gcs", "2024.6.1", "2026.8.1", "F->P"): ("single", None, "marker-only directory reported as directory"),
 ("pyarrow", "s3", "13.0.0", "14.0.0", "F->P"): ("single", None, "delete of a directory containing a key with '//' (GH-38821 family)"),
 ("s3fs", "s3", "2025.12.0", "2026.9.0", "P->F"): ("single", None, "move of an implicit directory"),
 # --- failure unrelated to the probes' rule -------------------------------------------------------
 ("s3path", "s3", "0.3.0", "0.3.1", "F->P"): ("unrelated_failure", None,
   "s3path 0.3.0 passes its endpoint configuration to smart_open via session/resource_kwargs, which smart_open 5.0.0 "
   "(resolved as of the release date) no longer accepts; every read and write fails with NoCredentialsError. 0.3.1 "
   "passes client=...; the two '~' probes then pass. Not a flip of the probes' rule."),
}
UNRELATED = {("s3path", "s3", "0.3.0"): "NoCredentialsError on every read/write (see event note)"}

def load(cl, be, orc, ver):
    d = f"{R}/{orc}__{be}"
    for f in os.listdir(d):
        if f.startswith(cl + "-") and f.endswith(".json"):
            r = json.load(open(f"{d}/{f}"))
            v = f[len(cl) + 1:-5]; v = {"bad": "2025.10.0", "good": "2025.12.0"}.get(v, v)
            if v == ver or r.get("version") == ver: return r
    return None

def failing_obs(cl, be, ver, key):
    orc, rest = key.split(":", 1); r = load(cl, be, orc, ver)
    if orc == "f2":
        var, a = rest.split(":"); x = r["variants"][var]; return ("EXC:" + str(x["error"])) if x.get("error") else str(x.get("left"))
    return str(r["probes"][rest].get("obs"))

out, seen = [], set()
for cl, be, a, b, d, keys in st["events"]:
    k = (cl, be, a, b, d)
    if k not in C: sys.exit(f"UNCLASSIFIED EVENT {k}")
    seen.add(k); cat, case, note = C[k]
    fail_ver = a if d == "F->P" else b
    exc = collections.Counter(o.split(":")[1].strip() for o in (failing_obs(cl, be, fail_ver, q) for q in keys) if o.startswith("EXC:"))
    out.append({"client": cl, "backend": be, "from": a, "to": b, "direction": d, "n_transitions": len(keys),
                "category": cat, "case": case, "note": note, "failing_side_exceptions": dict(exc),
                "failing_side_not_evaluable": UNRELATED.get((cl, be, fail_ver)), "probes": keys})
missing = set(C) - seen
if missing: sys.exit(f"CLASSIFIED BUT NOT IN FROZEN RUN: {missing}")
cnt = collections.Counter(e["category"] for e in out)
gc = collections.Counter(e["case"] for e in out if e["category"] == "golden")
fix_total = sum(1 for e in out if e["direction"] == "F->P")
fix_golden = sum(1 for e in out if e["direction"] == "F->P" and e["category"] == "golden")
print("events:", len(out), dict(cnt)); print("golden by case:", dict(sorted(gc.items())))
print(f"fix events (F->P): {fix_total}; of which Golden: {fix_golden}")
for e in out:
    if e["failing_side_not_evaluable"]: print("unrelated failure:", e["client"], e["from"], "->", e["to"], e["probes"])
json.dump({"counts": cnt, "golden_by_case": gc, "fix_events": fix_total, "golden_fix_events": fix_golden,
           "not_evaluable_releases": {"|".join(k): v for k, v in UNRELATED.items()}, "events": out},
          open("oracle/event_classification.json", "w"), indent=1, ensure_ascii=False)
