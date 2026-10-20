# AI log

What AI (Claude Code) generated in this project, what was wrong with it, and what a human changed.

**Working model:** Claude generates SQL, specs, and tests. The human reviews and validates, and makes every judgement call. Each generated artifact gets proof before it's accepted: cross-checks with independently shaped queries, negative controls, and live probes of the platform instead of recalled API knowledge.

## Defect summary

| # | Phase | Artifact | Defect | Caught by | Fix |
|---|---|---|---|---|---|
| 1 | 1 | `sql/profiling/rental_payment_profile.sql` | `UNION ALL` result sets had no `ORDER BY`, so row order was arbitrary and run-to-run diffs would be noisy | Reading the output | Added `ORDER BY` to every result set |
| 2 | 1 | Orphan negative control (ad hoc) | Planted-row test inside a rolled-back transaction still advanced `rental_rental_id_seq` (87559 → 87560), because sequences aren't transactional | Checking side effects after the run | Disclosed; noted for any sequence-value checks |
| 3 | 2 | `fulltext` derivability check (ad hoc) | Used weighted `setweight(...)` formula; matched 0/1000 rows and would have wrongly suggested tsvector was not derivable | Reading the source trigger definition | Re-ran with the trigger's actual formula; 1000/1000 match |
| 4 | 2 | Snowflake type assumptions (recall) | Recalled knowledge said Snowflake has no UUID type, no generated columns, and enforces only NOT NULL. All three are out of date | Docs check, then live probe in the account | Spec uses native `UUID`, a virtual column, and offers `CHECK` |
| 5 | 2 | Virtual column DDL probe | `NUMBER(4,2) AS (ROUND(...))` failed: Snowflake requires the expression type to match exactly, unlike Postgres | Live probe | Spec expression casts: `::NUMBER(4,2)` |
| 6 | 2 | `mapping/type_mapping.yml` | Plain YAML scalar contained `": "`, so the file did not parse | First test run | Reworded; scanned the file for other instances (none) |
| 7 | 2→3 | D08 recommendation (`CHECK`) | Recommended CHECK constraints after probing only `INSERT`. Snowflake rejects `COPY INTO` on tables with CHECK constraints, so `film` failed to load | First real load | Human chose to keep D08; loader lands CHECK tables in a temporary table, then `INSERT`s |
| 8 | 3 | `src/migrate/load.py` (draft) | argparse `choices=[[], ...]` hack, a magic number for psycopg's in-error transaction state, and an internal connector type path | Self-review before first run | Explicit table validation, `TransactionStatus.INERROR`, public import paths |
| 9 | 3 | Verification commands (ad hoc) | Passed `-c` to `sh` instead of `psql` (psql waited on stdin until timeout); used reserved word `rows` as a Snowflake alias | Hang, then a syntax error | Corrected; no effect on project files |
| 10 | 4 | MIG-006 requirement and test | Defined as "the latest run covers every table", which fails after any legitimate partial reload | The test failed on the human's partial `film payment` run | Redefined: each table's most recent load succeeded; requirement and test changed together |
| 11 | 4 | `src/reconcile/aggregates.py` (draft) | Applied `COLLATE "C"` to the `mpaa_rating` enum (an error), and the enum would have ordered by declaration, not alphabetically | First run | Non-text sources that land as text are compared as `::text COLLATE "C"` |
| 12 | 5 | `src/faults/inject.py` fingerprint (draft) | Hashed `GET_DDL`, which a clone reorders, so a correctly restored `FILM` looked unrestored | Apply/restore round trip | Structure is now fingerprinted from `DESC TABLE` and the PK columns |
| 13 | 4→5 | `src/reconcile/rowhash.py` diff | Loaded rows into `{key: hash}` dicts, so duplicate target rows collapsed and MIG-005 ("no extra rows") passed with 2 duplicated rentals | Fault matrix (`duplicate_rows`); predicted before the run | Diff takes row lists and reports duplicated keys per side; unit tests added |
| 14 | 4→5 | Vector normalization | 6-decimal rounding was over-conservative; a 1e-7 drift went undetected | Fault matrix (`tiny_vector_drift`) | Probe showed 9 decimals gives 0 false mismatches on 1,000 real embeddings and catches the drift; switched to 9 |

## Phase 1: Source profiling

- **Generated:** the rental/payment profiling SQL (null rates, ranges, key uniqueness, orphaned FKs).
- **Validation:**
  - Every number matched a second query of a different shape (`IS NULL`, `ORDER BY ... LIMIT 1`, `GROUP BY ... HAVING`, `LEFT JOIN` anti-join).
  - A planted orphan was detected.
  - Partition counts summed to the parent count.
- **Human change:** the human decided to drop the hand-written exercises. AI generates and the human validates (see "Working model").

## Phase 2: Mapping spec

- **Generated:** `mapping/type_mapping.yml` (16 tables, 94 columns, 8 excluded views) and `tests/test_mapping_spec.py`.
- **Validation:**
  - Every target type was created in a scratch table in this account, and its `DESC TABLE` string was copied into the spec.
  - The coverage tests were mutation-checked: a dropped column, a changed source type, and a dropped view were each caught.
- **Decisions:** the human reviewed D01–D09 on 2026-10-20 and accepted all nine AI recommendations unchanged. The rationale for each is in the spec's `decisions:` block.
- **Follow-up from D08:** making "check" actionable needed the constraint expressions in the spec. A `check` field was added to `film.release_year` and `film.rating`. Both were probed in Snowflake: valid values and NULLs were accepted, out-of-range values rejected.

| Decision | AI recommendation | Human decision |
|---|---|---|
| D01 timestamptz | `TIMESTAMP_TZ(6)` | Accepted |
| D02 `text[]` | `ARRAY` | Accepted |
| D03 tsvector | exclude | Accepted |
| D04 vector(20) | `VECTOR(FLOAT, 20)` | Accepted |
| D05 virtual column | virtual | Accepted |
| D06 views | exclude | Accepted |
| D07 uuid | `UUID` | Accepted. Revisit if dbt or Soda can't handle the type |
| D08 domain/enum | `CHECK` | Accepted |
| D09 staff.password | migrate | Accepted. Flagged sensitive; record as a waiver at sign-off |

## Phase 3: Migration loader

- **Generated:** `src/migrate/ddl.py` (DDL from the spec), `src/migrate/load.py` (extract → Parquet → PUT → COPY, with `QA.LOAD_LOG`), and `tests/test_loader.py`.
- **Probes before design.** I wrote a Parquet file with every target type and read it in Snowflake three ways. Three hazards that recalled knowledge wouldn't have predicted:
  - The default Parquet scanner decodes binary as UTF-8 and fails on non-text bytes, so the loader uses `USE_VECTORIZED_SCANNER = TRUE`.
  - Parquet timestamps arrive as `TIMESTAMP_LTZ`. With the account's default `America/Los_Angeles` session, a cast to `TIMESTAMP_TZ` stores `-08:00` offsets, so every project connection sets `TIMEZONE = 'UTC'`.
  - A Parquet list won't cast straight to `VECTOR`, so the loader goes through `::ARRAY::VECTOR(FLOAT, 20)`.
- **Validation:**
  - Spot values and aggregates matched Postgres: payment sum, distinct UUIDs, microseconds, `Z` offsets, float32 embeddings, the virtual column sum, array order.
  - The CHECK constraint rejected a bad rating after loading.
  - Idempotency: per-table `COUNT(*)` and `HASH_AGG(*)` were identical before and after a re-run.
- **Human decision:** keep D08 and load `film` through a landing table (see defect 7).

## Phase 4: Reconciliation suite

- **Generated:**
  - `requirements/requirements.yml` (MIG-001 to MIG-009, plus known source issues SRC-001 to SRC-004)
  - the `req` marker plumbing with a per-requirement summary
  - schema, volume, aggregate, row-hash, and integrity tests
  - the hand-written `payment` row-hash pair and the generator
  - Soda contracts for 4 tables
- **Probes before design:**
  - Formatting functions produced identical text on both engines.
  - Snowflake turns the literal `'\N'` into `N`, so the hash uses a presence flag instead of a null token.
  - Snowflake rewrites virtual column expressions (`60.0` became `SCALED_ROUND_INT_DIVIDE(LENGTH, 60)`), so schema parity checks the kind and the data layers check the values.
- **Validation:**
  - A planted FAILED load-log row failed MIG-006.
  - Dropping one film row produced 15 aggregate differences.
  - Without `COLLATE "C"`, 3 text columns would have given false failures.
  - The row-hash pair caught a missing and a changed payment by key.
  - The generator reproduces the hand-written hashes on both sides.
  - 11 row-hash mutations behaved as predicted, including 3 deliberate non-detections: a vector change under 1e-7, the same instant at a different offset, and UUID case.
  - Unknown requirement IDs fail collection.
  - A broken FILM copy failed exactly the 4 contract checks it should.
- **Differs from the brief:** Soda Core open source has no source↔target reconciliation; it needs the licensed `soda-reconciliation` package. The human chose contracts only, with reconciliation staying in pytest.
- **Found in the source:** `store.manager_staff_id` has no declared FK, and 499 of 500 managers belong to another store (SRC-004).

## Phase 5: Fault injection

- **Generated:**
  - `src/faults/` with 12 faults: the brief's 7, plus orphan FK, trailing whitespace, microsecond truncation, a dropped CHECK, and sub-tolerance vector drift
  - an apply/restore CLI with zero-copy clone backups
  - a matrix runner that maps failures to layers through requirement IDs in JUnit XML
- **Pre-registered predictions** were written down before the first run. All 12 rows matched, including both misses.
- **First run: 11/12.**
  - Missed `tiny_vector_drift`: vector tolerance too loose (defect 14).
  - The row layer was blind to `duplicate_rows`: dict collapse (defect 13).
- **Human decision:** fix the row-layer duplicates and tighten vectors to 9 decimals. Declined: a Soda email-completeness rule (a business rule, not a migration fact) and an expected-catch gate on the matrix.
- **Re-run: 12/12.** Every restore was verified by fingerprint.
- **Coverage notes:**
  - `swap_fk_values` and `trailing_whitespace` are caught only by the row layer.
  - The Soda contracts catch only duplicates.
  - The process layer can't see post-load corruption.
  - Faults run one at a time, so masking combinations are untested.
