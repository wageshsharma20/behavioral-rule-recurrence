"""Re-filter KEPT mutants with the plain-key control. KEPT -> KEPT_SPECIFIC or DISCARDED_GENERIC.
Usage: python refilter_mutants.py <case_impl>"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__)); import run_mutants as RM
ROOT = RM.ROOT
def main(key):
    c = RM.CFG[key]; out = f"{ROOT}/rq3/mutants/{key}"; res = json.load(open(f"{out}/results.json"))
    orig = open(f"{out}/ORIGINAL.py").read(); cache = os.path.join(os.path.dirname(f"{ROOT}/{c['file']}"), "__pycache__")
    def control():
        p = RM.server(c); RM.wait(c["port"])
        env = dict(os.environ, XF_BACKEND=c["backend"], XF_S3=f"http://127.0.0.1:{c['port']}", GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT="false")
        try:
            o = subprocess.run([f"{ROOT}/envs/{c['env']}/bin/python", f"{ROOT}/rq3/control_oracle.py", c["client"]],
                               capture_output=True, text=True, timeout=180, env=env, cwd=ROOT).stdout
            return json.loads(o)
        except Exception as e:
            return {"pass": False, "obs": f"CRASH {type(e).__name__}"}
        finally:
            p.kill(); p.wait()
    try:
        open(f"{ROOT}/{c['file']}", "w").write(orig); shutil.rmtree(cache, ignore_errors=True)
        base = control(); print(key, "control on ORIGINAL:", base)
        assert base["pass"], "control must pass on the unmutated GOOD version"
        for m in res["mutants"]:
            if m["status"] not in ("KEPT", "KEPT_SPECIFIC", "DISCARDED_GENERIC"): continue
            open(f"{ROOT}/{c['file']}", "w").write(open(f"{out}/{m['id']}.py").read()); shutil.rmtree(cache, ignore_errors=True)
            r = control(); m["control"] = r; m["status"] = "KEPT_SPECIFIC" if r["pass"] else "DISCARDED_GENERIC"
            print(key, m["id"], m["status"], r["obs"])
    finally:
        open(f"{ROOT}/{c['file']}", "w").write(orig); shutil.rmtree(cache, ignore_errors=True)
    json.dump(res, open(f"{out}/results.json", "w"), indent=1)
if __name__ == "__main__":
    main(sys.argv[1])
