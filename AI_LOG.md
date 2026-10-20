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
