# Evidence log (working notes kept during the study, chronological)
Superseded hypotheses are kept on purpose (e.g. C1 refuted, R2 downgraded to shared origin, 'GC4' reclassified as
prospective case PV1). Authoritative: the paper, `dataset/cases.jsonl`, `oracle/event_classification.json`.

# Golden Case candidates (stage 9)
Protocol: ../project/paper/BEHAVIORAL_ABSTRACTION_PROTOCOL.md. Pre-2026 history only.

## fsspec built-ins — funnel (28 Sep 2026)
2,512 pre-2026 commits → 409 fixes → 130 touch shared base code (excluded) → 118 single-backend
→ 79 in independent backends → 20 methods fixed in ≥2 backends (noisy proxy) → ~3 same-rule groups.
Not independent: arrow (wraps pyarrow), http_sync (derived from http), cached / cache_* / dirfs /
asyn_wrapper / chained (wrappers), reference.
Method-name matching is NOT rule matching (ls fixed in 7 backends for 7 unrelated reasons).
Note: git needs `*.py diff=python` for hunk headers to show indented methods.

## C1 — Placeholder directories — STRONG (first natural cross-implementation case)
Rule: in object stores a directory may exist as a key prefix AND/OR as an explicit placeholder
object (key ending in `/`); listing/find must treat these as one directory — no missing
subfolders, no duplicate entries.
- gcsfs #321 (2020-12-30, merged) — 353 words real rationale: placeholder objects cached in
  dircache → subfolders unretrievable.
- gcsfs #459 (2022-03-22) — "Fixes #458"; rationale in issue #458 (TO FETCH).
- s3fs #989 (2025-11-05, merged) — 457 words incl. discussion; repro shows duplicated entries
  ['a/', 'b', 'b/', 'c/']. CHECK for AI co-author markers (late 2025).
- fsspec memory 79c1493 (2020) — recursive rm fails with implicit (pseudo) parent dirs (related).
Independence: gcsfs and s3fs implement _ls/_find/_rm in their own core.py (s3fs _rm core.py:2390;
gcsfs _rm core.py:1640) — verify the placeholder handling itself is not inherited.
Remote-determined? No — the service exposes marker objects; normalization is backend code.
In fsspec API spec? No — project-specific engineering rule.
Shape: history in A (gcsfs 2020) → natural violation in independent B (s3fs 2025).
TODO: oracle — find tests added in #321 / #989; run locally (moto for s3fs, fake-gcs for gcsfs).

### C1 ORACLE RESULT (28 Sep 2026) — forward hypothesis REFUTED
Harness: oracle/c1_oracle.py + oracle/run_c1.sh. Identical world built via RAW API (boto3 /
GCS JSON API); assertions via generic fsspec API only. fake-gcs-server v1.37.2 (latest on fix
date; gcsfs 2022 CI used `:latest`, so the exact emulator is unrecoverable), sha256
d6cc307d...fbde. moto 5.2.3 in-process.
                 A1 no-dup  A2 ls cold==warm  A3 placeholder=dir   verdict
  gcsfs 2022.2.0   pass        FAIL              FAIL              violated
  gcsfs 2022.3.0   pass        FAIL              FAIL              violated
  s3fs 2025.10.0   pass        FAIL              pass              violated
  s3fs 2025.12.0   pass        pass              pass              HOLDS
- s3fs BAD reproduces #988 exactly: warm ls = ['c','e/','p','p','p/','q'] (duplicates).
- gcsfs #459 fixed ONLY info('p/') (trailing slash) file->directory — exactly its own test.
  info('p') still 'file'; warm ls returns nested files ['c/c','p/inner','q'] in BOTH versions.
- No single assertion discriminates BAD->GOOD in BOTH backends => the two fixes are DIFFERENT
  bugs in the same topic, not one rule. Forward C1 (gcsfs history -> s3fs violation) rejected.
- A4 (empty placeholder e/): gcsfs never treats it as a directory; s3fs does after #989.
  Genuine divergence between implementations -> correctly excluded from the verdict.

## ⚠ R2 — VERIFIED RULE, BUT SHARED-ORIGIN CODE (downgraded 28 Sep 2026) — was "Golden Case #1"
LINEAGE FINDING (decisive): gcsfs's find()->dircache code was PORTED from s3fs by the same author.
  s3fs  bdfb5b9 2020-09-22 Durant "Cache results of find, and (optionally) include directories"
  gcsfs b6368a2 2020-09-25 Durant "Find to return directories again (#289)"
  -> identical variable names (dirs, sdirs, par), identical dict literal incl. the S3-only
     "StorageClass": "DIRECTORY" inside gcsfs. Fails independence condition 1 at CODE-PATH level.
  gcsfs rewrote the path in E2 (2022, dtrifiro) -> post-2022 gcsfs code is a genuine rewrite, but the
  s3fs code that violated in E3/E4/OPEN is the original lineage. Also: gcsfs's test fixture world is
  byte-identical to s3fs's (files/csv_files/text_files/a-d) -> test suites share lineage too.
STATUS: keep as the MOTIVATING example (recurring rule, 4 fixes, open violation) and as a
'shared-origin' stratum case; NOT primary evidence for transfer across independent implementations.
Related work this now touches: recurring fixes in clones/ported code (Nguyen et al. ICSE'10;
Ray & Kim FSE'12; Ray et al. ASE'13 SPA). The paper must position against these.
IMPLICATION: fsspec backends broadly share Durant-authored lineage -> fsspec alone cannot supply
independent implementations. Prefer cross-LANGUAGE clients of the same abstraction (see §X-LANG).

### (original write-up, kept for the record)
RULE (derived from evidence, not chosen in advance): populating the directory cache through
find() must not change what ls() subsequently returns.
Placeholder objects are a TRIGGER, not part of the rule: without placeholders gcsfs-BAD still
fails and s3fs-BAD passes; with them, both fail. Oracle assertion = A2 (ls cold == ls warm).

| criterion | evidence |
|---|---|
| history A | gcsfs #488 (merged 2022-08-28, dtrifiro), 97 words + repro: "Calling find corrupts the dircache by adding found objects to each directory, thus when calling ls after find, wrong results will be returned" |
| history B | s3fs #988/#989 (merged 2025-11-05, Martin Durant), 457 words incl. discussion; 0 AI markers |
| BAD->GOOD in A | gcsfs 2022.7.1 FAIL -> 2022.8.2 pass (bisected over 44 releases; 2022.8.1 uninstallable) |
| BAD->GOOD in B | s3fs 2025.10.0 FAIL -> 2025.12.0 pass |
| same rule | ONE assertion (A2) discriminates BAD->GOOD in BOTH backends |
| independent code | fsspec held constant: gcsfs ba716f4^ FAIL / ba716f4 pass (fsspec 2022.8.2); s3fs 291fef9^ FAIL / 291fef9 pass (fsspec 2025.12.0). Fix lives in each backend's own code |
| developers | different authors (dtrifiro vs Martin Durant) |
| remote-determined | no — dircache is client-side |
| emulator-independent | gcsfs identical on fake-gcs-server v1.37.2 and v1.56.1 |
| provenance | pre-2026; gcsfs fix 2022 (pre-LLM-assistant era) |
Conditions: emulator TZ=UTC (non-UTC timestamps crash newer gcsfs); GCSFS HNS mode OFF.
Reproduce: oracle/run_c1.sh, oracle/gcs_run.sh; bisect log in session notes.
OPEN: unseen implementation C (candidates: adlfs/Azure via Azurite, ocifs).

### GC#1 expanded (28 Sep 2026, oracle/r2_oracle.py): R2 is a RECURRING rule — 4 fix events, 2 impls
Generalised oracle: reference = ls(d) with a cold cache; probe = ls(d) after trigger, for
d in {root, p, c}; triggers T1 = cold + find(t), T2 = warm ls + invalidate(t) + find(t) (the #492 repro);
t in {root, subdir p, file q, nested file c/c}. Worlds: full (placeholders) / noph.
| # | impl | fix (merged) | who (reporter/fixer) | rationale | BAD -> GOOD release | failing probes on BAD | attribution (fsspec held) |
|---|---|---|---|---|---|---|---|
| E1 | s3fs | #492/#493 2021-06-10 | alf239 / M. Durant | issue + 10-comment discussion, repro; "I would expect before == after" | 2021.6.0 -> 2021.6.1 | T*:file (both worlds) | 4fe36cb^ FAIL / 4fe36cb pass on T*:file @fsspec 2021.06.1 |
| E2 | gcsfs | #488 2022-08-28 | dtrifiro | 97 w + repro script | 2022.7.1 -> 2022.8.2 | T*:root (both worlds) | ba716f4^ FAIL / ba716f4 pass @fsspec 2022.8.2 |
| E3 | s3fs | #773/#791 2023-09-21 | mhtrinh / I. Thomas | issue + analysis w/ dircache dump; PR 70 w | 2023.9.1 -> 2023.9.2 | T*:root (noph) | 3323452^ FAIL / 3323452 pass @fsspec 2023.9.2 |
| E4 | s3fs | #988/#989 2025-11-05 | ischurov / M. Durant | 457 w | 2025.10.0 -> 2025.12.0 | T*:root duplicates (full only) | 291fef9^ FAIL / 291fef9 pass @fsspec 2025.12.0 |
| OPEN | s3fs | — | — | — | still in 2026.9.0 (latest) | ls(p) with placeholder p/: cold lists p/ itself, after find() it does not | — |
s3fs bisection (noph, T1:root): 2021.6.1 F, 2022.1.0 F, 2022.8.2 F, 2023.4.0 F, 2023.9.0 F, 2023.9.1 F,
2023.9.2 P, 2023.10.0 P, 2023.12.x P, 2025.10.0 P. fsspec diff 2023.9.1..2023.9.2 = typos/CI only.
KEY FACTS
- E3 (s3fs) is the SAME failure mode gcsfs fixed 13 months earlier (E2): s3fs releases 2022.8 -> 2023.9
  violated a rule already fixed, with rationale, in an independent implementation. Neither #773 nor
  #791 references gcsfs (checked). = natural "history in A predicts violation in B" instance.
- Same maintainer (Durant) fixed E1 and E4 in s3fs; rule still open in s3fs 2026.9.0.
- gcsfs 2026.8.1 HOLDS on all probes, both worlds (self-entry p/ listed consistently cold & warm).
- Self-entry itself is BY DESIGN in s3fs (#300, 2020, Durant: a real zero-size key exists); the
  violation is only the cache DEPENDENCE. Not reported upstream (search: is:issue dircache/placeholder).
  Reporting upstream deferred until after double-anonymous review.
- Emulator only (moto 5.2.3): real S3 also returns the prefix-equal key in Contents (documented AWS
  behaviour) but not verified on real S3 — threat to validity.
Other assertions: A3 (placeholder info = directory) fixed in gcsfs only after 2024.6.1 — a
separate behaviour; A4 empty placeholder diverges by design. Neither is part of R2.

## C2 — Prefix vs path-segment boundary — MODERATE
Rule: directory membership is decided by path-segment boundaries, not string prefix
(copying folder `a` must not include `ab`).
- gcsfs #576 (2023-08-31) — only 45 words rationale.
- s3fs c4a76cd (2021-04-29) — test `test_same_name_but_no_exact` (ready-made oracle).
TODO: check s3fs fix commit/PR for rationale; confirm independent code paths.

## Rejected
- Relative paths in makedirs: gcsfs #618 (local-side makedirs(dirname('file')) == makedirs(''))
  vs fsspec sftp #1451 (remote-side relative→absolute). Different behaviour — not the same rule.

## Blockers
- (resolved 28 Sep) GitHub API access restored.

## ★ GOLDEN CASE #1 (cross-language) — F2-delete — VERIFIED 28 Sep 2026
RULE (from the histories): recursively deleting directory d must remove EVERY object under d/,
including zero-byte directory-marker objects (d/, d/sub/, d/empty/), so d stops existing; objects that
only share a string prefix (dx/...) must survive.
Rule statement in history A (felipecrv, Arrow #38618): "to ask S3 to delete a directory ... the client
has to ask for the deletion of the empty object with a key ending with `/`".
Oracle: oracle/f2_delete_oracle.py — world via RAW boto3 on moto 5.2.3; verification via RAW boto3
listing (client never grades itself); 5 world variants (top marker / nested marker / empty nested
marker / all / no markers=control). Discriminating assertion: v-nested:A (nothing left under d/).
| | A: Apache Arrow C++ S3FileSystem (pyarrow) | B: s3fs (Python, fsspec) |
|---|---|---|
| history | issue GH-38618 (2023-11-06, martin-traverse) + analysis by jorisvandenbossche, felipecrv; PR #38845 "Rationale for this change" section | issue #918 (2024-12-02, LuchiLucs; Durant analysis 2024-12-03: expand_path drops the "/" placeholder); fix PR #1005 (ywilke) 2026-02-02 |
| BAD | 14.0.0, 14.0.1 (regression from PR #35440): leaves d/sub/, d/empty/ | 2021.6.1 … 2025.12.0: leaves d/, d/sub/, d/empty/ |
| GOOD | 13.0.0 and 14.0.2 | 2026.9.0 |
| same assertion discriminates | v-nested:A, v-emptysub:A, v-full:A | v-nested:A (+ v-top, v-emptysub, v-full) — identical leftover 'd/sub/' in v-nested |
| attribution | release-level: 32 commits 14.0.1..14.0.2, only S3 logic change = ae8ea4d71 (#38845); other S3 commit GH-38364 = lazy init only | commit-level: 5e5f7ea^ VIOLATED / 5e5f7ea HOLDS with fsspec held at 2026.1.0 |
| language / org / people | C++ / Apache Arrow / Van den Bossche, Crv | Python / fsspec / Wilke, Durant |
| AI markers | pre-2026 | fix commit 2026-02 (post-cutoff); only trailer = human co-author Durant; rationale 2024 (pre-cutoff) |
| remote-determined | no — the client chooses which keys to delete | no |
Independence: different languages -> no verbatim copying; pyarrow does not wrap s3fs (AWS SDK C++);
s3fs fix in s3fs's own code (attribution). Lineage condition 1: PASS. Wrapper 2: PASS. Base class 3:
s3fs _rm uses inherited _expand_path, but the discriminating fix is in s3fs code (split_path) -> PASS.
Remote 4: PASS.
Temporal: Arrow's history (2023-12) PRECEDES s3fs's violating releases (through 2025-12) -> natural
"history in A predicts violation in B" instance.
Emulator note: Arrow's own MinIO CI could NOT reproduce the bug (PR #38845 text); moto does
(moto mirrors AWS DeleteObjects no-op on missing key). Record emulator choice as a validity factor.
Held-out C candidates: OpenDAL remove_all, rclone purge (--s3-directory-markers), Hadoop S3A delete.

## ★ GOLDEN CASE #2a (cross-language) — exact key round-trip through put/get — VERIFIED 28 Sep 2026
RULE: the object key written/read must be exactly the user's string; the client must not URL-/percent-
encode it. Discriminating assertions: F3_write_key_exact[café], [sp ace], F3_read[café] (xfam_oracle).
| | A: s3path (Python, boto3 + smart_open) | B: object_store (Rust) via obstore |
|---|---|---|
| history | issue #77 (2021-06-17, realknorke): "the `=` is urlencoded by a as_uri() call ... I expected an tmp/foo=bar/ prefix"; maresb RFC-2396 discussion; fix PR #78 (maresb, 2021-06-21) | issues #496 (2025-07), #523; PR #524 (kylebarron, 2025-08-07) "Don't percent-encode paths": Path::from -> Path::parse |
| BAD | 0.3.01 (writes 'w/sp%20ace', reads 's/caf%C3%A9'); 0.3.0 NOT EVALUABLE in the frozen run (every read/write raises NoCredentialsError: smart_open 5.0.0 no longer accepts session/resource_kwargs; corrected 29 Sep 2026) | 0.4.0, 0.6.0 (writes 'pct%25', 'caf%C3%A9') |
| GOOD | 0.3.02 … 0.6.5 ('?' fixed only in 0.3.3) | 0.8.2 … 0.11.1 |
| attribution | COMMIT-level: 643c25b^ F / 643c25b P (other deps held, era-matched 2021-06) | release-level 0.6.0 -> 0.8.2 (TODO 0.7.3 vs 0.8.0) + PR diff = exact mechanism |
| mechanism | key passed through as_uri() (URL-encoding) | Path::from percent-encodes — SAME class, independent code |
Temporal: s3path history (2021) precedes obstore violation (2024-2025).
THIRD implementation (GCS): gcsfs (Python, GCS JSON API) — issue #447 (2022-02-10, "cannot read a file with
the file path containing # ... A silent bug"), #270; fix PR #502 (simonbohnen, 2022-10-11) "Escape all special
characters in URL paths" (closer to google-cloud-storage). BAD 2022.2.0 … 2022.8.2 (F3_read[hash#], [q?mark]:
'#' truncates the name as a URL fragment: s/hash# -> requests s/hash; corrected 29 Sep 2026), GOOD 2023.1.0 …; COMMIT-level attribution:
56281f4^ F / 56281f4 P with fsspec held at 2022.8.2.
=> GC2a spans s3path (2021) -> gcsfs (2022) -> object_store (2025): 3 independent implementations, 2 languages.
Note: s3path 0.3.x requires Python <=3.9 (pathlib internals) — era-correct interpreter mandatory.

## ★ GOLDEN CASE #2b (cross-language) — exact key round-trip through copy/rename — VERIFIED (oracle) 28 Sep 2026
RULE: copy/rename must address the EXACT stored key; the client must not (re-)encode the key string
(%, é, =, +, space ...). Oracle: oracle/xfam_oracle.py probes F3b_copy[c], F3b_move[c] (world + check
via RAW boto3 on moto). Discriminating assertion: F3b_copy[café], F3b_copy[pct%].
| | A: Apache Arrow C++ (pyarrow) | B: object_store (Rust) via obstore |
|---|---|---|
| history | ARROW-13048 = GH-28758 (2021-06-11): move fails for keys with = or +; David Li: source key DOUBLE-encoded (Arrow encodes, AWS SDK encodes again); fix PR #10526 (2021-06-14) | #671 (2026-04-22): "obs.copy() percent-encodes the source path internally"; fix PR #672. Earlier sibling: PR #524 (2025-08-07) "Don't percent-encode paths" (Path::from -> Path::parse) fixed put/get but MISSED copy/rename |
| BAD | 3.0.0, 4.0.1 (all 5 chars fail copy) | 0.4.0 … 0.9.3 (pct%, café fail copy) |
| GOOD | 5.0.0 … 21.0.0 | 0.9.4, 0.11.1 |
| attribution | release-level 4.0.1->5.0.0 (major release; mechanism-consistent: NoSuchKey on copy = double-encoded source) — WEAKER | 0.9.3..0.9.4 = exactly 2 commits: cherry-pick of #672 + version bump — commit-level equivalent |
| language/org/people | C++ / Apache Arrow / Li | Rust+Py / developmentseed / Barron; core object_store = arrow-rs |
| cutoff | pre-2026 | FIX 2026 (post-cutoff); #524 sibling 2025 pre-cutoff |
Also in family: obstore put/get key mangling 0.4.0/0.6.0 BAD -> 0.8.2 GOOD (#524).
Temporal: Arrow history (2021) precedes obstore violation (2024-2026).
Platform note: pyarrow <5 has no arm64 wheels -> run as x86_64 under Rosetta (uv cpython-3.9-macos-x86_64).

## ★ GOLDEN CASE #3 (cross-language) — path-segment boundary in existence checks — VERIFIED (oracle) 28 Sep 2026
RULE: "foo" exists as a directory only if some key starts with "foo/" (or equals "foo/"); a key that
merely starts with the string "foo" ("foobar", "prefix1") must not make "foo" exist.
World = s3fs test_same_name_but_no_exact: very/similar/prefix1, prefix2, prefix3/something.
Discriminating assertion: F1_stat_string_prefix_notfound[very/similar/prefix] (also [prefi], [prefix3/some]).
| | A: cloudpathlib (Python, boto3) | B: Apache OpenDAL (Rust) |
|---|---|---|
| history | issue #208 (2022-02-07, maciejb): "S3Path.exists() returns True on partial matches ... file foobar ... false positive when querying for foo"; jayqi: "too permissive and needs to also check if there's a /"; fix PR #244 (frndmg, merged 2022-08-11) | core PR #4959 (meteorgan, 2024-08-26) "make list return path itself" — complete.rs stat-dir simulation stopped trimming the trailing '/' before list(prefix, limit=1). Rationale section EMPTY; F1 fix is a side effect |
| BAD | 0.4.1 … 0.9.0 (info = directory) | python 0.43.0 … 0.45.9 (core <=0.49.2) |
| GOOD | 0.10.0 … 0.25.0 | python 0.45.10 (core 0.50.0) … 0.47.10 |
| attribution | 0.9.0..0.10.0 = 6 commits; only semantic one = #244 | core 0.49.2..0.50.0 = 39 commits; code-level: complete.rs diff in #4959 is exactly the mechanism (list(path.trim_end_matches('/')) -> list(path)); no Rust toolchain for commit-level rebuild |
| mechanism | list with prefix lacking '/' in the fallback path | list with prefix lacking '/' in stat-dir simulation — SAME mechanism, independent code |
| language/org | Python / DrivenData | Rust / Apache OpenDAL |
Temporal: cloudpathlib history (2022) precedes OpenDAL violation (to 2024-09) -> natural forward instance.
Related (not same assertion): gcsfs #576 (2023) find/copy of folder 'a' includes 'ab' — family F1.
OPEN VIOLATIONS of the same rule in s3path 0.6.5 (LATEST, 2026-01) — found by transferring this rule
(oracle/xfam2_oracle.py F15 + manual repro; client-side mechanism, not emulator-dependent):
  - rmdir('tmp') on an EMPTY dir deletes siblings 'tmpfile.txt', 'tmp_keep/important.csv' (DATA LOSS)
  - rename('reports'->'moved') also renames 'reportsX.txt', 'reports_archive/...'
  - rename('a'->'z') rewrites 'a/b/a/x' -> 'z/b/z/x' (str.replace of every occurrence)
  cause: accessor.py objects.filter(Prefix=key) without '/', and key.replace(src, dst). Present in every
  s3path version tested (0.3.02 … 0.6.5). No matching upstream issue found (searched rename/prefix/similar).
  Draft report prepared — NOT posted (deferred until after double-anonymous review).
=> Family F1 now has fix events in cloudpathlib (2022), gcsfs (2023), OpenDAL (2024) and a live
   violation in s3path (2026): 4 independent implementations.

## ◇ PROSPECTIVE CASE PV1 (was 'GC4', reclassified 29 Sep under strict v3 definition) — directory move/copy must not touch same-prefix siblings
RULE: moving/copying directory 'src' affects only keys under 'src/'; 'srcx', 'src_old/...' are untouched.
Oracle: oracle/xfam2_oracle.py F15b_move_dir_sibling_untouched[markers|implicit], F16b_copy_dir_sibling_not_copied.
| | A: gcsfs (Python, GCS; fake-gcs-server 1.56.1, TZ=UTC) | B: s3path (Python, S3; moto) |
|---|---|---|
| history | fsspec PR #1340 (jlanglois-jam, 2023-08-22): "copying a folder also copy files that have the same name prefix as the folder name" + example; gcsfs PR #576 (merged 2023-08-31) fix | none (no upstream report found) |
| BAD | 2022.8.2 … 2023.6.0 (F15b, F16b fail: copies/moves 'srcx', 'src_old/h') | 0.3.02 … 0.6.5 = ALL versions incl. latest (F15b fails: 'srcx' -> 'dstx') |
| GOOD | 2023.9.0 … 2026.8.1 | — (open) |
| attribution | COMMIT-level: 5b97087^ F / 5b97087 P on F15b[markers], F15b[implicit], F16b with fsspec held at 2023.6.0 | n/a (open); mechanism read in source: objects.filter(Prefix=key) w/o '/' |
| independence | different authors/projects (fsspec org vs liormizr); gcsfs = GCS JSON API, s3path = boto3; no shared code | |
Caveat: the rule was then encoded in fsspec's SHARED abstract test-suite (#1340) -> for fsspec backends it is
'spec-like'; s3path is outside fsspec, so no leakage for B.
Controls: s3fs (all tested versions) and cloudpathlib copytree hold F16b; cloudpathlib has no dir rename (n/a).
Family F1 (segment boundary) now: GC3 (exists: cloudpathlib->OpenDAL) + GC4 (move/copy: gcsfs->s3path) +
s3path rmdir sibling DELETION (live, data loss). Mixed model should include a FAMILY random effect.

## ◆ CONTESTED RULE (negative control) — does listing a directory include the directory's own marker?
World: m/ (zero-byte marker) + m/x. ls(m) == [m/x]?
| impl | behaviour | history |
|---|---|---|
| pyarrow C++ | EXCLUDES (all versions 3.0–21.0) | contract in docstring: "The selector's base directory will not be part of the results"; GH-37555/PR #37558 fixed the FSSpecHandler WRAPPER to match |
| cloudpathlib | INCLUDED <=0.10.0 -> EXCLUDES from 0.11.0 | fix in 0.10.0..0.11.0 (TODO: which PR; candidate #302 list_objects_v2) |
| s3path | INCLUDED <=0.3.01 -> EXCLUDES from 0.3.02 | COMMIT-level: 33e6d17 'fix_iterdir_returns_path_for_empty_directories' (#81, liormizr, 2021-06-27): 33e6d17^ F / 33e6d17 P |
| s3fs | INCLUDES (all versions) | #300 (2020): Durant — by design, a real zero-size key exists |
| obstore | INCLUDES (all versions) | object_store has no directory concept |
| OpenDAL | EXCLUDED <=0.45.9 -> INCLUDES from 0.45.10 | core PR #4959 "make list return path itself" (issue #4877) — deliberate reversal |
=> Implementations move in OPPOSITE directions over time. Use as negative control: history that
states this 'rule' should NOT transfer; a model that blindly transfers it is wrong on some impls.

## §X-LANG — cross-language object-store filesystem clients (proposed primary ecosystem, 28 Sep 2026)
Same abstraction (filesystem semantics over an object store), different languages/orgs -> no
verbatim copying possible; lexical overlap minimal. Backend held fixed (moto server; raw boto3 world).
  s3fs (Python, fsspec) · pyarrow.fs.S3FileSystem (C++, Apache Arrow) · object_store (Rust, arrow-rs;
  PyPI binding obstore) · OpenDAL (Rust, Apache; PyPI opendal) · rclone (Go; binary) · Hadoop S3A (Java)
Candidate rule families (client-side, observable through the public API):
  F1 path-segment boundary (list/delete/copy of `a` must not touch `ab`)
  F2 directory markers / placeholder objects (`dir/` zero-byte keys)
  F3 special characters in keys (space, +, %, unicode) round-trip
  F4 pagination (>1000 keys) completeness
  F5 parent-directory persistence after deleting the last child
TODO: mine fix history per client for each family; portable oracle per family.

## Batch-2 screening notes (xfam2, 28 Sep 2026)
- rmdir on NON-empty dir: s3fs/cloudpathlib/OpenDAL refuse or keep contents; s3path deletes (#205 open) -> contested/open.
- rmdir on EMPTY marker dir: cloudpathlib flip 0.10.0 F -> 0.13.0 P; s3fs always refuses (rmdir = buckets only) -> single-impl flip.
- s3fs 2026.9.0: mv(recursive) of an implicit dir raises FileNotFoundError after copying (left src+dst);
  NOT caused by #1005 (5e5f7ea^ and 5e5f7ea both pass). Regression somewhere 2026-02..2026-09 (post-cutoff). TODO bisect.

## GCS screening notes (xfam_oracle XF_BACKEND=gcs, fake-gcs-server 1.56.1, 28 Sep 2026)
- gcsfs F1_find/delete_boundary + F9 double-slash: P (2022.2-2022.7.1) -> F (2022.8.2-2023.1.0) -> P (2023.9.0):
  the R2 fix #488 (ba716f4, 2022-08) INTRODUCED a segment-boundary regression (`_prefix = key` without '/'),
  repaired by #576 (2023-08). Rule interaction worth reporting (fixing rule X broke rule Y).
- gcsfs F7_marker_is_dir: F until 2024.6.1, P at 2026.8.1 (single-impl flip; = A3 behaviour from C1 work).
- pyarrow GCS: F1_delete_boundary / F9 / F11_ls_dir_with_space fail in ALL versions 10-21 — UNVERIFIED:
  may be fake-gcs-server incompatibility with google-cloud-cpp; needs real GCS before any claim.
- OpenDAL 0.43 on GCS: all-F = auth/emulator incompatibility (excluded). obstore GCS: writes need a token,
  copy uses XML API unsupported by emulator -> only read/list probes valid.
- OpenDAL 0.45.x on GCS hangs (retry/backoff) -> runs aborted; S3 results used instead.

## Batch-3 screening notes (xfam2 F4b/F17/G*, S3, 28 Sep 2026)
- F4b >1000 sub-directories (CommonPrefixes pagination): all 6 clients pass in all versions.
- F17 info('t/f/') on a FILE: OpenDAL -> notfound; s3fs/s3path/pyarrow -> 'file'; cloudpathlib 'notfound'
  <=0.10.0 then 'file' from 0.13.0 -> CONTESTED.
- Glob (pathlib-spec-defined -> leakage flag): s3path 0.4.1 broken (G1 [], G2 leaks 'dx/e.csv' = F1 boundary
  violation) -> fixed 0.5.0 (issue #160, 2024-02); cloudpathlib <=0.10.0 glob from bucket root returns []
  -> fixed by #312 "Fix globbing top level buckets" (2023-01). Same assertion G1 flips in both but
  mechanisms differ and the 'rule' is generic ("glob works") -> WEAK candidate, not Golden.
- s3fs '**' semantics flip (2022.8.2 -> 2023.9.2) comes from fsspec's shared glob -> excluded (condition 3).

## Excluded: glob correctness (29 Sep) — not attributable
Same assertion G1 flips in s3path (0.4.1 F -> 0.5.0 P) and cloudpathlib (<=0.10.0 F -> 0.13.0 P), but: s3path's window
0.4.2..0.5.0 is a 44-commit refactor (no identifiable fix commit); cloudpathlib's failure at 0.10.0 PREDATES the
documented glob regression (#304 -> #311 -> fix #312, 2023-01), so the flip has no identified fix event. Fails the
attribution requirement -> excluded (principled, not post hoc). Also pathlib-spec-defined (leakage flag).
