"""Score an independent adjudication of rule identity against the study's classification.
Usage: python score.py answers.csv KEY.json. 'ambiguous' is reported separately and counted as disagreement in the
strict agreement; kappa is computed on the pairs answered same/different."""
import csv, json, sys
ans = {r["pair"].strip(): r["verdict"].strip().lower() for r in csv.DictReader(open(sys.argv[1])) if r.get("verdict", "").strip()}
key = json.load(open(sys.argv[2]))["key"]
rows = [(p, key[p]["expected"], ans.get(p, "")) for p in sorted(key)]
missing = [p for p, _, a in rows if a == ""]
amb = [p for p, _, a in rows if a == "ambiguous"]
dec = [(p, e, a) for p, e, a in rows if a in ("same", "different")]
agree = sum(e == a for _, e, a in dec)
n = len(dec)
po = agree / n if n else 0
pe = sum((sum(e == c for _, e, _ in dec) / n) * (sum(a == c for _, _, a in dec) / n) for c in ("same", "different")) if n else 0
kappa = (po - pe) / (1 - pe) if n and pe < 1 else float("nan")
print(f"pairs {len(rows)} | answered same/different {n} | ambiguous {len(amb)} | missing {len(missing)}")
print(f"agreement on decided pairs {agree}/{n} ({po:.2f}); strict (ambiguous = disagree) {agree}/{len(rows)}; Cohen's kappa {kappa:.2f}")
for p, e, a in rows:
    if a != e: print(f"  {p}: study={e:9s} reader={a or '-':9s} ({key[p]['source']}: {key[p]['A']} vs {key[p]['B']})")
