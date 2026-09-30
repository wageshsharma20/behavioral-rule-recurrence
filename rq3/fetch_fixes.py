"""For each fix PR: merge commit, parent, changed files + patches, and full file contents at parent and merge.
Token read from ~/.gh_token, never printed. Output: rq3/raw/<case>_<impl>.json"""
import json, os, base64, urllib.request, urllib.parse
tok = open(os.path.expanduser("~/.gh_token")).read().strip()
H = {"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "User-Agent": "lore-research"}; del tok
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60))
def content(repo, path, ref):
    try:
        d = get(f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(path)}?ref={ref}")
        if d.get("encoding") == "base64": return base64.b64decode(d["content"]).decode("utf-8", "replace")
        # large files: use blob API
        b = get(d["git_url"]); return base64.b64decode(b["content"]).decode("utf-8", "replace")
    except Exception as e:
        return None
SRC_EXT = (".py", ".cc", ".h", ".rs", ".cpp")
for f in json.load(open("rq3/fixes.json")):
    if os.path.exists(f"rq3/raw/{f['case']}_{f['impl']}.json"): continue
    pr = get(f"https://api.github.com/repos/{f['repo']}/pulls/{f['pr']}")
    sha = f.get("sha_override") or pr["merge_commit_sha"]; c = get(f"https://api.github.com/repos/{f['repo']}/commits/{sha}")
    sha = c["sha"]
    parent = c["parents"][0]["sha"]
    files = [x for x in c["files"] if x["filename"].endswith(SRC_EXT) and "test" not in x["filename"].lower()]
    out = {**f, "merge_sha": sha, "parent_sha": parent, "pr_title": pr["title"], "merged_at": pr["merged_at"],
           "files": []}
    for x in files:
        out["files"].append({"path": x["filename"], "patch": x.get("patch"),
                             "bad": content(f["repo"], x["filename"], parent),
                             "good": content(f["repo"], x["filename"], sha)})
    json.dump(out, open(f"rq3/raw/{f['case']}_{f['impl']}.json", "w"))
    print(f["case"], f["impl"], sha[:9], "parent", parent[:9], "| src files:", [x["filename"] for x in files],
          "| sizes:", [(len(x["bad"] or ""), len(x["good"] or "")) for x in out["files"]])
