"""F2-delete portable oracle — recursive directory deletion vs. directory-marker objects.

Candidate rule (cross-language): deleting a directory recursively must remove EVERY object
whose key lies under it, INCLUDING zero-byte directory markers ("d/", "d/sub/"), so that the
directory no longer exists; objects that merely share a string prefix ("dx/…") must survive.
History: Apache Arrow C++ GH-38618 / PR #38845 (2023, regression in 14.0; nested markers kept)
         s3fs #918 (2024 issue; fix PRs #1004/#1005 Jan 2026; top marker kept)

World: RAW boto3 on moto (backend fixed). Verification: RAW boto3 listing (not the client).
Client adapters: s3fs (Python) / pyarrow.fs.S3FileSystem (C++).
Usage: python f2_delete_oracle.py s3fs|pyarrow  -> one JSON line
"""
import json, os, sys
S3_URL = os.environ.get("XF_S3", "http://127.0.0.1:5555")
VARIANTS = {   # bucket -> keys; target directory is always "d"
    "v-top":    {"d/": b"", "d/g": b"x", "dx/k": b"x"},
    "v-nested": {"d/sub/": b"", "d/sub/f": b"x", "d/g": b"x", "dx/k": b"x"},
    "v-emptysub": {"d/": b"", "d/empty/": b"", "dx/k": b"x"},
    "v-full":   {"d/": b"", "d/sub/": b"", "d/sub/f": b"x", "d/g": b"x", "d/empty/": b"",
                 "dx/k": b"x"},
    "v-implicit": {"d/sub/f": b"x", "d/g": b"x", "dx/k": b"x"},   # control: no markers at all
}

def raw():
    import boto3
    return boto3.client("s3", endpoint_url=S3_URL, region_name="us-east-1",
                        aws_access_key_id="x", aws_secret_access_key="x")

def keys(c, b):
    return sorted(o["Key"] for o in c.list_objects_v2(Bucket=b).get("Contents", []))

def client(name):
    if name == "s3fs":
        import s3fs
        fs = s3fs.S3FileSystem(key="x", secret="x", skip_instance_cache=True,
                               client_kwargs={"endpoint_url": S3_URL, "region_name": "us-east-1"})
        def delete(b):
            fs.rm(f"{b}/d", recursive=True)
        def exists(b):
            fs.invalidate_cache()
            return fs.exists(f"{b}/d")
        return delete, exists, s3fs.__version__
    if name == "pyarrow":
        import pyarrow, pyarrow.fs as pafs
        fs = pafs.S3FileSystem(access_key="x", secret_key="x", region="us-east-1",
                               scheme="http", endpoint_override=S3_URL.split("//")[1].rstrip("/"))
        def delete(b):
            fs.delete_dir(f"{b}/d")
        def exists(b):
            return fs.get_file_info(f"{b}/d").type != pafs.FileType.NotFound
        return delete, exists, pyarrow.__version__
    if name == "cloudpathlib":
        import importlib.metadata as m
        from cloudpathlib import S3Client, S3Path
        cli = S3Client(endpoint_url=S3_URL, aws_access_key_id="x", aws_secret_access_key="x")
        def delete(b): S3Path(f"s3://{b}/d", client=cli).rmtree()
        def exists(b): return S3Path(f"s3://{b}/d", client=cli).exists()
        return delete, exists, m.version("cloudpathlib")
    if name == "opendal":
        import opendal, importlib.metadata as m
        ops = {}
        def op(b):
            if b not in ops:
                ops[b] = opendal.Operator("s3", bucket=b, endpoint=S3_URL, region="us-east-1",
                    access_key_id="x", secret_access_key="x", disable_config_load="true",
                    disable_ec2_metadata="true")
            return ops[b]
        def delete(b): op(b).remove_all("d/")
        def exists(b):
            try: op(b).stat("d/"); return True
            except Exception: return False
        return delete, exists, m.version("opendal")
    raise SystemExit("unknown client")

def main(name):
    c = raw(); delete, exists, ver = client(name)
    out = {"client": name, "version": ver, "variants": {}}
    for b, world in VARIANTS.items():
        c.create_bucket(Bucket=b)
        for k, v in world.items():
            c.put_object(Bucket=b, Key=k, Body=v)
        err = None
        try:
            delete(b)
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
        left = keys(c, b)
        try:
            still = exists(b)
        except Exception as e:
            still = f"EXC:{type(e).__name__}"
        out["variants"][b] = {
            "A_nothing_under_d": not any(k.startswith("d/") for k in left),
            "B_sibling_prefix_survives": "dx/k" in left,
            "C_client_says_gone": still is False,
            "left": left, "error": err}
    v = out["variants"]
    out["VERDICT_rule_holds"] = all(x["A_nothing_under_d"] and x["B_sibling_prefix_survives"]
                                    for x in v.values())
    out["failing"] = sorted(f"{b}:{a}" for b, x in v.items()
                            for a in ("A_nothing_under_d", "B_sibling_prefix_survives")
                            if not x[a])
    print(json.dumps(out))

if __name__ == "__main__":
    main(sys.argv[1])
