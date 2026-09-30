"""Second step of the people check (paper §5.2): for every cross-project contact found by participants.py, list the
issues/PRs of the other project in which that person was involved in the WINDOW between the two fixes, then scan their
full text (body and comments) for the rule's terms. Every term match is inspected by hand; the notes are recorded below.
Outputs: evidence/participants_window.json, evidence/participants_window_topics.json"""
import json, subprocess, os, re, time
HERE = os.path.dirname(os.path.abspath(__file__)); env = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}
W = [("martindurant", "apache/arrow", "2023-12-05", "2026-02-02", "GC1"), ("ywilke", "apache/arrow", "2023-12-05", "2026-02-02", "GC1"),
     ("jorisvandenbossche", "fsspec/s3fs", "2023-12-05", "2026-02-02", "GC1"), ("pitrou", "fsspec/s3fs", "2023-12-05", "2026-02-02", "GC1"),
     ("martindurant", "developmentseed/obstore", "2022-10-11", "2025-08-07", "GC2"), ("kylebarron", "apache/arrow", "2021-06-14", "2026-04-22", "GC2")]
KW = {"GC1": r"marker|placeholder|trailing slash|delete_dir|DeleteDir|rm\(|recursive delet",
      "GC2": r"percent|url-?encod|urlencod|quote\(|escap|special char|unicode|non-ascii|caf|%2F|copy_?source|CopyObject"}
MANUAL = {"developmentseed/obstore#60": "'%2F' occurs in a URL inside an error message; not about key encoding",
          "apache/arrow#35780": "'caf' is part of a benchmark hash", "apache/arrow#34996": "'caf' is the website py.cafe",
          "apache/arrow#32609": "'percent' is 'percentage' of code; type-checking discussion"}
def gh(args):
    r = subprocess.run(["gh", "api"] + args, capture_output=True, text=True, env=env); out = r.stdout.strip()
    try: return json.loads(out)
    except json.JSONDecodeError: return json.loads("[" + out.replace("][", ",")[1:-1] + "]")
window, topics = {}, {}
for who, repo, a, b, rule in W:
    d = gh(["-X", "GET", "/search/issues", "-f", f"q=repo:{repo} involves:{who} created:{a}..{b}", "-f", "per_page=100"]); time.sleep(2.3)
    items = [(x["created_at"][:10], x["title"][:95], x["html_url"]) for x in d.get("items", [])]
    window[f"{who}|{repo}|{a}..{b}"] = items; hits = []
    for created, title, url in items:
        n = url.rstrip("/").split("/")[-1]
        i = gh([f"/repos/{repo}/issues/{n}"]); cs = gh([f"/repos/{repo}/issues/{n}/comments?per_page=100", "--paginate"])
        text = " ".join([i.get("title", ""), i.get("body") or ""] + [c.get("body") or "" for c in cs])
        m = sorted(set(x.lower() for x in re.findall(KW[rule], text, re.I)))
        if m: hits.append({"url": url, "terms": m, "manual_verdict": MANUAL.get(f"{repo}#{n}", "NOT YET INSPECTED")})
    topics[f"{who}|{repo}|{a}..{b}"] = {"items": len(items), "term_matches": hits}
    print(who, repo, len(items), "items;", len(hits), "term matches")
json.dump(window, open(os.path.join(HERE, "participants_window.json"), "w"), indent=1)
json.dump(topics, open(os.path.join(HERE, "participants_window_topics.json"), "w"), indent=1)
print("total contacts in windows:", sum(len(v) for v in window.values()),
      "| about the rule after inspection:", sum(1 for v in topics.values() for h in v["term_matches"] if h["manual_verdict"] == "NOT YET INSPECTED"))
