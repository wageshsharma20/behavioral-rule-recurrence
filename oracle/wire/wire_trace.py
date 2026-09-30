"""Run ONE Golden-Case discriminating operation with the client talking to the backend through tap.py.
The world is built, and the outcome verified, through the backend's raw API directly (not through the relay),
exactly as in the screening oracles; only the client's own requests are recorded. Prints one JSON line:
  {"row":..., "verdict": <oracle verdict on the emulator>, "log": [start, end] byte offsets of the op's traffic}
Usage: WIRE_LOG=<file> XF_BACKEND=s3|gcs XF_S3_UP=... XF_S3_TAP=... python wire_trace.py <op> <client>"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
OP, CL = sys.argv[1], sys.argv[2]
S3_UP, S3_TAP = os.environ["XF_S3_UP"], os.environ["XF_S3_TAP"]
GCS_UP, GCS_TAP = os.environ["XF_GCS_UP"], os.environ["XF_GCS_TAP"]
os.environ["XF_S3"], os.environ["XF_GCS"] = S3_UP, GCS_UP
import xfam_oracle as X
c = X.raw()                                   # raw API client -> backend directly
def world(w):
    X.N[0] += 1; b = f"wire{X.N[0]:03d}"; c.create_bucket(Bucket=b)
    for k, v in w.items(): c.put_object(Bucket=b, Key=k, Body=v)
    return b
WORLDS = {"gc1": {"d/sub/": b"", "d/sub/f": b"x", "d/g": b"x", "dx/k": b"x"},
          "write": {}, "read": {"s/hash#": b"hash#"}, "copy": {"src/café": b"v"},
          "exists": {"very/similar/prefix1": b"1", "very/similar/prefix2": b"2", "very/similar/prefix3/something": b"3"},
          "movedir": {"src/sub/f": b"1", "src/g": b"2", "srcx": b"3"}}
b = world(WORLDS[OP])
X.S3, X.GCS = S3_TAP, GCS_TAP                 # the client under test -> relay -> backend
os.environ["XF_S3"], os.environ["XF_GCS"] = S3_TAP, GCS_TAP
if OP == "gc1":
    import f2_delete_oracle as F; F.S3_URL = S3_TAP
    delete, _, ver = F.client(CL); act = lambda: delete(b)
elif OP == "movedir":
    import xfam2_oracle as X2
    _, mvdir, _, ver = X2.ops(CL); act = lambda: mvdir(f"{b}/src", f"{b}/dst")
else:
    cl = {"s3fs": X.S3FS, "gcsfs": X.S3FS, "pyarrow": X.PA, "obstore": X.OBS, "opendal": X.ODAL,
          "cloudpathlib": X.CPL, "s3path": X.S3P}[CL](); ver = cl.v
    act = {"write": lambda: cl.write(f"{b}/w/café", b"v"), "read": lambda: cl.read(f"{b}/s/hash#"),
           "copy": lambda: cl.copy_file(f"{b}/src/café", f"{b}/dst/café"),
           "exists": lambda: cl.info(f"{b}/very/similar/prefix")}[OP]
log = os.environ["WIRE_LOG"]; start = os.path.getsize(log)
err, res = None, None
try: res = act()
except Exception as e: err = f"{type(e).__name__}: {str(e)[:120]}"
end = os.path.getsize(log)
X.S3, X.GCS = S3_UP, GCS_UP
k = X.keys(c, b)
V = {"gc1": lambda: not any(x.startswith("d/") for x in k) and "dx/k" in k,
     "write": lambda: "w/café" in k,
     "read": lambda: res == b"hash#",
     "copy": lambda: "dst/café" in k and "src/café" in k,
     "exists": lambda: res == "notfound",
     "movedir": lambda: "srcx" in k and not [x for x in k if x.startswith("dst") and ("srcx" in x or x == "dstx")]
                        and any(x.startswith("dst") for x in k)}[OP]()
print(json.dumps({"op": OP, "client": CL, "version": ver, "bucket": b, "verdict": V, "keys_after": k,
                  "result": res if isinstance(res, str) else (repr(res)[:40] if res is not None else None),
                  "error": err, "log": [start, end]}))
