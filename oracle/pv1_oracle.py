"""PV1 prospective oracle (NOT part of the frozen screening battery): segment boundary in s3path rmdir/rename.
A1 rmdir('tmp') [empty dir] must not delete 'tmpfile.txt' or 'tmp_keep/important.csv'
A2 rename('reports'->'moved') must not touch 'reportsX.txt' / 'reports_archive/old.csv'
A3 rename('a'->'z') must map 'a/b/a/x' -> 'z/b/a/x' (only the leading segment)
A4 control: rename('plain'->'plain2') moves all of plain/ ; rmdir of an empty marker dir removes the marker
Usage: python pv1_oracle.py  (s3path client, moto at XF_S3) -> JSON"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__)); import xfam_oracle as X
X.S3P()  # register endpoint
from s3path import S3Path
c = X.raw(); r = {}
def P(p): return S3Path("/" + p)
b = X.bucket(c, {"tmp/": b"", "tmpfile.txt": b"1", "tmp_keep/important.csv": b"2"})
try: P(f"{b}/tmp").rmdir()
except Exception as e: r["A1_err"] = type(e).__name__
k = X.keys(c, b); r["A1_rmdir_siblings_survive"] = {"pass": "tmpfile.txt" in k and "tmp_keep/important.csv" in k, "keys": k}
b = X.bucket(c, {"reports/2024.csv": b"1", "reportsX.txt": b"2", "reports_archive/old.csv": b"3"})
P(f"{b}/reports").rename(P(f"{b}/moved")); k = X.keys(c, b)
r["A2_rename_siblings_untouched"] = {"pass": k == ["moved/2024.csv", "reportsX.txt", "reports_archive/old.csv"] or sorted(k) == sorted(["moved/2024.csv", "reportsX.txt", "reports_archive/old.csv"]), "keys": k}
b = X.bucket(c, {"a/b/a/x": b"1"}); P(f"{b}/a").rename(P(f"{b}/z")); k = X.keys(c, b)
r["A3_rename_leading_segment_only"] = {"pass": k == ["z/b/a/x"], "keys": k}
b = X.bucket(c, {"plain/f": b"1", "plain/g/h": b"2"}); P(f"{b}/plain").rename(P(f"{b}/plain2")); k = X.keys(c, b)
b2 = X.bucket(c, {"e/": b""}); P(f"{b2}/e").rmdir(); k2 = X.keys(c, b2)
r["A4_control"] = {"pass": sorted(k) == ["plain2/f", "plain2/g/h"] and k2 == [], "keys": [k, k2]}
r["VERDICT_rule_holds"] = all(v["pass"] for kk, v in r.items() if kk.startswith(("A1_r", "A2", "A3")))
print(json.dumps(r))
