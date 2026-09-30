"""Deterministic history texts (ONLY content created before 2026-01-01, per protocol v3): for each thread (issue or PR): title, body, comments (chronological).
Cleaning: drop bot authors, HTML comments, PR-template headings/checkboxes, URLs, @mentions; cap 700 words.
Token from ~/.gh_token, never printed. Output rq3/histories/<key>.txt (+ .raw.json)."""
import json, os, re, urllib.request
tok = open(os.path.expanduser("~/.gh_token")).read().strip()
H = {"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "User-Agent": "lore-research"}; del tok
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60))
CUTOFF = "2026-01-01T00:00:00Z"
BOTS = re.compile(r"(bot|codecov|github-actions|conbench|asfimport-bot|dependabot)", re.I)
def clean(t):
    t = t or ""
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"https?://\S+", "[link]", t)
    t = re.sub(r"@[\w-]+", "@user", t)
    t = re.sub(r"^\s*[-*] \[[ xX]\].*$", "", t, flags=re.M)
    t = re.sub(r"^#+\s*(Which issue does this PR close\?|Rationale for this change|What changes are included in this PR\?|Are there any user-facing changes\?|Are these changes tested\?|Change list|Todo|Component\(s\)|Describe the bug, including details regarding any error messages, version, and platform\.)\s*$", "", t, flags=re.M | re.I)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
os.makedirs("rq3/histories", exist_ok=True)
for key, spec in json.load(open("rq3/histories.json")).items():
    parts, raw, comments = [], [], []
    threads = [(spec["repo"], n) for n in spec["threads"]] + [tuple(x) for x in spec.get("extra", [])]
    for repo, n in threads:   # bodies first (issue, then PR), comments afterwards in chronological order
        it = get(f"https://api.github.com/repos/{repo}/issues/{n}")
        kind = "Pull request" if "pull_request" in it else "Issue"
        if it["created_at"] >= CUTOFF:
            raw.append({"repo": repo, "n": n, "issue": it, "comments": [], "excluded": "created after cutoff"}); continue
        cs = get(f"https://api.github.com/repos/{repo}/issues/{n}/comments?per_page=100")
        raw.append({"repo": repo, "n": n, "issue": it, "comments": cs})
        parts.append(f"{kind}: {it['title']}\n{clean(it.get('body'))}")
        for c in cs:
            if BOTS.search((c.get("user") or {}).get("login", "")): continue
            if c["created_at"] >= CUTOFF: continue
            b = clean(c.get("body"))
            if len(b.split()) >= 5: comments.append((c["created_at"], f"Comment: {b}"))
    parts += [t for _, t in sorted(comments)]
    text = "\n\n".join(parts); words = text.split()
    if not parts:
        open(f"rq3/histories/{key}.txt", "w").write(""); json.dump(raw, open(f"rq3/histories/{key}.raw.json", "w"))
        print(f"{key:18s} NO pre-2026 content -> unavailable as a history source"); continue
    if len(words) > 700:
        # truncate at word 700 preserving line structure
        cut = 0; count = 0
        for m in re.finditer(r"\S+", text):
            count += 1
            if count == 700: cut = m.end(); break
        text = text[:cut] + "\n[... truncated at 700 words]"
    open(f"rq3/histories/{key}.txt", "w").write(text); json.dump(raw, open(f"rq3/histories/{key}.raw.json", "w"))
    print(f"{key:18s} words={min(len(words),700):4d} (raw {len(words)})")
