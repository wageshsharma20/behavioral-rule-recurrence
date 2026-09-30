"""Plain-key CONTROL for mutant filtering (not part of the frozen screening battery).
A rule-specific mutant must leave ordinary behaviour intact: write+read of plain keys, listing, exists.
Usage: python control_oracle.py <client>  -> {"pass": bool, "obs": ...}"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "oracle"))
import xfam_oracle as X
def main(name):
    cl = {"s3fs": X.S3FS, "gcsfs": X.S3FS, "cloudpathlib": X.CPL, "s3path": X.S3P}[name](); c = X.raw()
    b = X.bucket(c, {"plain/a.txt": b"A", "plain/sub/b.txt": b"B"}); obs = {}
    try:
        obs["read"] = cl.read(f"{b}/plain/a.txt") == b"A"
        cl.write(f"{b}/plain/new.txt", b"N"); obs["write"] = "plain/new.txt" in X.keys(c, b)
        obs["ls"] = cl.ls(f"{b}/plain") == sorted([f"{b}/plain/a.txt", f"{b}/plain/new.txt", f"{b}/plain/sub"])
        obs["info"] = cl.info(f"{b}/plain/a.txt") == "file" and cl.info(f"{b}/plain") == "directory"
    except Exception as e:
        obs["error"] = f"{type(e).__name__}: {str(e)[:80]}"
    print(json.dumps({"pass": all(v is True for k, v in obs.items() if k != "error") and "error" not in obs, "obs": obs}))
if __name__ == "__main__":
    main(sys.argv[1])
