"""Build RQ3 prompts for natural items. Deterministic. Output rq3/prompts_natural.jsonl"""
import json, hashlib
M = {(m["case"], m["impl"]): m for m in json.load(open("rq3/items/manifest.json"))}
LIB = {"pyarrow": ("Apache Arrow (pyarrow.fs)", "C++"), "s3fs": ("s3fs", "Python"), "s3path": ("s3path", "Python"),
       "gcsfs": ("gcsfs", "Python"), "obstore": ("obstore / object_store", "Rust"),
       "cloudpathlib": ("cloudpathlib", "Python"), "opendal": ("Apache OpenDAL", "Rust")}
OP = {"GC1": "recursively deleting a directory (removing a directory and everything stored under it)",
      "GC2a": "writing and reading objects by key",
      "GC2b": "copying or renaming an object",
      "GC3": "checking whether a path exists or is a directory"}
DATE = {"GC1_pyarrow": "2023-11", "GC1_s3fs": "2024-12", "GC2a_s3path": "2021-06", "GC2a_gcsfs": "2022-02",
        "GC2a_obstore": "2025-07", "GC2b_pyarrow": "2021-06",
        "GC3_cloudpathlib": "2022-02"}           # history date (issue opened); OpenDAL: no rationale; obstore GC2b (#671/#672): no pre-2026 content -> absent
HIST = {k: open(f"rq3/histories/{k}.txt").read() for k in DATE}
WC = {k: len(v.split()) for k, v in HIST.items()}
def cross_source(case, impl):
    cands = sorted([k for k in DATE if k.startswith(case + "_") and k != f"{case}_{impl}"], key=lambda k: DATE[k])
    return cands[0] if cands else None
def mismatched(case, ref_wc):
    cands = [k for k in DATE if not k.startswith(case + "_")]
    return min(cands, key=lambda k: (abs(WC[k] - ref_wc), k))
PRE = ("You are reviewing code from {lib}, a {lang} library that gives filesystem-style access to cloud object "
       "storage (Amazon S3 / Google Cloud Storage). The functions below are involved in {op}.\n\n"
       "Question: as written, does this code contain a behavioral defect in {op} — i.e. is there some valid input or "
       "storage state for which it produces an incorrect result (wrong objects affected, wrong key used, wrong answer, "
       "or an unexpected failure)?\n")
HBLK = ("\nFor context, here is an issue/pull-request discussion from an object-storage filesystem library's tracker. "
        "It may or may not be relevant.\n<<<DISCUSSION\n{h}\nDISCUSSION>>>\n")
CODE = "\n<<<CODE ({lang})\n{code}\nCODE>>>\n"
POST = ('\nAnswer with a single JSON object and nothing else: {{"verdict": "DEFECT" or "CORRECT", '
        '"scenario": "<one sentence: a concrete input/storage state that triggers the defect, or empty>"}}')
rows = []
for (case, impl), m in sorted(M.items()):
    if case == "PV1": continue
    lib, lang = LIB[impl]; op = OP[case]
    xs = cross_source(case, impl); own = f"{case}_{impl}" if f"{case}_{impl}" in HIST else None
    mm = mismatched(case, WC[xs] if xs else (WC[own] if own else 400))
    conds = {"B1": None, "B3": xs, "B4": mm, "B5": own}
    for ver, label in (("bad", "DEFECT"), ("good", "CORRECT")):
        code = open(f"rq3/items/{case}_{impl}_{ver}.nc.txt").read()
        for cond, hsrc in conds.items():
            if cond != "B1" and hsrc is None: continue
            p = PRE.format(lib=lib, lang=lang, op=op)
            if hsrc: p += HBLK.format(h=HIST[hsrc])
            p += CODE.format(lang=lang, code=code) + POST
            rid = f"{case}|{impl}|{ver}|{cond}"
            rows.append({"id": rid, "case": case, "impl": impl, "version": ver, "label": label, "condition": cond,
                         "history_source": hsrc, "prompt": p, "sha": hashlib.sha256(p.encode()).hexdigest()[:12],
                         "chars": len(p)})
with open("rq3/prompts_natural.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
from collections import Counter
print(len(rows), "prompts;", Counter(r["condition"] for r in rows))
for (case, impl) in sorted(M):
    if case == "PV1": continue
    xs = cross_source(case, impl); print(f"  {case}/{impl:12s} B3<-{xs}  B4<-{mismatched(case, WC[xs] if xs else 400)}")
print("max prompt chars", max(r["chars"] for r in rows))
