"""Audit of the frozen run's environments: for every release in the frame, the installed versions of the libraries
on the client's I/O path, and whether any was uploaded to PyPI later than the release date + 3 days.
Needs the environments (envs/<client>-<version>) and network access to pypi.org (read-only metadata).
Output: oracle/env_date_audit.json (versions, PyPI upload dates, per-environment verdict)."""
import json, os, subprocess, urllib.request, datetime as dt, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KEY = ["boto3", "botocore", "aiobotocore", "aiohttp", "smart-open", "google-auth", "google-cloud-storage", "numpy", "fsspec"]
frames = [l.strip() for f in ("oracle/frame_s3.txt", "oracle/frame_gcs.txt") for l in open(f) if l.strip()]
dates = json.load(open("oracle/frame_dates.json")); rel = {}
for k, lst in dates.items():
    for v, d in lst: rel[(k.split("|")[0], v)] = d
cache = {}
def uploaded(pkg, ver):
    if (pkg, ver) not in cache:
        try:
            d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{ver}/json", timeout=30))
            cache[(pkg, ver)] = min(u["upload_time_iso_8601"] for u in d["urls"])[:10] if d["urls"] else None
        except Exception: cache[(pkg, ver)] = None
    return cache[(pkg, ver)]
out = {}
for e in frames:
    cl, ver = e.split("-", 1); ver = {"bad": "2025.10.0", "good": "2025.12.0"}.get(ver, ver)
    fr = subprocess.run(f"VIRTUAL_ENV=envs/{e} uv pip freeze", shell=True, capture_output=True, text=True).stdout
    inst = dict(l.split("==", 1) for l in fr.splitlines() if "==" in l)
    rd = rel.get((cl, ver)); rec = {"release": ver, "release_date": rd, "versions": {k: inst.get(k) for k in KEY if inst.get(k)}}
    if rd and ver != "latest":
        lim = (dt.date.fromisoformat(rd) + dt.timedelta(days=3)).isoformat()
        rec["newer_than_release_plus_3d"] = {k: [v, uploaded(k, v)] for k, v in rec["versions"].items()
                                             if (uploaded(k, v) or "") > lim}
    out[e] = rec
json.dump(out, open("oracle/env_date_audit.json", "w"), indent=1)
by = collections.defaultdict(lambda: [0, 0])
for e, r in out.items():
    if "newer_than_release_plus_3d" in r: by[e.split("-")[0]][0] += 1; by[e.split("-")[0]][1] += bool(r["newer_than_release_plus_3d"])
for cl, (n, late) in by.items(): print(f"{cl:13s} {n:3d} environments checked, {late:2d} with a newer dependency")
