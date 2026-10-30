# Fast competition resume

Resume no longer repeats the entire payload audit for unchanged fights or reloads
finished conversations just to discover that they have already submitted.

- Tournament schedule extension uses a match-ID lookup rather than a quadratic
  scan of the existing fixture list.
- Journal references to the same artifact share one digest check.
- File checks use a bounded pool of eight I/O workers. SQLite and progress writes
  stay on the coordinator; this pool does not cap simultaneous engine fights.
- A derived `.verification-cache.sqlite` stores verified hashes, compact record
  data and validation receipts. It is disposable, not competition evidence.
- Reuse checks file identity, size, modification time and filesystem change time.
  Windows uses NTFS `ChangeTime`, not the creation-time value historically exposed
  as `st_ctime`. Missing change-stamp support falls back to content hashing.
- Fight receipts also bind the exact result, submissions, scenario configuration,
  engine provenance and source directory structure. A changed file, new/deleted
  source, changed binding or replaced file invalidates the applicable receipt.
- A journal session proof pairs the verified checkpoint digest with digests of the
  exact SQLite state and metadata-index bytes. Changes to either still require
  the full semantic comparison. Unchanged histories need not be decoded again.
- Unchanged final compilation assessments are not appended again. Match evidence,
  worker-setting events and competition runtime-update events can be appended
  without rewriting a frozen conversation checkpoint or resetting its counters.

New fights prepare these receipts while their results are validated. An old study
without receipts needs one initial audit to build them. Changed files and new
fixtures are still checked on every resume. The cache contains no open persistent
SQLite connection and does not prevent cleanup on Windows. Copying a study to
another filesystem invalidates the applicable file-identity checks automatically.
A missing/unusable cache falls back to verification from the actual artifacts.

Validation receipts now store the identity of the engine that actually produced
each result. Adding an accepted compatible runner version no longer invalidates
all earlier receipts just because the accepted-version list changed. Removing an
accepted engine or changing a result, source, scenario or replay still invalidates
the relevant proof. Old receipt formats are upgraded once; unchanged file hashes
remain reusable during that conversion. Reference checks also consult a valid
receipt before reopening source bodies, and historical replays are not copied
into cache entries for a different runner identity.

## Measurements

A synthetic archive had the same 35 submissions, six seeds, 7,350 scheduled fights
and self-play layout as the reported competition. It contained about 1.5 GB of
logical replay payloads, implemented with shared fixture files. It was measured on
Linux with a warm filesystem cache, so it is not a prediction of Windows disk or
antivirus performance.

| Measurement | Seconds |
|---|---:|
| Previous resume verification | 24.64 |
| First audit and cache construction | 30.11 to 35.15 |
| Subsequent cached resume, repeated observations | 4.32 to 6.84 |

The warm pass checked all 7,350 receipts and read no replay payloads. The first
conversion costs more because it builds the derived index. A completed two-round
153-fight experiment also resumed in about one second with provider and engine
calls explicitly forbidden, identical submissions/usage counters and no duplicate
final assessments. Separate checks rejected replay edits with preserved size and
mtime, added source files, modified SQLite states and modified metadata indexes.
A real JDK 25 tournament retained identical results and resumed without new fights.

## Inspect or force verification

**Copy scheduling diagnostics** includes `resume_performance` and
`fight_verification`: phase durations, unchanged receipts, computed digests and
bytes read. Activity shows the actual journal/fight check counts as they advance.
The files are `resume-performance.json` at the competition root and
`verification-performance.json` in each tournament directory.

For a fresh content audit regardless of the derived cache, set
`ARENA_FULL_AUDIT=1` before starting the application or CLI. This bypasses cached
hashes, records, fight receipts and session proofs; normal scheduling and results
are unchanged. The cache can also be removed while the competition is stopped;
it will be rebuilt from the original records. Derived rows have their own
checksums; damaged cache data are discarded rather than reported as lost fights.
Completed rounds release their bulky in-memory receipts after persistence, so
resume acceleration does not require keeping all historical metadata in RAM.
