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
| 15 | 6 | `mart_rental_returns.sql` (first build) | Output timestamps kept each input's UTC offset, violating "all dates are UTC" (same instant, different representation) | My own unit test's non-UTC fixture row | `CONVERT_TIMEZONE('UTC', ...)` on mart timestamps, also in the CLV mart |
| 16 | 6 | `assert_late_fee_matches_basis.sql` (draft) | Correlated subquery in a JOIN condition (unsupported in Snowflake), and a loose `<= 2 x duration + 1` bound | `dbt build` error, then self-review | Plain joins; exact `between 1 and 2 x duration` bound |
| 17 | 6 | Phase 0 dependency choice | Picked `snowflake-connector-python` 5.0 without checking downstream adapters; dbt-snowflake 1.12 requires < 5.0 | `uv add dbt-snowflake` resolution failure | Human chose to pin 4.x; dropped the 5.0-only option; full reload and suite re-run first |
| 18 | 7 | dq-triage agent, trial 3 | Stated that RAW.RENTAL has no primary key without checking; it has `RENTAL_PK` (declared, not enforced). Root cause also contradicted its own evidence (blamed a load retry although LOAD_LOG's count showed the extra rows arrived after the load) | Blind-test scoring against ground truth | Recorded; scored 1/2 on root cause. Pattern to watch: confident, plausible, unverified claims |
| 19 | 7 | AI-generated SQL, ETL-006 | Boundary diagnostics used `DATEDIFF('second')`, which counts boundaries crossed: 1 day + 0.8 s late reads as exactly 1 day. Latent: correct on today's data (12 = 12), wrong by construction; the agent's own self-consistency query used microseconds | Claude review, literal-value probe; confirmed by human | Logged; `reports/ai_sql_review.md` finding A |
| 20 | 7 | AI-generated SQL, ETL-002 | `c1` checksum weights payment_count by month only, with no store term, so counts moved between stores in a month go unnoticed | Claude review; confirmed by human | Logged; finding B |
| 21 | 7 | AI-generated SQL, ETL-002 | Skipped the acceptance criterion comparing store totals with the legacy `sales_by_store` view (the agent disclosed this) | Claude review; confirmed by human | Logged; finding C |
| 22 | 7 | AI-generated SQL, all three | Aggregate fingerprints instead of row-level comparison; offsetting errors pass (the agent flagged this, citing the 200-row tool cap) | Claude review; confirmed by human | Logged; finding D |
| 23 | 7 | AI-generated SQL, MIG-004 | The SQL it delivered was abbreviated (`UNION ALL ...`), so it can't be reviewed or reused as delivered | Claude review; confirmed by human | Logged; finding E |
| 24 | 7 | `src/reconcile/summarize.py` fact check (first version) | Checked requirement IDs and tables only; a Cortex summary that misattributed metrics to `payment_date` passed | Claude's close reading of a passing summary | Added an invented-number check; docstring states the check can't judge wording |
| 25 | 3 | `src/migrate/load.py` `migrate_table` | Caught only database errors; an Arrow or file error while building the Parquet extract crashed the run without a FAILED `LOAD_LOG` entry, leaving the previous SUCCESS as the latest | Codex review on PR #1 | Arrow and OS errors go through the same logging path; 2 unit tests, which fail with the old handler |
| 26 | 7 | `src/reconcile/record.py` | Recorded only `tests/reconciliation` and `tests/etl`, so MIG-001 (in `tests/test_mapping_spec.py`) never reached `QA.RECON_RESULTS`; a failing run could be stored and summarized as clean | Codex review on PR #1 | Records the whole suite; verified 17/17 requirements covered |
| 27 | 7 | `docker/init/03-triage-role.sh` | Hard-coded the `dq_triage` role while the query tool logs in as `$TRIAGE_PGUSER`, so the documented setting couldn't actually be changed | Codex review on PR #1 | Uses `TRIAGE_PGUSER`, quoted as an identifier; tested with a name that needs quoting |
| 28 | 6→7A | `monthly_revenue_rules` unit test | Fixture payment amounts (5.00, 0.00, 2.00) are all distinct, so a `SUM(DISTINCT amount)` bug passes the unit test; only the data test `assert_revenue_attributes_every_payment` caught it | dbt mutation baseline (`rev_sum_distinct`); predicted before the run | Logged; left as-is so the baseline the agents are compared against stays fixed |
| 29 | 7A | `src/faults/dbt_mutations.py` report (first run) | Took the last segment of dbt unique IDs, which for generic tests is a hash (`f5f1497056`) | Reading the generated report | `node_name()` takes the test name before the hash; report regenerated |
| 30 | 6 | `mart_rental_returns.sql` (Claude-written) | `ceil(micros_after_due / 86400000000)` loses precision: Snowflake keeps 6 decimal places in that quotient, so a return up to ~43 ms past a day boundary isn't counted (1 µs late gave 0 days; 1 day + 43 ms gave 1). Latent: 0 real rentals affected, so the unit tests, data tests, the Postgres re-implementation, and all 16 mutations missed it | `dbt-test-author` agent's 1 µs-late fixture row, in a blind run | Exact integer arithmetic (`(m - mod(m, D)) / D + iff(mod(m, D) > 0, 1, 0)`); added as mutation 17 `rr_ceil_decimal_division` |
| 31 | 7B | `dbt-test-author` proposals | Two "independent" recompute tests mirror the model in the same dialect (same joins, `CONVERT_TIMEZONE`/`DATE_TRUNC`; `TIMESTAMPADD` is a synonym of `DATEADD`), so a misread rule would be copied rather than caught. A replacement-fee consistency check is loose (`late_fee > 0`; the exact check exists in another test). Its report said 8 singular tests; it wrote 9 | Claude review | Logged; considered when deciding what to promote |
| 32 | 7C | `migration-check-author` proposals | `COALESCE(MIN(x), '')` makes an all-NULL column look like an empty string in min/max (the adjacent `null_count` still tells them apart); single-row count files have no `ORDER BY` (harmless); never ran a negative control (it said so) | Claude review; fault matrix | Logged; low severity |
| 33 | 4 | `src/reconcile/rowhash.py` and the hand-written payment pair (Claude-written) | Commented as "collision-free", but it joined `'1' || value` with only a separator: two different rows, (`'a'`, `'b␟1c'`) and (`'a␟1b'`, `'c'`), hashed identically (`c9480605…`) on both engines. Latent: no Pagila value contains `chr(31)` | `migration-check-author`'s length-prefixed design, then a counterexample run on both engines | Values encode as `1 || length || ':' || value`; generator and hand-written pair updated; checklist rule added |
| 34 | 7D | `rule-reviewer` review | Finding 3 labels its two readings of "more than 2x overdue" confusingly and never counts the reading the rule literally states (194 rentals overdue by more than 2x), although that's one query; it raised the timestamp-vs-calendar late threshold but not the exactly-at-due boundary (2 rentals) | Claude scoring against the answer key | Logged; the agent itself said finding 3 was confusingly worded |
| 35 | 7B | `src/triage/dbt_check.py` (Claude-written) | Overlaid every proposal file except `*.md` and ran dbt with the full environment, so a proposal could ship its own `profiles.yml` or macro, or reach the writable `SNOWFLAKE_PRIVATE_KEY_PATH`, and turn the "read-only" check into writes as `PAGILA_SVC` | Codex review on PR #2 (P1) | Only `models/**/*.yml` and `tests/**/*.sql` are overlaid, anything else is rejected by name; the profile always comes from this repo; writable key paths are withheld. 5 planted proposals: profile, macro, and model SQL rejected; a `run_query` CREATE TABLE blocked by the role; an env probe shows the key withheld (and fails with withholding off) |
| 36 | 7C | `src/triage/check_pair.py` `run_pair` | Caught only `SystemExit`, but the query helpers raise raw `psycopg` / Snowflake errors, so one pair with a SQL error aborted the whole run and `pair_matrix` | Codex review on PR #2 | Database errors fail that pair only; control: a broken pair on each side, the good pair still runs |
| 37 | 7C | `src/faults/pair_matrix.py` | Checked the fingerprint only after restore, so a fault that changed nothing was scored as **MISSED** and counted in the denominator; `faults.matrix` already handled this | Codex review on PR #2 | Fingerprint after apply; no-ops are reported as not applied and not scored; control: a no-op fault next to `drop_rows` |
| 38 | 7A | `src/faults/dbt_mutations.py` `dbt()` | Ignored dbt's exit code and reused `target/run_results.json`, so a crashed pass read the previous pass's results or none, and the mutation scored as SURVIVED (or as killed by stale failures) | Codex review on PR #2 | Results are deleted before each pass; exit code other than 0/1 or no results is an invalid run, not scored; control: a Jinja-crash mutation reported invalid; full re-score still 17/17 |
| 39 | 7B-7D | `.claude/agents/` author agents | Hard-coded `/Users/chet/...` in every tool command, so the agents fail on any other checkout or clone | Codex review on PR #2 | Relative `uv run --env-file .env`, run from the repository root, as `dq-triage` already did |
| 40 | 8 | `src/reconcile/signoff.py` first report | Printed "all made by the human" for the mapping decisions without counting them, and linked evidence as `../reports/x.md` from inside `reports/` | Reading the first generated report | Decisions are counted by status; links are relative to the report |
| 41 | 4 | `tests/reconciliation/conftest.py` (Claude-written) | Its `pytest_collection_modifyitems` marked every collected item, not just that directory's, so all 164 tests were `target_db` and `-m "not target_db"` selected none. Latent until something filtered on the markers | Running the planned PR selection with Snowflake unreachable: 164 deselected | Marks only tests under its own directory; 29 run without Snowflake |
| 42 | 8 | `.github/workflows/ci.yml` draft | Created the service container's superuser as `pagila`, but the Pagila dump assigns ownership to `postgres` (106 `OWNER TO postgres`), so the source load would fail in CI | Replica of the CI job: a fresh container loaded the same way | Superuser `postgres`, as in the local `.env`; replica loads 51,061 payments and passes 29/29 |
| 43 | 8 | `src/reconcile/signoff.py` gate | Judged only requirement status, so a failing test with no requirement (e.g. in `tests/test_loader.py`) was listed in the report while the gate said GO and exited 0, the only pass/fail step in the full CI run | Codex review on PR #3 (P1) | New gate G5: every untraced pytest and dbt test passes; no waiver can cover them. Control: a planted failing untraced test gives G5 NOT MET, exit 1 |
| 44 | 8 | `src/reconcile/signoff.py` G1 | A requirement whose only tests were skipped counted as "covered by a test that ran"; with a waiver it could pass G1 and G2 with nothing executed | Codex review on PR #3 | Skipped-only traces are uncovered; unit test with a waived, skipped-only requirement |
| 45 | 8 | `.github/workflows/full-run.yml` | Uploaded `reports/migration_signoff.md` with `if: always()`, but that file is committed, so a run failing before the gate published the old GO report as its result | Codex review on PR #3 | The gate writes to the runner's temp dir and only that file is uploaded; a run that never reaches the gate uploads nothing |
| 46 | 8 | `sql/snowflake_teardown.sql` draft | Used `ALTER ACCOUNT SET RESOURCE_MONITOR = NULL`, which the Snowflake docs don't document, and claimed a monitor must be dropped after its warehouse, which the docs contradict (dropping an assigned monitor is allowed) | Checking the DROP RESOURCE MONITOR and ALTER ACCOUNT docs before committing | Only documented statements remain; the ordering comment is gone |
| 47 | 8 | README setup step 2 | `cd ~/.snowflake` before generating keys and never returned, so step 5 (`cp .env.example`, `uv sync`) failed in the same shell | Codex review on PR #4 | Absolute key paths, no `cd`; the loop was run in a throwaway HOME and leaves the working directory unchanged |
| 48 | 8 | README cost figures and teardown cost query | Summed `WAREHOUSE_METERING_HISTORY.CREDITS_USED`, which includes cloud-services credits before Snowflake's daily adjustment, so "5.1 credits, about $15" overstated the project's cost | Codex review on PR #4 (the README's own figures were found while checking it) | Project compute is `CREDITS_USED_COMPUTE` (4.60 credits, about $13.80); billed comes from `METERING_DAILY_HISTORY.CREDITS_BILLED` (6.34 for the whole account); both queries run |
| 49 | 8 | README `connections.toml` example | The `[pagila_triage]` section was all comments; TOML sections don't inherit, so copying it gave an empty section and the read-only agent tools couldn't log in | Codex review on PR #4 | Full section; the snippet parses with tomllib and both sections have every field |
| 50 | 8 | README teardown and `sql/snowflake_teardown.sql` comments | Said the database was gone after the 1-day Time Travel window; a dropped permanent database then spends 7 days in Fail-safe (Snowflake-only recovery, storage still billed) before it's purged | Codex review on PR #4 | Both describe the three stages, matching the DROP DATABASE docs |
| 51 | 8 | `CLAUDE.md` commands | The local "what CI runs" command `uv run pytest -m "not target_db"` had no `--env-file .env`, so libpq fell back to port 5432 and the source-backed spec tests couldn't reach the source on 5434 | Codex review on PR #5 | `--env-file .env` added, with a note that CI sets `PG*` itself; run locally as documented: 31 passed |
| 52 | 8 | `CLAUDE.md` architecture notes | Said every pytest test carries `@pytest.mark.req`, but unit and harness tests are untraced by design (G5 covers them), so following it would attach unrelated requirements and degrade traceability | Codex review on PR #5 | Names which suites carry markers and the five files that don't, and says not to add a requirement just to mark a test |
| 53 | 8 | README "pytest and Soda" section (Claude-written) | "Each contract asserts ... valid values and ranges", but `rental.yml` has no valid-value or range check | Codex review on PR #5 | Coverage stated per category, checked against every contract file; the one custom rule is named. While fixing it, the CI test count (29, now 31) was corrected too |
| 54 | 8 | `CLAUDE.md` harness commands | `python -m faults.matrix` / `faults.dbt_mutations` / `faults.pair_matrix` used the system Python, not the uv environment, and no `.env`, so in a clean shell the package or its database settings were missing | Codex review on PR #5 (second pass) | All three are `uv run --env-file .env python -m ...`, matching the README |
| 55 | 8 | README intro (Claude-written) | Called the sign-off "a go/no-go gate run in CI", but PR CI runs only ruff and the Postgres-only tests; the gate runs only in the manually dispatched full run, so a PR can merge without it | Codex review on PR #5 (second pass) | Described as run on demand as a GitHub Actions workflow |

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

## Phase 6: ETL with dbt

- **Source finding:** the legacy business rule lives in `get_customer_balance()`, and its body never ran. It calls `IF()`, which doesn't exist in Postgres, and it was loaded with `check_function_bodies = false`. Its comment promises a replacement-cost rule that the body never implements. So the rules were re-specified from the documented intent instead of being ported.
- **Human decisions** (asked before any model was written):
  - Days late round up.
  - Replacement cost replaces the daily fee when more than 2x overdue.
  - Never-returned rentals are flagged with no fee.
  - Revenue goes to the inventory's store, as the legacy `sales_by_store` view does.
  - The connector is pinned to 4.x (defect 17).
- **Generated:**
  - ETL-001 to ETL-008 in `requirements.yml`, written before the models
  - 6 staging views and 3 marts
  - 3 dbt unit tests, 14 data tests, and 5 singular tests, each tagged `config.meta.requirement`
  - a Postgres re-implementation of every rule in `tests/etl/`
  - 3 mart Soda contracts
  - a manifest-based traceability test
- **Designed around:** Snowflake `DATEDIFF` counts unit boundaries crossed, not elapsed time, so lateness is measured in microseconds. A sub-second unit-test row (1 day + 0.1 s late must be 2 days) pins it.
- **Validation:**
  - 7 rule mutations of the late-returns model: floor, `DATEDIFF(second)`, `<` vs `<=`, `>=` at 2x, additive replacement, fee on never-returned, and due date off by one. The unit test caught all 7.
  - The Postgres re-implementation matches the marts on every store-month, all 999 customers, and all 51,805 rentals.
  - Mart store totals equal the legacy view.
  - A floor-for-ceil source mutation flagged exactly the 27,738 partial-day late rentals from profiling.
  - A planted wrong fee failed the Soda `failed_rows` check.
  - A dropped meta tag failed the traceability test.

## Phase 7: Triage agent blind test

- **Setup:**
  - `.claude/agents/dq-triage.md` (Sonnet) gets only the failing pytest output.
  - It reads the databases through `src/triage/query.py`, using identities that can't write. Postgres has `dq_triage` (SELECT only, read-only transactions). Snowflake has `PAGILA_TRIAGE_SVC` / `PAGILA_TRIAGE` (SELECT only, no secondary roles).
  - Fault backups live in a `FAULTS` schema the triage role can't see.
  - It's barred from the fault files. Compliance was checked by searching each transcript for reads, commands, and write SQL.
- **Draw:** 4 faults chosen at random (seed 886882). The scoring rubric was fixed before reading any answer: 0-2 each for locate, pattern, root cause, and remediation + earliest test.

| Trial | Fault (ground truth) | Locate | Pattern | Root cause | Remediation | Total | Compliance | Queries |
|---|---|---|---|---|---|---|---|---|
| 1 | `tiny_vector_drift` | 2 | 2 | 2 | 2 | 8 | pass | 30 |
| 2 | `drop_rows` | 2 | 2 | 2 | 2 | 8 | pass | 18 |
| 3 | `duplicate_rows` | 2 | 2 | 1 | 2 | 7 | pass | 30 |
| 4 | `drop_check_constraint` | 2 | 2 | 2 | 2 | 8 | pass | 18 |
| | | **8/8** | **8/8** | **7/8** | **8/8** | **31/32** | **4/4** | |

- **Where it was strong:**
  - It located the affected rows and described the change correctly every time.
  - It reconciled aggregate deltas exactly to the affected rows to prove nothing else changed, e.g. amount -9.97 = 1.99 + 0.99 + 6.99.
  - It used evidence I hadn't planned for: float32 ulp spacing, and `LAST_ALTERED` vs `CREATED` timestamps.
- **Where it failed (defect 18):**
  - It asserted a non-existent fact (no PK on RENTAL).
  - In trial 3 it reasoned inconsistently. It drew the right "post-load change" inference from LOAD_LOG counts in trial 2, then missed the same inference in trial 3.
- **Found a real gap in my suite:** trials 2 and 3 independently recommended comparing `LOAD_LOG.ROWS_LOADED` with the table's current `COUNT(*)`. MIG-006 trusts the log's own count, so post-load changes are invisible to it.
- **Access limit it hit:** the triage role can't read `QUERY_HISTORY`, which would have confirmed the mechanism in every trial. It said "unknown" rather than guessing, which is correct behaviour.
- **Caveats:**
  - N = 4.
  - Single-cause faults from a catalog I wrote.
  - The agent knows the codebase.
  - The grader (Claude) shares a model family with the agent, so the scores are evidence, not proof.

## Phase 7: AI-generated SQL from requirement IDs

- **Exercise:** the `dq-triage` agent wrote validation SQL for ETL-006, ETL-002, and MIG-004 (rental) from the requirement text, the mapping spec, and live data, and was barred from the existing implementation. It ran every query read-only. All three requirements hold, and every query ran.
- **Review:** Claude reviewed it and probed the suspect construct with literal values. The human confirmed all 5 findings (defects 19-23, details in `reports/ai_sql_review.md`).
- **Takeaways:**
  - The most important defect (19) is invisible to "it ran and the numbers matched". It took knowing the dialect trap and constructing a counterexample.
  - The agent was candid about its own blind spots (21, 22) but didn't fix them.
  - "Valid SQL that matches on today's data" is not the same as "a correct check".

## Phase 7: Snowflake Cortex

- **Availability (verified in the account; the docs pages read didn't mention it):** on a trial account only `AI_SUMMARIZE_AGG` runs. `AI_CLASSIFY`, `AI_COMPLETE`, `AI_SENTIMENT`, `AI_FILTER`, `AI_COUNT_TOKENS`, and legacy `SNOWFLAKE.CORTEX.COMPLETE` return `399258: not available for trial accounts`. The planned use (classify film descriptions against their categories) wasn't possible.
- **Use (human choice):**
  - `python -m reconcile.record` stores a pytest run in `QA.RECON_RESULTS`.
  - `python -m reconcile.summarize` has `AI_SUMMARIZE_AGG` summarize the failures, then fact-checks the summary for invented requirements, tables, or numbers and for omitted failures.
- **Result on a faulted run (`drop_rows`):**
  - The summary named the right 4 requirements and table, and the "3 rows" count, and passed the check.
  - Close reading still found a misattribution: min and sum differences claimed for `payment_date`, where only the distinct count differed (defect 24).
- **Cost:** 0.000355 credits per call (about $0.0007), from `ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY`.

## Phase 7: External AI review (Codex on PR #1)

- **Findings:** Codex (a different vendor's model) reviewed the PR and left 4 findings, all P2.
  - Three were real defects (25-27) in code that had passed every test, negative control, and self-review. Two of them sat in code that existed only to prevent silent gaps (load logging and recorded runs).
  - That's the case for reviews from an independent model: the same model writing and checking shares blind spots.
- **Disagreed (human decision):** Codex said the column-level `PAYMENT_ID` and `UUID` uniqueness checks in `soda/contracts/payment.yml` reject a source state the schema allows.
  - The checks stay. Postgres forced the source keys to include the partition column, and both columns are generated unique, so a repeat is a quality defect.
  - The contract now explains why.
- **Found while fixing 27:** a Docker single-file bind mount kept serving a stale, truncated copy of the edited init script until the container was recreated. A comment in `docker-compose.yml` now warns about this.

## Phase 7A: Shared foundations for the agents

- **Built:**
  - `docs/dq_checklist.md`: rules from defects 1-27 and the phase findings, which every agent must follow.
  - dbt targets `readonly` (PAGILA_TRIAGE_SVC: runs all 22 dbt tests, can't build) and `mutation` (builds only into `MUT_*` schemas; the real marts' `last_altered` didn't change).
  - `src/faults/dbt_mutations.py`: 16 business-rule mutations across the 3 marts, with unit and data tests scored separately.
- **Baseline for the existing dbt tests: 16/16 killed.** Unit tests alone caught 15, data tests alone 9 (`reports/dbt_mutation_matrix.md`).
- **Predictions written before the run:**
  - Right: all 16 killed, and the unit tests miss `rev_sum_distinct` (defect 28).
  - Wrong on 2: I predicted no data test catches `clv_no_coalesce` or `clv_inner_join`, assuming every customer has a payment. 2 customers don't, so the data tests caught both. That was an unverified assumption about the data, the same failure mode as defect 18.
- **What this means for the agents:** only the unit tests catch 7 mutations, because those mutations don't change any total or grain on today's data. An author agent that writes only data tests can score at most 9/16.

## Phase 7B: dbt-test-author blind evaluation

- **Setup:**
  - Agent `.claude/agents/dbt-test-author.md` (Sonnet) in a blind workspace: model SQL, requirements, mapping spec, and checklist only. All tests were removed, and a leak check found no test or mutation names.
  - It writes only to `proposals/`, verifies with `triage.dbt_check` (read-only dbt), and is scored with `faults.dbt_mutations`.
- **Caveat:** the checklist and requirement text were written after these models were built, so they hint at some edge cases. That's realistic for a team checklist but not a cold start.
- **Result:** 33 tests (5 unit, 19 generic, 9 singular). Every rule ETL-001 to ETL-007 is tagged. 0 false failures on the corrected model.
- **It found a real bug (defect 30)** that every earlier layer had missed.
  - Its 1 µs-late fixture failed. It proved in Snowflake that the model, not the test, was wrong, and reported it instead of weakening the test.
  - The model was fixed. The real-data mart is unchanged: the Postgres re-implementation still matches all 51,805 rentals.
- **Mutation scores (17 mutations, including the real bug as #17):**

| Suite | Caught | Unit tests alone | Data tests alone |
|---|---|---|---|
| Existing tests (Claude, human-reviewed) | 16/17 (missed the real bug) | 15 | 9 |
| `dbt-test-author`, blind | **17/17** | **17** | **15** |

- **Compliance: pass.**
  - The workspace inputs are byte-identical before and after.
  - It wrote only under `proposals/`.
  - It ran no `dbt run`/`build`, loader, or `faults.*` commands.
  - It accessed no files outside the workspace except its own saved tool output.
- **Review (defect 31):**
  - Its unit tests were hand-checked and are all correct, including offset-crossing instants and deliberately repeated amounts.
  - Weaknesses: some recompute tests mirror the model in the same dialect, one consistency check is loose, and its report has a test-count error.
- **Tooling finding:** a new agent file wasn't picked up until the session restarted, even though `.claude/agents/` already existed.
- **Promotion (human decision):**
  - Merged the agent's 5 unit tests into `dbt/models/marts/_unit_tests.yml`, plus 3 singular tests (`mart_rental_returns_outputs_utc`, `mart_rental_returns_matches_rules`, `mart_customer_lifetime_value_matches_source`).
  - Skipped `mart_monthly_store_revenue_matches_payments`, which mirrors the model.
  - Kept `matches_rules` because the human named it, even though it's same-dialect. Its header says so, and `tests/etl` is the cross-dialect check.
  - **Correction:** my recommendation both promoted "the rental recompute" and skipped "the two mirrored checks", although the rental recompute was one of those two. I flagged the contradiction rather than resolving it silently.
- **Merged suite: 17/17 mutations caught, unit tests alone 17, data tests alone 13.** `dbt build` passes (PASS=39). Skipping the revenue mirror costs 2 data-test detections (`rev_local_month`, `rev_staff_attribution`); the unit tests still catch both.
- **Follow-up (human decision): dropped `mart_rental_returns_matches_rules` too**, so both same-dialect mirror tests are now out.
  - Re-scored: still **17/17**; unit tests alone 17, data tests alone 12.
  - The drop cost one real-data detection, `rr_due_off_by_one`. Three unit tests still catch it.
  - `dbt build` PASS=38.

## Phase 7C: migration-check-author blind evaluation

- **Setup:**
  - Agent `.claude/agents/migration-check-author.md` (Sonnet) in a blind workspace: migration requirements, mapping spec, source profile, and checklist only. No reconciliation code, existing checks, or fault names; a leak check confirmed it.
  - Task: tables payment, rental, film, customer, address; requirements MIG-003, MIG-004, MIG-005.
  - It verifies with `triage.check_pair` (read-only pairs) and is scored with `faults.pair_matrix` (clean data, then 12 faults, with verified restores).
- **Result:** 17 check pairs (34 complete SQL files). **0/17 false alarms on clean data.**
- **Fault detection:** **10/12**, exactly as predicted before the run. All 10 faults within its brief were caught. The 2 misses were outside it:
  - `drop_check_constraint` (schema, MIG-002 wasn't assigned).
  - `tiny_vector_drift` (on `film_embedding`, which wasn't assigned).
- **Dialect traps:** all handled.
  - `COLLATE "C"` on text min/max; it passed the `address` trap that fails a naive `min()`.
  - UTC timestamps at microsecond precision; lowercase UUIDs; enums compared as text; the virtual column checked by value; `fulltext` excluded; arrays hashed without relying on JSON formatting.
- **Where it beat the existing suite:**
  - Its row hash length-prefixes each value (`1 || length || ':' || value`), so the encoding can't collide even if a value contains the separator. Mine assumes `chr(31)` never appears.
  - Its aggregates add a sum-of-text-length metric. That caught `trailing_whitespace` and `truncate_strings` at the aggregate layer: 9/10 in-scope faults at that layer against my 8/10. `swap_fk_values` stays row-hash-only for both, by design.
- **Compliance: pass.** Inputs unchanged; it wrote only under `proposals/`; no reads outside the workspace, no forbidden commands, no write SQL.
- **Review (defect 32):** minor only.
- **Promotion (human decision): both improvements ported into `src/reconcile`.**
  - `length_sum` metric for text columns in `aggregates.py`; UUIDs get their own kind because they're fixed length.
  - Length-prefixed encoding in `rowhash.py` and the hand-written payment pair (fixes defect 33).
  - Verified:
    - Old vs new encoding on a counterexample, on both engines.
    - The generator still matches the hand-written pair row for row.
    - Full suite: 157 passed.
  - **Fault matrix: still 12/12, as predicted, and the aggregate layer now also catches `trailing_whitespace`**, which only the row hash caught before.

## Phase 7D: rule-reviewer blind evaluation

- **Setup:**
  - Agent `.claude/agents/rule-reviewer.md` (Sonnet) reviewed a naive, pre-decision draft of the late-fee, revenue, and lifetime-value rules (`proposals/rule-reviewer/input_rules.md`).
  - Workspace: the draft, the mapping spec, and the source profile only. No requirements file. The checklist was left out because it was written from these decisions and would give away about 4 answers.
  - The answer key (13 gaps the draft leaves open, with how each was settled and its real-data impact) was written and fingerprinted before the run (`proposals/rule-reviewer/answer_key.md`).
- **Result:** 14 findings, each with a question, why it matters, evidence, and options.
- **Recall: 12.5 / 13.** Every gap except one half:
  - Raised: G1 rounding, G2 replace vs add, G3 never returned, G4 store attribution, G6 2x boundary, G7 time zone, G8 what 2x measures, G9 zero amounts, G10 customers with no payments, G11 payments before rental, G12 fan-out, G13 due-date arithmetic.
  - Half credit on G5: it raised the late threshold (timestamp vs calendar date) but not the exactly-at-due boundary.
- **Precision: 14 / 14** findings are real gaps (#13, money precision, is minor).
- **Beyond the answer key:**
  - **#11, the paying customer differs from the renting customer on 5 payments**, is a real source quirk not in the known source issues.
  - #12, sparse vs dense store-months, was settled in ETL-002 but missing from my answer key, so the key was incomplete.
  - #5: fees vs revenue.
- **Evidence:** every number re-measured independently and exact, including 27,750 / 22,552 late (timestamp / calendar), 10,535 under 24 h, fee totals $30,244 / $42,496 / $57,788 (floor / round / ceil), 1,827 out over 2x, 25,466 customer-vs-inventory store, 324 month changes in New York time, and 5 payer ≠ renter.
- **Recommendations:** they matched every decision the project actually made. Caveat: the project's original recommendations came from the same model family, so the agreement shows consistency, not independent proof the decisions were right.
- **Compliance: pass.** Inputs unchanged, it wrote only `review.md`, 12 read-only queries, no writes, no access outside the workspace.
- **Defect 34:** confusing labels in finding 3, the uncounted literal reading, and the missed exactly-at-due boundary.

## Phase 7E: External AI review (Codex on PR #2)

- **Findings:** Codex left 5 findings (1 P1, 4 P2). All were real, all fixed (defects 35-39).
- **The P1 was in the safety boundary itself.** `dbt_check` is how the dbt agent runs code against Snowflake "read-only", yet a proposal could pick its own profile. Read-only now rests on three things a proposal can't change: the repo's profile, a test-files-only whitelist, and no writable credentials in dbt's environment.
- **Three were harness honesty bugs:** a crash or a no-op could be scored as a miss or a pass. They didn't change any recorded score: the full mutation re-score is still 17/17, and no fault in the catalog is a no-op.
- **Proof:** a negative control for each fix (above), plus 4 unit tests in `tests/test_qa_tools.py`. Full suite: 161 passed.

## Phase 8: Sign-off report and quality gate

- **`python -m reconcile.signoff`** runs pytest, `dbt test`, and reads the latest `QA.LOAD_LOG` per table in one pass, then writes `reports/migration_signoff.md`: scope, run summary, per-requirement status, a traceability matrix (requirement → pytest functions and dbt tests → result), known issues, waivers, and a go/no-go recommendation. It exits 1 on NO-GO.
- **Gate criteria (drafted by Claude, for the human to approve):**
  - G1: every requirement is covered by a test that ran.
  - G2: every requirement passes or has an approved, unexpired waiver.
  - G3: every known source issue is accepted by a named human.
  - G4: the run is on committed code.
  - G5: every test that traces to no requirement passes (added after the PR #3 review, defect 43).
- **Human decisions live in `requirements/signoff.yml`.** Every disposition starts as `pending` with a recommendation, the same pattern as the mapping decisions, so the gate can't say GO before a human has looked.
- **Cross-checks:** 29 dbt tests match `dbt ls`; 122,209 rows match `INFORMATION_SCHEMA.TABLES` and the source's own counts.
- **Negative control (prediction written first):** with `drop_rows` applied, the gate went NO-GO with exactly MIG-003/004/005/006 and ETL-001/002/003 failing. The ETL failures are dbt data tests comparing the built marts with staging over RAW. Payment was restored to 51,061 rows.
- Unit tests for status, waivers, and the gate are in `tests/test_qa_tools.py`.

## Phase 8: CI

- **PR workflow** (`ci.yml`): ruff plus the 29 tests that need only Postgres, against the same `pgvector/pgvector:0.8.7-pg18-trixie` image as `docker-compose.yml`. Service containers start before checkout, so Pagila is loaded with the container's own `psql` (`ON_ERROR_STOP`, as the image's init does).
- **Full run** (`full-run.yml`, manual): fresh source, load, `dbt build`, then the sign-off gate as the pass/fail step. The key comes from a secret and is written to the runner's temp dir, 0600, never inside the checkout; `SNOWFLAKE_HOME` points the connector there.
- **Versions checked live, not recalled:** `actions/checkout` v7.0.1, `astral-sh/setup-uv` v10.2.0 (it publishes no floating major tag), `actions/upload-artifact` v7.0.1. All are pinned to commit SHAs; the newest releases under two weeks old were skipped.
- **Verified before pushing, with only the CI environment** (empty HOME, so no `~/.snowflake`; only the variables the workflow sets):
  - PR job: a fresh replica container, loaded the same way: 29 passed. An unloaded source fails 2 spec tests, so a broken load can't pass quietly.
  - Full run: the credentials script, then load (16 tables), `dbt build` (38/38), sign-off **GO** with a clean tree.
- **Found by the rehearsal:**
  - Defect 41 and defect 42 (above).
  - `.claude/settings.local.json` was kept out of git only by a global gitignore; the repo's `.gitignore` now covers it, so G4 doesn't depend on one machine.
  - A draft comment claimed dbt needs every target's variables; `dbt parse` without the readonly key variable succeeded, so the placeholder was removed before commit.

## Phase 8: README, cost, and teardown

- **README:**
  - Added: results at a glance, a Mermaid architecture diagram, numbered setup, fault-matrix proof under the layers table, measured cost notes, and a teardown checklist.
  - The diagram was rendered with Mermaid 11 in a browser before committing. That caught one wrong edge: Postgres was drawn writing the load log, but the loader writes it.
- **Costs are measured, not estimated:**
  - 4.60 compute credits on `PAGILA_WH` (`WAREHOUSE_METERING_HISTORY.CREDITS_USED_COMPUTE`) at $3.00/credit (`RATE_SHEET_DAILY`); 6.34 credits billed for the whole account (`METERING_DAILY_HISTORY`). The first draft summed `CREDITS_USED` (defect 48).
  - 73 MB storage.
  - Only about 1.5 of the 4.6 compute credits are attributed to queries, so most spend is per-resume minimums and auto-suspend idle time.
- **Teardown script** (`sql/snowflake_teardown.sql`):
  - Written for the human to run as ACCOUNTADMIN; not run.
  - Checked against the live inventory: all 46 objects owned by `PAGILA_ROLE` are inside `PAGILA_MIG`, and the users, roles, warehouse, and monitor named in the script are exactly the ones that exist.
  - Retention is 1 day (`DATA_RETENTION_TIME_IN_DAYS`), so `UNDROP` works for a day.
  - Suspending an already suspended warehouse errors with "Invalid state"; the checklist says that's harmless.
- **Side effect noticed:** the `recon` connection used for these account queries runs on `COMPUTE_WH`, so the queries resumed that warehouse. It auto-suspends after 60 s.
- Defect 46 (above).
