import base64, gzip, hashlib, json, os
L = os.path.expanduser("."); PLAN = os.path.expanduser("./protocol/BEHAVIORAL_ABSTRACTION_PROTOCOL.md")
prompts = open(f"{L}/rq3/prompts_all.jsonl", "rb").read(); plan = open(PLAN, "rb").read()
B = lambda b: base64.b64encode(gzip.compress(b, 9)).decode()
PLAN_HASH = hashlib.sha256(plan).hexdigest()[:16]; PROMPTS_SHA = hashlib.sha256(prompts).hexdigest()
md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s}
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s}
cells = [
md(f"""# RQ3 sensitivity run R1 — gpt-oss-20b, output budget 16,384 (frozen plan {PLAN_HASH}; amendment R1)
**Settings before Run All:** Accelerator = **GPU T4 x2**; Internet = **On** (needs a phone-verified Kaggle account).
Outputs go to `/kaggle/working/runs/*.jsonl` (+ `run_meta.json`). After the run: *Save Version* (Save & Run All)
or download `/kaggle/working/rq3_runs.zip`. If a session ends early, attach the previous version's output as an
input dataset and Run All again — finished calls are skipped (resume)."""),
code("""import os, subprocess, time, json, urllib.request, shutil
# fail fast with a clear message if the session lacks a GPU or internet (both need a phone-verified Kaggle account)
if shutil.which('nvidia-smi') is None: raise RuntimeError('NO_GPU: session has no GPU (phone-verify the Kaggle account / accelerator not granted)')
try: urllib.request.urlopen('https://ollama.com', timeout=15)
except Exception as e: raise RuntimeError(f'NO_INTERNET: {type(e).__name__} (enable internet; needs phone verification)')
print(subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv'], capture_output=True, text=True).stdout)
subprocess.run('apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y zstd pciutils >/dev/null 2>&1', shell=True)
r = subprocess.run('curl -fsSL https://ollama.com/install.sh | sh', shell=True, capture_output=True, text=True)
print(r.stdout[-400:], r.stderr[-400:])
env = dict(os.environ, OLLAMA_KEEP_ALIVE='24h', OLLAMA_NUM_PARALLEL='1', OLLAMA_HOST='127.0.0.1:11434')
srv = subprocess.Popen(['ollama', 'serve'], stdout=open('/kaggle/working/ollama.log','w'), stderr=subprocess.STDOUT, env=env)
for _ in range(120):
    try: print('ollama', json.load(urllib.request.urlopen('http://127.0.0.1:11434/api/version', timeout=2))); break
    except Exception: time.sleep(1)
"""),
code(f"""import base64, gzip, hashlib, json
PROMPTS_B64 = '{B(prompts)}'
PLAN_B64 = '{B(plan)}'
prompts_bytes = gzip.decompress(base64.b64decode(PROMPTS_B64)); plan_bytes = gzip.decompress(base64.b64decode(PLAN_B64))
assert hashlib.sha256(prompts_bytes).hexdigest() == '{PROMPTS_SHA}', 'prompt bundle corrupted'
PLAN_HASH = hashlib.sha256(plan_bytes).hexdigest()[:16]; assert PLAN_HASH == '{PLAN_HASH}'
ROWS = [json.loads(l) for l in prompts_bytes.decode().splitlines()]
for r in ROWS: assert hashlib.sha256(r['prompt'].encode()).hexdigest()[:12] == r['sha']
open('/kaggle/working/protocol.md','wb').write(plan_bytes)
print(len(ROWS), 'prompts; plan', PLAN_HASH)"""),
code("""import re, glob, shutil, time, os, json, urllib.request, subprocess
MODELS = ['gpt-oss:20b']          # R1 sensitivity rerun (amendment log R1)
FALLBACK = {}       # R1: no fallback; if gpt-oss cannot run, the run must fail
SAMPLES = 5; T_SAMPLE = 0.7; BUDGET_H = 11.3; T0 = time.time()
os.makedirs('/kaggle/working/runs', exist_ok=True)
for f in glob.glob('/kaggle/input/**/runs/*.jsonl', recursive=True):   # resume from a previous session
    dst = '/kaggle/working/runs/' + os.path.basename(f)
    if not os.path.exists(dst): shutil.copy(f, dst); print('resumed', dst)
def api(path, body=None, timeout=1800):
    req = urllib.request.Request('http://127.0.0.1:11434' + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))
def pull(model):
    r = subprocess.run(['ollama', 'pull', model], capture_output=True, text=True); print(model, 'pull rc', r.returncode, r.stderr[-300:])
    return r.returncode == 0
def digest(model):
    for m in api('/api/tags')['models']:
        if m['name'] == model or m['model'] == model: return m.get('digest'), m.get('details', {})
    return None, {}
def parse(text):
    m = re.search(r'\\{.*\\}', text or '', re.S)
    if m:
        try:
            j = json.loads(m.group(0)); v = str(j.get('verdict', '')).upper()
            if v in ('DEFECT', 'CORRECT'): return v, j.get('scenario', '')
        except Exception: pass
    t = (text or '').upper()
    if 'DEFECT' in t and 'CORRECT' not in t: return 'DEFECT', ''
    if 'CORRECT' in t and 'DEFECT' not in t: return 'CORRECT', ''
    return 'UNPARSED', ''
GPU = subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'], capture_output=True, text=True).stdout.strip()
OVER = api('/api/version')['version']
def run(model, phase):
    slug = re.sub(r'[^\\w.-]', '_', 'ollama:' + model) + '_R1_budget16k'; out = f'/kaggle/working/runs/{slug}.jsonl'
    done = set()
    if os.path.exists(out):
        for l in open(out): d = json.loads(l); done.add((d['sha'], d['temperature'], d['k']))
    dg, det = digest(model)
    plan = [(r, 0.0, 0) for r in ROWS] if phase == 0 else [(r, T_SAMPLE, k) for k in range(1, SAMPLES + 1) for r in ROWS]
    todo = [(r, T, k) for r, T, k in plan if (r['sha'], T, k) not in done]; print(model, 'phase', phase, 'todo', len(todo))
    with open(out, 'a') as f:
        for i, (r, T, k) in enumerate(todo):
            if (time.time() - T0) / 3600 > BUDGET_H: print('time budget reached; stopping (resume next session)'); return False
            t1 = time.time()
            try:
                resp = api('/api/generate', {'model': model, 'prompt': r['prompt'], 'stream': False,
                                             'options': {'temperature': T, 'seed': 1000 + k, 'num_ctx': 24576, 'num_predict': 16384}})
                text = resp.get('response', ''); thinking = resp.get('thinking', '')
                usage = {x: resp.get(x) for x in ('prompt_eval_count', 'eval_count', 'total_duration')}
            except Exception as e:
                text, thinking, usage = f'ERROR {type(e).__name__}: {str(e)[:200]}', '', {}
            v, sc = parse(text)
            f.write(json.dumps({'id': r['id'], 'sha': r['sha'], 'model': 'ollama:' + model, 'temperature': T, 'k': k,
                                'label': r['label'], 'verdict': v, 'scenario': sc, 'raw': text, 'thinking': thinking[:20000],
                                'usage': usage, 'latency_s': round(time.time() - t1, 2), 'plan_hash': PLAN_HASH,
                                'ollama_version': OVER, 'model_digest': dg, 'model_details': det, 'gpu': GPU, 'run_config': 'R1: num_predict=16384, num_ctx=24576, T=0 only',
                                'ts': time.strftime('%Y-%m-%dT%H:%M:%S')}) + '\\n'); f.flush()
            if i % 10 == 0: print(model, phase, i, '/', len(todo), r['id'], v, 'label', r['label'], f'{time.time()-t1:.1f}s', flush=True)
    return True
ACTIVE = []
for m in MODELS:
    if pull(m): ACTIVE.append(m)
    elif m in FALLBACK and pull(FALLBACK[m]): ACTIVE.append(FALLBACK[m]); print('USING FALLBACK', FALLBACK[m], 'for', m)
json.dump({'plan_hash': PLAN_HASH, 'models': ACTIVE, 'digests': {m: digest(m)[0] for m in ACTIVE}, 'ollama': OVER, 'gpu': GPU},
          open('/kaggle/working/run_meta.json', 'w'), indent=1)
print('ACTIVE', ACTIVE)"""),
code("""# Phase 0: every model at T=0 (primary analysis) -- runs first so the primary results are complete early
for m in ACTIVE: run(m, 0)"""),
code("""# R1: no sampling phase (amendment log R1)
subprocess.run('cd /kaggle/working && zip -qr rq3_runs.zip runs run_meta.json protocol.md ollama.log', shell=True)
for f in glob.glob('/kaggle/working/runs/*.jsonl'):
    n = sum(1 for _ in open(f)); print(os.path.basename(f), n, 'calls')"""),
]
for i, c in enumerate(cells): c["id"] = f"cell-{i}"
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open(f"{L}/rq3/kaggle/rq3_kaggle_R1.ipynb", "w"))
print("notebook written; plan", PLAN_HASH, "prompts sha", PROMPTS_SHA[:16], "size KB", os.path.getsize(f"{L}/rq3/kaggle/rq3_kaggle_R1.ipynb") // 1024)
