"""Sensitivity analyses for RQ3 (see protocol/PLAN_AMENDMENTS_POSTFREEZE.md). The frozen analysis stays primary.

P1(b) (post hoc): balanced accuracy excluding UNPARSED answers, T=0, on the items paired for the primary comparison
      (i)  dropping unparsed answers per condition; (ii) dropping every pair in which either answer is unparsed.
R1   (defined before it ran): gpt-oss-20b rerun with a larger output budget (num_predict 16,384, num_ctx 24,576), same
      78 prompts, T=0. Integrity checks, then the frozen analysis code (results_to_latex.compute) on the rerun.
Usage: python rq3/sensitivity.py   -> rq3/sensitivity_results.json
"""
import json, glob, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import analyze as A, results_to_latex as RL
os.chdir(os.path.dirname(HERE))
FROZEN = {"ollama:gpt-oss:20b": "rq3/runs/ollama_gpt-oss_20b.jsonl", "ollama:qwen3-coder:30b": "rq3/runs/ollama_qwen3-coder_30b.jsonl"}
PLAN = "f5de6779689e8c4c"

def load(p): return [json.loads(l) for l in open(p)]
def partner(i, c): md = A.meta(i); return "|".join([md["case"], md["impl"], md["version"], c])

def unparsed_sensitivity(rows):
    V = {i: v for (m, i), v in A.verdict_T0(rows).items()}; lab = {r["id"]: r["label"] for r in rows}
    nat = {i: v for i, v in V.items() if A.meta(i)["stratum"] == "natural"}
    b3 = [i for i in nat if A.meta(i)["cond"] == "B3" and partner(i, "B1") in nat]; b1 = [partner(i, "B1") for i in b3]
    ba = lambda ids: A.balacc([(lab[i], nat[i]) for i in ids])
    keep = [(i, j) for i, j in zip(b3, b1) if nat[i] != "UNPARSED" and nat[j] != "UNPARSED"]
    return {"paired_items": len(b3), "unparsed_B3": sum(nat[i] == "UNPARSED" for i in b3), "unparsed_B1": sum(nat[i] == "UNPARSED" for i in b1),
            "unparsed_all_T0": sum(v == "UNPARSED" for v in V.values()), "n_T0": len(V),
            "as_errors": {"B3": ba(b3), "B1": ba(b1)},
            "drop_per_condition": {"B3": ba([i for i in b3 if nat[i] != "UNPARSED"]), "B1": ba([i for i in b1 if nat[i] != "UNPARSED"])},
            "drop_pairs": {"n": len(keep), "B3": ba([i for i, _ in keep]), "B1": ba([j for _, j in keep])}}

out = {"P1b": {m: unparsed_sensitivity(load(p)) for m, p in FROZEN.items()}}

r1_files = sorted(glob.glob("rq3/runs_R1/**/*.jsonl", recursive=True))
if r1_files:
    r1 = [r for p in r1_files for r in load(p)]
    frozen = [r for r in load(FROZEN["ollama:gpt-oss:20b"]) if r["temperature"] == 0.0]
    chk = {"files": [os.path.relpath(p) for p in r1_files], "records": len(r1),
           "ids_match_frozen_T0": sorted(r["id"] for r in r1) == sorted(r["id"] for r in frozen),
           "unique_ids": len({r["id"] for r in r1}) == len(r1),
           "plan_hash_ok": all(r.get("plan_hash") == PLAN for r in r1),
           "temperature_0": all(r["temperature"] == 0.0 for r in r1),
           "run_config": sorted({str(r.get("run_config")) for r in r1}),
           "model_digest_same_as_frozen": {r.get("model_digest") for r in r1} == {r.get("model_digest") for r in frozen},
           "prompt_sha_same_as_frozen": {r["id"]: r["sha"] for r in r1} == {r["id"]: r["sha"] for r in frozen},
           "hit_budget": sum(1 for r in r1 if (r.get("usage") or {}).get("eval_count", 0) >= 16380),
           "max_eval_count": max((r.get("usage") or {}).get("eval_count", 0) for r in r1)}
    res = RL.compute(r1, A.verdict_T0(r1))["ollama:gpt-oss:20b"]
    fz = RL.compute(frozen, A.verdict_T0(frozen))["ollama:gpt-oss:20b"]
    lab = {r["id"]: r["label"] for r in r1}; v_new = {r["id"]: r["verdict"] for r in r1}; v_old = {r["id"]: r["verdict"] for r in frozen}
    changed = collections.Counter(f"{v_old[i]}->{v_new[i]}" for i in v_new if v_old[i] != v_new[i])
    nat = [i for i in v_new if A.meta(i)["stratum"] == "natural"]
    rate = lambda V, lbl: [sum(V[i] == "DEFECT" for i in nat if lab[i] == lbl and A.meta(i)["cond"] == c) for c in ("B1", "B3", "B4", "B5")]
    out["R1"] = {"integrity": chk, "unparsed": res["unparsed"], "frozen_unparsed": fz["unparsed"],
                 "cond": res["cond"], "B3_vs_B1": res["pairs"]["B3_vs_B1"], "B3_vs_B4": res["pairs"]["B3_vs_B4"],
                 "B5_vs_B3": res["pairs"]["B5_vs_B3"], "delta_B3_B1_ci": res["delta_B3_B1_ci"], "rules": res["rules"],
                 "holdout": res.get("holdout"), "prospective": res["prospective"], "constructed_recall": res["constructed_recall"],
                 "verdict_changes_vs_frozen": dict(changed),
                 "defect_on_violating_B1_B3_B4_B5": rate(v_new, "DEFECT"), "defect_on_satisfying_B1_B3_B4_B5": rate(v_new, "CORRECT"),
                 "unparsed_sensitivity": unparsed_sensitivity(r1)}
json.dump(out, open("rq3/sensitivity_results.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:6000])
