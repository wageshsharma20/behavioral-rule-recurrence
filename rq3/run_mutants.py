"""Run rule-blind mutants against the oracle battery; keep those killed ONLY by the case's rule probes.
Usage: python run_mutants.py <case_impl> ; config below. Writes rq3/mutants/<case_impl>/results.json"""
import ast, json, os, re, shutil, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = {
 "GC1_s3fs": dict(env="s3fs-attr1005", file="envs/s3fs-attr1005/lib/python3.12/site-packages/s3fs/core.py",
      funcs="S3FileSystem.split_path", backend="s3", port=5561, client="s3fs", oracles=["f2", "xfam"],
      family=lambda k: k.startswith("f2:") and k.endswith(":A_nothing_under_d")),
 "GC2a_s3path": dict(env="s3path-attr78", file="envs/s3path-attr78/lib/python3.9/site-packages/s3path.py",
      funcs="_S3Accessor.open", backend="s3", port=5562, client="s3path", oracles=["xfam"],
      family=lambda k: k.startswith(("xfam:F3_", "xfam:F3b_"))),
 "GC3_cloudpathlib": dict(env="cloudpathlib-attr244", file="envs/cloudpathlib-attr244/lib/python3.10/site-packages/cloudpathlib/s3/s3client.py",
      funcs="S3Client._s3_file_query", backend="s3", port=5563, client="cloudpathlib", oracles=["xfam"],
      family=lambda k: k.startswith(("xfam:F1_stat_string_prefix", "xfam:F1_info_prefix_notfound"))),
 "GC2a_gcsfs": dict(env="gcsfs-attr502", file="envs/gcsfs-attr502/lib/python3.10/site-packages/gcsfs/core.py",
      funcs="GCSFile.discard,GCSFileSystem._format_path,GCSFileSystem._rm_files,GCSFileSystem.url,initiate_upload,quote,quote_plus,simple_upload",
      backend="gcs", port=4443, client="gcsfs", oracles=["xfam"], timeout=180,
      family=lambda k: k.startswith(("xfam:F3_", "xfam:F3b_"))),
}
def server(c):
    if c["backend"] == "gcs":
        subprocess.run(f"lsof -ti:{c['port']} | xargs kill 2>/dev/null", shell=True)
        env = dict(os.environ, TZ="UTC")
        return subprocess.Popen([f"{ROOT}/tools/fgs-1.56.1/fake-gcs-server", "-scheme", "http", "-port", str(c["port"]),
            "-public-host", f"localhost:{c['port']}", "-external-url", f"http://localhost:{c['port']}", "-backend", "memory"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    subprocess.run(f"lsof -ti:{c['port']} | xargs kill 2>/dev/null", shell=True)
    return subprocess.Popen([f"{ROOT}/envs/s3fs-bad/bin/moto_server", "-p", str(c["port"])],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def wait(port):
    import socket
    for _ in range(80):
        try: socket.create_connection(("127.0.0.1", port), 0.5).close(); return
        except OSError: time.sleep(0.25)
def run_battery(c):
    res = {}
    for o in c["oracles"]:
        p = server(c); wait(c["port"])
        env = dict(os.environ, XF_BACKEND=c["backend"], XF_S3=f"http://127.0.0.1:{c['port']}",
                   GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT="false")
        script = {"f2": "oracle/f2_delete_oracle.py", "xfam": "oracle/xfam_oracle.py"}[o]
        try:
            out = subprocess.run([f"{ROOT}/envs/{c['env']}/bin/python", f"{ROOT}/{script}", c["client"]],
                                 capture_output=True, text=True, timeout=c.get("timeout", 900), env=env, cwd=ROOT).stdout
            r = json.loads(out)
            if o == "f2":
                for v, x in r["variants"].items():
                    for a in ("A_nothing_under_d", "B_sibling_prefix_survives"): res[f"f2:{v}:{a}"] = x[a]
            else:
                for k, x in r["probes"].items():
                    if x["pass"] is not None: res[f"xfam:{k}"] = x["pass"]
        except Exception as e:
            res[f"{o}:__CRASH__"] = False
        finally:
            p.kill(); p.wait()
    return res
def main(key):
    c = CFG[key]; out = f"{ROOT}/rq3/mutants/{key}"; os.makedirs(out, exist_ok=True)
    orig = open(f"{ROOT}/{c['file']}").read(); bak = f"{out}/ORIGINAL.py"; open(bak, "w").write(orig)
    unp = ast.unparse(ast.parse(orig))           # baseline on the UNPARSED original (same printer as mutants)
    open(f"{ROOT}/{c['file']}", "w").write(unp)
    base = run_battery(c); open(f"{ROOT}/{c['file']}", "w").write(orig)
    subprocess.run([sys.executable, f"{ROOT}/rq3/mutate.py", bak, c["funcs"], out, "30"], check=True)
    idx = json.load(open(f"{out}/index.json")); results = {"baseline": base, "mutants": []}
    prev = f"{out}/results.json"
    if os.path.exists(prev):                       # resume: keep finished mutants, same deterministic mutant set
        old = json.load(open(prev)); results["mutants"] = old.get("mutants", [])
    finished = {m["id"] for m in results["mutants"]}
    try:
        for m in idx["mutants"]:
            if m["id"] in finished: continue
            open(f"{ROOT}/{c['file']}", "w").write(open(f"{out}/{m['id']}.py").read())
            for pc in [os.path.join(os.path.dirname(f"{ROOT}/{c['file']}"), "__pycache__")]:
                shutil.rmtree(pc, ignore_errors=True)
            r = run_battery(c)
            newly_failed = sorted(k for k, v in base.items() if v and r.get(k) is False)
            fam = [k for k in newly_failed if c["family"](k)]; other = [k for k in newly_failed if not c["family"](k)]
            crash = any(k.endswith("__CRASH__") for k in r)
            status = "KEPT" if fam and not other and not crash else ("SURVIVED" if not newly_failed and not crash else "DISCARDED")
            results["mutants"].append({**m, "status": status, "family_failed": fam, "other_failed": other, "crash": crash})
            print(key, m["id"], status, len(fam), len(other), flush=True)
            json.dump(results, open(f"{out}/results.json", "w"), indent=1)
    finally:
        open(f"{ROOT}/{c['file']}", "w").write(orig)     # ALWAYS restore
    from collections import Counter
    print(key, "DONE", Counter(x["status"] for x in results["mutants"]))
if __name__ == "__main__":
    main(sys.argv[1])
