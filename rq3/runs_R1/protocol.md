# Learning Behavioral Abstractions from Historical Software Evolution
**Protocol v3 — 29 Sep 2026. Target: FSE 2027 research track (due Fri 2 Oct 2026 AoE; 18 pp + 4 refs, acmsmall,
double-anonymous, Data Availability section required). v2 archived as BEHAVIORAL_ABSTRACTION_PROTOCOL_v2_archive.md.**
Rule for this document: it describes ONLY what was executed or is fixed before execution. Nothing aspirational.

## Research question
Does historical engineering evidence enable a model to recover implementation-independent
behavioral knowledge, rather than rely on implementation-specific cues?

## Notation
- H = historical evidence; P = implementation; z = f(H) latent behavioral abstraction (not measured)
- y(P) ∈ {0,1} behavioral oracle (executable test); ŷ(H,P) ∈ {0,1} model prediction
- Δcross = Acc_same − Acc_cross, both accuracies of ŷ against y (use balanced accuracy if classes skew)
- P1 ~B P2 ⇒ g(P1) ≈ g(P2) is MOTIVATION ONLY — not measured; no representation probing in v1

## Case categories (v3, strict — used in the paper)
- GOLDEN: one executable assertion discriminates BAD->GOOD (a natural historical flip) in >=2 lineage-independent
  implementations, with rationale in at least one of them. (4 cases: GC1, GC2a, GC2b, GC3 — all with
  cross-language evidence.)
- PROSPECTIVE: a rule recovered from >=1 implementation's history is transferred, by executing its oracle, to an
  implementation that has NO history for it, and exposes a live violation in the latest release. Not a Golden Case.
  (PV1: segment-boundary rule from cloudpathlib #208 / gcsfs #576 / OpenDAL -> s3path 0.6.5 rmdir/rename.)
- SHARED-ORIGIN: same rule, but the code path was ported (fails lineage check) — motivating only. (SO1: R2.)
- CONTESTED: implementations change in OPPOSITE directions — negative control. (CT1: listing excludes own marker.)
- SINGLE-IMPL: a flip in one implementation with no partner — reported in the funnel only.

## Golden Case (historical definition, kept for provenance)
Historical rationale + regression/correction + executable oracle + ≥2 independent implementations.
Elements may come from different artifacts. The fix need not add a test (shared suite or an authored
discriminating test may serve as oracle). Rationale measured AFTER stripping PR-template boilerplate.

## Stage 9 (the bottleneck — report funnel stages separately)
The same behavioral rule, with evidence in ≥2 INDEPENDENT implementations.
**Independent** requires ALL of:
1. not a fork / derived / copied implementation (e.g. redis→valkey is NOT independent)
2. not a thin wrapper around another counted implementation — tracked GLOBALLY across ecosystems
   (fsspec HadoopFileSystem wraps pyarrow HDFS; pyarrow HDFS calls Hadoop's Java client via
   libhdfs; pyarrow FSSpecHandler wraps fsspec)
3. the rule's code path is written in the backend itself, NOT inherited from a shared base class
   (e.g. fsspec AbstractFileSystem glob/walk/find/copy do not count)
4. the behavior is decided by the backend's code, NOT by a remote service it passes through
5. (v2) CODE-PATH LINEAGE: the rule's code path in B was not ported from A. Checked by (a) git origin of
   the path (`git log -S`/blame on the key identifiers), (b) same author within a short window, (c) textual
   similarity at origin, (d) telltale literals. Example that FAILS: gcsfs find()->dircache (b6368a2,
   2020-09-25) ported by the same author 3 days after s3fs bdfb5b9, keeping the S3-only literal
   "StorageClass": "DIRECTORY". Cross-LANGUAGE pairs pass (a)-(d) by construction.
Wording (v3): GOLDEN requires a natural BAD->GOOD flip in EVERY counted implementation. A live violation
without a flip makes the case PROSPECTIVE, never GOLDEN (v2's looser wording is withdrawn).
Metadata per case: implementation_A, implementation_B, lineage, base_class_or_override,
relevant_code_path, remote_determined, independence_status. Only independence_status=true is primary.

## Constructed cases (v3)
- Rule-BLIND mutation of GOOD code (operators: drop call, delete/flip condition, remove string concat of '/',
  swap argument) applied to the functions in the extracted code set; Python targets only (C++/Rust rebuild
  infeasible in the time frame — limitation).
- Keep a mutant as BAD only if it fails the case's discriminating assertion AND passes every other probe of the
  oracle battery (xfam/xfam2/f2 probes) — documented deviation from 'the full upstream test suite'.
- Report operator mix after filtering; natural and constructed items reported as separate strata.
- Amendment (29 Sep, BEFORE any model call): a kept mutant must ALSO pass a plain-key control (rq3/control_oracle.py:
  ordinary write/read/list/info). Reason: all 16 initially kept s3path mutants broke open() generically
  (NameError/TypeError) and would have counted as rule violations. The control is a separate file; the frozen
  screening battery is unchanged.

## Hypotheses (v3; H1/H2 of v1 withdrawn — they presupposed a trained model with same/cross code exposure)
- H3 (PRIMARY): BalAcc(B3: code + cross-implementation history) > BalAcc(B1: code only).
- S1: BalAcc(B3) > BalAcc(B4: code + mismatched history)  — gain comes from rule content, not context length.
- S2: B2 (history only) = 0.5 analytically (identical inputs across a pair) — reported, not run.
- S3: Δcross = BalAcc(B5: own-implementation history) − BalAcc(B3) — descriptive.
Analysis: see 'RQ3 analysis plan'.

## Conditions (v3) = B1–B5 as defined in 'RQ3 analysis plan'
Lexical control: report token overlap between history and target code per item; B4 histories matched on
length and ecosystem.

## Ecosystem selection
Filters (all required): independent implementations · accessible rationale/history · oracle runnable
locally or via reproducible testbench · behavior implemented in backend code (filter 4 above).
Academic precedent = tie-breaker only.
Considered and NOT used (v3): Hadoop FileSystem (normative spec => leakage; JVM cost), Apache Libcloud, Keyv
(Stage-9 yield 0, see record), fsspec alone (backends share Durant-authored lineage). Used: see sampling frames.

## Sampling frames actually used (v3; replaces v1/v2 '100 random fix events', which was NOT executed)
- Implementation frame: filesystem-style client libraries for object stores that (i) expose directory/key
  semantics through a public API, (ii) have >=2 years of installable releases, (iii) have a public tracker,
  (iv) are lineage-independent of each other (checked). Result: s3fs, gcsfs (Python, fsspec), pyarrow.fs (C++),
  object_store/obstore (Rust), OpenDAL (Rust), cloudpathlib (Python), s3path (Python).
- Probe frame: every probe is derived from a historical issue/PR/test (traceability table in the paper); probes are
  purposive, not random -> RQ1 claims EXISTENCE and CHARACTERISTICS of recurrence, NOT prevalence.
- Release frame: a spread of releases per client (97 distinct releases), densified by bisection around flips.
- Stopping: all probes run on all installable releases in the frame; no result-dependent pruning.
Prevalence estimation from a random sample of fix events is out of scope for this paper (stated as a limitation).

## Keyv status (record)
Rationale+fix funnel: 1,969 pre-2026 commits → 131 fixes → 64 single-adapter fixes with PR →
9 ≥40 real words → 3 ≥80 → 1 ≥150 (PR #881). #881 fails stage 9: its rule (namespace set consistent
with stored keys) exists only in Redis-lineage adapters (valkey 38 refs; redis now 0; SQL/mongo/etcd/
dynamo/memcache 0); fix uses Redis MULTI/EXEC. "0 natural stage-9 cases identified so far."

## Mining method (v2): cross-implementation historical differential screening
1. Backend held FIXED (moto 5.2.3 for S3; fake-gcs-server for GCS; TZ=UTC). World built through the RAW
   storage API; verification of side effects through the RAW API (a client never grades itself).
2. Probes = executable assertions derived from histories (each probe cites the issue/PR it came from).
   Adapters call only the client's NATIVE public API; a probe needing a concept the client lacks is n/a.
3. Run every probe on a spread of releases of every client, era-matched dependencies
   (uv --exclude-newer = release date + 3 d), era-correct interpreter (e.g. s3path 0.3.x needs py<=3.9;
   pyarrow <5 has no arm64 wheels -> x86_64 CPython under Rosetta).
4. A BAD->GOOD flip marks a fix event: bisect releases -> fix commit -> rationale -> attribution
   (commit-level: install fix^ and fix with all other deps held; else release-level + diff inspection).
5. A Golden Case = the SAME assertion discriminates BAD->GOOD in >=2 lineage-independent implementations.
Clients (S3): s3fs (Py), pyarrow.fs (C++), object_store/obstore (Rust), OpenDAL (Rust), cloudpathlib (Py),
s3path (Py). GCS: gcsfs. Emulator choice matters: Arrow GH-38618 reproduces on moto, not on MinIO.

## Threats to validity (running list)
emulator-only (no real AWS/GCS; moto chosen for AWS fidelity, record per case) · attribution granularity
(commit vs release) · rule granularity (single assertion vs family) · probe design by the authors (mitigate:
every probe traceable to a historical test/issue; pre-register the probe set) · era-matching of deps ·
public histories => LLM memorisation (mitigate: temporal holdout, constructed cases, renaming) ·
AI-authored metadata (pre-2026 cutoff for history; scan trailers) · small N (report per-rule, mixed model).

## RQ3 analysis plan (fixed BEFORE any model run; commit this file's hash into the run log)
Task: binary judgement. Input = target implementation code for one operation at one version; output =
{"verdict": "DEFECT"|"CORRECT", "scenario": str}. Label = oracle outcome (BAD -> DEFECT, GOOD -> CORRECT).
Code shown: the functions changed by the fix, plus their direct in-package callers on the operation's path,
extracted at BOTH versions (identical function set -> no version-specific localisation signal).
Conditions: B1 code + operation name only · B2 history only (no code; negative control, expected chance) ·
B3 code + history of the SAME rule from a DIFFERENT implementation (cross) · B4 code + mismatched history
(different rule, similar length/ecosystem) · B5 code + history from the SAME implementation's own fix (same;
upper reference for Δcross).
Items: natural BAD/GOOD pairs for each implementation of each Golden Case; constructed rule-blind mutants of GOOD
code for Python targets (kept only if they fail the case's discriminating assertion and pass every other probe
in the oracle battery — documented deviation from 'full test suite').
Models (amendment 29 Sep, before any call): open-weight models run locally with Ollama on Kaggle (2x NVIDIA T4):
  M1 qwen3-coder:30b (Qwen3-Coder-30B-A3B-Instruct, released 2025-07-31; Ollama default 4-bit quantisation),
  M2 gpt-oss:20b (OpenAI open-weight, released 2025-08-05; stated knowledge cutoff 2024-06; default reasoning).
  Fallback if a tag cannot run on T4: qwen2.5-coder:32b (released 2024-11). The exact Ollama version and model
  digests are logged. Optional: one frontier API model, same prompts, reported separately.
Decoding: T=0 (seed 1000) = primary; then k=5 samples at T=0.7 (seeds 1001-1005). Order: all models at T=0 first.
num_ctx 12288; num_predict 4096 (reasoning output).
History inputs (amendment): only issue/PR/comment content created before 2026-01-01 is shown to models (human-authored
era). Consequences: obstore GC2b history (#671/#672, 2026) is unavailable; s3fs GC1 history is the 2024 part of #918.
Temporal holdout per model = target items whose fix was merged after the model's release date (M1, M2) or stated
cutoff (M2: 2024-06): s3fs GC1 (2026-02), obstore GC2a (2025-08), obstore GC2b (2026-04); for M2 also OpenDAL GC3 (2024-08).
Item counts: 64 natural (14 with a cross-history B3), 8 prospective (PV1), 6 constructed (cloudpathlib only; all
s3path/gcsfs/s3fs candidates failed the specificity filters).
Primary test (H3): balanced accuracy B3 > B1 on cross items; paired by item; reported per rule and pooled with a
mixed-effects logistic model (item nested in rule; rule as random effect); rule-level bootstrap CIs.
Secondary: B3 > B4 (content, not length); Δcross = B5 − B3.
B2 amendment (29 Sep, before any run): B2 inputs are byte-identical for the BAD and GOOD item of a pair, so at T=0
BalAcc(B2)=0.5 analytically; B2 is reported analytically and NOT run. Bias-from-extra-context is controlled by B4.
Framing: B3/B4/B5 use the SAME neutral preamble ("an issue/pull-request discussion from an object-storage
filesystem library's tracker; it may or may not be relevant") — no cue whether it is same/different/relevant.
Cross-source rule: the history source for target T is the earliest-dated OTHER implementation of the same case
that has rationale text. OpenDAL #4959 has no rationale for the rule -> never a source; cloudpathlib (GC3) has
no cross source -> its items enter B1/B4/B5 only.
Mismatched source (B4): the history from a DIFFERENT case whose word count is closest to the B3 history.
Code shown is comment- and docstring-stripped (the Arrow fix added an explanatory comment -> leakage).
Temporal-holdout subset: items whose target fix post-dates the model's stated training cutoff.
Small N (4 rules) is reported as a limitation; no population-level claims.

## Open (29 Sep 2026)
- model access (user) · s3path upstream report approval (user) · professor sign-off (user)
- build RQ3 materials; run; analyse; write
