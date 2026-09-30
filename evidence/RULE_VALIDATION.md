# Rule Validation Table (paper Definition 3 and §5.1)
One block per Golden Case. A rule is accepted only if all three agreements of Definition 3 hold:
- **executable agreement**: one oracle assertion separates a violating from a satisfying release in ≥2 lineage-independent
  implementations;
- **historical agreement**: every implementation's fix record supports the same proposition;
- **normative agreement**: the rule follows from a specification or documented client contract that is independent of
  the fixes. The oracle is never accepted merely because the fix passes it.

Sources:
- quotes: `evidence/SPECIFICATION_ANCHORS.md` and `rq2_baseline/threads/`;
- runs: `oracle/verify_golden.sh`, `oracle/wire/out/wire_results.json`, `oracle/wire/out/self_consistency_results.json`;
- lineage: `CANDIDATES.md` and `evidence/participants*.json`.

## GC1: recursive delete removes directory markers
| Field | Content |
|---|---|
| Rule statement | Recursively deleting directory `d` removes every object under `d/`, including zero-byte markers (`d/`, `d/sub/`), so `d` no longer exists; `dx/…` survives. |
| Historical source A | Apache Arrow GH-38618 / PR #38845 (Dec 2023): "we need to add the [separator] … to properly delete the object" |
| Historical source B | s3fs #918 / PR #1005 (Feb 2026): "`expand_path` is not recovering the zero-length directory placeholder with '/' suffix" |
| External specification | AWS S3 User Guide: a console folder is a 0-byte object whose key ends in `/`. S3 DeleteObjects removes exactly the keys named. |
| Client API promise | pyarrow `delete_dir`: "Delete a directory and its contents, recursively."; fsspec `rm(recursive=True)`: deletes directories and their contents |
| Observable violation | After `delete_dir(d)` returns normally, `d/sub/` remains and the client still reports `d` as existing (self-contradiction, 2/2 violating rows) |
| Oracle | `oracle/f2_delete_oracle.py`, assertion `v-nested:A_nothing_under_d` (raw-API listing) |
| Request-level evidence | Violating releases never name `d/sub/` in their delete requests; fixed releases do |
| Alternative interpretation considered | "Explicitly created directory markers are user data that a recursive delete may keep." Rejected: both clients' documentation promises deletion of the directory *and its contents*; both clients themselves report `d` as still existing; both projects fixed it; no thread argues for keeping markers. |
| Same rule, not only same failing test | Different code (C++ listing refactor vs. Python path splitting); both threads state that the marker must be deleted with its trailing separator |
| Lineage | C++ vs. Python; no shared code; no shared fix participant; the 2 contacts between the fixes are unrelated to the rule |
| Final validated proposition | A recursive delete of `d` must delete `d`'s marker objects, including nested ones. |

## GC2a: stored keys equal the user's string (put/get)
| Field | Content |
|---|---|
| Rule statement | The object key written or read is exactly the user's string; the client must not percent-encode it or cut it at a URL delimiter. |
| Historical sources | s3path #77 / PR #78 (Jun 2021): "the `=` is urlencoded … I expected an `tmp/foo=bar/` prefix"; gcsfs #447 (+#270) / PR #502 (Oct 2022); obstore #496 / PR #524 (Aug 2025) |
| External specification | AWS: "The object key (or key name) uniquely identifies the object … When you create an object, you specify the key name." GCS: `#` must be encoded in an object name in a URL (a raw `#` begins the URL fragment and is never sent). |
| Client API promise | s3path ("Like pathlib, but for S3") and cloudpathlib-style path APIs: the path names the object; obstore `put(path)` / gcsfs `cat_file(path)` address the given path |
| Observable violation | `café` is stored as `caf%C3%A9`; reading `s/hash#` requests `s/hash`. The client lists a different name than it wrote, or cannot read a path it lists (self-contradiction, 3/3 violating rows). |
| Oracle | `oracle/xfam_oracle.py`, assertions `F3_write_key_exact[café]` and `F3_read[hash#]` |
| Request-level evidence | Violating releases send `caf%25C3%25A9` (double-encoded) or request `s/hash` |
| Alternative interpretation considered | "A client may define its own key mapping, such as URL-safe encoding." Rejected: both services define the key as the name the user specifies; the encoded objects are invisible under their name to every other tool; s3path's reporter calls it a break from s3path ≤0.3; all three projects changed to exact keys. |
| Same rule, not only same failing test | Three mechanisms (URI helper, missing escape, percent-encoding constructor), one proposition: the service must receive exactly the user's key |
| Lineage | Python (2 clients) and Rust; no shared code; no shared fix participant; the 13 gcsfs–obstore contacts are all unrelated to key encoding |
| Final validated proposition | The key a client stores or reads is the user's string, unmodified. |

## GC2b: copy/rename addresses the exact source key
| Field | Content |
|---|---|
| Rule statement | Copy and rename address the exact stored source key; the client must not re-encode it. |
| Historical sources | Arrow GH-28758 (ARROW-13048) / PR #10526 (Jun 2021); obstore #671 / PR #672 (Apr 2026) |
| External specification | AWS CopyObject: `x-amz-copy-source` is `bucket/key`, and "The value must be URL-encoded" (exactly once) |
| Client API promise | pyarrow `copy_file`: "Copy a file."; obstore `copy`/`rename` of a path |
| Observable violation | Copying `café` or `eq=1` fails with "The specified key does not exist", although the client can read the source (self-contradiction, 2/2 violating rows) |
| Oracle | `oracle/xfam_oracle.py`, assertion `F3b_copy[café]` |
| Request-level evidence | Violating releases send `x-amz-copy-source: …caf%25C3%25A9` (encoded twice) |
| Alternative interpretation considered | "Keys with special characters are unsupported for copy." Rejected: both clients read and write such keys; the service documents one level of encoding; both projects fixed it. |
| Same rule, not only same failing test | Both violations double-encode the copy source (Arrow: client plus SDK; obstore: path constructor); same proposition |
| Lineage | C++ vs. Rust; no shared code; no shared fix participant; the 44 contacts of the obstore author with Arrow in the window concern PyCapsule, JS and Parquet, not S3 |
| Final validated proposition | Copy and rename must address the source object by its exact key. |

## GC3: a directory does not exist because a string-prefix sibling does
| Field | Content |
|---|---|
| Rule statement | `foo` exists as a directory only if some key starts with `foo/`; keys that merely start with the string `foo` (`foobar`, `prefix1`) do not make `foo` exist. |
| Historical sources | cloudpathlib #208 / PR #244 (Aug 2022): "exists() is returning True for anything that begins with the same as a real file"; OpenDAL PR #4959 (Aug 2024; the fix diff, no rationale text) |
| External specification | POSIX 1003.1-2024 §4.16: "Each filename in the pathname is located in the directory specified by its predecessor". AWS/GCS: a folder is a prefix ending in the delimiter `/`. |
| Client API promise | OpenDAL: "To specify that a path is a directory, you must include a trailing slash (/)"; cloudpathlib mimics pathlib (`is_dir`, `exists`) |
| Observable violation | The client reports directory `very/similar/prefix` while its own listing of that directory is empty (self-contradiction, 2/2 violating rows) |
| Oracle | `oracle/xfam_oracle.py`, assertion `F1_stat_string_prefix_notfound[very/similar/prefix]` |
| Request-level evidence | Violating releases list prefix `foo` (no separator) with limit 1; fixed releases list `foo/` |
| Alternative interpretation considered | "S3 prefixes are plain strings (ListObjects `prefix` matches `foobar`), so this is the service's semantics." Rejected: that is the semantics of a *listing prefix*, not of *directory existence*. Directory existence is defined by path components (POSIX), by the services' folder convention (a prefix ending in `/`) and by the clients' own conventions. The client's own listing contradicts its verdict. |
| Same rule, not only same failing test | Same mechanism and remedy in Python and Rust (Fig. 3); cloudpathlib's thread states the rule; OpenDAL's diff implements it |
| Lineage | Python vs. Rust; no shared code; no shared fix participant; no contacts between the projects |
| Final validated proposition | Directory existence is decided by path segments, not by string prefixes. |

## Contrast: the contested rule fails normative agreement
Does listing `d` return `d`'s own marker? The clients' own specifications disagree:
- pathlib `iterdir` excludes the directory itself;
- OpenDAL `list` returns "path itself … if it exists".

The rule therefore fails normative agreement. It is classified as contested, not validated.

## Independent adjudication (pending)
Not yet done. The kit is in `evidence/adjudication/`:
- blinded thread pairs;
- the instructions;
- the answer sheet;
- the scoring script.

It is for a reader who did not derive the probes.
