"""Cross-implementation SCREENING oracle (exploratory; not confirmatory).
Rule families over object stores, observable through each client's public API.
World: RAW boto3 on moto (fixed backend). One fresh bucket per probe. s3fs cache invalidated
before every observation (so R2 cache effects cannot confound these families).
Usage: python xfam_oracle.py s3fs|pyarrow -> JSON line {probe: {"pass":bool, "obs":...}}
"""
import json, os, sys, urllib.request, urllib.parse
S3 = os.environ.get("XF_S3", "http://127.0.0.1:5555")
GCS = os.environ.get("XF_GCS", "http://localhost:4443")
BACKEND = os.environ.get("XF_BACKEND", "s3")

class RawGCS:
    """boto3-shaped minimal raw client for fake-gcs-server (JSON API) — world + verification."""
    def _call(self, m, u, d=None, ct="application/json"):
        r = urllib.request.Request(u, data=d, method=m, headers={"Content-Type": ct})
        return urllib.request.urlopen(r, timeout=30).read()
    def create_bucket(self, Bucket):
        self._call("POST", f"{GCS}/storage/v1/b?project=test", json.dumps({"name": Bucket}).encode())
    def put_object(self, Bucket, Key, Body):
        self._call("POST", f"{GCS}/upload/storage/v1/b/{Bucket}/o?uploadType=media&name="
                   + urllib.parse.quote(Key, safe=""), Body, "application/octet-stream")
    def keys(self, Bucket):
        out, tok = [], None
        while True:
            u = f"{GCS}/storage/v1/b/{Bucket}/o?maxResults=1000" + (f"&pageToken={urllib.parse.quote(tok)}" if tok else "")
            d = json.loads(self._call("GET", u)); out += [i["name"] for i in d.get("items", [])]
            tok = d.get("nextPageToken")
            if not tok: return sorted(out)
def raw():
    if BACKEND == "gcs": return RawGCS()
    import boto3
    return boto3.client("s3", endpoint_url=S3, region_name="us-east-1",
                        aws_access_key_id="x", aws_secret_access_key="x")

class S3FS:
    def __init__(self):
        if BACKEND == "gcs":
            import gcsfs; self.v = gcsfs.__version__
            self.fs = gcsfs.GCSFileSystem(endpoint_url=GCS, token="anon", skip_instance_cache=True)
        else:
            import s3fs; self.v = s3fs.__version__
            self.fs = s3fs.S3FileSystem(key="x", secret="x", skip_instance_cache=True,
                                        client_kwargs={"endpoint_url": S3, "region_name": "us-east-1"})
    def _i(self): self.fs.invalidate_cache()
    def ls(self, d): self._i(); return sorted(p.rstrip("/") for p in self.fs.ls(d, detail=False))
    def find(self, d): self._i(); return sorted(self.fs.find(d))
    def info(self, p):
        self._i()
        try: return self.fs.info(p)["type"]
        except FileNotFoundError: return "notfound"
    def delete_dir(self, d): self._i(); self.fs.rm(d, recursive=True)
    def read(self, p): self._i(); return self.fs.cat_file(p)
    def write(self, p, b): self._i(); self.fs.pipe_file(p, b)
    def move(self, a, b): self._i(); self.fs.mv(a, b, recursive=True)
    def copy_file(self, a, b): self._i(); self.fs.copy(a, b)
    def move_file(self, a, b): self._i(); self.fs.mv(a, b)

class PA:
    def __init__(self):
        import pyarrow, pyarrow.fs as pafs; self.v = pyarrow.__version__; self.pafs = pafs
        if BACKEND == "gcs":
            self.fs = pafs.GcsFileSystem(anonymous=True, endpoint_override=GCS.split("//")[1].rstrip("/"), scheme="http")
        else:
            self.fs = pafs.S3FileSystem(access_key="x", secret_key="x", region="us-east-1",
                                        scheme="http", endpoint_override=S3.split("//")[1].rstrip("/"))
    def _sel(self, d, rec):
        return self.fs.get_file_info(self.pafs.FileSelector(d, recursive=rec))
    def ls(self, d): return sorted(i.path.rstrip("/") for i in self._sel(d, False))
    def find(self, d): return sorted(i.path for i in self._sel(d, True)
                                     if i.type == self.pafs.FileType.File)
    def info(self, p):
        t = self.fs.get_file_info(p).type
        return {self.pafs.FileType.File: "file", self.pafs.FileType.Directory: "directory"}.get(t, "notfound")
    def delete_dir(self, d): self.fs.delete_dir(d)
    def read(self, p):
        with self.fs.open_input_stream(p) as f: return f.read()
    def write(self, p, b):
        with self.fs.open_output_stream(p) as f: f.write(b)
    def move(self, a, b): self.fs.move(a, b)
    def copy_file(self, a, b): self.fs.copy_file(a, b)
    def move_file(self, a, b): self.fs.move(a, b)


class NA(Exception):
    """probe needs a concept the client does not expose natively -> not applicable"""

def _split(p):
    b, _, k = p.partition("/"); return b, k

class OBS:
    """object_store (Rust, arrow-rs) via obstore. No directory concept: info/delete_dir/move = n/a."""
    def __init__(self):
        import obstore, importlib.metadata as m; self.o = obstore; self.v = m.version("obstore")
        from obstore.store import S3Store; self.S3Store = S3Store; self.stores = {}
    def st(self, b):
        if b not in self.stores and BACKEND == "gcs":
            from obstore.store import GCSStore
            self.stores[b] = GCSStore(b, skip_signature=True, base_url=GCS, client_options={"allow_http": True})
        if b not in self.stores:
            try:
                self.stores[b] = self.S3Store(b, endpoint=S3, access_key_id="x", secret_access_key="x",
                                              region="us-east-1", client_options={"allow_http": True})
            except TypeError:
                self.stores[b] = self.S3Store(b, config={"endpoint": S3, "access_key_id": "x",
                    "secret_access_key": "x", "region": "us-east-1"}, client_options={"allow_http": True})
        return self.stores[b]
    def ls(self, d):
        b, k = _split(d); r = self.o.list_with_delimiter(self.st(b), prefix=k or None)
        objs = r["objects"]; cps = r["common_prefixes"]
        return sorted([f"{b}/{x.rstrip('/')}" for x in cps] + [f"{b}/{o['path']}" for o in objs])
    def find(self, d):
        b, k = _split(d); out = []
        for batch in self.o.list(self.st(b), prefix=k or None):
            out += [f"{b}/{o['path']}" for o in batch]
        return sorted(out)
    def info(self, p): raise NA()
    def delete_dir(self, d): raise NA()
    def move(self, a, b): raise NA()
    def copy_file(self, a, b_):
        b, k = _split(a); _, k2 = _split(b_); self.o.copy(self.st(b), k, k2)
    def move_file(self, a, b_):
        b, k = _split(a); _, k2 = _split(b_); self.o.rename(self.st(b), k, k2)
    def read(self, p):
        b, k = _split(p); return bytes(self.o.get(self.st(b), k).bytes())
    def write(self, p, data):
        b, k = _split(p); self.o.put(self.st(b), k, data)

class ODAL:
    """Apache OpenDAL (Rust) via opendal. Dirs are addressed with a trailing '/'."""
    def __init__(self):
        import opendal, importlib.metadata as m; self.od = opendal; self.v = m.version("opendal"); self.ops = {}
    def op(self, b):
        if b not in self.ops:
            if BACKEND == "gcs":
                self.ops[b] = self.od.Operator("gcs", bucket=b, endpoint=GCS, allow_anonymous="true",
                    disable_vm_metadata="true", disable_config_load="true")
            else:
                self.ops[b] = self.od.Operator("s3", bucket=b, endpoint=S3, region="us-east-1",
                    access_key_id="x", secret_access_key="x", disable_config_load="true",
                    disable_ec2_metadata="true")
        return self.ops[b]
    def _paths(self, it): return [e.path for e in it]
    def ls(self, d):
        b, k = _split(d); k = k.rstrip("/") + "/" if k else "/"
        return sorted(f"{b}/{x.rstrip('/')}" for x in self._paths(self.op(b).list(k)))
    def find(self, d):
        b, k = _split(d); k = k.rstrip("/") + "/" if k else "/"
        try: it = self.op(b).list(k, recursive=True)
        except TypeError: it = self.op(b).scan(k)
        return sorted(f"{b}/{x}" for x in self._paths(it) if not x.endswith("/"))
    def info(self, p):
        b, k = _split(p)
        for key, kind in ((k, None), (k.rstrip("/") + "/", "directory")):
            try:
                m = self.op(b).stat(key).mode
                return "directory" if m.is_dir() else "file"
            except Exception as e:
                if "NotFound" not in type(e).__name__ and "NotFound" not in str(e): raise
        return "notfound"
    def delete_dir(self, d):
        b, k = _split(d); self.op(b).remove_all(k.rstrip("/") + "/")
    def move(self, a, b_): raise NA()
    def copy_file(self, a, b_):
        b, k = _split(a); _, k2 = _split(b_); self.op(b).copy(k, k2)
    def move_file(self, a, b_):
        b, k = _split(a); _, k2 = _split(b_); self.op(b).rename(k, k2)
    def read(self, p):
        b, k = _split(p); return bytes(self.op(b).read(k))
    def write(self, p, data):
        b, k = _split(p); self.op(b).write(k, data)

class CPL:
    """cloudpathlib (Python, pathlib API over boto3) — independent of fsspec/s3fs."""
    def __init__(self):
        import cloudpathlib, importlib.metadata as m
        self.v = m.version("cloudpathlib")
        if BACKEND == "gcs":
            from cloudpathlib import GSClient, GSPath
            from google.cloud import storage
            from google.auth.credentials import AnonymousCredentials
            sc = storage.Client(credentials=AnonymousCredentials(), project="test",
                                client_options={"api_endpoint": GCS})
            self.cli = GSClient(storage_client=sc); self.S3Path = GSPath; self.scheme = "gs://"
        else:
            from cloudpathlib import S3Client, S3Path
            self.cli = S3Client(endpoint_url=S3, aws_access_key_id="x", aws_secret_access_key="x")
            self.S3Path = S3Path; self.scheme = "s3://"
    def P(self, p): return self.S3Path(f"{self.scheme}{p}", client=self.cli)
    def _s(self, x): return str(x)[len(self.scheme):].rstrip("/")
    def ls(self, d): return sorted(self._s(x) for x in self.P(d).iterdir())
    def find(self, d): return sorted(self._s(x) for x in self.P(d).glob("**/*") if x.is_file())
    def info(self, p):
        x = self.P(p)
        return "file" if x.is_file() else ("directory" if x.is_dir() else "notfound")
    def delete_dir(self, d): self.P(d).rmtree()
    def move(self, a, b): raise NA()
    def copy_file(self, a, b): self.P(a).copy(self.P(b))
    def move_file(self, a, b): self.P(a).rename(self.P(b))
    def read(self, p): return self.P(p).read_bytes()
    def write(self, p, data): self.P(p).write_bytes(data)

class S3P:
    """s3path (Python, pathlib over boto3) — independent of fsspec/cloudpathlib."""
    def __init__(self):
        import boto3, importlib.metadata as m
        from s3path import S3Path, register_configuration_parameter, PureS3Path
        self.v = m.version("s3path"); self.S3Path = S3Path
        res = boto3.resource("s3", endpoint_url=S3, region_name="us-east-1",
                             aws_access_key_id="x", aws_secret_access_key="x")
        register_configuration_parameter(PureS3Path("/"), resource=res)
    def P(self, p): return self.S3Path("/" + p)
    def _s(self, x): return str(x).lstrip("/").rstrip("/")
    def ls(self, d): return sorted(self._s(x) for x in self.P(d).iterdir())
    def find(self, d): return sorted(self._s(x) for x in self.P(d).rglob("*") if x.is_file())
    def info(self, p):
        x = self.P(p)
        return "file" if x.is_file() else ("directory" if x.is_dir() else "notfound")
    def delete_dir(self, d): raise NA()
    def move(self, a, b): raise NA()
    def copy_file(self, a, b): raise NA()
    def move_file(self, a, b): self.P(a).rename(self.P(b))
    def read(self, p): return self.P(p).read_bytes()
    def write(self, p, data): self.P(p).write_bytes(data)

def keys(c, b):
    if BACKEND == "gcs": return c.keys(b)
    out, tok = [], None
    while True:
        kw = {"Bucket": b, **({"ContinuationToken": tok} if tok else {})}
        r = c.list_objects_v2(**kw); out += [o["Key"] for o in r.get("Contents", [])]
        if not r.get("IsTruncated"): return sorted(out)
        tok = r["NextContinuationToken"]

N = [0]
def bucket(c, world):
    N[0] += 1; b = f"xf{N[0]:03d}"; c.create_bucket(Bucket=b)
    for k, v in world.items(): c.put_object(Bucket=b, Key=k, Body=v)
    return b

def probe(res, name, fn):
    try:
        ok, obs = fn()
    except NA:
        res[name] = {"pass": None, "obs": "n/a"}; return
    except Exception as e:
        if type(e).__name__ in ("UnsupportedError", "NotImplementedError") or "Unsupported (permanent)" in str(e):
            res[name] = {"pass": None, "obs": f"n/a:{type(e).__name__}"}; return
        ok, obs = False, f"EXC:{type(e).__name__}: {str(e)[:100]}"
        res[name] = {"pass": False, "obs": obs}; return
    except Exception as e:
        ok, obs = False, f"EXC:{type(e).__name__}: {str(e)[:100]}"
    res[name] = {"pass": bool(ok), "obs": obs}

def run(cl):
    c, r = raw(), {}
    # ---- F1 path-segment boundary -------------------------------------------------
    W1 = {"a/x": b"1", "ab": b"2", "ab2/y": b"3", "a.b/z": b"4"}
    b = bucket(c, W1)
    probe(r, "F1_ls_boundary", lambda: (lambda o: (o == [f"{b}/a/x"], o))(cl.ls(f"{b}/a")))
    probe(r, "F1_find_boundary", lambda: (lambda o: (o == [f"{b}/a/x"], o))(cl.find(f"{b}/a")))
    probe(r, "F1_info_a_is_dir", lambda: (lambda o: (o == "directory", o))(cl.info(f"{b}/a")))
    probe(r, "F1_info_ab_is_file", lambda: (lambda o: (o == "file", o))(cl.info(f"{b}/ab")))
    probe(r, "F1_info_prefix_notfound", lambda: (lambda o: (o == "notfound", o))(cl.info(f"{b}/a.")))
    b = bucket(c, W1)
    def f1del():
        cl.delete_dir(f"{b}/a"); k = keys(c, b)
        return k == ["a.b/z", "ab", "ab2/y"], k
    probe(r, "F1_delete_boundary", f1del)
    b = bucket(c, {"very/similar/prefix1": b"1", "very/similar/prefix2": b"2",
                   "very/similar/prefix3/something": b"3"})
    for q in ["very/similar/prefix", "very/similar/prefi", "very/similar/prefix3/some"]:
        probe(r, f"F1_stat_string_prefix_notfound[{q}]", lambda q=q: (lambda o: (o == "notfound", o))(cl.info(f"{b}/{q}")))
        probe(r, f"F1_stat_string_prefix_slash_notfound[{q}]", lambda q=q: (lambda o: (o == "notfound", o))(cl.info(f"{b}/{q}/")))
    # ---- F3 special characters in keys -----------------------------------------------
    SPECIAL = ["sp ace", "pl+us", "per%25cent", "pct%", "hash#", "q?mark", "eq=1", "tilde~",
               "café", "semi;colon", "amp&", "colon:x", "star*", "brack[1]"]
    b = bucket(c, {f"s/{n}": n.encode() for n in SPECIAL})
    probe(r, "F3_ls_names_exact", lambda: (lambda o: (o == sorted(f"{b}/s/{n}" for n in SPECIAL),
            sorted(set(o) ^ set(f"{b}/s/{n}" for n in SPECIAL))))(cl.ls(f"{b}/s")))
    for n in SPECIAL:
        probe(r, f"F3_read[{n}]", lambda n=n: (lambda o: (o == n.encode(), o[:20] if isinstance(o, bytes) else o))(cl.read(f"{b}/s/{n}")))
    b = bucket(c, {})
    for n in SPECIAL:
        def wr(n=n):
            cl.write(f"{b}/w/{n}", b"v"); k = keys(c, b)
            return f"w/{n}" in k, [x for x in k if x.startswith("w/")][-1:]
        probe(r, f"F3_write_key_exact[{n}]", wr)
    # ---- F4 pagination -------------------------------------------------------------
    b = bucket(c, {})
    for i in range(1105):
        c.put_object(Bucket=b, Key=f"many/{i:05d}", Body=b"")
    probe(r, "F4_ls_1105", lambda: (lambda o: (len(o) == 1105, len(o)))(cl.ls(f"{b}/many")))
    probe(r, "F4_find_1105", lambda: (lambda o: (len(o) == 1105, len(o)))(cl.find(f"{b}/many")))
    # ---- F6 trailing slash equivalence --------------------------------------------------
    b = bucket(c, {"d/f1": b"1", "d/g/f2": b"2"})
    probe(r, "F6_ls_slash_eq", lambda: (lambda x, y: (x == y, {"d": x, "d/": y}))(cl.ls(f"{b}/d"), cl.ls(f"{b}/d/")))
    probe(r, "F6_info_slash_eq", lambda: (lambda x, y: (x == y == "directory", [x, y]))(cl.info(f"{b}/d"), cl.info(f"{b}/d/")))
    # ---- F7 marker-only empty directory ----------------------------------------------
    b = bucket(c, {"e/": b"", "f": b"1"})
    probe(r, "F7_marker_is_dir", lambda: (lambda o: (o == "directory", o))(cl.info(f"{b}/e")))
    probe(r, "F7_root_lists_marker_dir", lambda: (lambda o: (f"{b}/e" in o, o))(cl.ls(b)))
    probe(r, "F7_ls_marker_dir_empty", lambda: (lambda o: (o == [], o))(cl.ls(f"{b}/e")))
    b = bucket(c, {"m/": b"", "m/x": b"1"})
    probe(r, "F7_ls_dir_excludes_own_marker", lambda: (lambda o: (o == [f"{b}/m/x"], o))(cl.ls(f"{b}/m")))
    # ---- F2-move: moving a directory carries its markers ----------------------------------
    b = bucket(c, {"src/": b"", "src/sub/": b"", "src/sub/f": b"1", "src/g": b"2"})
    def mv():
        cl.move(f"{b}/src", f"{b}/dst"); k = keys(c, b)
        return (not any(x.startswith("src/") for x in k) and "dst/sub/f" in k and "dst/g" in k), k
    probe(r, "F2_move_dir_complete", mv)
    # ---- F3b copy / move of keys with special characters (Arrow GH-28758 family) --------
    CM = ["eq=1", "pl+us", "sp ace", "pct%", "caf\u00e9"]
    for n in CM:
        b = bucket(c, {f"src/{n}": b"v"})
        def cp(n=n, b=b):
            cl.copy_file(f"{b}/src/{n}", f"{b}/dst/{n}"); k = keys(c, b)
            return f"dst/{n}" in k and f"src/{n}" in k, k
        probe(r, f"F3b_copy[{n}]", cp)
        b = bucket(c, {f"src/{n}": b"v"})
        def mvf(n=n, b=b):
            cl.move_file(f"{b}/src/{n}", f"{b}/dst/{n}"); k = keys(c, b)
            # parent-marker re-creation ('src/') is a separate, by-design behaviour (Arrow GH-36275)
            return f"dst/{n}" in k and f"src/{n}" not in k, k
        probe(r, f"F3b_move[{n}]", mvf)
    # ---- F8 stat of a NON-existent directory (OpenDAL #2086 family) ---------------------
    b = bucket(c, {"real/x": b"1"})
    probe(r, "F8_stat_missing", lambda: (lambda o: (o == "notfound", o))(cl.info(f"{b}/nothere")))
    probe(r, "F8_stat_missing_slash", lambda: (lambda o: (o == "notfound", o))(cl.info(f"{b}/nothere/")))
    # ---- F9 keys with a double slash (Arrow GH-38821 family) -----------------------------
    b = bucket(c, {"dd//x": b"1", "dd/y": b"2", "ddz": b"3"})
    def dsl():
        cl.delete_dir(f"{b}/dd"); k = keys(c, b)
        return k == ["ddz"], k
    probe(r, "F9_delete_dir_with_double_slash_key", dsl)
    # ---- F10 zero-byte object without slash is a FILE ------------------------------------
    b = bucket(c, {"z": b"", "zz/": b""})
    probe(r, "F10_zero_byte_is_file", lambda: (lambda o: (o == "file", o))(cl.info(f"{b}/z")))
    # ---- F11 directory names with spaces / special characters (object_store #223) --------
    b = bucket(c, {"s p/x": b"1", "s p/y/z": b"2", "u+v/x": b"3"})
    probe(r, "F11_ls_dir_with_space", lambda: (lambda o: (o == [f"{b}/s p/x", f"{b}/s p/y"], o))(cl.ls(f"{b}/s p")))
    probe(r, "F11_find_dir_with_space", lambda: (lambda o: (o == [f"{b}/s p/x", f"{b}/s p/y/z"], o))(cl.find(f"{b}/s p")))
    probe(r, "F11_ls_dir_with_plus", lambda: (lambda o: (o == [f"{b}/u+v/x"], o))(cl.ls(f"{b}/u+v")))
    # ---- F14 type exclusivity: a file is not a dir, a dir is not a file ------------------
    b = bucket(c, {"t/f": b"1", "t/d/x": b"2"})
    probe(r, "F14_file_is_file", lambda: (lambda o: (o == "file", o))(cl.info(f"{b}/t/f")))
    probe(r, "F14_implicit_dir_is_dir", lambda: (lambda o: (o == "directory", o))(cl.info(f"{b}/t/d")))
    probe(r, "F14_bucket_root_is_dir", lambda: (lambda o: (o == "directory", o))(cl.info(f"{b}")))
    return r

if __name__ == "__main__":
    cl = {"s3fs": S3FS, "pyarrow": PA, "obstore": OBS, "opendal": ODAL, "cloudpathlib": CPL, "s3path": S3P, "gcsfs": S3FS}[sys.argv[1]]()
    res = run(cl)
    print(json.dumps({"client": sys.argv[1], "backend": BACKEND, "version": cl.v, "probes": res}, default=repr))
