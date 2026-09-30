# Independent adjudication of rule identity (about 1.5–2 hours)
**Who:** someone who did NOT derive the probes, for example the co-author or a mentor. Do not look at the paper's
Table 3 or §5, or at any file outside this folder, until you have finished.

## Task
`pairs/` holds 17 pairs of historical fix discussions (issue and pull-request text). Library and project names are
replaced by `[LIB]`. For each pair `Pxx`, read `Pxx_A.txt` and `Pxx_B.txt` and decide:

- **same**: both discussions are about violating and then fixing the *same behavioral rule*, i.e. the same observable
  requirement on what the software must do, even if the code, language or mechanism differs;
- **different**: they concern different requirements, even if the topic is similar;
- **ambiguous**: you cannot decide from the text.

In `answers.csv`, for each pair write the verdict (`same`, `different` or `ambiguous`), the rule(s) in one sentence,
and the minutes spent. Work alone, without searching the web for the projects.

## After finishing
Send `answers.csv` back. The scoring is:

```bash
python3 evidence/adjudication/score.py evidence/adjudication/answers.csv adjudication_KEY_do_not_open.json
```

It reports agreement with the study's classification and Cohen's κ, and lists every disagreement.
