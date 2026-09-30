# Probe catalog (frozen battery; oracle/FROZEN_v1.sha256)

| # | probe | family | derived from |
|---|---|---|---|
| 1 | `F1_ls_boundary` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 2 | `F1_find_boundary` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 3 | `F1_info_a_is_dir` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 4 | `F1_info_ab_is_file` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 5 | `F1_info_prefix_notfound` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 6 | `F1_delete_boundary` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 7 | `F1_stat_string_prefix_notfound[very/similar/prefix]` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 8 | `F1_stat_string_prefix_slash_notfound[very/similar/prefix]` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 9 | `F1_stat_string_prefix_notfound[very/similar/prefi]` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 10 | `F1_stat_string_prefix_slash_notfound[very/similar/prefi]` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 11 | `F1_stat_string_prefix_notfound[very/similar/prefix3/some]` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 12 | `F1_stat_string_prefix_slash_notfound[very/similar/prefix3/some]` | F1 | segment boundary — s3fs test_same_name_but_no_exact; cloudpathlib #208; OpenDAL #2086/#4959 |
| 13 | `F3_ls_names_exact` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 14 | `F3_read[sp ace]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 15 | `F3_read[pl+us]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 16 | `F3_read[per%25cent]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 17 | `F3_read[pct%]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 18 | `F3_read[hash#]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 19 | `F3_read[q?mark]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 20 | `F3_read[eq=1]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 21 | `F3_read[tilde~]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 22 | `F3_read[café]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 23 | `F3_read[semi;colon]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 24 | `F3_read[amp&]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 25 | `F3_read[colon:x]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 26 | `F3_read[star*]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 27 | `F3_read[brack[1]]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 28 | `F3_write_key_exact[sp ace]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 29 | `F3_write_key_exact[pl+us]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 30 | `F3_write_key_exact[per%25cent]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 31 | `F3_write_key_exact[pct%]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 32 | `F3_write_key_exact[hash#]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 33 | `F3_write_key_exact[q?mark]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 34 | `F3_write_key_exact[eq=1]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 35 | `F3_write_key_exact[tilde~]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 36 | `F3_write_key_exact[café]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 37 | `F3_write_key_exact[semi;colon]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 38 | `F3_write_key_exact[amp&]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 39 | `F3_write_key_exact[colon:x]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 40 | `F3_write_key_exact[star*]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 41 | `F3_write_key_exact[brack[1]]` | F3 | key round-trip put/get — s3path #77; gcsfs #447/#270; obstore #496/#524 |
| 42 | `F4_ls_1105` | F4 | pagination (files) — all clients' listing code |
| 43 | `F4_find_1105` | F4 | pagination (files) — all clients' listing code |
| 44 | `F6_ls_slash_eq` | F6 | trailing-slash equivalence — Arrow/OpenDAL trackers |
| 45 | `F6_info_slash_eq` | F6 | trailing-slash equivalence — Arrow/OpenDAL trackers |
| 46 | `F7_marker_is_dir` | F7 | marker-only directories; self-entry — s3fs #300; Arrow GH-36983/GH-37555; OpenDAL #4959 |
| 47 | `F7_root_lists_marker_dir` | F7 | marker-only directories; self-entry — s3fs #300; Arrow GH-36983/GH-37555; OpenDAL #4959 |
| 48 | `F7_ls_marker_dir_empty` | F7 | marker-only directories; self-entry — s3fs #300; Arrow GH-36983/GH-37555; OpenDAL #4959 |
| 49 | `F7_ls_dir_excludes_own_marker` | F7 | marker-only directories; self-entry — s3fs #300; Arrow GH-36983/GH-37555; OpenDAL #4959 |
| 50 | `F2_move_dir_complete` | F2 | directory move with markers — s3fs #918 family |
| 51 | `F3b_copy[eq=1]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 52 | `F3b_move[eq=1]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 53 | `F3b_copy[pl+us]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 54 | `F3b_move[pl+us]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 55 | `F3b_copy[sp ace]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 56 | `F3b_move[sp ace]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 57 | `F3b_copy[pct%]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 58 | `F3b_move[pct%]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 59 | `F3b_copy[café]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 60 | `F3b_move[café]` | F3b | key round-trip copy/rename — Arrow GH-28758 (ARROW-13048); obstore #671 |
| 61 | `F8_stat_missing` | F8 | stat of missing path — OpenDAL #2086 |
| 62 | `F8_stat_missing_slash` | F8 | stat of missing path — OpenDAL #2086 |
| 63 | `F9_delete_dir_with_double_slash_key` | F9 | double slash in keys — Arrow GH-38821 |
| 64 | `F10_zero_byte_is_file` | F10 | zero-byte object is a file — Arrow GH-36983 discussion |
| 65 | `F11_ls_dir_with_space` | F11 | spaces/plus in directory names — object_store #223 |
| 66 | `F11_find_dir_with_space` | F11 | spaces/plus in directory names — object_store #223 |
| 67 | `F11_ls_dir_with_plus` | F11 | spaces/plus in directory names — object_store #223 |
| 68 | `F14_file_is_file` | F14 | file/directory type exclusivity — pathlib contract |
| 69 | `F14_implicit_dir_is_dir` | F14 | file/directory type exclusivity — pathlib contract |
| 70 | `F14_bucket_root_is_dir` | F14 | file/directory type exclusivity — pathlib contract |
| 71 | `F13a_rmdir_nonempty_keeps_contents` | F13 | rmdir semantics — s3path #205 |
| 72 | `F13b_rmdir_nonempty_implicit_keeps_contents` | F13b | rmdir semantics — s3path #205 |
| 73 | `F13c_rmdir_empty_marker_removes_it` | F13 | rmdir semantics — s3path #205 |
| 74 | `F15_move_dir_complete[markers]` | F15 | directory move completeness — s3fs/gcsfs move with markers |
| 75 | `F15b_move_dir_sibling_untouched[markers]` | F15b | directory move boundary — gcsfs #576; fsspec #1340 |
| 76 | `F15_move_dir_complete[implicit]` | F15 | directory move completeness — s3fs/gcsfs move with markers |
| 77 | `F15b_move_dir_sibling_untouched[implicit]` | F15b | directory move boundary — gcsfs #576; fsspec #1340 |
| 78 | `F16_copy_dir_boundary` | F16 | directory copy — gcsfs #576 |
| 79 | `F16b_copy_dir_sibling_not_copied` | F16b | directory copy boundary — gcsfs #576; fsspec #1340 |
| 80 | `F4b_ls_1105_subdirs` | F4b | pagination (common prefixes) — all clients' listing code |
| 81 | `F17_file_with_trailing_slash_not_file` | F17 | trailing slash on a file — Arrow GH-20316 |
| 82 | `G1_glob_star_one_level` | G | glob basics — s3path #160; cloudpathlib #311/#312 |
| 83 | `G2_glob_doublestar_recursive` | G | glob basics — s3path #160; cloudpathlib #311/#312 |
| 84 | `G3_glob_prefix_boundary` | G | glob basics — s3path #160; cloudpathlib #311/#312 |

Recursive-deletion oracle (oracle/f2_delete_oracle.py; Arrow GH-38618, s3fs #918): world variants v-top, v-nested,
v-emptysub, v-full, v-implicit; assertions A_nothing_under_d (rule) and B_sibling_prefix_survives (segment-boundary control).