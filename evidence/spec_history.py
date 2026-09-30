"""Temporal check of the specification anchors (paper §5.1, reviewer concern: 'was the requirement documented BEFORE the
fix, or only afterwards?'). For every anchor we retrieve a version dated BEFORE the relevant fix and search it for the
requirement:
  * web documentation: the latest Internet Archive snapshot before the cutoff (CDX API), fetched as archived (id_);
  * library documentation: the docstring shipped in an old release (installed in envs/), dated by its release date;
  * versioned documentation (POSIX 2018 edition; docs.rs pages of an older crate version), dated by their edition.
Cutoff = the EARLIEST fix of the case (for a client's own contract: that client's own fix).
Output: evidence/spec_history.json and a printed table. A MISS is reported as such, never dropped."""
import json, os, re, subprocess, sys, urllib.request, html as H, time, gzip
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def get(url, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-replication"}), timeout=60).read()
            if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)   # some archived pages are stored gzip-compressed
            return raw.decode("utf-8", "replace")
        except Exception as e:
            err = e; time.sleep(3 * (i + 1))
    raise err
def text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h); h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", H.unescape(h))
def wayback(url, before):
    cdx = json.loads(get(f"https://web.archive.org/cdx/search/cdx?url={url}&to={before}&filter=statuscode:200&output=json&fl=timestamp,original"))
    rows = [r for r in cdx[1:] if r[0][:8] < before]
    if not rows: return None, None
    ts, orig = rows[-1]
    return ts, text(get(f"https://web.archive.org/web/{ts}id_/{orig}"))
def docstring(env, code):
    py = os.path.join(ROOT, "envs", env, "bin", "python")
    return subprocess.run([py, "-c", code], capture_output=True, text=True).stdout

def earliest(url, cutoff, rx):
    """earliest archived year (first snapshot of each year, 2014..cutoff) whose text already states the requirement"""
    for y in range(2014, int(cutoff[:4]) + 1):
        try:
            cdx = json.loads(get(f"https://web.archive.org/cdx/search/cdx?url={url}&from={y}&to={y}&filter=statuscode:200&output=json&fl=timestamp,original&limit=1"))
        except Exception: continue
        if len(cdx) < 2 or cdx[1][0][:8] >= cutoff: continue
        ts, orig = cdx[1]
        try:
            if re.search(rx, text(get(f"https://web.archive.org/web/{ts}id_/{orig}")), re.I | re.S): return ts[:8]
        except Exception: continue
    return None
A = [  # case, anchor, kind, source, cutoff (YYYYMMDD, exclusive), requirement regex
 ("GC1", "pyarrow delete_dir docstring", "release", ("pyarrow-3.0.0", "import pyarrow.fs as f;print(f.FileSystem.delete_dir.__doc__)", "pyarrow 3.0.0 (released 2021-01-26)", "20210126"), "20231205", r"Delete a directory and its contents, recursively"),
 ("GC1", "fsspec rm(recursive) docstring", "release", ("s3fs-2021.6.0", "import fsspec;print(fsspec.__version__);print(fsspec.AbstractFileSystem.rm.__doc__)", "fsspec in the s3fs 2021.6.0 environment (s3fs released 2021-06-07)", "20210607"), "20231205", r"recursively delete contents and then\s+also remove the directory"),
 ("GC1", "S3: console folder = zero-byte object with trailing '/'", "web", "docs.aws.amazon.com/AmazonS3/latest/userguide/using-folders.html", "20231205", r"(0-byte|zero-byte) object"),
 ("GC1", "S3 DeleteObjects: missing key reported as deleted", "web", "docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html", "20231205", r"(isn't|is not) found, Amazon S3 (returns|confirms)"),
 ("GC2a", "S3: key uniquely identifies the object; user specifies it", "web", "docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html", "20210621", r"uniquely identifies the object"),
 ("GC2a", "S3 (older URL): key uniquely identifies the object", "web", "docs.aws.amazon.com/AmazonS3/latest/dev/UsingMetadata.html", "20210621", r"uniquely identifies the object"),
 ("GC2a", "GCS: special characters in object names must be encoded in URLs", "web", "cloud.google.com/storage/docs/request-endpoints", "20210621", r"(percent|URL)[- ]encod|encode the following characters|must be encoded"),
 ("GC2b", "S3 CopyObject: copy source must be URL-encoded", "web", "docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html", "20210614", r"must be URL[- ]?encoded"),
 ("GC3", "POSIX pathname resolution (2018 edition)", "versioned", ("https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap04.html", "IEEE Std 1003.1-2017 (2018 edition)", "20180101"), "20220811", r"located in the directory specified by its predecessor"),
 ("GC3", "S3: folders are shared prefixes ending in the delimiter", "web", "docs.aws.amazon.com/AmazonS3/latest/userguide/using-folders.html", "20220811", r"shared name prefix|prefix.{0,80}delimiter"),
 ("GC3", "pathlib is_dir (followed by cloudpathlib)", "web", "docs.python.org/3/library/pathlib.html", "20220811", r"Return True if the path points to a directory"),
 ("GC3", "OpenDAL: directory paths end with '/' (own contract, before its fix)", "web", "opendal.apache.org/docs/rust/opendal/struct.Operator.html", "20240826", r"(end|ends|ending) with `?/`?|trailing slash"),
 ("GC3", "OpenDAL docs.rs 0.45.0 (own contract, before its fix)", "versioned", ("https://docs.rs/opendal/0.45.0/opendal/struct.Operator.html", "opendal 0.45.0 docs.rs (crate published 2024-02-05)", "20240205"), "20240826", r"(end|ends|ending) with `?/`?|trailing slash"),
 ("PV1", "pathlib rename/rmdir act on the named path", "web", "docs.python.org/3/library/pathlib.html", "20260101", r"Rename this (file or directory|path)"),
 ("contested", "pathlib iterdir excludes '.' (directory itself)", "web", "docs.python.org/3/library/pathlib.html", "20210601", r"special entries .{0,6}\..{0,12}are not included"),
]
out = []
for case, what, kind, src, cutoff, rx in A:
    rec = {"case": case, "anchor": what, "cutoff_before": cutoff, "requirement_regex": rx}
    try:
        if kind == "web":
            ts, body = wayback(src, cutoff)
            rec.update(source=src, version_date=ts[:8] if ts else None, snapshot=f"https://web.archive.org/web/{ts}/{src}" if ts else None)
            rec["earliest_snapshot_stating_it"] = earliest(src, cutoff, rx) if ts else None
        elif kind == "release":
            body = docstring(src[0], src[1]); rec.update(source=src[2], version_date=src[3])
        else:
            body = text(get(src[0])); rec.update(source=src[0], version_date=src[2], edition=src[1])
        m = re.search(rx, body or "", re.I | re.S)
        rec["found_before_cutoff"] = bool(m) and (rec["version_date"] is None or not rec["version_date"][:1].isdigit() or rec["version_date"] < cutoff)
        rec["quote"] = (body[max(0, m.start() - 80): m.end() + 80].strip() if m else None)
    except Exception as e:
        rec.update(error=str(e)[:120], found_before_cutoff=False)
    out.append(rec)
    print(f"{case:9s} {rec.get('version_date') or '-':>10s} < {cutoff}  {'FOUND' if rec['found_before_cutoff'] else 'MISS '}  since {rec.get('earliest_snapshot_stating_it') or '-':>8s}  {what}")
json.dump(out, open(os.path.join(HERE, "spec_history.json"), "w"), indent=1, ensure_ascii=False)
