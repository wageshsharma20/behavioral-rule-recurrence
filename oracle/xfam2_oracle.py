"""Screening oracle, batch 2 (S3/moto). Reuses world/verification helpers from xfam_oracle (read-only import).
F13 rmdir semantics (s3path #205 family) · F15 directory move completeness (s3fs markers / s3path rename).
Usage: python xfam2_oracle.py <client> -> JSON line"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import xfam_oracle as X

def ops(name):
    """per-client native rmdir / move_dir; NA if the client has no native operation."""
    if name in ("s3fs", "gcsfs"):
        if name == "gcsfs":
            import gcsfs as mod; fs = mod.GCSFileSystem(endpoint_url=X.GCS, token="anon", skip_instance_cache=True)
        else:
            import s3fs as mod; fs = mod.S3FileSystem(key="x", secret="x", skip_instance_cache=True,
                        client_kwargs={"endpoint_url": X.S3, "region_name": "us-east-1"})
        def rmdir(p): fs.invalidate_cache(); fs.rmdir(p)
        def mvdir(a, b): fs.invalidate_cache(); fs.mv(a, b, recursive=True)
        def cpdir(a, b): fs.invalidate_cache(); fs.copy(a, b, recursive=True)
        return rmdir, mvdir, cpdir, mod.__version__
    if name == "cloudpathlib":
        import importlib.metadata as m; from cloudpathlib import S3Client, S3Path
        cli = S3Client(endpoint_url=X.S3, aws_access_key_id="x", aws_secret_access_key="x")
        P = lambda p: S3Path(f"s3://{p}", client=cli)
        return (lambda p: P(p).rmdir()), (lambda a, b: P(a).rename(P(b))), (lambda a, b: P(a).copytree(P(b))), m.version("cloudpathlib")
    if name == "s3path":
        X.S3P()  # registers the endpoint configuration
        import importlib.metadata as m; from s3path import S3Path
        P = lambda p: S3Path("/" + p)
        def na(*a): raise X.NA()
        return (lambda p: P(p).rmdir()), (lambda a, b: P(a).rename(P(b))), na, m.version("s3path")
    if name == "opendal":
        o = X.ODAL()
        def rmdir(p):
            b, k = X._split(p); o.op(b).delete(k.rstrip("/") + "/")
        def mvdir(a, b): raise X.NA()
        return rmdir, mvdir, mvdir, o.v
    if name in ("pyarrow", "obstore"):
        c = X.PA() if name == "pyarrow" else X.OBS()
        def na(*a): raise X.NA()
        return na, na, na, c.v
    raise SystemExit("unknown client")

def run(name):
    c = X.raw(); rmdir, mvdir, cpdir, ver = ops(name); r = {}
    def attempt(fn):
        try: fn(); return None
        except X.NA: raise
        except Exception as e: return f"{type(e).__name__}"
    # F13a rmdir on a NON-empty explicit dir must not delete contents
    b = X.bucket(c, {"n/": b"", "n/x": b"1"})
    def f13a():
        err = attempt(lambda: rmdir(f"{b}/n")); k = X.keys(c, b)
        return "n/x" in k, {"err": err, "left": k}
    X.probe(r, "F13a_rmdir_nonempty_keeps_contents", f13a)
    b = X.bucket(c, {"i/x": b"1"})
    def f13b():
        err = attempt(lambda: rmdir(f"{b}/i")); k = X.keys(c, b)
        return "i/x" in k, {"err": err, "left": k}
    X.probe(r, "F13b_rmdir_nonempty_implicit_keeps_contents", f13b)
    b = X.bucket(c, {"e/": b"", "f": b"1"})
    def f13c():
        err = attempt(lambda: rmdir(f"{b}/e")); k = X.keys(c, b)
        return k == ["f"], {"err": err, "left": k}
    X.probe(r, "F13c_rmdir_empty_marker_removes_it", f13c)
    # F15 moving a directory moves everything (markers included), leaves nothing behind
    for tag, world in (("markers", {"src/": b"", "src/sub/": b"", "src/sub/f": b"1", "src/g": b"2", "srcx": b"3"}),
                       ("implicit", {"src/sub/f": b"1", "src/g": b"2", "srcx": b"3"})):
        b = X.bucket(c, world)
        def f15(b=b, world=world):
            err = attempt(lambda: mvdir(f"{b}/src", f"{b}/dst")); k = X.keys(c, b)
            moved = all(("dst/" + x[4:]) in k for x in world if x.startswith("src/"))
            return (not any(x.startswith("src/") for x in k)) and moved and "srcx" in k, {"err": err, "left": k}
        X.probe(r, f"F15_move_dir_complete[{tag}]", f15)
        b = X.bucket(c, world)
        def f15b(b=b):
            err = attempt(lambda: mvdir(f"{b}/src", f"{b}/dst")); k = X.keys(c, b)
            touched = [x for x in k if x.startswith("dst") and ("srcx" in x or x == "dstx")]
            return "srcx" in k and not touched and any(x.startswith("dst") for x in k), {"err": err, "keys": k}
        X.probe(r, f"F15b_move_dir_sibling_untouched[{tag}]", f15b)
    # F16 copying a directory must not pick up same-prefix siblings (gcsfs #576 family)
    b = X.bucket(c, {"src/g": b"1", "src/sub/f": b"2", "srcx": b"3", "src_old/h": b"4"})
    def f16():
        err = attempt(lambda: cpdir(f"{b}/src", f"{b}/dst")); k = X.keys(c, b)
        dst = sorted(x for x in k if x.startswith("dst"))
        return dst == ["dst/g", "dst/sub/f"], {"err": err, "dst": dst}
    X.probe(r, "F16_copy_dir_boundary", f16)
    b = X.bucket(c, {"src/g": b"1", "src/sub/f": b"2", "srcx": b"3", "src_old/h": b"4"})
    def f16b():
        err = attempt(lambda: cpdir(f"{b}/src", f"{b}/dst")); k = X.keys(c, b)
        dst = [x for x in k if x.startswith("dst")]
        leaked = [x for x in dst if "srcx" in x or "src_old" in x or x.startswith(("dstx", "dst_old"))]
        return bool(dst) and not leaked, {"err": err, "dst": dst}
    X.probe(r, "F16b_copy_dir_sibling_not_copied", f16b)
    # ---- batch 3 (uses the generic adapters from xfam_oracle) ----------------------------
    cl = {"s3fs": X.S3FS, "gcsfs": X.S3FS, "pyarrow": X.PA, "obstore": X.OBS, "opendal": X.ODAL,
          "cloudpathlib": X.CPL, "s3path": X.S3P}[name]()
    # F4b >1000 COMMON PREFIXES (subdirectories) — different pagination path than files
    b = X.bucket(c, {})
    if X.BACKEND == "s3":
        for i in range(1105): c.put_object(Bucket=b, Key=f"many/d{i:05d}/f", Body=b"")
    else:
        for i in range(1105): c.put_object(Bucket=b, Key=f"many/d{i:05d}/f", Body=b"")
    X.probe(r, "F4b_ls_1105_subdirs", lambda: (lambda o: (len(o) == 1105, len(o)))(cl.ls(f"{b}/many")))
    # F17 a FILE addressed with a trailing slash is not that file (Arrow GH-20316 family)
    b = X.bucket(c, {"t/f": b"1"})
    X.probe(r, "F17_file_with_trailing_slash_not_file", lambda: (lambda o: (o != "file", o))(cl.info(f"{b}/t/f/")))
    # G glob basics (pathlib semantics) — only clients with a native glob
    b = X.bucket(c, {"d/a.csv": b"1", "d/b.txt": b"2", "d/sub/c.csv": b"3", "dx/e.csv": b"4"})
    def gl(pat):
        if name in ("s3fs", "gcsfs"): cl._i(); return sorted(cl.fs.glob(f"{b}/{pat}"))
        if name == "cloudpathlib": return sorted(cl._s(x) for x in cl.P(b).glob(pat))
        if name == "s3path": return sorted(cl._s(x) for x in cl.P(b).glob(pat))
        raise X.NA()
    X.probe(r, "G1_glob_star_one_level", lambda: (lambda o: (o == [f"{b}/d/a.csv"], o))(gl("d/*.csv")))
    X.probe(r, "G2_glob_doublestar_recursive", lambda: (lambda o: (o == [f"{b}/d/a.csv", f"{b}/d/sub/c.csv"], o))(gl("d/**/*.csv")))
    X.probe(r, "G3_glob_prefix_boundary", lambda: (lambda o: (o == [f"{b}/d/a.csv"], o))(gl("d/a*")))
    return {"client": name, "backend": X.BACKEND, "version": ver, "probes": r}

if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), default=repr))
