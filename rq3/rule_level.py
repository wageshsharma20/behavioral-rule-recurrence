"""RQ3 at the rule level (the unit of replication): for each rule, balanced accuracy on the natural items that have both
a code-only (B1) and a cross-implementation-history (B3) version, and the paired difference. T=0.
Runs: the two frozen runs (primary) and the gpt-oss output-budget rerun R1 (sensitivity).
Writes rq3/rule_level_results.json and paper/tab_rq3_rules.tex."""
import json, os, sys, collections, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import analyze as A
os.chdir(os.path.dirname(HERE)); PAPER = os.path.expanduser("./paper")
RUNS = [("gpt-oss-20b", "rq3/runs/ollama_gpt-oss_20b.jsonl"), ("Qwen3-Coder", "rq3/runs/ollama_qwen3-coder_30b.jsonl"),
        ("gpt-oss-20b, R1", "rq3/runs_R1/runs/ollama_gpt-oss_20b_R1_budget16k.jsonl")]
def f(x): return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"
def d(x): return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else (f"{x:+.2f}" if abs(x) > 1e-9 else "0.00")
out = {}
for name, path in RUNS:
    if not os.path.exists(path): continue
    rows = [json.loads(l) for l in open(path)]
    V = {i: v for (m, i), v in A.verdict_T0(rows).items()}; lab = {r["id"]: r["label"] for r in rows}
    nat = {i: v for i, v in V.items() if A.meta(i)["stratum"] == "natural"}
    per = collections.defaultdict(lambda: {"B1": [], "B3": [], "B4": [], "B5": []})
    for i in nat:
        md = A.meta(i)
        if md["cond"] != "B3": continue
        key = lambda c: "|".join([md["case"], md["impl"], md["version"], c])
        if key("B1") not in nat: continue
        for c in ("B1", "B3", "B4", "B5"):
            if key(c) in nat: per[md["case"]][c].append((lab[key(c)], nat[key(c)]))
            if key(c) in nat: per["all"][c].append((lab[key(c)], nat[key(c)]))
    res = {}
    for case, p in per.items():
        r = {c: (A.balacc(p[c]) if p[c] else None) for c in ("B1", "B3", "B4", "B5")}
        r["n"] = len(p["B3"]); r["delta"] = r["B3"] - r["B1"]; res[case] = r
    out[name] = res
json.dump(out, open("rq3/rule_level_results.json", "w"), indent=1)
names = [n for n, _ in RUNS if n in out]
L = ["\\begin{tabular}{@{}lr" + "rrr" * len(names) + "@{}}\\toprule",
     " & & " + " & ".join(f"\\multicolumn{{3}}{{c}}{{{n}}}" for n in names) + " \\\\",
     "".join(f"\\cmidrule(lr){{{3 + 3 * k}-{5 + 3 * k}}}" for k in range(len(names))),
     "Rule & Items & " + " & ".join(["B1 & B3 & $\\Delta$"] * len(names)) + " \\\\ \\midrule"]
for case in ["GC1", "GC2a", "GC2b", "GC3", "all"]:
    label = "All rules" if case == "all" else f"\\gc{{{case}}}"
    if case == "all": L.append("\\midrule")
    n = out[names[0]][case]["n"]
    L.append(f"{label} & {n} & " + " & ".join(f"{f(out[m][case]['B1'])} & {f(out[m][case]['B3'])} & {d(out[m][case]['delta'])}" for m in names) + " \\\\")
L.append("\\bottomrule\\end{tabular}")
open(f"{PAPER}/tab_rq3_rules.tex", "w").write("\n".join(L))
for m in names: print(m, {c: (round(v["B1"], 2), round(v["B3"], 2), round(v["delta"], 2), v["n"]) for c, v in out[m].items()})
