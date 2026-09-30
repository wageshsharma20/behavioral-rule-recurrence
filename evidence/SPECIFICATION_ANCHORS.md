# Specification anchors of the Golden-Case rules (paper §5.1, "Correctness, not a design decision")
Current versions retrieved 1 Oct 2026. For versions dated before each fix, see `SPEC_HISTORY.md`. Every quote is short and verbatim; the URLs point to the sources. These specifications were
written independently of the fixes studied.

| Rule | Independent specification | Quote |
|---|---|---|
| GC1 recursive delete removes directory markers | pyarrow.fs.FileSystem.delete_dir (https://arrow.apache.org/docs/python/generated/pyarrow.fs.FileSystem.html) | "Delete a directory and its contents, recursively." |
| GC1 | fsspec AbstractFileSystem.rm (https://filesystem-spec.readthedocs.io/en/latest/api.html) | "Delete files or directories"; with `recursive=True`, directories are deleted with their contents |
| GC1 (what a marker is) | AWS S3 User Guide, folders (https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-folders.html) | the console "creates a 0-byte object with the key `photos/`" for folder `photos` |
| GC2a/GC2b keys equal the user's string | AWS S3 User Guide, naming objects (https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html) | "The object key (or key name) uniquely identifies the object … When you create an object, you specify the key name." |
| GC2a/GC2b | AWS CopyObject (https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html) | x-amz-copy-source: "The value must be URL-encoded." |
| GC2a (gcsfs, `#`) | GCS request endpoints (https://cloud.google.com/storage/docs/request-endpoints) | encode "#" (among others) "when they appear in either the object name or query string of a request URL" |
| GC3 foo is not a directory because foobar exists | POSIX IEEE Std 1003.1-2024, §4.16 Pathname Resolution (https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap04.html) | "Each filename in the pathname is located in the directory specified by its predecessor" |
| GC3 | AWS S3 User Guide, folders | a folder is a shared name prefix; the console shows prefixes ending in the delimiter `/` as folders |
| GC3 | GCS objects (https://cloud.google.com/storage/docs/objects) | tools "interpret the slash (`/`) character in an object's name as a delimiter, in order to simulate folders" |
| GC3 (OpenDAL) | OpenDAL Operator docs (https://opendal.apache.org/docs/rust/opendal/struct.Operator.html) | "To specify that a path is a directory, you must include a trailing slash (/)." |
| PV1 rename/rmdir act on the named directory only | Python pathlib (https://docs.python.org/3/library/pathlib.html), followed by cloudpathlib ("mimic pathlib.Path's interface") and s3path ("Like pathlib, but for S3 Buckets") | `Path.rename`: "Rename this file or directory to the given target … implemented in terms of os.rename() and gives the same guarantees"; `Path.rmdir`: "Remove this directory." |
| PV1 | POSIX rename() (https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html) | "The rename() function shall change the name of a file." |

## Contested rule: the specifications disagree
Does listing directory d return d's own marker?

| Specification | Says | Implementations following it |
|---|---|---|
| Python pathlib `Path.iterdir` | "the special entries '.' and '..' are not included" (the directory itself is not listed) | s3path (changed 2021) and cloudpathlib (changed 2022) exclude it |
| OpenDAL `list` | "If `path` itself exists (file or dir), it will be returned as an entry in addition to any prefixed children." | OpenDAL (changed 2024) includes it |

Because the interfaces' own specifications decide this in opposite ways, each direction is a documented design decision.
The study therefore classifies the rule as contested, not as a violation.
