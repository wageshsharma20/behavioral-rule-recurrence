"""RQ2 baseline (POST HOC, illustrative): does topic/text similarity between fix threads identify the recurrences that
executable screening + lineage checks identify? Threads = full issue + PR text (title, body, comments), all dates,
cleaned with the same recipe as the RQ3 histories (links, @mentions, bot comments, PR-template boilerplate removed).
Implementation/project names are removed so that similarity reflects topic, not project vocabulary.
Metric: TF-IDF cosine similarity. Output: rq2_baseline/results.json + printed summary."""
import json, os, re, math, itertools, urllib.request, sys
sys.path.insert(0, "rq3")
def get(u):  # token read lazily: only needed when a thread is not cached in rq2_baseline/threads/
    H = {"Accept": "application/vnd.github+json", "User-Agent": "replication"}
    tf = os.path.expanduser(os.environ.get("GH_TOKEN_FILE", "~/.gh_token"))
    if os.path.exists(tf): H["Authorization"] = "Bearer " + open(tf).read().strip()
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60))
BOTS = re.compile(r"(bot|codecov|github-actions|conbench|dependabot)", re.I)
def clean(t):
    t = t or ""; t = re.sub(r"<!--.*?-->", "", t, flags=re.S); t = re.sub(r"https?://\S+", " ", t); t = re.sub(r"@[\w-]+", " ", t)
    t = re.sub(r"^\s*[-*] \[[ xX]\].*$", "", t, flags=re.M)
    t = re.sub(r"^#+\s*(Which issue does this PR close\?|Rationale for this change|What changes are included in this PR\?|Are there any user-facing changes\?|Are these changes tested\?|Change list|Todo|Component\(s\)|Describe the bug.*)\s*$", "", t, flags=re.M | re.I)
    return t
THREADS = {  # key: (repo, [numbers])
 "GC1_arrow": ("apache/arrow", [38618, 38845]), "GC1_s3fs": ("fsspec/s3fs", [918, 1005]),
 "GC2a_s3path": ("liormizr/s3path", [77, 78]), "GC2a_gcsfs": ("fsspec/gcsfs", [447, 502]),
 "GC2a_obstore": ("developmentseed/obstore", [496, 524]), "GC2b_arrow": ("apache/arrow", [28758, 10526]),
 "GC2b_obstore": ("developmentseed/obstore", [671, 672]), "GC3_cloudpathlib": ("drivendataorg/cloudpathlib", [208, 244]),
 "GC3_opendal": ("apache/opendal", [4877, 4959]),
 "C1_gcsfs": ("fsspec/gcsfs", [458, 459]), "C1_s3fs": ("fsspec/s3fs", [988, 989]),
 "R2_s3fs_2021": ("fsspec/s3fs", [492, 493]), "R2_s3fs_2023": ("fsspec/s3fs", [773, 791]), "R2_gcsfs_2022": ("fsspec/gcsfs", [488]),
 "REL_gcsfs": ("fsspec/gcsfs", [618]), "REL_sftp": ("fsspec/filesystem_spec", [1451]),
 "CT_s3path": ("liormizr/s3path", [81]),
 "GLOB_s3path": ("liormizr/s3path", [160]), "GLOB_cloudpathlib": ("drivendataorg/cloudpathlib", [311, 312]),
}
NAMES = r"\b(s3fs|gcsfs|pyarrow|arrow|obstore|object_store|objectstore|opendal|cloudpathlib|s3path|fsspec|apache|github)\b"
os.makedirs("rq2_baseline/threads", exist_ok=True)
texts = {}
for k, (repo, nums) in THREADS.items():
    fp = f"rq2_baseline/threads/{k}.txt"
    if os.path.exists(fp): texts[k] = open(fp).read(); continue
    parts = []
    for n in nums:
        it = get(f"https://api.github.com/repos/{repo}/issues/{n}"); parts.append((it.get("title") or "") + "\n" + clean(it.get("body")))
        for c in get(f"https://api.github.com/repos/{repo}/issues/{n}/comments?per_page=100"):
            if not BOTS.search((c.get("user") or {}).get("login", "")): parts.append(clean(c.get("body")))
    texts[k] = "\n".join(parts); open(fp, "w").write(texts[k])
STOP = set("the and for that this with from are was were not but you your have has had can will would should could our its it's into when then than there their them they what which who how why all any some one two also just only very more most such other been being does did doing about over under after before while where because if else so we i a an to of in on at by as is be or it no yes do".split())
def toks(t):
    t = re.sub(NAMES, " ", t.lower())
    return [w for w in re.findall(r"[a-z_][a-z0-9_]{2,}", t) if w not in STOP]
docs = {k: toks(v) for k, v in texts.items()}
df = {}
for k, ws in docs.items():
    for w in set(ws): df[w] = df.get(w, 0) + 1
N = len(docs)
def vec(ws):
    tf = {}
    for w in ws: tf[w] = tf.get(w, 0) + 1
    v = {w: (1 + math.log(c)) * math.log((1 + N) / (1 + df[w])) for w, c in tf.items()}
    n = math.sqrt(sum(x * x for x in v.values())) or 1.0
    return {w: x / n for w, x in v.items()}
V = {k: vec(ws) for k, ws in docs.items()}
cos = lambda a, b: sum(x * V[b].get(w, 0.0) for w, x in V[a].items())
GOLDEN = [("GC1_arrow", "GC1_s3fs"), ("GC2a_s3path", "GC2a_gcsfs"), ("GC2a_s3path", "GC2a_obstore"), ("GC2a_gcsfs", "GC2a_obstore"),
          ("GC2b_arrow", "GC2b_obstore"), ("GC3_cloudpathlib", "GC3_opendal")]
REJECTED = {("C1_gcsfs", "C1_s3fs"): "same topic, different defects (no single assertion separates both)",
            ("R2_s3fs_2021", "R2_gcsfs_2022"): "same rule, shared code origin (lineage condition 5)",
            ("R2_s3fs_2023", "R2_gcsfs_2022"): "same rule, shared code origin (lineage condition 5)",
            ("REL_gcsfs", "REL_sftp"): "similar topic, different behaviour",
            ("CT_s3path", "GC3_opendal"): "contested rule (opposite directions)",
            ("GLOB_s3path", "GLOB_cloudpathlib"): "flip not attributable"}
gk = [k for k in THREADS if k.startswith("GC")]
DIFF = [(a, b) for a, b in itertools.combinations(gk, 2) if (a, b) not in GOLDEN and (b, a) not in GOLDEN]
res = {"golden": {f"{a}|{b}": cos(a, b) for a, b in GOLDEN}, "rejected": {f"{a}|{b}": cos(a, b) for a, b in REJECTED},
       "different_rule": {f"{a}|{b}": cos(a, b) for a, b in DIFF}}
thr = min(res["golden"].values())
above_rej = [k for k, v in res["rejected"].items() if v >= thr]; above_diff = [k for k, v in res["different_rule"].items() if v >= thr]
neg = list(res["rejected"].values()) + list(res["different_rule"].values()); pos = list(res["golden"].values())
auc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
res["summary"] = {"threshold_admitting_all_golden": thr, "rejected_at_or_above": above_rej, "different_rule_at_or_above": len(above_diff),
                  "n_different_rule": len(DIFF), "auc_golden_vs_all_other": auc,
                  "max_rejected": max(res["rejected"].items(), key=lambda x: x[1]), "min_golden": min(res["golden"].items(), key=lambda x: x[1])}
allp = sorted([(v, "G", k) for k, v in res["golden"].items()] + [(v, "R", k) for k, v in res["rejected"].items()] +
              [(v, "D", k) for k, v in res["different_rule"].items()], reverse=True)
res["summary"]["n_pairs"] = len(allp)
res["summary"]["ranks_of_golden"] = [i + 1 for i, (_, t, _) in enumerate(allp) if t == "G"]
res["summary"]["top6_counts"] = {t: sum(1 for _, tt, _ in allp[:6] if tt == t) for t in "GRD"}
res["summary"]["second_most_similar_pair"] = allp[1][2]
res["summary"]["rejected_more_similar_than_n_golden"] = {k: sum(1 for g in res["golden"].values() if v > g) for k, v in res["rejected"].items()}
json.dump(res, open("rq2_baseline/results.json", "w"), indent=1)
print("GOLDEN:", {k: round(v, 3) for k, v in sorted(res["golden"].items(), key=lambda x: x[1])})
print("REJECTED:", {k: round(v, 3) for k, v in sorted(res["rejected"].items(), key=lambda x: x[1])})
d = sorted(res["different_rule"].values()); print(f"DIFFERENT-RULE ({len(d)}): min {d[0]:.3f} median {d[len(d)//2]:.3f} max {d[-1]:.3f}")
print("threshold admitting all golden:", round(thr, 3), "| rejected >= thr:", above_rej, "| different-rule >= thr:", len(above_diff), "of", len(DIFF), "| AUC:", round(auc, 3))
