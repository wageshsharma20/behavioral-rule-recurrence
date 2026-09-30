"""All paper numbers for RQ1/RQ2 from the frozen run (oracle/results_v1) ONLY."""
import json, glob, re, collections, os
R = "oracle/results_v1"
def vkey(v):
    v = {"bad": "2025.10.0", "good": "2025.12.0", "latest": "9999"}.get(v, v)
    try: return tuple(int(x) for x in v.split("."))
    except ValueError: return (0,)
series = collections.defaultdict(dict); releases = collections.defaultdict(set); execs = 0
for d in sorted(glob.glob(f"{R}/*__*")):
    orc, be = os.path.basename(d).split("__")
    for f in glob.glob(f"{d}/*.json"):
        env = os.path.basename(f)[:-5]; cl, ver = env.split("-", 1); r = json.load(open(f))
        if cl == "s3fs" and ver in ("bad", "good"): ver = {"bad": "2025.10.0", "good": "2025.12.0"}[ver]
        if ver == "latest":
            ver = r.get("version", "9999")
        releases[(cl, be)].add(ver)
        if orc == "f2":
            for v, x in r["variants"].items():
                for a in ("A_nothing_under_d", "B_sibling_prefix_survives"):
                    series[(cl, be, f"f2:{v}:{a}")][ver] = x[a]; execs += 1
        else:
            for k, p in r["probes"].items():
                if p["pass"] is not None: series[(cl, be, f"{orc}:{k}")][ver] = p["pass"]; execs += 1
nrel = sum(len(v) for v in releases.values())
print("client/backend pairs:", len(releases), " releases:", nrel, " probe executions (non-n/a):", execs)
for k in sorted(releases): print(f"   {k[0]:13s} {k[1]:4s} {len(releases[k]):3d} releases  {min(releases[k], key=vkey)} .. {max(releases[k], key=vkey)}")
trans = []
for key, vs in series.items():
    o = sorted(vs, key=vkey)
    for a, b in zip(o, o[1:]):
        if vs[a] != vs[b]: trans.append((key, a, b, "F->P" if vs[b] else "P->F"))
print("probe series:", len(series), " transitions:", collections.Counter(t[3] for t in trans))
ev = collections.defaultdict(list)
for (cl, be, k), a, b, d in trans: ev[(cl, be, a, b, d)].append(k)
print("distinct fix/regression events (client,backend,window,direction):", len(ev),
      "  F->P:", sum(1 for e in ev if e[4] == "F->P"), " P->F:", sum(1 for e in ev if e[4] == "P->F"))
for e, ks in sorted(ev.items()): print("  ", e, len(ks), ks[:2])
json.dump({"releases": nrel, "pairs": len(releases), "executions": execs, "series": len(series),
           "transitions": len(trans), "events": [list(e) + [ks] for e, ks in ev.items()]},
          open("oracle/frozen_stats.json", "w"), indent=1)
