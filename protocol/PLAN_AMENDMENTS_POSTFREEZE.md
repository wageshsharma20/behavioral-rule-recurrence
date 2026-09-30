# Post-freeze amendment log (the frozen plan BEHAVIORAL_ABSTRACTION_PROTOCOL.md, sha256 prefix f5de6779689e8c4c, is NOT modified)
Every entry is written BEFORE any model output has been seen. Entries are EXPLORATORY analyses; they do not change
the primary test (B3 vs B1 balanced accuracy, T=0) or any secondary comparison.

## A1 — 2026-09-29 05:26 IST — scenario-mechanism coding (exploratory)
For every model answer with verdict DEFECT on a BAD item, code whether the free-text "scenario" names the rule's
mechanism, using fixed case-insensitive keyword sets (defined now, before results):
- GC1 (delete markers): marker | placeholder | trailing slash | "/" suffix | empty object | zero-byte | directory object
- GC2a / GC2b (exact key): encod | escap | percent | quote | url-encod | %2 | %c3 | special character | unicode | "=" | "+" | "#"
- GC3 (segment boundary): prefix | separator | trailing slash | foobar | sibling | similar name | "/" suffix | starts with
- PV1 (s3path rename/rmdir): prefix | separator | sibling | replace | similar name | starts with
Report: share of correct DEFECT verdicts whose scenario names the mechanism, per condition (B1, B3, B4, B5).
Rationale: a correct verdict can be right for the wrong reason; this measures whether history changes the reason.

## A2 — same time — reporting of k=5 samples
Report per-item agreement across the 5 samples at T=0.7 (share of items with a unanimous verdict) as a stability
measure, alongside the majority-vote balanced accuracy already specified.

## P1 — 2026-09-29 10:31 IST — POST HOC (defined AFTER seeing results; reported as post hoc)
(a) Mechanism coding (A1 keywords) applied to FALSE ALARMS (satisfying code judged DEFECT) — motivated by the observed
    defect bias. (b) Sensitivity: balanced accuracy excluding UNPARSED answers (gpt-oss exhausted its 4,096-token budget
    during reasoning on 23/78 primary prompts). Neither changes the primary analysis, which counts UNPARSED as errors.

## R1 — 2026-09-29 12:53 IST — configuration sensitivity rerun (defined after the frozen results, BEFORE this run)
Reason: gpt-oss-20b exhausted its 4,096-token output budget during reasoning on 23 of 78 primary prompts.
Run: gpt-oss-20b (same Ollama tag), the same 78 prompts (same sha256), T=0, seed 1000, num_predict=16,384,
num_ctx=24,576; everything else unchanged (same parser, same analysis code). No sampling runs.
Reporting: a configuration-sensitivity analysis next to the frozen primary result; the frozen run remains the primary
analysis and is not replaced, whatever the outcome.

## P2 — 2026-09-29 12:55 IST — POST HOC: text-similarity baseline for RQ2 (illustrative)
TF-IDF cosine similarity between full fix threads (issue + PR, cleaned; implementation names removed) for every
candidate pair examined in the study: 6 Golden pairs, 6 rejected pairs, 30 different-rule pairs among Golden threads.
Script: rq2_baseline/topic_similarity.py. Illustrative only: the pair set is the one examined, not a sample.

## E1 — 2026-09-29 13:30 IST — dependency-era sensitivity check (post hoc; defined BEFORE running it)
Finding: an audit of the frozen run's environments against PyPI upload dates showed that 4 s3fs environments (2021.6.0,
2021.6.1, 2025.10.0, 2025.12.0) and 8 gcsfs environments resolved some dependencies later than release date + 3 days
(gcsfs: current aiohttp / google-auth). s3path (12/12) and cloudpathlib (16/16) are era-matched; pyarrow, obstore and
OpenDAL ship their I/O code in the release wheel (their Python dependencies serve only the oracle's raw API).
Check: rebuild the 12 releases with every dependency resolved as of release date + 3 days, run the unchanged frozen
oracles (hash-checked), compare every verdict with the frozen run (oracle/run_era_check.sh, oracle/compare_era.py).
Reporting: the frozen run remains primary; the paper states the environment policy as executed and reports this check,
whatever its outcome.
Outcome (E1): the 12 releases rebuilt with every dependency resolved as of release date + 3 days (28 oracle runs,
1,048 probe verdicts) reproduce every verdict of the frozen run (0 differences). One rebuilt environment (s3fs 2025.12.0)
first lacked boto3, which the oracle's raw API needs (the s3fs [boto3] extra no longer exists); boto3 was added under the
same date bound and the three oracles re-run. Files: oracle/results_era/, oracle/era_comparison.json,
oracle/env_date_audit.json (audit script: oracle/audit_env_dates.py).

## R1 outcome — 2026-09-29 (run completed 14:51 IST; analysed with rq3/sensitivity.py, rq3/rule_level.py)
Integrity: 78 records; ids, prompt hashes, plan hash (f5de6779689e8c4c) and model digest identical to the frozen gpt-oss run.
8 of 78 answers remain without a verdict (frozen: 23); no answer that the frozen run had parsed changed.
Paired items (14): B1 0.43, B3 0.57 (W/L 2/0, exact p = 0.50); B4 on the same items 0.64; satisfying versions flagged
under B3: 5 of 7. Conclusion unchanged. Reported next to the frozen primary analysis, which it does not replace.
P1(b) is reported in two forms: dropping unanswered items per condition (B3 0.64 vs B1 0.50) and dropping every pair with
an unanswered item (8 pairs, 0.50 vs 0.50); the second form was computed on 29 Sep 2026, after R1 was defined.
Rule-level presentation (Table 9): the frozen plan's per-rule results, shown as paired B1/B3 per rule with the difference;
added after reviewer feedback, computed by rq3/rule_level.py; no new test.

## W1 — Request-level check of the Golden-Case verdicts (1 Oct 2026; post hoc, outside the frozen plan)
Reason: reviewers ask whether the verdicts are artifacts of the emulators (moto, fake-gcs-server). No production
cloud accounts were available. Procedure: `oracle/wire/run_wire.sh` re-runs the discriminating operation of all 21
verification rows (`oracle/verify_golden.sh`) with the client connected to a fresh emulator through a byte-level
recording relay (`tap.py`, which forwards traffic unchanged); world set-up and verification bypass the relay.
`wire_check.py` then decides each row from the recorded client requests alone, using only documented service
contracts (S3 API Reference: CopyObject, DeleteObjects, ListObjectsV2; GCS request endpoints). The predicates are
written per case in `wire_check.py`. The first analysis flagged one row (gcsfs 2023.9.0, PV1) because it also deletes
the non-existent key `src` itself; the predicate was refined to exclude the two directory names and was re-applied
to all rows.
Outcome: all 21 request-level verdicts equal the emulator verdicts and the frozen expectations
(`oracle/wire/out/wire_results.json`). It does not test whether the production services honor their documentation.

## W2: Self-consistency check of the Golden-Case rules (1 Oct 2026; post hoc, outside the frozen plan)
Reason: a reviewer argued that a rule derived from a fix shows convergence, not correctness. Procedure:
`oracle/wire/self_consistency.py` runs on the 21 verification rows. It builds the world through the raw API, then uses
only the client under test to check whether the operation's outcome contradicts the client's own API.
Two predicates were refined after a first run, and both refinements were re-applied to all rows:
- copy: the evidence that the source exists is now a successful read by the client, because obstore has no info call;
- move: "inside src" is now the client's non-recursive listing walked level by level, because gcsfs 2023.6.0's
  recursive find itself wrongly includes srcx.

Outcome: 11 of 11 violating rows are self-contradictory and 0 of 10 satisfying rows are
(`oracle/wire/out/self_consistency_results.json`).
