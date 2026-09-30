# Was each specification documented BEFORE the fix? (paper §5.1; generated from `evidence/spec_history.json`)

`evidence/spec_history.py` retrieves, for every specification anchor, a version dated before the earliest fix of its case (for
a client's own contract: before that client's own fix) and searches it for the requirement. Web documentation comes from
Internet Archive snapshots (URLs in the JSON); library documentation from the docstrings shipped in old releases
(installed in `envs/`); POSIX and docs.rs pages by edition or version. The earliest snapshot is the first snapshot of the
earliest year that already states the requirement (one snapshot is checked per year).

| Case | Anchor | Dated version checked | Earliest snapshot stating it | Earliest fix of the case | Stated before the fix? |
|---|---|---|---|---|---|
| GC1 | pyarrow delete_dir docstring | 2021-01-26 | – | Arrow fix, Dec 2023 (s3fs: Feb 2026) | yes |
| GC1 | fsspec rm(recursive) docstring | 2021-06-07 | – | Arrow fix, Dec 2023 (s3fs: Feb 2026) | yes |
| GC1 | S3: console folder = zero-byte object with trailing '/' | 2023-11-07 | 2023-01-27 | Arrow fix, Dec 2023 (s3fs: Feb 2026) | yes |
| GC1 | S3 DeleteObjects: missing key reported as deleted | 2023-10-29 | 2021-01-10 | Arrow fix, Dec 2023 (s3fs: Feb 2026) | yes |
| GC2a | S3: key uniquely identifies the object; user specifies it | 2021-04-13 | 2021-01-21 | s3path fix, Jun 2021 (gcsfs Oct 2022; obstore Aug 2025) | yes |
| GC2a | S3 (older URL): key uniquely identifies the object | 2021-01-23 | 2014-02-10 | s3path fix, Jun 2021 (gcsfs Oct 2022; obstore Aug 2025) | yes |
| GC2a | GCS: special characters in object names must be encoded in URLs | 2021-05-07 | 2020-04-24 | s3path fix, Jun 2021 (gcsfs Oct 2022; obstore Aug 2025) | yes |
| GC2b | S3 CopyObject: copy source must be URL-encoded | 2021-04-18 | 2019-10-17 | Arrow fix, Jun 2021 (obstore: Apr 2026) | yes |
| GC3 | POSIX pathname resolution (2018 edition) | 2018-01-01 | – | cloudpathlib fix, Aug 2022 (OpenDAL: Aug 2024) | yes |
| GC3 | S3: folders are shared prefixes ending in the delimiter | 2022-06-26 | 2021-02-12 | cloudpathlib fix, Aug 2022 (OpenDAL: Aug 2024) | yes |
| GC3 | pathlib is_dir (followed by cloudpathlib) | 2022-08-08 | 2014-03-24 | cloudpathlib fix, Aug 2022 (OpenDAL: Aug 2024) | yes |
| GC3 | OpenDAL: directory paths end with '/' (own contract, before its fix) | – | – | cloudpathlib fix, Aug 2022 (OpenDAL: Aug 2024) | not archived (see next row) |
| GC3 | OpenDAL docs.rs 0.45.0 (own contract, before its fix) | 2024-02-05 | – | cloudpathlib fix, Aug 2022 (OpenDAL: Aug 2024) | yes |
| PV1 | pathlib rename/rmdir act on the named path | 2025-12-31 | 2014-03-24 | prospective (2026) | yes |
| contested | pathlib iterdir excludes '.' (directory itself) | 2021-05-27 | 2021-01-01 | s3path change, 2021 | yes |

Every Golden-Case anchor is stated in a version older than the earliest fix of its case. The one exception is OpenDAL's
own contract: it is stated before OpenDAL's fix, and the earlier GC3 fix is covered by POSIX, the S3 folder convention and
pathlib. OpenDAL's website was never archived before the fix; its versioned 0.45.0 documentation on docs.rs (crate
published 2024-02-05) states it: "If you do want to list a dir, please make sure the path is end with /".

Quotes, as matched in the dated versions, are in the JSON (`quote`).
