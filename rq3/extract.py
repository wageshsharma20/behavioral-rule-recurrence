"""Extract the enclosing function(s) of every changed hunk, at BAD (parent) and GOOD (fix) versions.
Same function-name set at both versions -> no version-specific localisation signal.
Output: rq3/items/<case>_<impl>_{bad,good}.txt and rq3/items/manifest.json"""
import json, re, ast, os, glob
os.makedirs("rq3/items", exist_ok=True)
SCOPE = {  # multi-file fixes: files on the probed operation's path (documented manual scoping)
    ("GC3", "opendal"): ["core/src/layers/complete.rs"],
    ("GC2a", "obstore"): ["pyo3-object_store/src/path.rs", "obstore/src/path.rs"],
    ("GC2a", "gcsfs"): ["gcsfs/core.py"],
}
def hunks(patch):
    out = []
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", patch or "", re.M):
        out.append((int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1)))
    return out
def changed_lines(patch):
    old, new = set(), set(); o = n = 0
    for line in (patch or "").splitlines():
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if m: o, n = int(m.group(1)), int(m.group(2)); continue
        if line.startswith("-"): old.add(o); o += 1
        elif line.startswith("+"): new.add(n); n += 1
        else: o += 1; n += 1
    return old, new
# ---------- python ----------
def py_defs(src):
    t = ast.parse(src); res = []
    def walk(node, prefix=""):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                res.append((prefix + ch.name, ch.lineno, ch.end_lineno)); walk(ch, prefix + ch.name + ".")
            elif isinstance(ch, ast.ClassDef): walk(ch, prefix + ch.name + ".")
    walk(t); return res
def py_enclosing(src, lines):
    defs = py_defs(src); names = set()
    for L in lines:
        c = [d for d in defs if d[1] <= L <= d[2]]
        if c: names.add(min(c, key=lambda d: d[2] - d[1])[0])
    return names
def py_extract(src, names):
    lines = src.splitlines(); out = []
    for nm, a, b in py_defs(src):
        if nm in names: out.append("\n".join(lines[a - 1:b]))
    return out
# ---------- rust / c++ ----------
SIG = {"rust": re.compile(r"^\s*(pub(\([^)]*\))?\s+)?(async\s+)?(unsafe\s+)?fn\s+(\w+)"),
       "cpp": re.compile(r"^\s*(?:[\w:<>\*&,]+\s+)+(?:[\w:~]+::)?([\w~]+)\s*\([^;]*$")}
def brace_block(lines, start):
    depth = 0; seen = False
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if "{" in lines[i]: seen = True
        if seen and depth <= 0: return i
    return len(lines) - 1
def c_blocks(src, lang):
    lines = src.splitlines(); res = []
    for i, l in enumerate(lines):
        m = SIG[lang].match(l)
        if m and not l.strip().startswith(("if", "for", "while", "return", "else", "switch", "//", "*")):
            name = m.group(5) if lang == "rust" else m.group(1)
            if name in ("if", "for", "while", "switch", "return"): continue
            end = brace_block(lines, i); res.append((name, i + 1, end + 1))
    return res
def c_enclosing(src, lang, lines_changed):
    blocks = c_blocks(src, lang); names = set()
    for L in lines_changed:
        c = [b for b in blocks if b[1] <= L <= b[2]]
        if c: names.add(max(c, key=lambda b: b[2] - b[1])[0] if lang == "cpp" else min(c, key=lambda b: b[2]-b[1])[0])
    return names
def c_extract(src, lang, names):
    lines = src.splitlines(); out = []; seen = set()
    for nm, a, b in c_blocks(src, lang):
        if nm in names and (nm, a) not in seen:
            if any(a >= x and b <= y for (_, x, y) in [(n2, a2, b2) for n2, a2, b2 in c_blocks(src, lang) if n2 in names and (a2, b2) != (a, b) and a2 <= a and b <= b2]):
                continue  # nested inside another selected block
            seen.add((nm, a)); out.append("\n".join(lines[a - 1:b]))
    return out
manifest = []
for p in sorted(glob.glob("rq3/raw/*.json")):
    d = json.load(open(p)); key = (d["case"], d["impl"]); scope = SCOPE.get(key)
    bad_parts, good_parts, names_all = [], [], {}
    for f in d["files"]:
        if scope and f["path"] not in scope: continue
        if not f["bad"] or not f["good"]: continue
        old, new = changed_lines(f["patch"])
        if d["lang"] == "python":
            names = py_enclosing(f["bad"], old) | py_enclosing(f["good"], new)
            b, g = py_extract(f["bad"], names), py_extract(f["good"], names)
        else:
            names = c_enclosing(f["bad"], d["lang"], old) | c_enclosing(f["good"], d["lang"], new)
            b, g = c_extract(f["bad"], d["lang"], names), c_extract(f["good"], d["lang"], names)
        if names:
            names_all[f["path"]] = sorted(names)
            hdr = f"// file: {f['path']}" if d["lang"] != "python" else f"# file: {f['path']}"
            bad_parts.append(hdr + "\n" + "\n\n".join(b)); good_parts.append(hdr + "\n" + "\n\n".join(g))
    stem = f"rq3/items/{d['case']}_{d['impl']}"
    open(stem + "_bad.txt", "w").write("\n\n".join(bad_parts)); open(stem + "_good.txt", "w").write("\n\n".join(good_parts))
    rec = {"case": d["case"], "impl": d["impl"], "lang": d["lang"], "repo": d["repo"], "pr": d["pr"],
           "bad_sha": d["parent_sha"], "good_sha": d["merge_sha"], "functions": names_all,
           "bad_lines": sum(x.count("\n") + 1 for x in bad_parts), "good_lines": sum(x.count("\n") + 1 for x in good_parts),
           "identical": "\n".join(bad_parts) == "\n".join(good_parts)}
    manifest.append(rec); print(rec["case"], rec["impl"], rec["functions"], rec["bad_lines"], rec["good_lines"], "IDENTICAL!" if rec["identical"] else "")
json.dump(manifest, open("rq3/items/manifest.json", "w"), indent=1)
