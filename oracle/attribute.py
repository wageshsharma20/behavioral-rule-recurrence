"""Commit-level attribution: for each fix, install parent and fix commit into one environment with every other
dependency held fixed, run the case's discriminating assertion, record both verdicts.
Expected: parent -> False (violates), fix -> True (satisfies). Output: oracle/attribution_results.json"""
import json, os, subprocess, sys, time, socket
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S3P, GCSP = 5590, 4460
SPECS = [
 {"case": "GC1", "impl": "s3fs", "repo": "fsspec/s3fs", "fix": "5e5f7ea", "py": "3.12",
  "held": ["fsspec==2026.1.0", "aiobotocore>=2.19,<4", "boto3", "aiohttp>=3.9"], "exclude_newer": None, "pkg": "s3fs",
  "backend": "s3", "oracle": "f2_delete_oracle.py", "client": "s3fs", "assert": "v-nested:A_nothing_under_d"},
 {"case": "GC2a", "impl": "s3path", "repo": "liormizr/s3path", "fix": "643c25b", "py": "/usr/bin/python3",
  "held": ["s3path==0.3.1", "boto3"], "exclude_newer": "2021-06-25", "pkg": "s3path",
  "backend": "s3", "oracle": "xfam_oracle.py", "client": "s3path", "assert": "F3_write_key_exact[café]"},
 {"case": "GC2a", "impl": "gcsfs", "repo": "fsspec/gcsfs", "fix": "56281f4", "py": "3.10",
  "held": ["gcsfs==2022.8.2"], "exclude_newer": "2022-09-05", "pkg": "gcsfs",
  "backend": "gcs", "oracle": "xfam_oracle.py", "client": "gcsfs", "assert": "F3_read[hash#]"},
 {"case": "GC3", "impl": "cloudpathlib", "repo": "drivendataorg/cloudpathlib", "fix": "e781f1fa2", "py": "3.10",
  "held": ["cloudpathlib[s3]==0.9.0", "boto3"], "exclude_newer": "2022-08-12", "pkg": "cloudpathlib",
  "backend": "s3", "oracle": "xfam_oracle.py", "client": "cloudpathlib", "assert": "F1_stat_string_prefix_notfound[very/similar/prefix]"},
 {"case": "PV1-source", "impl": "gcsfs", "repo": "fsspec/gcsfs", "fix": "5b97087", "py": "3.10",
  "held": ["gcsfs==2023.6.0"], "exclude_newer": "2023-06-15", "pkg": "gcsfs",
  "backend": "gcs", "oracle": "xfam2_oracle.py", "client": "gcsfs", "assert": "F15b_move_dir_sibling_untouched[implicit]"},
]
def sh(cmd, **kw): return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
def gh_parent(repo, sha):
    import urllib.request
    tokf = os.path.expanduser(os.environ.get("GH_TOKEN_FILE", "~/.gh_token")); H = {"User-Agent": "attr"}
    if os.path.exists(tokf): H["Authorization"] = "Bearer " + open(tokf).read().strip()
    d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{repo}/commits/{sha}", headers=H), timeout=60))
    return d["sha"], d["parents"][0]["sha"]
def server(backend):
    port = S3P if backend == "s3" else GCSP; sh(f"lsof -ti:{port} | xargs kill 2>/dev/null")
    if backend == "s3": p = subprocess.Popen([f"{ROOT}/envs/s3fs-bad/bin/moto_server", "-p", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else: p = subprocess.Popen([f"{ROOT}/tools/fgs-1.56.1/fake-gcs-server", "-scheme", "http", "-port", str(port), "-public-host", f"localhost:{port}",
                                "-external-url", f"http://localhost:{port}", "-backend", "memory"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ, TZ="UTC"))
    for _ in range(80):
        try: socket.create_connection(("127.0.0.1", port), 0.5).close(); break
        except OSError: time.sleep(0.25)
    return p
def verdict(env, s):
    p = server(s["backend"])
    try:
        e = dict(os.environ, XF_BACKEND=s["backend"], XF_S3=f"http://127.0.0.1:{S3P}", XF_GCS=f"http://localhost:{GCSP}", GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT="false")
        out = subprocess.run([f"{env}/bin/python", f"{ROOT}/oracle/{s['oracle']}", s["client"]], capture_output=True, text=True, env=e, timeout=1200).stdout
        r = json.loads(out)
        if "variants" in r: v, a = s["assert"].split(":"); return r["variants"][v][a]
        return r["probes"][s["assert"]]["pass"]
    finally:
        p.kill(); p.wait()
res = []
for s in SPECS:
    fix, parent = gh_parent(s["repo"], s["fix"]); env = f"{ROOT}/envs/attr-{s['case']}-{s['impl']}"
    sh(f"rm -rf {env}"); sh(f"uv venv -q -p {s['py']} {env}")
    ex = f"--exclude-newer {s['exclude_newer']}T00:00:00Z" if s["exclude_newer"] else ""
    r = sh(f"VIRTUAL_ENV={env} uv pip install -q {ex} " + " ".join(f"'{x}'" for x in s["held"]))
    row = {**{k: s[k] for k in ("case", "impl", "repo", "assert")}, "fix": fix, "parent": parent, "held": s["held"], "exclude_newer": s["exclude_newer"]}
    for tag, sha in (("parent", parent), ("fix", fix)):
        sh(f"VIRTUAL_ENV={env} uv pip install -q --no-deps --reinstall '{s['pkg']} @ git+https://github.com/{s['repo']}@{sha}'")
        row[tag] = verdict(env, s)
    row["held_versions"] = sh(f"{env}/bin/python -m pip list --format=freeze 2>/dev/null || VIRTUAL_ENV={env} uv pip freeze").stdout.strip().splitlines()[:60]
    row["attributed"] = row["parent"] is False and row["fix"] is True
    res.append(row); print(s["case"], s["impl"], "parent:", row["parent"], "fix:", row["fix"], "ATTRIBUTED" if row["attributed"] else "NOT ATTRIBUTED", flush=True)
    json.dump(res, open(f"{ROOT}/oracle/attribution_results.json", "w"), indent=1)
