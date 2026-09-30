"""RQ3 analysis per the frozen plan. Usage: python analyze.py rq3/runs/<model>.jsonl [...]
Primary: BalAcc(B3) vs BalAcc(B1) on cross items (natural pairs), T=0. Secondary: B3 vs B4; Δcross = B5 − B3;
stability over k=5 samples at T=0.7 (majority vote); constructed-mutant recall by condition.
Paired item-level exact sign test (McNemar-style on discordant pairs); rule-level bootstrap CI (10k, seed 0)."""
import json, sys, random, math, collections
def load(paths):
    rows = []
    for p in paths:
        for l in open(p): rows.append(json.loads(l))
    return rows
def meta(i):   # "GC1|s3fs|bad|B3"  or mutant "M|GC1|s3fs|m03_SD..|B3"
    parts = i.split("|")
    if parts[0] == "M": return {"stratum": "constructed", "case": parts[1], "impl": parts[2], "version": parts[3], "cond": parts[4]}
    if parts[0] == "PV1": return {"stratum": "prospective", "case": parts[0], "impl": parts[1], "version": parts[2], "cond": parts[3]}
    return {"stratum": "natural", "case": parts[0], "impl": parts[1], "version": parts[2], "cond": parts[3]}
def balacc(pairs):  # list of (label, verdict)
    pos = [v == "DEFECT" for l, v in pairs if l == "DEFECT"]; neg = [v == "CORRECT" for l, v in pairs if l == "CORRECT"]
    if not pos or not neg: return float("nan")
    return 0.5 * (sum(pos) / len(pos) + sum(neg) / len(neg))
def sign_test(wins, losses):
    n = wins + losses
    if n == 0: return 1.0
    k = min(wins, losses); p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)
def verdict_T0(rows):
    d = {}
    for r in rows:
        if r["temperature"] == 0.0: d[(r["model"], r["id"])] = r["verdict"]
    return d
def verdict_vote(rows):
    c = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["temperature"] > 0: c[(r["model"], r["id"])][r["verdict"]] += 1
    return {k: v.most_common(1)[0][0] for k, v in c.items()}
HOLDOUT = {  # frozen plan: target fix merged after model release (Qwen3-Coder) / after stated cutoff 2024-06 (gpt-oss)
    "qwen3-coder": {("GC1", "s3fs"), ("GC2a", "obstore"), ("GC2b", "obstore")},
    "qwen2.5-coder": {("GC1", "s3fs"), ("GC2a", "obstore"), ("GC2b", "obstore"), ("GC3", "opendal")},
    "gpt-oss": {("GC1", "s3fs"), ("GC2a", "obstore"), ("GC2b", "obstore"), ("GC3", "opendal")}}
def holdout_set(model):
    for k, v in HOLDOUT.items():
        if k in model: return v
    return set()
def report(rows, V, title):
    models = sorted({m for m, _ in V}); print(f"\n===== {title} =====")
    for m in models:
        items = {i: v for (mm, i), v in V.items() if mm == m}
        labels = {r["id"]: r["label"] for r in rows}
        nat = {i: v for i, v in items.items() if meta(i)["stratum"] == "natural"}
        print(f"\n## {m}  (unparsed: {sum(v == 'UNPARSED' for v in items.values())})")
        by = collections.defaultdict(list)
        for i, v in nat.items(): by[meta(i)["cond"]].append((labels[i], v))
        for cnd in sorted(by): print(f"  {cnd}: BalAcc={balacc(by[cnd]):.3f}  n={len(by[cnd])}")
        # paired comparisons on items that have both conditions
        def pair(c1, c2):
            w = l = t = 0
            for i, v in nat.items():
                md = meta(i)
                if md["cond"] != c1: continue
                j = "|".join([md["case"], md["impl"], md["version"], c2])
                if j not in nat: continue
                a = v == labels[i]; b = nat[j] == labels[j]
                w += a and not b; l += b and not a; t += 1
            return w, l, t
        for c1, c2 in (("B3", "B1"), ("B3", "B4"), ("B5", "B3")):
            w, l, t = pair(c1, c2); print(f"  {c1} vs {c2}: {c1} right & {c2} wrong={w}, reverse={l}, paired items={t}, exact p={sign_test(w, l):.3f}")
        # per rule
        for case in sorted({meta(i)["case"] for i in nat}):
            s = []
            for cnd in ("B1", "B3", "B4", "B5"):
                pr = [(labels[i], v) for i, v in nat.items() if meta(i)["case"] == case and meta(i)["cond"] == cnd]
                s.append(f"{cnd}={balacc(pr):.2f}" if pr else f"{cnd}=  - ")
            print(f"  rule {case:5s}: " + "  ".join(s))
        # rule-level bootstrap of BalAcc(B3)-BalAcc(B1)
        cases = sorted({meta(i)["case"] for i in nat}); rnd = random.Random(0); diffs = []
        for _ in range(10000):
            pick = [rnd.choice(cases) for _ in cases]
            b3 = [(labels[i], v) for c in pick for i, v in nat.items() if meta(i)["case"] == c and meta(i)["cond"] == "B3"]
            b1 = [(labels[i], v) for c in pick for i, v in nat.items() if meta(i)["case"] == c and meta(i)["cond"] == "B1"
                  and "|".join([meta(i)["case"], meta(i)["impl"], meta(i)["version"], "B3"]) in nat]
            x, y = balacc(b3), balacc(b1)
            if not (math.isnan(x) or math.isnan(y)): diffs.append(x - y)
        diffs.sort()
        if diffs: print(f"  Δ(B3−B1) rule-bootstrap 95% CI: [{diffs[int(.025*len(diffs))]:.3f}, {diffs[int(.975*len(diffs))]:.3f}]")
        ho = holdout_set(m)
        if ho:
            for cnd in ("B1", "B3", "B4", "B5"):
                pr = [(labels[i], v) for i, v in nat.items() if (meta(i)["case"], meta(i)["impl"]) in ho and meta(i)["cond"] == cnd]
                if pr: print(f"  temporal-holdout {cnd}: BalAcc={balacc(pr):.3f} n={len(pr)}")
        con = collections.defaultdict(list)
        for i, v in items.items():
            if meta(i)["stratum"] == "constructed": con[meta(i)["cond"]].append(v == "DEFECT")
        for cnd in sorted(con): print(f"  constructed recall {cnd}: {sum(con[cnd])}/{len(con[cnd])}")
        pv = {i: v for i, v in items.items() if meta(i)["stratum"] == "prospective"}
        for cnd in sorted({meta(i)["cond"] for i in pv}):
            got = {meta(i)["version"]: v for i, v in pv.items() if meta(i)["cond"] == cnd}
            print(f"  prospective PV1 {cnd}: live-bug(bad)->{got.get('bad')}  patched(good)->{got.get('good')}")
if __name__ == "__main__":
    rows = load(sys.argv[1:]); report(rows, verdict_T0(rows), "T=0 (primary)"); report(rows, verdict_vote(rows), "majority of k samples at T=0.7")
