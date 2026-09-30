# Replication package (to be anonymized before upload)

## Quick start
`./reproduce.sh GC3` rebuilds one Golden Case from a clean checkout: it creates the environments of the case's last
violating and first satisfying releases from `oracle/env_locks/` (one lock file per environment of the study, with the
Python version and architecture), starts a fresh emulator, and runs the discriminating assertion. Use `GC1`, `GC2a`,
`GC2b`, `PV1` or `all` for the other cases. Needs only `uv`; fake-gcs-server is fetched on demand for GCS rows.

## Evidence summaries
- `evidence/CANDIDATE_RULES.md` (`oracle/candidate_funnel.py`): per probe family, the assertions, series, flips and event
  classifications of the frozen run, and every candidate recurrence examined by hand with its outcome.
- `evidence/s3path_existing_report_search.json`: the search behind "we found no existing report" for the s3path defect
  (all 209 issues and pull requests, keyword matches, and the assessment of the closest match).

## Layout
- `oracle/` — executable oracles. Screening battery frozen by hash: `oracle/FROZEN_v1.sha256`
  (`xfam_oracle.py`, `xfam2_oracle.py`, `f2_delete_oracle.py`, `c1_oracle.py`). `r2_oracle.py` (shared-origin case),
  `pv1_oracle.py` (prospective case) are separate and not part of the screening battery.
- `oracle/frame_s3.txt`, `oracle/frame_gcs.txt` — the release frame; `oracle/frame_EXCLUDED.txt` — exclusions + reasons.
- `oracle/run_frozen.sh s3|gcs` — full-frame screening run (verifies the freeze hash first) -> `oracle/results_v1/`.
- `oracle/verify_golden.sh` — re-verifies each Golden Case's discriminating assertion on its BAD/GOOD releases.
- `oracle/mk_s3env.sh` — era-matched environments (`uv --exclude-newer <release date + 3 d>`).
- `dataset/cases.jsonl` — Golden / shared-origin / contested / prospective cases with provenance and attribution.
- `CANDIDATES.md` — working evidence log (bisections, attribution runs, lineage checks), chronological; superseded
  hypotheses are kept. Authoritative: the paper, `dataset/cases.jsonl`, `oracle/event_classification.json`.
- `rq3/` — LLM study: `fixes.json`, `fetch_fixes.py`, `extract.py`, `strip.py` (comment/docstring removal),
  `fetch_histories.py` + `histories/`, `build_prompts.py` -> `prompts_natural.jsonl`, `prompts_prospective.jsonl`,
  `mutate.py`, `run_mutants.py`, `control_oracle.py`, `refilter_mutants.py`, `run_models.py`, `analyze.py`.
- `rq3/pv1_fix.patch` — oracle-verified fix for the prospective s3path defect. `oracle/run_pv1.sh` -> `oracle/pv1_results.json`
  runs `oracle/pv1_oracle.py` on s3path 0.6.5, released and patched, on both code paths (Python 3.10 and 3.12), each with
  a fresh emulator; `rq3/pv1_patched_xfam*.json` — the frozen battery on the patched release (only four directory-move
  probes change, from fail to pass).

## Environment
macOS arm64; Python via uv; moto 5.2.3 (S3); fake-gcs-server 1.56.1 with `TZ=UTC` (GCS);
`GCSFS_EXPERIMENTAL_ZB_HNS_SUPPORT=false`. pyarrow < 5 runs as x86-64 CPython 3.9 under Rosetta.
s3path 0.3.x requires CPython <= 3.9.

## Frozen analysis plan
`BEHAVIORAL_ABSTRACTION_PROTOCOL.md` (v3). Its SHA-256 prefix is written into every model-call record (`plan_hash`).

## Results in this package
- `oracle/results_v1/` — the frozen full-frame screening run (all RQ1/RQ2 numbers); `oracle/frozen_stats.py` recomputes them.
  Environment names `s3fs-bad` and `s3fs-good` hold s3fs releases 2025.10.0 and 2025.12.0 (names from an early bisection;
  the `version` field inside each result file is authoritative).
- `oracle/classify_events.py` -> `oracle/event_classification.json` — classification of all 26 events (Table 5), with the
  exception types seen on each event's failing side. s3path 0.3.0 is not evaluable: every read/write raises
  NoCredentialsError because it passes its configuration to smart_open 5.0.0 through an interface that release no longer
  accepts; its one event (two '~' probes, 0.3.0 -> 0.3.1) is classified as a failure unrelated to the probes' rule.
- `paper/tools/gen_timeline.py` — regenerates Figure 2 (`paper/fig_timeline.tex`) from the frozen run.
- Dependency-era audit and check (post hoc, amendment E1): `oracle/audit_env_dates.py` -> `oracle/env_date_audit.json`
  (installed versions vs. PyPI upload dates); `oracle/run_era_check.sh` rebuilds the 12 s3fs/gcsfs releases whose
  dependencies were newer than release date + 3 d, strictly era-matched, and re-runs the frozen oracles ->
  `oracle/results_era/` (incl. `*.freeze.txt`); `oracle/compare_era.py` -> `oracle/era_comparison.json`:
  1,048 verdicts compared, 0 differ. pyarrow, obstore and OpenDAL ship their I/O code in the wheel; their other Python
  dependencies serve the oracle's raw API only.
- `oracle/attribution_results.json` — commit-level attribution (`oracle/attribute.py`): parent violates, fix satisfies.
- `PROBE_CATALOG.md` — every probe with the historical artifact it was derived from.
- `rq3/runs/*.jsonl` — every model call (raw output, verdict, plan hash, model digest, GPU); `rq3/runs/run_meta.json`.
  `rq3/runs/protocol.md` is the plan file the Kaggle run hashed (identical to `protocol/BEHAVIORAL_ABSTRACTION_PROTOCOL.md`).
- `rq3/analyze.py`, `rq3/results_to_latex.py`, `rq3/exploratory.py` — reproduce Tables 7 and 8 and all RQ3 numbers:
  `python rq3/results_to_latex.py rq3/runs/ollama_qwen3-coder_30b.jsonl rq3/runs/ollama_gpt-oss_20b.jsonl`
- `protocol/PLAN_AMENDMENTS_POSTFREEZE.md` — exploratory analyses defined before results (A1, A2) and post hoc ones (P1).
- `rq2_baseline/` — post hoc text-similarity baseline (Table 6): `python rq2_baseline/topic_similarity.py`
  (fetched thread texts are included, so it runs offline).
- `rq3/kaggle/rq3_kaggle_R1.ipynb`, `rq3/runs_R1/` — configuration-sensitivity rerun R1 of gpt-oss-20b (larger output
  budget), defined in `protocol/PLAN_AMENDMENTS_POSTFREEZE.md` before it ran.
- `rq3/sensitivity.py` -> `rq3/sensitivity_results.json` — P1(b) (balanced accuracy excluding unparsed answers) and
  the R1 analysis (integrity checks, then the frozen analysis code applied to the rerun).
- `rq3/rule_level.py` -> `rq3/rule_level_results.json`, `paper/tab_rq3_rules.tex` (Table 9): per-rule paired B1/B3
  balanced accuracy and difference for the two frozen runs and the R1 rerun.

## Third-party content
Issue and pull-request texts (`rq3/histories/*.txt`, `rq2_baseline/threads/*.txt`) are public GitHub content, included
only as the exact inputs of the reported experiments. The raw GitHub API responses, which carry user-profile metadata
(logins, ids, avatar URLs), are not redistributed; `rq3/fetch_histories.py` re-fetches them from the public API. Project
and commit identifiers refer to public repositories; the evidence log names developers only where public commit
authorship is itself evidence (lineage checks).

## Request-level check: are the verdicts artifacts of the emulators? (paper §6, "Are the verdicts artifacts of the emulators?")
- `oracle/wire/run_wire.sh` re-runs the discriminating operation of all 21 Golden-Case/PV1 verification rows with the
  client connected to a fresh emulator through `oracle/wire/tap.py`, a relay that records the client's requests and
  forwards them unchanged.
- `python3 oracle/wire/wire_check.py` decides every row from the recorded requests alone, using only the services'
  documented API contracts (listed in its header), and compares with the emulator verdict. Recorded traffic is in
  `oracle/wire/out/`; the result, 21 of 21 agreeing, is in `oracle/wire/out/wire_results.json`. The checker runs
  without any environment: `python3 oracle/wire/wire_check.py`.
