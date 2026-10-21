# Data QA trap checklist

Rules learned in this project, each tied to where it happened (`D#` = defect number in `AI_LOG.md`, `P#` = phase). All agents read this before writing SQL or tests, and reviewers check against it.

## Postgres ↔ Snowflake dialect

- **DATEDIFF counts unit boundaries crossed, not elapsed time.** `DATEDIFF('second', a, b)` gives 86400 for 1 day + 0.8 s. Measure elapsed time in the stored precision (`microsecond`), or compare timestamps directly. (P6, D19)
- **Text min/max needs `COLLATE "C"` in Postgres.** Postgres sorts by the database locale (`en_US.utf8`); Snowflake compares code points. Without it, 3 Pagila text columns give false mismatches. (P4)
- **Enums order by declaration, not alphabetically,** and can't take a collation. Compare an enum as `::text COLLATE "C"`. The same goes for any non-text source that lands as text, such as `uuid`. (D11)
- **Backslashes are escapes in Snowflake string literals.** `'\N'` is the one-character string `N`. Never use backslash null tokens; encode NULL as `0` and a value as `1 || length(value) || ':' || value`. (P4)
- **`UUID` output is lowercase in Snowflake.** Lowercase on both sides before hashing or comparing. (P2)
- **Snowflake rewrites virtual-column expressions** (`60.0` became `SCALED_ROUND_INT_DIVIDE(LENGTH, 60)`). Don't compare expression text; compare the computed values. (P4)
- **`COPY INTO` is rejected on tables with CHECK constraints.** Load into an unconstrained landing table and `INSERT` from it. (D7)
- **A VECTOR can't be cast from a Parquet list directly**; go `::ARRAY::VECTOR(FLOAT, n)`. (P3)
- **The default Parquet scanner decodes binary as UTF-8.** Use `USE_VECTORIZED_SCANNER = TRUE`. (P3)
- **Snowflake has no correlated subqueries in JOIN conditions;** use plain joins. (D16)
- **`rows` is a reserved word in Snowflake;** don't use it as an alias. (D9)
- **`GET_DDL` output order changes on clone;** compare structure through `DESC TABLE` and `SHOW PRIMARY KEYS`. (D12)
- **Primary keys and foreign keys aren't enforced in Snowflake (NOT NULL and CHECK are).** "No PK error" doesn't mean "no duplicates", so check uniqueness and orphans explicitly. Declared PKs do exist: look them up with `SHOW PRIMARY KEYS` before stating otherwise. (P2, D18)

## Timestamps and time zones

- **This account's default session time zone is `America/Los_Angeles`.** Pin `TIMEZONE = 'UTC'` on every connection, or convert explicitly with `CONVERT_TIMEZONE('UTC', ...)`. (P3)
- **Bucket months in UTC on both sides:** `date_trunc('month', ts AT TIME ZONE 'UTC')` in Postgres, `DATE_TRUNC('month', CONVERT_TIMEZONE('UTC', ts))` in Snowflake. (P6)
- **`TIMESTAMP_TZ` keeps each value's own offset.** Two equal instants can render differently, so normalize to UTC before comparing *text*. Outputs that promise UTC must convert. (D15)
- **Keep microsecond precision.** Format with `US` in Postgres and `FF6` in Snowflake. Truncating to seconds or milliseconds hides real defects. (P4, P5)

## Comparing results across systems

- **Every result set needs `ORDER BY`,** or run-to-run diffs are noise. (D1)
- **Don't collapse rows into a dict keyed by primary key;** duplicates vanish. Count keys and report duplicates per side. (D13)
- **Check numerics at fixed scale** (`FM990.00` for `NUMBER(5,2)`), and integer sums exactly. No float tolerance unless the type is float. (P4)
- **Pick vector or float tolerance from evidence.** 6 decimals hid a 1e-7 drift; 9 decimals had zero false mismatches on real data. (D14)
- **Aggregate fingerprints are a first pass, not proof.** Counts, sums and checksums miss offsetting errors and swaps. Pair them with a row-level comparison, and make every dimension (such as `store_id`) part of the checksum. (D20, D22)
- **Strings are compared untrimmed.** Pagila has no `CHAR(n)`, so trimming can only hide defects. (P4)
- **Length-prefix values when concatenating for a hash.** A separator alone can collide: (`'a'`, `'b␟1c'`) and (`'a␟1b'`, `'c'`) encode identically. Never rely on a separator not appearing in the data. (D33)
- **Add the sum of text lengths to text aggregates.** It catches truncation and a single added or removed character even when distinct counts and min/max don't move. (P7C)
- **A requirement's acceptance criteria are the checklist.** Implement every one, or say explicitly which you skipped and why. (D21)

## Test design

- **A test that has never failed proves nothing.** Show a negative control: break the data or the code on purpose and watch the test fail. (all phases)
- **Data that happens to be clean hides latent bugs.** If a boundary case isn't in the data (exactly at the due date, 1 second late), add it as a synthetic row in a dbt unit test. (D19, P6)
- **Verify after the fact, not just at write time.** A load log's own count misses rows changed after the load; recount the table. (P7)
- **Every failure path must leave a trace.** A crash that skips the FAILED log entry leaves a stale SUCCESS as the latest. (D25)
- **A recorded run must cover every requirement,** or a failing run can be stored as clean. (D26)
- **Configuration you document must actually work when changed** (environment variables, names). (D27)
- **Side effects are part of the test.** Sequences advance even in a rolled-back transaction. (D2)
- **A harness must tell "didn't run" from "nothing failed".** Check exit codes, clear old results before each run, and confirm a fault actually changed the data; otherwise a crash or a no-op is scored as a pass or a miss. (D36-D38)

## Delivering SQL and tests

- **Deliver complete, runnable files.** No `...`, and no "the other blocks have the same shape". (D23)
- **State interpretations and assumptions** next to the SQL, especially where the requirement text is ambiguous.
- **Run what you deliver,** and report the actual result, not the expected one.

## Agent conduct

- **Check facts before stating them.** "No primary key", "already covered", "can't happen": query first, or label it unverified. (D18)
- **Keep reasoning consistent with the evidence.** If a load log's count disagrees with the table, the change happened outside the load. (D18)
- **Say "unknown" rather than guess** when the access you have can't settle a question. (P7, trial 4)
