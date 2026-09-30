"""Provider-agnostic runner for RQ3 prompts. Keys are read from ~/.llm_keys/<provider> and never printed.
Usage: python run_models.py <provider>:<model> <prompts.jsonl> [--samples 5] [--limit N]
Providers: openai, gemini, anthropic (HTTPS APIs); ollama (local). Every call is cached by (model, prompt sha, T, k)
so re-runs are free and resumable. Output: rq3/runs/<model_slug>.jsonl (one line per call) with the plan hash."""
import json, os, sys, time, hashlib, urllib.request, urllib.error, re, argparse
KEYDIR = os.path.expanduser("~/.llm_keys")
PLAN = os.path.expanduser("./protocol/BEHAVIORAL_ABSTRACTION_PROTOCOL.md")
PLAN_HASH = hashlib.sha256(open(PLAN, "rb").read()).hexdigest()[:16]
def key(p):
    f = os.path.join(KEYDIR, p)
    if not os.path.exists(f): sys.exit(f"missing key file {f} (create with read -s; never paste in chat)")
    return open(f).read().strip()
def post(url, body, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    return json.load(urllib.request.urlopen(req, timeout=timeout))
def call(provider, model, prompt, temperature, seed):
    if provider == "openai":
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "seed": seed}
        r = post("https://api.openai.com/v1/chat/completions", body, {"Authorization": "Bearer " + key("openai")})
        return r["choices"][0]["message"]["content"], r.get("usage", {})
    if provider == "anthropic":
        body = {"model": model, "max_tokens": 1024, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]}
        r = post("https://api.anthropic.com/v1/messages", body, {"x-api-key": key("anthropic"), "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in r["content"]), r.get("usage", {})
    if provider == "gemini":
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature, "seed": seed}}
        r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", body, {"x-goog-api-key": key("gemini")})
        return "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"]), r.get("usageMetadata", {})
    if provider == "ollama":
        body = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": temperature, "seed": seed, "num_ctx": 8192}}
        r = post("http://127.0.0.1:11434/api/generate", body, {}, timeout=900)
        return r["response"], {"eval_count": r.get("eval_count")}
    sys.exit("unknown provider")
def parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if m:
        try:
            j = json.loads(m.group(0)); v = str(j.get("verdict", "")).upper()
            if v in ("DEFECT", "CORRECT"): return v, j.get("scenario", "")
        except Exception: pass
    t = (text or "").upper()
    if "DEFECT" in t and "CORRECT" not in t: return "DEFECT", ""
    if "CORRECT" in t and "DEFECT" not in t: return "CORRECT", ""
    return "UNPARSED", ""
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("model"); ap.add_argument("prompts")
    ap.add_argument("--samples", type=int, default=5); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); provider, model = a.model.split(":", 1)
    slug = re.sub(r"[^\w.-]", "_", a.model); os.makedirs("rq3/runs", exist_ok=True); out = f"rq3/runs/{slug}.jsonl"
    done = set()
    if os.path.exists(out):
        for l in open(out):
            d = json.loads(l); done.add((d["sha"], d["temperature"], d["k"]))
    rows = [json.loads(l) for l in open(a.prompts)][: a.limit or None]
    plan = [(r, 0.0, 0) for r in rows] + [(r, 0.7, k) for r in rows for k in range(1, a.samples + 1)]
    with open(out, "a") as f:
        for r, T, k in plan:
            if (r["sha"], T, k) in done: continue
            for attempt in range(6):
                try:
                    t0 = time.time(); text, usage = call(provider, model, r["prompt"], T, 1000 + k); break
                except urllib.error.HTTPError as e:
                    if e.code in (429, 500, 502, 503, 529): time.sleep(min(60, 2 ** attempt * 3)); continue
                    text, usage = f"HTTPError {e.code}", {}; break
                except Exception as e:
                    time.sleep(5); text, usage = f"ERROR {type(e).__name__}", {}
            v, sc = parse(text)
            f.write(json.dumps({"id": r["id"], "sha": r["sha"], "model": a.model, "temperature": T, "k": k,
                                "label": r["label"], "verdict": v, "scenario": sc, "raw": text, "usage": usage,
                                "latency_s": round(time.time() - t0, 2), "plan_hash": PLAN_HASH,
                                "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n"); f.flush()
            print(r["id"], T, k, v, "label", r["label"], flush=True)
if __name__ == "__main__":
    main()
