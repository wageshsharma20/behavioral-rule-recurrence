"""Parse the recorded client requests of every row and decide each row's verdict from the REQUESTS ALONE,
using only the services' documented API semantics (no emulator response is consulted):
  S3-key   the object key of a REST request is its URI path after the bucket, percent-decoded once;
  S3-copy  x-amz-copy-source is '<bucket>/<key>', URL-encoded once (CopyObject);
  S3-del   DeleteObject/DeleteObjects remove exactly the keys named (a missing key is reported as deleted);
  list     ListObjects(V2) returns the keys that begin with 'prefix' as a string (S3 and GCS);
  GCS-name a JSON-API object name is one percent-encoded path segment; a '#' ends the URL (RFC 3986 fragment)
           and is never transmitted.
Writes out/wire_results.json and prints a table; exit 1 if any request-level verdict differs from the oracle's."""
import json, os, re, sys, urllib.parse as U, html
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
def streams(path, a, b):
    data = open(path, "rb").read()[a:b]; s = {}; i = 0
    while i < len(data):
        nl = data.index(b"\n", i); _, cid, n = data[i:nl].split(); n = int(n)
        s.setdefault(int(cid), bytearray()).extend(data[nl + 1:nl + 1 + n]); i = nl + 1 + n
    return s
def requests(buf):
    out, i = [], 0; buf = bytes(buf)
    while True:
        m = re.compile(rb"(GET|PUT|POST|DELETE|HEAD) (\S+) HTTP/1\.[01]\r\n").search(buf, i)
        if not m: return out
        he = buf.index(b"\r\n\r\n", m.end() - 2); hdr = {}
        for line in buf[m.end():he].split(b"\r\n"):
            if b":" in line: k, v = line.split(b":", 1); hdr[k.decode().lower()] = v.strip().decode("latin-1")
        j = he + 4; body = b""
        if "content-length" in hdr: body = buf[j:j + int(hdr["content-length"])]; j += len(body)
        elif "chunked" in hdr.get("transfer-encoding", ""):
            while True:
                e = buf.index(b"\r\n", j); n = int(buf[j:e].split(b";")[0], 16); j = e + 2
                if n == 0: j = buf.find(b"\r\n", j) + 2; break
                body += buf[j:j + n]; j += n + 2
        t = m.group(2).decode("latin-1"); p, _, q = t.partition("?")
        out.append({"method": m.group(1).decode(), "target": t, "path": p, "query": dict(U.parse_qsl(q, keep_blank_values=True)),
                    "headers": hdr, "body": body}); i = j
def s3_key(r, b):   # path-style: /<bucket>/<key>
    p = r["path"]; pre = f"/{b}/"
    return U.unquote(p[len(pre):]) if p.startswith(pre) else None
def gcs_obj(r, b):  # /storage/v1/b/<b>/o/<name>[/...], /download/storage/v1/b/<b>/o/<name>
    m = re.match(rf"(?:/download)?/storage/v1/b/{re.escape(b)}/o/([^/?]+)", r["path"])
    return U.unquote(m.group(1)) if m else None
def listing(r, b, gcs):
    if gcs: return r["query"].get("prefix") if re.match(rf"/storage/v1/b/{re.escape(b)}/o/?$", r["path"]) and r["method"] == "GET" else None
    return r["query"].get("prefix") if r["method"] == "GET" and r["path"].rstrip("/") == f"/{b}" else None
def deleted_keys(rs, b, gcs):
    ks = []
    for r in rs:
        if r["method"] == "DELETE": ks.append(gcs_obj(r, b) if gcs else s3_key(r, b))
        if r["method"] == "POST" and "delete" in r["query"]:
            ks += [html.unescape(k) for k in re.findall(r"<Key>(.*?)</Key>", r["body"].decode("utf-8", "replace"))]
    return [k for k in ks if k is not None]
def judge(op, rs, b, gcs, world_keys):
    """return (request-level verdict, evidence string)"""
    if op == "gc1":
        named = set(deleted_keys(rs, b, gcs)); need = [k for k in world_keys if k.startswith("d/")]
        miss = [k for k in need if k not in named]
        return (not miss and "dx/k" not in named), f"deletes {sorted(named)}" + (f"; never names {miss}" if miss else "")
    if op == "write":
        ks = [s3_key(r, b) for r in rs if r["method"] == "PUT" and "x-amz-copy-source" not in r["headers"]]
        ks = [k for k in ks if k is not None]
        return (bool(ks) and all(k == "w/café" for k in ks)), f"PUT key(s) {ks}  [raw {[r['path'] for r in rs if r['method']=='PUT'][:1]}]"
    if op == "read":
        ns = [gcs_obj(r, b) for r in rs if r["method"] == "GET"]; ns = [n for n in ns if n is not None]
        return (bool(ns) and all(n == "s/hash#" for n in ns)), f"object name(s) requested {sorted(set(ns))}"
    if op == "copy":
        srcs = [U.unquote(r["headers"]["x-amz-copy-source"]).lstrip("/") for r in rs if "x-amz-copy-source" in r["headers"]]
        return (bool(srcs) and all(s.split("?")[0] == f"{b}/src/café" for s in srcs)), f"copy source(s) {srcs}  [header {[r['headers']['x-amz-copy-source'] for r in rs if 'x-amz-copy-source' in r['headers']][:1]}]"
    if op == "exists":
        ps = [p for p in (listing(r, b, gcs) for r in rs) if p is not None]
        heads = [s3_key(r, b) for r in rs if r["method"] == "HEAD"]
        # a listing answers 'is there a key under foo/' only if its prefix is 'foo/'; with prefix 'foo' the service
        # (by documented string-prefix semantics) also returns foobar-style siblings present in this world
        exposed = [p for p in ps if any(k.startswith(p) and not k.startswith("very/similar/prefix/") for k in world_keys)]
        return (not exposed), f"list prefixes {ps}; HEAD {heads}"
    if op == "movedir":
        touched = set(deleted_keys(rs, b, gcs))
        for r in rs:
            if "x-amz-copy-source" in r["headers"]:
                touched.add(U.unquote(r["headers"]["x-amz-copy-source"]).lstrip("/").split("/", 1)[1]); touched.add(s3_key(r, b))
            m = re.match(rf"/storage/v1/b/{re.escape(b)}/o/([^/]+)/(?:rewriteTo|copyTo)/b/{re.escape(b)}/o/([^/?]+)", r["path"])
            if m: touched |= {U.unquote(m.group(1)), U.unquote(m.group(2))}
        # keys other than the directories themselves ('src', 'dst' name no object in this world) and their contents
        outside = sorted(k for k in touched if k and k not in ("src", "dst") and not (k.startswith("src/") or k.startswith("dst/")))
        ps = [p for p in (listing(r, b, gcs) for r in rs) if p is not None]
        return (not outside), f"list prefixes {ps}; touches objects outside the two directories: {outside}"
W = {"gc1": ["d/sub/", "d/sub/f", "d/g", "dx/k"], "write": [], "read": ["s/hash#"], "copy": ["src/café"],
     "exists": ["very/similar/prefix1", "very/similar/prefix2", "very/similar/prefix3/something"],
     "movedir": ["src/sub/f", "src/g", "srcx"]}
rows, bad = [], 0
for line in open(os.path.join(OUT, "rows.jsonl")):
    R = json.loads(line); t = R["trace"]
    if not t: print("NO TRACE", R["case"], R["env"]); bad += 1; continue
    ss = streams(os.path.join(os.path.dirname(os.path.dirname(HERE)), R["logfile"]), *t["log"])
    rs = [q for cid in sorted(ss) for q in requests(ss[cid])]
    v, ev = judge(t["op"], rs, t["bucket"], R["backend"] == "gcs", W[t["op"]])
    agree = (v == t["verdict"] == R["expect"]); bad += not agree
    rows.append({"case": R["case"], "env": R["env"], "backend": R["backend"], "expected": R["expect"],
                 "emulator_verdict": t["verdict"], "request_level_verdict": v, "agree": agree,
                 "n_requests": len(rs), "evidence": ev})
    print(f"{R['case']:5s} {R['env']:22s} exp={str(R['expect']):5s} emu={str(t['verdict']):5s} req={str(v):5s} {'OK ' if agree else 'XX '} {ev[:150]}")
json.dump({"semantics": __doc__, "rows": rows, "all_agree": bad == 0}, open(os.path.join(OUT, "wire_results.json"), "w"), indent=1, ensure_ascii=False)
print(f"{len(rows)} rows, {sum(r['agree'] for r in rows)} agree"); sys.exit(1 if bad else 0)
