"""Self-consistency check (does the violation contradict the client's OWN API?), per Golden-Case / PV1 row.
The world is built through the raw API; the operation and every follow-up observation use ONLY the client under
test. A row is 'self-contradictory' if, after the operation, the client's own API reports a state that contradicts
what the operation (per the client's own documentation of it) promised or what the client itself reported before:
  gc1     delete_dir(d) returned normally, but the client still reports d as existing
  read    the client lists s/hash# under s/, but reading that listed path fails or returns other bytes
  copy    the client reads src/café successfully, but copying it fails or yields no dst/café in the client's listing
  write   write(w/café) returned, but the client's own listing of w/ does not contain w/café
  exists  the client reports directory foo while its own recursive listing of foo/ is empty
  movedir rename(src, dst) changed an object that is not inside src by the client's own non-recursive listing
          (walked level by level, taken before the move)
Usage: python self_consistency.py <op> <client>   (XF_BACKEND, XF_S3/XF_GCS as for the oracles)"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
OP, CL = sys.argv[1], sys.argv[2]
import xfam_oracle as X
c = X.raw()
def world(w):
    X.N[0] += 1; b = f"self{X.N[0]:03d}"; c.create_bucket(Bucket=b)
    for k, v in w.items(): c.put_object(Bucket=b, Key=k, Body=v)
    return b
def attempt(f):
    try: return f(), None
    except Exception as e: return None, f"{type(e).__name__}: {str(e)[:100]}"
out = {"op": OP, "client": CL}
if OP == "gc1":
    import f2_delete_oracle as F
    delete, exists, ver = F.client(CL)
    b = world({"d/sub/": b"", "d/sub/f": b"x", "d/g": b"x", "dx/k": b"x"})
    _, err = attempt(lambda: delete(b)); still, e2 = attempt(lambda: exists(b))
    out.update(version=ver, delete_error=err, client_says_exists_after=still, exists_error=e2,
               contradiction=(err is None and still is True))
elif OP == "movedir":
    import xfam2_oracle as X2
    _, mvdir, _, ver = X2.ops(CL)
    lister = X.S3FS() if CL in ("s3fs", "gcsfs") else X.S3P()
    b = world({"src/sub/f": b"1", "src/g": b"2", "srcx": b"3"})
    def walk(d, depth=0):   # the client's own notion of 'inside d': its non-recursive listing, walked level by level
        out = []
        for p in lister.ls(d):
            if p.rstrip("/") == d.rstrip("/") or depth > 5: continue
            out += walk(p, depth + 1) if lister.info(p) == "directory" else [p]
        return out
    before, e0 = attempt(lambda: walk(f"{b}/src"))
    _, err = attempt(lambda: mvdir(f"{b}/src", f"{b}/dst"))
    after = X.keys(c, b)            # which objects changed is read from the raw API; 'inside' is the client's own view
    inside = {p.split("/", 1)[1] for p in (before or [])}
    changed_outside = [k for k in ["srcx"] if k not in after] + [k for k in after if k.startswith("dst") and not k.startswith("dst/")]
    out.update(version=ver, client_listing_of_src=sorted(inside), move_error=err, changed_outside_listing=changed_outside,
               contradiction=bool(changed_outside) and "srcx" not in inside)
else:
    cl = {"s3fs": X.S3FS, "gcsfs": X.S3FS, "pyarrow": X.PA, "obstore": X.OBS, "opendal": X.ODAL,
          "cloudpathlib": X.CPL, "s3path": X.S3P}[CL](); out["version"] = cl.v
    if OP == "read":
        b = world({"s/hash#": b"hash#"})
        listed, e0 = attempt(lambda: cl.ls(f"{b}/s")); data, err = attempt(lambda: cl.read(f"{b}/s/hash#"))
        out.update(client_lists=listed, read_error=err, read_ok=(data == b"hash#"),
                   contradiction=bool(listed) and f"{b}/s/hash#" in listed and data != b"hash#")
    elif OP == "copy":
        b = world({"src/café": b"v"})
        data, e0 = attempt(lambda: cl.read(f"{b}/src/café"))     # the client itself can read the source
        kind = "readable" if data == b"v" else f"unreadable ({e0})"
        _, err = attempt(lambda: cl.copy_file(f"{b}/src/café", f"{b}/dst/café"))
        lst, e1 = attempt(lambda: cl.find(f"{b}/dst"))
        ok = bool(lst) and f"{b}/dst/café" in lst
        out.update(client_info_src=kind, copy_error=err, client_finds_copy=ok,
                   contradiction=(not ok) and kind == "readable")
    elif OP == "write":
        b = world({})
        _, err = attempt(lambda: cl.write(f"{b}/w/café", b"v")); lst, e1 = attempt(lambda: cl.find(f"{b}/w"))
        back, e2 = attempt(lambda: cl.read(f"{b}/w/café"))
        out.update(write_error=err, client_lists=lst, client_reads_back=(back == b"v"),
                   contradiction=err is None and not (lst and f"{b}/w/café" in lst))
    elif OP == "exists":
        b = world({"very/similar/prefix1": b"1", "very/similar/prefix2": b"2", "very/similar/prefix3/something": b"3"})
        kind, e0 = attempt(lambda: cl.info(f"{b}/very/similar/prefix"))
        lst, e1 = attempt(lambda: cl.find(f"{b}/very/similar/prefix"))
        out.update(client_info=kind, client_recursive_listing=lst,
                   contradiction=(kind == "directory") and not lst)
print(json.dumps(out, default=repr))
