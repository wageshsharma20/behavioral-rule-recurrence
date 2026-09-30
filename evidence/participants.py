"""Knowledge-flow check through PEOPLE for every Golden-Case pair (paper §5.2).
For each fix we collect every GitHub account that took part: issue author and commenters, PR author, reviewers, review
commenters, PR commenters, commit authors and the merger (bots excluded). For each pair (earlier fix A, later fix B) we
report:
  (1) shared participants of the two fixes;
  (2) prior cross-project activity before B's fix date: any participant of either fix who authored a commit in, or opened
      or commented on an issue/PR of, the other project.
Uses the GitHub REST API via the `gh` CLI (read-only). Output: evidence/participants.json"""
import json, subprocess, time, os, sys
FIX = {"GC1/arrow": ("apache/arrow", 38618, 38845, "2023-12-05"), "GC1/s3fs": ("fsspec/s3fs", 918, 1005, "2026-02-02"),
       "GC2a/s3path": ("liormizr/s3path", 77, 78, "2021-06-21"), "GC2a/gcsfs": ("fsspec/gcsfs", 447, 502, "2022-10-11"),
       "GC2a/obstore": ("developmentseed/obstore", 496, 524, "2025-08-07"),
       "GC2b/arrow": ("apache/arrow", 28758, 10526, "2021-06-14"), "GC2b/obstore": ("developmentseed/obstore", 671, 672, "2026-04-22"),
       "GC3/cloudpathlib": ("drivendataorg/cloudpathlib", 208, 244, "2022-08-11"), "GC3/opendal": ("apache/opendal", None, 4959, "2024-08-26")}
PAIRS = [("GC1/arrow", "GC1/s3fs"), ("GC2a/s3path", "GC2a/gcsfs"), ("GC2a/s3path", "GC2a/obstore"), ("GC2a/gcsfs", "GC2a/obstore"),
         ("GC2b/arrow", "GC2b/obstore"), ("GC3/cloudpathlib", "GC3/opendal")]
env = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}
def api(path, paginate=True):
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github+json", path] + (["--paginate"] if paginate else [])
    for _ in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if r.returncode == 0:
            out = r.stdout.strip()
            try: return json.loads(out)
            except json.JSONDecodeError: return json.loads("[" + out.replace("][", ",")[1:-1] + "]") if out.startswith("[") else json.loads(out.split("\n")[0])
        time.sleep(5)
    raise RuntimeError(r.stderr[:200])
def human(u): return u and u.get("type") != "Bot" and not u["login"].endswith("[bot]") and u["login"] not in ("asfimport",)
def participants(repo, issue, pr):
    P = {}
    def add(u, role):
        if human(u): P.setdefault(u["login"], set()).add(role)
    if issue:
        i = api(f"/repos/{repo}/issues/{issue}", False); add(i["user"], "issue author")
        for c in api(f"/repos/{repo}/issues/{issue}/comments?per_page=100"): add(c["user"], "issue commenter")
    p = api(f"/repos/{repo}/pulls/{pr}", False); add(p["user"], "PR author"); add(p.get("merged_by"), "merger")
    for c in api(f"/repos/{repo}/issues/{pr}/comments?per_page=100"): add(c["user"], "PR commenter")
    for c in api(f"/repos/{repo}/pulls/{pr}/reviews?per_page=100"): add(c["user"], "reviewer")
    for c in api(f"/repos/{repo}/pulls/{pr}/comments?per_page=100"): add(c["user"], "review commenter")
    for c in api(f"/repos/{repo}/pulls/{pr}/commits?per_page=100"): add(c.get("author"), "commit author")
    return {k: sorted(v) for k, v in P.items()}
def activity(login, repo, before):
    c = api(f"/repos/{repo}/commits?author={login}&until={before}T00:00:00Z&per_page=1", False)
    time.sleep(2.2)
    s = api(f"/search/issues?q=repo:{repo}+involves:{login}+created:<{before}&per_page=5", False)
    items = [{"url": x["html_url"], "title": x["title"][:80], "created": x["created_at"][:10]} for x in s.get("items", [])]
    return {"commits_before": len(c), "issues_prs_involving_before": s.get("total_count", 0), "examples": items}
if __name__ == "__main__":
    parts = {k: participants(r, i, p) for k, (r, i, p, d) in FIX.items()}
    out = {"participants": parts, "pairs": []}
    for a, b in PAIRS:
        ra, rb, db = FIX[a][0], FIX[b][0], FIX[b][3]
        shared = sorted(set(parts[a]) & set(parts[b]))
        cross = {}
        for who in parts[b]:
            if ra != rb: cross[f"{who} (later fix) in {ra}"] = activity(who, ra, db)
        for who in parts[a]:
            if ra != rb: cross[f"{who} (earlier fix) in {rb}"] = activity(who, rb, db)
        hits = {k: v for k, v in cross.items() if v["commits_before"] or v["issues_prs_involving_before"]}
        out["pairs"].append({"pair": [a, b], "shared_participants": shared, "n_checked": len(cross), "cross_activity": hits})
        print(a, b, "shared:", shared, "| cross-activity:", {k: (v["commits_before"], v["issues_prs_involving_before"]) for k, v in hits.items()})
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "participants.json"), "w"), indent=1)
