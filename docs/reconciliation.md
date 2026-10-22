# Reconciliation details

## pytest and Soda

**pytest reconciliation** (`tests/`, `src/reconcile/`) compares the Postgres source with the Snowflake target for every migrated table:
- schema against the mapping spec
- row counts and per-column aggregates
- a normalized row hash per primary key
- orphan and domain-rule checks in the target
- paired checks in `sql/checks/`: a `<name>.pg.sql` and `<name>.sf.sql` that must return identical rows (line 1 is `-- requirement: MIG-00X`; `tests/reconciliation/test_07_pairs.py` runs them)

Failures name the table, column, or key that differs. This is the layer that signs off the migration.

**Soda Core data contracts** (`soda/contracts/`) are declarative YAML checks on one Snowflake dataset at a time: the payment, rental, film, and customer tables in RAW, and the three marts. They assert:
- schema shape and row count (every contract)
- required values and uniqueness (every contract)
- valid values and ranges (every contract except `rental`)
- one custom rule: on `mart_rental_returns`, a daily late fee is $1.00 per day late

pytest runs every contract (MIG-009, ETL-008).

## dbt marts

| Mart | Grain | Rules |
|---|---|---|
| `MARTS.MART_MONTHLY_STORE_REVENUE` | store × UTC month | ETL-001, ETL-002 |
| `MARTS.MART_CUSTOMER_LIFETIME_VALUE` | customer | ETL-003 |
| `MARTS.MART_RENTAL_RETURNS` | rental | ETL-004 to ETL-007: due date, status, days late, late fee |

Rules are written in plain English in `requirements/requirements.yml`. Every dbt test declares its rule in `config.meta.requirement`, and `tests/test_etl_traceability.py` fails if a rule has no dbt test.

## Row-hash normalization

Hand-written for `payment` in `sql/reconciliation/` (both dialects), generalized in `src/reconcile/rowhash.py`. A test proves the generator matches the hand-written pair row for row.

- NULL is encoded as `0` and a value as `1` + its length + `:` + the value. A `\N` token doesn't work, because Snowflake reads `'\N'` as `N`. The length prefix makes the encoding unambiguous: a separator alone lets two different rows produce the same text.
- Timestamps are UTC with microseconds. Numerics use fixed scale. UUIDs are lowercase.
- Strings are compared untrimmed. Pagila has no `CHAR(n)` columns, so trimming could only hide defects.
- Vectors are rounded to 9 decimals per element: no false mismatches on the 1,000 real embeddings, and a 1e-7 drift is caught.
