"""Frozen analysis -> JSON + LaTeX tables for the paper (no hand-copied numbers).
Usage: python results_to_latex.py <runs.jsonl>... ; writes rq3/rq3_results.json, paper_fse/tab_rq3*.tex"""
import json, sys, os, math, random, collections
sys.path.insert(0, os.path.dirname(__file__)); import analyze as A
PAPER = os.path.expanduser("./paper")
def compute(rows, V):
    labels = {r["id"]: r["label"] for r in rows}; res = {}
    for m in sorted({mm for mm, _ in V}):
        items = {i: v for (mm, i), v in V.items() if mm == m}
        nat = {i: v for i, v in items.items() if A.meta(i)["stratum"] == "natural"}
        d = {"unparsed": sum(v == "UNPARSED" for v in items.values()), "cond": {}, "pairs": {}, "rules": {}, "holdout": {}}
        for c in ("B1", "B3", "B4", "B5"):
            pr = [(labels[i], v) for i, v in nat.items() if A.meta(i)["cond"] == c]
            if pr: d["cond"][c] = {"balacc": A.balacc(pr), "n": len(pr)}
        def pair(c1, c2, subset=None):
            w = l = t = 0
            for i, v in nat.items():
                md = A.meta(i)
                if md["cond"] != c1 or (subset and (md["case"], md["impl"]) not in subset): continue
                j = "|".join([md["case"], md["impl"], md["version"], c2])
                if j not in nat: continue
                a = v == labels[i]; b = nat[j] == labels[j]; w += a and not b; l += b and not a; t += 1
            # balanced accuracy on the paired item set
            ids1 = [i for i in nat if A.meta(i)["cond"] == c1 and "|".join([A.meta(i)["case"], A.meta(i)["impl"], A.meta(i)["version"], c2]) in nat
                    and (not subset or (A.meta(i)["case"], A.meta(i)["impl"]) in subset)]
            ids2 = ["|".join([A.meta(i)["case"], A.meta(i)["impl"], A.meta(i)["version"], c2]) for i in ids1]
            return {"wins": w, "losses": l, "paired": t, "p": A.sign_test(w, l),
                    "balacc_1": A.balacc([(labels[i], nat[i]) for i in ids1]), "balacc_2": A.balacc([(labels[i], nat[i]) for i in ids2])}
        for c1, c2 in (("B3", "B1"), ("B3", "B4"), ("B5", "B3")): d["pairs"][f"{c1}_vs_{c2}"] = pair(c1, c2)
        cases = sorted({A.meta(i)["case"] for i in nat}); rnd = random.Random(0); diffs = []
        for _ in range(10000):
            pick = [rnd.choice(cases) for _ in cases]; b3 = []; b1 = []
            for c in pick:
                for i, v in nat.items():
                    md = A.meta(i)
                    if md["case"] != c: continue
                    if md["cond"] == "B3": b3.append((labels[i], v))
                    if md["cond"] == "B1" and "|".join([md["case"], md["impl"], md["version"], "B3"]) in nat: b1.append((labels[i], v))
            x, y = A.balacc(b3), A.balacc(b1)
            if not (math.isnan(x) or math.isnan(y)): diffs.append(x - y)
        diffs.sort(); d["delta_B3_B1_ci"] = [diffs[int(.025 * len(diffs))], diffs[int(.975 * len(diffs))]] if diffs else None
        for case in cases:
            d["rules"][case] = {}
            for c in ("B1", "B3", "B4", "B5"):
                pr = [(labels[i], v) for i, v in nat.items() if A.meta(i)["case"] == case and A.meta(i)["cond"] == c]
                if pr: d["rules"][case][c] = {"balacc": A.balacc(pr), "n": len(pr)}
        ho = A.holdout_set(m)
        if ho: d["holdout"] = {"set": sorted("/".join(x) for x in ho), "B3_vs_B1": pair("B3", "B1", ho)}
        pv = {i: v for i, v in items.items() if A.meta(i)["stratum"] == "prospective"}
        d["prospective"] = {A.meta(i)["cond"] + ":" + A.meta(i)["version"]: v for i, v in pv.items()}
        con = collections.defaultdict(list)
        for i, v in items.items():
            if A.meta(i)["stratum"] == "constructed": con[A.meta(i)["cond"]].append(v == "DEFECT")
        d["constructed_recall"] = {c: [sum(x), len(x)] for c, x in con.items()}
        res[m] = d
    return res
def f(x): return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"
def pretty(m): return {"ollama:qwen3-coder:30b": "Qwen3-Coder-30B-A3B", "ollama:gpt-oss:20b": "gpt-oss-20b",
                       "ollama:qwen2.5-coder:32b": "Qwen2.5-Coder-32B"}.get(m, m)
def main(paths):
    rows = [json.loads(l) for p in paths for l in open(p)]
    out = {"T0": compute(rows, A.verdict_T0(rows)), "vote": compute(rows, A.verdict_vote(rows))}
    json.dump(out, open("rq3/rq3_results.json", "w"), indent=1)
    L = ["\\begin{tabular}{@{}ll rrrr rrr rrr@{}}\\toprule",
         " & & \\multicolumn{4}{c}{B3 vs.\\ B1 (primary, paired)} & \\multicolumn{3}{c}{B3 vs.\\ B4 (paired)} & \\multicolumn{3}{c}{B5 vs.\\ B3 (paired)} \\\\",
         "\\cmidrule(lr){3-6}\\cmidrule(lr){7-9}\\cmidrule(lr){10-12}",
         "Model & Dec. & B1 & B3 & W/L & $p$ & B4 & W/L & $p$ & B5 & W/L & $p$ \\\\ \\midrule"]
    for dec, name in (("T0", "$T{=}0$"), ("vote", "vote")):
        for m, d in out[dec].items():
            a = d["pairs"]["B3_vs_B1"]; b = d["pairs"]["B3_vs_B4"]; c = d["pairs"]["B5_vs_B3"]
            L.append(f"{pretty(m)} & {name} & {f(a['balacc_2'])} & {f(a['balacc_1'])} & {a['wins']}/{a['losses']} & {a['p']:.2f} & "
                     f"{f(b['balacc_2'])} & {b['wins']}/{b['losses']} & {b['p']:.2f} & {f(c['balacc_1'])} & {c['wins']}/{c['losses']} & {c['p']:.2f} \\\\")
    L += ["\\bottomrule\\end{tabular}"]
    ci = {m: d["delta_B3_B1_ci"] for m, d in out["T0"].items()}
    json.dump({"ci_T0": ci, "paired_n": {m: d["pairs"]["B3_vs_B1"]["paired"] for m, d in out["T0"].items()},
               "paired_n_B5": {m: d["pairs"]["B5_vs_B3"]["paired"] for m, d in out["T0"].items()}}, open("rq3/rq3_textnums.json", "w"), indent=1)
    open(f"{PAPER}/tab_rq3_main.tex", "w").write("\n".join(L))
    R = ["\\begin{tabular}{@{}ll" + "rrrr" + "@{}}\\toprule", "Model & Rule & B1 & B3 & B4 & B5 \\\\ \\midrule"]
    for m, d in out["T0"].items():
        for case, cc in d["rules"].items():
            R.append(f"{pretty(m)} & \\gc{{{case}}} & " + " & ".join(f(cc.get(c, {}).get('balacc')) for c in ("B1", "B3", "B4", "B5")) + " \\\\")
        R.append("\\midrule")
    R[-1] = "\\bottomrule\\end{tabular}"
    open(f"{PAPER}/tab_rq3_rules.tex", "w").write("\n".join(R))
    print(json.dumps({m: {"cond": d["cond"], "B3vB1": d["pairs"]["B3_vs_B1"], "ci": d["delta_B3_B1_ci"], "holdout": d.get("holdout", {}).get("B3_vs_B1")} for m, d in out["T0"].items()}, indent=1)[:2500])
if __name__ == "__main__":
    main(sys.argv[1:])

def rates_table(paths):
    """Hit / false-alarm decomposition at T=0 (natural items) + exploratory A1 (mechanism named) + post-hoc
    mechanism naming in false alarms. Writes paper_fse/tab_rq3_rates.tex"""
    import re, exploratory as E
    rows = [json.loads(l) for p in paths for l in open(p)]
    L = ["\\begin{tabular}{@{}l l rrr rr@{}}\\toprule",
         " & & \\multicolumn{3}{c}{DEFECT verdicts (natural items)} & \\multicolumn{2}{c}{names mechanism} \\\\",
         "\\cmidrule(lr){3-5}\\cmidrule(lr){6-7}",
         "Model & Cond. & on violating & on satisfying & unparsed & hits$^{a}$ & false alarms$^{b}$ \\\\ \\midrule"]
    for m in sorted({r["model"] for r in rows}):
        for c in ("B1", "B3", "B4", "B5"):
            X = [r for r in rows if r["model"] == m and r["temperature"] == 0 and A.meta(r["id"])["stratum"] == "natural" and A.meta(r["id"])["cond"] == c]
            bad = [r for r in X if r["label"] == "DEFECT"]; good = [r for r in X if r["label"] == "CORRECT"]
            hits = [r for r in bad if r["verdict"] == "DEFECT"]; fas = [r for r in good if r["verdict"] == "DEFECT"]
            nm = lambda Z: sum(bool(re.search(E.KW[A.meta(r["id"])["case"]], r.get("scenario") or "", re.I)) for r in Z)
            L.append(f"{pretty(m)} & {c} & {len(hits)}/{len(bad)} & {len(fas)}/{len(good)} & {sum(r['verdict']=='UNPARSED' for r in X)} & "
                     f"{nm(hits)}/{len(hits)} & {nm(fas)}/{len(fas)} \\\\")
        L.append("\\midrule")
    L[-1] = "\\bottomrule\\end{tabular}"
    open(f"{PAPER}/tab_rq3_rates.tex", "w").write("\n".join(L))

if __name__ == "__main__" and len(sys.argv) > 1:
    rates_table(sys.argv[1:])
