"""Exploratory analyses A1 (scenario-mechanism coding) and A2 (sample stability), defined in
PLAN_AMENDMENTS_POSTFREEZE.md before any model output was seen."""
import json, re, sys, collections
KW = {"GC1": r"marker|placeholder|trailing slash|/.{0,3}suffix|empty object|zero[- ]byte|directory object",
      "GC2a": r"encod|escap|percent|quote|url-encod|%2|%c3|special char|unicode|'='|\"=\"|'\+'|\"\+\"|'#'|\"#\"",
      "GC3": r"prefix|separator|trailing slash|foobar|sibling|similar name|/.{0,3}suffix|starts with",
      "PV1": r"prefix|separator|sibling|replace|similar name|starts with"}
KW["GC2b"] = KW["GC2a"]
def meta(i):
    p = i.split("|")
    return (p[1], p[4], "constructed") if p[0] == "M" else (p[0], p[3], "prospective" if p[0] == "PV1" else "natural")
def run(paths):
    rows = [json.loads(l) for p in paths for l in open(p)]
    out = {}
    for m in sorted({r["model"] for r in rows}):
        R = [r for r in rows if r["model"] == m]
        a1 = collections.defaultdict(lambda: [0, 0])
        for r in R:
            if r["temperature"] != 0.0 or r["label"] != "DEFECT" or r["verdict"] != "DEFECT": continue
            case, cond, stratum = meta(r["id"])
            if stratum == "constructed": continue
            hit = bool(re.search(KW[case], r.get("scenario") or "", re.I))
            a1[(cond if stratum == "natural" else "PV1-" + cond)][0] += hit; a1[(cond if stratum == "natural" else "PV1-" + cond)][1] += 1
        by = collections.defaultdict(list)
        for r in R:
            if r["temperature"] > 0: by[r["id"]].append(r["verdict"])
        unanimous = sum(1 for v in by.values() if len(set(v)) == 1); n = len(by)
        out[m] = {"A1_mechanism_named": {k: {"named": v[0], "correct_defects": v[1]} for k, v in sorted(a1.items())},
                  "A2_unanimous_items": unanimous, "A2_items_sampled": n}
        print(f"## {m}"); [print(f"  A1 {k}: {v[0]}/{v[1]} correct DEFECT verdicts name the mechanism") for k, v in sorted(a1.items())]
        print(f"  A2 unanimous across samples: {unanimous}/{n}")
    return out
if __name__ == "__main__":
    json.dump(run(sys.argv[1:]), open("rq3/exploratory_results.json", "w"), indent=1)
